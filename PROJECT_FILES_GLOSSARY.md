# 專案檔案詞彙表

本文件提供專案中所有重要檔案與目錄的用途說明。

## 根目錄

| 檔案/目錄 | 用途 |
| :--- | :--- |
| `README.md` | **專案的「活的儀表板」**，提供系統能力清單與執行命令。 |
| `commander_console.py` | **後台任務的「萬能鑰匙」**，所有離線作戰能力的唯一入口。 |
| `config.yml` | 專案的主要設定檔，包含資料庫路徑、API 金鑰等。 |
| `gunicorn.conf.py` | Gunicorn 伺服器的設定檔，用於設定工人數量、綁定端口等。 |
| `mypy.ini` | MyPy 靜態型別檢查工具的設定檔。 |
| `poetry.lock` | Poetry 相依性管理工具的鎖定檔，確保在不同環境中使用完全相同的套件版本。 |
| `preflight-check.sh` | **作戰資格預檢驗腳本**，執行全面的靜態分析、依賴檢查與測試。 |
| `pyproject.toml` | Poetry 的專案設定檔，定義專案元數據、相依性與工具鏈設定。 |
| `pytest.ini` | Pytest 測試框架的設定檔。 |
| `rapid-check.sh` | **快速整合檢查腳本**，執行一組快速的靜態分析與核心整合測試。 |
| `real_worker.py` | **真實的背景工人**，負責執行由 API 伺服器分派的非同步任務。 |
| `run.py` | **核心服務啟動器**，使用 Gunicorn 啟動 API 伺服器與背景工人蜂群。 |
| `src/` | **專案原始碼**，所有核心邏輯的所在地。 |
| `tests/` | **自動化測試套件**，包含所有單元、整合與 E2E 測試。 |

## `src/` 目錄

| 檔案/目錄 | 用途 |
| :--- | :--- |
| `src/prometheus/` | 專案的主要命名空間。 |
| `src/prometheus/cli/` | 命令列介面相關的程式碼。 |
| `src/prometheus/core/` | 專案的核心元件，包含設定、資料庫、引擎等。 |
| `src/prometheus/entrypoints/` | 專案的各個進入點，例如 API 伺服器、背景工人應用等。 |
| `src/prometheus/models/` | 資料模型定義。 |
| `src/prometheus/pipelines/` | 資料處理管線的定義。 |
| `src/prometheus/services/` | 專案的服務層，封裝了特定的業務邏輯。 |
| `src/prometheus/web/` | Web 前端相關的檔案。 |

## `tests/` 目錄

| 檔案/目錄 | 用途 |
| :--- | :--- |
| `tests/conftest.py` | Pytest 的設定檔，提供測試固件 (fixtures)。 |
| `tests/e2e/` | 端對端 (End-to-End) 測試。 |
| `tests/fixtures/` | 測試所使用的假資料或檔案。 |
| `tests/ignition_test.py` | **架構點火測試**，確保所有核心模組都可以被成功匯入。 |
| `tests/integration/` | 整合測試。 |
| `tests/test_capabilities.py` | **功能契約測試**，驗證 `README.md` 中定義的所有能力。 |
| `tests/unit/` | 單元測試。 |
