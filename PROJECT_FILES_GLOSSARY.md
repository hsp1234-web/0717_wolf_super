# 專案檔案詞彙表

本文件旨在提供專案中關鍵檔案與目錄的用途說明。

## 核心目錄

- `src/prometheus/`: 專案所有核心 Python 原始碼的根目錄。
- `src/prometheus/core/`: 存放專案最核心的、可重用的模組。
- `src.prometheus/entrypoints/`: 專案的服務入口點，例如 API 伺服器。
- `src/prometheus/web/`: 存放 Web 前端相關檔案 (HTML, JS, CSS)。
- `tests/`: 存放所有自動化測試檔案。

## 關鍵檔案說明

### 根目錄
- `run.py`: **新的系統總啟動器**。用於啟動生產級服務。
- `gunicorn.conf.py`: **Gunicorn 配置文件**。定義了 API 伺服器集群的工人數量、日誌等生產級參數。
- `real_worker.py`: **實戰工人程序**。可並行啟動多個，負責從任務佇列中領取並執行真正的分析任務。
- `mock_worker.py`: **模擬工人程序**。在「作戰演習模式」下，取代 `real_worker.py`，使用模擬數據進行快速測試。
- `config.yml`: **全局設定檔**。包含了 API 金鑰、資料庫路徑以及因子定義。
- `poetry.lock`: **Poetry 鎖定檔案**。
- `pyproject.toml`: **Poetry 專案設定檔**。
- `pytest.ini`: **Pytest 設定檔**。
- `mypy.ini`: **Mypy 設定檔**。
- `test_sentinel_robustness.py`: **「哨兵」測試腳本**。我們最先進的整合測試腳本，用於驗證系統的穩定性與正確性。
- `test_dashboard_final.py`, `test_dynamic_dashboard.py`, `test_fast_integration.py`, `test_history_system.py`, `test_hive_system.py`, `test_hydra_system.py`, `test_interactive_dashboard.py`, `test_monitoring_system.py`, `test_probe_enhanced.py`, `test_real_system.py`, `test_swarm_throughput.py`: **整合測試腳本**。

### `src/prometheus/`
- `cli/main.py`: **命令列介面**。`Typer` 應用的主要實作。
- `core/constants.py`: **「羅盤」**。使用 `pathlib` 定義所有共享資源的絕對路徑，是確保系統穩定的基石。
- `core/logging_config.py`: **「瞭望塔」**。配置全域統一日誌系統，將所有程序的日誌匯總至單一檔案。
- `core/analysis/data_engine.py`: **真實數據引擎**。
- `core/analysis/mock_data_engine.py`: **模擬數據引擎**。在「作戰演習模式」下取代真實數據引擎，用於快速測試。
- `core/queue/sqlite_queue.py`: **任務佇列**。基於 `sqlite3` 的同步任務佇列。
- `entrypoints/query_gateway.py`: **FastAPI 應用**。定義了所有 Web API 端點，是前端與後端溝通的橋樑。
- `entrypoints/olympus_api.py`: **「普羅米修斯之腦」API 核心**。提供非同步 AI 訓練任務的 FastAPI 服務。
- `web/dashboard.html`: **前端指揮中心**。使用者與系統互動的主介面。

### `tests/`
- `test_api_contract.py`: **「API 聖約」功能契約**。用以驗證 `olympus_api.py` 是否遵守其 API 承諾的整合測試。
- `conftest.py`: **測試設定**。`Pytest` 的本地插件檔案，用於定義所有測試共享的 `fixtures`。
- `fixtures/`: **測試數據**。存放所有測試案例所需的靜態數據檔案。
- `integration/`: **整合測試**。
- `unit/`: **單元測試**。
- `ignition_test.py`: **點火測試**。
- `test_p0_downloader.py`: **下載器測試**。
