# -*- coding: utf-8 -*-
"""
tests/integration/test_in_process_flow.py

一個單體迴路整合測試，用於在單一進程內驗證從 API 到工人的完整核心邏輯。
"""

import pytest
from fastapi.testclient import TestClient
import os

from src.prometheus.entrypoints.query_gateway import app, get_task_queue
from mock_worker import MockWorker
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue

# --- 常數設定 ---
APP_HOST = "127.0.0.1"
APP_PORT = 8009  # 使用一個不同的端口，以避免與 E2E 測試衝突
BASE_URL = f"http://{APP_HOST}:{APP_PORT}"


@pytest.fixture(scope="module")
def client():
    """
    提供一個 FastAPI 測試客戶端。
    """
    return TestClient(app)


@pytest.fixture(scope="module")
def task_queue():
    """
    一個在模組範圍內共享的 SQLiteQueue 實例。
    """
    db_path = "data/test_prometheus.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    return SQLiteQueue(db_path)


def test_in_process_api_to_worker_flow(client, task_queue):
    """
    【單體迴路整合測試】
    在單一進程內測試從 API 提交任務到工人完成任務的完整流程。
    """
    # 1. 提交一個任務
    strategy_payload = {
        "id": "test_strategy_123",
        "target_asset": "MOCK.US",
        "factors": ["MOMENTUM_1D"],
        "weights": {"MOMENTUM_1D": 1.0}
    }
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    response = client.post("/api/v1/task/backtest", json=strategy_payload)
    assert response.status_code == 200
    task_response = response.json()
    assert "task_id" in task_response
    task_id = task_response["task_id"]
    print(f"  - 成功提交任務，任務 ID: {task_id}")

    # 2. 在同一個進程內處理任務
    worker = MockWorker(db_path="data/test_prometheus.db")
    worker.queue = task_queue
    worker.process_single_task()

    # 3. 驗證任務結果
    result_response = client.get(f"/api/v1/task/result/{task_id}")
    assert result_response.status_code == 200
    result_data = result_response.json()
    assert result_data["status"] == "completed"
    assert "original_payload" in result_data["result"]
    assert result_data["result"]["original_payload"]["strategy"] == strategy_payload
    print("  - 任務已成功完成。")
