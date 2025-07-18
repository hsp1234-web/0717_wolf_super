import os
import json
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.models.snapshot_models import (
    Factor, ShanJiaLangInitialData, AIAnalysisRequest, BacktestRequest
)
from src.prometheus.core.analysis.mock_data_engine import MockDataEngine

app = FastAPI(
    title="作戰司令部 API",
    description="用於接收分析指令並查詢任務結果的輕量級 API 伺服器。",
    version="1.5.0",
)

# --- 模型定義 ---
class TaskResponse(BaseModel):
    message: str
    task_id: str

class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]]
    created_at: float
    updated_at: float

# --- 核心服務與依賴注入 ---
def get_db_path():
    return os.getenv('DB_PATH', 'data/prometheus.db')

def get_task_queue(db_path: str = Depends(get_db_path)) -> SQLiteQueue:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return SQLiteQueue(db_path)

def get_mock_engine() -> MockDataEngine:
    return MockDataEngine()

# --- API 端點定義 ---
@app.get("/health", tags=["系統監控"])
def health_check(): return {"status": "作戰司令部 API 正常運行"}

@app.get("/api/v1/market_snapshot", response_model=List[Factor], tags=["市場數據"])
def get_market_snapshot(mock_engine: MockDataEngine = Depends(get_mock_engine)):
    try: return mock_engine.get_market_factors()
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/shan_jia_lang/initial_data", response_model=ShanJiaLangInitialData, tags=["情報融合"])
def get_shan_jia_lang_initial_data(mock_engine: MockDataEngine = Depends(get_mock_engine)):
    try: return mock_engine.get_shan_jia_lang_initial_data()
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ai/initial_analysis", response_model=TaskResponse, tags=["情報融合"])
def post_ai_analysis(request: AIAnalysisRequest, task_queue: SQLiteQueue = Depends(get_task_queue)):
    try:
        task_id = task_queue.put(task_type='initial_analysis', payload=request.model_dump())
        return {"message": "AI 分析任務已成功提交", "task_id": task_id}
    except Exception as e: raise HTTPException(status_code=500, detail=f"提交 AI 分析任務時發生錯誤: {str(e)}")

@app.get("/api/v1/task/result/{task_id}", response_model=TaskResultResponse, tags=["任務調度"])
def get_task_result(task_id: str, task_queue: SQLiteQueue = Depends(get_task_queue)):
    task_info = task_queue.get_task(task_id)
    if not task_info: raise HTTPException(status_code=404, detail="找不到指定的任務 ID")
    result_payload = json.loads(task_info['result']) if task_info.get('result') else None
    return TaskResultResponse(
        task_id=task_info['task_id'], status=task_info['status'], result=result_payload,
        created_at=task_info['created_at'], updated_at=task_info['updated_at']
    )

# 新增的 API 端點
@app.post("/api/v1/backtest/run", response_model=TaskResponse, tags=["策略回測"])
def run_backtest(request: BacktestRequest, task_queue: SQLiteQueue = Depends(get_task_queue)):
    """
    接收策略程式碼並建立一個回測任務。
    """
    try:
        task_id = task_queue.put(
            task_type='backtest',
            payload=request.model_dump()
        )
        return {"message": "策略回測任務已成功提交", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交回測任務時發生錯誤: {str(e)}")
