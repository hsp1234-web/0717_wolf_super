import sqlite3
import json
import time
import uuid
from typing import Optional, Dict, Any, Tuple

class SQLiteQueue:
    """
    一個基於 SQLite 的持久化任務佇列，支持任務狀態追蹤。
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        # 每次操作都建立新的連線，以簡化多線程/多進程下的問題
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化資料庫和資料表。"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    payload TEXT,
                    status TEXT NOT NULL,
                    result TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    def put(self, task_type: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """
        將一個新任務加入佇列。
        """
        task_id = str(uuid.uuid4())
        current_time = time.time()
        payload_json = json.dumps(payload) if payload else None

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO tasks (task_id, task_type, payload, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, task_type, payload_json, 'pending', current_time, current_time)
            )
            conn.commit()
        return task_id

    def get(self) -> Optional[Tuple[str, str, Optional[Dict[str, Any]]]]:
        """
        以原子操作獲取一個待處理的任務並將其標記為 'processing'。
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # 以原子方式尋找並更新任務
            cursor.execute("""
                UPDATE tasks
                SET status = 'processing', updated_at = ?
                WHERE task_id = (
                    SELECT task_id FROM tasks
                    WHERE status = 'pending'
                    ORDER BY created_at
                    LIMIT 1
                )
                RETURNING task_id, task_type, payload;
            """, (time.time(),))

            task = cursor.fetchone()
            conn.commit()

        if task:
            payload = json.loads(task['payload']) if task['payload'] else None
            return task['task_id'], task['task_type'], payload
        return None

    def update_task(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """
        更新任務的狀態和結果。
        """
        current_time = time.time()
        result_json = json.dumps(result) if result else None

        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, result = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (status, result_json, current_time, task_id)
            )
            conn.commit()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根據任務 ID 獲取任務的詳細資訊。
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()

        return dict(task) if task else None
