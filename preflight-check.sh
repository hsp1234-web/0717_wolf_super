#!/bin/bash
#
# 【普羅米修斯】作戰資格預檢驗腳本
# 在提交任何程式碼前，必須 100% 通過此腳本的所有檢查。
#

# 設置顏色
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}--- 🚀 開始執行作戰資格預檢驗 ---${NC}"

# 第一道防線：靜態掃描 (Ruff)
echo -e "\n${GREEN}--- 🛡️ 第一道防線：靜態程式碼掃描 (Ruff) ---${NC}"
poetry run ruff check . && poetry run ruff format . --check
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 預檢驗失敗：Ruff 掃描發現問題。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Ruff 掃描通過。${NC}"

# 第二道防線：依賴檢查 (Deptry)
echo -e "\n${GREEN}--- 📦 第二道防線：依賴健全性檢查 (Deptry) ---${NC}"
poetry run deptry .
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 預檢驗失敗：Deptry 發現依賴問題。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 依賴健全性通過。${NC}"

# 第三道防線：點火測試 (Ignition Test)
echo -e "\n${GREEN}--- 🔥 第三道防線：架構點火測試 (Ignition Test) ---${NC}"
poetry run pytest -m smoke
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 預檢驗失敗：點火測試發現導入錯誤。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 架構點火測試通過。${NC}"

echo -e "\n${GREEN}--- 🎉 恭喜！所有預檢驗項目均已通過 ---${NC}"
exit 0
