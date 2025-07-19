# -*- coding: utf-8 -*-
"""
tests/integration/test_api_to_worker_flow.py

一個快速整合測試，用於驗證從 API 到工人的核心通訊鏈路。
"""

import os
import subprocess
import time
import pytest
import requests

# --- 常數設定 ---
APP_HOST = "127.0.0.1"
APP_PORT = 8009  # 使用一個不同的端口，以避免與 E2E 測試衝突
BASE_URL = f"http://{APP_HOST}:{APP_PORT}"


@pytest.fixture(scope="module")
def mock_system_up():
    """
    一個測試生命週期管理夾具，負責啟動 API 服務和模擬工人。
    """
    api_process = None
    worker_process = None
    try:
        print("\n🚀 開始啟動模擬系統服務...")
        env = os.environ.copy()
        env["DB_PATH"] = "data/test_prometheus.db"
        print(f"Using DB_PATH: {env['DB_PATH']}")
        api_process = subprocess.Popen(
            [
                "poetry", "run", "uvicorn",
                "src.prometheus.entrypoints.query_gateway:app",
                "--host", APP_HOST, "--port", str(APP_PORT)
            ],
            env=env,
            stdout=open("api.log", "w"), stderr=subprocess.STDOUT
        )
        worker_process = subprocess.Popen(
            ["poetry", "run", "python", "mock_worker.py"],
            env=env,
            stdout=open("mock_worker.log", "w"), stderr=subprocess.STDOUT
        )
        time.sleep(10)  # 等待服務啟動
        print("✅ 模擬系統服務（API 和模擬工人）已啟動。")
        yield BASE_URL
    finally:
        print("\n🛑 開始關閉模擬系統服務...")
        if api_process:
            api_process.terminate()
            api_process.wait()
            print("  - API 服務已終止。")
        if worker_process:
            worker_process.terminate()
            worker_process.wait()
            print("  - 模擬工人服務已終止。")
        print("✅ 所有背景服務已清理完畢。")


def test_api_to_mock_worker_flow(mock_system_up):
    """
    測試從 API 提交任務到模擬工人完成任務的完整流程。
    """
    # 1. 提交一個任務
    strategy_payload = {
        "id": "test_strategy_123",
        "target_asset": "MOCK.US",
        "factors": ["MOMENTUM_1D"],
        "weights": {"MOMENTUM_1D": 1.0}
    }
    response = requests.post(f"{BASE_URL}/api/v1/task/backtest", json=strategy_payload)
    if response.status_code != 200:
        pytest.fail(f"API 請求失敗，狀態碼: {response.status_code}, 回應: {response.text}")
    task_response = response.json()
    assert "task_id" in task_response
    task_id = task_response["task_id"]
    print(f"  - 成功提交任務，任務 ID: {task_id}")

    # 2. 輪詢任務結果
    for _ in range(10):  # 最多等待 10 秒
        time.sleep(1)
        result_response = requests.get(f"{BASE_URL}/api/v1/task/result/{task_id}")
        assert result_response.status_code == 200
        result_data = result_response.json()
        if result_data["status"] == "completed":
            print("  - 任務已成功完成。")
            assert "original_payload" in result_data["result"]
            assert result_data["result"]["original_payload"]["strategy"] == strategy_payload
            return  # 測試成功

    pytest.fail("任務在超時時間內未完成。")
