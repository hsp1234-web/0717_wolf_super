# -*- coding: utf-8 -*-
from pathlib import Path

# --- pathlib 驅動的絕對路徑定義中心 (羅盤) ---
# 獲取專案的絕對根目錄，無論此腳本在哪裡被調用
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# 定義所有共享資源的絕對路徑 (Path 物件)
DB_PATH = PROJECT_ROOT / "tasks.sqlite"
LOG_PATH = PROJECT_ROOT / "prometheus_system.log"
CONFIG_PATH = PROJECT_ROOT / "config.yml"
WEB_DIR = PROJECT_ROOT / "src" / "prometheus" / "web"

print(f"[*] 羅盤已使用 pathlib 校準 - 資料庫路徑: {DB_PATH}")
