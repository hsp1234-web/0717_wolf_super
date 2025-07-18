import pandas_datareader.data as web
import pandas as pd
from .base import BaseClient

class FredClient(BaseClient):
    def fetch_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        return web.DataReader(symbol, 'fred', start_date, end_date)
