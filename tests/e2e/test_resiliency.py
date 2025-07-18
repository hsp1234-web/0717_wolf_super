import os
import pytest
import pandas as pd
from unittest.mock import patch
from fastapi.testclient import TestClient

# 必須在導入 app 之前設定環境變數
TEST_DB = "data/test_resiliency.db"
TEST_WAREHOUSE = "data/test_resiliency.duckdb"
os.environ['DB_PATH'] = TEST_DB
os.environ['WAREHOUSE_PATH'] = TEST_WAREHOUSE

from src.prometheus.entrypoints.query_gateway import app
from src.prometheus.core.db.data_warehouse import DataWarehouse
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue

client = TestClient(app)

@pytest.fixture
def setup_dbs():
    # 確保目錄存在
    os.makedirs(os.path.dirname(TEST_DB), exist_ok=True)
    os.makedirs(os.path.dirname(TEST_WAREHOUSE), exist_ok=True)

    for db_file in [TEST_DB, TEST_WAREHOUSE, f"{TEST_WAREHOUSE}.wal"]:
        if os.path.exists(db_file): os.remove(db_file)

    # 關鍵：為測試資料庫建立必要的表
    SQLiteQueue(TEST_DB)._create_table()

    yield

    for db_file in [TEST_DB, TEST_WAREHOUSE, f"{TEST_WAREHOUSE}.wal"]:
        if os.path.exists(db_file): os.remove(db_file)

@pytest.mark.resiliency
def test_cache_hit_scenario(setup_dbs):
    """ 驗證場景 1: 快取命中 """
    # 準備: 在快取中植入兩個因子的新鮮數據
    warehouse = DataWarehouse(TEST_WAREHOUSE)
    vix_data = pd.DataFrame({'Adj Close': [100, 101]}, index=pd.to_datetime(['2025-07-17', '2025-07-18']))
    dgs10_data = pd.DataFrame({'DGS10': [1.5, 1.6]}, index=pd.to_datetime(['2025-07-17', '2025-07-18']))
    warehouse.save_data('^VIX', vix_data)
    warehouse.save_data('DGS10', dgs10_data)

    # 模擬: 外部 API 應該不會被呼叫
    # 我們 mock 整個工廠，確保沒有任何 client 被創建
    with patch('src.prometheus.core.analysis.data_engine.ClientFactory.get_client') as mock_get_client:
        response = client.get("/api/v1/market_snapshot")
        assert response.status_code == 200
        assert len(response.json()) == 2 # 確保兩個因子都從快取中讀取
        mock_get_client.assert_not_called() # 斷言：工廠從未被用來創建 client
        print("\n[驗收成功] 快取命中，系統未訪問外部 API。")

@pytest.mark.resiliency
def test_cache_miss_and_api_success_scenario(setup_dbs):
    """ 驗證場景 2: 快取失效，API 成功 """
    with patch('src.prometheus.core.clients.yfinance.YFinanceClient.fetch_data') as mock_yf_fetch, \
         patch('src.prometheus.core.clients.fred.FredClient.fetch_data') as mock_fred_fetch:

        # 準備: 模擬 API 回傳成功
        mock_yf_fetch.return_value = pd.DataFrame(
            {'Adj Close': [100, 102]},
            index=pd.to_datetime(['2025-07-17', '2025-07-18'])
        )
        mock_fred_fetch.return_value = pd.DataFrame(
            {'DGS10': [1.5, 1.6]},
            index=pd.to_datetime(['2025-07-17', '2025-07-18'])
        )

        response = client.get("/api/v1/market_snapshot")
        assert response.status_code == 200
        assert mock_yf_fetch.call_count > 0
        assert mock_fred_fetch.call_count > 0

        # 驗證: 新數據是否已寫入快取
        warehouse = DataWarehouse(TEST_WAREHOUSE)
        cached_vix = warehouse.get_data('^VIX')
        assert cached_vix is not None
        assert cached_vix['data_value'].iloc[-1] == 102

        cached_dgs10 = warehouse.get_data('DGS10')
        assert cached_dgs10 is not None
        assert cached_dgs10['data_value'].iloc[-1] == 1.6
        print("\n[驗收成功] 快取失效後，系統成功從 API 獲取數據並更新快取。")

@pytest.mark.resiliency
def test_api_fail_with_stale_cache_scenario(setup_dbs):
    """ 驗證場景 3: API 失敗，服務降級 """
    # 準備: 在快取中植入一份數據 (即使陳舊也沒關係)
    warehouse = DataWarehouse(TEST_WAREHOUSE)
    stale_data = pd.DataFrame(
        {'Adj Close': [90, 91]},
        index=pd.to_datetime(['2025-07-10', '2025-07-11'])
    )
    warehouse.save_data('^VIX', stale_data)

    with patch('src.prometheus.core.clients.yfinance.YFinanceClient.fetch_data') as mock_fetch:
        # 模擬: API 呼叫失敗
        mock_fetch.side_effect = Exception("Network Error")

        # 讓 fred client 成功以確保能返回部分結果
        with patch('src.prometheus.core.clients.fred.FredClient.fetch_data') as mock_fred_fetch:
            mock_fred_fetch.return_value = pd.DataFrame(
                {'DGS10': [1.5, 1.6]},
                index=pd.to_datetime(['2025-07-17', '2025-07-18'])
            )

            response = client.get("/api/v1/market_snapshot")
            assert response.status_code == 200
            response_data = response.json()

            vix_factor = next((item for item in response_data if item['name'] == 'VIX 恐慌指數'), None)
            assert vix_factor is not None
            # 斷言：系統回傳了陳舊數據，並附帶警告
            assert '(舊)' in vix_factor['value']
            print("\n[驗收成功] API 失敗後，系統成功降級服務並回傳陳舊快取。")
