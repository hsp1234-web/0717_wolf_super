# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse # <-- 關鍵修復：導入 FileResponse
import uvicorn
import logging
import os

# 設定基礎日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 取得專案根目錄的絕對路徑
# 這確保無論從哪裡執行 run.py，都能找到正確的檔案路徑
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WEB_DIR = os.path.join(PROJECT_ROOT, 'prometheus', 'web')


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """提供儀表板主頁面。"""
    dashboard_path = os.path.join(WEB_DIR, 'dashboard.html')
    logger.info(f"正在嘗試提供儀表板檔案，路徑: {dashboard_path}")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    else:
        logger.error(f"錯誤：找不到儀表板檔案 at {dashboard_path}")
        return HTMLResponse(content="<h1>錯誤：找不到儀表板檔案。</h1>", status_code=404)

@app.get("/api/v1/system_status")
def get_system_status():
    """提供模擬的系統狀態數據。"""
    logger.info("接收到 /api/v1/system_status 請求")
    return {"stress_index": 88, "active_strategies": 5, "status": "ok"}


def start():
    """啟動儀表板後端服務。"""
    logger.info("命令：啟動 uvicorn 伺服器...")
    uvicorn.run(
        "prometheus.entrypoints.query_gateway:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
