# tests/conftest.py
import pytest
import subprocess
import time
import os

# 由於我們使用了 pytest，sys.path 的問題由 pytest.ini 處理
from prometheus.core.constants import DB_PATH, LOG_PATH

@pytest.fixture(scope="session")
def live_services():
    """
    一個統一的、session 等級的 fixture，負責 E2E 測試的服務啟動與關閉。
    1. 清理舊的日誌和數據庫。
    2. 在測試環境下，同時啟動 API 伺服器和一個工人進程。
    3. 驗證服務都已成功啟動。
    4. 在測試結束後，終止所有服務。
    """
    # --- 1. 戰場準備 ---
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

    # --- 2. 啟動服務 ---
    test_env = os.environ.copy()
    test_env['PROMETHEUS_ENV'] = 'test'
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    src_path = os.path.join(project_root, 'src')
    test_env["PYTHONPATH"] = src_path + os.pathsep + test_env.get("PYTHONPATH", "")

    server_process, worker_process = None, None
    try:
        print("\n[Fixture Setup] 正在『作戰演習模式』下啟動所有服務...")

        server_cmd = ["poetry", "run", "python", "-m", "prometheus.cli.main", "dashboard"]
        server_process = subprocess.Popen(server_cmd, env=test_env, cwd=project_root)

        worker_cmd = ["poetry", "run", "python", "real_worker.py"]
        worker_process = subprocess.Popen(worker_cmd, env=test_env, cwd=project_root)

        # --- 3. 健康檢查 ---
        print("[Fixture Setup] 等待 5 秒，讓服務穩定...")
        time.sleep(5)

        if server_process.poll() is not None:
            pytest.fail("API 伺服器未能啟動！")
        if worker_process.poll() is not None:
            pytest.fail("工人程序未能啟動！")

        print("[Fixture Setup] 所有作戰單位均已成功啟動。")

        yield server_process, worker_process

    finally:
        # --- 4. 戰場清理 ---
        print("\n[Fixture Teardown] 正在發送關閉信號...")
        if server_process:
            server_process.terminate()
        if worker_process:
            worker_process.terminate()

        if server_process:
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
        if worker_process:
            try:
                worker_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker_process.kill()

        print("[Fixture Teardown] 所有服務已關閉。")
