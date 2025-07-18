# -- coding: utf-8 --
""" start_colab.py

Colab 作戰沙盒啟動器 v5.0 - 原生通道版

本腳本為普羅米修斯計畫在 Google Colab 環境中的主入口點。 最新版本採用 google.colab.output 建立原生、安全的訪問通道。 功能：

--test-mode: 啟用測試模式，運行一段時間後自動退出。
--mock-data: 啟用模擬數據模式，無需啟動後端服務。
--no-dashboard: 僅啟動後端服務和原生通道，不顯示動態儀表板。
環境感知：自動檢測運行環境，適應 Colab 與標準終端機。 """
import argparse
import os
import shlex
import subprocess
import sys
import threading
import time
from typing import List, Dict, Any

# --- 環境與依賴檢測 ---
try:
    import psutil
    import requests
except ImportError as e:
    print(f"錯誤：缺少核心依賴 {e}。請執行 'poetry install'。")
    sys.exit(1)

def is_ipython() -> bool:
    """檢查腳本是否在 IPython 環境 (如 Colab) 中運行。"""
    try:
        shell = get_ipython().__class__.__name__
        # 'ZMQInteractiveShell' 表示在 Notebook 或 QtConsole 中
        # 'Shell' 表示在 Colab 的原生 Python 環境
        return shell in ['ZMQInteractiveShell', 'Shell']
    except NameError:
        return False

# 只有在 IPython 環境中才導入專用模組
if is_ipython():
    from IPython.display import clear_output, display, HTML
    from google.colab import output as colab_output
else:
    # 提供 dummy function 以免在標準終端機中執行時出錯
    def clear_output(wait=False):
        os.system('cls' if os.name == 'nt' else 'clear')
    def display(obj):
        pass  # 在標準終端機中，display 不執行任何操作

# --- 組態設定 ---
NUM_WORKERS = max(1, psutil.cpu_count() - 1)
API_HOST = "127.0.0.1"  # Gunicorn/Uvicorn 監聽本地
API_PORT = 8000
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
TEST_MODE_DURATION = 10
REFRESH_INTERVAL = 5
TEST_REFRESH_INTERVAL = 2

# --- 顏色代碼 ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- 顯示管理器 ---
class DisplayManager:
    """負責繪製和刷新動態儀表板。"""
    def __init__(self, stop_event: threading.Event, args: argparse.Namespace):
        self.stop_event = stop_event
        self.args = args
        self.processes: List[subprocess.Popen] = []
        self.refresh_interval = TEST_REFRESH_INTERVAL if self.args.test_mode else REFRESH_INTERVAL

    def set_processes(self, processes: List[subprocess.Popen]):
        self.processes = processes

    def _get_mock_data(self, endpoint: str) -> Dict[str, Any]:
        if endpoint.startswith("/api/v1/status"):
            return {"system": {"cpu_percent": 15.5, "memory_percent": 55.2, "memory_used_gb": 8.8, "memory_total_gb": 16.0}, "queue": {"pending": 5, "processing": 2}}
        if endpoint.startswith("/api/v1/logs"):
            return {"logs": [{"level": "INFO", "message": "模擬日誌：系統初始化成功。"}, {"level": "WARNING", "message": "模擬日誌：偵測到高記憶體使用率。"}, {"level": "ERROR", "message": "模擬日誌：無法連接到外部數據源。"}]}
        return {"error": "未知的模擬端點"}

    def _fetch_api_data(self, endpoint: str) -> Dict[str, Any]:
        if self.args.mock_data:
            return self._get_mock_data(endpoint)
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=2)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def _format_log_message(self, log: Dict[str, Any]) -> str:
        msg, level = log.get("message", "無效的日誌格式"), log.get("level", "INFO")
        color = Colors.FAIL if "ERROR" in level else Colors.WARNING if "WARN" in level else Colors.ENDC
        return f"{color}[{level:<7}] {msg}{Colors.ENDC}"

    def _check_process_status(self) -> List[str]:
        if self.args.mock_data:
            return ["  - 模擬模式下未啟動真實服務。"]
        status_lines = []
        for p in self.processes:
            status = "🟢 RUNNING" if p.poll() is None else f"🔴 STOPPED (code: {p.poll()})"
            cmd = ' '.join(p.args) if isinstance(p.args, list) else p.args
            status_lines.append(f"  - PID {p.pid:<5} {status:<18} | CMD: {cmd[:50]}...")
        return status_lines

    def draw_dashboard(self):
        clear_output(wait=True)
        print(f"{Colors.HEADER}{Colors.BOLD}普羅米修斯作戰系統 - 「神之眼」動態儀表板{Colors.ENDC}")
        print("=" * 70)
        status_data = self._fetch_api_data("/api/v1/status")
        if "error" in status_data:
            print(f"{Colors.FAIL}🔴 無法連接到作戰司令部: {status_data['error']}{Colors.ENDC}")
        else:
            s, q = status_data.get('system', {}), status_data.get('queue', {})
            print(f"{Colors.CYAN}📊 系統資源: [CPU: {s.get('cpu_percent', 'N/A')}%] [記憶體: {s.get('memory_percent', 'N/A')}% ({s.get('memory_used_gb', 'N/A')}/{s.get('memory_total_gb', 'N/A')} GB)]{Colors.ENDC}")
            print(f"{Colors.CYAN}📦 任務佇列: [待處理: {q.get('pending', 'N/A')}] [處理中: {q.get('processing', 'N/A')}]{Colors.ENDC}")
        print("-" * 70)
        print(f"{Colors.BLUE}{Colors.BOLD}蜂巢服務狀態:{Colors.ENDC}")
        for line in self._check_process_status():
            print(line)
        print("-" * 70)
        print(f"{Colors.BLUE}{Colors.BOLD}即時日誌 (最近 5 條):{Colors.ENDC}")
        log_data = self._fetch_api_data("/api/v1/logs?limit=5")
        logs = log_data.get("logs", []) if "error" not in log_data else [{"level": "ERROR", "message": log_data["error"]}]
        for log in logs:
            print(self._format_log_message(log))
        print("=" * 70)
        if self.args.test_mode:
            print(f"測試模式運行中... {TEST_MODE_DURATION}秒後自動退出。")
        else:
            print(f"儀表板每 {self.refresh_interval} 秒刷新一次... (按 Ctrl+C 或 Colab 中斷按鈕來停止)")

    def run(self):
        start_time = time.time()
        while not self.stop_event.is_set():
            if self.args.test_mode and time.time() - start_time > TEST_MODE_DURATION:
                print(f"\n{Colors.WARNING}[測試模式] 已達運行時間上限，自動停止。{Colors.ENDC}")
                break
            self.draw_dashboard()
            time.sleep(self.refresh_interval)
        clear_output(wait=True)
        print(f"{Colors.GREEN}儀表板執行緒已停止。{Colors.ENDC}")

