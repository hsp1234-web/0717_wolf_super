# -*- coding: utf-8 -*-
import os
import subprocess
import atexit
import time
from typing import List
from pathlib import Path

# ==============================================================================
# 抽象層：服務管理器 (Abstraction Layer: Service Manager) - v2 (哨兵版)
# ==============================================================================
class ServiceManager:
    def __init__(self):
        self._processes: List[subprocess.Popen] = []
        self._log_dir = Path("logs")
        self._log_dir.mkdir(exist_ok=True)
        atexit.register(self.shutdown_all)
        print("✅ 服務管理器 (v2) 已初始化，日誌目錄已準備。")

    def launch(self, command: List[str], name: str, health_check_func=None):
        log_path = self._log_dir / f"{name}_startup.log"
        with open(log_path, 'w') as log_file:
            process = subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT)

        self._processes.append(process)
        print(f"🚀 正在發射【{name}】服務 (PID: {process.pid})...")

        # 給予服務啟動時間
        time.sleep(3)

        # 檢查進程是否在啟動時就已崩潰
        if process.poll() is not None:
            print(f"❌ 嚴重錯誤：【{name}】服務在啟動時立即失敗！")
            self._print_log_on_failure(log_path)
            raise RuntimeError(f"{name} service failed to start.")

        # 如果提供了健康檢查函式，則執行它
        if health_check_func:
            print(f"🔬 正在對【{name}】執行健康檢查...")
            if not health_check_func():
                print(f"❌ 嚴重錯誤：【{name}】未能通過健康檢查！")
                self._print_log_on_failure(log_path)
                raise RuntimeError(f"{name} service failed health check.")
            print(f"✅ 【{name}】已通過健康檢查。")

    def _print_log_on_failure(self, log_path: Path):
        print(f"--- 捕獲到的【黑盒子】啟動日誌 ({log_path.name}) ---")
        if log_path.exists():
            with open(log_path, 'r') as f:
                print(f.read())
        print("--- 日誌結束 ---")

    def shutdown_all(self):
        # ... (此函式邏輯與之前版本相同) ...
        for p in self._processes:
            if p.poll() is None:
                print(f"Terminating process {p.pid}...")
                p.terminate()
        for p in self._processes:
            p.wait()

# ==============================================================================
# 探針：健康檢查器 (Probe: Health Checker)
# ==============================================================================
def check_api_server_health() -> bool:
    """使用獨立的 check_health.py 腳本來探測 API 伺服器。"""
    try:
        # 設置超時以防止無限等待
        result = subprocess.run(
            ["poetry", "run", "python", "check_health.py"],
            capture_output=True, text=True, timeout=15
        )
        print(result.stdout) # 打印健康檢查腳本的輸出
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ 健康檢查超時！API 伺服器可能未在監聽端口。")
        return False
    except Exception as e:
        print(f"❌ 執行健康檢查時發生未知錯誤: {e}")
        return False

# ==============================================================================
# 主執行區：作戰啟動序列 (Main Execution: Launch Sequence)
# ==============================================================================
def main():
    # ... (main 函式與之前版本類似，但 launch 方法現在包含健康檢查) ...
    try:
        manager = ServiceManager()
        # 步驟 1: 啟動 API 伺服器，並附加健康檢查
        api_server_cmd = [
            "poetry", "run", "gunicorn", "-k", "uvicorn.workers.UvicornWorker",
            "--bind", "0.0.0.0:8000", "src.prometheus.entrypoints.query_gateway:app"
        ]
        manager.launch(api_server_cmd, "API 伺服器", health_check_func=check_api_server_health)
        # 步驟 2: 啟動工人蜂群 (無需健康檢查，因為它們依賴於 API)
        # ...
    except (RuntimeError, KeyboardInterrupt) as e:
        print(f"\n捕獲到錯誤或中斷信號: {e}")
        # atexit 會自動處理關閉

if __name__ == "__main__":
    main()
