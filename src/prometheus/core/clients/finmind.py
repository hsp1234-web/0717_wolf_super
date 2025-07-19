# 檔案位置: src/prometheus/core/clients/finmind.py
import os
import requests
import pandas as pd
from typing import Optional, Dict, Any

from .base import BaseClient

class FinMindClient(BaseClient):
    """
    FinMind API 客戶端。

    此客戶端負責與 FinMind API 進行通訊，獲取金融數據。
    它支持使用 API Token 進行驗證以獲取更高的請求額度，
    同時也支持在沒有 Token 的情況下以匿名模式（較低額度）運行。
    """

    def __init__(self, token: Optional[str] = None):
        """
        初始化 FinMindClient。

        Args:
            token (Optional[str]): FinMind API token。如果未提供，
                                   將嘗試從環境變數 FINMIND_API_TOKEN 讀取。
                                   如果兩者皆無，則以匿名模式運行。
        """
        self.token = token or os.getenv("FINMIND_API_TOKEN")
        self.base_url = "https://api.finmindtrade.com/api/v4/data"

    def _make_request(self, params: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        向 FinMind API 發出請求並處理回應。

        Args:
            params (Dict[str, Any]): 請求參數字典。

        Returns:
            Optional[pd.DataFrame]: 包含 API 回應數據的 DataFrame，如果失敗則返回 None。
        """
        headers = {}
        # 只有在 token 存在時才加入 Authorization 標頭
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # 為所有請求添加 token 參數，即使是空字串，以兼容舊版或匿名模式
        # FinMind API 在沒有 token 參數時也能運作
        params_with_token = params.copy()
        params_with_token['token'] = self.token if self.token else ""

        try:
            response = requests.get(self.base_url, params=params_with_token, headers=headers)
            response.raise_for_status()  # 檢查 HTTP 錯誤狀態
            data = response.json()

            if data.get("status", -1) == 200 and "data" in data:
                return pd.DataFrame(data["data"])
            else:
                # 即使請求成功但沒有數據，也打印 API 訊息
                print(f"FinMind API 訊息: {data.get('msg', '沒有可用的數據或發生未知錯誤。')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"請求 FinMind API 時發生錯誤: {e}")
            return None
        except ValueError:  # JSON 解碼錯誤
            print("無法解析 FinMind API 的回應。")
            return None

    def fetch_data(self, symbol: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        從 FinMind 獲取指定數據集。

        Args:
            dataset (str): 數據集名稱 (例如 "TaiwanStockPrice")。
            data_id (str): 股票代號或數據 ID。
            start_date (str): 開始日期 (格式 "YYYY-MM-DD")。
            end_date (Optional[str]): 結束日期 (格式 "YYYY-MM-DD")。

        Returns:
            Optional[pd.DataFrame]: 包含所請求數據的 DataFrame，如果失敗則返回 None。
        """
        params = {
            "dataset": kwargs.get("dataset"),
            "data_id": symbol,
            "start_date": kwargs.get("start_date"),
        }
        if "end_date" in kwargs:
            params["end_date"] = kwargs.get("end_date")

        return self._make_request(params)
