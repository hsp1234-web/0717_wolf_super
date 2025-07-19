# src/prometheus/entrypoints/olympus_api.py
"""
普羅米修斯之腦 - API 聖約與任務控制核心
"""
import uuid
import time
from enum import Enum
from typing import Dict, Any, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

# --- API 聖約：資料模型 (Pydantic Models) ---
# 這些模型定義了客戶端與 API 之間通訊的數據結構。
# 它們是我們「活的儀表板」的基礎。

class TrainingRequest(BaseModel):
    """
    啟動一個新訓練任務的請求主體。
    """
    model_name: str = Field(
        ...,
        description="要訓練的 AI 模型名稱。",
        json_schema_extra={"example": "ZeusNetV3"}
    )
    hyperparameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="模型的超參數字典。",
        json_schema_extra={"example": {"learning_rate": 0.001, "epochs": 100}}
    )
    dataset_id: str = Field(
        ...,
        description="用於訓練的數據集唯一標識符。",
        json_schema_extra={"example": "Crypto_OHLCV_2025_Q2"}
    )

class TrainingResponse(BaseModel):
    """
    成功啟動訓練任務後的回應。
    """
    task_id: str = Field(..., description="新建立的背景任務的唯一 ID。", json_schema_extra={"example": "a1b2c3d4-e5f6-7890-1234-567890abcdef"})
    message: str = Field("訓練任務已成功啟動", description="提供給使用者的確認訊息。")

class TaskStatusEnum(str, Enum):
    """
    任務狀態的枚舉類型。
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStatusResponse(BaseModel):
    """
    查詢特定任務狀態的回應。
    """
    task_id: str = Field(..., description="所查詢任務的唯一 ID。")
    status: TaskStatusEnum = Field(..., description="任務的當前狀態。")
    details: Optional[Dict[str, Any]] = Field(None, description="關於任務進度的可選詳細資訊，例如進度百分比或當前 loss。")


# --- 任務控制核心：記憶體資料庫 ---
# 一個簡單的字典，用於在記憶體中存儲和追蹤任務的狀態。
# 在生產環境中，這可能會被 Redis 或資料庫取代。
tasks_db: Dict[str, Dict[str, Any]] = {}


# --- 應用程式實例 ---
# 這是我們的 FastAPI 應用程式，即「普羅米修斯之腦」的最高法律。
app = FastAPI(
    title="普羅米修斯之腦 API",
    description="為「奧林帕斯計畫」提供非同步 AI 訓練任務的核心服務。",
    version="1.0.0",
)


# --- API 端點：任務控制 (Mission Control) ---

def run_simulated_training(task_id: str, model_name: str, hyperparameters: Dict):
    """
    一個模擬的 AI 訓練函數，用於在背景執行。
    它會逐步更新任務狀態，模擬一個真實的訓練過程。
    """
    print(f"任務 {task_id}: 開始訓練模型 {model_name}...")

    # 1. 將狀態更新為「處理中」
    tasks_db[task_id]["status"] = TaskStatusEnum.PROCESSING
    tasks_db[task_id]["details"] = {"progress": 0, "current_loss": 1.0}
    time.sleep(2) # 模擬數據準備

    # 2. 模擬訓練迴圈
    total_epochs = hyperparameters.get("epochs", 10)
    for epoch in range(total_epochs):
        progress = int(((epoch + 1) / total_epochs) * 100)
        loss = 1.0 - (progress / 100.0)
        tasks_db[task_id]["details"] = {"progress": progress, "current_loss": round(loss, 4)}
        print(f"任務 {task_id}: 進度 {progress}%, 當前 Loss: {loss:.4f}")
        time.sleep(0.5) # 模擬每個 epoch 的計算時間

    # 3. 訓練完成
    tasks_db[task_id]["status"] = TaskStatusEnum.COMPLETED
    tasks_db[task_id]["result"] = {
        "final_loss": 0.0,
        "accuracy": 0.98,
        "model_path": f"/models/{model_name}_{task_id}.pt"
    }
    print(f"任務 {task_id}: 訓練完成。")


@app.post("/api/start-training", response_model=TrainingResponse, status_code=202)
async def start_training(
    request: TrainingRequest, background_tasks: BackgroundTasks
):
    """
    啟動一個新的 AI 模型訓練任務。

    這是一個非同步端點：
    1. 它會立即接受請求並回傳一個 `task_id`。
    2. 真正的訓練過程將在背景執行。
    """
    task_id = str(uuid.uuid4())
    # 在資料庫中創建任務紀錄
    tasks_db[task_id] = {"status": TaskStatusEnum.QUEUED, "details": {}}

    # 將真正的訓練函數添加到背景任務佇列
    background_tasks.add_task(
        run_simulated_training,
        task_id,
        request.model_name,
        request.hyperparameters
    )

    return TrainingResponse(task_id=task_id)


@app.get("/api/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    根據 `task_id` 查詢特定任務的當前狀態。
    """
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="找不到指定的任務 ID。")

    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        details=task.get("details")
    )


@app.get("/api/task-result/{task_id}")
async def get_task_result(task_id: str):
    """
    獲取已完成任務的最終結果。

    - 如果任務正在進行中，會提示使用者稍後再試。
    - 如果任務失敗，會提供錯誤訊息。
    - 如果任務成功，會回傳訓練結果。
    """
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="找不到指定的任務 ID。")

    if task["status"] == TaskStatusEnum.COMPLETED:
        return {"task_id": task_id, "status": task["status"], "result": task.get("result", "沒有可用的結果。")}
    elif task["status"] == TaskStatusEnum.FAILED:
        return {"task_id": task_id, "status": task["status"], "error": task.get("error", "未知的錯誤。")}
    else:
        return {"task_id": task_id, "status": task["status"], "message": "任務仍在進行中，請稍後再查詢結果。"}
