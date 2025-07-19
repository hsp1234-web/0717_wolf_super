import logging
import asyncio
from typing import List

from src.prometheus.core.clients.client_factory import ClientFactory
from src.prometheus.core.config import config
from src.prometheus.core.db.db_manager import DBManager
from src.prometheus.core.engines.crypto_factor_engine import CryptoFactorEngine
from src.prometheus.core.pipelines.pipeline import Pipeline
from src.prometheus.core.pipelines.steps.financial_steps import RunCryptoFactorEngineStep
from src.prometheus.core.pipelines.steps.loaders import LoadCryptoDataStep
from src.prometheus.core.pipelines.steps.savers import SaveToWarehouseStep
from src.prometheus.core.pipelines.steps.splitters import GroupBySymbolStep
from src.prometheus.core.pipelines.steps.normalize_columns_step import NormalizeColumnsStep

logger = logging.getLogger(__name__)

class P5_CryptoFactorGeneration:
    """
    第五號生產線：加密貨幣因子生成
    """

    def __init__(self, symbols: List[str] = None):
        """
        初始化 P5 生產線。

        :param symbols: 要處理的加密貨幣代號列表。如果為 None，則使用預設列表。
        """
        self.target_symbols = symbols or ["BTC-USD", "ETH-USD"]
        self.db_manager = DBManager(db_path=config.get("database.main_db_path"))
        self.client_factory = ClientFactory()
        self.pipeline = self._create_pipeline()

    def _create_pipeline(self) -> Pipeline:
        """
        創建用於生成加密貨幣因子的 Pipeline。
        """
        crypto_factor_engine = CryptoFactorEngine(self.client_factory)
        steps = [
            LoadCryptoDataStep(symbols=self.target_symbols, client_factory=self.client_factory),
            NormalizeColumnsStep(),
            GroupBySymbolStep(),
            RunCryptoFactorEngineStep(engine=crypto_factor_engine),
            SaveToWarehouseStep(db_manager=self.db_manager, table_name="factors"),
        ]
        return Pipeline(steps=steps)

    def run(self):
        """
        執行加密貨幣因子生成流程。
        """
        logger.info("===== 開始執行第五號生產線：加密貨幣因子生成 =====")
        logger.info(f"目標加密貨幣: {self.target_symbols}")

        try:
            asyncio.run(self.pipeline.run())
            logger.info("Pipeline 執行成功。")
        except Exception as e:
            logger.error(f"Pipeline 執行過程中發生錯誤: {e}", exc_info=True)

        logger.info("===== 第五號生產線執行完畢 =====")

if __name__ == "__main__":
    pipeline = P5_CryptoFactorGeneration()
    pipeline.run()
