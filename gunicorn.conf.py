# -*- coding: utf-8 -*-
import multiprocessing

# --- Gunicorn 配置文件 ---

# 綁定 IP 與端口
bind = "0.0.0.0:8000"

# API 伺服器工作進程數量
# Gunicorn 會管理這些 FastAPI 進程
workers = (multiprocessing.cpu_count() * 2) + 1

# API 伺服器的工作模式
# uvicorn.workers.UvicornWorker 讓我們能以 ASGI 模式運行 FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# 日誌設定
loglevel = "info"
accesslog = "-"  # 將訪問日誌輸出到標準輸出
errorlog = "-"  # 將錯誤日誌輸出到標準輸出

# 設置環境變數，確保所有 Gunicorn 管理的進程都處於生產模式
raw_env = ["PROMETHEUS_ENV=production"]
