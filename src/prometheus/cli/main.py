import typer
import os
from prometheus.entrypoints.query_gateway import start
from prometheus.core.logging.log_manager import LogManager

app = typer.Typer()
# 由於 LogManager 不再是單例，我們為 CLI 的主進程創建一個常規的 logger
log_manager = LogManager(log_file="prometheus_cli.log")
logger = log_manager.get_logger("Conductor")

@app.command(name="dashboard")
def cli_dashboard(
    host: str = typer.Option("127.0.0.1", help="綁定主機"),
    port: int = typer.Option(8000, help="綁定埠號"),
):
    """啟動網頁儀表板。"""
    logger.info(f"準備在 http://{host}:{port} 啟動儀表板...")
    start()

data_app = typer.Typer()
app.add_typer(data_app, name="data")

# 導入新的服務模組
from prometheus.services import cli_services

@data_app.command("create-dummy")
def create_dummy():
    """
    建立一個用於測試的虛構 OHLCV CSV 檔案。
    """
    logger.info("正在調用數據服務以創建虛構數據...")
    cli_services.create_dummy_data()


results_app = typer.Typer()
app.add_typer(results_app, name="results")

@results_app.command("clear")
def clear_results():
    """
    清除所有生成的結果、佇列、日誌和檢查點。
    """
    logger.info("正在調用服務以清除所有執行數據...")
    cli_services.clear_all_results()


@results_app.command("show")
def show_results():
    """
    從 SQLite 資料庫查詢並顯示回測結果。
    """
    cli_services.show_backtest_results()


@results_app.command("generate-report")
def generate_report(
    xml_path: str = typer.Option("output/reports/report.xml", help="JUnit XML 報告的路徑"),
    md_path: str = typer.Option("TEST_REPORT.md", help="要生成的 Markdown 報告的路徑"),
):
    """
    從 JUnit XML 檔案產生 Markdown 報告。
    """
    cli_services.generate_markdown_report(xml_path, md_path)


@results_app.command("add-tasks")
def add_tasks(
    num_tasks: int = typer.Option(10, help="要添加的任務數量"),
):
    """
    向任務佇列中添加指定數量的隨機回測任務。
    """
    cli_services.add_tasks_to_queue(num_tasks)


pipelines_app = typer.Typer()
app.add_typer(pipelines_app, name="pipelines")

@pipelines_app.command("run-downloader")
def run_downloader(
    start_date: str = typer.Option(..., help="下載開始日期 (YYYY-MM-DD)"),
    end_date: str = typer.Option(..., help="下載結束日期 (YYYY-MM-DD)"),
    output_dir: str = typer.Option("data/downloads", help="檔案儲存目錄"),
    max_workers: int = typer.Option(16, help="最大同時下載任務數"),
):
    """
    TAIFEX 自動化數據採集器 v1.0
    """
    cli_services.run_downloader_service(start_date, end_date, output_dir, max_workers)


@pipelines_app.command("run-explorer")
def run_explorer(
    input_dir: str = typer.Option("data/downloads", help="掃描的原始檔案目錄"),
    db_path: str = typer.Option("data/metadata/schema_registry.db", help="格式註冊表資料庫路徑"),
):
    """
    TAIFEX 格式探勘與註冊器 v1.0
    """
    cli_services.run_schema_explorer_service(input_dir, db_path)


def get_header_fingerprint(header_line: str) -> str:
    """對標準化後的標頭計算指紋。"""
    import hashlib
    normalized_header = "".join(header_line.lower().split()).replace('"', "")
    return hashlib.sha256(normalized_header.encode("utf-8")).hexdigest()


@pipelines_app.command("run-elt")
def run_elt(
    input_dir: str = typer.Option("data/downloads", help="下載檔案的來源目錄 (供 Loader 使用)"),
    raw_db_path: str = typer.Option("data/raw_warehouse/raw_taifex.duckdb", help="原始數據艙資料庫路徑"),
    schema_db_path: str = typer.Option("data/metadata/schema_registry.db", help="格式註冊表資料庫路徑"),
    analytics_db_path: str = typer.Option("data/analytics_warehouse/analytics_taifex.duckdb", help="分析數據庫路徑"),
):
    """
    TAIFEX ELT 加工管線 v1.0
    """
    cli_services.run_elt_service(input_dir, raw_db_path, schema_db_path, analytics_db_path)


@pipelines_app.command("run-stock-factors")
def run_stock_factors():
    """
    執行第四號生產線：股票因子生成。
    """
    from prometheus.pipelines.p4_stock_factor_generation import main as p4_main
    logger.info("--- 啟動 P4：股票因子生成管線 ---")
    p4_main()
    logger.info("--- P4：股票因子生成管線執行完畢 ---")


@pipelines_app.command("run-crypto-factors")
def run_crypto_factors():
    """
    執行第五號生產線：加密貨幣因子生成。
    """
    from prometheus.pipelines.p5_crypto_factor_generation import main as p5_main
    logger.info("--- 啟動 P5：加密貨幣因子生成管線 ---")
    p5_main()
    logger.info("--- P5：加密貨幣因子生成管線執行完畢 ---")


@app.command(name="build-feature-store")
def build_feature_store():
    """
    【作戰指令】統一數據倉儲重構：建造特徵倉儲。
    """
    from prometheus.core.db.db_manager import DBManager
    from prometheus.pipelines.p4_stock_factor_generation import main as p4_main
    from prometheus.pipelines.p5_crypto_factor_generation import main as p5_main

    logger.info("--- 啟動統一數據倉儲建構流程 ---")
    DBManager()

    logger.info("執行 P4 股票因子生成...")
    p4_main()
    logger.info("P4 股票因子數據已合併。")

    logger.info("執行 P5 加密貨幣因子生成...")
    p5_main()
    logger.info("P5 加密貨幣因子數據已合併。")

    logger.info("--- 統一數據倉儲建構流程完畢 ---")


