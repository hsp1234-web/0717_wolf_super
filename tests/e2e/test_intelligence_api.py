from fastapi.testclient import TestClient
import sys
import os

# 將專案根目錄加入 sys.path，以解決模組導入問題
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.prometheus.entrypoints.query_gateway import app
from src.prometheus.models.snapshot_models import ShanJiaLangInitialData, MasterInsight

client = TestClient(app)

def test_get_initial_data_e2e():
    """
    端對端測試：驗證 /api/v1/shan_jia_lang/initial_data 端點。

    此測試模擬前端應用，驗證以下項目：
    1.  HTTP 狀態碼為 200。
    2.  回傳的數據結構符合 ShanJiaLangInitialData 模型契約。
    3.  數據內容的類型正確（例如，week_list 是一個列表）。
    """
    # 1. 扮演前端，向 API 發起 GET 請求
    response = client.get("/api/v1/shan_jia_lang/initial_data")

    # 2. 驗證 HTTP 狀態碼
    assert response.status_code == 200, f"預期狀態碼為 200，但收到 {response.status_code}"

    # 3. 驗證回傳的數據結構與契約
    try:
        data = ShanJiaLangInitialData(**response.json())
    except Exception as e:
        assert False, f"回傳的數據不符合 ShanJiaLangInitialData 模型契約: {e}"

    # 4. 深入驗證數據內容
    assert isinstance(data.week_list, list)
    assert len(data.week_list) > 0
    assert data.default_week in data.week_list
    assert isinstance(data.raw_content, str)
    assert len(data.raw_content) > 0
    assert isinstance(data.master_insights, list)
    assert len(data.master_insights) > 0
    assert isinstance(data.master_insights[0], MasterInsight)

    print("\n[驗收成功] /api/v1/shan_jia_lang/initial_data 端點功能與數據契約皆正確。")
