# 整合狀態與交付缺口

## 這次接通的程式

| 路徑 | 已實作 | 驗證界線 |
|---|---|---|
| Web → API → CC worker → GG renderer | 共用輸入驗證、命令建構、獨立 Python 環境、資料路徑設定 | CPU／假 runtime／瀏覽器測試通過；無新 GPU 結果 |
| GG fork | lean、turntable、環境根目錄、trajectory 基本檢查 | 沿用交接加速實作；未宣稱等品質或新速度數字 |
| CC／ActorsHQ | 固定官方 commit；子程序 DEFAULTS 配置 | 不是遠端 dirty checkout 的完整重現 |
| 離線入口 | prepare、initialize、reconstruct、register-template、register-sequence、appearance、convert、dynamics | 每階段獨立 opt-in 執行，不假裝 UV／人工審核能自動完成 |
| 品質工具 | 8 個 mask／相機／mesh／資料切分工具 | 原樣搬移，沒有自動套用 TSDF 白名單，也未驗證門檻品質 |
| 資產檢查 | 實際消費路徑、可選 SHA256、基本 trajectory 檢查 | 不等於完整拓撲、人體座標、模型語意驗算 |

## 使用順序

先 `pip install -e .`，複製並填寫 paths.local.json。CC／GG／重建環境依各固定 checkout 的 README／INSTALL 建立；Web 的 .venv 不承擔所有 CUDA 套件。先使用 `doctor`，再用 `doctor --probe` 檢查專用 Python 中的套件規格；這不會載入模型或啟動訓練。

```bash
python -m realfit3d.cli --config configs/paths.local.json doctor --probe
python -m realfit3d.cli --config configs/paths.local.json offline prepare --subject Actor08 --gender male --prompt "plaid shirt"
python -m realfit3d.cli --config configs/paths.local.json offline initialize --subject Actor08 --frame 0
python -m realfit3d.cli --config configs/paths.local.json offline reconstruct --subject Actor08 --prompt "plaid shirt"
```

預設只輸出 JSON 計畫與缺少的路徑，不執行。確認輸入、輸出和成本後，加 `--execute` 執行該階段。執行紀錄與 log 放於 `output_root/offline_jobs/<id>/`。訓練依上游自身規則寫 checkpoint，不自動替既有實驗改名或覆寫設定。

S1 後需先完成 UV seams／unwrap，得到 stage1/template_uv.obj；再依序使用 register-template、register-sequence、appearance。各階段不是一個可無人監督按到底的按鈕。appearance 沿用官方原始設定（程式內仍會把 epochs 設為 5）；不以 argparse 宣告的 3 冒充實際值。

`convert` 呼叫官方 GauGarConverter 產生 Stage4、garment dictionary 與 CC finetune YAML；若已有 Stage4 或同名 YAML，拒絕覆寫。官方 converter 會在 CC 的 configs/finetune 寫入新 YAML，因此執行後需檢查 git status、訓練設定、pin 與資料切分。`dynamics` 才執行對應 CC 訓練。此轉換入口不等於 Web 的恢復／relax 匯入入口，兩者用途不同。

Web 與 CLI 試衣使用同一個命令建構器：

```bash
python -m realfit3d.cli --config configs/paths.local.json tryon \
  --betas /trusted/body/betas.pkl --height 1.70 --weight 58 --gender female \
  --upper 00170_upper --lower 00170_lower --motion 0
```

betas 必須來自可信擬合結果且與列出的身體條件一致；CLI 不反序列化它來猜測。不要傳入網路下載的不可信 pickle。CLI 和 Web **尚無跨程序 GPU 排程**，不可同時啟動 GPU 工作。

品質工具命令預設同樣為 dry run。使用 `--execute` 之前請先閱讀工具的參數與覆寫行為：

```bash
python -m realfit3d.cli --config configs/paths.local.json quality --execute audit_tsdf_views -- --help
```

## 為何沒有直接混合兩套 Fixed-size

前端版和 backend_temp 不是完全相同的工具：前端版增加 fit-aware waistband pin、重建 node_type、pin-loop 選項及可選 collision radius。直接以其中一份覆蓋另一份可能改變模擬結果。Web／tryon 目前統一走前端交接版；backend 的舊版保留為比較來源，不再作為另一個默默可切換的 Web 實作。

experimental_smplx_pose_transfer 尚未升為預設路徑，其 ICP fallback 與報告描述差異仍需研究驗證。固定身形預計算／跨任務結果快取與鄰近身形加速仍是待實作設計，不是「缺一個檔案就已有的功能」。

## 需要補交的實際項目

1. **透明度 V3：只有文字，沒有核心 code。** 重新 fetch 後，transparent_garments_temp/main 仍為 f706ff4，全部 9 個追蹤檔案只含 Markdown 與 3 個 actor shell scripts。沒有 active/v3/common.py、train.py、evaluate entry 或 checkpoint，沒有其他遠端分支。請提供 V3 程式、設定、相容 Stage3 權重識別與推論範例；不用先整理成完美 package。
2. **遠端 S2／S3 修改：報告提過，但未附完整 diff。** backend_temp/evidence/ORIGIN_STATE.md 明確記錄 dirty 狀態未嵌入。需要當時 commit 加 diff，或可唯讀檢查的 checkout 路徑。不能把官方原版當作這些修改已重現。
3. **GPU 驗收：有程式但缺可用部署存取與資產定位。** 本機是 6 GiB RTX 3060，尚無 ccraft／gaugar Conda 環境；首次 SSH 測試停在跳板機 public-key 驗證，尚未檢查遠端目錄。先提供能登入的 SSH 設定及一套已成功跑過的衣物／動作／模型路徑。
4. **發布：本機有提交，不代表 GitHub 已收到。** 必須先 push GG fork，再 push 主 repo 的 gitlink；目前 GitHub CLI 憑證尚未配置。不要先發布主 repo 去引用尚未上傳的 fork commit。

來源檔案的固定 commit 與 SHA256 見 source_manifest.json。那是來源摘要，不是聲稱修改後檔案仍與來源相同。

## 下一個 GPU 驗收

選一組組員已跑通的衣物和動作。先唯讀 inventory、確認環境和授權資料，再執行同一組舊／新命令。比較 garment_names 順序、頂點／面／UV、frame 數、PNG／MP4、耗時與峰值記憶體；記錄 checkpoint 雜湊與完整命令。沒有完成這一步前，不標成「全專案整合完成」。
