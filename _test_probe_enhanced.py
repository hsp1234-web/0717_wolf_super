# -*- coding: utf-8 -*-
import subprocess
import sys
import time

import requests

# --- 作戰參數 ---
SERVICE_URL = "http://127.0.0.1:8000/"
STARTUP_TIMEOUT = 15  # 伺服器啟動的最長等待時間（秒）
REQUEST_TIMEOUT = 5  # API 請求的超時時間（秒）

# 啟動後台服務，並將日誌輸出到檔案
print("戰報：正在啟動後台服務...")
server_log_file = open("server_probe.log", "w")
server_process = subprocess.Popen(
    ["poetry", "run", "python", "run.py", "dashboard"], stdout=server_log_file, stderr=subprocess.STDOUT
)

try:
    # --- 智慧等待與連接測試 ---
    print(f"戰報：進入智慧等待階段，最長 {STARTUP_TIMEOUT} 秒...")
    is_server_ready = False
    for i in range(STARTUP_TIMEOUT):
        try:
            # 嘗試連接，設置較短的連接超時
            response = requests.get(SERVICE_URL, timeout=REQUEST_TIMEOUT)
            if response.status_code == 404:
                print(f"戰報：伺服器在第 {i+1} 秒響應！連接成功。")
                is_server_ready = True
                break
        except requests.ConnectionError:
            time.sleep(1)  # 連接失敗，等待1秒後重試
        except requests.RequestException as e:
            print(f"警告：在等待期間發生非預期的請求錯誤: {e}")
            time.sleep(1)

    if not is_server_ready:
        print("\n【作戰失敗】：伺服器在指定時間內未能啟動或響應。")
        sys.exit(1)

    # --- 健康檢查驗證 ---
    print("戰報：正在驗證 / 端點的回應...")
    response = requests.get(SERVICE_URL, timeout=REQUEST_TIMEOUT)

    # Since the report files don't exist, we expect a 404 Not Found.
    # This is sufficient to confirm the server is running.
    if response.status_code == 404:
        print("\n【作戰成功】：伺服器已成功啟動並按預期回應 404！")
        sys.exit(0)
    else:
        print("\n【作戰失敗】：/ 端點回應不符合預期。")
        print(f"    預期狀態碼: 404, 實際: {response.status_code}")
        print(f"    實際內容: {response.text}")
        sys.exit(1)

except requests.RequestException as e:
    print(f"\n【作戰失敗】：在主驗證流程中發生請求錯誤: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n【作戰失敗】：發生未知的嚴重錯誤: {e}")
    sys.exit(1)
finally:
    # --- 確保戰場清理 ---
    print("戰報：正在關閉後台服務...")
    server_process.terminate()
    server_process.wait()
    server_log_file.close()
    print("戰報：服務已關閉。查閱 server_probe.log 以獲得詳細伺服器日誌。")
