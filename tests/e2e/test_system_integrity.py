# -*- coding: utf-8 -*-
"""
【作戰計畫 188.1 驗收測試】
單一核心系統完整性端對端測試 (Single Core System Integrity E2E Test)

這個測試檔案是新架構的最終驗收標準。它驗證了從 API 入口到異步工
人執行的整個請求生命週期，確保在「單一核心」重構後，系統的所有關
鍵部分都能正確協同工作。
"""

import time
from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.prometheus.core.services import PrometheusService
from src.prometheus.entrypoints.real_worker_app import RealWorkerApp


def test_system_integrity_full_flow(
    test_app_client: TestClient, prometheus_service_fixture: PrometheusService
):
    """
    測試從 API 提交任務到工人執行完畢的全鏈路流程。

    這個測試模擬了以下步驟：
    1.  一個外部客戶端請求市場快照。
    2.  該客戶端提交一個需要異步處理的分析任務。
    3.  一個作戰工人 (RealWorkerApp) 實例被啟動。
    4.  工人從隊列中拾取任務並委託給核心服務 (PrometheusService) 執行。
    5.  核心服務執行業務邏輯並返回結果。
    6.  工人更新資料庫中的任務狀態。
    7.  客戶端輪詢任務結果，並最終獲取成功的響應。
    """
    # --- 步驟 1: 客戶端請求市場快照 ---
    # 設置模擬數據
    mock_yfinance_client = MagicMock()
    mock_yfinance_client.fetch_data.return_value = pd.DataFrame({
        "Adj Close": [15.0, 16.0],
        "Date": pd.to_datetime(["2024-01-01", "2024-01-02"])
    }).set_index("Date")

    prometheus_service_fixture.client_factory.get_client.return_value = mock_yfinance_client

    # 觸發 API
    response = test_app_client.get("/api/v1/market_snapshot")
    assert response.status_code == 200
    data = response.json()
    # 驗證來自模擬數據的結果
    assert any(item["name"] == "VIX 恐慌指數" and item["value"] == "16.00" for item in data)
    print("✅ 步驟 1/5: 市場快照 API 成功返回數據。")

    # --- 步驟 2: 客戶端提交一個壓力指數分析任務 ---
    response = test_app_client.post("/api/v1/task/stress_index_analysis")
    assert response.status_code == 200
    task_submission = response.json()
    assert task_submission["message"] == "壓力指數分析任務已成功提交"
    task_id = task_submission["task_id"]
    print(f"✅ 步驟 2/5: 異步任務 '{task_id}' 已成功提交。")

    # --- 步驟 3 & 4: 啟動工人並執行任務 ---
    # 創建一個 worker 實例，它會使用與測試客戶端相同的測試資料庫
    # 因為 `setup_test_environment` fixture 設置了環境變數
    worker = RealWorkerApp()

    # 模擬工人的一次主循環迭代
    task_info = worker.queue.get()  # 從隊列中獲取任務
    assert task_info is not None
    assert task_info[0] == task_id  # 驗證任務 ID

    # 直接調用 dispatch 方法來模擬任務執行
    # 在測試環境中，PrometheusService 會使用 Mock Client
    status, result = worker._dispatch_task(task_info[0], task_info[1])
    worker.queue.update_task(task_info[0], status, {"message": result})
    print("✅ 步驟 3&4/5: 工人已拾取並執行了任務。")

    # --- 步驟 5: 客戶端輪詢並獲取最終結果 ---
    max_retries = 5
    for i in range(max_retries):
        response = test_app_client.get(f"/api/v1/task/result/{task_id}")
        assert response.status_code == 200
        result_data = response.json()
        if result_data["status"] == "completed":
            assert result_data["task_id"] == task_id
            assert "分析完成。指數為: 73.17" in result_data["result"]["message"]
            print("✅ 步驟 5/5: 任務結果已成功獲取並驗證。")
            return  # 測試成功
        time.sleep(0.2)  # 等待一會再重試

    pytest.fail("在最大重試次數後，仍未獲取到 'completed' 的任務狀態。")
