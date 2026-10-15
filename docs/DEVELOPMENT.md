# 開發與提交流程

## 兩個 repo，不是兩次修改

在同一個 VS Code 視窗工作即可：主專案管理 Web／流程程式；`upstream/Gaussian-Garments` 管理 GG 內部修改。寫一次程式，但跨 repo 變更需要各自提交。

## 修改 RealFit3D 自己的程式

在主目錄建立分支、修改、測試，再針對本次檔案提交。這類修改不需要變更 GG commit。

## 修改 GG 內部

Submodule 由固定 commit 還原時通常處於 detached HEAD。先在子目錄建立具名分支，再修改；不要直接改完忘記把 commit 推送到 fork。

以下是流程示意，分支名稱與提交訊息需依實際工作選擇：

```bash
cd upstream/Gaussian-Garments
git switch -c realfit3d/feature-name
# 修改並測試後，只加入這次修改的檔案
git add <changed-files>
git commit -m "Describe the GG change"
git push -u origin realfit3d/feature-name
git rev-parse HEAD
cd ../..
```

再把 `upstream.lock.json` 的 `commit` 更新成新的完整 SHA，保留原始 `upstream_baseline`。主目錄執行：

```bash
git add upstream/Gaussian-Garments upstream.lock.json
python scripts/check_checkout.py
# 補上修改說明與測試，再提交主專案的版本引用
git commit -m "Pin GG to the tested RealFit3D revision"
```

先讓 GG commit 能從 fork 取得，再發布主專案引用。正式採用時應依團隊 PR／review 流程決定是否先合併 fork 分支。不要對同一份 fork 修改再重複套一套 patch。

## 更新與檢查

其他人取得新版主 repo 後，用 `git submodule update --init --recursive` 還原指定版本；不要把 `--remote` 當成一般安裝步驟，因為它可能選到不同於主專案固定的版本。

`python scripts/check_checkout.py` 比對：來源設定、gitlink、實際 HEAD、工作樹是否乾淨。檢查 dirty 時會回報失敗以提醒尚未固定的修改，不會刪除或還原任何檔案。

主 repo 的 `.gitignore` 不會管理 submodule 內部資料。GG 的輸出、模型與本機設定也要避免提交；推送前分別檢查主 repo 與子 repo 的 staged diff。不要使用 `git add .` 盲目加入實驗產物。
