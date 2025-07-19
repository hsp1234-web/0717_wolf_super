# tests/test_api_contract.py
"""
API 功能契約 - 驗證「普羅米修斯之腦」API 的所有行為。

這份腳本是我們的「唯一真相來源」，確保後端服務遵守「API 聖約」。
"""
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
import sys
import os

# 確保 'src' 目錄在 Python 的搜尋路徑中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from prometheus.entrypoints.olympus_api import app, tasks_db, TaskStatusEnum

# 將測試客戶端標記為異步
@pytest.mark.asyncio
async def test_start_training_success(mocker):
    """
    驗證 POST /api/start-training 在收到正確參數時，能成功回傳一個格式正確的 task_id。
    """
    # 模擬 background_tasks.add_task 以避免實際執行
    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 清空之前的任務紀錄以確保測試獨立性
        tasks_db.clear()

        payload = {
            "model_name": "ZeusNetV3",
            "hyperparameters": {"learning_rate": 0.01},
            "dataset_id": "Crypto_OHLCV_2025_Q2"
        }
        response = await client.post("/api/start-training", json=payload)

        # 驗證 HTTP 狀態碼
        assert response.status_code == status.HTTP_202_ACCEPTED

        # 驗證回應的 JSON 結構與內容
        data = response.json()
        assert "task_id" in data
        assert isinstance(data["task_id"], str)
        assert data["message"] == "訓練任務已成功啟動"

        # 驗證任務是否已在後端資料庫中創建
        task_id = data["task_id"]
        assert task_id in tasks_db
        assert tasks_db[task_id]["status"] == TaskStatusEnum.QUEUED

        # 驗證 add_task 是否被呼叫
        mock_add_task.assert_called_once()

@pytest.mark.asyncio
async def test_start_training_validation_error():
    """
    驗證在傳入錯誤參數時（例如，缺少必要欄位），API 能回傳符合規範的 422 Unprocessable Entity 錯誤。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "model_name": "ZeusNetV3"
            # "dataset_id" 是必要欄位，此處故意遺漏
        }
        response = await client.post("/api/start-training", json=payload)

        # 驗證 HTTP 狀態碼
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 驗證 FastAPI 的詳細錯誤訊息
        error_data = response.json()
        assert "detail" in error_data
        assert error_data["detail"][0]["type"] == "missing"
        assert error_data["detail"][0]["loc"] == ["body", "dataset_id"]

@pytest.mark.asyncio
async def test_get_task_status_found():
    """
    驗證 GET /api/task-status/{task_id} 能回傳一個包含 status 欄位的正確 JSON 結構。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 手動在資料庫中創建一個任務以供測試
        tasks_db.clear()
        test_task_id = "test_id_123"
        tasks_db[test_task_id] = {"status": TaskStatusEnum.PROCESSING, "details": {"progress": 50}}

        response = await client.get(f"/api/task-status/{test_task_id}")

        # 驗證 HTTP 狀態碼
        assert response.status_code == status.HTTP_200_OK

        # 驗證回應的 JSON 結構與內容
        data = response.json()
        assert data["task_id"] == test_task_id
        assert data["status"] == "processing"
        assert data["details"]["progress"] == 50

import asyncio

@pytest.mark.asyncio
async def test_get_task_status_not_found():
    """
    驗證當查詢一個不存在的 task_id 時，API 會回傳 404 Not Found。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tasks_db.clear()
        response = await client.get("/api/task-status/non_existent_id")

        # 驗證 HTTP 狀態碼
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "找不到指定的任務 ID。"

@pytest.mark.asyncio
async def test_full_training_workflow():
    """
    執行一個完整的端到端工作流程：
    1. 啟動訓練任務。
    2. 輪詢任務狀態直到完成。
    3. 驗證最終狀態與進度。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 啟動訓練
        tasks_db.clear()
        payload = {
            "model_name": "HermesNet",
            "hyperparameters": {"epochs": 3}, # 使用較少的 epochs 以加速測試
            "dataset_id": "Test_Dataset"
        }
        response = await client.post("/api/start-training", json=payload)
        assert response.status_code == status.HTTP_202_ACCEPTED
        task_id = response.json()["task_id"]

        # 2. 輪詢狀態
        timeout = 15  # 總等待時間（秒）
        interval = 0.5  # 輪詢間隔（秒）
        elapsed = 0

        final_status = ""
        while elapsed < timeout:
            status_response = await client.get(f"/api/task-status/{task_id}")
            assert status_response.status_code == status.HTTP_200_OK
            current_status = status_response.json()["status"]

            if current_status == TaskStatusEnum.COMPLETED:
                final_status = current_status
                break

            print(f"當前狀態: {current_status}, 已等待 {elapsed:.1f} 秒...")
            await asyncio.sleep(interval)
            elapsed += interval

        # 3. 驗證最終結果
        assert final_status == TaskStatusEnum.COMPLETED, f"任務在 {timeout} 秒內未完成！"

        final_data = status_response.json()
        assert final_data["details"]["progress"] == 100

@pytest.mark.asyncio
async def test_get_task_result_completed():
    """
    驗證當任務成功完成時，GET /api/task-result/{task_id} 能回傳正確的結果。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tasks_db.clear()
        test_task_id = "task_completed_1"
        expected_result = {"accuracy": 0.99}
        tasks_db[test_task_id] = {"status": TaskStatusEnum.COMPLETED, "result": expected_result}

        response = await client.get(f"/api/task-result/{test_task_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == TaskStatusEnum.COMPLETED
        assert data["result"] == expected_result

@pytest.mark.asyncio
async def test_get_task_result_in_progress():
    """
    驗證當任務仍在進行中時，GET /api/task-result/{task_id} 會回傳提示訊息。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tasks_db.clear()
        test_task_id = "task_inprogress_1"
        tasks_db[test_task_id] = {"status": TaskStatusEnum.PROCESSING}

        response = await client.get(f"/api/task-result/{test_task_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == TaskStatusEnum.PROCESSING
        assert "仍在進行中" in data["message"]

@pytest.mark.asyncio
async def test_get_task_result_not_found():
    """
    驗證查詢不存在的任務結果時，GET /api/task-result/{task_id} 會回傳 404。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tasks_db.clear()
        response = await client.get("/api/task-result/non_existent_id")
        assert response.status_code == status.HTTP_404_NOT_FOUND
