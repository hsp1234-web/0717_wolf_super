# -*- coding: utf-8 -*-
import subprocess
import time
import sys
import os
from playwright.sync_api import sync_playwright, expect

from src.prometheus.core.constants import DB_PATH

SERVICE_URL = "http://127.0.0.1:8000/"
VERIFICATION_TIMEOUT = 15000

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

test_env = os.environ.copy()
test_env['PROMETHEUS_ENV'] = 'test'

print("戰報：正在『作戰演習模式』下啟動所有服務...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"], env=test_env)
worker_process = subprocess.Popen(["poetry", "run", "python", "real_worker.py"], env=test_env)
time.sleep(3)

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」系統啟動，驗證『九頭蛇』多任務能力...")
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SERVICE_URL)

        status_message = page.locator("#task-status-message")

        # --- 測試任務一：壓力指數 ---
        print("戰報：正在下達『壓力指數』指令...")
        page.locator("#stress-index-btn").click()
        expected_result_1 = "任務結果: 分析完成。指數為: 73.17"
        expect(status_message).to_have_text(expected_result_1, timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 壓力指數任務成功。")

        # 等待 UI 恢復
        time.sleep(3)

        # --- 測試任務二：相關性分析 ---
        print("戰報：正在下達『因子相關性』指令...")
        page.locator("#correlation-btn").click()
        import re
        expected_regex_2 = re.compile(r"任務結果: 分析完成。VIX 與 SKEW 的滾動相關性為: -?0\.\d+")
        expect(status_message).to_have_text(expected_regex_2, timeout=VERIFICATION_TIMEOUT)
        print("戰報：驗證通過 - 因子相關性任務成功。")

        browser.close()
        print("\n【作戰勝利】：「九頭蛇」多任務系統已通過全自動化驗證！架構擴展性得到證明！")
        sys.exit(0)

except Exception as e:
    print(f"\n【作戰失敗】：自動化驗證過程中發生嚴重錯誤: {e}")
    sys.exit(1)

finally:
    print("戰報：正在關閉所有後台服務...")
    server_process.terminate()
    worker_process.terminate()
    server_process.wait(timeout=5)
    worker_process.wait(timeout=5)
    print("戰報：所有服務已關閉，戰場清理完畢。")
