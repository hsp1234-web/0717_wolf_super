# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

# 從我們的羅盤導入絕對路徑
from .constants import LOG_PATH


def setup_logging(process_name: str):
    """設定統一的日誌系統 (瞭望塔)。"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 如果已經有處理器，先清除，避免重複記錄
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- JSON 檔案日誌處理器 ---
    # 這裡我們使用自訂的格式，包含了 process_name
    log_formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s %(process_name)s"
    )

    # RotatingFileHandler 可以直接接受 pathlib.Path 物件
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    # --- 主控台日誌處理器 (可選，用於本地調試) ---
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        f"[{process_name}] - %(asctime)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 注入額外的上下文
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.process_name = process_name
        return record

    logging.setLogRecordFactory(record_factory)

    logging.info(f"瞭望塔 JSON 日誌系統已啟動，日誌將寫入: {LOG_PATH}")
