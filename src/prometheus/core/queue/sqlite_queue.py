import json
import sqlite3
import time
import abc
from pathlib import Path
from typing import Any, Optional

import logging

# 為此模組創建一個標準的 logger，而不是依賴 LogManager
# 這使得模組更加獨立和可重用
logger = logging.getLogger(__name__)


class BaseQueue(abc.ABC):
    """
    任務佇列抽象基底類別。
    定義了所有佇列實現都必須提供的標準介面。
    """

    @abc.abstractmethod
    def put(self, task_data: dict) -> None:
        """
        將一個新任務放入佇列。

        Args:
            task_data (dict): 要執行的任務內容，必須是可序列化為 JSON 的字典。
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self) -> dict | None:
        """
        從佇列中取出一個待處理的任務。
        此操作應具備原子性，防止多個工作者取得同一個任務。

        Returns:
            dict | None: 如果佇列中有任務，則返回任務內容；否則返回 None。
        """
        raise NotImplementedError

    @abc.abstractmethod
    def task_done(self, task_id: any) -> None:
        """
        標記一個任務已完成。

        Args:
            task_id (any): 已完成任務的唯一識別碼。
        """
        raise NotImplementedError

    @abc.abstractmethod
    def qsize(self) -> int:
        """
        返回佇列中待處理任務的數量。

        Returns:
            int: 待處理任務的數量。
        """
        raise NotImplementedError


class SQLiteQueue(BaseQueue):
    """
    一個基於 SQLite 的、支持阻塞和毒丸關閉的持久化佇列。
    """

    def __init__(self, db_path: str | Path, table_name: str = "queue"):
        self.db_path = Path(db_path)
        self.table_name = table_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # 允許多執行緒共享同一個連線，並增加超時
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
        self._init_db()

    def _init_db(self):
        with self.conn:
            # 佇列本身的表
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 用於追蹤任務狀態的表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def put(self, item: Any):
        """
        將一個項目放入佇列，並在 tasks 表中創建一條記錄。
        item 必須是一個包含 'task_id' 的字典。
        """
        item_dict = json.loads(item) if isinstance(item, str) else item
        task_id = item_dict.get("task_id")
        if not task_id:
            raise ValueError("任務數據中必須包含 'task_id'")

        with self.conn:
            # 寫入佇列
            self.conn.execute(
                f"INSERT INTO {self.table_name} (item) VALUES (?)", (json.dumps(item_dict),)
            )
            # 創建任務狀態記錄
            self.conn.execute(
                "INSERT INTO tasks (task_id, status) VALUES (?, ?)",
                (task_id, "pending")
            )

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None):
        """更新指定任務的狀態和結果。"""
        with self.conn:
            self.conn.execute(
                """
                UPDATE tasks
                SET status = ?, result = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
                """,
                (status, result, task_id)
            )

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Any]:
        """
        從佇列中取出一個項目。
        如果 block=True，則會等待直到有項目可用。
        """
        start_time = time.time()
        while True:
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute(
                        f"SELECT id, item FROM {self.table_name} ORDER BY id LIMIT 1"
                    )
                    row = cursor.fetchone()

                    if row:
                        item_id, item_json = row
                        cursor.execute(
                            f"DELETE FROM {self.table_name} WHERE id = ?", (item_id,)
                        )
                        return json.loads(item_json)
            except sqlite3.Error as e:
                # 如果發生資料庫錯誤，短暫等待後重試
                logger.error(f"從佇列讀取時發生資料庫錯誤: {e}", exc_info=True)
                time.sleep(0.1)

            if not block:
                return None

            if timeout and (time.time() - start_time) > timeout:
                return None

            time.sleep(0.1)  # 避免過於頻繁地查詢

    def qsize(self) -> int:
        """返回佇列中的項目數量。"""
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cursor.fetchone()[0]

    def task_done(self, task_id: any) -> None:
        """在這個實作中，get() 已經是原子性的，所以這個方法可以留空。"""
        pass

    def close(self):
        """關閉資料庫連線。"""
        if self.conn:
            self.conn.close()
            self.conn = None
