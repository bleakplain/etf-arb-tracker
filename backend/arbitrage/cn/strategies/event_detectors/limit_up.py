"""
涨停检测策略

检测A股市场的涨停事件。
不同板块有不同的涨停限制：
- 主板: 10%
- 科创板/创业板: 20%
- 北交所: 30%
"""

from backend.arbitrage.cn.strategies.interfaces import IEventDetector
from backend.market.domain.events import LimitUpEvent
from backend.arbitrage.strategy_registry import event_detector_registry
from typing import Dict, Optional


@event_detector_registry.register(
    "limit_up_cn",
    priority=100,
    description="A股涨停检测策略",
    version="1.0.0"
)
class LimitUpDetectorCN(IEventDetector):
    """
    A股涨停事件检测器

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
        return "limit_up_cn"

    def detect(self, quote: Dict) -> Optional[LimitUpEvent]:
        """
        检测涨停事件

        Args:
            quote: 行情数据，需包含 is_limit_up 字段

        Returns:
            涨停事件信息，未涨停返回None
        """
        if not quote.get('is_limit_up', False):
            return None

        return LimitUpEvent(
            stock_code=quote.get('code', ''),
            stock_name=quote.get('name', ''),
            price=quote.get('price', 0.0),
            change_pct=quote.get('change_pct', 0.0),
            limit_time=quote.get('limit_time', quote.get('timestamp', '')),
            seal_amount=quote.get('seal_amount', 0),
            open_count=quote.get('open_count', 0),
            is_first_limit=quote.get('is_first_limit', True),
            timestamp=quote.get('timestamp', '')
        )

    def is_valid(self, event: LimitUpEvent) -> bool:
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
