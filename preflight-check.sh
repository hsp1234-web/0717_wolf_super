#!/bin/bash

# 「領航員」起飛前預檢腳本
# 如果任何命令失敗，立即退出 (-e)
# 如果使用了未定義的變數，立即退出 (-u)
# 如果管線中的任何一個命令失敗，整個管線都算失敗 (-o pipefail)
set -euo pipefail

echo "=== 「領航員」預檢系統啟動 ==="

# --- 第一道防線：靜態掃描 ---
echo ""
echo "1/4: 執行 ruff 靜態掃描，檢查語法與邏輯錯誤..."
poetry run ruff check .
echo "✅ Ruff 檢查通過。"

# --- 第二道防線：依賴檢查 ---
echo ""
echo "2/4: 執行 deptry 依賴檢查，確保依賴完整..."
poetry run deptry .
echo "✅ Deptry 檢查通過。"

# --- 第三道防線：導入鏈點火測試 ---
echo ""
echo "3/4: 執行 pytest 點火測試，驗證導入鏈..."
# 我們只運行 ignition_test.py，以求快速
PYTHONPATH=src poetry run pytest -v tests/ignition_test.py
echo "✅ 點火測試通過。"

# --- 第四道防線：完整單元測試 (可選，但建議) ---
echo ""
echo "4/4: 執行完整的單元測試套件..."
PYTHONPATH=src poetry run pytest -v tests/unit/
echo "✅ 單元測試通過。"

echo ""
echo "==================================="
echo "🎉 【領航員】所有預檢項目通過！"
echo "   系統已準備就緒，可以安全起飛。"
echo "==================================="
