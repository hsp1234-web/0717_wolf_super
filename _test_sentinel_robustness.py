# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import time

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from prometheus.core.constants import DB_PATH, LOG_PATH

SERVICE_URL = "http://127.0.0.1:8000/"
VERIFICATION_TIMEOUT = 15000

# --- 戰場準備 ---
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
if os.path.exists(LOG_PATH):
    os.remove(LOG_PATH)

test_env = os.environ.copy()
test_env["PROMETHEUS_ENV"] = "test"

server_process, worker_process = None, None
try:
    print("哨兵報告：正在『作戰演習模式』下啟動所有服務...")
    server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"], env=test_env)
    worker_process = subprocess.Popen(["poetry", "run", "python", "real_worker.py"], env=test_env)

    print("哨兵報告：等待 5 秒，讓服務穩定...")
    time.sleep(5)

    # --- 健康檢查：確認工人和伺服器都還活著 ---
    if server_process.poll() is not None:
        raise RuntimeError("嚴重錯誤：API 伺服器未能啟動！")
    if worker_process.poll() is not None:
        raise RuntimeError("嚴重錯誤：工人程序未能啟動！")
    print("哨兵報告：所有作戰單位均已成功啟動。")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SERVICE_URL)

        button = page.locator("#execute-task-btn")
        status_message = page.locator("#task-status-message")

        print("哨兵報告：正在下達指令...")
        button.click()

        print("哨兵報告：等待並驗證最終結果，最長等待時間 15 秒...")
        expected_result = "任務結果: 分析完成。指數為: 73.17"
        expect(status_message).to_have_text(expected_result, timeout=VERIFICATION_TIMEOUT)

        browser.close()
        print("\n【作戰勝利】：系統在高可用性架構下已通過全自動化診斷測試！")

except Exception as e:
    print(f"\n【作戰失敗】：哨兵測試過程中發生嚴重錯誤: {e}")
    # --- 關鍵：在失敗時，打印瞭望塔的完整報告 ---
    if os.path.exists(LOG_PATH):
        print("\n--- 瞭望塔最終戰報 ---")
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            print(f.read())
        print("--- 戰報結束 ---")
    sys.exit(1)

finally:
    print("哨兵報告：正在發送關閉信號 (毒丸)...")
    if server_process:
        server_process.terminate()
    if worker_process:
        worker_process.terminate()
    if server_process:
        server_process.wait(timeout=5)
    if worker_process:
        worker_process.wait(timeout=5)
    print("哨兵報告：所有服務已關閉，戰場清理完畢。")
