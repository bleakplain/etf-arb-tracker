"""
市场数据模型 - 跨市场通用
"""

from dataclasses import dataclass
from typing import Dict
from enum import Enum


class ETFCategory(Enum):
    """ETF类别"""
    BROAD_INDEX = "broad_index"
    SECTOR = "sector"
    THEME = "theme"
    STRATEGY = "strategy"
    OTHER = "other"


@dataclass
class StockQuote:
    """股票行情"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float = 0
    amount: float = 0
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'volume': self.volume,
            'amount': self.amount,
            'timestamp': self.timestamp
        }


@dataclass
class ETFQuote:
    """ETF行情"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float = 0
    premium: float = 0
    timestamp: str = ""


@dataclass
class Holding:
    """ETF持仓"""
    stock_code: str
    stock_name: str
    weight: float
    rank: int = -1
