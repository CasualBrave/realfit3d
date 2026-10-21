# 透明度 V3 訓練與接入紀錄

本文件保留接入前的來源查核。後續實作、GPU 測試與現況見
[透明度接入紀錄](OPACITY_INTEGRATION_20261020.md)。

維護用，2026-10-20。來源為伺服器交付目錄
`/home/vtongroup/iismtl5197096_actor1267_delivery_20261020/Gaussian-Garments/`。
本次只讀文字與計算雜湊，沒有執行遠端程式、載入 checkpoint 或改動遠端檔案。

## 1. 已確認的流程

```text
Stage 2 mesh、AO／normal 貼圖、相機 + Stage 3 epoch 5 模型
    → 固定幾何與原模型參數
    → 原 opacity 光柵化得到 A1
    → 取控制值 s，建立目標 s × A1
    → V3 產生新的逐 Gaussian opacity
    → 光柵化得到 As
    → 比較 As 與 s × A1，反向更新 V3
    → controller.pt
```

訓練入口是 `train_opacity_controller_v3.py`，資料與渲染函式在
`opacity_controller_common.py`。`load_frozen_model` 載入 Stage 3 checkpoint，
要求 epoch 為 5，將 AvatarNet 參數設為不可訓練。原 opacity 與幾何狀態均
detach；optimizer 只包含 V3 controller 的參數。

訓練目標是渲染 alpha，不是透明衣物照片。相機資料夾的 PNG 用來取得影像尺寸，
本流程沒有拿其 RGB 作為透明度 supervision。

## 2. 控制器如何調整 opacity

`SplineOpacityController` 的 MLP 為 `4 → 32 → 32 → 8`，
中間使用 SiLU，共 1,480 個參數。輸入是每顆 Gaussian 的原 opacity
及標準化 canonical xyz；控制值 s 用於後面的分段線性函數。

MLP 輸出經 softplus 加 epsilon，再正規化為八個正值權重 p。
權重的累積和定義八段分段線性函數 m(s)，且 m(0)=0、m(1)=1。
Gaussian opacity 轉換為：

```text
alpha_new = 1 - (1 - alpha_base) ^ m(s)
```

實作用 log1p／expm1 計算，並對 s=0、s=1 明確回傳零與原 opacity。
初始最後一層權重與 bias 為零，因此八段權重均為 1/8，
起點對應 optical-depth 縮放 `m(s)=s`。

訓練的原因是多顆 Gaussian 的 alpha 合成不是線性相加；
逐顆乘 s 不一定使整張圖的 alpha 等比例縮小。
V3 學習每顆 Gaussian 的控制曲線，讓最後的影像 alpha 接近要求比例。

## 3. Loss 與預設設定

令 A1 為原模型的 alpha 圖，As 為控制後的 alpha 圖：

```text
w = 1[A1 > 0.001] + 0.25 × A1
L_cal = sum(w × abs(As - s × A1)) / max(sum(w), 1)
L_reg = mean((p - 1/8)^2)
L = L_cal + 0.001 × L_reg
```

前景權重使空背景不主導誤差，正則項將分段權重約束在均勻分布附近。
梯度經由 alpha rasterizer 回到 controller。

以下為參考訓練入口的程式預設，並非已讀出兩份交付 checkpoint 的實際設定：

| 項目 | 值 |
|---|---|
| 衣物 | Actor02_upper |
| 訓練／驗證／測試幀 | 0–29／30–39／40–49 |
| 相機 | 從有標定且有影像目錄的相機中選取，最多 8 台 |
| 控制值 | 每步均勻抽樣 0.05–0.95 |
| optimizer | Adam，learning rate 0.001 |
| 訓練步數 | 5,000，smoke 預設 20 |
| 渲染尺寸 | 原影像寬、高各乘 0.5 |
| 輸出 | controller.pt、config.json、train_log.csv、validation_metrics.csv、training_summary.json |

`controller.pt` 存 controller state_dict、canonical_center、canonical_scale、
step 與 config。完整訓練入口讀取 50 幀 Stage 2 mesh 及預烘焙貼圖；
目前供前端使用的交付資產清單不包含這套訓練輸入。

## 4. 其他訓練與評估入口

### 不同衣物與相機設定

`run_v3_protocol_experiment.py` 配合 `opacity_protocol_utils.py`，
提供 `--subject`、`--output-name`、`--train-cameras`、
`--heldout-cameras`，沿用相同 controller、loss 與 checkpoint 格式。
訓練與保留相機不能重疊；驗證使用訓練相機配未參與訓練的幀，
測試另可加入保留相機。此入口仍要求 Stage 3 epoch 5 與 50 幀 Stage 2 資料。
它會讀取 Actor02_upper 的參考 controller 並計算 hash，因此不是任意衣物可獨立啟動的通用入口。

