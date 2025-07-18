# -*- coding: utf-8 -*-
import os
import re
import subprocess
import sys
import time

from playwright.sync_api import expect, sync_playwright

SERVICE_URL = "http://127.0.0.1:8000/"
DB_FILE = "tasks.sqlite"
VERIFICATION_TIMEOUT = 20000

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

print("戰報：正在啟動所有後台服務...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"])
worker_process = subprocess.Popen(["poetry", "run", "python", "real_worker.py"])
time.sleep(5)

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」系統啟動，驗證『神之眼』監控系統...")
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SERVICE_URL)

        # 初始狀態下，歷史紀錄應為空
        print("戰報：驗證初始歷史紀錄為空...")
        history_body = page.locator("#task-history-body")
        expect(history_body).to_have_text("", timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 初始紀錄為空。")

        print("戰報：正在下達『執行深度分析』指令...")
        page.locator("#execute-task-btn").click()

        print("戰報：等待任務完成...")
        status_message = page.locator("#task-status-message")
        expect(status_message).to_have_text(
            re.compile(r"任務結果: 分析完成。市場壓力指數評估為: \d+"), timeout=VERIFICATION_TIMEOUT
        )
        print("戰報：任務已完成。")

        print("戰報：驗證歷史紀錄面板是否已更新...")
        # 等待 JS 刷新
        time.sleep(1)
        first_row = history_body.locator("tr:first-child")

        # 驗證新紀錄的關鍵欄位
        expect(first_row.locator("td").nth(1)).to_have_text("deep_analysis")
        expect(first_row.locator("td").nth(2)).to_have_text("completed")
        expect(first_row.locator("td").nth(3)).to_contain_text("分析完成")
        print("戰報：驗證通過 - 歷史紀錄已正確顯示！")

        browser.close()
        print("\n【作戰成功】：「神之眼」監控系統已通過全自動化整合驗證！")
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
