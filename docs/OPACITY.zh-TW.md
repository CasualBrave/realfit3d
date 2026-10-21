# 透明度

[English](OPACITY.md)

## 流程

模擬 mesh 決定衣服的形狀，GG Stage 3 checkpoint 提供 Gaussian 外觀。
透明度模組在光柵化前調整每顆 Gaussian 的 alpha，再由渲染器將衣服與人體合成。
多角度預覽與動畫使用相同設定；使用者調整透明度不會重新訓練模型。

- `direct`：每顆 Gaussian 的 opacity 直接乘上控制值。
- `optical_depth`：使用 `1 - (1 - alpha)^s` 調整。
- `v3`：`4 → 32 → 32 → 8` 網路讀取原始 opacity 與正規化初始位置，
  產生單調函數 `m(s)`，再使用 `1 - (1 - alpha)^m(s)` 調整。

三種模式在 1 時保留原本 Gaussian opacity，在 0 時隱藏衣物。
V3 對整套穿搭使用同一個控制值，但每件衣服各自載入對應權重。
這裡調整的是渲染透明度，不是布料力學或材質折射。

## 設定 V3 衣物

控制器必須搭配訓練時使用的 Stage 3 資產。每件衣物的 catalog 項目加入
相對於 `gg_output_root/<衣物名稱>/` 的路徑：

```json
{
  "name": "Actor02_upper",
  "opacity_controller": "opacity_controller_v3/controller.pt"
}
```

這段內容補入原本的項目，保留其 slot、label、thumbnail、source_gender 欄位。
Actor02 下身交付的相對路徑為
`opacity_controller_v3_valid_cameras/controller.pt`。
瀏覽器不能任意指定 checkpoint 檔案路徑。
選中的上下身都設定 controller 時，網頁才開放 V3 選項；
預設範例 catalog 尚未指定 V3 權重。

## 渲染

在選衣頁選擇控制模式與不透明度，再按生成。目前會建立新的試衣任務，
不是拖動滑桿就立即重新渲染既有結果。

`POST /generate` 接受 `opacity_mode` 與 `opacity_scale`，預設為 `direct`、`1`。
無效或非有限數值會在啟動任務前被拒絕。CLI 使用相同設定：

```bash
python -m realfit3d.cli --config configs/paths.local.json tryon \
  --betas /trusted/body/betas.pkl --height 1.70 --weight 58 --gender female \
  --upper Actor02_upper --lower Actor02_lower --motion 0 \
  --opacity-mode v3 --opacity-scale 0.5
```

這條命令先列出計畫，加 `--execute` 才執行；選用的衣物與人體資產須已完成配置。
單獨執行 GG 渲染的方式見
[GG 說明](../upstream/Gaussian-Garments/REALFIT3D_CHANGES.zh-TW.md#透明度控制)。

## Stage 3 後訓練

可選的離線 `opacity` 階段讀入 Stage 2 mesh、point cloud、AO／normal 貼圖、
相機校正資料與影像尺寸，以及 Stage 3 checkpoint。
固定 GG 後先渲染原始 alpha 圖 A1，再抽取 s，只訓練 controller，
讓新 alpha 圖接近 `s * A1`。產出的控制器與同一件衣物的 Stage 3 權重一起保存。

```bash
python -m realfit3d.cli --config configs/paths.local.json offline opacity \
  --subject Actor02_upper --sequence Sequence1
```

確認計畫後加 `--execute`。預設輸出至
`gg_output_root/Actor02_upper/opacity_controller_v3/`，已有目錄時會拒絕覆寫。
fork 的 `train_opacity_v3.py` 另提供指定訓練幀、相機、步數及新輸出目錄的參數。

訓練屬於衣物資產準備，不會在每次使用者請求時執行。
匯入已有控制器的衣物可跳過訓練。

目前訓練讀取器要求 `gg_data_root/<subject>/<sequence>` 下有以相機名稱為鍵的
校正字典，以及各相機影像目錄；它會讀取 PNG 取得影像尺寸。
Stage 2 輸出的渲染相機清單本身不符合這個輸入配置。

2026-10-21 補件已包含每件衣物 50 幀配準 mesh、50 張 AO、50 張 normal，
以及 Stage 2 點雲。Actor02 的 `stage1/cameras.json` 也有完整校正資料與影像尺寸。
這些資產已具備，但訓練讀取器尚未支援直接使用這種不含原始影像的交付配置。
完整重訓尚未執行；既有 controller 的推論方式不變。
