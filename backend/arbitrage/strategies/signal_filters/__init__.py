"""
信号过滤策略包

定义各种信号过滤策略：
- TimeFilter: 时间过滤（距收盘时间检查）
- LiquidityFilter: 流动性过滤
- RiskFilter: 风险过滤（持仓集中度等）
- ConfidenceFilter: 置信度过滤
"""

from backend.arbitrage.domain.interfaces import ISignalFilterStrategy
from backend.arbitrage.strategy_registry import signal_filter_registry
from backend.arbitrage.domain.interfaces import EventInfo
from backend.arbitrage.domain.models import TradingSignal
from backend.market.domain import CandidateETF
from typing import Dict
from datetime import datetime


@signal_filter_registry.register(
    "time_filter",
    priority=100,
    description="时间过滤（距收盘时间检查）",
    version="1.0.0"
)
class TimeFilter(ISignalFilterStrategy):
    """
    时间过滤器

    检查距离收盘的时间，避免在收盘前太短时间内发出信号。
    """

    def __init__(self, min_time_to_close: int = 1800):
        """
        初始化时间过滤器

        Args:
            min_time_to_close: 距收盘最小时间（秒），默认30分钟
        """
        self.min_time_to_close = min_time_to_close

    @property
    def filter_name(self) -> str:
        return "time_filter"

    def should_filter(
        self,
        event: EventInfo,
        fund: CandidateETF,
        signal: TradingSignal
    ) -> tuple[bool, str]:
        """
        判断是否过滤该信号

        Args:
            event: 触发事件
            fund: 选择的基金
            signal: 生成的信号

        Returns:
            (should_filter, reason) - (是否过滤, 过滤原因)
        """
        time_to_close = self._get_time_to_close()

        # 不在交易时间
        if time_to_close < 0:
            return True, "当前不在交易时间"

        # 距收盘太近
        if 0 < time_to_close < self.min_time_to_close:
            minutes = time_to_close // 60
            return True, f"距收盘仅{minutes}分钟，时间不足"

        return False, ""

    @staticmethod
    def _get_time_to_close() -> int:
        """获取距离收盘的秒数"""
        now = datetime.now()
        close_time = now.replace(hour=15, minute=0, second=0, microsecond=0)

        if now.hour < 9 or now.hour >= 15:
            return -1

        delta = close_time - now
        return int(delta.total_seconds())

    def is_required(self) -> bool:
        """时间过滤是必需的"""
        return True


@signal_filter_registry.register(
    "liquidity_filter",
    priority=100,
    description="流动性过滤（ETF日成交额检查）",
    version="1.0.0"
)
class LiquidityFilter(ISignalFilterStrategy):
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
    def filter_name(self) -> str:
        return "liquidity_filter"

    def should_filter(
        self,
        event: EventInfo,
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


@signal_filter_registry.register(
    "risk_filter",
    priority=50,
    description="风险过滤（持仓集中度、前10占比等）",
    version="1.0.0"
)
class RiskFilter(ISignalFilterStrategy):
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
    def filter_name(self) -> str:
        return "risk_filter"

    def should_filter(
        self,
        event: EventInfo,
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


@signal_filter_registry.register(
    "confidence_filter",
    priority=40,
    description="置信度过滤（最低置信度要求）",
    version="1.0.0"
)
class ConfidenceFilter(ISignalFilterStrategy):
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
    def filter_name(self) -> str:
        return "confidence_filter"

    def should_filter(
        self,
        event: EventInfo,
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
