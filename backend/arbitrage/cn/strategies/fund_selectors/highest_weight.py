"""
最高权重选择策略

从符合条件的ETF中选择权重最高的。
这是最直接的策略，权重高意味着该事件对ETF影响最大。
"""

from backend.arbitrage.cn.strategies.interfaces import IFundSelector
from backend.market.events import MarketEvent
from backend.arbitrage.strategy_registry import fund_selector_registry
from backend.market import CandidateETF
from backend.utils.constants import CNMarketConstants
from typing import List, Optional


@fund_selector_registry.register(
    "highest_weight",
    priority=100,
    description="选择权重最高的ETF",
    version="1.0.0"
)
class HighestWeightSelector(IFundSelector):
    """
    最高权重选择策略

    从符合条件的ETF中选择权重最高的。
    这是最直接的策略，权重高意味着该事件对ETF影响最大。
    """

    def __init__(self, min_weight: float = None):
        """
        初始化最高权重选择器

        Args:
            min_weight: 最小权重阈值（默认使用A股默认阈值5%）
        """
        self.min_weight = min_weight if min_weight is not None else CNMarketConstants.DEFAULT_MIN_WEIGHT

    @property
    def strategy_name(self) -> str:
        return "highest_weight"

    def select(
        self,
        eligible_funds: List[CandidateETF],
        event: MarketEvent
    ) -> Optional[CandidateETF]:
        """
        选择权重最高的ETF

        Args:
            eligible_funds: 符合条件的ETF列表（已按权重筛选）
            event: 触发事件

        Returns:
            选中的ETF，无符合条件的返回None
        """
        if not eligible_funds:
            return None

        # 按权重降序排序，选择第一个
        return sorted(eligible_funds, key=lambda x: x.weight, reverse=True)[0]

    def get_selection_reason(self, fund: CandidateETF) -> str:
        """获取选择原因"""
        return f"权重最高({fund.weight_pct:.2f}%)"
