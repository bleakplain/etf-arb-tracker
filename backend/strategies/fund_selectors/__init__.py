"""
基金选择策略包

定义各种基金（ETF/LOF等）选择策略：
- HighestWeightSelector: 选择权重最高的
- BestLiquiditySelector: 选择流动性最好的
- LowestPremiumSelector: 选择溢价最低的
- BalancedSelector: 综合评估选择
"""

from backend.domain.strategy_interfaces import IFundSelectionStrategy, EventInfo
from backend.core.strategy_registry import fund_selector_registry
from backend.domain.value_objects import ETFReference
from typing import List, Optional


@fund_selector_registry.register(
    "highest_weight",
    priority=100,
    description="选择权重最高的ETF",
    version="1.0.0"
)
class HighestWeightSelector(IFundSelectionStrategy):
    """
    最高权重选择策略

    从符合条件的ETF中选择权重最高的。
    这是最直接的策略，权重高意味着该事件对ETF影响最大。
    """

    def __init__(self, min_weight: float = 0.05):
        """
        初始化最高权重选择器

        Args:
            min_weight: 最小权重阈值
        """
        self.min_weight = min_weight

    @property
    def strategy_name(self) -> str:
        return "highest_weight"

    def select(
        self,
        eligible_funds: List[ETFReference],
        event: EventInfo
    ) -> Optional[ETFReference]:
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

    def get_selection_reason(self, fund: ETFReference) -> str:
        """获取选择原因"""
        return f"权重最高({fund.weight_pct:.2f}%)"


@fund_selector_registry.register(
    "best_liquidity",
    priority=75,
    description="选择流动性最好的ETF",
    version="1.0.0"
)
class BestLiquiditySelector(IFundSelectionStrategy):
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
        eligible_funds: List[ETFReference],
        event: EventInfo
    ) -> Optional[ETFReference]:
        """
        选择流动性最好的ETF

        注意：当前ETFReference没有流动性信息，
        实际使用时需要扩展ETFReference或从外部获取流动性数据

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

    def get_selection_reason(self, fund: ETFReference) -> str:
        """获取选择原因"""
        return "流动性最好"


@fund_selector_registry.register(
    "lowest_premium",
    priority=60,
    description="选择溢价最低的ETF",
    version="1.0.0"
)
class LowestPremiumSelector(IFundSelectionStrategy):
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
        eligible_funds: List[ETFReference],
        event: EventInfo
    ) -> Optional[ETFReference]:
        """
        选择溢价最低的ETF

        注意：当前ETFReference没有溢价信息，
        实际使用时需要从外部获取ETF的实时溢价

        Args:
            eligible_funds: 符合条件的ETF列表
            event: 触发事件

        Returns:
            选中的ETF
        """
        if not eligible_funds:
            return None

        # 简化实现：选择权重最高的
        # 实际应该查询ETF的溢价率
        return sorted(eligible_funds, key=lambda x: x.weight, reverse=True)[0]

    def get_selection_reason(self, fund: ETFReference) -> str:
        """获取选择原因"""
        return "溢价最低"


@fund_selector_registry.register(
    "balanced",
    priority=50,
    description="综合评估选择（平衡权重、流动性、溢价）",
    version="1.0.0"
)
class BalancedSelector(IFundSelectionStrategy):
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
        eligible_funds: List[ETFReference],
        event: EventInfo
    ) -> Optional[ETFReference]:
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
        def calc_score(fund: ETFReference) -> float:
            # 权重得分（归一化到0-1）
            weight_score = min(fund.weight / 0.20, 1.0)

            # 这里可以添加流动性和溢价的计算
            # 当前简化为只使用权重

            return weight_score * self.weight_score

        # 选择得分最高的
        return sorted(eligible_funds, key=calc_score, reverse=True)[0]

    def get_selection_reason(self, fund: ETFReference) -> str:
        """获取选择原因"""
        return f"综合评估最优（权重{fund.weight_pct:.2f}%）"
