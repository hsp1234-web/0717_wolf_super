# tests/e2e/test_multi_task.py
from playwright.sync_api import sync_playwright, expect

SERVICE_URL = "http://127.0.0.1:8000/"
VERIFICATION_TIMEOUT = 25000 # 兩個任務，需要更長的超時

def test_hydra_multi_task_execution(live_services):
    """
    驗證系統可以接收並成功執行多個不同的任務。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SERVICE_URL)

        status_message = page.locator("#task-status-message")
        stress_btn = page.locator("#stress-index-btn")
        correlation_btn = page.locator("#correlation-btn")

        # --- 測試任務一：壓力指數 ---
        print("Hydra Test: 正在下達『壓力指數』指令...")
        stress_btn.click()
        expected_result_1 = '任務結果: {"message": "分析完成。指數為: 73.17"}'
        expect(status_message).to_have_text(expected_result_1, timeout=VERIFICATION_TIMEOUT)
        print("Hydra Test: 壓力指數任務成功。")

        # 等待 UI 按鈕恢復可用
        expect(stress_btn).to_be_enabled(timeout=5000)
        expect(correlation_btn).to_be_enabled(timeout=5000)

        # --- 測試任務二：相關性分析 ---
        print("Hydra Test: 正在下達『因子相關性』指令...")
        correlation_btn.click()
        expected_result_2 = '任務結果: {"message": "分析完成。VIX 與 SKEW 的滾動相關性為: -0.54"}'
        expect(status_message).to_have_text(expected_result_2, timeout=VERIFICATION_TIMEOUT)
        print("Hydra Test: 因子相關性任務成功。")

        browser.close()
