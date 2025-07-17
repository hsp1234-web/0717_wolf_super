# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
import logging
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WEB_DIR = os.path.join(PROJECT_ROOT, 'prometheus', 'web')

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    dashboard_path = os.path.join(WEB_DIR, 'dashboard.html')
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return HTMLResponse(content="<h1>錯誤：找不到儀表板檔案。</h1>", status_code=404)

@app.get("/api/v1/system_status")
def get_system_status():
    return {"stress_index": 88, "active_strategies": 5, "status": "ok"}

# --- 新增的指令接收端點 ---
@app.post("/api/v1/execute_task")
def execute_task():
    """接收前端指令，執行一個模擬的耗時任務。"""
    logger.info("接收到前端指令：執行模擬任務...")
    # 模擬一個需要時間執行的任務
    time.sleep(1)
    logger.info("模擬任務執行完畢。")
    return {"status": "ok", "message": "後端確認：任務已成功觸發並執行完畢。"}
# -------------------------

def start():
    logger.info("命令：啟動 uvicorn 伺服器...")
    uvicorn.run(
        "prometheus.entrypoints.query_gateway:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
