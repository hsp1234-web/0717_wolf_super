# -*- coding: utf-8 -*-
import subprocess
import time
import sys
import os
from playwright.sync_api import sync_playwright, expect

# --- 作戰參數 ---
SERVICE_URL = "http://127.0.0.1:8000/"
DB_FILE = os.path.abspath("tasks.sqlite")
VERIFICATION_TIMEOUT = 20000 # 毫秒

# --- 戰場準備：清理舊的資料庫 ---
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print("戰報：已清理舊的任務資料庫。")

# --- 設定環境變數 ---
env = os.environ.copy()
env["DB_PATH"] = DB_FILE

# --- 啟動所有作戰單位 ---
print("戰報：正在啟動後端 API 伺服器...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"], env=env)

print("戰報：正在啟動後台工人程序...")
worker_process = subprocess.Popen(["poetry", "run", "python", "mock_worker.py"], env=env)

# 給予所有單位足夠的啟動時間
time.sleep(5)

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」系統啟動，開始驗證『蜂巢』系統...")
        browser = p.chromium.launch()
        page = browser.new_page()

        print(f"戰報：正在導航至 {SERVICE_URL}...")
        page.goto(SERVICE_URL)

        # 定位元素
        button = page.locator("#execute-task-btn")
        status_message = page.locator("#task-status-message")

        print("戰報：正在下達『執行深度分析』指令...")
        button.click()

        print("戰報：驗證任務提交後的追蹤狀態...")
        expect(status_message).to_contain_text("任務已提交", timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 任務提交訊息已顯示。")

        print("戰報：等待並驗證工人程序更新的『執行中』狀態...")
        expect(status_message).to_contain_text("任務狀態: running", timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 『執行中』狀態已顯示。")

        print("戰報：等待並驗證最終的『完成』狀態與結果...")
        expected_result = "任務完成: 分析完成，一切指標正常。"
        expect(status_message).to_have_text(expected_result, timeout=VERIFICATION_TIMEOUT)
        print(f"戰報：驗證通過 - 成功接收到最終結果: '{expected_result}'")

        browser.close()
        print("\n【作戰成功】：「蜂巢」非同步任務系統已通過全自動化整合驗證！")
        sys.exit(0)

except Exception as e:
    print("\n【作戰失敗】：自動化驗證過程中發生嚴重錯誤。")
    print(f"錯誤詳情: {e}")
    sys.exit(1)

finally:
    # --- 戰場清理 ---
    print("戰報：正在關閉所有後台服務...")
    server_process.terminate()
    worker_process.terminate()
    server_process.wait()
    worker_process.wait()
    print("戰報：所有服務已關閉，戰場清理完畢。")
