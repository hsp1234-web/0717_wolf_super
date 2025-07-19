# -*- coding: utf-8 -*-
"""
commander_console.py

普羅米修斯計畫 - 指揮官控制台

此工具是所有離線數據整備任務的唯一入口。
"""

import argparse
import logging
import sys

from src.prometheus.pipelines.p4_stock_factor_generation import main as run_stock_pipeline
from src.prometheus.pipelines.p5_crypto_factor_generation import main as run_crypto_pipeline

# 配置日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def build_feature_store(args):
    """執行建立因子儲存庫的任務。"""
    logger.info("--- 🎬 指令：建立因子儲存庫 (build-feature-store) ---")
    try:
        logger.info("--- 🏭 第一階段：執行股票因子生產線 (P4) ---")
        run_stock_pipeline()
        logger.info("--- ✅ 股票因子生產線 (P4) 執行完畢 ---")

        logger.info("--- 🏭 第二階段：執行加密貨幣因子生產線 (P5) ---")
        run_crypto_pipeline()
        logger.info("--- ✅ 加密貨幣因子生產線 (P5) 執行完畢 ---")

        logger.info("--- 🎉 成功：因子儲存庫已成功建立/更新。 ---")
    except Exception as e:
        logger.error(f"❌ 在建立因子儲存庫過程中發生嚴重錯誤: {e}", exc_info=True)
        sys.exit(1)


def main():
    """主執行函數，解析命令列參數並分派任務。"""
    parser = argparse.ArgumentParser(description="普羅米修斯計畫指揮官控制台")
    subparsers = parser.add_subparsers(dest="command", required=True, help="可用的指令")

    # --- 建立 build-feature-store 指令 ---
    parser_build = subparsers.add_parser(
        "build-feature-store",
        help="執行大規模、離線的批次數據處理，以預先填充完整的「因子儲存庫」。",
    )
    parser_build.set_defaults(func=build_feature_store)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
