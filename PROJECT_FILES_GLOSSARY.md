# 專案檔案詞彙表

本文件旨在提供專案中關鍵檔案與目錄的詳細用途說明，幫助開發者快速理解整個系統的架構與運作方式。

## 根目錄檔案

-   `pyproject.toml`: **專案定義檔**。使用 Poetry 管理專案的依賴套件、腳本、以及基本資訊 (如名稱、版本)。
-   `poetry.lock`: **依賴鎖定檔**。確保在任何環境中都安裝完全相同版本的套件，實現可重現的建置。
-   `config.yml`: **全局設定檔**。集中管理所有可變的設定，例如 API 金鑰、資料庫路徑、因子計算參數等。這使得調整系統行為無需修改程式碼。
-   `gunicorn.conf.py`: **Gunicorn 伺服器設定檔**。定義了生產環境下 API 伺服器 (`FastAPI`) 的運作方式，如工人數量、日誌格式、超時時間等。
-   `real_worker.py`: **實戰工人程序**。此腳本是「工人蜂群」的執行單元。可以啟動多個實例，每個實例都會從任務佇列中獲取並執行耗時的分析任務。
-   `start.sh` / `colab_start.sh`: **啟動腳本**。這些是方便開發者快速啟動整個服務的 shell 腳本。
-   `start_colab.py`: **Colab 啟動器**。專為 Google Colab 環境設計的 Python 啟動腳本，用於處理 Colab 的特殊環境設定。
-   `preflight-check.sh`: **飛行前檢查腳本**。在啟動服務前，執行此腳本可以驗證所有必要的設定與環境是否都已準備就緒。
-   `mypy.ini`, `pytest.ini`, `ruff.ini`: **程式碼品質工具設定檔**。分別用於設定 Mypy (靜態型別檢查)、Pytest (測試框架) 和 Ruff (程式碼風格檢查)。

## `src/` - 核心原始碼

`src/` 目錄是本專案所有 Python 原始碼的家。

### `src/prometheus/`

-   `cli/main.py`: **命令列介面 (CLI) 入口**。使用 `Typer` 建立，是使用者與系統互動的主要命令列入口。所有如 `services start` 等命令都在此定義。

### `src/prometheus/core/` - 核心引擎

`core/` 目錄包含了專案中最核心、最通用的模組。

-   `config.py`: **設定載入器**。負責讀取 `config.yml` 並將其內容轉換為 Python 物件，供應用程式其他部分使用。
-   `constants.py`: **路徑常數**。定義了專案中所有重要的檔案路徑，避免在程式碼中寫死路徑，提高可維護性。
-   `logging_config.py`: **日誌設定**。設定了全域的日誌系統，確保所有模組的日誌都有一致的格式，並能被正確地收集。
-   **`analysis/`**:
    -   `data_engine.py`: **數據引擎**。負責數據的獲取、快取與基礎處理，是所有分析的數據來源。
    -   `stress_index.py`: **壓力指數計算**。實作了用於衡量市場或特定資產風險的壓力指數模型。
-   **`clients/`**: **外部數據客戶端**。
    -   `base.py`: 定義了所有客戶端的基礎介面。
    -   `finmind.py`, `fmp.py`, `fred.py`, `nyfed.py`, `taifex_db.py`, `yfinance.py`: 分別對應不同金融數據 API 的客戶端實作。
-   **`db/`**: **資料庫相關模組**。
    -   `data_warehouse.py`: **數據倉庫**。使用 `duckdb` 實作，提供高效的數據儲存與查詢能力。
    -   `db_manager.py`: **資料庫管理器**。封裝了資料庫的連接與操作。
-   **`engines/`**: **因子計算引擎**。
    -   `bond_factor_engine.py`, `crypto_factor_engine.py`, `index_factor_engine.py`, `stock_factor_engine.py`: 針對不同資產類別的特徵因子計算邏輯。
-   **`pipelines/`**: **數據處理管線**。
    -   `pipeline.py`: **管線執行器**。可以將多個「步驟」串連起來，形成一個完整的數據處理流程。
    -   `steps/`: **管線步驟**。包含如 `loaders.py` (載入)、`savers.py` (儲存)、`aggregators.py` (聚合) 等可重用的處理單元。
-   **`queue/`**:
    -   `sqlite_queue.py`: **任務佇列**。使用 `aiosqlite` 實作的一個輕量、持久化的非同步任務佇列，是前端與背景工人之間溝通的橋樑。

### `src/prometheus/entrypoints/` - 服務入口

-   `query_gateway.py`: **FastAPI 查詢閘道**。定義了所有對外的 Web API 端點，是前端 Web 介面與後端服務溝通的唯一入口。

### `src/prometheus/services/` - 應用服務

-   `backtesting_service.py`: **回測服務**。提供了策略回測的核心邏輯。
-   `optimizer_service.py`: **最佳化服務**。使用遺傳演算法 (`deap`) 來尋找最佳的策略參數。
-   `strategy_reporter.py`: **策略報告器**。產生詳細的回測報告，包含各種績效指標與圖表。

### `src/prometheus/web/` - 前端檔案

-   `dashboard.html`: **前端指揮中心**。使用者與系統互動的主介面，使用 HTML, CSS 和 JavaScript 撰寫。

## `tests/` - 自動化測試

`tests/` 目錄存放了所有用於確保程式碼品質的自動化測試。

-   `conftest.py`: **Pytest 設定檔**。定義了測試中可共享的 `fixtures` (例如，一個初始化的資料庫連接)。
-   **`e2e/`**: **端對端 (End-to-End) 測試**。模擬真實使用者的操作，從前端介面一直測試到後端資料庫，確保整個系統的完整性。
-   **`integration/`**: **整合測試**。測試多個模組協同工作時的正確性。
-   **`unit/`**: **單元測試**。針對單一函式或類別進行的最小單位測試，確保每個小零件都正常運作。
