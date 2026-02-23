"""
A股市场事件
"""

from dataclasses import dataclass
from backend.market.events import MarketEvent
from backend.utils.constants import STRONG_LIMIT_SEAL_AMOUNT_THRESHOLD


@dataclass
class LimitUpEvent(MarketEvent):
    """
    涨停事件 - A股涨停套利的核心事件

    业务含义：股票价格达到当日涨幅限制（主板10%，创业板20%）

    特有属性：
    - limit_time: 涨停时间
    - locked_amount: 封单金额（未成交的卖出委托金额）
    - open_count: 打开次数（"炸板"次数）
    """
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    timestamp: str = ""
    limit_time: str = ""
    locked_amount: float = 0
    open_count: int = 0
    is_first_limit: bool = True

    # 使用dataclass字段作为属性，避免to_dict调用
    @property
    def event_type(self) -> str:
        return "limit_up"

    @property
    def is_strong_limit(self) -> bool:
        """是否强势涨停（封单金额大）"""
        return self.locked_amount > STRONG_LIMIT_SEAL_AMOUNT_THRESHOLD

    @property
    def is_stable(self) -> bool:
        """是否稳定（没有打开）"""
        return self.open_count == 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'price': self.price,
            'change_pct': self.change_pct,
            'limit_time': self.limit_time,
            'locked_amount': self.locked_amount,
            'open_count': self.open_count,
            'is_first_limit': self.is_first_limit,
            'is_strong_limit': self.is_strong_limit,
            'is_stable': self.is_stable,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_limit_up_stock(cls, stock) -> 'LimitUpEvent':
        """从LimitUpStock创建事件"""
        return cls(
            stock_code=stock.stock_code,
            stock_name=stock.stock_name,
            price=stock.price,
            change_pct=stock.change_pct,
            limit_time=stock.limit_time,
            locked_amount=stock.locked_amount,
            timestamp=stock.timestamp
        )
