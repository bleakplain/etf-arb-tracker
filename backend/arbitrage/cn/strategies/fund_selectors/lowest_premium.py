"""
最低溢价选择策略

从符合条件的ETF中选择溢价最低的。
溢价低意味着买入成本更接近实际价值。
"""

from backend.arbitrage.cn.strategies.interfaces import IFundSelector
from backend.market.events import MarketEvent
from backend.arbitrage.strategy_registry import fund_selector_registry
from backend.market import CandidateETF


@fund_selector_registry.register(
    "lowest_premium",
    priority=60,
    description="选择溢价最低的ETF",
    version="1.0.0"
)
class LowestPremiumSelector(IFundSelector):
    """
    最低溢价选择策略

    从符合条件的ETF中选择溢价最低的。
    溢价低意味着买入成本更接近实际价值。
    """

    def __init__(self):
        """初始化溢价选择器"""
        pass

    @property
    def strategy_name(self) -> str:
        return "lowest_premium"

    def select(
        self,
        eligible_funds: list[CandidateETF],
        event: MarketEvent
    ) -> CandidateETF | None:
        """
        选择溢价最低的ETF

        Args:
            eligible_funds: 符合条件的ETF列表
            event: 触发事件

        Returns:
            选中的ETF
        """
        return self.select_by_weight(eligible_funds)

    def get_selection_reason(self, fund: CandidateETF) -> str:
        """获取选择原因"""
        return "溢价最低"
