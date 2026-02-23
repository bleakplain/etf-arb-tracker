"""
美股市场事件
"""

from dataclasses import dataclass
from backend.market.events import MarketEvent


@dataclass
class MomentumEvent(MarketEvent):
    """
    动量事件 - 美股市场

    业务含义：股票价格呈现强劲动量
    """
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    timestamp: str = ""
    volume_ratio: float = 0.0

    @property
    def event_type(self) -> str:
        return "momentum"

    def to_dict(self) -> dict:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'price': self.price,
            'change_pct': self.change_pct,
            'volume_ratio': self.volume_ratio,
            'timestamp': self.timestamp
        }
