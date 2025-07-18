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
