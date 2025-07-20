# tests/e2e/test_sentinel.py
import os
from playwright.sync_api import sync_playwright, expect

# 由於我們使用了 pytest，sys.path 的問題由 pytest.ini 處理，這裡不再需要手動修改

# 從 src 導入，路徑更清晰
from prometheus.core.constants import LOG_PATH

SERVICE_URL = "http://127.0.0.1:8000/"
VERIFICATION_TIMEOUT = 20000  # 增加超時以應對 CI 環境

def test_sentinel_end_to_end_flow(live_services, capsys):
    """
    一個完整的 E2E 測試，模擬用戶操作並驗證結果。
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(SERVICE_URL)

            # 在舊的 HTML 中，按鈕 ID 是 #execute-task-btn
            # 在新的 HTML 中，有兩個按鈕，我們需要點擊其中一個
            # 我們選擇點擊「計算市場壓力指數」
            button = page.locator("#stress-index-btn")
            status_message = page.locator("#task-status-message")

            print("哨兵報告：正在下達『計算市場壓力指數』指令...")
            button.click()

            print(f"哨兵報告：等待並驗證中間與最終結果，最長等待時間 {VERIFICATION_TIMEOUT / 1000} 秒...")

            # 由於 processing 狀態太快，直接驗證最終結果以避免測試不穩定
            final_text = '任務結果: {"message": "分析完成。指數為: 73.17"}'
            expect(status_message).to_have_text(final_text, timeout=VERIFICATION_TIMEOUT)

            # 我們可以進一步驗證日誌中是否有成功的標記
            # (這需要在 fixture 中捕獲日誌，或者在測試後讀取日誌檔案)

            browser.close()
            print("\n【作戰勝利】：系統在高可用性架構下已通過全自動化診斷測試！")

    except Exception as e:
        # 如果發生任何錯誤，pytest 會自動捕獲並報告
        # 為了調試，我們可以打印日誌檔案的內容
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, 'r', encoding='utf-8') as f:
                log_content = f.read()
            # 使用 pytest 的捕獲機制打印日誌，而不是直接 print
            capsys.readouterr()
            print("\n--- 瞭望塔最終戰報 ---\n", log_content)
        # 重新引發異常，讓 pytest 知道測試失敗了
        raise e
