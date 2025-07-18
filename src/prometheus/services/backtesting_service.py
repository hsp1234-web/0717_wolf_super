# -*- coding: utf-8 -*-
"""
回測服務：使用 backtrader 引擎評估單一策略的歷史績效。
"""

import backtrader as bt
import pandas as pd
from prometheus.core.db.db_manager import DBManager
from prometheus.models.strategy_models import PerformanceReport, Strategy


class _FactorStrategy(bt.Strategy):
    """
    一個通用的 backtrader 策略，它根據外部傳入的因子數據和權重來生成交易信號。
    """

    params = (
        ("factors", None),  # 因子名稱列表
        ("weights", None),  # 因子權重字典
    )

    def __init__(self):
        """初始化策略並計算組合信號"""
        self.z_scores = {}
        # 1. 對每個因子計算 Z-score
        for factor in self.p.factors:
            factor_line = getattr(self.data, factor.lower())
            mean = bt.indicators.SimpleMovingAverage(factor_line, period=252, plot=False)
            std = bt.indicators.StandardDeviation(factor_line, period=252, plot=False)
            self.z_scores[factor] = (factor_line - mean) / std

        # 2. 計算加權後的組合信號
        self.combined_signal = 0
        for factor in self.p.factors:
            weight = self.p.weights.get(factor, 0)
            self.combined_signal += self.z_scores[factor] * weight

    def prenext(self):
        self.next()

    def next(self):
        """每個 bar 的決策邏輯"""
        # 直接使用預先計算好的組合信號
        current_signal = self.combined_signal[0]

        # 根據 Z-score 信號的強度進行交易
        # 示例：信號大於 1.5 (強烈買入) 則滿倉, 小於 -1.5 (強烈賣出) 則清倉
        if current_signal > 1.5:
            self.order_target_percent(target=0.95)
        elif current_signal < -1.5:
            self.order_target_percent(target=0.0)
        # 在中間區域可以設置更細緻的倉位管理，此處簡化


class BacktestingService:
    """
    一個使用 backtrader 引擎的獨立、高效的回測服務。
    此服務是整個演化系統的心臟，專職負責精準評估任何單一策略（基因組）的歷史績效。
    """

    def __init__(self, db_manager: DBManager):
        """
        初始化回測服務。

        Args:
            db_manager (DBManager): 用於從數據倉儲讀取因子與價格數據的數據庫管理器。
        """
        self.db_manager = db_manager

    def _load_data(self, strategy: Strategy) -> pd.DataFrame:
        """
        從數據庫加載並合併因子與目標資產價格數據。
        """
        # 1. 加載所有因子數據
        all_factors_df = self.db_manager.fetch_table("factors")
        if "open" not in all_factors_df.columns:
            all_factors_df["open"] = all_factors_df["close"]
            all_factors_df["high"] = all_factors_df["close"]
            all_factors_df["low"] = all_factors_df["close"]
            all_factors_df["volume"] = 0
        # 2. 篩選出策略所需的因子
        required_factors = all_factors_df[["date", "symbol"] + strategy.factors]

        # 3. 加載目標資產的價格數據 (OHLCV)
        price_cols = ["date", "open", "high", "low", "close", "volume"]
        target_prices_df = all_factors_df[all_factors_df["symbol"] == strategy.target_asset][price_cols]

        # 4. 合併數據
        target_prices_df = target_prices_df.drop(columns=["symbol"])
        asset_factors_df = required_factors[required_factors["symbol"] == strategy.target_asset].drop(
            columns=["symbol"]
        )
        merged_df = pd.merge(target_prices_df, asset_factors_df, on="date", how="inner")
        merged_df["date"] = pd.to_datetime(merged_df["date"])
        merged_df = merged_df.set_index("date").sort_index()

        # 確保所有因子列都是數值類型並填充 NaN
        for factor in strategy.factors:
            if factor in merged_df.columns:
                merged_df[factor] = pd.to_numeric(merged_df[factor], errors="coerce").fillna(0)

        # 確保 OHLCV 數據也完整
        for col in ["open", "high", "low", "close", "volume"]:
            if col in merged_df.columns:
                merged_df[col] = pd.to_numeric(merged_df[col], errors="coerce").fillna(method="ffill")

        return merged_df

    def run(self, strategy: Strategy) -> PerformanceReport:
        """
        使用 backtrader 執行一次完整的策略回測。
        """
        cerebro = bt.Cerebro()

        # 1. 數據加載和預處理
        data_df = self._load_data(strategy)
        if data_df.empty or len(data_df) < 2:
            print(f"WARN: 策略 {strategy.target_asset} 的數據不足，跳過回測。")
            return PerformanceReport()

        # 將 pandas DataFrame 轉換為 backtrader 的數據 feed
        # 注意：自定義因子需要作為額外的 "lines" 添加到數據 feed 中
        class PandasDataWithFactors(bt.feeds.PandasData):
            lines = tuple(strategy.factors)
            params = tuple((factor, -1) for factor in strategy.factors)

        data_feed = PandasDataWithFactors(dataname=data_df)
        cerebro.adddata(data_feed)

        # 2. 添加策略
        cerebro.addstrategy(
            _FactorStrategy,
            factors=strategy.factors,
            weights=strategy.weights,
        )

        # 3. 設置初始資金和分析器
        cerebro.broker.setcash(100000.0)
        cerebro.addanalyzer(bt.analyzers.Sharpe, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        # 4. 運行回測
        results = cerebro.run()
        strat = results[0]

        # 5. 提取績效指標
        sharpe_ratio = strat.analyzers.sharpe.get_analysis().get("sharperatio", 0.0)
        annual_return = strat.analyzers.returns.get_analysis().get("rnorm100", 0.0)
        max_drawdown = strat.analyzers.drawdown.get_analysis().get("max", {}).get("drawdown", 0.0)
        total_trades = len(strat.analyzers.trades.get_analysis().get("total", {}).get("closed", []))

        return PerformanceReport(
            sharpe_ratio=float(sharpe_ratio if sharpe_ratio is not None else 0.0),
            annualized_return=float(annual_return),
            max_drawdown=float(max_drawdown),
            total_trades=int(total_trades),
        )
