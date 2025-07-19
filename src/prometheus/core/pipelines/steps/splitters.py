# src/prometheus/core/pipelines/steps/splitters.py

import logging
from typing import Any, Dict

import pandas as pd

from src.prometheus.core.pipelines.base_step import BaseStep

logger = logging.getLogger(__name__)


class GroupBySymbolStep(BaseStep):
    """
    一個 Pipeline 步驟，用於將 DataFrame 按 'symbol' 欄位分組。
    """

    async def run(self, data: pd.DataFrame, context: Dict[str, Any]):
        """
        將輸入的 DataFrame 按 'symbol' 分組。

        :param data: 包含 'symbol' 欄位的 DataFrame。
        :param context: Pipeline 的共享上下文。
        :return: 一個 DataFrame 的列表，每個 DataFrame 對應一個 symbol。
        """
        logger.info("正在執行 GroupBySymbolStep...")

        if "symbol" not in data.columns:
            logger.warning("輸入的 DataFrame 缺少 'symbol' 欄位，跳過分組步驟。")
            return

        if data.empty:
            logger.info("輸入的 DataFrame 為空，無需分組。")
            return

        grouped = data.groupby("symbol")

        logger.info(f"成功將數據分為 {len(grouped)} 組。")
        for _, group in grouped:
            yield group
