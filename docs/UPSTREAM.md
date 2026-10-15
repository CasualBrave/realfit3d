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

正式版本由主 repo 的 gitlink 固定；`upstream.lock.json` 記錄來源與比較基線，檢查工具會確認兩者一致。之後更新本組 fork 時，只更新採用的 `commit`；官方比較基線不能未經說明就跟著改。

本機曾下載的 `Gaussian-Garments-fork/`、`Gaussian-Garments-upstream/` 是此主專案外的獨立副本，不是本主專案的執行依賴。今後整合工作的 GG 修改在本專案 submodule 內的開發分支進行，避免兩份 fork 工作目錄交錯修改。

此版本上游 repo 根目錄未包含獨立 LICENSE 檔。保留原始歷史、README、引用與已有聲明；不要自行替上游套用本組授權。正式發布整合修改與資產前，需確認各來源的適用條款。

## 其他研究依賴

ContourCraft 與 ActorsHQ-for-Gaussian-Garments 尚未加入本主專案。將依已核對的執行版本分別固定，不能把最新遠端版本直接視為既有實驗版本。

交接 repo 是另一種來源證據，不是 GG 官方上游：

| 交接來源 | 本次規劃所依據的版本 | 用途 |
|---|---|---|
| `CasualBrave/frontend_temp` | `2a643b1b43a0329dce23b7c40fbc2757bcfab968` | Web、資產準備、人體擬合、fixed-size、預覽流程 |
| `CasualBrave/backend_temp` | `e5125ed3d0b4ad744f4581e83e6563f7b7152de7` | 訓練 wrappers、品質工具、fixed-size 與交接證據 |
| `CasualBrave/transparent_garments_temp` | `f706ff4b3667dd21efbdde75613a6a573a58b1ec` | 透明度／Actor 重建說明，核心 V3 實作未交付 |

這些內容尚未整包複製進主專案。移入功能時記錄來源檔案與 commit，並區分直接沿用、重構與行為變更。
