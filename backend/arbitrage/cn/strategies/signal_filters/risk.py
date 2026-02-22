"""
风险过滤策略

检查ETF的风险指标，如持仓集中度过高等。
"""

from backend.arbitrage.cn.strategies.interfaces import ISignalFilter
from backend.market.domain.events import MarketEvent
from backend.arbitrage.strategy_registry import signal_filter_registry
from backend.arbitrage.models import TradingSignal
from backend.market.domain import CandidateETF


@signal_filter_registry.register(
    "risk_filter",
    priority=50,
    description="风险过滤（持仓集中度、前10占比等）",
    version="1.0.0"
)
class RiskFilter(ISignalFilter):
    """
    风险过滤器

    检查ETF的风险指标，如持仓集中度过高等。
    """

    def __init__(
        self,
        max_top10_ratio: float = 0.70,  # 前10持仓最大占比
        min_rank: int = 1                # 最小排名要求
    ):
        """
        初始化风险过滤器

        Args:
            max_top10_ratio: 前10持仓最大占比
            min_rank: 排名要求（0表示不限制）
        """
        self.max_top10_ratio = max_top10_ratio
        self.min_rank = min_rank

    @property
    def strategy_name(self) -> str:
        return "risk_filter"

    def filter(
        self,
        event: MarketEvent,
        fund: CandidateETF,
        signal: TradingSignal
    ) -> tuple[bool, str]:
        """判断是否过滤该信号"""
        # 检查持仓集中度
        if fund.top10_ratio > self.max_top10_ratio:
            return True, f"持仓过于集中（前10占比{fund.top10_ratio*100:.1f}%）"

        # 检查排名
        if self.min_rank > 0 and fund.rank > self.min_rank:
            return True, f"排名过低（第{fund.rank}名）"

        return False, ""

    @property
    def is_required(self) -> bool:
        """风险过滤不是必需的（仅警告）"""
        return False
