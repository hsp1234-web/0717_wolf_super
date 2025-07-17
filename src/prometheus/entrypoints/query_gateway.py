# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import logging
import os
import sqlite3
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()

class TaskRequest(BaseModel):
    task_type: str

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DB_PATH = os.environ.get("DB_PATH", os.path.join(PROJECT_ROOT, 'tasks.sqlite'))
WEB_DIR = os.path.join(PROJECT_ROOT, 'src', 'prometheus', 'web')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result TEXT
        )""")
        conn.commit()

@app.on_event("startup")
async def startup_event(): init_db()

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return FileResponse(os.path.join(WEB_DIR, 'dashboard.html'))

@app.post("/api/v1/submit_task")
def submit_task(task_request: TaskRequest):
    task_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, task_type, status) VALUES (?, ?, ?)",
                       (task_id, task_request.task_type, 'pending'))
        conn.commit()
    return {"status": "ok", "message": "任務已成功提交", "task_id": task_id}

@app.get("/api/v1/task_status/{task_id}")
def get_task_status(task_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT status, result FROM tasks WHERE task_id = ?", (task_id,))
        task = cursor.fetchone()
    if task:
        return {"task_id": task_id, "status": task["status"], "result": task["result"]}
    raise HTTPException(status_code=404, detail="找不到指定的任務")

# --- 新增的歷史任務接口 ---
@app.get("/api/v1/get_task_history")
def get_task_history():
    """獲取最近 10 筆歷史任務記錄。"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT task_id, task_type, status, result, created_at FROM tasks ORDER BY created_at DESC LIMIT 10")
        tasks = cursor.fetchall()
    # 將 sqlite3.Row 物件轉換為字典列表以便 JSON 序列化
    return [dict(task) for task in tasks]
# -------------------------

def start():
    uvicorn.run("prometheus.entrypoints.query_gateway:app", host="0.0.0.0", port=8000, log_level="info")
