# -*- coding: utf-8 -*-
"""
mock_worker.py

一個瞬時響應的模擬工人，用於快速整合測試。
它會立即將任何收到的任務標記為成功，並返回一個預設的回應。
"""

import logging
import os
import signal
import time

from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.core.logging_config import setup_logging

# --- 全局變數和信號處理 ---
shutdown_signal = False


def handle_signal(signum, frame):
    """優雅地處理關閉信號。"""
    global shutdown_signal
    logging.info(f"接收到信號 {signum}，模擬工人將立即退出。")
    shutdown_signal = True


class MockWorker:
    """
    模擬工人應用程式。
    """

    def __init__(self, db_path="data/test_prometheus.db"):
        setup_logging(process_name="MOCK_WORKER")
        self.queue = SQLiteQueue(db_path)
        logging.info(f"模擬工人已初始化，資料庫路徑: {db_path}")

    def process_single_task(self):
        """處理單一任務。"""
        logging.info("Polling for a single task...")
        task_info = self.queue.get()

        if task_info:
            task_id, task_type, payload = task_info
            logging.info(f"任務 {task_id}: 已接收類型為 '{task_type}' 的任務。")
            # 立即回報成功
            result_payload = {
                "message": f"模擬成功: 任務 {task_id} 已由模擬工人處理。",
                "original_payload": payload,
            }
            self.queue.update_task(task_id, "completed", result_payload)
            logging.info(f"任務 {task_id}: 已被標記為 'completed'。")
            return True
        return False

    def main_loop(self):
        """工人的主執行循環。"""
        logging.info("模擬工人主循環已啟動，等待任務...")
        while not shutdown_signal:
            self.process_single_task()
            time.sleep(0.1)
        logging.info("模擬工人主循環已結束。")

    def run(self):
        """啟動工人的方法。"""
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        self.main_loop()
        logging.info("模擬工人程序已優雅關閉。")


if __name__ == "__main__":
    # 確保在多進程環境下能找到 src 模組
    # 這在從根目錄執行 `python mock_worker.py` 時是必需的
    import sys
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    app = MockWorker()
    app.run()
