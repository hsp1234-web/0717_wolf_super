# -*- coding: utf-8 -*-
import pandas as pd
import logging

class MockDataEngine:
    """
    一個用於快速測試的模擬數據引擎。
    它模仿真實 DataEngine 的行為，但返回硬編碼的數據，以消除網路延遲。
    """
    def __init__(self, config=None):
        logging.info("[作戰演習模式] 模擬數據引擎已初始化。")
        # 準備一份小規模、結構正確的假數據
        self.mock_data = {
            'vix': pd.DataFrame({'Close': [20.5, 21.0, 22.5]}, index=pd.to_datetime(['2025-07-15', '2025-07-16', '2025-07-17'])),
            'skew': pd.DataFrame({'Value': [120.0, 125.0, 130.0]}, index=pd.to_datetime(['2025-07-15', '2025-07-16', '2025-07-17']))
        }

    def get_data(self, data_name: str, **kwargs) -> pd.DataFrame:
        """
        獲取模擬數據。
        """
        logging.info(f"[作戰演習模式] 正在提供模擬數據: {data_name}")
        if data_name in self.mock_data:
            return self.mock_data[data_name]
        # 如果請求的數據不存在，返回一個空的 DataFrame 以防止崩潰
        return pd.DataFrame()
