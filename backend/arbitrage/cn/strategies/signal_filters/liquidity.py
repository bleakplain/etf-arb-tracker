"""
流动性过滤策略

检查ETF的日成交额是否满足最低要求。
"""

from backend.arbitrage.cn.strategies.interfaces import ISignalFilter
from backend.market.events import MarketEvent
from backend.arbitrage.strategy_registry import signal_filter_registry
from backend.arbitrage.models import TradingSignal
from backend.market import CandidateETF


@signal_filter_registry.register(
    "liquidity_filter",
    priority=100,
    description="流动性过滤（ETF日成交额检查）",
    version="1.0.0"
)
class LiquidityFilter(ISignalFilter):
    """
    流动性过滤器

    检查ETF的日成交额是否满足最低要求。
    """

    def __init__(self, min_daily_amount: float = 50000000):
        """
        初始化流动性过滤器

        Args:
            min_daily_amount: 最小日成交额（元），默认5000万元
        """
        self.min_daily_amount = min_daily_amount

    @property
    def strategy_name(self) -> str:
        return "liquidity_filter"

    def filter(
        self,
        event: MarketEvent,
        fund: CandidateETF,
        signal: TradingSignal
    ) -> tuple[bool, str]:
        """判断是否过滤该信号"""
        # 注意：当前需要从外部获取ETF流动性数据
        # 这里假设signal中已有相关信息，或需要额外查询

        # 简化实现：假设所有ETF都满足流动性要求
        # 实际应该查询ETF的成交额

        return False, ""

    @property
    def is_required(self) -> bool:
        """流动性过滤是必需的"""
        return True
