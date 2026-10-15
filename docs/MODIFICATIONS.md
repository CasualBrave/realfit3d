# 修改與遷移紀錄

## 2026-10-15：初始化

- 建立主專案來源與 submodule 連結。
- GG 固定至 `ceb66fc36598da05b3b3391f4562cdc54d2a2ed2`，未修改上游程式。
- 新增唯讀 checkout 檢查與 CPU 測試。
- 未建立新模型、未移入 Web、未重跑 GPU 推論或訓練。

## 待遷移範圍

### 第一階段 Web 整合

- 來源：`CasualBrave/frontend_temp`，commit `2a643b1b43a0329dce23b7c40fbc2757bcfab968`。
- `ContourCraft/preview_server.py` 的 HTML／CSS／JS 拆至 `apps/web/`；API 重組至 `apps/api/server.py`，GPU 命令集中至 `src/realfit3d/adapters/preview.py`。
- 同目錄其餘 13 個 Python worker 原樣搬至 `src/realfit3d/workers/contourcraft/`，不是新增演算法。衣物縮圖原樣沿用 `ContourCraft/catalog_thumbnails/`；預設 catalog 從 server 常數抽出。
- 改變行為：以設定檔指定 Python 與資料路徑；原子鎖保護單 GPU 操作；拒絕錯誤 motion index／衣物槽位；監測程序退出；讀取半寫入 status 時重試；限制結果下載為圖片／影片；不再自動清除舊試衣結果；fit 失敗保留原人體；補手機排版。
- 保留：人體先建立一次再選衣、下身先於上身、fixed-size／pin 參數、站姿轉盤與動畫順序。進度權重仍為交接估計，不是本次實測效能。
- GG submodule 未改動。GG 的 `inference.py` 差異及兩個渲染入口尚未遷入 fork；暫由設定指定已部署的交接 runtime。
- CPU 測試與瀏覽器檢查不等於 GPU 品質／速度驗證。離線 S1–S4、透明度與 backend_temp 第二套流程尚未合併。

| 功能 | 目標責任 | 驗收前的注意事項 |
|---|---|---|
| Web 與試衣流程 | RealFit3D 主專案 | 第一階段拆分完成，待實際 GPU 產物 parity 驗證 |
| 體型擬合、資產準備、fixed-size | 本組模組＋CC 適配 | 合併兩份 fixed-size 前比較 pin 等實際行為 |
| LBS／ICP 初始化 | 先保留獨立前處理 | 交付腳本在無合格 ICP 候選時的 fallback 與 PDF 描述不同，需對齊 |
| GG 精簡渲染／烘焙設定 | GG fork 或本組渲染入口 | 保留 baseline 與加速設定，不將低採樣當成同品質 |
| 透明度 | 可選 controller＋GG renderer 接入 | 核心程式、相容權重及多層合成行為待交付確認 |
| 固定選項快取 | RealFit3D 主專案 | 是待實作功能，不宣稱現在已具完整跨請求快取 |

後續每項修改記錄：來源 repo／檔案／commit、修改目的、是否改行為、測試與已知限制。不得只根據程式放在本組資料夾，就將沿用邏輯當作新演算法。
