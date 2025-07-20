import os
from pyngrok import ngrok

# 從環境變數中取得 ngrok authtoken
authtoken = os.environ.get("NGROK_AUTHTOKEN")
if not authtoken:
    print("錯誤：請在環境變數中設定 NGROK_AUTHTOKEN")
    exit(1)

ngrok.set_auth_token(authtoken)

# 啟動 ngrok 通道
public_url = ngrok.connect(8000)
print("====================================================================")
print(f"  服務網址： {public_url}")
print("====================================================================")
