from abc import ABC, abstractmethod

import pandas as pd


class BaseClient(ABC):
    """所有數據客戶端的抽象基底類別。"""

    @abstractmethod
    def fetch_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        獲取指定代號在某個時間區間內的數據。
        :param symbol: 商品代號 (e.g., '^VIX', 'DGS10')
        :param start_date: 開始日期 (YYYY-MM-DD)
        :param end_date: 結束日期 (YYYY-MM-DD)
        :return: 一個包含時間序列數據的 pandas DataFrame。
        """
        pass
