# -*- coding: utf-8 -*-
import logging
import os
import sqlite3
import time

logging.basicConfig(level=logging.INFO, format="[工人] %(asctime)s - %(message)s")
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "tasks.sqlite"))


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
        logging.info("任務資料庫已成功初始化。")


def process_task(task_id):
    """模擬處理一個任務。"""
    logging.info(f"正在處理任務 {task_id}...")
    time.sleep(5)  # 模擬耗時工作
    result_message = "分析完成，一切指標正常。"
    logging.info(f"任務 {task_id} 處理完畢。")
    return result_message


def main_loop():
    """工人的主循環，不斷尋找並處理任務。"""
    init_db()
    logging.info("工人程序已啟動，正在監聽新任務...")
    while True:
        task_to_process = None
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # --- 事務性操作：安全地領取任務 ---
            conn.execute("BEGIN IMMEDIATE")
            try:
                cursor.execute("SELECT task_id FROM tasks WHERE status = 'pending' LIMIT 1")
                task = cursor.fetchone()
                if task:
                    task_id = task["task_id"]
                    cursor.execute("UPDATE tasks SET status = 'running' WHERE task_id = ?", (task_id,))
                    conn.commit()
                    task_to_process = task_id
                else:
                    conn.commit()  # 如果沒任務，也要結束事務
            except Exception as e:
                conn.rollback()
                logging.error(f"領取任務時發生資料庫錯誤: {e}")

        if task_to_process:
            result = process_task(task_to_process)
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET status = 'completed', result = ? WHERE task_id = ?", (result, task_to_process)
                )
                conn.commit()

        time.sleep(1)  # 輪詢間隔


if __name__ == "__main__":
    main_loop()
