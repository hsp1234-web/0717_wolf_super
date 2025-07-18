import json
import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from src.prometheus.core.clients.client_factory import ClientFactory
from src.prometheus.core.db.data_warehouse import DataWarehouse
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue

# 導入新的核心服務
from src.prometheus.core.services import PrometheusService
from src.prometheus.models.snapshot_models import Factor
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="作戰司令部 API", version="2.0.0 (單一核心)")

# 取得 web 目錄的絕對路徑
web_dir = os.path.join(os.path.dirname(__file__), '..', 'web')

# 掛載靜態文件目錄
app.mount("/static", StaticFiles(directory=web_dir), name="static")


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
    return os.getenv("DB_PATH", "data/prometheus.db")


def get_warehouse_path():
    return os.getenv("WAREHOUSE_PATH", "data/warehouse.duckdb")


def get_task_queue(db_path: str = Depends(get_db_path)) -> SQLiteQueue:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return SQLiteQueue(db_path)


def get_data_warehouse(warehouse_path: str = Depends(get_warehouse_path)) -> DataWarehouse:
    return DataWarehouse(warehouse_path)


def get_client_factory() -> ClientFactory:
    # 這裡可以擴展為從配置中讀取 API 金鑰
    return ClientFactory()


def get_prometheus_service(
    queue: SQLiteQueue = Depends(get_task_queue),
    warehouse: DataWarehouse = Depends(get_data_warehouse),
    client_factory: ClientFactory = Depends(get_client_factory),
) -> PrometheusService:
    """提供一個 PrometheusService 實例。"""
    return PrometheusService(queue=queue, warehouse=warehouse, client_factory=client_factory)


# --- API 端點定義 ---
@app.get("/health", tags=["系統監控"])
def health_check():
    return {"status": "作戰司令部 API 正常運行 (v2.0 單一核心)"}


@app.get("/api/v1/market_snapshot", response_model=List[Factor], tags=["市場數據"])
def get_market_snapshot(service: PrometheusService = Depends(get_prometheus_service)):
    """
    獲取市場快照。

    此端點現在是 PrometheusService.get_market_snapshot() 的一個簡單代理。
    """
    try:
        factors = service.get_market_snapshot()
        if not factors:
            raise HTTPException(status_code=503, detail="數據源暫時無法訪問或未返回任何數據。")
        return factors
    except Exception as e:
        print(f"獲取市場數據時發生嚴重錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"獲取市場數據時發生嚴重錯誤: {str(e)}")


@app.post("/api/v1/task/stress_index_analysis", response_model=TaskResponse, tags=["情報融合"])
def post_stress_index_analysis(tq: SQLiteQueue = Depends(get_task_queue)):
    """提交一個壓力指數分析任務。"""
    try:
        # 這裡的 payload 可以是空的，因為任務類型本身就定義了操作
        task_id = tq.put(task_type="stress_index_analysis", payload={})
        return {"message": "壓力指數分析任務已成功提交", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交任務時發生錯誤: {str(e)}")


@app.post("/api/v1/task/factor_correlation_analysis", response_model=TaskResponse, tags=["情報融合"])
def post_factor_correlation_analysis(tq: SQLiteQueue = Depends(get_task_queue)):
    """提交一個因子相關性分析任務。"""
    try:
        task_id = tq.put(task_type="factor_correlation_analysis", payload={})
        return {"message": "因子相關性分析任務已成功提交", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交任務時發生錯誤: {str(e)}")


@app.get("/api/v1/task/result/{task_id}", response_model=TaskResultResponse, tags=["任務調度"])
def get_task_result(task_id: str, tq: SQLiteQueue = Depends(get_task_queue)):
    """
    根據任務 ID 獲取任務的狀態和結果。
    """
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
