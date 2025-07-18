import json
import sqlite3
import time
import uuid
from typing import Any, Dict, Optional, Tuple


class SQLiteQueue:
    # ... (原有 __init__, _get_connection) ...
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_table()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=10)

    def _create_table(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 任務表 (既有)
            # 注意：我們將 task_id 設為 UNIQUE 但不是 PRIMARY KEY，以允許自動增量的 id
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    task_type TEXT NOT NULL,
                    payload TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    retrieved_at REAL
                )
            """)
            # 新增：性能日誌表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    step_name TEXT NOT NULL,
                    duration REAL NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            # 新增：硬體日誌表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hardware_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cpu_percent REAL NOT NULL,
                    ram_percent REAL NOT NULL,
                    active_workers INTEGER
                )
            """)
            conn.commit()

    # ... (原有 put, get, update_task, get_task 方法) ...
    def put(self, task_type: str, payload: Optional[Dict[str, Any]] = None) -> str:
        task_id = str(uuid.uuid4())
        current_time = time.time()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, task_type, payload, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, task_type, json.dumps(payload) if payload else "{}", "pending", current_time, current_time),
            )
        return task_id

    def get(self) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 使用 FOR UPDATE 和 LIMIT 1 來鎖定行，雖然 SQLite 的並行處理方式不同，但這是個好習慣
            cursor.execute(
                "SELECT id, task_id, task_type, payload FROM tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                record_id, task_id, task_type, payload_str = row
                cursor.execute(
                    "UPDATE tasks SET status = ?, retrieved_at = ? WHERE id = ?", ("processing", time.time(), record_id)
                )
                conn.commit()
                # 如果 payload 為空，返回一個空字典
                return task_id, task_type, json.loads(payload_str) if payload_str else {}
        return None

    def update_task(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE task_id = ?",
                (status, json.dumps(result) if result else "{}", time.time(), task_id),
            )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # 新增：日誌寫入方法
    def log_performance(self, task_id: str, step_name: str, duration: float):
        """紀錄一個性能指標"""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO performance_logs (task_id, step_name, duration, timestamp) VALUES (?, ?, ?, ?)",
                (task_id, step_name, duration, time.time()),
            )

    def log_hardware(self, cpu: float, ram: float, workers: int):
        """紀錄硬體使用情況"""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO hardware_logs (timestamp, cpu_percent, ram_percent, active_workers) VALUES (?, ?, ?, ?)",
                (time.time(), cpu, ram, workers),
            )
