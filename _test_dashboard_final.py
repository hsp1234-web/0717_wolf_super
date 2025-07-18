# -*- coding: utf-8 -*-
import subprocess
import time
import requests
import sys

SERVICE_URL = "http://127.0.0.1:8000/"
STARTUP_TIMEOUT = 15

print("戰報：正在啟動儀表板服務...")
server_process = subprocess.Popen(["poetry", "run", "python", "run.py", "dashboard"])

try:
    print(f"戰報：等待服務啟動，最長 {STARTUP_TIMEOUT} 秒...")
    time.sleep(STARTUP_TIMEOUT) # 給予足夠的啟動時間

    print(f"戰報：正在向 {SERVICE_URL} 發送請求...")
    response = requests.get(SERVICE_URL, timeout=5)

    if response.status_code == 200 and "<h1>作戰指揮中心</h1>" in response.text:
        print("\n【作戰成功】：儀表板服務驗證通過！灘頭堡已成功建立！")
        sys.exit(0)
    else:
        print("\n【作戰失敗】：儀表板服務無響應或內容不正確。")
        print(f"    狀態碼: {response.status_code}")
        print(f"    回應內容片段: {response.text[:200]}...")
        sys.exit(1)
except requests.RequestException as e:
    print(f"\n【作戰失敗】：請求時發生嚴重錯誤: {e}")
    sys.exit(1)
finally:
    print("戰報：正在關閉服務...")
    server_process.terminate()
    server_process.wait()
    print("戰報：服務已關閉。")
