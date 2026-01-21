"""
领域值对象 - 不可变的业务概念

值对象特征：
1. 不可变性
2. 通过属性值判断相等性
3. 自包含验证逻辑
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional
from enum import Enum


class ConfidenceLevel(Enum):
    """信号置信度"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class RiskLevel(Enum):
    """风险等级"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class ETFCategory(Enum):
    """ETF分类"""
    BROAD_INDEX = "宽基"
    TECH = "科技"
    CONSUMER = "消费"
    FINANCIAL = "金融"
    OTHER = "其他"


@dataclass(frozen=True)
class StockInfo:
    """股票信息值对象"""
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


@dataclass(frozen=True)
class ETFReference:
    """ETF引用值对象"""
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


@dataclass(frozen=True)
class TradingSignal:
    """交易信号值对象"""
    signal_id: str
    timestamp: str

    # 涨停股票信息
    stock_code: str
    stock_name: str
    stock_price: float
    limit_time: str
    seal_amount: float
    change_pct: float

    # ETF信息
    etf_code: str
    etf_name: str
    etf_weight: float
    etf_price: float
    etf_premium: float

    # 信号评估
    reason: str
    confidence: str
    risk_level: str

    # 策略验证信息
    actual_weight: float
    weight_rank: int
    top10_ratio: float

    def to_dict(self) -> dict:
        """转换为字典"""
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TradingSignal":
        """从字典创建"""
        return cls(**data)


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
