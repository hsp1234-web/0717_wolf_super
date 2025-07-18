import yfinance as yf
import pandas as pd
from .base import BaseClient

class YFinanceClient(BaseClient):
    def fetch_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            # 關鍵修復：yfinance 對某些代號的行為不穩定，我們捕捉潛在的錯誤
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            # 如果返回的 data 沒有任何行，也視為空
            if data.empty:
                return pd.DataFrame()
            return data
        except Exception:
            # 發生任何異常，都返回一個空的 DataFrame 以確保流程繼續
            return pd.DataFrame()
