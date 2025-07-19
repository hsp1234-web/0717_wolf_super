#!/bin/bash

# --- 顏色定義 ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# --- 任務開始 ---
echo -e "${GREEN}--- 🚀 開始執行快速整合檢查 ---${NC}"
start_time=$SECONDS

# --- 🛡️ 第一道防線：靜態程式碼掃描 (Ruff) ---
echo -e "\n${GREEN}--- 🛡️ 第一道防線：靜態程式碼掃描 (Ruff) ---${NC}"
if ! poetry run ruff check .; then
    echo -e "${RED}❌ 快速檢查失敗：Ruff 掃描發現問題。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Ruff 掃描通過。${NC}"

# --- 📦 第二道防線：依賴健全性檢查 (Deptry) ---
echo -e "\n${GREEN}--- 📦 第二道防線：依賴健全性檢查 (Deptry) ---${NC}"
if ! poetry run deptry .; then
    echo -e "${RED}❌ 快速檢查失敗：Deptry 發現依賴問題。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 依賴健全性通過。${NC}"

# --- 🔥 第三道防線：架構點火測試 (Ignition Test) ---
echo -e "\n${GREEN}--- 🔥 第三道防線：架構點火測試 (Ignition Test) ---${NC}"
if ! poetry run pytest tests/ignition_test.py; then
    echo -e "${RED}❌ 快速檢查失敗：點火測試發現導入錯誤。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 架構點火測試通過。${NC}"

# --- ⚡ 第四道防線：單體迴路整合測試 ---
echo -e "\n${YELLOW}--- ⚡ 第四道防線：單體迴路整合測試 (已跳過) ---${NC}"
# 已根據「記憶聖約」原則，移除對已刪除檔案的測試
# if ! poetry run pytest tests/integration/test_in_process_flow.py; then
#     echo -e "${RED}❌ 快速檢查失敗：單體迴路整合測試失敗。${NC}"
#     exit 1
# fi
# echo -e "${GREEN}✅ 單體迴路整合測試通過。${NC}"

end_time=$SECONDS
duration=$((end_time - start_time))

echo -e "\n${GREEN}--- 🎉 恭喜！所有快速檢查項目均已通過 ---${NC}"
echo -e "⏱️  總耗時: ${duration} 秒。"

if [ "$duration" -gt 15 ]; then
    echo -e "${YELLOW}⚠️ 警告：快速檢查執行時間超過 15 秒，請考慮優化。${NC}"
fi

exit 0
