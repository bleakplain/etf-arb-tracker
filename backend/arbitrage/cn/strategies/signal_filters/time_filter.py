"""
A股时间过滤策略

检查距离A股收盘的时间，避免在收盘前太短时间内发出信号。

A股交易时间：9:30-11:30, 13:00-15:00
"""

from backend.arbitrage.cn.strategies.interfaces import ISignalFilter
from backend.market.domain.events import MarketEvent
from backend.arbitrage.strategy_registry import signal_filter_registry
from backend.arbitrage.models import TradingSignal
from backend.market.domain import CandidateETF
from datetime import datetime


@signal_filter_registry.register(
    "time_filter_cn",
    priority=100,
    description="A股时间过滤（距收盘时间检查）",
    version="1.0.0"
)
class TimeFilterCN(ISignalFilter):
    """
    A股时间过滤器

    检查距离A股收盘的时间（15:00），避免在收盘前太短时间内发出信号。
    """

    def __init__(self, min_time_to_close: int = 1800):
        """
        初始化A股时间过滤器

        Args:
            min_time_to_close: 距收盘最小时间（秒），默认30分钟
        """
        self.min_time_to_close = min_time_to_close

    @property
    def strategy_name(self) -> str:
        return "time_filter_cn"

    def filter(
        self,
        event: MarketEvent,
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
            return True, "当前不在A股交易时间"

        # 距收盘太近
        if 0 < time_to_close < self.min_time_to_close:
            minutes = time_to_close // 60
            return True, f"距A股收盘仅{minutes}分钟，时间不足"

        return False, ""

    @staticmethod
    def _get_time_to_close() -> int:
        """获取距离A股收盘的秒数（15:00收盘）"""
        now = datetime.now()
        close_time = now.replace(hour=15, minute=0, second=0, microsecond=0)

        if now.hour < 9 or now.hour >= 15:
            return -1

        delta = close_time - now
        return int(delta.total_seconds())

    @property
    def is_required(self) -> bool:
        """时间过滤是必需的"""
        return True
