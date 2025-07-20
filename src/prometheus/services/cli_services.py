# src/prometheus/services/cli_services.py
"""
這個模組包含了從 CLI (command-line interface) 層剝離出來的業務邏輯。
目的是讓 CLI 層保持輕量，只負責命令的解析和參數的傳遞，而將
實際的業務操作封裝在可重用、可測試的服務函數中。
"""
import os
import shutil
import sqlite3
import random
import uuid
import pandas as pd
import numpy as np
from pathlib import Path

from prometheus.core.logging.log_manager import LogManager

# 為服務層創建一個 logger
logger = LogManager.get_instance().get_logger("CliServices")

def create_dummy_data():
    """
    建立一個用於測試的虛構 OHLCV CSV 檔案。
    """
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    file_path = DATA_DIR / "ohlcv_data.csv"

    date_range = pd.to_datetime(
        pd.date_range(start="2022-01-01", periods=1000, freq="D")
    )
    open_prices = np.random.uniform(90, 110, size=1000)
    data = {
        "Date": date_range,
        "Open": open_prices,
        "High": open_prices + np.random.uniform(0, 5, size=1000),
        "Low": open_prices - np.random.uniform(0, 5, size=1000),
        "Close": open_prices + np.random.uniform(-2, 2, size=1000),
        "Volume": np.random.randint(100000, 500000, size=1000),
    }
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    logger.info(f"已成功建立虛構數據檔案於: {file_path}")
    return file_path

def clear_all_results():
    """
    清除所有生成的結果、佇列、日誌和檢查點。
    """
    logger.info("開始清除所有執行數據...")

    # 這裡的路徑可以從 core.constants 或 config 導入，以保持一致
    # 為了簡化，暫時硬編碼
    PATHS_TO_CLEAR = {
        "output/results.sqlite": "file",
        "data/queues": "dir",
        "data/logs": "dir",
        "data/checkpoints": "dir",
        "data/reports": "dir",
    }

    def remove_path(path_str, is_dir):
        if is_dir:
            if os.path.isdir(path_str):
                shutil.rmtree(path_str)
                logger.info(f"已刪除並清空目錄: {path_str}")
        else:
            if os.path.exists(path_str):
                os.remove(path_str)
                logger.info(f"已刪除檔案: {path_str}")

    try:
        for path, path_type in PATHS_TO_CLEAR.items():
            remove_path(path, path_type == "dir")

        # 重建空目錄
        for path, path_type in PATHS_TO_CLEAR.items():
            if path_type == "dir":
                os.makedirs(path, exist_ok=True)

        logger.info("清除程序完成。")
    except Exception as e:
        logger.error(f"清除過程中發生錯誤: {e}", exc_info=True)

def show_backtest_results():
    """
    從 SQLite 資料庫查詢並顯示回測結果。
    """
    logger.info("正在從 SQLite 資料庫查詢結果...")
    DB_PATH = "output/results.sqlite"
    TABLE_NAME = "backtest_results"
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
        conn.close()

        if df.empty:
            logger.warning("資料庫中尚無任何結果。")
        else:
            logger.info("查詢完成。")
            logger.info(f"\n--- 回測結果 ---\n{df.to_string()}\n----------------")
    except Exception as e:
        logger.error(f"查詢結果時發生錯誤: {e}", exc_info=True)

