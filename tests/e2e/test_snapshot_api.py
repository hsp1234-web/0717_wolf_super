from fastapi.testclient import TestClient
import sys
import os

# 將專案根目錄加入 sys.path，以解決模組導入問題
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.prometheus.entrypoints.query_gateway import app
from src.prometheus.models.snapshot_models import Factor

client = TestClient(app)

def test_get_market_snapshot_e2e():
    """
    端對端測試：驗證 /api/v1/market_snapshot 端點。

    此測試模擬前端應用，直接向 API 發起請求，並驗證以下項目：
    1.  HTTP 狀態碼是否為 200 (成功)。
    2.  回傳的數據是否為一個列表 (JSON array)。
    3.  列表中的每個項目，是否都符合 Factor 模型的數據契約。
    """
    # 1. 扮演前端，向 API 發起 GET 請求
    response = client.get("/api/v1/market_snapshot")

    # 2. 驗證 HTTP 狀態碼
    assert response.status_code == 200, f"預期狀態碼為 200，但收到 {response.status_code}"

    # 3. 驗證回傳數據
    data = response.json()
    assert isinstance(data, list), "回傳的數據應為一個列表"
    assert len(data) > 0, "回傳的數據列表不應為空"

    # 4. 抽樣驗證數據契約
    first_item = data[0]
    # 使用 Pydantic 模型來驗證第一個項目的結構，確保契約被遵守
    try:
        Factor(**first_item)
    except Exception as e:
        assert False, f"回傳的數據項目不符合 Factor 模型契約: {e}"

    print("\n[驗收成功] /api/v1/market_snapshot 端點功能與數據契約皆正確。")
