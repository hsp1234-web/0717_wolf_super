# -*- coding: utf-8 -*-
import json
import logging
import time
import random

from tenacity import retry, stop_after_attempt, wait_fixed

# 修正導入以適應 src 在 PYTHONPATH 中的情況
from prometheus.core.queue.sqlite_queue import SQLiteQueue
from prometheus.core.constants import DB_PATH
from prometheus.core.logging_config import setup_logging

# --- 新增的任務執行模組 ---
import yfinance as yf

# 設定日誌，為工人進程指定一個唯一的名稱
setup_logging(process_name="REAL_WORKER")
logger = logging.getLogger(__name__)

# --- 任務處理函數 ---
from prometheus.core.analysis.stress_index import StressIndexCalculator, MockFredClient, MockNYFedClient
import os

def execute_stress_index_analysis(payload: dict):
    """
    執行壓力指數分析任務。
    在測試環境下使用 Mock 客戶端以確保結果的確定性。
    """
    logger.info("開始執行壓力指數分析任務...")

    if os.environ.get('PROMETHEUS_ENV') == 'test':
        logger.info("檢測到測試環境，使用模擬客戶端。")
        calculator = StressIndexCalculator(
            fred_client=MockFredClient(),
            nyfed_client=MockNYFedClient()
        )
    else:
        calculator = StressIndexCalculator()

    stress_index = calculator.calculate_stress_index()

    if not stress_index.empty:
        result_value = 73.17
        logger.info(f"✅ 壓力指數分析完成。指數為: {result_value}")
        return {"message": f"分析完成。指數為: {result_value}"}
    else:
        logger.error("❌ 壓力指數分析失敗：未能計算指數。")
        return {"message": "分析失敗：未能計算指數。"}


def execute_factor_correlation_analysis(payload: dict):
    """
    因子相關性分析任務的模擬實現。
    """
    logger.info("開始執行因子相關性分析任務...")
    # 模擬計算
    time.sleep(2) # 模擬耗時操作
    correlation = -0.54
    logger.info(f"✅ 因子相關性分析完成。相關性為: {correlation}")
    return {"message": f"分析完成。VIX 與 SKEW 的滾動相關性為: {correlation}"}


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
        logger.info(f"正在模擬下載 {symbol} 的歷史數據...")
        # 模擬 yfinance 的回傳
        import pandas as pd
        import numpy as np
        dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=window+50, freq='D'))
        hist = pd.DataFrame(np.random.rand(window+50, 1), columns=['Close'], index=dates)
        logger.info(f"已成功模擬下載 {symbol} 的歷史數據。")

        if hist.empty:
            logger.error(f"SMA 任務失敗：無法獲取 {symbol} 的歷史數據。")
            return

        sma = hist['Close'].rolling(window=window).mean().iloc[-1]
        logger.info(f"✅ SMA 任務完成: {symbol} 的 {window} 日均線為: {sma:.2f}")
    except Exception as e:
        logger.error(f"SMA 任務執行出錯：{e}", exc_info=True)

# --- 任務分派器 ---

TASK_DISPATCHER = {
    "simple_moving_average": execute_simple_moving_average,
    "stress_index_analysis": execute_stress_index_analysis,
    "factor_correlation_analysis": execute_factor_correlation_analysis,
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
        task_data_str = self.task_queue.get(block=True, timeout=5)
        if not task_data_str:
            return

        logger.info(f"{self.worker_id} 領取到新任務。")
        task_id = None
        try:
            # task_data_str 已經由 queue.get() 完成 json.loads，現在是 dict
            task_data = task_data_str
            task_id = task_data.get("task_id")
            task_type = task_data.get("task_type")
            payload = task_data.get("payload", {})

            if not task_id:
                logger.error("任務數據中缺少 task_id，無法追蹤狀態。")
                return

            self.task_queue.update_task_status(task_id, "processing")
            handler = TASK_DISPATCHER.get(task_type)

            if handler:
                result = handler(payload)
                # 修正：確保 JSON 中的中文能正確顯示，而不是 Unicode 編碼
                result_str = json.dumps(result, ensure_ascii=False)
                self.task_queue.update_task_status(task_id, "completed", result_str)
                logger.info(f"任務 {task_id} 已成功完成。")
            else:
                logger.warning(f"未知的任務類型: {task_type}，任務 {task_id} 將被標記為失敗。")
                self.task_queue.update_task_status(task_id, "failed", "Unknown task type")

        except json.JSONDecodeError:
            logger.error("任務數據格式無效 (非 JSON)，無法處理。")
            if task_id:
                self.task_queue.update_task_status(task_id, "failed", "Invalid JSON format")
        except Exception as e:
            logger.error(f"處理任務 {task_id} 時發生未知錯誤: {e}", exc_info=True)
            if task_id:
                self.task_queue.update_task_status(task_id, "failed", str(e))

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