def generate_markdown_report(xml_path: str, md_path: str):
    """
    從 JUnit XML 檔案產生 Markdown 報告。
    """
    import xml.etree.ElementTree as ET
    from datetime import datetime

    logger.info(f"AI 報告生成器啟動，正在讀取原始數據: {xml_path}")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        suite = root.find("testsuite")

        total = int(suite.get("tests", 0))
        failures = int(suite.get("failures", 0))
        errors = int(suite.get("errors", 0))
        skipped = int(suite.get("skipped", 0))
        exec_time = float(suite.get("time", 0))
        passed = total - failures - errors - skipped

        report_content = [
            "# **【普羅米修斯之火】系統測試作戰報告**",
            f"> 報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "## **一、 戰況總覽**"
        ]

        if failures == 0 and errors == 0:
            report_content.append("> **結論：<font color='green'>任務成功 (SUCCESS)</font>** - 所有品質閘門均已通過。系統戰備狀態良好。")
        else:
            report_content.append("> **結論：<font color='red'>任務失敗 (FAILURE)</font>** - 發現關鍵性錯誤。系統存在風險，需立即審查。")

        summary_table = [
            "| 指標 (Metric) | 數量 (Count) |", "|:---|:---:|",
            f"| ✅ **測試通過 (Passed)** | {passed} |", f"| ❌ **測試失敗 (Failed)** | {failures} |",
            f"| 🔥 **執行錯誤 (Errors)** | {errors} |", f"| 🚧 **測試跳過 (Skipped)** | {skipped} |",
            f"| ⏱️ **總執行時間 (Time)** | {exec_time:.2f} 秒 |", f"| 🧮 **總執行數量 (Total)** | {total} |"
        ]
        report_content.append("\n".join(summary_table))

        if failures > 0 or errors > 0:
            report_content.append("\n## **二、 失敗與錯誤詳情**")
            count = 1
            for testcase in suite.findall("testcase"):
                detail = testcase.find("failure") or testcase.find("error")
                if detail is not None:
                    test_name = testcase.get("name", "未知測試")
                    class_name = testcase.get("classname", "未知類別")
                    error_type = detail.tag.capitalize()
                    message = detail.get("message", "無訊息").splitlines()[0]
                    report_content.extend([
                        f"\n### {count}. {error_type}: {message}",
                        f"- **測試位置:** `{class_name}.{test_name}`",
                        "- **詳細堆疊追蹤:**",
                        f"```\n{(detail.text.strip() if detail.text else '無堆疊追蹤資訊。')}\n```"
                    ])
                    count += 1

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_content))
        logger.info(f"作戰報告已成功生成至: {md_path}")

    except FileNotFoundError:
        logger.error(f"找不到原始數據檔案: {xml_path}")
    except ET.ParseError:
        logger.error(f"原始數據檔案格式錯誤: {xml_path}")
    except Exception as e:
        logger.error(f"生成報告時發生未知錯誤: {e}")

def run_elt_service(input_dir: str, raw_db_path: str, schema_db_path: str, analytics_db_path: str):
    """
    執行 TAIFEX ELT 加工管線。
    """
    os.makedirs(os.path.dirname(raw_db_path), exist_ok=True)
    os.makedirs(os.path.dirname(schema_db_path), exist_ok=True)
    os.makedirs(os.path.dirname(analytics_db_path), exist_ok=True)
    _run_loader(input_dir, raw_db_path, schema_db_path)
    _run_transformer(raw_db_path, schema_db_path, analytics_db_path)

def _run_loader(input_dir, raw_db_path, schema_db_path):
    """(私有) ELT 的 Loader 階段。"""
    from prometheus.core.db.data_warehouse import RawDataWarehouse
    from prometheus.core.db.schema_registry import SchemaRegistry
    from prometheus.core.utils.helpers import prospect_file_content, read_file_content, get_header_fingerprint

    logger.info("--- [階段 2] 執行 Loader ---")
    raw_wh = RawDataWarehouse(raw_db_path)
    schema_registry = SchemaRegistry(schema_db_path)
    known_fingerprints = schema_registry.get_known_fingerprints()

    if not os.path.exists(input_dir):
        logger.warning(f"Loader 輸入目錄 {input_dir} 不存在，跳過加載。")
        raw_wh.close()
        schema_registry.close()
        return

    files_loaded = 0
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if not os.path.isfile(file_path) or raw_wh.is_file_processed(file_path):
            continue
        try:
            file_bytes_content = read_file_content(file_path)
            if file_bytes_content is None: continue
            result = prospect_file_content(file_bytes_content)
            if result["status"] == "success":
                fingerprint = get_header_fingerprint(result["header"])
                if fingerprint in known_fingerprints:
                    raw_wh.log_processed_file(file_path, file_bytes_content, fingerprint)
                    files_loaded += 1
                    logger.info(f"Loader: 已加載 {filename} (schema: {fingerprint[:8]}...)")
        except Exception as e:
            logger.error(f"Loader 處理 {filename} 失敗: {e}", exc_info=True)

    raw_wh.close()
    schema_registry.close()
    logger.info(f"Loader 完成，新載入 {files_loaded} 個檔案。")

