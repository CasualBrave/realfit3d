# 遠端交付初查：2026-10-20

維護紀錄：供程式接入、資產核對與實驗安排使用。

## 範圍

以使用者授權的 SSH agent 登入 `cvlab-5090-p`，唯讀檢查
`/home/vtongroup/iismtl5197096_actor1267_delivery_20261020/`。
本輪只列目錄、讀取文字與計算下列四個檔案的 SHA256；
未建立遠端資料夾、修改檔案、執行交付腳本、載入 checkpoint 或啟動 GPU 工作。
以下路徑均相對於上述交付目錄。

## 已確認的程式與權重

- `Gaussian-Garments/opacity_controller_v3_common.py`：已閱讀實作，
  `SplineOpacityController` 用 base alpha 與正規化 canonical xyz 作為四維輸入，
  經 MLP 產生八個正值、正規化的區間權重，構造單調分段線性控制函數；
  輸出以 `1 - (1 - alpha)^m` 控制 opacity，並處理 s=0、s=1 端點。
- `Gaussian-Garments/inference_opacity.py`：已讀到 V3 import、按衣物選取並載入
  controller、subject/normalization 檢查及 pre-raster opacity 控制分支。
  direct 模式則使用 `base_opacity * opacity_scale`。
- 訓練與評估入口 `train_opacity_controller_v3.py`、
  `evaluate_opacity_controller_v3.py` 已閱讀主要流程；詳見後續訓練查核紀錄。
- Actor02 上衣及下衣的 `controller.pt` 均為存在的普通檔案，已計算雜湊，
  未反序列化，因此尚未驗證權重內容與載入相容性。

| 檔案 | SHA256 |
|---|---|
| `Gaussian-Garments/opacity_controller_v3_common.py` | `d9f0d2f25f1476e72466e1f34baadf15a559bca7064eff2e40098a1d39094d68` |
| `Gaussian-Garments/inference_opacity.py` | `9e9dc5917850c53e1dd7e4b0cd12780f899de685a6a8775369e9f5e9993c6bd0` |
| `output_actorshq_gg/Actor02_upper/opacity_controller_v3/controller.pt` | `4d7f0dbd2e31c613761fd10d18665885b17d5ed4b6a18aeca2ba812395cfda5d` |
| `output_actorshq_gg/Actor02_lower/opacity_controller_v3_valid_cameras/controller.pt` | `255e9b0dea842e228b49dd8c52fc6f7ac3aca2d0c66283514ba89c755d458d61` |

## 交付設定與既有測試紀錄

已閱讀 `outputs/frontend_handoff_actor1267/FRONTEND_DELIVERY_20261019.md`
與 `frontend_runtime_modes.json`：

- Actor02 使用 learned V3；Actor01、Actor06、Actor07 使用 direct pre-raster opacity。
- 每次推論只有一個全域 0–1 控制值，尚非獨立上下衣滑桿。
- Actor01、Actor06 的指定 trajectory 是 replay；Actor02、Actor07 指向 Stage4 simulation。
  Replay 提供既有動作的重播輸入；新身形模擬需要另跑 ContourCraft。
- 交付紀錄中的資產驗證為通過；RealFit3D 的全量 checksum 與 GPU 驗收排在資產接入階段。

## 接入狀態

先前的 GitHub 交付提供研究說明與 actor scripts；
本次遠端交付另提供 V3 核心程式與 Actor02 權重。
目前已完成來源定位與初步閱讀，接下來進行程式比對、資產驗證與 GG 接入。

### 後續訓練查核

恢復連線後，已閱讀 V3 訓練迴圈、共用資料／渲染函式、不同衣物／相機入口、
主要評估流程與資料量實驗入口。固定模型、alpha 校準目標、loss、
取樣與 checkpoint 格式均已從程式確認。
詳見 [透明度訓練與接入紀錄](OPACITY_TRAINING_REVIEW_20261020.md)。

後續先唯讀比對 S1–S4、推論與設定差異，辨別必要修正、實驗分支和機器路徑。
需要實驗時先通知使用者，僅在 `/home/vtongroup/lin/` 建立工作副本，
不得執行會寫回既有小組目錄的程式。本機完成程式修改與 push，
伺服器只在新工作副本取得更新。
