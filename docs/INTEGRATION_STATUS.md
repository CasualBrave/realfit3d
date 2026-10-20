# 整合狀態

## 功能與驗證

| 路徑 | 已實作 | 驗證界線 |
|---|---|---|
| Web → API → CC worker → GG renderer | 共用輸入驗證、命令建構、獨立 Python 環境、資料路徑設定 | CPU／假 runtime／瀏覽器測試通過；無新 GPU 結果 |
| GG fork | lean、turntable、環境根目錄、trajectory 基本檢查 | GPU 畫質、耗時比較待執行 |
| CC／ActorsHQ | 固定官方 commit；子程序 DEFAULTS 配置 | 不是遠端 dirty checkout 的完整重現 |
| 離線入口 | prepare、initialize、reconstruct、register-template、register-sequence、appearance、convert、dynamics | 各階段獨立執行；UV 製作與 mask 覆核為人工步驟 |
| 品質工具 | 8 個 mask／相機／mesh／資料切分工具 | 算法沿用 backend；TSDF 白名單需手動接入，門檻待資料集驗證 |
| 資產檢查 | 實際消費路徑、可選 SHA256、基本 trajectory 檢查 | 拓撲、人體座標與 checkpoint 相容性需另外核對 |

## 使用順序

先 `pip install -e .`，複製並填寫 paths.local.json。CC／GG／重建環境依各固定 checkout 的 README／INSTALL 建立；Web 的 .venv 不承擔所有 CUDA 套件。先使用 `doctor`，再用 `doctor --probe` 檢查專用 Python 中的套件規格；這不會載入模型或啟動訓練。

```bash
python -m realfit3d.cli --config configs/paths.local.json doctor --probe
python -m realfit3d.cli --config configs/paths.local.json offline prepare --subject Actor08 --gender male --prompt "plaid shirt"
python -m realfit3d.cli --config configs/paths.local.json offline initialize --subject Actor08 --frame 0
python -m realfit3d.cli --config configs/paths.local.json offline reconstruct --subject Actor08 --prompt "plaid shirt"
```

預設只輸出 JSON 計畫與缺少的路徑，不執行。確認輸入、輸出和成本後，加 `--execute` 執行該階段。執行紀錄與 log 放於 `output_root/offline_jobs/<id>/`。訓練依上游自身規則寫 checkpoint，不自動替既有實驗改名或覆寫設定。

S1 後先完成 UV seams／unwrap，得到 `stage1/template_uv.obj`，
再依序執行 register-template、register-sequence、appearance。
appearance 沿用官方程式內設定，實際執行 5 epochs；
argparse 的預設值 3 會被程式覆蓋。

`convert` 呼叫官方 GauGarConverter 產生 Stage4、garment dictionary 與 CC finetune YAML；若已有 Stage4 或同名 YAML，拒絕覆寫。官方 converter 會在 CC 的 configs/finetune 寫入新 YAML，因此執行後需檢查 git status、訓練設定、pin 與資料切分。`dynamics` 執行對應 CC 訓練。Web 的恢復／relax 匯入入口則準備線上試衣資產。

Web 與 CLI 試衣使用同一個命令建構器：

```bash
python -m realfit3d.cli --config configs/paths.local.json tryon \
  --betas /trusted/body/betas.pkl --height 1.70 --weight 58 --gender female \
  --upper 00170_upper --lower 00170_lower --motion 0
```

betas 應使用與輸入身體條件一致的可信擬合結果；CLI 只檢查檔案路徑。
pickle 反序列化可執行程式碼，僅使用已核准來源的檔案。
CLI 和 Web **尚無跨程序 GPU 排程**，GPU 工作需逐一執行。

品質工具命令預設同樣為 dry run。使用 `--execute` 之前請先閱讀工具的參數與覆寫行為：

```bash
python -m realfit3d.cli --config configs/paths.local.json quality --execute audit_tsdf_views -- --help
```

## Fixed-size 實作選擇

Web／tryon 統一使用前端交接版，包含 fit-aware waistband pin、node_type 重建、
pin-loop 選項及可選 collision radius。backend_temp 的版本保留作為比較來源。

experimental_smplx_pose_transfer 保留為實驗分支，其 ICP fallback 行為待驗證。
固定身形預計算、跨任務結果快取與鄰近身形加速列入後續開發。

## 整合工作進度

1. **透明度 V3：程式與權重已定位，接入進行前需完成相容性比對。** 遠端交付包含 SplineOpacityController、推論接入程式及 Actor02 上下衣 controller.pt。Actor01／06／07 使用 direct opacity。路徑與雜湊見 [遠端發現紀錄](REMOTE_DISCOVERY_20261020.md)。
2. **S2／S3：待比對遠端訓練修改。** backend_temp/evidence/ORIGIN_STATE.md 記錄了遠端工作目錄的未提交變更；下一步從交付程式與實際 checkout 產生相對官方基線的 diff，核對啟動參數。
3. **GPU 驗收：已接通 cvlab-5090-p，完成初步檔案檢查。** 待確認環境與資產後，執行同組輸入的舊／新流程比較。
4. **發布：2026-10-20 已推送首輪整合。** GG fork 的程式整合提交為 `8a52dc6`，主專案為 `1a91602`。目前採用版本見 `upstream.lock.json`；更新順序為 GG fork、主專案 gitlink。

來源檔案的 commit 與 SHA256 見 `source_manifest.json`；
該檔記錄匯入時的來源版本，後續變更記錄於 Git 與 [MODIFICATIONS.md](MODIFICATIONS.md)。

## 下一個 GPU 驗收

### 遠端操作範圍

- 使用者指定 `/home/vtongroup/lin/` 為後續工作目錄；建立前先通知，若已存在先唯讀確認用途，不直接覆寫。
- 其他既有小組目錄只讀：不修改、搬移、刪除，不在既有 checkout 執行安裝、pull、訓練或實驗腳本。
- 程式修改與 GitHub push 在本機完成；伺服器僅在 `lin/` 下的獨立 checkout 取得更新，不在伺服器登入使用者的 GitHub。
- 實驗前檢查所有寫入路徑，包括模型轉換設定、暫存、套件快取、log 與輸出，全部置於 `lin/` 內。不以連到既有目錄的 symlink 作為可寫工作副本。
- 先唯讀比對程式與版本差異，核對執行腳本和設定，再選定測試版本。

選一組既有成功結果的衣物和動作，在新工作目錄執行同組舊／新命令。
驗收項目為 garment_names 順序、頂點／面／UV、frame 數、PNG／MP4、
耗時與峰值記憶體；每次結果記錄 checkpoint 雜湊、完整命令及差異。
