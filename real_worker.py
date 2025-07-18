#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
舊的「作戰工人」啟動腳本。

為了與現有的執行流程（例如 systemd 或 supervisor 配置）保持相容，
此腳本現在作為一個跳板，調用位於 entrypoints 中的、經過重構的核心邏輯。

要直接運行，請執行：
`poetry run python real_worker.py`
"""

from src.prometheus.entrypoints.real_worker_app import main

if __name__ == "__main__":
    main()
