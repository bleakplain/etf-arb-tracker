"""信号领域接口"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict


class ISignalEvaluator(ABC):
    """信号评估器接口"""

    @abstractmethod
    def evaluate(self, limit_info: Dict, etf_info: Dict) -> Tuple[str, str]:
        """
        评估信号质量

        Args:
            limit_info: 涨停股票信息
            etf_info: ETF信息

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
