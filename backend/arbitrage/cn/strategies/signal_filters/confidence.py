"""
置信度过滤策略

过滤掉置信度过低的信号。
"""

from backend.arbitrage.cn.strategies.interfaces import ISignalFilter
from backend.market.domain.events import MarketEvent
from backend.arbitrage.strategy_registry import signal_filter_registry
from backend.arbitrage.models import TradingSignal
from backend.market.domain import CandidateETF


@signal_filter_registry.register(
    "confidence_filter",
    priority=40,
    description="置信度过滤（最低置信度要求）",
    version="1.0.0"
)
class ConfidenceFilter(ISignalFilter):
    """
    置信度过滤器

    过滤掉置信度过低的信号。
    """

    def __init__(self, min_confidence: str = "中"):
        """
        初始化置信度过滤器

        Args:
            min_confidence: 最低置信度要求（"低"/"中"/"高"）
        """
        confidence_order = {"低": 1, "中": 2, "高": 3}
        self.min_confidence_level = confidence_order.get(min_confidence, 2)

    @property
    def strategy_name(self) -> str:
        return "confidence_filter"

    def filter(
        self,
        event: MarketEvent,
        fund: CandidateETF,
        signal: TradingSignal
    ) -> tuple[bool, str]:
        """判断是否过滤该信号"""
        confidence_order = {"低": 1, "中": 2, "高": 3}
        signal_level = confidence_order.get(signal.confidence, 2)

        if signal_level < self.min_confidence_level:
            return True, f"置信度过低（{signal.confidence}）"

        return False, ""

    @property
    def is_required(self) -> bool:
        """置信度过滤不是必需的"""
        return False
