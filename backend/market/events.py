"""
市场事件基类 - 跨市场通用
"""

from abc import ABC, abstractmethod
from typing import Dict


class MarketEvent(ABC):
    """市场事件基类"""

    @property
    @abstractmethod
    def event_type(self) -> str:
        """事件类型"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict:
        """转换为字典"""
        pass
