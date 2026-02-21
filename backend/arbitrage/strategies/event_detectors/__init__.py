"""
事件检测策略包

定义各种市场事件检测策略：
- LimitUpDetector: 涨停检测（A股）
- BreakoutDetector: 突破检测（美股）
- ShortSqueezeDetector: 逼空检测（做空）
- GapUpDetector: 跳空高开检测
"""

from backend.arbitrage.domain.interfaces import IEventDetectorStrategy, EventInfo
from backend.arbitrage.strategy_registry import event_detector_registry
from typing import Dict, Optional


@event_detector_registry.register(
    "limit_up",
    priority=100,
    description="A股涨停检测策略",
    version="1.0.0"
)
class LimitUpDetector(IEventDetectorStrategy):
    """
    涨停事件检测器

    检测A股市场的涨停事件。
    不同板块有不同的涨停限制：
    - 主板: 10%
    - 科创板/创业板: 20%
    - 北交所: 30%
    """

    def __init__(self, min_change_pct: float = 0.095):
        """
        初始化涨停检测器

        Args:
            min_change_pct: 最小涨幅阈值（默认9.5%）
        """
        self.min_change_pct = min_change_pct

    @property
    def strategy_name(self) -> str:
        return "limit_up"

    def detect(self, quote: Dict) -> Optional[EventInfo]:
        """
        检测涨停事件

        Args:
            quote: 行情数据，需包含 is_limit_up 字段

        Returns:
            涨停事件信息，未涨停返回None
        """
        if not quote.get('is_limit_up', False):
            return None

        return EventInfo(
            event_type="limit_up",
            security_code=quote.get('code', ''),
            security_name=quote.get('name', ''),
            price=quote.get('price', 0.0),
            change_pct=quote.get('change_pct', 0.0),
            trigger_price=quote.get('price', 0.0),
            trigger_time=quote.get('timestamp', ''),
            volume=quote.get('volume', 0),
            amount=quote.get('amount', 0),
            metadata={
                'market': 'CN',
                'seal_amount': quote.get('seal_amount', 0)  # 封单量
            }
        )

    def is_valid(self, event: EventInfo) -> bool:
        """
        验证涨停事件是否有效

        Args:
            event: 涨停事件信息

        Returns:
            是否符合策略要求
        """
        # 基本验证：涨幅必须达到阈值
        if event.change_pct < self.min_change_pct:
            return False

        # 可以添加更多验证逻辑：
        # - 封单量检查
        # - 时间段检查
        # - 换手率检查

        return True


@event_detector_registry.register(
    "breakout",
    priority=50,
    description="突破检测策略（适用于美股/港股）",
    version="1.0.0"
)
class BreakoutDetector(IEventDetectorStrategy):
    """
    突破事件检测器

    检测价格突破关键阻力的机会。
    适用于没有涨停限制的市场（如美股、港股）。
    """

    def __init__(
        self,
        breakout_pct: float = 0.10,  # 突破涨幅
        min_volume: float = 1000000,  # 最小成交量
        lookback_days: int = 20       # 回看天数（计算阻力位）
    ):
        self.breakout_pct = breakout_pct
        self.min_volume = min_volume
        self.lookback_days = lookback_days

    @property
    def strategy_name(self) -> str:
        return "breakout"

    def detect(self, quote: Dict) -> Optional[EventInfo]:
        """检测突破事件"""
        change_pct = quote.get('change_pct', 0)

        if change_pct < self.breakout_pct:
            return None

        # 计算阻力位（简化实现，实际应该使用历史数据）
        prev_close = quote.get('prev_close', 0)
        if prev_close <= 0:
            return None

        return EventInfo(
            event_type="breakout",
            security_code=quote.get('symbol', quote.get('code', '')),
            security_name=quote.get('name', ''),
            price=quote.get('price', 0.0),
            change_pct=change_pct,
            trigger_price=prev_close * (1 + self.breakout_pct),
            trigger_time=quote.get('timestamp', ''),
            volume=quote.get('volume', 0),
            amount=quote.get('amount', 0),
            metadata={
                'lookback_days': self.lookback_days,
                'resistance_level': prev_close * 1.05  # 示例阻力位
            }
        )

    def is_valid(self, event: EventInfo) -> bool:
        """验证突破事件是否有效"""
        # 成交量检查
        if event.volume < self.min_volume:
            return False

        # 可以添加更多验证：
        # - 突破有效性（是否站稳）
        # - 市场情绪
        # - 行业热度

        return True
