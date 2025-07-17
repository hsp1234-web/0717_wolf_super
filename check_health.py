# -*- coding: utf-8 -*-
import requests
import time
import sys

URL = "http://127.0.0.1:8000/health"
ATTEMPTS = 5
DELAY = 2

print(f"健康探針已啟動，將在 {ATTEMPTS * DELAY} 秒內嘗試探測 {URL}...")
for i in range(ATTEMPTS):
    try:
        response = requests.get(URL, timeout=3)
        if response.status_code == 200 and response.json().get("status") == "ok":
            print(f"✅ 探測成功！伺服器在第 {i+1} 次嘗試後回報狀態正常。")
            sys.exit(0)
        else:
            print(f"🟡 第 {i+1} 次嘗試：伺服器回應異常，狀態碼 {response.status_code}。")
    except requests.ConnectionError:
        print(f"🟡 第 {i+1} 次嘗試：無法連接到伺服器，等待 {DELAY} 秒後重試...")
    except Exception as e:
        print(f"🟡 第 {i+1} 次嘗試：發生未知錯誤 {e}。")

    time.sleep(DELAY)

print("❌ 探測失敗！在所有嘗試後，伺服器仍未處於健康狀態。")
sys.exit(1)
