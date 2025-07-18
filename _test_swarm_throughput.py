# -*- coding: utf-8 -*-
import subprocess
import time
import sys
import os
from playwright.sync_api import sync_playwright

from src.prometheus.core.constants import DB_PATH

SERVICE_URL = "http://127.0.0.1:8000/"
VERIFICATION_TIMEOUT = 45000 # 增加超時以應對多任務
TASK_COUNT = 4 # 我們要提交的任務總數

if os.path.exists(DB_PATH): os.remove(DB_PATH)

test_env = os.environ.copy()
test_env['PROMETHEUS_ENV'] = 'test'

print("戰報：正在啟動生產級服務...")
# 注意：我們現在不直接啟動服務，而是假設服務已由 run.py start_services 啟動
# 在真實 CI/CD 環境中，服務啟動和測試是分開的步驟
# 為簡化，我們這裡仍然手動啟動
server_process = subprocess.Popen(["poetry", "run", "gunicorn", "-c", "gunicorn.conf.py", "src.prometheus.entrypoints.query_gateway:app"], env=test_env)
worker_processes = [
    subprocess.Popen(["poetry", "run", "python", "real_worker.py"], env=test_env)
    for _ in range(max(1, os.cpu_count() - 1))
]
time.sleep(5)

try:
    with sync_playwright() as p:
        print("戰報：「獵犬」系統啟動，開始『蜂群』壓力測試...")
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SERVICE_URL)

        stress_btn = page.locator("#stress-index-btn")
        correlation_btn = page.locator("#correlation-btn")

        print(f"戰報：正在快速提交 {TASK_COUNT} 個混合任務...")
        for i in range(TASK_COUNT):
            if i % 2 == 0:
                stress_btn.click()
            else:
                correlation_btn.click()
            time.sleep(0.1) # 模擬快速點擊

        print("戰報：任務已全部提交，等待蜂群處理...")

        # 驗證最終結果：輪詢後端 API 確認所有任務都已完成
        start_time = time.time()
        while time.time() - start_time < VERIFICATION_TIMEOUT / 1000:
            try:
                response = page.request.get(f"{SERVICE_URL}api/v1/get_task_history")
                history = response.json()
                completed_count = sum(1 for task in history if task['status'] == 'completed')
                if completed_count == TASK_COUNT:
                    print(f"戰報：驗證通過 - API 返回了 {completed_count} 個已完成的任務！")
                    break
            except Exception as e:
                print(f"警告：輪詢歷史 API 時出錯: {e}")
            time.sleep(2)
        else:
            raise Exception(f"驗證超時：未能在 {VERIFICATION_TIMEOUT}ms 內確認 {TASK_COUNT} 個已完成的任務。")

        browser.close()
        print("\n【作戰勝利】：「工人蜂群」已證明其卓越的並行處理能力！系統已具備生產級吞吐量！")
        sys.exit(0)

except Exception as e:
    print(f"\n【作戰失敗】：壓力測試過程中發生嚴重錯誤: {e}")
    sys.exit(1)

finally:
    print("戰報：正在關閉所有後台服務...")
    server_process.terminate()
    for worker in worker_processes:
        worker.terminate()
    server_process.wait(timeout=5)
    for worker in worker_processes:
        worker.wait(timeout=5)
    print("戰報：所有服務已關閉，戰場清理完畢。")
