# -*- coding: utf-8 -*-
import subprocess
import time
import sys
import os
import re
from playwright.sync_api import sync_playwright, expect

SERVICE_URL = "http://127.0.0.1:8000/"
DB_FILE = "tasks.sqlite"
VERIFICATION_TIMEOUT = 15000

if os.path.exists(DB_FILE): os.remove(DB_FILE)

print("戰報：正在啟動所有後台服務...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"])
# 在這個測試中，我們不需要工人程序，以隔離驗證監控功能
time.sleep(5)

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」系統啟動，驗證『神經中樞』監控系統...")
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SERVICE_URL)

        cpu_text = page.locator("#cpu-text")
        mem_text = page.locator("#mem-text")

        print("戰報：驗證初始監控數據...")
        # 初始值可能為 0.0%，等待第一次 API 回傳
        expect(cpu_text).not_to_have_text("0.0%", timeout=VERIFICATION_TIMEOUT)
        expect(mem_text).not_to_have_text("0.0%", timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 監控數據已成功從 0.0% 更新。")

        print("戰報：正在捕獲監控數據格式...")
        # 使用正則表達式驗證數據格式是否正確
        cpu_regex = r"\d+\.\d+%"
        mem_regex = r"\d+\.\d+%"
        expect(cpu_text).to_have_text(re.compile(cpu_regex))
        expect(mem_text).to_have_text(re.compile(mem_regex))
        print("戰報：驗證通過 - CPU 與記憶體數據格式正確！")

        browser.close()
        print("\n【作戰成功】：「神經中-樞」即時監控系統已通過全自動化整合驗證！")
        sys.exit(0)

except Exception as e:
    print(f"\n【作戰失敗】：自動化驗證過程中發生嚴重錯誤: {e}")
    sys.exit(1)

finally:
    print("戰報：正在關閉後台服務...")
    server_process.terminate()
    server_process.wait()
    print("戰報：服務已關閉，戰場清理完畢。")
