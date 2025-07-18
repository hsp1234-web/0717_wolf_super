import os
import random
import time
import traceback

from src.prometheus.core.queue.sqlite_queue import SQLiteQueue


# --- 裝備性能計時器 (裝飾器) ---
def timeit(queue, task_id, step_name):
    """一個裝飾器，用於計時函數執行時間並記錄到資料庫。"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            # 使用 queue 的日誌方法記錄性能
            queue.log_performance(task_id, step_name, duration)
            print(f"性能日誌: {task_id} - {step_name} - {duration:.4f} 秒")
            return result

        return wrapper

    return decorator


def process_initial_analysis(queue, task_id, payload):
    """模擬 AI 進行初步分析，並計時。"""

    @timeit(queue, task_id, "ai_analysis_processing")
    def timed_process():
        time.sleep(1)  # 模擬 AI 思考
        return {"summary": "分析完成", "strategy_suggestion": "..."}

    return timed_process()


def process_backtest(queue, task_id, payload):
    """模擬執行策略回測，並計時。"""

    @timeit(queue, task_id, "backtest_processing")
    def timed_process():
        # 模擬一個更真實的回測負載
        time.sleep(random.uniform(1.5, 2.5))  # 模擬回測運算
        return {
            "annualized_return": round(random.uniform(5.0, 15.0), 2),
            "max_drawdown": round(random.uniform(-10.0, -25.0), 2),
            "sharpe_ratio": round(random.uniform(0.7, 1.8), 2),
            "win_rate": round(random.uniform(0.50, 0.60), 2),
            "equity_curve": [100, 101, 102],  # 簡化曲線
        }

    return timed_process()


def main():
    db_path = os.getenv("DB_PATH", "data/prometheus.db")
    queue = SQLiteQueue(db_path)
    # LogManager 暫時不用，但保留接口
    # log_manager = LogManager(db_path)
    worker_id = f"worker-{os.getpid()}"
    # logger = log_manager.get_logger(worker_id)
    print(f"堅韌工人 {worker_id} 已啟動，連接到 {db_path}")

    task_processors = {"initial_analysis": process_initial_analysis, "backtest": process_backtest}

    while True:
        task = queue.get()
        if task:
            task_id, task_type, payload = task
            print(f"工人 {worker_id} 接收到任務 {task_id} (類型: {task_type})")
            try:
                processor = task_processors.get(task_type)
                if processor:
                    # 將 queue 和 task_id 傳遞給處理函數
                    result = processor(queue, task_id, payload)
                    queue.update_task(task_id, "completed", result)
                    print(f"工人 {worker_id} 任務 {task_id} 執行成功。")
                else:
                    error_msg = f"未知的任務類型: {task_type}"
                    print(error_msg)
                    queue.update_task(task_id, "failed", {"error": error_msg})
            except Exception as e:
                error_message = f"任務 {task_id} 執行期間發生錯誤: {e}"
                print(error_message)
                print(traceback.format_exc())
                queue.update_task(task_id, "failed", {"error": error_message})
        else:
            # 縮短休眠以提高響應速度，並加入微小的隨機性以避免活鎖
            time.sleep(random.uniform(0.05, 0.15))


if __name__ == "__main__":
    # 確保在多進程環境下能找到 src 模組
    # 這在從根目錄執行 `python real_worker.py` 時是必需的
    import sys

    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    main()
