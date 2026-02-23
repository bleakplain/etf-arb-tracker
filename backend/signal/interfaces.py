"""信号接口定义"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, TYPE_CHECKING

from backend.arbitrage.models import TradingSignal

if TYPE_CHECKING:
    from backend.market.events import MarketEvent
    from backend.market import CandidateETF


class ISignalEvaluator(ABC):
    """信号评估器接口"""

    @abstractmethod
    def evaluate(
        self,
        market_event: 'MarketEvent',
        etf_holding: 'CandidateETF'
    ) -> Tuple[str, str]:
        """
        评估信号质量

        Args:
            market_event: 市场事件（如 LimitUpEvent）
            etf_holding: ETF持仓信息（CandidateETF）

        Returns:
            (置信度, 风险等级)
        """
        pass


class ISignalRepository(ABC):
    """信号仓储接口"""

    @abstractmethod
    def save(self, signal: TradingSignal) -> bool:
        """保存信号"""
        pass

    @abstractmethod
    def get_all_signals(self) -> List[TradingSignal]:
        """获取所有信号"""
        pass

    @abstractmethod
    def get_signal(self, signal_id: str) -> Optional[TradingSignal]:
        """获取单个信号"""
        pass


class ISignalSender(ABC):
    """信号发送器接口"""

    @abstractmethod
    def send_signal(self, signal: TradingSignal) -> bool:
        """发送信号通知"""
        pass
