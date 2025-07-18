from pydantic import BaseModel, Field
from typing import List, Union

class Factor(BaseModel):
    """
    定義單一市場因子的數據結構，與前端契約完全對應。
    """
    category: str = Field(..., description="因子分類，例如 '市場情緒'")
    name: str = Field(..., description="因子名稱，例如 'VIX 恐慌指數'")
    value: str = Field(..., description="當前數值")
    change: float = Field(..., description="變動百分比")
    trend: List[Union[float, int]] = Field(..., description="用於繪製迷你圖的近期趨勢數據")

class MarketSnapshotResponse(BaseModel):
    """
    定義 /api/v1/market_snapshot 端點的回傳數據結構。
    """
    data: List[Factor]

# --- 新增模型 ---
class MasterInsight(BaseModel):
    """ 定義單一大師觀點的數據結構 """
    name: str
    content: str

class ShanJiaLangInitialData(BaseModel):
    """ 定義「週報覆盤」頁面初始化數據的完整結構 """
    week_list: List[str] = Field(..., description="所有可選的週次列表")
    default_week: str = Field(..., description="預設選中的週次")
    raw_content: str = Field(..., description="預設週次的原始文本內容")
    master_insights: List[MasterInsight] = Field(..., description="所有可選的大師觀點列表")

# --- 新增 AI 分析請求模型 ---
class AIAnalysisRequest(BaseModel):
    """
    定義提交給 AI 進行初步分析的請求數據結構。
    """
    raw_content: str = Field(..., description="當週的原始文本")
    selected_masters: List[str] = Field(..., description="用戶選擇融合的大師觀點名稱列表")

# --- 新增回測相關模型 ---
class BacktestRequest(BaseModel):
    """
    定義提交策略回測的請求數據結構。
    """
    strategy_code: str = Field(..., description="包含完整策略邏輯的 Python 程式碼字串")
    strategy_name: str = Field("未命名策略", description="策略的名稱")

class BacktestResult(BaseModel):
    """
    定義回測績效報告的數據結構。
    """
    annualized_return: float = Field(..., description="年化報酬率")
    max_drawdown: float = Field(..., description="最大回撤")
    sharpe_ratio: float = Field(..., description="夏普比率")
    win_rate: float = Field(..., description="勝率")
    equity_curve: List[float] = Field(..., description="用於繪製權益曲線的數據點")