def _run_transformer(raw_db_path, schema_db_path, analytics_db_path):
    """(私有) ELT 的 Transformer 階段。"""
    import io
    import pandas as pd
    from prometheus.core.db.data_warehouse import AnalyticsDataWarehouse, RawDataWarehouse
    from prometheus.core.db.schema_registry import SchemaRegistry
    from prometheus.core.utils.helpers import get_header_fingerprint

    logger.info("--- [階段 3] 執行 Transformer ---")
    schema_registry = SchemaRegistry(schema_db_path)
    raw_wh = RawDataWarehouse(raw_db_path)
    analytics_wh = AnalyticsDataWarehouse(analytics_db_path)
    schema_map = schema_registry.get_all_schemas()

    if not schema_map:
        logger.warning("Transformer: 格式註冊表為空，無法執行轉換。")
        raw_wh.close()
        analytics_wh.close()
        schema_registry.close()
        return

    target_fingerprint = get_header_fingerprint("交易日期,契約代碼,到期月份(週別),開盤價,最高價,最低價,收盤價,成交量")
    analytics_wh.create_daily_futures_table()
    records = raw_wh.execute_query("SELECT content_blob, format_fingerprint FROM raw_import_log").fetchall()
    transformed_count = 0

    for blob, fingerprint in records:
        if fingerprint != target_fingerprint: continue
        header_str, encoding = schema_map.get(fingerprint, (None, None))
        if not header_str: continue
        try:
            df = pd.read_csv(io.BytesIO(blob), encoding=encoding, thousands=",", header=0, on_bad_lines="skip")
            df.columns = [str(col).strip().replace('"', "") for col in df.columns]
            target_columns = ["交易日期", "契約代碼", "到期月份(週別)", "開盤價", "最高價", "最低價", "收盤價", "成交量"]
            df_to_load = pd.DataFrame()
            for col in target_columns:
                df_to_load[col] = df.get(col)
            if not df_to_load.empty:
                analytics_wh.insert_daily_futures(df_to_load)
                transformed_count += 1
        except Exception as e:
            logger.error(f"Transformer 處理指紋 {fingerprint[:8]}... 的資料時失敗: {e}", exc_info=True)

    raw_wh.close()
    analytics_wh.close()
    schema_registry.close()
    logger.info(f"Transformer 完成，成功轉換 {transformed_count} 筆記錄。")

def add_tasks_to_queue(num_tasks: int):
    """
    向任務佇列中添加指定數量的隨機回測任務。
    """
    from prometheus.core.context import AppContext

    # AppContext 似乎是為非同步使用設計的，但這裡的 CLI 是同步的。
    # 這可能是一個需要進一步重構的點，但暫時保持原樣。
    # 理想情況下，我們應該直接使用 `SQLiteQueue`。
    try:
        with AppContext() as ctx:
            logger.info(f"正在生成 {num_tasks} 個回測任務...")
            batch_id = str(uuid.uuid4())
            for i in range(num_tasks):
                task = {
                    "task_id": str(uuid.uuid4()),
                    "type": "backtest",
                    "strategy": "SMA_Crossover",
                    "symbol": random.choice(["BTC/USDT", "ETH/USDT", "XRP/USDT"]),
                    "params": {"fast": random.randint(5, 15), "slow": random.randint(20, 40)},
                    "batch_id": batch_id,
                }
                ctx.queue.put(task)
                logger.debug(f"已將任務 {i+1}/{num_tasks} ({task['strategy']}) 添加到佇列。")
            logger.info(f"成功將 {num_tasks} 個任務添加到佇列。")
    except Exception as e:
        logger.error(f"添加任務時發生錯誤: {e}", exc_info=True)

def run_evolution_cycle_service():
    """
    執行一次完整的演化週期：演化 -> 回測 -> 報告。
    """
    from prometheus.models.strategy_models import Strategy
    from prometheus.services.backtesting_service import BacktestingService
    from prometheus.services.evolution_chamber import EvolutionChamber
    from prometheus.services.strategy_reporter import StrategyReporter
    from prometheus.core.db.db_manager import DBManager

    logger.info("--- 啟動【演化室行動】完整作戰週期 ---")

    backtester = BacktestingService(DBManager())
    all_factors_df = backtester.db_manager.fetch_table('factors')
    available_factors = [col for col in all_factors_df.columns if col not in ['date', 'symbol', 'close']]

    if not available_factors:
        logger.error("錯誤：數據庫中找不到可用的因子。請先執行 build-feature-store。")
        return

    target_asset = 'AAPL'
    logger.info(f"INFO: 將使用 '{target_asset}' 作為本次演化的目標資產。")
    chamber = EvolutionChamber(backtester, available_factors, target_asset=target_asset)

    hof = chamber.run_evolution(n_pop=20, n_gen=5)
    if not hof:
        logger.error("錯誤：演化未能產生有效結果。")
        return

    best_individual = hof[0]
    best_factors = [available_factors[i] for i in best_individual]
    final_strategy = Strategy(
        factors=best_factors,
        weights={factor: 1.0 / len(best_factors) for factor in best_factors},
        target_asset=target_asset
    )
    final_report = backtester.run(final_strategy)

    reporter = StrategyReporter()
    reporter.generate_report(hof, final_report, available_factors)

    logger.info("--- 【演化室行動】作戰週期結束 ---")

