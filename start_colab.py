import os
import subprocess
import time
from IPython.display import display, HTML

def run_command(command):
    """執行一個 shell 命令並打印輸出"""
    print(f"🚀 執行中: {command}")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in iter(process.stdout.readline, ''):
        print(line, end='')
    process.stdout.close()
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)

def main():
    """
    普羅米修斯計畫 Colab 一鍵式部署腳本
    """
    print("==============================================")
    print("== 普羅米修斯計畫：Colab 作戰沙盒部署啟動 ==")
    print("==============================================")

    # --- 步驟 1: 環境準備 ---
    print("\n--- 步驟 1: 準備作戰環境 ---")
    os.makedirs("data", exist_ok=True)

    # 在真實 Colab 環境中，需要確保所有 .py 檔案已存在
    # 此處假設它們位於正確的路徑

    # --- 步驟 2: 安裝作戰所需軍火 (依賴) ---
    print("\n--- 步驟 2: 安裝作戰依賴 ---")
    try:
        # 在 Colab 中，我們不使用 poetry 的虛擬環境
        run_command("pip install poetry && poetry config virtualenvs.create false && poetry install --no-root")
    except Exception as e:
        print(f"🔴 依賴安裝失敗: {e}")
        return

    # --- 步驟 3: 啟動核心背景服務 ---
    print("\n--- 步驟 3: 啟動核心背景服務 ---")

    # 啟動 Gunicorn 作戰司令部 (API Server)
    # 使用 nohup 確保進程在背景持續運行
    api_log = open("api_server.log", "w")
    api_process = subprocess.Popen(
        "gunicorn -c gunicorn.conf.py src.prometheus.entrypoints.query_gateway:app",
        shell=True,
        stdout=api_log,
        stderr=api_log
    )
    print("✅ 作戰司令部 (API Server) 已在背景啟動。日誌 -> api_server.log")

    # 啟動多個堅韌工人 (Worker)
    num_workers = 2
    worker_processes = []
    for i in range(num_workers):
        worker_log = open(f"worker_{i+1}.log", "w")
        worker_process = subprocess.Popen(
            "python real_worker.py",
            shell=True,
            stdout=worker_log,
            stderr=worker_log
        )
        worker_processes.append(worker_process)
        print(f"✅ 作戰部隊 {i+1} (Worker) 已在背景啟動。日誌 -> worker_{i+1}.log")

    print(f"✅ 共 {num_workers} 組作戰部隊已部署。")

    # --- 步驟 4: 建立原生通道並展示神之眼儀表板 ---
    print("\n--- 步驟 4: 建立原生安全通道 ---")
    print("⏳ 請稍候，正在生成公開訪問連結...")
    time.sleep(5) # 等待服務完全啟動

    try:
        # 使用 pyngrok 作為備用方案，因為 Colab 原生功能有時不穩定
        from pyngrok import ngrok
        public_url = ngrok.connect(8000)
        print(f"✅ ngrok 通道已建立: {public_url}")
    except ImportError:
        print("無法導入 pyngrok，將嘗試 Colab 原生端口轉發。")
        print("如果失敗，請手動執行 !pip install pyngrok")
        from google.colab.output import serve_kernel_port_as_window
        public_url = serve_kernel_port_as_window(8000, anchor_text="👉 點此開啟「善狼研究平台」作戰指揮室")

    # --- 步驟 5: 交付儀表板 ---
    dashboard_html = f"""
    <div style="border: 2px solid #4285F4; padding: 20px; border-radius: 10px; font-family: 'Noto Sans TC', sans-serif;">
        <h2 style="color: #1A73E8; margin-top: 0;">🚀 普羅米修斯系統已上線 🚀</h2>
        <p>所有背景服務已成功啟動，系統進入待命狀態。</p>
        <p><strong>作戰指揮室入口:</strong></p>
        <p>✅ <a href="{public_url}" target="_blank">點此開啟「善狼研究平台」安全通道</a></p>
        <p><strong>系統狀態:</strong></p>
        <ul>
            <li><strong>作戰司令部 (API Server):</strong> <span style="color: green;">●</span> 運行中</li>
            <li><strong>作戰部隊 (Workers):</strong> <span style="color: green;">●</span> {num_workers} 組運行中</li>
        </ul>
        <p style="font-size: 0.8em; color: #5f6368;"><i>請在新視窗中操作平台。此 Colab 頁面將持續顯示服務日誌。</i></p>
    </div>
    """
    display(HTML(dashboard_html))
    print("\n==============================================")
    print("== 部署完成，系統待命中... ==")
    print("==============================================")


if __name__ == "__main__":
    # 在 Colab 中，我們需要確保 ngrok 在導入時可用
    try:
        import pyngrok
    except ImportError:
        print("未檢測到 pyngrok，正在自動安裝...")
        run_command("pip install pyngrok")
    main()
