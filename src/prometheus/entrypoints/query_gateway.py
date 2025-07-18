import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

# 由於 'src.prometheus' 的路徑問題，我們需要調整導入方式
# 這是一個常見的 Python 路徑問題，當從專案根目錄執行時會發生
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.models.snapshot_models import Factor
from src.prometheus.core.analysis.mock_data_engine import MockDataEngine

# 初始化 FastAPI 應用
app = FastAPI(
    title="作戰司令部 API",
    description="用於接收分析指令並查詢任務結果的輕量級 API 伺服器。",
    version="1.2.0",
)

# --- 模型定義 (僅為 API 文件所需，與佇列無關) ---
class TaskRequest(BaseModel):
    task_type: str = Field(..., description="任務的類型")
    payload: Optional[Dict[str, Any]] = Field(None, description="任務參數")

class TaskResponse(BaseModel):
    message: str
    task_id: str

# --- 初始化核心服務 ---
# 在實際應用中，DB_PATH 可能來自環境變數或設定檔
# 為了讓測試和執行更穩定，我們先寫死路徑
# 注意：這在生產環境中可能需要更改
if not os.path.exists('data'):
    os.makedirs('data')
DB_PATH = os.getenv('DB_PATH', 'data/prometheus.db')
task_queue = SQLiteQueue(DB_PATH)
mock_engine = MockDataEngine()

# --- API 端點定義 ---

@app.get("/health", tags=["系統監控"])
def health_check():
    """ 提供一個簡單的健康檢查端點。 """
    return {"status": "作戰司令部 API 正常運行"}

@app.post("/api/v1/submit_task", response_model=TaskResponse, tags=["任務調度"])
def submit_task(request: TaskRequest):
    """ 接收一個新的分析任務，並將其放入佇列。 """
    try:
        # 根據 SQLiteQueue 的實現，我們只傳遞 task_type 和 payload
        task_id = task_queue.put(request.task_type, request.payload)
        return {"message": "任務已成功提交", "task_id": task_id}
    except Exception as e:
        # 增加日誌記錄，以便於除錯
        import logging
        logging.error(f"提交任務時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交任務時發生錯誤: {e}")

@app.get("/api/v1/market_snapshot", response_model=List[Factor], tags=["市場數據"])
def get_market_snapshot():
    """ 提供「市場數據總覽」頁面所需的所有因子數據。 """
    try:
        factors = mock_engine.get_market_factors()
        return factors
    except Exception as e:
        import logging
        logging.error(f"獲取市場數據時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"獲取市場數據時發生錯誤: {str(e)}")
