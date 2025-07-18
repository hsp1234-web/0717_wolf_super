import asyncio
import os
import sqlite3
import subprocess
import time

import httpx
import matplotlib.pyplot as plt
import pandas as pd
import psutil
import pytest

# --- 測試參數 ---
DB_PATH = "data/stress_test.db"
API_URL = "http://127.0.0.1:8000"
NUM_TASKS = 20  # 要併發提交的任務總數
CONCURRENCY = 5  # 併發請求數
NUM_WORKERS = 2  # 啟動的工人數量


@pytest.fixture(scope="module")
def setup_stress_test_environment():
    """在所有測試前，清理、建立目錄、啟動後端服務"""
    # 確保 data 目錄存在
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    os.environ["DB_PATH"] = DB_PATH

    # 啟動 API 伺服器
    api_server = subprocess.Popen(
        ["uvicorn", "src.prometheus.entrypoints.query_gateway:app", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # 啟動工人
    workers = [
        subprocess.Popen(["python", "real_worker.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(NUM_WORKERS)
    ]

    time.sleep(3)  # 等待服務啟動

    yield  # 執行測試

    # 測試結束後，清理所有進程
    api_server.terminate()
    for worker in workers:
        worker.terminate()
    api_server.wait()
    for worker in workers:
        worker.wait()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


async def hardware_monitor(stop_event):
    """背景硬體監控任務"""
    # 延遲導入以避免在 pytest 收集期間出錯
    from src.prometheus.core.queue.sqlite_queue import SQLiteQueue

    queue = SQLiteQueue(DB_PATH)
    while not stop_event.is_set():
        # 獲取活躍的 worker 數量 (這是一個簡化的範例)
        active_workers = NUM_WORKERS
        queue.log_hardware(psutil.cpu_percent(), psutil.virtual_memory().percent, active_workers)
        try:
            # 使用 await asyncio.sleep 讓出控制權
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break


@pytest.mark.stress
@pytest.mark.asyncio
async def test_high_concurrency_workload(setup_stress_test_environment):
    """壓力測試主函數"""
    print("\n--- 🚀 開始壓力測試 ---")

    # 啟動硬體監控
    stop_monitor = asyncio.Event()
    monitor_task = asyncio.create_task(hardware_monitor(stop_monitor))

    start_time = time.time()

    async with httpx.AsyncClient(base_url=API_URL, timeout=30) as client:
        # 建立併發提交任務的信號量
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def submit_task(i):
            async with semaphore:
                # 根據 BacktestRequest 模型，我們需要提供 strategy_code
                payload = {"strategy_code": f"code_{i}", "strategy_name": f"stress_test_{i}"}
                try:
                    # 使用正確的端點 /api/v1/backtest/run
                    response = await client.post("/api/v1/backtest/run", json=payload)
                    response.raise_for_status()  # 確保請求成功
                    return response
                except httpx.RequestError as e:
                    print(f"請求錯誤: {e}")
                    return None

        tasks = [submit_task(i) for i in range(NUM_TASKS)]
        responses = await asyncio.gather(*tasks)

    task_ids = [r.json()["task_id"] for r in responses if r and r.status_code == 200]
    print(f"✅ {len(task_ids)} 個任務已成功提交。")

    # 如果沒有任務成功提交，測試就沒有意義了
    if not task_ids:
        pytest.fail("沒有任何任務成功提交，請檢查 API 服務和端點。")

    # 等待所有任務完成
    print("⏳ 等待所有任務完成...")
    conn = sqlite3.connect(DB_PATH)
    while True:
        try:
            # 查詢特定 task_id 的完成狀態
            completed_count = pd.read_sql_query(
                f"SELECT COUNT(*) FROM tasks WHERE status = 'completed' AND task_id IN ({','.join(['?']*len(task_ids))})",
                conn,
                params=task_ids,
            ).iloc[0, 0]
            if completed_count >= len(task_ids):
                print(f"✅ 所有 {len(task_ids)} 個任務已完成。")
                break
        except (pd.io.sql.DatabaseError, sqlite3.OperationalError) as e:
            print(f"讀取資料庫時發生錯誤: {e}, 稍後重試...")
            pass
        await asyncio.sleep(1)

    end_time = time.time()
    total_duration = end_time - start_time

    # 停止硬體監控
    stop_monitor.set()
    try:
        await asyncio.wait_for(monitor_task, timeout=2.0)
    except asyncio.TimeoutError:
        monitor_task.cancel()  # 如果無法正常停止，則取消它

    # --- 生成報告 ---
    print("\n--- 📊 壓力測試報告 ---")
    print(f"總耗時: {total_duration:.2f} 秒")
    if total_duration > 0:
        print(f"系統吞吐量: {NUM_TASKS / total_duration:.2f} 任務/秒")

    # 性能分析
    try:
        df_perf = pd.read_sql_query("SELECT * FROM performance_logs", conn)
        if not df_perf.empty:
            print("\n任務處理時間分析 (秒):")
            print(df_perf["duration"].describe())
        else:
            print("\n沒有可用的性能日誌。")
    except pd.io.sql.DatabaseError:
        print("\n無法讀取性能日誌。")

    # 硬體分析
    try:
        df_hw = pd.read_sql_query("SELECT * FROM hardware_logs", conn)
        if not df_hw.empty:
            print("\n硬體資源使用分析:")
            print(df_hw[["cpu_percent", "ram_percent"]].describe())

            # 繪製圖表
            fig, ax1 = plt.subplots(figsize=(12, 6))
            ax1.set_xlabel("時間 (秒)")
            ax1.set_ylabel("CPU 使用率 (%)", color="tab:red")
            # 計算相對時間
            relative_time = df_hw["timestamp"] - df_hw["timestamp"].min()
            ax1.plot(relative_time, df_hw["cpu_percent"], color="tab:red", label="CPU Usage")
            ax1.tick_params(axis="y", labelcolor="tab:red")
            ax1.grid(True, axis="y", linestyle="--", alpha=0.7)

            ax2 = ax1.twinx()
            ax2.set_ylabel("RAM 使用率 (%)", color="tab:blue")
            ax2.plot(relative_time, df_hw["ram_percent"], color="tab:blue", label="RAM Usage")
            ax2.tick_params(axis="y", labelcolor="tab:blue")

            fig.tight_layout()
            plt.title("壓力測試期間系統資源使用圖")
            plt.legend()
            report_path = "stress_test_report.png"
            plt.savefig(report_path)
            print(f"\n📈 性能圖表已生成: {report_path}")
        else:
            print("\n沒有可用的硬體日誌。")
    except pd.io.sql.DatabaseError:
        print("\n無法讀取硬體日誌。")

    conn.close()
    assert total_duration > 0, "測試持續時間應大於零"
    # 增加一個斷言，確保至少有一些任務被處理
    assert len(task_ids) > 0, "應成功提交至少一個任務"