def run_downloader_service(start_date: str, end_date: str, output_dir: str, max_workers: int):
    """
    執行 TAIFEX 自動化數據採集。
    """
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime, timedelta
    import requests
    from prometheus.core.config import config

    logger.info(f"--- 啟動數據採集任務 (時間範圍: {start_date} 到 {end_date}) ---")

    tasks = []
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = [start_dt + timedelta(days=x) for x in range((end_dt - start_dt).days + 1)]
    base_url = config.get("data_acquisition.taifex.base_url")

    for current_date in date_range:
        date_str = current_date.strftime("%Y_%m_%d")
        tasks.append({
            "url": f"{base_url}/file/taifex/Dailydownload/DailydownloadCSV/Daily_{date_str}.zip",
            "file_name": f"Daily_{date_str}.zip",
            "min_delay": 0.2,
            "max_delay": 1.0,
        })

    results_counter = Counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        with requests.Session() as session:
            future_to_task = {executor.submit(_execute_single_download, session, task, output_dir): task for task in tasks}
            for future in as_completed(future_to_task):
                try:
                    status, message = future.result()
                    results_counter[status] += 1
                    logger.info(f"[{status.upper()}] {message}")
                except Exception as exc:
                    logger.info(f"[CRITICAL] 任務執行異常: {exc}")

    logger.info("\n--- 採集任務總結 ---")
    for status, count in results_counter.items():
        logger.info(f"  {status}: {count} 個")

def _execute_single_download(session, task_info, output_dir):
    """(私有) 執行單一檔案下載任務，包含重試與錯誤處理。"""
    import random
    import time
    import requests
    from prometheus.core.config import config

    file_path = os.path.join(output_dir, task_info["file_name"])
    if os.path.exists(file_path):
        return "exists", f"檔案已存在: {task_info['file_name']}"

    time.sleep(random.uniform(task_info.get("min_delay", 0.1), task_info.get("max_delay", 0.5)))
    user_agents = config.get("data_acquisition.taifex.user_agents")
    base_url = config.get("data_acquisition.taifex.base_url")

    for attempt in range(3):
        try:
            headers = {"User-Agent": random.choice(user_agents), "Referer": task_info.get("referer", base_url)}
            response = session.get(task_info["url"], headers=headers, timeout=120)
            if response.status_code == 200 and len(response.content) > 100 and "查無資料" not in response.text:
                os.makedirs(output_dir, exist_ok=True)
                with open(file_path, "wb") as f: f.write(response.content)
                return "success", f"成功下載: {task_info['file_name']}"
            elif response.status_code == 404:
                return "not_found", f"404 Not Found: {task_info['file_name']}"
            else:
                return "error", f"伺服器錯誤 {response.status_code}: {task_info['file_name']}"
        except requests.exceptions.RequestException as e:
            if attempt == 2: return "error", f"網路請求失敗: {e}"
            time.sleep(5 * (attempt + 1))
    return "error", f"達到最大重試次數: {task_info['file_name']}"

def run_schema_explorer_service(input_dir: str, db_path: str):
    """
    執行 TAIFEX 格式探勘與註冊。
    """
    from prometheus.core.db.schema_registry import SchemaRegistry
    from prometheus.core.utils.helpers import prospect_file_content, read_file_content, get_header_fingerprint

    registry = SchemaRegistry(db_path)
    logger.info(f"開始掃描目錄: {input_dir}")
    new_formats, updated_formats = 0, 0

    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if not os.path.isfile(file_path): continue
        try:
            file_bytes_content = read_file_content(file_path)
            if file_bytes_content is None: continue
            result = prospect_file_content(file_bytes_content)
            if result["status"] == "success":
                fingerprint = get_header_fingerprint(result["header"])
                status = registry.add_or_update_schema(fingerprint, result["header"], result["encoding"], filename)
                if status == "new": new_formats += 1
                else: updated_formats += 1
        except Exception as e:
            logger.error(f"處理檔案 {filename} 失敗: {e}", exc_info=True)

    registry.close()
    logger.info(f"--- 格式探勘總結 ---\n發現新格式: {new_formats} 種\n更新現有格式計數: {updated_formats} 次")
