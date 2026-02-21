"""信号模块 - 信号管理、通知"""

from backend.signal.domain import ISignalRepository, ISignalSender, ISignalManager
from backend.signal.service.signal_manager import SignalManager

__all__ = [
    'ISignalRepository',
    'ISignalSender',
    'ISignalManager',
    'SignalManager',
]
