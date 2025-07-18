# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler

# 從我們的羅盤導入絕對路徑
from .constants import LOG_PATH


def setup_logging(process_name: str):
    """設定統一的日誌系統 (瞭望塔)。"""
    log_formatter = logging.Formatter(f"[{process_name}] %(asctime)s - %(levelname)s - %(message)s")

    # RotatingFileHandler 可以直接接受 pathlib.Path 物件
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    logging.info(f"瞭望塔日誌系統已啟動，日誌將寫入: {LOG_PATH}")
