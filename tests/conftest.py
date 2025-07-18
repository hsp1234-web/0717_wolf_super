import os
import shutil
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.prometheus.core.analysis.data_engine import DataEngine
from src.prometheus.core.clients.client_factory import BaseClient, ClientFactory
from src.prometheus.core.config import config
from src.prometheus.core.db.data_warehouse import DataWarehouse
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue

# 導入依賴注入所需的核心組件
from src.prometheus.entrypoints.query_gateway import app, get_data_engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """在整個測試會話期間，強制使用測試配置。"""
    os.environ["DB_PATH"] = config.TEST_DB_PATH
    os.environ["WAREHOUSE_PATH"] = config.TEST_WAREHOUSE_PATH
    os.makedirs(os.path.dirname(config.TEST_DB_PATH), exist_ok=True)
    yield
    test_data_dir = os.path.dirname(config.TEST_DB_PATH)
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)


@pytest.fixture
def clean_dbs(setup_test_environment):
    """在每個測試前，確保資料庫是乾淨的。"""
    db_files = [config.TEST_DB_PATH, config.TEST_WAREHOUSE_PATH]
    for db_file in db_files:
        if os.path.exists(db_file):
            os.remove(db_file)
    yield


@pytest.fixture
def mock_clients():
    """提供一組可供控制的 Mock 客戶端。"""
    return {
        "yfinance": MagicMock(spec=BaseClient),
        "fred": MagicMock(spec=BaseClient),
    }


@pytest.fixture
def test_app_client(clean_dbs, mock_clients):
    """
    【核心修正】測試應用程式工廠。
    為每個測試創建一個帶有 mock 依賴的、完全隔離的 app 實例。
    """

    def get_test_data_engine():
        class MockClientFactory(ClientFactory):
            def get_client(self, source_name: str) -> BaseClient:
                return mock_clients[source_name]

        return DataEngine(
            queue=SQLiteQueue(config.TEST_DB_PATH),
            warehouse=DataWarehouse(config.TEST_WAREHOUSE_PATH),
            client_factory=MockClientFactory(),
        )

    # 應用依賴覆蓋
    app.dependency_overrides[get_data_engine] = get_test_data_engine

    with TestClient(app) as client:
        yield client

    # 測試結束後，清除覆蓋，恢復 app 原始狀態
    app.dependency_overrides.clear()
