from google.colab.output import eval_js

# 使用 Colab 內建代理產生公開網址
public_url = eval_js('google.colab.kernel.proxyPort(8000)')

print("====================================================================")
print(f"  服務網址： {public_url}")
print("====================================================================")
