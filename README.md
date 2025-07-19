# 普羅米修斯計畫：記憶聖約

本文件是普羅米修斯計畫的「活的儀表板」，是專案能力的唯一入口。

## 系統能力清單

| 能力 | 描述 | 執行命令 |
| :--- | :--- | :--- |
| 🚀 **啟動核心服務** | 啟動 Gunicorn API 伺服器與背景工人蜂群。 | `poetry run python run.py start-services` |
| 🛠️ **建立因子儲存庫** | 執行所有資料管線，建立股票與加密貨幣的完整因子儲存庫。 | `poetry run python commander_console.py build-feature-store` |
| 🧠 **演化交易策略** | 啟動遺傳演算法，自動演化交易策略。 | `poetry run python commander_console.py evolve-strategies` |
| 📊 **報告最佳策略** | 顯示演化出的最佳策略的詳細報告。 | `poetry run python commander_console.py report-best-strategy` |
| ✅ **作戰資格預檢驗** | 執行全面的靜態分析、依賴檢查、整合與 E2E 測試。 | `bash preflight-check.sh` |
| ⚡ **快速整合檢查** | 執行一組快速的靜態分析與核心整合測試。 | `bash rapid-check.sh` |
