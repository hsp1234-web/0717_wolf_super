import time
import os
import traceback
import random
import sys

# 假設此 worker 檔案在專案根目錄下
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
# from src.prometheus.core.logging.log_manager import LogManager # 暫不使用

def process_initial_analysis(payload):
    """
    模擬 AI 進行初步分析。
    """
    time.sleep(1) # 模擬 AI 思考時間
    raw_content = payload.get('raw_content', '')
    selected_masters = payload.get('selected_masters', [])
    analysis_summary = f"已分析文本，長度為 {len(raw_content)} 字元。"
    if selected_masters:
        analysis_summary += f" 已融合 {len(selected_masters)} 位大師的觀點: {', '.join(selected_masters)}。"
    return { "summary": analysis_summary, "strategy_suggestion": "建議採取「VIX 波動率擴大」相關策略。" }

def process_backtest(payload):
    """
    模擬執行一個策略回測。
    在真實世界中，這裡會呼叫一個複雜的回測引擎。
    """
    time.sleep(3) # 模擬回測運算時間
    strategy_name = payload.get('strategy_name', '未命名策略')

    # 生成模擬的績效數據
    equity_curve = [100]
    for _ in range(100):
        equity_curve.append(equity_curve[-1] * (1 + random.uniform(-0.02, 0.025)))

    return {
        "strategy_name": strategy_name,
        "annualized_return": round(random.uniform(5.0, 25.0), 2),
        "max_drawdown": round(random.uniform(-8.0, -20.0), 2),
        "sharpe_ratio": round(random.uniform(0.8, 2.5), 2),
        "win_rate": round(random.uniform(0.45, 0.65), 2),
        "equity_curve": equity_curve
    }

def main():
    db_path = os.getenv('DB_PATH', 'data/prometheus.db')
    queue = SQLiteQueue(db_path)
    worker_id = f"worker-{os.getpid()}"
    print(f"堅韌工人 {worker_id} 已啟動...")

    task_processors = {
        'initial_analysis': process_initial_analysis,
        'backtest': process_backtest
    }

    while True:
        try:
            task = queue.get()
            if task:
                task_id, task_type, payload = task
                print(f"接收到任務 {task_id} (類型: {task_type})")
                try:
                    processor = task_processors.get(task_type)
                    if processor:
                        result = processor(payload)
                    else:
                        print(f"未知的任務類型: {task_type}")
                        result = {"error": f"未知的任務類型: {task_type}"}

                    print(f"任務 {task_id} 執行成功。")
                    queue.update_task(task_id, 'completed', result)
                except Exception as e:
                    error_message = f"任務 {task_id} 執行失敗: {e}"
                    print(error_message)
                    print(traceback.format_exc())
                    queue.update_task(task_id, 'failed', {'error': error_message})
            else:
                time.sleep(1)
        except Exception as e:
            print(f"工人主循環發生嚴重錯誤: {e}")
            print(traceback.format_exc())
            time.sleep(5)

if __name__ == "__main__":
    main()