### 模型比較

`evaluate_opacity_controller_v3.py` 比較 Direct、Optical depth、V1、V2、V3，
在測試幀與控制值 0、0.25、0.5、0.75、1 上計算：
前景 alpha MAE、要求比例與渲染比例之差、端點誤差、Gaussian 與像素單調性。
它需要 V1、V2 權重及訓練紀錄；並非只靠 V3 前端交付包即可執行。

程式含 renderer early-termination 的研究說明，將 Gaussian 單調性與像素單調性
分開記錄。本輪沒有獨立比對該 CUDA kernel 或重跑評估。

### 資料量實驗

`run_v3_data_efficiency.py` 使用 5／10／20／30 幀的巢狀子集合，
以時間距離的 greedy farthest-point 方法選幀，各跑 seeds 0、1、2。
每組仍使用 5,000 步與同一組八台相機，以比較固定優化預算下的資料量影響。
這是程式設定；本輪沒有取得這 12 組執行結果。

## 5. 推論如何使用 checkpoint

`inference_opacity.py` 依衣物名稱選擇 controller，檢查 subject 與正規化參數，
將當前 Gaussian 的原 opacity、canonical xyz 及全域控制值送入 V3。
上、下衣各用自己的 controller，得到的 opacity 合併後再套 visibility mask，
送入 Gaussian rasterizer。人體先獨立渲染為 mesh 影像，再與衣物做 alpha 合成。

交付 README 記錄 Actor02 上下衣各用 5,000 步 controller，
Actor01／06／07 使用 direct。兩個 Actor02 controller 檔案已確認存在，
但尚未反序列化核對其 config／step。

目前 `prepare_gaussian` 每次處理相機時都會執行 controller。
controller 輸入不含相機或當前變形頂點，後續可考慮在固定模型與 s 時快取輸出；
這項最佳化尚未實作。

## 6. 接入工作

| 層級 | 修改範圍 |
|---|---|
| GG fork | 移入 controller 與必要載入函式；在既有渲染流程加入 opacity 模式與控制值；保留不透明預設 |
| 渲染入口 | lean／turntable 傳入同一套透明度設定，避免分別維護完整 renderer |
| RealFit3D | catalog 登錄各衣物可用模式與 controller 路徑；API／CLI 傳遞設定；網站提供控制值 |
| 資產 | Stage 3 模型與相應 controller 配對；權重放資產目錄，不放程式 Git repo |
| 測試 | s=0／1、控制曲線、上下衣順序、缺少權重、圖片／影片與全流程測試 |

獨立的 config.json、training_summary.json、train_log.csv 與比較結果，
在本交付目錄深度 6 以內的搜尋中未找到；兩個 controller 目錄只列出 controller.pt。
以上是 2026-10-20 查核時的交付範圍。2026-10-21 已補交 Stage 2 mesh、
AO／normal、點雲與相機清單，逐檔驗證結果見
[接入紀錄的補件章節](OPACITY_INTEGRATION_20261020.md#stage-2-supplement-2026-10-21)。
GG fork `5c03d7e` 已支援 Stage 1 校正與 Stage 2 視角清單，Actor02 上下衣通過 CPU 相機檢查。
完整重訓尚未執行；若要重現原 controller 的確切訓練，
還需對應實際 command、設定／log 與 Stage 3 checkpoint 識別。

## 7. 本輪閱讀的原始碼版本

| 檔案 | SHA256 |
|---|---|
| train_opacity_controller_v3.py | `68ff83895b0816c717b3b81719767fec73040712a13f8b9e59a25f8215fef52e` |
| opacity_controller_common.py | `f9e596bdd54a46c0217d4915d08fcc06074e9c48a8ad1585e479a32aec6a29ee` |
| run_v3_protocol_experiment.py | `3d0378f373a060cd76964000f0a87119a38a3b3fd2410a31c18f571fc2cf4dcf` |
| opacity_protocol_utils.py | `be1b8a1273a66189f7e1d40bf9cef0d05a6a44bd83b385edb30501dd1b02c0d3` |
| evaluate_opacity_controller_v3.py | `41eeb500b2bbe5831fad711123cf527b7f9b15d9741d6ff50891b878621ce048` |
| run_v3_data_efficiency.py | `cc38f0b74c2681037a3a70f3f23ac0ad05e82810ded96cf413cb5f9a9107049b` |
