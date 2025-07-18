# -*- coding: utf-8 -*-
# ==============================================================================
#  磐石協議 (The Bedrock Protocol) v2.0 - 融合「領航員」點火測試
#  導入測試器：ignition_test.py
#
#  功能：
#  - 驗證所有關鍵應用程式入口點 (Gateway, Worker, DB Init) 能否成功導入並實例化。
#  - 自動化、輕量級地嘗試導入專案中的所有模組，以捕獲以下錯誤：
#    1. 循環依賴 (Circular Dependencies)。
#    2. 導入時執行了錯誤的代碼 (Initialization-Time Errors)。
#    3. 某些 Python 版本或環境中才會出現的導入失敗。
#
#  執行方式：
#  - 作為 pytest 測試套件的一部分自動運行。
# ==============================================================================

import importlib
import os
from pathlib import Path
import pytest

# --- 「領航員」指定的關鍵入口點測試 ---

def test_gateway_ignition():
    """
    點火測試：驗證「作戰司令部」(API Gateway) 的導入鏈是否完好。
    這是解決 Gunicorn 靜默失敗問題的關鍵探針。
    """
    try:
        from src.prometheus.entrypoints import query_gateway
        assert query_gateway.app is not None, "FastAPI app instance is missing!"
    except ImportError as e:
        pytest.fail(f"API Gateway 導入失敗，導入鏈可能存在問題: {e}")
    except AttributeError:
        pytest.fail("API Gateway 模組中缺少 'app' 物件，請確認 FastAPI 實例已正確命名並暴露。")
    except Exception as e:
        pytest.fail(f"API Gateway 初始化時發生非預期的錯誤: {e}")


def test_worker_ignition():
    """
    點火測試：驗證「作戰工人」(Real Worker) 的導入鏈是否完好。
    """
    try:
        # 為了可測試性，我們期望 real_worker.py 將其核心應用或對象命名為 `real_worker_app`
        from src.prometheus.entrypoints import real_worker_app
        assert real_worker_app is not None, "Real Worker 的核心應用 (app) 物件不存在。"
    except ImportError as e:
        pytest.fail(f"Real Worker 導入失敗: {e}")
    except AttributeError:
        pytest.fail("Real Worker 模組中缺少 'real_worker_app' 物件，請確認其核心邏輯已被封裝並暴露。")
    except Exception as e:
        pytest.fail(f"Real Worker 初始化時發生非預期的錯誤: {e}")


def test_db_init_ignition():
    """
    點火測試：驗證「地基工程」(DB Init) 腳本的導入鏈是否完好。
    """
    try:
        # 為了可測試性，我們期望 db_init.py 將其核心應用或對象命名為 `db_init_app`
        from src.prometheus.entrypoints import db_init_app
        assert db_init_app is not None, "DB Init 的核心應用 (app) 物件不存在。"
    except ImportError as e:
        pytest.fail(f"DB Init script 導入失敗: {e}")
    except AttributeError:
        pytest.fail("DB Init 模組中缺少 'db_init_app' 物件，請確認其核心邏輯已被封裝並暴露。")
    except Exception as e:
        pytest.fail(f"DB Init script 初始化時發生非預期的錯誤: {e}")


# --- 「磐石協議」通用模組導入測試 ---

# 定義專案的根目錄
PROJECT_ROOT = Path(__file__).parent.parent
# 定義要進行導入測試的源碼目錄
SOURCE_DIRECTORIES = ["src"]
# 定義需要從測試中排除的特定檔案或目錄
EXCLUDE_PATTERNS = [
    "__pycache__",
    "py.typed",
    # 我們已經對 entrypoints 進行了專門的、更深入的測試，此處可排除以避免重複
    "entrypoints",
]

def is_excluded(path: Path, root: Path) -> bool:
    """檢查給定的檔案路徑是否符合任何排除規則。"""
    relative_path_str = str(path.relative_to(root))
    return any(pattern in relative_path_str for pattern in EXCLUDE_PATTERNS)

def discover_modules(root_dir: Path, source_dirs: list[str]) -> list[str]:
    """從指定的源碼目錄中發現所有可導入的 Python 模組。"""
    modules = []
    for source_dir in source_dirs:
        walk_path = root_dir / source_dir
        for root, _, files in os.walk(walk_path):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    file_path = Path(root) / file
                    if not is_excluded(file_path, root_dir):
                        # 將檔案系統路徑轉換為 Python 的模組導入路徑
                        relative_path = file_path.relative_to(root_dir)
                        # 移除 .py 副檔名並將分隔符轉為點
                        module_name = str(relative_path.with_suffix("")).replace(os.sep, ".")
                        modules.append(module_name)
    return modules

all_modules = discover_modules(PROJECT_ROOT, SOURCE_DIRECTORIES)

@pytest.mark.parametrize("module_name", all_modules)
def test_module_ignition_bedrock(module_name: str):
    """對給定的模組名稱執行導入測試（磐石協議）。"""
    try:
        importlib.import_module(module_name)
    except ImportError as e:
        pytest.fail(
            f"🔥 磐石協議：導入模組 '{module_name}' 時發生錯誤: {e}", pytrace=False
        )
    except Exception as e:
        pytest.fail(
            f"💥 磐石協議：模組 '{module_name}' 在導入時崩潰: {e.__class__.__name__}: {e}",
            pytrace=True,
        )
