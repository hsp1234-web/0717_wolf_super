# -*- coding: utf-8 -*-
"""
策略報告生成器。
"""

import os
from typing import List

from deap import tools
from prometheus.models.strategy_models import PerformanceReport


class StrategyReporter:
    """
    將演化過程中發現的最優策略，生成一份清晰的報告。
    """

    def __init__(self, report_dir: str = "reports"):
        self.report_dir = report_dir
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)

    def generate_report(
        self, best_individual: tools.HallOfFame, performance_report: PerformanceReport, available_factors: List[str]
    ):
        """
        生成並儲存策略報告。

        Args:
            best_individual (tools.HallOfFame): 包含最優個體的名人堂。
            performance_report (PerformanceReport): 最優個體的回測績效報告。
            available_factors (List[str]): 所有可用因子的列表。
        """
        if not best_individual:
            print("WARN: 名人堂為空，無法生成報告。")
            return

        best_strategy_indices = best_individual[0]
        best_strategy_factors = [available_factors[i] for i in best_strategy_indices]

        report_content = f"""# 【普羅米修斯之火：最優策略報告】

演化完成，這是本次發現的最佳策略詳細資訊。

## 📈 核心績效指標

| 指標                        | 數值                  |
| --------------------------- | --------------------- |
| 夏普比率 (Sharpe Ratio)     | {performance_report.sharpe_ratio:.4f} |
| 年化報酬率 (Annualized Return) | {performance_report.annualized_return:.2%}  |
| 最大回撤 (Max Drawdown)     | {performance_report.max_drawdown:.2%}   |
| 總交易天數 (Total Trades)   | {performance_report.total_trades}     |

## 🧬 策略基因構成

此策略由以下 **{len(best_strategy_factors)}** 個因子等權重構成：

```
{', '.join(best_strategy_factors)}
```
"""
        report_path = os.path.join(self.report_dir, "best_strategy_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"✅ 策略報告已成功生成於: {report_path}")
