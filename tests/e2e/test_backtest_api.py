import os
import time
import pytest
from fastapi.testclient import TestClient
import sys
import uuid

# 將專案根目錄加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.prometheus.entrypoints.query_gateway import app, get_task_queue
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.models.snapshot_models import BacktestResult

# --- 測試用的依賴覆寫 ---

# 為每個測試模組創建一個獨立的資料庫
TEST_DB_PATH = f"./data/test_backtest_{uuid.uuid4()}.db"

def get_test_task_queue():
    """提供一個指向獨立測試資料庫的佇列實例。"""
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
    return SQLiteQueue(TEST_DB_PATH)

app.dependency_overrides[get_task_queue] = get_test_task_queue

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_db():
    """在所有測試執行完畢後，清理測試資料庫檔案。"""
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def run_worker_once(db_path):
    """ 一個輔助函數，僅執行一次工人任務獲取與處理 """
    from real_worker import process_backtest

    queue = SQLiteQueue(db_path)
    task = queue.get()
    if task:
        task_id, task_type, payload = task
        if task_type == 'backtest':
            result = process_backtest(payload)
            queue.update_task(task_id, 'completed', result)
        else:
            print(f"測試工人忽略了非回測任務: {task_type}")


@pytest.mark.e2e
def test_backtest_full_workflow():
    """
    端對端全流程測試：策略回測
    1. 提交一個回測任務。
    2. 獲得 task_id。
    3. 模擬工人執行回測。
    4. 輪詢結果 API 直到任務完成。
    5. 驗證績效報告的數據契約。
    """
    # 1. 提交任務
    strategy_code = "def handle_data(context, data): order_target_percent(context.asset, 1)"
    request_payload = {
        "strategy_code": strategy_code,
        "strategy_name": "黃金交叉策略"
    }
    response = client.post("/api/v1/backtest/run", json=request_payload)
    assert response.status_code == 200, f"提交任務失敗: {response.text}"
    task_id = response.json().get("task_id")
    assert task_id is not None
    print(f"\n[進度] 回測任務已提交，Task ID: {task_id}")

    # 2. 模擬工人執行
    run_worker_once(TEST_DB_PATH)
    print("[進度] 模擬工人已執行回測任務。")

    # 3. 輪詢結果
    timeout = 10
    start_time = time.time()
    final_result = None
    while time.time() - start_time < timeout:
        result_response = client.get(f"/api/v1/task/result/{task_id}")
        assert result_response.status_code == 200
        result_data = result_response.json()

        if result_data["status"] == "completed":
            print("[進度] 回測任務狀態已變為 completed。")
            final_result = result_data
            break

        print(f"[進度] 任務狀態: {result_data['status']}，等待中...")
        time.sleep(0.5)

    # 4. 驗證最終結果
    assert final_result is not None, "輪詢超時，未能獲得 completed 狀態"
    assert final_result["status"] == "completed"

    # 驗證績效報告的數據契約
    try:
        BacktestResult(**final_result["result"])
    except Exception as e:
        assert False, f"回傳的績效報告不符合 BacktestResult 模型契約: {e}"

    assert final_result["result"]["strategy_name"] == "黃金交叉策略"
    assert len(final_result["result"]["equity_curve"]) > 0

    print("[驗收成功] 策略回測任務的提交、執行、查詢全流程驗證通過。")