@pipelines_app.command("run-simulation-training")
def run_simulation_training(
    target_factor: str = typer.Option(..., help="要模擬的目標因子名稱"),
):
    """
    執行第六號生產線：因子代理模擬模型訓練。
    """
    from prometheus.pipelines.p6_simulation_training import run_main as p6_run_main
    logger.info(f"--- 啟動 P6：因子代理模擬模型訓練管線，目標為 {target_factor} ---")
    p6_run_main(target_factor=target_factor)
    logger.info("--- P6：因子代理模擬模型訓練管線執行完畢 ---")


@pipelines_app.command("run")
def run_pipeline(
    name: str = typer.Option(..., help="要執行的管線名稱"),
    ticker: str = typer.Option(None, "--ticker", "-t", help="要處理的資產代號")
):
    """
    執行指定的數據管線。
    """
    import asyncio
    pipeline_context = {"ticker": ticker} if ticker else {}
    logger.info(f"--- 啟動 {name} 管線，上下文: {pipeline_context} ---")

    if name == "p1_factor_generation":
        from prometheus.pipelines.p1_factor_generation import p1_factor_generation_pipeline
        asyncio.run(p1_factor_generation_pipeline.run(context=pipeline_context))
    elif name == "p2_index_factor_generation":
        from prometheus.pipelines.p2_index_factor_generation import p2_index_factor_pipeline
        asyncio.run(p2_index_factor_pipeline.run(context=pipeline_context))
    elif name == "p3_bond_factor_generation":
        from prometheus.pipelines.p3_bond_factor_generation import p3_bond_factor_pipeline
        asyncio.run(p3_bond_factor_pipeline.run(context=pipeline_context))
    else:
        logger.error(f"錯誤：找不到名為 '{name}' 的管線。")
        raise typer.Exit(code=1)

    logger.info(f"--- {name} 管線執行完畢 ---")


@pipelines_app.command("run-backfill")
def run_backfill_cli(
    start_date: str = typer.Option(..., help="回填開始日期 (YYYY-MM-DD)"),
    end_date: str = typer.Option(..., help="回填結束日期 (YYYY-MM-DD)"),
):
    """
    執行歷史數據回填管線。
    """
    import pandas as pd
    from prometheus.core.analysis.data_engine import DataEngine
    from prometheus.core.clients.client_factory import ClientFactory

    logger.info(f"--- 開始執行數據回填作業：從 {start_date} 到 {end_date} ---")

    data_engine = DataEngine()
    hourly_timestamps = pd.date_range(start=start_date, end=end_date, freq="H")
    total_tasks = len(hourly_timestamps)

    for i, ts in enumerate(hourly_timestamps):
        logger.debug(f"--- 正在處理 ({i + 1}/{total_tasks}): {ts} ---")
        try:
            data_engine.generate_snapshot(ts)
        except Exception as e:
            logger.error(f"❌ 處理 {ts} 時發生錯誤: {e}", exc_info=True)

    data_engine.close()
    ClientFactory.close_all()
    logger.info("--- 數據回填作業完成 ---")


@app.command()
def run_evolution_cycle():
    """
    🚀 [端到端] 執行一次完整的演化週期：演化 -> 回測 -> 報告。
    """
    cli_services.run_evolution_cycle_service()

services_app = typer.Typer()
app.add_typer(services_app, name="services")

@services_app.command("start")
def start_services():
    """
    【生產級】使用 Gunicorn 啟動 API 伺服器和工人蜂群。
    """
    import subprocess
    import signal

    # 根據 CPU 核心數決定工人數量，留出一個核心給系統和 API
    worker_count = max(1, os.cpu_count() - 1)

    logger.info("[*] 正在啟動 API 伺服器 (由 Gunicorn 管理)...")
    # 使用 gunicorn 啟動 FastAPI 應用
    # 注意：Gunicorn 的目標應用路徑也需要相對於 src 目錄
    api_server_cmd = [
        "poetry", "run", "gunicorn",
        "-c", "gunicorn.conf.py",
        "prometheus.entrypoints.query_gateway:app"
    ]
    api_process = subprocess.Popen(api_server_cmd)

    logger.info(f"[*] 正在啟動 {worker_count} 個工人的蜂群...")
    worker_processes = []
    for _ in range(worker_count):
        # real_worker.py 也需要正確的 PYTHONPATH
        # 我們假設它在專案根目錄，所以直接執行
        worker_cmd = ["poetry", "run", "python", "real_worker.py"]
        # 確保子進程也能找到 prometheus 模組
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath("src") + os.pathsep + env.get("PYTHONPATH", "")
        worker_processes.append(subprocess.Popen(worker_cmd, env=env))

    logger.info("\n[+] 所有服務已啟動。API 伺服器運行在 http://0.0.0.0:8000")
    logger.info(f"[+] {worker_count} 個工人正在背景監聽任務。")
    logger.info("使用 Ctrl+C 來關閉所有服務。")

    def shutdown_handler(signum, frame):
        logger.info("\n[*] 收到關閉信號，正在優雅地關閉所有服務...")

        # 終止工人進程
        for p in worker_processes:
            p.terminate()

        # 終止 Gunicorn 主進程
        api_process.terminate()

        # 等待進程結束
        for p in worker_processes:
            p.wait()
        api_process.wait()

        logger.info("[+] 所有服務已成功關閉。")
        exit(0)

    # 註冊信號處理器
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # 等待主 Gunicorn 進程結束
    api_process.wait()


if __name__ == "__main__":
    app()
