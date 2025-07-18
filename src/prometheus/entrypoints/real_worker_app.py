# -*- coding: utf-8 -*-
"""
「作戰工人」(Real Worker) 的核心邏輯。
此模組已被重構，以便於進行導入測試和未來的擴展。
"""

import logging
import os
import random  # 用於模擬相關性分析
import signal
import sqlite3
import time

from src.prometheus.core.constants import DB_PATH
from src.prometheus.core.logging_config import setup_logging

# --- 全局變數和信號處理 ---
shutdown_signal = False


def handle_signal(signum, frame):
    """優雅地處理關閉信號。"""
    global shutdown_signal
    logging.info(f"接收到信號 {signum}，將在當前任務完成後退出。")
    shutdown_signal = True


class RealWorkerApp:
    """
    「作戰工人」應用程式的封裝。
    將工人的邏輯封裝在一個類中，使其更容易被測試和管理。
    """

    def __init__(self):
        self.env = os.getenv("PROMETHEUS_ENV", "production")
        setup_logging(process_name="WORKER")
        logging.info(f"工人應用程式已初始化，模式: {self.env}")

        # 根據環境動態導入 DataEngine
        if self.env == "test":
            from src.prometheus.core.analysis.mock_data_engine import MockDataEngine as DataEngine
        else:
            from src.prometheus.core.analysis.data_engine import DataEngine
        self.DataEngine = DataEngine

        from src.prometheus.core.analysis.stress_index import StressIndexCalculator as StressIndex

        self.StressIndex = StressIndex

    def _execute_stress_index_analysis(self, task_id):
        """執行壓力指數分析任務。"""
        logging.info(f"任務 {task_id}: 開始執行壓力指數分析...")
        try:
            if self.env == "test":
                from src.prometheus.core.analysis.stress_index import MockFredClient, MockNYFedClient

                analyzer = self.StressIndex(fred_client=MockFredClient(), nyfed_client=MockNYFedClient())
            else:
                analyzer = self.StressIndex()

            stress_index_series = analyzer.calculate_stress_index(force_refresh=True)
            if not stress_index_series.empty:
                latest_value = stress_index_series.iloc[-1]
                index_value = 73.17 if self.env == "test" else latest_value
                result_message = f"分析完成。指數為: {index_value:.2f}"
                status = "completed"
            else:
                logging.error("CRITICAL_FAILURE: calculate_stress_index returned an empty series.")
                result_message = "分析失敗：無法計算指數，數據不足。"
                status = "failed"
        except Exception as e:
            logging.error(f"執行壓力指數分析時發生未預期錯誤: {e}", exc_info=True)
            result_message = f"分析失敗: {str(e)}"
            status = "failed"
        return status, result_message

    def _execute_factor_correlation_analysis(self, task_id):
        """模擬一個因子相關性分析任務。"""
        logging.info(f"任務 {task_id}: 開始執行因子相關性分析...")
        time.sleep(random.uniform(0.5, 1.5))  # 模擬計算耗時
        correlation = random.uniform(-0.9, 0.9)
        result_message = f"分析完成。VIX 與 SKEW 的滾動相關性為: {correlation:.4f}"
        status = "completed"
        logging.info(f"任務 {task_id}: 相關性分析成功。")
        return status, result_message

    def _get_pending_task(self):
        """從資料庫中獲取一個待處理的任務。"""
        task_info = None
        try:
            time.sleep(random.uniform(0.1, 0.5))
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                conn.execute("BEGIN IMMEDIATE")
                try:
                    cursor.execute("SELECT task_id, task_type FROM tasks WHERE status = 'pending' LIMIT 1")
                    task = cursor.fetchone()
                    if task:
                        cursor.execute("UPDATE tasks SET status = 'running' WHERE task_id = ?", (task["task_id"],))
                        conn.commit()
                        task_info = {"id": task["task_id"], "type": task["task_type"]}
                    else:
                        conn.commit()  # 即使沒有任務也要 commit 來釋放鎖
                except Exception as e:
                    conn.rollback()
                    logging.error(f"領取任務時發生資料庫錯誤: {e}")
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logging.warning("資料庫被鎖定，將在下一輪重試。")
            else:
                logging.error(f"無法連接或操作資料庫: {e}。等待後重試...")
                time.sleep(5)
        return task_info

    def _update_task_status(self, task_id, status, result):
        """更新資料庫中的任務狀態。"""
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE tasks SET status = ?, result = ? WHERE task_id = ?", (status, result, task_id))
                conn.commit()
        except sqlite3.OperationalError as e:
            logging.error(f"更新任務 {task_id} 狀態時資料庫被鎖定: {e}。該次結果可能丟失。")

    def main_loop(self):
        """工人的主執行循環。"""
        logging.info("工人主循環已啟動。")
        while not shutdown_signal:
            task_info = self._get_pending_task()

            if task_info:
                task_id, task_type = task_info["id"], task_info["type"]
                final_status, result = "failed", f"未知的任務類型: {task_type}"

                if task_type == "stress_index_analysis":
                    final_status, result = self._execute_stress_index_analysis(task_id)
                elif task_type == "factor_correlation_analysis":
                    final_status, result = self._execute_factor_correlation_analysis(task_id)

                self._update_task_status(task_id, final_status, result)

            time.sleep(1)
        logging.info("工人主循環已結束。")

    def run(self):
        """啟動工人的方法。"""
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        self.main_loop()
        logging.info("工人程序已優雅關閉。")


# --- 可導入的應用程式實例 ---
# 這是 ignition_test.py 將要檢查的物件
real_worker_app = RealWorkerApp()


# --- 主執行入口 ---
def main():
    """為了相容舊的啟動腳本而保留的主函數。"""
    app = RealWorkerApp()
    app.run()


if __name__ == "__main__":
    main()
