# -*- coding: utf-8 -*-
import os
import subprocess
import time

import click

# 根據 CPU 核心數決定工人數量，留出一個核心給系統和 API
WORKER_COUNT = max(1, os.cpu_count() - 1)


@click.group()
def cli():
    """普羅米修斯系統管理工具"""
    pass


@cli.command()
def start_services():
    """使用 Gunicorn 啟動 API 伺服器和工人蜂群"""
    print("[*] 正在啟動 API 伺服器 (由 Gunicorn 管理)...")
    # 使用 gunicorn 啟動 FastAPI 應用
    api_server_cmd = [
        "poetry",
        "run",
        "gunicorn",
        "-c",
        "gunicorn.conf.py",
        "src.prometheus.entrypoints.query_gateway:app",
    ]
    # 在背景啟動 API 伺服器
    subprocess.Popen(api_server_cmd)

    print(f"[*] 正在啟動 {WORKER_COUNT} 個工人的蜂群...")
    # 獨立啟動多個工人程序
    for i in range(WORKER_COUNT):
        worker_cmd = ["poetry", "run", "python", "real_worker.py"]
        subprocess.Popen(worker_cmd, env=os.environ.copy())

    print("\n[+] 所有服務已啟動。API 伺服器運行在 http://0.0.0.0:8000")
    print(f"[+] {WORKER_COUNT} 個工人正在背景監聽任務。")
    # 讓主腳本保持運行以監控
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 正在關閉所有服務...")
        # 這裡需要一個更優雅的關閉機制，但暫時從簡
        subprocess.run(["pkill", "-f", "gunicorn"])
        subprocess.run(["pkill", "-f", "real_worker.py"])
        print("[+] 服務已關閉。")


if __name__ == "__main__":
    cli()
