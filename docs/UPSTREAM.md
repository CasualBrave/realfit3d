# 上游來源與固定基線

## Gaussian Garments

| 項目 | 值 |
|---|---|
| 原始 repo | https://github.com/eth-ait/Gaussian-Garments.git |
| 本組 fork | https://github.com/CasualBrave/Gaussian-Garments.git |
| 本機 submodule | `upstream/Gaussian-Garments` |
| 初始官方基線 | `ceb66fc36598da05b3b3391f4562cdc54d2a2ed2` |
| 初始 fork 版本 | 同上 |
| 初始內部修改 | 無 |
| 目前 fork 版本 | 見 upstream.lock.json；已加入渲染入口、環境路徑與 trajectory 檢查 |

正式版本由主 repo 的 gitlink 固定；`upstream.lock.json` 記錄來源與比較基線，檢查工具確認兩者一致。更新 fork 時同步更新採用的 `commit`；升級官方比較基線時，在修改紀錄記下新舊版本與遷移內容。

本機曾下載的 `Gaussian-Garments-fork/`、`Gaussian-Garments-upstream/` 是此主專案外的獨立副本，不是本主專案的執行依賴。今後整合工作的 GG 修改在本專案 submodule 內的開發分支進行，避免兩份 fork 工作目錄交錯修改。

此版本上游 repo 根目錄未包含獨立 LICENSE 檔。我們保留原始歷史、README、引用與已有聲明；整合程式與資產的發布授權仍在確認中。

## 其他研究依賴

ContourCraft 已固定至 `d606432c2f7e96b05664e6a4ffb9d1cb98705baf`；ActorsHQ-for-Gaussian-Garments 已固定至 `46651f55030407ea25463ed070eed9f7e837a9af`，其 GS2Mesh gitlink 為 `b08a68f2b896301472d25fe3f5287b5b1bf1b737`。遠端訓練目錄的未提交修改另列於待比對項目。

小組整合程式來源：

| 交接來源 | 本次規劃所依據的版本 | 用途 |
|---|---|---|
| `CasualBrave/frontend_temp` | `2a643b1b43a0329dce23b7c40fbc2757bcfab968` | Web、資產準備、人體擬合、fixed-size、預覽流程 |
| `CasualBrave/backend_temp` | `e5125ed3d0b4ad744f4581e83e6563f7b7152de7` | 訓練 wrappers、品質工具、fixed-size 與交接證據 |
| `CasualBrave/transparent_garments_temp` | `f706ff4b3667dd21efbdde75613a6a573a58b1ec` | 透明度／Actor 重建說明與 actor scripts |

已移入的範圍為 Web、試衣 worker、渲染入口與品質工具；來源檔案雜湊見
[source_manifest.json](source_manifest.json)，修改紀錄見 [MODIFICATIONS.md](MODIFICATIONS.md)。
V3 程式與 Actor02 權重來自另一份遠端交付，路徑與雜湊見
[REMOTE_DISCOVERY_20261020.md](REMOTE_DISCOVERY_20261020.md)。
