"""
最佳流动性选择策略

从符合条件的ETF中选择流动性最好的。
流动性好意味着更容易买卖，滑点更小。
"""

from backend.arbitrage.cn.strategies.interfaces import IFundSelector
from backend.market.events import MarketEvent
from backend.arbitrage.strategy_registry import fund_selector_registry
from backend.market import CandidateETF
from typing import List, Optional


@fund_selector_registry.register(
    "best_liquidity",
    priority=75,
    description="选择流动性最好的ETF",
    version="1.0.0"
)
class BestLiquiditySelector(IFundSelector):
    """
    最佳流动性选择策略

    从符合条件的ETF中选择流动性最好的。
    流动性好意味着更容易买卖，滑点更小。
    """

    def __init__(self):
        """初始化流动性选择器"""
        pass

    @property
    def strategy_name(self) -> str:
        return "best_liquidity"

    def select(
        self,
        eligible_funds: List[CandidateETF],
        event: MarketEvent
    ) -> Optional[CandidateETF]:
        """
        选择流动性最好的ETF

        注意：当前CandidateETF没有流动性信息，
        实际使用时需要扩展CandidateETF或从外部获取流动性数据

        Args:
            eligible_funds: 符合条件的ETF列表
            event: 触发事件

        Returns:
            选中的ETF
        """
        if not eligible_funds:
            return None

        # 简化实现：选择权重最高的（假设权重高通常流动性也好）
        # 实际应该查询ETF的成交额
        return sorted(eligible_funds, key=lambda x: x.weight, reverse=True)[0]

    def get_selection_reason(self, fund: CandidateETF) -> str:
        """获取选择原因"""
        return "流动性最好"
