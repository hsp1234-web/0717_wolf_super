# -*- coding: utf-8 -*-
import subprocess
import time
import sys
from playwright.sync_api import sync_playwright, expect

SERVICE_URL = "http://127.0.0.1:8000/"
STARTUP_WAIT_TIME = 5
VERIFICATION_TIMEOUT = 10000

print("戰報：正在啟動儀表板服務...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"])
time.sleep(STARTUP_WAIT_TIME)

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」系統啟動，開始驗證互動功能...")
        browser = p.chromium.launch()
        page = browser.new_page()

        print(f"戰報：正在導航至 {SERVICE_URL}...")
        page.goto(SERVICE_URL)

        # 定位關鍵元素
        button = page.locator("#execute-task-btn")
        status_message = page.locator("#task-status-message")

        print("戰報：驗證初始狀態...")
        expect(button).to_be_enabled()
        expect(status_message).to_have_text("請下達指令")
        print("戰報：初始狀態驗證通過。")

        print("戰報：正在點擊『執行深度分析』按鈕...")
        button.click()

        print("戰報：驗證點擊後的中間狀態...")
        expect(button).to_be_disabled()
        expect(status_message).to_have_text("指令已發送，等待後端確認...")
        print("戰報：中間狀態驗證通過。")

        print("戰報：等待並驗證最終的成功反饋...")
        expected_message = "後端確認：任務已成功觸發並執行完畢。"
        expect(status_message).to_have_text(expected_message, timeout=VERIFICATION_TIMEOUT)
        print(f"戰報：最終狀態驗證通過 - 成功接收到訊息: '{expected_message}'")

        browser.close()
        print("\n【作戰成功】：「信使」互動循環已通過全自動化驗證！")
        sys.exit(0)

except Exception as e:
    print("\n【作戰失敗】：自動化驗證過程中發生嚴重錯誤。")
    print(f"錯誤詳情: {e}")
    sys.exit(1)

finally:
    print("戰報：正在關閉後台服務...")
    server_process.terminate()
    server_process.wait()
    print("戰報：服務已關閉，戰場清理完畢。")
