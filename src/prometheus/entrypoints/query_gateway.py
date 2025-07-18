import json
import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

# 導入進化後的 DataEngine
from src.prometheus.core.analysis.data_engine import DataEngine
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.models.snapshot_models import AIAnalysisRequest, BacktestRequest, Factor

app = FastAPI(title="作戰司令部 API", version="1.7.0 (心臟移植版)")


# --- 模型定義 (與之前相同的部分可以保留) ---
class TaskResponse(BaseModel):
    message: str
    task_id: str


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]]
    created_at: float
    updated_at: float


from src.prometheus.core.db.data_warehouse import DataWarehouse  # 導入

app = FastAPI(title="作戰司令部 API", version="1.8.0 (金剛之軀)")


# --- 核心服務與依賴注入 ---
def get_db_path():
    return os.getenv("DB_PATH", "data/prometheus.db")


def get_warehouse_path():
    return os.getenv("WAREHOUSE_PATH", "data/warehouse.duckdb")


def get_task_queue(db_path: str = Depends(get_db_path)) -> SQLiteQueue:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return SQLiteQueue(db_path)


def get_data_warehouse(warehouse_path: str = Depends(get_warehouse_path)) -> DataWarehouse:
    return DataWarehouse(warehouse_path)


def get_data_engine(
    queue: SQLiteQueue = Depends(get_task_queue), warehouse: DataWarehouse = Depends(get_data_warehouse)
) -> DataEngine:
    return DataEngine(queue, warehouse)


# --- API 端點定義 ---
@app.get("/health", tags=["系統監控"])
def health_check():
    return {"status": "作戰司令部 API 正常運行"}


@app.get("/api/v1/market_snapshot", response_model=List[Factor], tags=["市場數據"])
def get_market_snapshot(data_engine: DataEngine = Depends(get_data_engine)):
    try:
        factors = data_engine.get_market_factors()
        if not factors:
            raise HTTPException(status_code=503, detail="數據源暫時無法訪問或未返回任何數據。")
        return factors
    except Exception as e:
        # 記錄詳細錯誤以供調試
        print(f"獲取市場數據時發生嚴重錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"獲取市場數據時發生嚴重錯誤: {str(e)}")


# 保留其他任務提交和結果查詢的端點
@app.post("/api/v1/ai/initial_analysis", response_model=TaskResponse, tags=["情報融合"])
def post_ai_analysis(request: AIAnalysisRequest, tq: SQLiteQueue = Depends(get_task_queue)):
    try:
        task_id = tq.put(task_type="initial_analysis", payload=request.model_dump())
        return {"message": "AI 分析任務已成功提交", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交 AI 分析任務時發生錯誤: {str(e)}")


@app.post("/api/v1/backtest/run", response_model=TaskResponse, tags=["策略回測"])
def run_backtest(request: BacktestRequest, tq: SQLiteQueue = Depends(get_task_queue)):
    try:
        task_id = tq.put(task_type="backtest", payload=request.model_dump())
        return {"message": "策略回測任務已成功提交", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交回測任務時發生錯誤: {str(e)}")


@app.get("/api/v1/task/result/{task_id}", response_model=TaskResultResponse, tags=["任務調度"])
def get_task_result(task_id: str, tq: SQLiteQueue = Depends(get_task_queue)):
    task_info = tq.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="找不到指定的任務 ID")
    result_payload = json.loads(task_info.get("result", "{}")) if task_info.get("result") else None
    return TaskResultResponse(
        task_id=task_info["task_id"],
        status=task_info["status"],
        result=result_payload,
        created_at=task_info["created_at"],
        updated_at=task_info["updated_at"],
    )
