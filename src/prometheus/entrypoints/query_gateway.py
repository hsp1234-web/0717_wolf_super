# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
import logging
import os
import sqlite3
import uuid

# --- 基礎設定 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()

# --- 路徑與資料庫設定 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH = os.environ.get("DB_PATH", os.path.join(PROJECT_ROOT, 'tasks.sqlite'))
WEB_DIR = os.path.join(PROJECT_ROOT, 'prometheus', 'web')

def init_db():
    """初始化任務資料庫與資料表。"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result TEXT
        )
        """)
        conn.commit()
        logger.info("任務資料庫已成功初始化。")

@app.on_event("startup")
async def startup_event():
    """伺服器啟動時初始化資料庫。"""
    init_db()

# --- API 端點 ---
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return FileResponse(os.path.join(WEB_DIR, 'dashboard.html'))

@app.post("/api/v1/submit_task")
def submit_task():
    """接收前端指令，創建一個任務並放入佇列。"""
    task_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (task_id, task_type, status) VALUES (?, ?, ?)",
            (task_id, 'deep_analysis', 'pending')
        )
        conn.commit()
    logger.info(f"已創建新任務，ID: {task_id}")
    return {"status": "ok", "message": "任務已成功提交", "task_id": task_id}

@app.get("/api/v1/task_status/{task_id}")
def get_task_status(task_id: str):
    """根據任務 ID 查詢任務狀態。"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT status, result FROM tasks WHERE task_id = ?", (task_id,))
        task = cursor.fetchone()
    if task:
        return {"task_id": task_id, "status": task["status"], "result": task["result"]}
    raise HTTPException(status_code=404, detail="找不到指定的任務")

def start():
    uvicorn.run("prometheus.entrypoints.query_gateway:app", host="0.0.0.0", port=8000, log_level="info")
