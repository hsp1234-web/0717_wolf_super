import time
import os
import traceback
import sys

# 假設此 worker 檔案在專案根目錄下
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.core.logging.log_manager import LogManager

def process_initial_analysis(payload):
    """
    模擬 AI 進行初步分析。
    在真實世界中，這裡會呼叫一個大型語言模型。
    """
    time.sleep(2) # 模擬 AI 思考時間
    raw_content = payload.get('raw_content', '')
    selected_masters = payload.get('selected_masters', [])

    analysis_summary = f"已分析文本，長度為 {len(raw_content)} 字元。"
    if selected_masters:
        analysis_summary += f" 已融合 {len(selected_masters)} 位大師的觀點: {', '.join(selected_masters)}。"
    else:
        analysis_summary += " 未載入額外大師觀點。"

    return {
        "summary": analysis_summary,
        "strategy_suggestion": "基於當前情報，建議採取「VIX 波動率擴大」相關策略。"
    }

def main():
    db_path = os.getenv('DB_PATH', 'data/prometheus.db')
    queue = SQLiteQueue(db_path)
    # 在 worker 中使用 log_manager 可能會過於複雜，暫時使用 print
    # log_manager = LogManager(db_path)
    worker_id = f"worker-{os.getpid()}"
    # logger = log_manager.get_logger(worker_id)

    print(f"堅韌工人 {worker_id} 已啟動...")

    while True:
        try:
            task = queue.get()
            if task:
                task_id, task_type, payload = task
                print(f"接收到任務 {task_id} (類型: {task_type})")

                try:
                    result = None
                    if task_type == 'initial_analysis':
                        result = process_initial_analysis(payload)
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
