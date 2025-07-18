# -*- coding: utf-8 -*-
import subprocess
import time
import sys
import os
import re
from playwright.sync_api import sync_playwright, expect

SERVICE_URL = "http://127.0.0.1:8000/"
DB_FILE = os.path.abspath("tasks.sqlite")
VERIFICATION_TIMEOUT = 20000

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

env = os.environ.copy()
env["DB_PATH"] = DB_FILE

print("戰報：正在啟動後端 API 伺服器...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"], env=env)

print("戰報：正在啟動『實戰工人』程序...")
worker_process = subprocess.Popen(["poetry", "run", "python", "real_worker.py"], env=env)

time.sleep(5)

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」系統啟動，驗證『實戰工人』整合...")
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SERVICE_URL)

        button = page.locator("#execute-task-btn")
        status_message = page.locator("#task-status-message")

        print("戰報：正在下達『執行深度分析』指令...")
        button.click()

        print("戰報：驗證任務追蹤狀態...")
        expect(status_message).to_contain_text("任務已提交", timeout=VERIFICATION_TIMEOUT)
        expect(status_message).to_contain_text("任務狀態: running", timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 已成功追蹤到 running 狀態。")

        print("戰報：等待並驗證最終的分析結果...")
        # 使用正則表達式來匹配成功的結果，因為數字是隨機的
        expect(status_message).to_have_text(re.compile(r"任務結果: 分析完成。市場壓力指數評估為: \d+"), timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 成功接收到真實的分析結果！")

        browser.close()
        print("\n【作戰成功】：「實戰工人」已成功整合至「蜂巢」系統並通過全自動化驗證！")
        sys.exit(0)

except Exception as e:
    print(f"\n【作戰失敗】：自動化驗證過程中發生嚴重錯誤: {e}")
    sys.exit(1)

finally:
    print("戰報：正在關閉所有後台服務...")
    server_process.terminate()
    worker_process.terminate()
    server_process.wait()
    worker_process.wait()
    print("戰報：所有服務已關閉，戰場清理完畢。")
