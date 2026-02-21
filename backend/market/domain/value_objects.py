"""市场值对象"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class LimitUpEvent:
    """涨停事件

    由market模块发布，arbitrage模块监听此事件生成套利信号
    """
    event_id: str
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    limit_time: str
    seal_amount: float = 0
    timestamp: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if not self.event_id:
            object.__setattr__(self, 'event_id', f"evt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.stock_code}")
        if not self.timestamp:
            object.__setattr__(self, 'timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    @classmethod
    def from_limit_up_stock(cls, stock: 'LimitUpStock') -> 'LimitUpEvent':
        """从LimitUpStock实体创建事件"""
        return cls(
            stock_code=stock.stock_code,
            stock_name=stock.stock_name,
            price=stock.price,
            change_pct=stock.change_pct,
            limit_time=stock.limit_time,
            seal_amount=stock.seal_amount,
            timestamp=stock.timestamp
        )


@dataclass(frozen=True)
class CandidateETF:
    """候选ETF值对象（用于套利策略选择）

    表示包含特定股票的ETF候选，套利策略从中选择最优的一个。
    """
    etf_code: str
    etf_name: str
    weight: float
    category: 'ETFCategory'  # Forward reference
    rank: int = -1
    in_top10: bool = False
    top10_ratio: float = 0.0

    def __post_init__(self):
        if not self.etf_code:
            raise ValueError("ETF代码不能为空")
        if not 0 <= self.weight <= 1:
            raise ValueError("权重必须在0-1之间")
        if self.rank < -1:
            raise ValueError("排名不能小于-1")
        if not 0 <= self.top10_ratio <= 1:
            raise ValueError("前10占比必须在0-1之间")

    @property
    def weight_pct(self) -> float:
        """权重百分比"""
        return self.weight * 100


@dataclass(frozen=True)
class ETFQuote:
    """ETF行情值对象"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    premium: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.code:
            raise ValueError("ETF代码不能为空")
        if self.price < 0:
            raise ValueError("价格不能为负")


@dataclass(frozen=True)
class TradingHours:
    """交易时间值对象"""
    morning_start: str = "09:30"
    morning_end: str = "11:30"
    afternoon_start: str = "13:00"
    afternoon_end: str = "15:00"

    def is_trading_time(self, current_time: datetime = None) -> bool:
        """判断是否在交易时间内"""
        if current_time is None:
            current_time = datetime.now()

        from datetime import time
        now = current_time.time()

        morning_start = time.fromisoformat(self.morning_start)
        morning_end = time.fromisoformat(self.morning_end)
        afternoon_start = time.fromisoformat(self.afternoon_start)
        afternoon_end = time.fromisoformat(self.afternoon_end)

        return (morning_start <= now <= morning_end or
                afternoon_start <= now <= afternoon_end)

    def get_time_to_close(self, current_time: datetime = None) -> int:
        """获取距离收盘的秒数"""
        if current_time is None:
            current_time = datetime.now()

        close_time = current_time.replace(
            hour=15, minute=0, second=0, microsecond=0
        )

        if current_time.hour < 9 or current_time.hour >= 15:
            return -1

        delta = close_time - current_time
        return int(delta.total_seconds())
