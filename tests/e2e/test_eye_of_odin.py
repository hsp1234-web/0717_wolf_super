# -*- coding: utf-8 -*-
"""
【作戰計畫 192】：奧丁之眼 (Eye of Odin) - v13
全自動化端對端（E2E）測試框架
"""

import subprocess
import time
import pytest
import pandas as pd
from playwright.sync_api import sync_playwright, expect
from src.prometheus.core.db.data_warehouse import DataWarehouse

# --- 常數設定 ---
APP_HOST = "127.0.0.1"
APP_PORT = 8008
BASE_URL = f"http://{APP_HOST}:{APP_PORT}"
DASHBOARD_URL = f"{BASE_URL}/static/dashboard.html"


def setup_test_data():
    """準備回測所需的測試數據"""
    warehouse = DataWarehouse(db_path="data/warehouse.duckdb")
    warehouse.connection.execute("DROP TABLE IF EXISTS factors")

    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=100, freq="D"))
    data = {
        "date": dates,
        "symbol": "TEST.US",
        "MOMENTUM_1M": [i / 100 for i in range(100)],
        "VOLATILITY_20D": [i / 200 + 0.1 for i in range(100)],
        "open": [100 + i for i in range(100)],
        "high": [102 + i for i in range(100)],
        "low": [99 + i for i in range(100)],
        "close": [101 + i for i in range(100)],
        "volume": [10000 + i * 100 for i in range(100)],
    }
    df = pd.DataFrame(data)

    warehouse.save_table(df, "factors", if_exists="replace")
    print("✅ 測試數據已植入。")


@pytest.fixture(scope="module")
def full_system_up():
    """
    一個測試生命週期管理夾具 (fixture)，負責啟動和關閉後端服務。
    """
    setup_test_data()
    api_process = None
    worker_process = None
    try:
        print("\n🚀 開始啟動全系統服務...")
        api_process = subprocess.Popen(
            [
                "poetry", "run", "uvicorn",
                "src.prometheus.entrypoints.query_gateway:app",
                "--host", APP_HOST, "--port", str(APP_PORT)
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        worker_process = subprocess.Popen(
            ["poetry", "run", "python", "src/prometheus/entrypoints/real_worker_app.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(8)
        print("✅ 全系統服務（API 和工人）已啟動。")
        yield BASE_URL
    finally:
        print("\n🛑 開始關閉全系統服務...")
        if api_process:
            api_process.terminate()
            api_process.wait()
            print("  - API 服務已終止。")
        if worker_process:
            worker_process.terminate()
            worker_process.wait()
            print("  - 工人服務已終止。")
        print("✅ 所有背景服務已清理完畢。")


def test_odin_vision_full_backtest_flow(full_system_up):
    """
    奧丁之眼 - 全鏈路回測驗證
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        try:
            page.goto(DASHBOARD_URL, timeout=20000)
            expect(page).to_have_title("善狼研究平台 v8.0 (Live API)", timeout=15000)
            print("  - 已成功導航至儀表板並驗證標題。")

            lab_tab = page.locator('div[data-tab="lab"]')
            expect(lab_tab).to_be_visible(timeout=15000)
            lab_tab.click()
            print("  - 已成功切換到策略回測中心。")

            run_button = page.locator('button#run-backtest-button')
            expect(run_button).to_be_enabled(timeout=15000)
            run_button.click()
            print("  - 已點擊執行策略回測按鈕。")

            expect(run_button).to_have_text("回測執行中...", timeout=15000)
            print("  - 按鈕狀態已變為執行中。")

            annual_return_kpi = page.locator('#backtest-kpis div:has-text("年化報酬") p.text-lg')
            expect(annual_return_kpi).not_to_be_empty(timeout=60000)
            expect(annual_return_kpi).not_to_have_text("0.00%", timeout=10000)

            total_trades_kpi = page.locator('#backtest-kpis div:has-text("總交易數") p.text-lg')
            expect(total_trades_kpi).not_to_have_text("0", timeout=10000)

            print(f"  - 驗證成功！年化報酬: {annual_return_kpi.inner_text()}")
            print("👁️ 奧丁之眼已見證全鏈路的暢通。")
        finally:
            browser.close()
