import pandas as pd
import pytest

from src.prometheus.core.config import config
from src.prometheus.core.db.data_warehouse import DataWarehouse


@pytest.mark.resiliency
def test_mixed_success_and_fail_scenario(test_app_client, mock_clients):
    """
    【最終驗證】使用注入了 mock 客戶端的、隔離的 app 實例進行測試。
    """
    # 準備: 在快取中植入陳舊數據
    warehouse = DataWarehouse(config.TEST_WAREHOUSE_PATH)
    stale_vix_data = pd.DataFrame(
        {"Adj Close": [90, 91]}, index=[pd.to_datetime("2025-07-10"), pd.to_datetime("2025-07-11")]
    )
    warehouse.save_data("^VIX", stale_vix_data)

    # 設定 Mock 行為
    mock_clients["yfinance"].fetch_data.side_effect = Exception("Network Error")
    fred_success_data = pd.DataFrame(
        {"DGS10": [4.1, 4.2]}, index=[pd.to_datetime("2025-07-17"), pd.to_datetime("2025-07-18")]
    )
    mock_clients["fred"].fetch_data.return_value = fred_success_data

    # 執行 API 呼叫
    response = test_app_client.get("/api/v1/market_snapshot")
    assert response.status_code == 200
    response_data = response.json()

    # 斷言
    vix_factor = next((item for item in response_data if item["name"] == "VIX 恐慌指數"), None)
    assert vix_factor is not None and "(舊)" in vix_factor["value"]

    dgs10_factor = next((item for item in response_data if item["name"] == "美國十年債利率"), None)
    assert dgs10_factor is not None and "(舊)" not in dgs10_factor["value"]

    mock_clients["yfinance"].fetch_data.assert_called_once()
    mock_clients["fred"].fetch_data.assert_called_once()

    print("\n[驗收成功] 鳳凰重生：韌性測試在隔離環境下穩定通過。")
