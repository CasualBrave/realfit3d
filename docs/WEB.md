# Web 整合與驗證界線

## 執行責任

瀏覽器 (`apps/web`) → Flask (`apps/api/server.py`) → `PreviewRuntime` adapter → 專用 ccraft Python 執行保留的 worker → 專用 GG Python 渲染 → PNG／MP4 與 status.json → 瀏覽器輪詢。

Web 環境只安裝 Flask，不 import torch、SMPL-X、Blender 或研究套件。worker 的 subprocess 命令使用參數陣列，不透過 shell；GPU 環境與網站 Python 分開。人體擬合仍同步等待，試衣以背景程序執行。

`scripts/check_checkout.py` 是來源檢查工具，不是網站也不是訓練流程。`workers/contourcraft` 保留交接佈局以降低搬移風險，並不表示這些都是 ContourCraft 官方程式。

## GPU 先決條件

`configs/paths.example.json` 所有路徑皆需改成部署機器的絕對路徑：

- `ccraft_python`：已具備 ContourCraft、torch、SMPL-X 等依賴的環境。
- `gaugar_python`：已具備 GG、Blender／渲染依賴的環境。
- `contourcraft_root`：既有可運作的 ContourCraft checkout；目前尚未固定為本 repo submodule。
- `gaugar_root`：已安裝交接版 `render_lean.py`、`render_turntable.py` 與其配套 `inference.py` 的 GG 部署目錄。**不能直接指定目前仍為官方基線的 submodule 就認為完整可跑。**
- `body_model_root`、`reference_motion`、`checkpoint`：有合法使用權的模型、參考動作與 CC 權重。
- `output_root`：既有衣物資產／預熱快取與新結果的根目錄；catalog 的衣物 ID 必須與該目錄及 GG 資產對應。缺少官方訓練衣物時，須先按交接流程匯入，不能單靠目錄名稱產生。

GG 部署差異來源：[frontend_temp/Gaussian-Garments 固定版本](https://github.com/CasualBrave/frontend_temp/tree/2a643b1b43a0329dce23b7c40fbc2757bcfab968/Gaussian-Garments)。本次未自動覆蓋 GG 或執行上游安裝。接下來應比較這些修改、遷入團隊 GG fork、驗證後更新 submodule，不長期依賴不明版本的外部部署。

檔案存在檢查只能及早拒絕缺少路徑，不能證明 CUDA、checkpoint、模型授權、資料相容性或推論品質已通過。`catalog.json` 是交接樣例，不代表資產與權重隨 repo 提供。

## API 與安全界線

| API | 責任 |
|---|---|
| GET `/`、`/garment_thumbnail/<id>` | 頁面與衣物縮圖 |
| POST `/fit_body` | height（公尺）、weight（公斤）、gender；產生人體 |
| GET `/body_status`、`/body_preview.png` | 目前人體與預覽 |
| POST `/discard_body` | 閒置時清除目前人體 |
| POST `/generate` | upper、lower、motion（catalog 索引）；啟動試衣 |
| GET `/status/<id>`、`/latest_frame/<id>` | 程序狀態與渲染進度 |
| GET `/file/<id>/<path>` | 限該次任務中的圖片／影片，拒絕跨目錄與 symlink 逃逸 |

鎖與任務表僅在單一程序內有效，不支援多 WSGI worker 或多人服務。無認證、持久化排程、取消或重啟恢復；重啟不會重新認領既有程序，應待 GPU 任務結束後再重啟。body 資料不進 Git；替換／清除會刪除目前人體。程序重啟遺留的人體目錄需自行清理。

新任務不再自動刪除其他試衣結果。請定期檢查 output_root 空間，先確認目錄再清理。Web 不提供任意檔案／pkl 下載，也不接受上傳 pkl。

## 驗證

```bash
python -m unittest discover -s tests -v
python scripts/check_checkout.py
```

測試使用假 runtime，不計算人體或衣物。驗證頁面／縮圖、輸入錯誤、缺少環境、互斥、程序失敗、半寫入 JSON、結果路徑與命令順序。真實 GPU 驗收仍需在同組輸入上比較舊／新流程的 mesh、轉盤、影片、耗時與記憶體。

沒有承諾新架構更快，也沒有把本次重構算成新訓練結果。

可選 UI 檢查：另安裝 `playwright` 與其 Chromium，在未設定 GPU runtime 的本機服務運行時執行 `python tests/browser_smoke.py`。可用 `REALFIT3D_BROWSER` 指定已有的 Chromium，`REALFIT3D_URL` 指定服務網址。此測試會 mock 人體狀態來檢查選衣頁，沒有偽造後端推論；截圖存於 `/tmp/realfit3d-*.png`。
