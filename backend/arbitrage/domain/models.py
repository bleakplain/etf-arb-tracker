"""套利领域模型"""

from dataclasses import dataclass, field
from typing import Dict
from datetime import datetime


@dataclass(frozen=True)
class TradingSignal:
    """交易信号实体
    
    由套利引擎生成，表示一个套利机会
    """
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

    def __post_init__(self):
        if not self.signal_id:
            raise ValueError("信号ID不能为空")
        if not self.stock_code:
            raise ValueError("股票代码不能为空")
        if not self.etf_code:
            raise ValueError("ETF代码不能为空")

    def to_dict(self) -> dict:
        """转换为字典"""
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TradingSignal":
        """从字典创建"""
        return cls(**data)
