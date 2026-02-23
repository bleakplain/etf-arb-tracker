"""套利领域模型

跨市场的通用模型定义：
- TradingSignal: 交易信号实体
- ChosenETF: 选中的ETF值对象
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ChosenETF:
    """选中的ETF（套利目标）

    由套利策略从候选ETF中选择出来的最优ETF。
    """
    etf_code: str
    etf_name: str
    weight: float
    category: str
    rank: int = -1
    in_top10: bool = False
    selection_reason: str = ""

    def __post_init__(self):
        if not self.etf_code:
            raise ValueError("ETF代码不能为空")
        if not 0 <= self.weight <= 1:
            raise ValueError("权重必须在0-1之间")

    @property
    def weight_pct(self) -> float:
        """权重百分比"""
        return self.weight * 100


@dataclass(frozen=True)
class TradingSignal:
    """交易信号实体

    由套利引擎生成，表示一个套利机会
    """
    signal_id: str
    timestamp: str

    # 事件证券信息
    stock_code: str
    stock_name: str
    stock_price: float
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

    # A股特有字段（可选，保持向后兼容）
    limit_time: str = ""
    locked_amount: float = 0

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
