from typing import Dict, Type

from .base import BaseClient
from .fred import FredClient
from .yfinance import YFinanceClient


class ClientFactory:
    """
    客戶端工廠，根據數據源名稱創建並回傳對應的客戶端實例。
    """

    _clients: Dict[str, Type[BaseClient]] = {
        "yfinance": YFinanceClient,
        "fred": FredClient,
    }

    @staticmethod
    def get_client(source_name: str) -> BaseClient:
        client_class = ClientFactory._clients.get(source_name.lower())
        if not client_class:
            raise ValueError(f"未知的數據源: {source_name}")
        return client_class()
