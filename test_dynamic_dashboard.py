# -*- coding: utf-8 -*-
import subprocess
import time
import sys
from playwright.sync_api import sync_playwright, Page, expect

# --- 作戰參數 ---
SERVICE_URL = "http://127.0.0.1:8000/"
STARTUP_WAIT_TIME = 5  # 啟動後等待時間
VERIFICATION_TIMEOUT = 10000 # 頁面元素驗證的超時時間 (毫秒)

print("戰報：正在啟動儀表板服務...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"])
print(f"戰報：服務程序 PID: {server_process.pid}")
time.sleep(STARTUP_WAIT_TIME)

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」測試系統啟動...")
        browser = p.chromium.launch()
        page = browser.new_page()

        print(f"戰報：正在導航至 {SERVICE_URL}...")
        page.goto(SERVICE_URL)

        print("戰報：正在驗證『系統壓力指數』是否已動態更新...")
        stress_index_locator = page.locator("#stress-index")
        expect(stress_index_locator).to_have_text("88", timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 『系統壓力指數』為 88。")

        print("戰報：正在驗證『現役策略數量』是否已動態更新...")
        active_strategies_locator = page.locator("#active-strategies")
        expect(active_strategies_locator).to_have_text("5", timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 『現役策略數量』為 5。")

        browser.close()
        print("\n【作戰成功】：動態儀表板所有自動化驗證均已通過！")
        sys.exit(0)

except Exception as e:
    print(f"\n【作戰失敗】：自動化驗證過程中發生嚴重錯誤。")
    print(f"錯誤詳情: {e}")
    sys.exit(1)

finally:
    print("戰報：正在關閉後台服務...")
    server_process.terminate()
    server_process.wait()
    print("戰報：服務已關閉，戰場清理完畢。")
