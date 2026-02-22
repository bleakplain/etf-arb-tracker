"""
港股市场事件
"""

from dataclasses import dataclass
from backend.market.events import MarketEvent


@dataclass
class BreakoutEvent(MarketEvent):
    """
    突破事件 - 港股市场

    业务含义：股票价格突破关键阻力位
    """
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    breakout_level: float
    timestamp: str = ""

    @property
    def event_type(self) -> str:
        return "breakout"

    def to_dict(self) -> dict:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'price': self.price,
            'change_pct': self.change_pct,
            'breakout_level': self.breakout_level,
            'timestamp': self.timestamp
        }
