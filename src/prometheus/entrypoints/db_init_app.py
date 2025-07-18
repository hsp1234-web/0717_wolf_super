# -*- coding: utf-8 -*-
"""
「地基工程」(DB Init) 的點火測試代理。

這個模組本身不包含複雜的邏輯。它的主要目的是作為一個「探針」，
在被導入時，會觸發對核心 CLI 應用程式 (`src.prometheus.cli.main`) 的導入。

如果 CLI 應用程式或其任何依賴存在語法錯誤、循環導入或其他導入時的致命問題，
導入此模組將會失敗，從而讓我們的 `ignition_test.py` 能夠捕獲到這些問題。
"""

try:
    # 我們嘗試從核心 CLI 應用程式中導入 typer app 物件。
    # 這個導入動作本身就是一個測試。如果成功，代表 CLI 模組及其所有子依賴都是可導入的。
    from src.prometheus.cli.main import app as cli_app

    # 我們將導入的 app 物件賦值給 db_init_app，以便 ignition_test.py 可以對其進行斷言。
    # 這樣做可以確保導入不僅成功，而且我們期望的物件也確實存在。
    db_init_app = cli_app

except ImportError as e:
    # 如果導入失敗，我們將 db_init_app 設置為 None，並讓測試框架來報告錯誤。
    # 這裡不拋出異常，是為了讓 `ignition_test.py` 中的 try-except 結構能夠捕獲並提供更豐富的上下文。
    db_init_app = None
    print(f"在導入 'db_init_app' 代理時發生錯誤: {e}")

except Exception as e:
    # 捕捉其他可能的非導入錯誤
    db_init_app = None
    print(f"在初始化 'db_init_app' 代理時發生非預期錯誤: {e}")
