"""
策略接口定义

定义套利策略的可插拔接口，支持：
1. 事件检测策略（涨停/突破/逼空等）
2. 基金选择策略（权重/流动性/溢价等）
3. 信号过滤策略（时间/流动性/风险等）
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple

from backend.market.domain.events import MarketEvent
from backend.arbitrage.models import TradingSignal
from backend.market.domain import CandidateETF


class IEventDetector(ABC):
    """
    事件检测策略接口

    职责：检测市场中的套利机会事件
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @abstractmethod
    def detect(self, quote: Dict) -> Optional[MarketEvent]:
        """检测单个证券的市场事件"""
        pass

    @abstractmethod
    def is_valid(self, event: MarketEvent) -> bool:
        """验证事件是否有效"""
        pass


class IFundSelector(ABC):
    """
    基金选择策略接口

    职责：从符合条件的基金中选择最优的
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @abstractmethod
    def select(
        self,
        eligible_funds: List[CandidateETF],
        event: MarketEvent
    ) -> Optional[CandidateETF]:
        """从符合条件的基金中选择最优的"""
        pass

    @abstractmethod
    def get_selection_reason(self, fund: CandidateETF) -> str:
        """获取选择原因说明"""
        pass


class ISignalFilter(ABC):
    """
    信号过滤策略接口

    职责：对生成的信号进行过滤验证
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @property
    @abstractmethod
    def is_required(self) -> bool:
        """是否必须执行"""
        pass

    @abstractmethod
    def filter(
        self,
        event: MarketEvent,
        fund: CandidateETF,
        signal: TradingSignal
    ) -> Tuple[bool, str]:
        """
        过滤信号

        Returns:
            (是否通过, 原因说明)
        """
        pass
