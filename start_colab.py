import os
import sys
import time
import subprocess
import logging
from datetime import datetime

# --- 在設定日誌之前，立即確保 logs 目錄存在 ---
if not os.path.exists("logs"):
    os.makedirs("logs")

# --- 日誌地基工程 ---
log_filename = f"logs/colab_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Prometheus")

class ServiceManager:
    """「普羅米修斯」服務管理器。"""
    def __init__(self):
        self.processes = []
        self.log_files = {}

    def launch(self, command, service_name, health_check_func=None):
        """啟動一個服務，並像鷹一樣盯著它。"""
        try:
            service_log_path = f"logs/{service_name.lower().replace(' ', '_')}.log"
            log_file = open(service_log_path, 'w')
            self.log_files[service_name] = log_file

            logger.info(f"🚀 發射 '{service_name}'...")
            logger.info(f"   - 指令: {' '.join(command)}")
            logger.info(f"   - 日誌: {service_log_path}")

            process = subprocess.Popen(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                # 確保子進程可以看到 src
                env={**os.environ, "PYTHONPATH": f".{os.pathsep}{os.environ.get('PYTHONPATH', '')}"}
            )
            self.processes.append((process, service_name))
            logger.info(f"   ✅ '{service_name}' 進程已啟動 (PID: {process.pid}).")

            if health_check_func:
                logger.info(f"   🩺 正在對 '{service_name}' 進行健康檢查...")
                if not health_check_func():
                    raise RuntimeError(f"'{service_name}' 健康檢查失敗。請檢查日誌: {service_log_path}")
                logger.info(f"   ❤️ '{service_name}' 健康檢查通過。")

        except Exception as e:
            logger.error(f"💥 啟動 '{service_name}' 時發生致命錯誤: {e}")
            raise RuntimeError(f"無法啟動 {service_name}")

    def terminate_all(self):
        """執行「焦土協議」：乾淨利落地終止所有子進程。"""
        logger.info("--- 執行焦土協議：正在終止所有服務 ---")
        for process, name in reversed(self.processes):
            try:
                if process.poll() is None:
                    logger.warning(f"   - 正在發送終止信號給 '{name}' (PID: {process.pid})...")
                    process.terminate()
                    process.wait(timeout=10)
                    logger.info(f"   - '{name}' 已成功終止。")
                else:
                    logger.info(f"   - '{name}' 已經自行終止。")
            except subprocess.TimeoutExpired:
                logger.error(f"   - 警告: '{name}' 在 10 秒內未響應終止信號。強制擊殺！")
                process.kill()
                logger.info(f"   - '{name}' 已被強制擊殺。")
            except Exception as e:
                logger.error(f"   - 終止 '{name}' 時發生錯誤: {e}")

        for log_file in self.log_files.values():
            log_file.close()
        logger.info("--- 所有服務均已關閉。焦土協議執行完畢。 ---")

def check_api_server_health(retries=5, delay=3):
    """一個固執的健康檢查員。"""
    import requests
    url = "http://127.0.0.1:8000/health"
    for i in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"      -> 第 {i+1} 次嘗試: 成功！伺服器回應: {response.json()}")
                return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"      -> 第 {i+1} 次嘗試: API 伺服器尚未就緒... ({e})")
            time.sleep(delay)
    logger.error("API 伺服器在多次嘗試後仍未通過健康檢查。")
    return False

def run_db_init():
    """執行資料庫初始化。"""
    logger.info("--- 第一階段：奠定數據基石 ---")
    logger.info("   - 正在執行資料庫初始化腳本...")
    try:
        # 使用 sys.executable 來確保我們用的是同一個 Python
        python_executable = sys.executable
        command = [python_executable, "-m", "src.prometheus.entrypoints.db_init"]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            env={**os.environ, "PYTHONPATH": f".{os.pathsep}{os.environ.get('PYTHONPATH', '')}"}
        )
        logger.info("   - 資料庫初始化腳本輸出:")
        for line in result.stdout.strip().split('\n'):
            logger.info(f"     {line}")
        logger.info("   ✅ 資料庫基石已成功奠定。")
    except subprocess.CalledProcessError as e:
        logger.error("   💥 資料庫初始化失敗！")
        logger.error(f"   - 返回碼: {e.returncode}")
        output = e.stdout + (e.stderr or "")
        logger.error(f"   - 輸出:\n{output}")
        raise RuntimeError("資料庫初始化失敗")

def main():
    """「普羅米修斯計畫」- 環境校準版啟動程序。"""
    logger.info("======================================================")
    logger.info("===       「普羅米修斯計畫」後端啟動序列       ===")
    logger.info("======================================================")

    manager = ServiceManager()

    try:
        run_db_init()

        logger.info("\n--- 第二階段：並行啟動所有服務 ---")

        # 回歸作戰計畫最初的方案：使用 sys.executable
        python_executable = sys.executable
        api_server_cmd = [
            python_executable, "-m", "gunicorn",
            "-w", "1",
            "-k", "uvicorn.workers.UvicornWorker",
            "src.prometheus.entrypoints.query_gateway:app",
            "--bind", "0.0.0.0:8000"
        ]
        manager.launch(api_server_cmd, "API_伺服器", health_check_func=check_api_server_health)

        worker_count = max(1, (os.cpu_count() or 2) - 1)
        logger.info(f"ℹ️  將並行部署 {worker_count} 個作戰工人。")
        for i in range(worker_count):
            worker_cmd = [python_executable, "real_worker.py"]
            manager.launch(worker_cmd, f"工人蜂-{i+1}")

        logger.info("\n======================================================")
        logger.info("🎉 所有服務已成功發射。系統進入穩定運行狀態。")
        logger.info("======================================================")

        while True:
            time.sleep(300)

    except (RuntimeError, KeyboardInterrupt) as e:
        if isinstance(e, RuntimeError):
            logger.error(f"\n💥 啟動序列失敗: {e}")
        else:
            logger.info("\n⌨️ 接收到使用者中斷指令。")

        logger.info("🔴 系統正在關閉...")

    finally:
        manager.terminate_all()

if __name__ == "__main__":
    main()
