import time
from src.prometheus.core.config import config
from src.prometheus.core.db.db_manager import DBManager
from src.prometheus.core.logging.log_manager import LogManager
from src.prometheus.core.queue.sqlite_queue import SQLiteQueue
from src.prometheus.services.evolution_chamber import EvolutionChamber

# << 新增函式封裝 >>
def run_evolution(generations: int, population_size: int):
    """
    執行策略演化主流程。

    Args:
        generations (int): 演化的最大世代數。
        population_size (int): 每一代的族群大小。
    """
    log_manager = LogManager()
    logger = log_manager.get_logger(__name__)

    db_manager = DBManager(config.get("database.main_db_path"))
    queue = SQLiteQueue(db_manager)
    evolution_chamber = EvolutionChamber(queue, log_manager)

    logger.info("正在初始化演化室...")
    evolution_chamber.initialize_population(population_size)
    logger.info("演化室初始化完成。")

    for gen in range(generations):
        logger.info(f"--- 開始演化第 {gen + 1} 代 ---")
        evolution_chamber.evolve_one_generation()
        logger.info("等待回測工人完成計算...")

        # 等待所有回測任務完成
        while not queue.is_empty("backtest_tasks"):
            time.sleep(5)

        logger.info("回測計算完成，正在評估適應度...")
        evolution_chamber.evaluate_fitness()
        logger.info(f"--- 第 {gen + 1} 代演化完成 ---")

    best_individual = evolution_chamber.get_best_individual()
    logger.info(f"演化完成！最佳策略基因: {best_individual}")
    logger.info(f"最佳策略適應度: {best_individual.fitness.values[0]}")


# 主程式進入點 (保持不變，用於直接執行)
if __name__ == "__main__":
    # 這裡可以設置預設值或從環境變數讀取
    MAX_GENERATIONS = 50
    POPULATION_SIZE = 100
    run_evolution(generations=MAX_GENERATIONS, population_size=POPULATION_SIZE)
