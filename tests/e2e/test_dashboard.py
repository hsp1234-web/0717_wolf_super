# tests/e2e/test_dashboard.py
import time
import requests

SERVICE_URL = "http://127.0.0.1:8000/"
STARTUP_TIMEOUT = 20  # 增加啟動超時以應對較慢的環境

def test_dashboard_loads_and_has_correct_title(live_services):
    """
    測試儀表板是否能成功加載並包含正確的標題。
    這個測試現在依賴於 conftest.py 中統一的 live_services fixture。
    """
    # Fixture `live_services` 會自動啟動服務
    # 加入一個短暫的等待，以確保即使在慢速 CI 環境中，服務也已完全準備好
    time.sleep(2)
    response = requests.get(SERVICE_URL, timeout=10)

    # 驗證狀態碼
    assert response.status_code == 200, f"預期狀態碼 200，但收到 {response.status_code}"

    # 驗證 HTML 內容
    expected_title = "普羅米修斯 - 作戰指揮中心"
    assert expected_title in response.text, f"HTML 中未找到預期的標題: '{expected_title}'"
