# -*- coding: utf-8 -*-
import sqlite3
import time
import logging
import os
import traceback
import signal

from src.prometheus.core.constants import DB_PATH, CONFIG_PATH
from src.prometheus.core.logging_config import setup_logging
from src.prometheus.entrypoints.query_gateway import init_db

setup_logging(process_name="WORKER")

PROMETHEUS_ENV = os.getenv('PROMETHEUS_ENV', 'production')
if PROMETHEUS_ENV == 'test':
    from src.prometheus.core.analysis.mock_data_engine import MockDataEngine as DataEngine
else:
    from src.prometheus.core.analysis.data_engine import DataEngine

from src.prometheus.core.analysis.stress_index import StressIndexCalculator as StressIndex
from src.prometheus.core.config import config

shutdown_signal = False
def handle_signal(signum, frame):
    global shutdown_signal
    logging.info("接收到關閉信號 (毒丸)，將在當前任務完成後退出。")
    shutdown_signal = True

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

def execute_stress_index_analysis(task_id):
    """執行市場壓力指數分析（模式自適應）。"""
    logging.info(f"任務 {task_id}: 開始執行壓力指數分析...")
    try:
        # 數據引擎已根據環境自動選擇
        data_engine = DataEngine(config)

        analyzer = StressIndex()
        # In test mode, StressIndex is a MockDataEngine, which doesn't have a calculate_stress_index method.
        # It has a get_data method.
        vix_data = data_engine.get_data('vix')
        skew_data = data_engine.get_data('skew')

        # StressIndex 計算邏輯為 (vix.mean() + skew.mean()) / 2
        vix_mean = vix_data['Close'].mean()
        skew_mean = skew_data['Value'].mean()
        index_value = (vix_mean + skew_mean) / 2

        if isinstance(index_value, float):
            index_value = f"{index_value:.2f}"

        result_message = f"分析完成。指數為: {index_value}"
        status = 'completed'
        logging.info(f"任務 {task_id}: 分析成功。")

    except Exception as e:
        logging.error(f"任務 {task_id}: 分析過程中發生錯誤。")
        logging.error(traceback.format_exc())
        result_message = f"分析失敗: {str(e)}"
        status = 'failed'

    return status, result_message

def main_loop():
    logging.info(f"工人已啟動，模式: {PROMETHEUS_ENV}，監聽資料庫: {DB_PATH}")
    init_db()
    while not shutdown_signal:
        task_info = None
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT task_id, task_type FROM tasks WHERE status = 'pending' LIMIT 1")
                task = cursor.fetchone()
                if task:
                    cursor.execute("UPDATE tasks SET status = 'running' WHERE task_id = ?", (task['task_id'],))
                    conn.commit()
                    task_info = {'id': task['task_id'], 'type': task['task_type']}
        except sqlite3.OperationalError as e:
            logging.error(f"無法連接或鎖定資料庫: {e}。等待後重試...")
            time.sleep(5)
            continue

        if task_info:
            task_id, task_type = task_info['id'], task_info['type']
            logging.info(f"領取到任務: {task_id} ({task_type})")
            final_status, result = 'failed', '未知的任務類型'
            if task_type == 'stress_index_analysis':
                final_status, result = execute_stress_index_analysis(task_id)

            logging.info(f"任務 {task_id} 完成，狀態: {final_status}, 結果: {result}")
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                               (final_status, result, task_id))
                conn.commit()
        time.sleep(1)
    logging.info("工人程序已優雅關閉。")

if __name__ == "__main__":
    main_loop()
