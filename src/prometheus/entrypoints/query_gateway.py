# -*- coding: utf-8 -*-
from fastapi import FastAPI
import logging
from fastapi import HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import os
import sqlite3
import uuid
import time
import threading
import psutil

from src.prometheus.core.constants import DB_PATH, WEB_DIR
from src.prometheus.core.logging_config import setup_logging

setup_logging(process_name="API_SERVER")

app = FastAPI()

@app.get("/health", tags=["System"])
def health_check():
    """提供一個簡單的健康檢查端點，用於驗證服務是否啟動並可響應。"""
    return {"status": "ok", "message": "Prometheus API is alive."}

# --- 全域變數與鎖，用於儲存和安全地讀寫監控數據 ---
system_metrics = {"cpu_percent": 0.0, "memory_percent": 0.0}
metrics_lock = threading.Lock()

class TaskRequest(BaseModel):
    task_type: str

def hardware_monitor():
    """在背景持續監控硬體資源。"""
    logging.info("[神經中樞] 硬體監控執行緒已啟動。")
    while True:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        with metrics_lock:
            system_metrics["cpu_percent"] = cpu
            system_metrics["memory_percent"] = mem
        time.sleep(2) # 每 2 秒更新一次數據

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY, task_type TEXT NOT NULL, status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, result TEXT
        )""")
        conn.commit()

@app.on_event("startup")
async def startup_event():
    init_db()
    # 啟動背景監控執行緒
    monitor_thread = threading.Thread(target=hardware_monitor, daemon=True)
    monitor_thread.start()

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return FileResponse(WEB_DIR / 'dashboard.html')

@app.post("/api/v1/submit_task")
def submit_task(task_request: TaskRequest):
    task_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task_id, task_type, status) VALUES (?, ?, ?)",
                       (task_id, task_request.task_type, 'pending'))
        conn.commit()
    return {"status": "ok", "task_id": task_id}

@app.get("/api/v1/task_status/{task_id}")
def get_task_status(task_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT status, result FROM tasks WHERE task_id = ?", (task_id,))
        task = cursor.fetchone()
    if task: return {"task_id": task_id, "status": task["status"], "result": task["result"]}
    raise HTTPException(status_code=404, detail="找不到指定的任務")

@app.get("/api/v1/get_task_history")
def get_task_history():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 10")
        tasks = cursor.fetchall()
    return [dict(task) for task in tasks]

# --- 新增的系統指標接口 ---
@app.get("/api/v1/get_system_metrics")
def get_system_metrics():
    """獲取即時的系統資源使用率。"""
    with metrics_lock:
        return system_metrics.copy()
# -------------------------

def start():
    uvicorn.run("prometheus.entrypoints.query_gateway:app", host="0.0.0.0", port=8000, log_level="info")
