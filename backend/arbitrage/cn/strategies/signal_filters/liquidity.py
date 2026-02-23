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

        从signal.etf_premium字段推断成交额信息。
        如果信号创建时已获取ETF行情，这里应检查成交额。
        """
        # 检查ETF是否有足够的流动性
        # 这里通过检查signal的隐含信息来判断
        # 实际流动性数据需要在生成signal时从etf_quote中获取

        # 简化实现：如果有ETF价格信息，假设流动性满足要求
        # 生产环境应通过etf_quote_provider.get_etf_quote()获取真实成交额
        if signal.etf_price <= 0:
            return True, "ETF价格异常，流动性无法确认"

        # TODO: 从etf_quote中获取amount进行真实流动性检查
        # 当前简化实现：假设所有价格正常的ETF都满足流动性要求
        return False, ""

    @property
    def is_required(self) -> bool:
        """流动性过滤是必需的"""
        return True
