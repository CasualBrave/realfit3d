# RealFit3D

基於 Gaussian Garments 的三維虛擬試衣系統。

## 目前狀態

2026-10-15：Web／API、共用 CLI、試衣 worker、GG 渲染入口及離線階段命令已接入，GG／CC／ActorsHQ 固定版本。**網頁可獨立啟動；完整 GPU 試衣與訓練尚未完成端到端驗證，透明度 V3 核心仍待交付。**

| 已完成 | 尚未完成 |
|---|---|
| GG／CC／ActorsHQ submodule、版本檢查、Web／API、subprocess adapter | GPU 環境與資產配置、真實輸出 parity 驗證 |
| GG 精簡渲染／轉盤移入 fork；前端試衣 worker | 透明度核心與 checkpoint、遠端未交付 S2／S3 dirty diff |
| 離線階段 CLI、品質工具、資產檔案檢查 | 完整拓撲語意驗證、固定身形結果快取／鄰近身形加速 |

## 取得程式

```bash
git clone --recurse-submodules https://github.com/CasualBrave/realfit3d.git
cd realfit3d
python scripts/check_checkout.py
```

已 clone 的使用者可執行 `git submodule update --init --recursive` 取得主專案指定版本；這不會自動選擇 GG 的最新版。

檢查工具只依賴 Python 3.10+ 與 Git，不安裝 CUDA、不載入模型，也不啟動訓練。它確認的是程式來源與版本，**不是 GPU 執行準備完成**。

## 目錄與來源

```text
realfit3d/
  apps/api/server.py         # Flask API 與本機服務入口
  apps/web/templates/        # 網頁 HTML
  apps/web/static/           # JS、CSS、交接衣物縮圖
  src/realfit3d/adapters/     # GPU 環境檢查與 subprocess 命令
  src/realfit3d/pipelines/    # 離線各階段命令與先決條件
  src/realfit3d/quality/      # 搬入的本組 mask／相機／mesh 檢查工具
  src/realfit3d/cli.py        # doctor、offline、tryon、assets、quality
  src/realfit3d/workers/      # 暫時保留原結構的交接 worker
  configs/                   # 衣物／動作目錄與本機設定範例
  upstream/Gaussian-Garments/  # 獨立 Git repo：我們的 GG fork
  upstream/ContourCraft/       # 固定官方交接基線，不修改原始碼
  upstream/ActorsHQ-for-Gaussian-Garments/  # 含固定 GS2Mesh submodule
  upstream.lock.json          # 來源、固定 commit、官方比較基線
  scripts/check_checkout.py   # 唯讀來源／版本檢查
  tests/                     # checkout 與 CPU API 測試
  docs/                      # 來源、修改紀錄與開發流程
```

`workers/` 是過渡邊界，不是最終模組設計。先保持交接腳本的相鄰依賴與行為，再以 GPU parity 測試逐步拆成 body／assets／fitting／pipelines。`scripts/` 只放維護工具；GG 內部修改之後由 fork commit 管理，不重複維護同一份 patch。

## 啟動網站

在 repo 根目錄執行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m apps.api.server
```

開啟 http://127.0.0.1:5000 。不用 CUDA 即可瀏覽；未設定 GPU runtime 時，生成請求會回覆 503，不會偽造結果。`PORT=5001` 可更換埠號。

複製 `configs/paths.example.json` 為 `configs/paths.local.json` 並填入實際部署路徑，再設定 `REALFIT3D_CONFIG` 指向該檔案後啟動。此版本只支援單一程序、單一使用者的本機展示，無認證，不可直接公開到網路。

GPU 先決條件及驗證範圍見 [Web 整合說明](docs/WEB.md)。目前不提供脫離原始碼目錄的 wheel-only 網站部署。

## 共用 CLI

```bash
python -m realfit3d.cli --config configs/paths.local.json doctor
python -m realfit3d.cli --config configs/paths.local.json offline reconstruct --subject Actor08 --prompt "plaid shirt"
python -m realfit3d.cli --config configs/paths.local.json assets Actor05 --hash
```

`offline`、`tryon`、`quality` 預設只列出命令，不執行 GPU 工作；確認後才加 `--execute`。各階段先決條件、試衣命令和品質工具用法見 [整合狀態](docs/INTEGRATION_STATUS.md)。不要同時執行 Web 和 CLI GPU 任務，目前沒有跨程序排程。

## 上游與本組功能

- [Gaussian Garments 官方專案](https://github.com/eth-ait/Gaussian-Garments)：研究核心與原始程式。
- [本組 GG fork](https://github.com/CasualBrave/Gaussian-Garments)：維護確實需要修改 GG 內部的部分。
- 本主專案：後續維護 Web、資產、人體適配、任務、快取與流程整合。

GG fork 已加入交接渲染入口、環境變數路徑與 trajectory 檢查，詳見其 `REALFIT3D_CHANGES.md`。沒有把未交付的透明度或 S2／S3 修改冒充為已接入。Submodule 不會因主 repo 的 commit 而自動提交內部程式；細節見 [開發流程](docs/DEVELOPMENT.md)。

## 資料與權重

資料集、SMPL／SMPL-X 模型、checkpoint、重建結果、使用者輸入和本機設定都不納入程式 repo。後續將提供各自的取得方式與相容性驗證，不把「下載程式」當成「已取得全部模型與資料」。

不要在上游 `setup.sh` 尚未檢閱前直接執行。這次初始化沒有執行任何上游安裝腳本。

## 測試

```bash
python -m unittest discover -s tests -v
```

來源與基線見 [UPSTREAM.md](docs/UPSTREAM.md)；已移入／待移入的功能見 [MODIFICATIONS.md](docs/MODIFICATIONS.md)。本專案尚未選定自己的發布授權；不以本 README 改變上游程式、模型或資料的條款。
