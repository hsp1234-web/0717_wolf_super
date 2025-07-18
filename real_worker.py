# -*- coding: utf-8 -*-
import json
import logging
import time
import random

from tenacity import retry, stop_after_attempt, wait_fixed

# 修正導入
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.core.constants import DB_PATH
from src.prometheus.core.logging_config import setup_logging

# --- 新增的任務執行模組 ---
import yfinance as yf
import pandas as pd

# 設定日誌
setup_logging()
logger = logging.getLogger(__name__)

# --- 任務處理函數 ---

def execute_simple_moving_average(payload: dict):
    """
    執行簡單移動平均線 (SMA) 計算任務。
    """
    symbol = payload.get("symbol")
    window = payload.get("window", 20)

    if not symbol:
        logger.error("SMA 任務失敗：缺少股票代碼 (symbol)。")
        return

    logger.info(f"開始執行 SMA 任務：股票代碼={symbol}, 窗口={window}")
    try:
        stock = yf.Ticker(symbol)
        # 獲取足夠的歷史數據
        hist = stock.history(period=f"{window+50}d")
        if hist.empty:
            logger.error(f"SMA 任務失敗：無法獲取 {symbol} 的歷史數據。")
            return

        sma = hist['Close'].rolling(window=window).mean().iloc[-1]
        # 在原有的日誌基礎上，使用 logging.SUCCESS
        logger.info(f"✅ SMA 任務完成: {symbol} 的 {window} 日均線為: {sma:.2f}")
    except Exception as e:
        logger.error(f"SMA 任務執行出錯：{e}")

# --- 任務分派器 ---

TASK_DISPATCHER = {
    "simple_moving_average": execute_simple_moving_average
}

class RealWorker:
    def __init__(self):
        # 修正實例化
        self.task_queue = SQLiteQueue(db_path=DB_PATH)
        self.worker_id = f"worker-{random.randint(1000, 9999)}"
        logger.info(f"工人 {self.worker_id} 已啟動，準備接收任務。")

    # tenacity 的重試邏輯在這裡可能不再完全適用於簡單的 get，但暫時保留
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def fetch_and_process_task(self):
        # 使用 get 方法
        task_data_str = self.task_queue.get(block=False) # 非阻塞獲取
        if task_data_str:
            logger.info(f"{self.worker_id} 領取到新任務。")

            try:
                # 反序列化 JSON 字串為 Python 字典
                task_data = json.loads(task_data_str)
                task_type = task_data.get("task_type")
                payload = task_data.get("payload", {})

                handler = TASK_DISPATCHER.get(task_type)

                if handler:
                    handler(payload)
                else:
                    logger.warning(f"未知的任務類型: {task_type}，任務將被忽略。")

                # SQLiteQueue 的 get 是原子性的，取出即刪除，所以不需要 complete/fail
                logger.info(f"任務處理完畢。")

            except json.JSONDecodeError:
                logger.error(f"任務數據格式無效 (非 JSON)，任務已被丟棄。")
            except Exception as e:
                logger.error(f"處理任務時發生未知錯誤: {e}，任務已被丟棄。")
        else:
            # logger.info(f"{self.worker_id} 未發現新任務，稍後重試。")
            pass # 沒有任務時保持安靜

    def run(self):
        while True:
            try:
                self.fetch_and_process_task()
            except Exception as e:
                # 如果 fetch_and_process_task 的 retry 耗盡，這裡會捕獲異常
                logger.error(f"獲取任務失敗，暫停 10 秒後重試: {e}")
                time.sleep(10)

            time.sleep(5) # 每 5 秒輪詢一次

if __name__ == "__main__":
    worker = RealWorker()
    worker.run()
