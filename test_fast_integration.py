# -*- coding: utf-8 -*-
import subprocess
import time
import sys
import os
from playwright.sync_api import sync_playwright, expect

SERVICE_URL = "http://127.0.0.1:8000/"
DB_FILE = "tasks.sqlite"
VERIFICATION_TIMEOUT = 10000 # 10 秒的超時，對於快速測試已綽綽有餘

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# --- 關鍵：設定作戰演習模式 ---
test_env = os.environ.copy()
test_env['PROMETHEUS_ENV'] = 'test'

print("戰報：正在『作戰演習模式』下啟動所有服務...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"], env=test_env)
worker_process = subprocess.Popen(["poetry", "run", "python", "real_worker.py"], env=test_env)
time.sleep(3) # 快速啟動

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」系統啟動，進行『閃電戰』快速整合驗證...")
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SERVICE_URL)

        button = page.locator("#execute-task-btn")
        status_message = page.locator("#task-status-message")

        print("戰報：正在下達『計算市場壓力指數』指令...")
        button.click()

        print("戰報：等待並驗證來自『模擬數據』的最終計算結果...")
        # 根據我們的模擬數據，預期結果應該是固定的
        # StressIndex 計算邏輯為 (vix.mean() + skew.mean()) / 2
        # ( (20.5+21.0+22.5)/3 + (120.0+125.0+130.0)/3 ) / 2 = (21.333 + 125) / 2 = 73.166
        expected_result = "任務結果: 分析完成。指數為: 73.17"
        expect(status_message).to_have_text(expected_result, timeout=VERIFICATION_TIMEOUT)
        print(f"戰報：驗證通過 - 成功接收到預期的模擬計算結果！")

        browser.close()
        print("\n【作戰成功】：核心智能的快速整合流程已跑通！開發效率已大幅提升！")
        sys.exit(0)

except Exception as e:
    print(f"\n【作戰失敗】：快速整合驗證過程中發生嚴重錯誤: {e}")
    sys.exit(1)

finally:
    print("戰報：正在關閉所有後台服務...")
    server_process.terminate()
    worker_process.terminate()
    server_process.wait()
    worker_process.wait()
    print("戰報：所有服務已關閉，戰場清理完畢。")
