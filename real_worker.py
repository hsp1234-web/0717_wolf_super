# -*- coding: utf-8 -*-
import sqlite3
import time
import logging
import os
import random

logging.basicConfig(level=logging.INFO, format='[實戰工人] %(asctime)s - %(message)s')
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), 'tasks.sqlite'))

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

def execute_deep_analysis(task_id):
    """模擬一個真實的、有隨機性的深度分析任務。"""
    logging.info(f"任務 {task_id}: 開始執行深度分析...")
    # 模擬複雜計算
    time.sleep(5)
    # 模擬可能成功或失敗的結果
    if random.random() > 0.1: # 90% 的成功率
        result_message = f"分析完成。市場壓力指數評估為: {random.randint(20, 80)}"
        status = 'completed'
    else:
        result_message = "分析失敗：關鍵數據源無法連接。"
        status = 'failed'

    logging.info(f"任務 {task_id}: 分析結束，狀態為 {status}。")
    return status, result_message

def main_loop():
    init_db()
    logging.info("實戰工人已啟動，準備接收作戰指令...")
    while True:
        task_info = None
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            conn.execute("BEGIN IMMEDIATE")
            try:
                cursor.execute("SELECT task_id, task_type FROM tasks WHERE status = 'pending' LIMIT 1")
                task = cursor.fetchone()
                if task:
                    cursor.execute("UPDATE tasks SET status = 'running' WHERE task_id = ?", (task['task_id'],))
                    conn.commit()
                    task_info = {'id': task['task_id'], 'type': task['task_type']}
                else:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                logging.error(f"領取任務時發生資料庫錯誤: {e}")

        if task_info:
            task_id, task_type = task_info['id'], task_info['type']
            final_status, result = 'failed', '未知的任務類型'

            if task_type == 'deep_analysis':
                final_status, result = execute_deep_analysis(task_id)
            # 未來可在此處添加更多 elif task_type == '...'

            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                    (final_status, result, task_id)
                )
                conn.commit()

        time.sleep(1)

if __name__ == "__main__":
    main_loop()
