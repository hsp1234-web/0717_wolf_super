# -*- coding: utf-8 -*-
"""
「作戰工人」(Real Worker) 的核心邏輯 v2.0 (單一核心版)。

此工人現在是一個純粹的指令執行者。它從隊列中獲取任務，
並將其分派給 `PrometheusService` 來處理實際的業務邏輯。
"""

import logging
import os
import signal
import time

from src.prometheus.core.clients.client_factory import ClientFactory
from src.prometheus.core.db.data_warehouse import DataWarehouse
from src.prometheus.core.logging_config import setup_logging
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.core.services import PrometheusService

# --- 全局變數和信號處理 ---
shutdown_signal = False


def handle_signal(signum, frame):
    """優雅地處理關閉信號。"""
    global shutdown_signal
    logging.info(f"接收到信號 {signum}，將在當前任務完成後退出。")
    shutdown_signal = True


class RealWorkerApp:
    """
    「作戰工人」應用程式 v2.0

    此版本將所有業務邏輯委託給 PrometheusService。
    """

    def __init__(self):
        self.env = os.getenv("PROMETHEUS_ENV", "production")
        setup_logging(process_name="WORKER_V2")
        logging.info(f"工人應用程式已初始化，模式: {self.env}")

        # 初始化所有依賴項
        db_path = os.getenv("DB_PATH", "data/prometheus.db")
        warehouse_path = os.getenv("WAREHOUSE_PATH", "data/warehouse.duckdb")

        self.queue = SQLiteQueue(db_path)
        self.warehouse = DataWarehouse(warehouse_path)
        self.client_factory = ClientFactory()  # 可根據需要進行擴展

        # 創建核心服務的單一實例
        self.service = PrometheusService(
            queue=self.queue,
            warehouse=self.warehouse,
            client_factory=self.client_factory,
        )
        logging.info("PrometheusService 已成功初始化。")

    def _dispatch_task(self, task_id: str, task_type: str):
        """
        根據任務類型將任務分派給核心服務。
        """
        logging.info(f"任務 {task_id}: 正在分派類型為 '{task_type}' 的任務...")

        handler_map = {
            "stress_index_analysis": self.service.run_stress_index_analysis,
            "factor_correlation_analysis": self.service.run_factor_correlation_analysis,
        }

        handler = handler_map.get(task_type)

        if handler:
            # 傳遞 task_id，如果處理程序需要它
            if task_type == "stress_index_analysis":
                return handler(task_id=task_id, env=self.env)
            else:
                return handler(task_id=task_id)
        else:
            logging.warning(f"任務 {task_id}: 找不到類型為 '{task_type}' 的處理程序。")
            return "failed", f"未知的任務類型: {task_type}"

    def main_loop(self):
        """工人的主執行循環。"""
        logging.info("工人主循環已啟動。")
        while not shutdown_signal:
            task_info = self.queue.get()  # 使用正確的 get 方法

            if task_info:
                task_id, task_type, payload = task_info
                final_status, result_message = self._dispatch_task(task_id, task_type)
                # 將結果打包成字典
                result_payload = {"message": result_message}
                self.queue.update_task(task_id, final_status, result_payload)

            time.sleep(1)  # 短暫休眠以避免 CPU 過度使用
        logging.info("工人主循環已結束。")

    def run(self):
        """啟動工人的方法。"""
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        self.main_loop()
        logging.info("工人程序已優雅關閉。")


# --- 可導入的應用程式實例 ---
real_worker_app = RealWorkerApp()


# --- 主執行入口 ---
def main():
    """為了相容舊的啟動腳本而保留的主函數。"""
    app = RealWorkerApp()
    app.run()


if __name__ == "__main__":
    main()
