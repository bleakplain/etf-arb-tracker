"""
市场数据模型 - 跨市场通用
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime


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
class ETFHolding:
    """ETF持仓"""
    stock_code: str
    stock_name: str
    weight: float
    rank: int = -1


@dataclass(frozen=True)
class CandidateETF:
    """候选ETF值对象（用于套利策略选择）

    表示包含特定股票的ETF候选，套利策略从中选择最优的一个。
    """
    etf_code: str
    etf_name: str
    weight: float
    category: ETFCategory
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


@dataclass
class ETF:
    """ETF实体"""
    code: str
    name: str
    category: ETFCategory
    holdings: List[ETFHolding] = None

    def __post_init__(self):
        if not self.code:
            raise ValueError("ETF代码不能为空")
        if self.holdings is None:
            self.holdings = []

    def get_holding(self, stock_code: str) -> Optional[ETFHolding]:
        """获取指定股票的持仓信息"""
        for holding in self.holdings:
            if holding.stock_code == stock_code:
                return holding
        return None


@dataclass(frozen=True)
class TradingPeriod:
    """交易时段（起止时间）"""
    start: str  # 开始时间，格式 "HH:MM"
    end: str    # 结束时间，格式 "HH:MM"

    def is_active(self, current_time: datetime = None) -> bool:
        """判断当前是否在该时段内"""
        if current_time is None:
            current_time = datetime.now()

        from datetime import time
        now = current_time.time()
        start_time = time.fromisoformat(self.start)
        end_time = time.fromisoformat(self.end)

        return start_time <= now <= end_time

    def get_time_to_end(self, current_time: datetime = None) -> int:
        """获取距离该时段结束的秒数"""
        if current_time is None:
            current_time = datetime.now()

        from datetime import time
        end_time = time.fromisoformat(self.end)

        period_end = current_time.replace(
            hour=end_time.hour,
            minute=end_time.minute,
            second=0,
            microsecond=0
        )

        delta = period_end - current_time
        return max(0, int(delta.total_seconds()))
