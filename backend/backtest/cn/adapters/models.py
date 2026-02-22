"""
回测模型适配器 - 连接 backtest 和 arbitrage/market 模块

提供模型转换和适配功能：
- ETFReference (backtest) ↔ CandidateETF (market)
- 历史数据格式转换
"""

from typing import Dict, List
from loguru import logger

from backend.market import ETFCategory, CandidateETF


class ETFReference:
    """ETF引用值对象（回测专用）

    这是 backtest 模块内部使用的模型，对应 market.CandidateETF
    为了保持向后兼容而保留。
    """
    def __init__(
        self,
        etf_code: str,
        etf_name: str,
        weight: float,
        category: ETFCategory,
        rank: int = -1,
        in_top10: bool = False,
        top10_ratio: float = 0.0
    ):
        # 使用 CandidateETF 作为底层存储
        self._candidate = CandidateETF(
            etf_code=etf_code,
            etf_name=etf_name,
            weight=weight,
            category=category,
            rank=rank,
            in_top10=in_top10,
            top10_ratio=top10_ratio
        )

    @property
    def etf_code(self) -> str:
        return self._candidate.etf_code

    @property
    def etf_name(self) -> str:
        return self._candidate.etf_name

    @property
    def weight(self) -> float:
        return self._candidate.weight

    @property
    def category(self) -> ETFCategory:
        return self._candidate.category

    @property
    def rank(self) -> int:
        return self._candidate.rank

    @property
    def in_top10(self) -> bool:
        return self._candidate.in_top10

    @property
    def top10_ratio(self) -> float:
        return self._candidate.top10_ratio

    @property
    def weight_pct(self) -> float:
        return self._candidate.weight_pct

    def to_candidate_etf(self) -> CandidateETF:
        """转换为 CandidateETF"""
        return self._candidate

    @classmethod
    def from_candidate_etf(cls, candidate: CandidateETF) -> "ETFReference":
        """从 CandidateETF 创建 ETFReference"""
        return cls(
            etf_code=candidate.etf_code,
            etf_name=candidate.etf_name,
            weight=candidate.weight,
            category=candidate.category,
            rank=candidate.rank,
            in_top10=candidate.in_top10,
            top10_ratio=candidate.top10_ratio
        )

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "etf_code": self.etf_code,
            "etf_name": self.etf_name,
            "weight": self.weight,
            "category": self.category.value,
            "rank": self.rank,
            "in_top10": self.in_top10,
            "top10_ratio": self.top10_ratio
        }
