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

    def __init__(self, min_daily_amount: float = None):
        """
        初始化流动性过滤器

        Args:
            min_daily_amount: 最小日成交额（元），默认使用常量5000万元
        """
        from backend.utils.constants import CNMarketConstants
        self.min_daily_amount = min_daily_amount or CNMarketConstants.DEFAULT_MIN_DAILY_AMOUNT

    @property
    def strategy_name(self) -> str:
        return "liquidity_filter"

    def filter(
        self,
        event: MarketEvent,
        fund: CandidateETF,
        signal: TradingSignal
    ) -> tuple[bool, str]:
        """
        判断是否过滤该信号

        使用signal.etf_amount检查ETF流动性。
        """
        # 检查ETF是否有足够的流动性
        if signal.etf_amount <= 0:
            return True, f"ETF成交额异常（¥{signal.etf_amount:,.0f}），流动性无法确认"

        if signal.etf_amount < self.min_daily_amount:
            return True, f"ETF流动性不足（成交额¥{signal.etf_amount:,.0f} < ¥{self.min_daily_amount:,.0f}）"

        return False, ""

    @property
    def is_required(self) -> bool:
        """流动性过滤是必需的"""
        return True
