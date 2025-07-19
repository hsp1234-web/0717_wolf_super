import json
import os
import traceback
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.prometheus.core.clients.client_factory import ClientFactory
from src.prometheus.core.db.data_warehouse import DataWarehouse
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue

# 導入新的核心服務
from src.prometheus.core.services import PrometheusService
from src.prometheus.models.snapshot_models import Factor
from src.prometheus.models.strategy_models import Strategy
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="作戰司令部 API", version="2.0.0 (單一核心)")

# 取得 web 目錄的絕對路徑
web_dir = os.path.join(os.path.dirname(__file__), '..', 'web')

# 掛載靜態文件目錄
app.mount("/static", StaticFiles(directory=web_dir), name="static")


# --- 作戰情報中心：全域錯誤攔截中介軟體 ---
@app.middleware("http")
async def error_trapping_middleware(request: Request, call_next):
    """
    這個中介軟體會攔截所有 HTTP 請求，並在發生未處理的伺服器錯誤時，
    以結構化的 JSON 格式回傳詳細的錯誤情報，而不是 HTML 錯誤頁面。
    """
    try:
        return await call_next(request)
    except Exception as e:
        # 獲取詳細的堆疊追蹤資訊
        tb_str = traceback.format_exc()
        # 在伺服器日誌中記錄完整的錯誤
        # logger.error("Unhandled exception: %s", tb_str)
        # 回傳一個標準化的 JSON 錯誤回應
        return JSONResponse(
            status_code=500,
            content={
                "error": "一個無法預期的內部錯誤發生了。",
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "traceback": tb_str.splitlines(),
            },
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
    return "data/prometheus.db"


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
    cache_only: bool = False,
) -> PrometheusService:
    """提供一個 PrometheusService 實例。"""
    return PrometheusService(
        queue=queue,
        warehouse=warehouse,
        client_factory=client_factory,
        cache_only=cache_only,
    )


# --- API 端點定義 ---
@app.get("/health", tags=["系統監控"])
def health_check():
    return {"status": "作戰司令部 API 正常運行 (v2.0 單一核心)"}


@app.get("/api/v1/market_snapshot", response_model=List[Factor], tags=["市場數據"])
def get_market_snapshot(cache_only: bool = False, service: PrometheusService = Depends(get_prometheus_service)):
    """
    獲取市場快照。

    此端點現在是 PrometheusService.get_market_snapshot() 的一個簡單代理。
    """
    print(f"Received cache_only parameter: {cache_only}")  # 添加日誌
    try:
        # 這裡我們需要重新獲取一個 service，並傳入 cache_only 參數
        service.cache_only = cache_only
        factors = service.get_market_snapshot()
        if not factors:
            raise HTTPException(status_code=503, detail="數據源暫時無法訪問或未返回任何數據。")
        return factors
    except Exception as e:
        print(f"獲取市場數據時發生嚴重錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"獲取市場數據時發生嚴重錯誤: {str(e)}")


@app.post("/api/v1/task/backtest", response_model=TaskResponse, tags=["策略回測"])
def post_backtest(strategy: Strategy, cache_only: bool = False, tq: SQLiteQueue = Depends(get_task_queue)):
    """提交一個回測任務。"""
    print(f"Received backtest request with cache_only={cache_only}")
    if strategy.id == "trigger_error":
        raise ValueError("這是一個用於測試的故意引發的錯誤。")
    try:
        payload = {
            "strategy": strategy.dict(),
            "cache_only": cache_only,
        }
        task_id = tq.put(task_type="backtest", payload=payload)
        return {"message": "回測任務已成功提交", "task_id": task_id}
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        print(f"Error in post_backtest: {e}\n{tb_str}")
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb_str})


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
