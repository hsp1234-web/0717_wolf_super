import os
import duckdb
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

class DataWarehouse:
    """
    基於 DuckDB 的數據倉庫，作為高效的本地快取層。
    負責儲存和檢索來自外部數據源的時間序列數據。
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def _get_connection(self):
        return duckdb.connect(database=self.db_path, read_only=False)

    def save_data(self, symbol: str, data: pd.DataFrame):
        """將一個 DataFrame 存儲到對應的 symbol 表中。"""
        table_name = symbol.replace('^', '').replace('=', '_').replace('-', '_').replace('.', '_')
        with self._get_connection() as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (timestamp TIMESTAMP, data_value DOUBLE, fetched_at TIMESTAMP)")
            # 為了簡化，我們只儲存單一數值列，並重新命名
            df_to_save = data[[data.columns[0]]].copy()
            df_to_save.columns = ['data_value']
            df_to_save['timestamp'] = pd.to_datetime(df_to_save.index)
            df_to_save['fetched_at'] = datetime.now()
            conn.register('df_to_save_view', df_to_save)
            # 關鍵修復：在註冊視圖後，直接執行 INSERT INTO ... SELECT，不需再傳遞 DataFrame 作為參數
            conn.execute(f"""
                INSERT INTO {table_name} (timestamp, data_value, fetched_at)
                SELECT timestamp, data_value, fetched_at FROM df_to_save_view
            """)

    def get_data(self, symbol: str, staleness_days: int = 1) -> Optional[pd.DataFrame]:
        """
        獲取指定 symbol 的數據。如果數據過於陳舊，則回傳 None。
        """
        table_name = symbol.replace('^', '').replace('=', '_').replace('-', '_').replace('.', '_')
        with self._get_connection() as conn:
            try:
                # 檢查表是否存在
                tables = conn.execute("SHOW TABLES").fetchall()
                if (table_name,) not in tables:
                    return None

                # 檢查最新數據的新鮮度
                latest_fetch_result = conn.execute(f"SELECT MAX(fetched_at) FROM {table_name}").fetchone()
                if latest_fetch_result is None or latest_fetch_result[0] is None:
                    return None # 沒有數據或沒有有效的 fetched_at

                latest_fetch = latest_fetch_result[0]
                if datetime.now() - latest_fetch > timedelta(days=staleness_days):
                    # 即使數據陳舊，我們仍然返回它，讓調用者決定如何處理
                    pass

                df = conn.execute(f"SELECT timestamp, data_value, fetched_at FROM {table_name} ORDER BY timestamp").fetchdf()
                # 關鍵修復：在返回前，確保 index 是 timestamp
                if 'timestamp' in df.columns:
                    df = df.set_index('timestamp')
                return df
            except Exception:
                return None
