import os
import shutil
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# 核心變更：直接導入 PrometheusService
from src.prometheus.core.clients.client_factory import BaseClient, ClientFactory
from src.prometheus.core.config import config
from src.prometheus.core.db.data_warehouse import DataWarehouse
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.core.services import PrometheusService
# 核心變更：從 query_gateway 導入新的依賴注入函數
from src.prometheus.entrypoints.query_gateway import app, get_prometheus_service


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """在整個測試會話期間，強制使用測試配置和環境變數。"""
    os.environ["PROMETHEUS_ENV"] = "test"
    os.environ["DB_PATH"] = config.TEST_DB_PATH
    os.environ["WAREHOUSE_PATH"] = config.TEST_WAREHOUSE_PATH
    os.makedirs(os.path.dirname(config.TEST_DB_PATH), exist_ok=True)
    yield
    test_data_dir = os.path.dirname(config.TEST_DB_PATH)
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)


@pytest.fixture
def clean_dbs(setup_test_environment):
    """在每個測試前，確保資料庫檔案是全新的。"""
    db_files = [config.TEST_DB_PATH, config.TEST_WAREHOUSE_PATH, f"{config.TEST_WAREHOUSE_PATH}.wal"]
    for db_file in db_files:
        if os.path.exists(db_file):
            os.remove(db_file)
    # 重新創建目錄以確保路徑存在
    os.makedirs(os.path.dirname(config.TEST_DB_PATH), exist_ok=True)
    yield


@pytest.fixture
def mock_client_factory() -> ClientFactory:
    """提供一個注入了 MagicMock 客戶端的 ClientFactory。"""
    mock_factory = MagicMock(spec=ClientFactory)
    mock_factory.get_client.return_value = MagicMock(spec=BaseClient)
    return mock_factory


@pytest.fixture
def prometheus_service_fixture(clean_dbs, mock_client_factory: ClientFactory) -> PrometheusService:
    """
    【新的核心 Fixture】
    提供一個帶有模擬依賴項的 PrometheusService 實例。
    這是單元測試和集成測試業務邏輯的基礎。
    """
    service = PrometheusService(
        queue=SQLiteQueue(config.TEST_DB_PATH),
        warehouse=DataWarehouse(config.TEST_WAREHOUSE_PATH),
        client_factory=mock_client_factory,
    )
    return service


@pytest.fixture
def test_app_client(prometheus_service_fixture: PrometheusService) -> TestClient:
    """
    【重構後的核心 Fixture】
    提供一個用於端對端測試的 FastAPI TestClient。
    它通過覆蓋 get_prometheus_service 依賴，注入了我們帶有 mock 的 service fixture。
    """

    # 定義一個返回我們已創建的、帶有 mock 的服務實例的函數
    def get_test_prometheus_service():
        return prometheus_service_fixture

    # 應用依賴覆蓋
    app.dependency_overrides[get_prometheus_service] = get_test_prometheus_service

    with TestClient(app) as client:
        yield client

    # 測試結束後，清除覆蓋，恢復 app 原始狀態
    app.dependency_overrides.clear()
