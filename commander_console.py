"""
普羅米修斯計畫指揮官控制台
"""
import typer
from src.prometheus.pipelines.p4_stock_factor_generation import P4_StockFactorGeneration
from src.prometheus.pipelines.p5_crypto_factor_generation import P5_CryptoFactorGeneration
from src.prometheus.entrypoints.evolution_app import run_evolution  # << 新增導入
from src.prometheus.core.logging.log_manager import LogManager

# 初始化應用
app = typer.Typer()
log_manager = LogManager()

@app.command(name="build-feature-store", help="建立並填充所有資產類別的因子儲存庫。")
def build_feature_store():
    """
    執行所有資料管線，建立完整的因子儲存庫。
    """
    logger = log_manager.get_logger(__name__)
    logger.info("====== 指揮官命令：開始建立因子儲存庫 ======")

    # 執行 P4 股票因子管線
    logger.info("--- 正在執行 P4 股票因子生成管線 ---")
    p4_pipeline = P4_StockFactorGeneration()
    p4_pipeline.run()
    logger.info("--- P4 股票因子生成管線執行完畢 ---")

    # 執行 P5 加密貨幣因子管線
    logger.info("--- 正在執行 P5 加密貨幣因子生成管線 ---")
    p5_pipeline = P5_CryptoFactorGeneration()
    p5_pipeline.run()
    logger.info("--- P5 加密貨幣因子生成管線執行完畢 ---")

    logger.info("====== 因子儲存庫已成功建立！ ======")

# << 新增區塊開始 >>
@app.command(name="evolve-strategies", help="啟動遺傳演算法，自動演化交易策略。")
def evolve_strategies(
    max_generations: int = typer.Option(50, "--generations", "-g", help="演化的最大世代數。"),
    population_size: int = typer.Option(100, "--population", "-p", help="每一代的族群大小。")
):
    """
    啟動策略演化室，尋找最佳交易策略。
    """
    logger = log_manager.get_logger(__name__)
    logger.info("====== 指揮官命令：啟動策略演化室 ======")
    logger.info(f"最大世代數: {max_generations}, 族群大小: {population_size}")

    try:
        run_evolution(generations=max_generations, population_size=population_size)
        logger.info("====== 策略演化任務成功完成！ ======")
    except Exception as e:
        logger.error(f"策略演化過程中發生致命錯誤: {e}", exc_info=True)
        raise typer.Exit(code=1)
# << 新增區塊結束 >>

if __name__ == "__main__":
    app()
