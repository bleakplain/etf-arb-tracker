"""
综合评估选择策略

综合考虑权重、流动性、溢价等多个因素，
通过打分机制选择最优ETF。
"""

from backend.arbitrage.cn.strategies.interfaces import IFundSelector
from backend.market.events import MarketEvent
from backend.arbitrage.strategy_registry import fund_selector_registry
from backend.market import CandidateETF


@fund_selector_registry.register(
    "balanced",
    priority=50,
    description="综合评估选择（平衡权重、流动性、溢价）",
    version="1.0.0"
)
class BalancedSelector(IFundSelector):
    """
    综合评估选择策略

    综合考虑权重、流动性、溢价等多个因素，
    通过打分机制选择最优ETF。
    """

    def __init__(
        self,
        weight_score: float = 0.5,    # 权重得分权重
        liquidity_score: float = 0.3, # 流动性得分权重
        premium_score: float = 0.2     # 溢价得分权重
    ):
        """
        初始化综合选择器

        Args:
            weight_score: 权重因子权重
            liquidity_score: 流动性因子权重
            premium_score: 溢价因子权重
        """
        self.weight_score = weight_score
        self.liquidity_score = liquidity_score
        self.premium_score = premium_score

    @property
    def strategy_name(self) -> str:
        return "balanced"

    def select(
        self,
        eligible_funds: list[CandidateETF],
        event: MarketEvent
    ) -> CandidateETF | None:
        """
        综合评估选择最优ETF

        Args:
            eligible_funds: 符合条件的ETF列表
            event: 触发事件

        Returns:
            综合得分最高的ETF
        """
        if not eligible_funds:
            return None

        # 简化实现：计算综合得分
        def calc_score(fund: CandidateETF) -> float:
            # 权重得分（归一化到0-1）
            weight_score = min(fund.weight / 0.20, 1.0)

            # 这里可以添加流动性和溢价的计算
            # 当前简化为只使用权重

            return weight_score * self.weight_score

        # 选择得分最高的
        return sorted(eligible_funds, key=calc_score, reverse=True)[0]

    def get_selection_reason(self, fund: CandidateETF) -> str:
        """获取选择原因"""
        return f"综合评估最优（权重{fund.weight_pct:.2f}%）"
