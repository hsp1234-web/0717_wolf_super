import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import pandas as pd

from ...models.snapshot_models import Factor
from ..clients.client_factory import ClientFactory
from ..db.data_warehouse import DataWarehouse
from ..queue.sqlite_queue import SQLiteQueue


class DataEngine:
    """
    數據引擎 v3.0 (金剛之軀)
    一個具備快取、性能監控與服務降級能力的韌性數據調度中心。
    """

    def __init__(self, queue: SQLiteQueue, warehouse: DataWarehouse, client_factory: ClientFactory):
        self.queue = queue
        self.warehouse = warehouse
        self.client_factory = client_factory
        self.factors_config = [
            {
                "name": "VIX 恐慌指數",
                "category": "市場情緒",
                "source": "yfinance",
                "symbol": "^VIX",
                "value_col": "Adj Close",
            },
            {
                "name": "美國十年債利率",
                "category": "宏觀經濟",
                "source": "fred",
                "symbol": "DGS10",
                "value_col": "DGS10",
            },
        ]
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=30)

    @staticmethod
    def _process_data(df: pd.DataFrame, value_col: str) -> Tuple[Dict[str, Any], bool]:
        """處理數據並回傳一個標記，指示數據是否陳舊。"""
        if value_col not in df.columns and "Close" in df.columns:
            value_col = "Close"

        if value_col not in df.columns:
            return ({"value": "N/A", "change": 0.0, "trend": []}, True)

        df = df.dropna(subset=[value_col])
        if len(df) < 2:
            return ({"value": "N/A", "change": 0.0, "trend": []}, True)

        is_stale = False
        if "fetched_at" in df.columns:
            last_fetch = df["fetched_at"].max()
            if isinstance(last_fetch, pd.Timestamp):
                last_fetch = last_fetch.to_pydatetime()

            if datetime.now() - last_fetch > timedelta(hours=4):
                is_stale = True

        latest = df[value_col].iloc[-1]
        previous = df[value_col].iloc[-2]
        change = ((latest - previous) / previous) * 100 if previous != 0 else 0

        result = {"value": f"{latest:.2f}", "change": round(change, 2), "trend": df[value_col].tail(10).tolist()}
        return (result, is_stale)

    def _fetch_live_data(self, config: Dict) -> pd.DataFrame:
        """從主數據源獲取即時數據。"""
        start_str = self.start_date.strftime("%Y-%m-%d")
        end_str = self.end_date.strftime("%Y-%m-%d")
        client = self.client_factory.get_client(config["source"])
        data = client.fetch_data(config["symbol"], start_str, end_str)

        if not data.empty:
            if config["source"] == "fred":
                data.rename(columns={config["symbol"]: config["value_col"]}, inplace=True)
            else:
                if "Adj Close" in data.columns:
                    data.rename(columns={"Adj Close": config["value_col"]}, inplace=True)
                elif "Close" in data.columns:
                    data.rename(columns={"Close": config["value_col"]}, inplace=True)
                else:
                    data.rename(columns={data.columns[0]: config["value_col"]}, inplace=True)
        return data

    def get_market_factors(self) -> List[Factor]:
        all_factors = []
        for config in self.factors_config:
            step_name = f"get_factor_{config['symbol']}"
            start_time = time.time()

            try:
                # 1. 主數據源
                live_data = self._fetch_live_data(config)
                if not live_data.empty:
                    self.warehouse.save_data(config["symbol"], live_data)
                    processed_data, _ = self._process_data(live_data, config["value_col"])
                    self.queue.log_performance("factor_fetch", f"{step_name}_live_success", time.time() - start_time)
                    all_factors.append(Factor(category=config["category"], name=config["name"], **processed_data))
                    continue
                else:
                    raise ValueError("Live data source returned no data.")
            except Exception as e:
                self.queue.log_performance("factor_fetch", f"{step_name}_live_fail", time.time() - start_time)
                print(f"警告: 即時獲取 {config['name']} 失敗: {e}")

            # 2. 服務降級 (快取)
            cached_data = self.warehouse.get_data(config["symbol"], staleness_days=365)
            if cached_data is not None:
                processed_data, _ = self._process_data(cached_data, "data_value")
                processed_data["value"] = f"{processed_data.get('value', 'N/A')} (舊)"
                all_factors.append(Factor(category=config["category"], name=config["name"], **processed_data))
                print(f"服務降級: 為 {config['name']} 提供陳舊的快取數據。")
            else:
                print(f"錯誤: {config['name']} 無法從任何來源獲取，已放棄。")

        return all_factors
