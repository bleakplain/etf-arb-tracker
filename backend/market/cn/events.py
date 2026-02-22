"""
A股市场事件
"""

from dataclasses import dataclass
from backend.market.events import MarketEvent


@dataclass
class LimitUpEvent(MarketEvent):
    """
    涨停事件 - A股涨停套利的核心事件

    业务含义：股票价格达到当日涨幅限制（主板10%，创业板20%）

    特有属性：
    - limit_time: 涨停时间
    - seal_amount: 封单金额（未成交的卖出委托金额）
    - open_count: 打开次数（"炸板"次数）
    """
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    limit_time: str
    seal_amount: float = 0
    open_count: int = 0
    is_first_limit: bool = True
    timestamp: str = ""

    @property
    def event_type(self) -> str:
        return "limit_up"

    @property
    def is_strong_limit(self) -> bool:
        """是否强势涨停（封单金额大）"""
        return self.seal_amount > 1000000  # 100万以上

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
            'seal_amount': self.seal_amount,
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
            seal_amount=stock.seal_amount,
            timestamp=stock.timestamp
        )
