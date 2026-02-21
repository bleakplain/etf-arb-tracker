"""市场领域模型"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


@dataclass
class LimitUpStock:
    """涨停股票实体"""
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    limit_time: str
    seal_amount: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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
            seal_amount=quote.get('seal_amount', 0)
        )


@dataclass(frozen=True)
class StockQuote:
    """股票行情值对象"""
    code: str
    name: str
    price: float
    change_pct: float
    is_limit_up: bool
    timestamp: str = ""

    def __post_init__(self):
        if not self.code:
            raise ValueError("股票代码不能为空")
        if not self.name:
            raise ValueError("股票名称不能为空")
        if self.price < 0:
            raise ValueError("价格不能为负")
        if not -100 <= self.change_pct <= 100:
            raise ValueError("涨跌幅必须在-100%到100%之间")


class ETFCategory(Enum):
    """ETF分类"""
    BROAD_INDEX = "宽基"
    TECH = "科技"
    CONSUMER = "消费"
    FINANCIAL = "金融"
    OTHER = "其他"


@dataclass
class ETF:
    """ETF实体"""
    code: str
    name: str
    category: ETFCategory
    holdings: List['Holding'] = field(default_factory=list)

    def __post_init__(self):
        if not self.code:
            raise ValueError("ETF代码不能为空")

    def get_holding(self, stock_code: str) -> Optional['Holding']:
        """获取指定股票的持仓信息"""
        for holding in self.holdings:
            if holding.stock_code == stock_code:
                return holding
        return None


@dataclass(frozen=True)
class Holding:
    """ETF持仓值对象"""
    stock_code: str
    stock_name: str
    weight: float
    rank: int = -1
    in_top10: bool = False

    def __post_init__(self):
        if not self.stock_code:
            raise ValueError("股票代码不能为空")
        if not 0 <= self.weight <= 1:
            raise ValueError("权重必须在0-1之间")

    @property
    def weight_pct(self) -> float:
        """权重百分比"""
        return self.weight * 100
