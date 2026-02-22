"""信号接口定义"""

from abc import ABC, abstractmethod
from typing import List, Tuple


class ISignalEvaluator(ABC):
    """信号评估器接口"""

    @abstractmethod
    def evaluate(self, market_event, etf_holding) -> Tuple[str, str]:
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
    def save(self, signal) -> bool:
        """保存信号"""
        pass

    @abstractmethod
    def get_all_signals(self) -> List:
        """获取所有信号"""
        pass

    @abstractmethod
    def get_signal(self, signal_id: str):
        """获取单个信号"""
        pass


class ISignalSender(ABC):
    """信号发送器接口"""

    @abstractmethod
    def send_signal(self, signal) -> bool:
        """发送信号通知"""
        pass


class ISignalManager(ABC):
    """信号管理器接口"""

    @abstractmethod
    def save_and_notify(self, signal) -> bool:
        """保存信号并发送通知"""
        pass
