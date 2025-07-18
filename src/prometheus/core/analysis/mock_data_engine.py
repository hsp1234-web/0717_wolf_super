from typing import List
from ...models.snapshot_models import Factor, MasterInsight, ShanJiaLangInitialData

class MockDataEngine:
    """
    一個模擬的數據引擎，用於在開發階段提供穩定的因子與情報數據。
    """
    def get_market_factors(self) -> List[Factor]:
        """
        回傳與前端模擬數據完全一致的因子列表。
        """
        mock_data = [
            { "category": '市場情緒', "name": 'VIX 恐慌指數', "value": '13.5', "change": -5.2, "trend": [14.2, 14.1, 13.9, 13.6, 13.5, 13.8, 13.6, 13.5] },
            { "category": '市場情緒', "name": 'Put/Call Ratio', "value": '0.85', "change": 10.1, "trend": [0.75, 0.78, 0.80, 0.82, 0.85, 0.83, 0.84, 0.85] },
            { "category": '宏觀經濟', "name": '美國十年債利率', "value": '4.21%', "change": -0.9, "trend": [4.28, 4.26, 4.25, 4.22, 4.21, 4.23, 4.22, 4.21] },
            { "category": '籌碼面 (台股)', "name": '外資期貨未平倉', "value": '-8,500', "change": 25.1, "trend": [-4500, -5000, -6800, -7200, -8500, -7500, -8000, -8500] },
            { "category": '技術分析', "name": '市場寬度 (>50MA)', "value": '65%', "change": 8.0, "trend": [55, 58, 60, 62, 65, 63, 64, 65] },
        ]
        return [Factor(**item) for item in mock_data]

    def get_shan_jia_lang_initial_data(self) -> ShanJiaLangInitialData:
        """
        提供「週報覆盤」頁面所需的初始化數據。
        """
        weekly_raw_content = {
            "2025年第14週": "**作者**：善甲狼a機智生活\n**標題**：買黃金跟債券避險\n**日期**：2025-03-31\n**文章內容**：\n買黃金跟債券避險\n484不如買 #VIX 阿?",
            "2025年第13週": "**作者**：善甲狼a機智生活\n**標題**：風平浪靜的一週\n**日期**：2025-03-24\n**文章內容**：\n本週市場波瀾不驚。"
        }
        master_insights_data = {
            '交易醫生': '核心策略: 跳空SOP1(逆勢封閉缺口), 跳空SOP2(順勢追擊)。',
            '刀疤老二': '核心策略: 順勢而為，在上升趨勢中的回檔買進。',
            'Vincent余鄭文': '核心策略: 投資框架三部曲(選對公司、等對價格、計劃下注)。'
        }

        week_keys = list(weekly_raw_content.keys())
        default_week = week_keys[0]

        return ShanJiaLangInitialData(
            week_list=week_keys,
            default_week=default_week,
            raw_content=weekly_raw_content[default_week],
            master_insights=[MasterInsight(name=k, content=v) for k, v in master_insights_data.items()]
        )
