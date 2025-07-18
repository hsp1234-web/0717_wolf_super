import time
import pytest
from fastapi.testclient import TestClient
import sys
import os
import uuid

# 將專案根目錄加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.prometheus.entrypoints.query_gateway import app, get_task_queue
from src.prometheus.models.snapshot_models import ShanJiaLangInitialData
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue

# --- 測試用的依賴覆寫 ---

# 為每個測試創建一個獨立的資料庫，以確保隔離性
TEST_DB_PATH = f"./data/test_{uuid.uuid4()}.db"

def get_test_task_queue():
    """提供一個指向獨立測試資料庫的佇列實例。"""
    # 確保目錄存在
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
    return SQLiteQueue(TEST_DB_PATH)

# 在應用層級覆寫依賴
app.dependency_overrides[get_task_queue] = get_test_task_queue

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_db():
    """在所有測試執行完畢後，清理測試資料庫檔案。"""
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_get_initial_data_e2e():
    """
    端對端測試：驗證 /api/v1/shan_jia_lang/initial_data 端點。
    """
    response = client.get("/api/v1/shan_jia_lang/initial_data")
    assert response.status_code == 200
    try:
        ShanJiaLangInitialData(**response.json())
    except Exception as e:
        assert False, f"回傳的數據不符合 ShanJiaLangInitialData 模型契約: {e}"
    print("\n[驗收成功] /api/v1/shan_jia_lang/initial_data 端點功能與數據契約皆正確。")


def run_worker_once(db_path):
    """
    一個輔助函數，僅執行一次工人任務獲取與處理。
    """
    from real_worker import process_initial_analysis

    queue = SQLiteQueue(db_path)
    task = queue.get()
    if task:
        task_id, task_type, payload = task
        print(f"[Worker] 接收到任務 {task_id}")
        if task_type == 'initial_analysis':
            result = process_initial_analysis(payload)
            queue.update_task(task_id, 'completed', result)
            print(f"[Worker] 任務 {task_id} 已完成")
        else:
            queue.update_task(task_id, 'failed', {"error": "unknown task type"})
            print(f"[Worker] 未知任務類型 {task_type}")


@pytest.mark.e2e
def test_ai_analysis_full_workflow():
    """
    端對端全流程測試：
    1. 提交一個 AI 分析任務。
    2. 獲得 task_id。
    3. 模擬工人執行任務。
    4. 輪詢結果 API 直到任務完成。
    5. 驗證最終結果是否正確。
    """
    # 1. 提交任務
    request_payload = {
        "raw_content": "VIX 指數飆升，市場恐慌。",
        "selected_masters": ["交易醫生"]
    }
    response = client.post("/api/v1/ai/initial_analysis", json=request_payload)
    assert response.status_code == 200, f"提交任務失敗: {response.text}"
    task_id = response.json().get("task_id")
    assert task_id is not None
    print(f"\n[進度] 任務已提交，Task ID: {task_id}")

    # 2. 模擬工人執行
    # 使用與被覆寫的依賴相同的 DB 路徑
    run_worker_once(TEST_DB_PATH)
    print("[進度] 模擬工人已執行任務。")

    # 3. 輪詢結果
    timeout = 10  # 秒
    start_time = time.time()
    final_result = None
    while time.time() - start_time < timeout:
        result_response = client.get(f"/api/v1/task/result/{task_id}")
        assert result_response.status_code == 200
        result_data = result_response.json()

        if result_data["status"] == "completed":
            print("[進度] 任務狀態已變為 completed。")
            final_result = result_data
            break

        print(f"[進度] 任務狀態: {result_data['status']}，等待中...")
        time.sleep(0.5)

    # 4. 驗證最終結果
    assert final_result is not None, "輪詢超時，未能在指定時間內獲得 completed 狀態"
    assert final_result["status"] == "completed"
    assert "result" in final_result and final_result["result"] is not None
    assert "summary" in final_result["result"]
    assert "長度為 14 字元" in final_result["result"]["summary"]
    assert "交易醫生" in final_result["result"]["summary"]

    print("[驗收成功] AI 分析任務的提交、執行、查詢全流程驗證通過。")