# --- 主執行流程 ---
def run_command(command: str) -> subprocess.Popen:
    args = shlex.split(command)
    process_name = os.path.basename(args[1] if 'gunicorn' in args[0] else args[-1])
    print(f"{Colors.GREEN}🚀 正在背景啟動 {process_name}...{Colors.ENDC}")
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, preexec_fn=os.setsid)

def main():
    parser = argparse.ArgumentParser(description="普羅米修斯計畫 Colab 啟動器 v5.0")
    parser.add_argument("--test-mode", action="store_true", help="啟用測試模式，運行指定時間後自動退出。")
    parser.add_argument("--mock-data", action="store_true", help="使用模擬數據，不啟動後端服務。")
    parser.add_argument("--no-dashboard", action="store_true", help="僅啟動服務和通道，不顯示儀表板。")
    args = parser.parse_args()

    print(f"{Colors.HEADER}{Colors.BOLD}--- 普羅米修斯計畫 Colab 部署腳本 v5.0 ---{Colors.ENDC}")

    all_processes = []
    stop_event = threading.Event()
    display_thread = None

    try:
        if not args.mock_data:
            python_executable = sys.executable
            print(f"\n{Colors.BLUE}--- [階段 1/2] 執行地基工程 ---{Colors.ENDC}")
            db_init_proc = subprocess.run([python_executable, "-m", "src.prometheus.entrypoints.db_init"], capture_output=True, text=True)
            if db_init_proc.returncode != 0:
                raise RuntimeError(f"資料庫初始化失敗:\n{db_init_proc.stderr}")
            print(f"{Colors.GREEN}✅ 資料庫初始化完成。{Colors.ENDC}")

            print(f"\n{Colors.BLUE}--- [階段 2/2] 啟動作戰單位 ---{Colors.ENDC}")
            gunicorn_cmd = f"gunicorn src.prometheus.entrypoints.query_gateway:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:{API_PORT}"
            all_processes.append(run_command(gunicorn_cmd))
            time.sleep(5)

            for _ in range(NUM_WORKERS):
                worker_cmd = f"{python_executable} real_worker.py"
                all_processes.append(run_command(worker_cmd))
            print(f"{Colors.GREEN}✅ 所有 {len(all_processes)} 個背景服務已啟動。{Colors.ENDC}")

            if is_ipython():
                print(f"\n{Colors.BLUE}--- 建立 Colab 原生通道 ---{Colors.ENDC}")
                display(HTML(f"<p style='color:yellow;'>正在等待 Colab 指派公開網址，請稍候...</p>"))
                colab_output.serve_kernel_port_as_window(API_PORT, anchor_text=f"🚀 點此開啟普羅米修斯 API 介面 (連接埠 {API_PORT})")

        if not args.no_dashboard:
            print(f"\n{Colors.BLUE}--- 啟動「神之眼」動態儀表板 ---{Colors.ENDC}")
            display_manager = DisplayManager(stop_event, args)
            display_manager.set_processes(all_processes)
            display_thread = threading.Thread(target=display_manager.run)
            display_thread.start()
            display_thread.join()
        else:
            print("\n✅ 所有服務已啟動。禁用儀表板模式。按 Ctrl+C 或 Colab 中斷按鈕關閉所有服務。")
            while not stop_event.is_set():
                time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}捕獲到手動中斷信號...{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}發生意外錯誤: {e}{Colors.ENDC}")
    finally:
        print(f"\n{Colors.WARNING}--- 正在關閉所有服務 ---{Colors.ENDC}")
        stop_event.set()
        if display_thread and display_thread.is_alive():
            display_thread.join(timeout=2)

        for p in reversed(all_processes):
            if p.poll() is None:
                print(f"正在終止 PID: {p.pid} (PGID: {os.getpgid(p.pid)})...")
                try:
                    os.killpg(os.getpgid(p.pid), subprocess.signal.SIGTERM)
                    p.wait(timeout=5)
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    os.killpg(os.getpgid(p.pid), subprocess.signal.SIGKILL)
                except Exception:
                    pass
        print(f"{Colors.GREEN}✅ 所有服務已安全關閉。{Colors.ENDC}")

if __name__ == "__main__":
    main()
