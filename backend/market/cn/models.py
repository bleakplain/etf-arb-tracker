"""
A股市场模型
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class LimitUpStock:
    """涨停股票实体"""
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    limit_time: str
    locked_amount: float = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.stock_code:
            raise ValueError("股票代码不能为空")

    @property
    def is_valid(self) -> bool:
        """检查涨停信息是否有效"""
        return (
            self.price > 0
            and self.change_pct > 9.5
            and self.stock_code is not None
        )

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'code': self.stock_code,
            'name': self.stock_name,
            'price': self.price,
            'time': self.limit_time,
            'change_pct': self.change_pct
        }

    @classmethod
    def from_quote(cls, quote: Dict) -> "LimitUpStock":
        """从行情字典创建"""
        return cls(
            stock_code=quote.get('code', ''),
            stock_name=quote.get('name', ''),
            price=quote.get('price', 0.0),
            change_pct=quote.get('change_pct', 0.0),
            limit_time=quote.get('timestamp', ''),
            locked_amount=quote.get('locked_amount', 0)
        )
