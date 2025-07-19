"""
策略報告服務
負責從資料庫中提取最佳策略並生成報告。
"""
from src.prometheus.core.config import load_config
from src.prometheus.core.db.db_manager import DBManager
from src.prometheus.core.logging.log_manager import LogManager

class StrategyReporter:
    """
    生成最佳策略報告的服務。
    """
    def __init__(self, log_manager: LogManager):
        self.config = load_config()
        self.log_manager = log_manager
        self.logger = self.log_manager.get_logger(__name__)
        self.db_manager = DBManager(self.config["db_path"])

    def generate_report(self) -> str:
        """
        從 evolution_log 中查詢適應度最高的策略並生成報告。

        Returns:
            str: 格式化後的文字報告。如果沒有紀錄則返回提示訊息。
        """
        self.logger.info("正在從資料庫查詢最佳策略...")
        query = "SELECT individual, fitness FROM evolution_log ORDER BY fitness DESC LIMIT 1"

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                result = cursor.execute(query).fetchone()
        except Exception as e:
            self.logger.error(f"查詢最佳策略時發生資料庫錯誤: {e}", exc_info=True)
            return "錯誤：無法從資料庫讀取策略紀錄。"

        if not result:
            self.logger.warning("在 evolution_log 中找不到任何策略紀錄。")
            return "資料庫中尚無任何演化紀錄。"

        best_individual, best_fitness = result
        self.logger.info(f"成功找到最佳策略。基因: {best_individual}, 適應度: {best_fitness}")

        # 格式化報告
        report = f"""
==================================================
<<<<<        雅典娜之鏡：最佳策略報告        >>>>>
==================================================

這是由普羅米修斯演化室產出的當前最優策略。

📈 最高適應度 (Fitness Score):
   {best_fitness:.6f}

🧬 策略基因 (Strategy Genes):
   {best_individual}

==================================================
"""
        return report.strip()
