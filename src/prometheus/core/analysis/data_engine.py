import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ...models.snapshot_models import Factor
from ..queue.sqlite_queue import SQLiteQueue
from ..clients.client_factory import ClientFactory

class DataEngine:
    """
    數據引擎 v2.0 (進化版)
    一個使用「客戶端工廠」模式的、具備性能監控能力的數據調度中心。
    """
    def __init__(self, queue: SQLiteQueue):
        self.queue = queue
        self.factors_config = [
            {'name': 'VIX 恐慌指數', 'category': '市場情緒', 'source': 'yfinance', 'symbol': '^VIX', 'value_col': 'Adj Close'},
            {'name': '美國十年債利率', 'category': '宏觀經濟', 'source': 'fred', 'symbol': 'DGS10', 'value_col': 'DGS10'},
            {'name': '美元指數', 'category': '宏觀經濟', 'source': 'yfinance', 'symbol': 'DX-Y.NYB', 'value_col': 'Adj Close'},
            {'name': 'S&P 500', 'category': '市場指數', 'source': 'yfinance', 'symbol': '^GSPC', 'value_col': 'Adj Close'},
        ]
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=30)

    @staticmethod
    def _process_data(df: pd.DataFrame, value_col: str) -> Dict[str, Any]:
        """從 DataFrame 中提取前端所需的數據格式，增加對 'Close' 的備用支持。"""
        # 彈性欄位選擇：如果指定的 value_col 不存在，但 'Close' 存在，則使用 'Close'
        if value_col not in df.columns and 'Close' in df.columns:
            value_col = 'Close'

        if value_col not in df.columns:
             # 如果兩個欄位都不存在，返回空結果
            return {}

        df = df.dropna(subset=[value_col])
        if len(df) < 2: return {"value": "N/A", "change": 0.0, "trend": []}

        latest = df[value_col].iloc[-1]
        previous = df[value_col].iloc[-2]
        change = ((latest - previous) / previous) * 100 if previous != 0 else 0

        return {
            "value": f"{latest:.2f}",
            "change": round(change, 2),
            "trend": df[value_col].tail(10).tolist()
        }

    def get_market_factors(self) -> List[Factor]:
        """獲取並處理所有定義的市場因子。"""
        all_factors = []
        start_str = self.start_date.strftime('%Y-%m-%d')
        end_str = self.end_date.strftime('%Y-%m-%d')

        for config in self.factors_config:
            step_name = f"fetch_{config['source']}_{config['symbol']}"
            start_time = time.time()
            try:
                client = ClientFactory.get_client(config['source'])
                data = client.fetch_data(config['symbol'], start_str, end_str)

                processed = self._process_data(data, config['value_col'])
                if processed:
                    all_factors.append(Factor(category=config['category'], name=config['name'], **processed))

            except Exception as e:
                print(f"警告: 處理因子 {config['name']} 時發生錯誤: {e}")
            finally:
                # 最終手段：無論如何都記錄性能
                duration = time.time() - start_time
                self.queue.log_performance('global_data_fetch', step_name, duration)

        return all_factors
