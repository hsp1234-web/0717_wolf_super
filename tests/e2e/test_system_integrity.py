# -*- coding: utf-8 -*-
"""
【作戰計畫 190.1 驗收測試】: 利刃出鞘 (Unsheathing the Blade)
系統完整性 E2E 測試 - Backtrader 整合

此測試驗證 `backtrader` 引擎是否已成功整合到 `PrometheusService` 的回測流程中。
"""

import time
import uuid
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.prometheus.core.db.db_manager import DBManager
from src.prometheus.entrypoints.real_worker_app import RealWorkerApp
from src.prometheus.models.strategy_models import Strategy


@pytest.fixture(scope="function")
def setup_backtest_data(db_manager: DBManager):
    """準備一次回測所需的基本數據：因子數據和價格數據"""
    db_manager.initialize_db()
    # 創建一個模擬的因子和價格數據表
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=100, freq="D"))
    data = {
        "date": dates,
        "symbol": "TEST.US",
        "MOMENTUM_1M": [i / 100 for i in range(100)],  # 一個簡單的動量因子
        "VOLATILITY_20D": [i / 200 + 0.1 for i in range(100)],  # 一個波動率因子
        "open": [100 + i for i in range(100)],
        "high": [102 + i for i in range(100)],
        "low": [99 + i for i in range(100)],
        "close": [101 + i for i in range(100)],
        "volume": [10000 + i * 100 for i in range(100)],
    }
    df = pd.DataFrame(data)
    # 將數據存入 'factors' 表
    db_manager.save_table(df, "factors", if_exists="replace")
    print("✅ 測試數據已植入。")


def test_backtrader_integration_full_flow(test_app_client: TestClient, setup_backtest_data, db_manager: DBManager):
    """
    測試從 API 提交回測任務到工人執行完畢，並返回真實 backtrader 指標的全流程。
    """
    # --- 步驟 1: 定義一個回測策略並提交任務 ---
    strategy_to_test = Strategy(
        id=str(uuid.uuid4()),
        target_asset="TEST.US",
        factors=["MOMENTUM_1M", "VOLATILITY_20D"],
        weights={"MOMENTUM_1M": 0.7, "VOLATILITY_20D": -0.3},  # 追逐動量，規避波動
    )
    response = test_app_client.post("/api/v1/task/backtest", json=strategy_to_test.model_dump())
    assert response.status_code == 200
    task_submission = response.json()
    task_id = task_submission["task_id"]
    print(f"✅ 步驟 1/4: 回測任務 '{task_id}' 已成功提交。")

    # --- 步驟 2: 啟動工人並執行回測任務 ---
    worker = RealWorkerApp()
    task_info = worker.queue.get()
    assert task_info is not None
    assert task_info[0] == task_id

    status, result = worker._dispatch_task(task_info[0], task_info[1])
    worker.queue.update_task(task_info[0], status, result)
    print("✅ 步驟 2/4: 工人已拾取並執行回測。")

    # --- 步驟 3: 輪詢並獲取最終結果 ---
    max_retries = 5
    result_data = {}
    for i in range(max_retries):
        response = test_app_client.get(f"/api/v1/task/result/{task_id}")
        assert response.status_code == 200
        result_data = response.json()
        if result_data["status"] == "completed":
            print("✅ 步驟 3/4: 任務結果已成功獲取。")
            break
        time.sleep(0.2)
    assert result_data.get("status") == "completed", "任務未在預期時間內完成"

    # --- 步驟 4: 驗證回測結果是否包含真實的 backtrader 績效 ---
    performance_report = result_data["result"]
    print(f"收到的績效報告: {performance_report}")
    # 驗證返回的績效指標是否為有效的浮點數，且不為預設的 0.0
    # 這證明了 backtrader 分析器確實運行並產生了輸出
    assert isinstance(performance_report["sharpe_ratio"], float)
    assert performance_report["sharpe_ratio"] != 0.0, "夏普比率不應為 0"
    assert isinstance(performance_report["annualized_return"], float)
    assert performance_report["annualized_return"] != 0.0, "年化回報不應為 0"
    assert isinstance(performance_report["max_drawdown"], float)
    # 最大回撤可以是 0，但我們驗證它存在
    assert isinstance(performance_report["total_trades"], int)
    assert performance_report["total_trades"] > 0, "回測應產生至少一筆交易"
    print("✅ 步驟 4/4: Backtrader 績效指標已成功驗證！利刃已出鞘！")
