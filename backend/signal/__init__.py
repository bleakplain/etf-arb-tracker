"""信号模块 - 信号管理、通知"""

from backend.signal.interfaces import ISignalRepository, ISignalSender, ISignalManager, ISignalEvaluator
from backend.signal.repository import FileSignalRepository, InMemorySignalRepository
from backend.signal.manager import SignalManager
from backend.signal.evaluator import SignalEvaluator, SignalEvaluatorFactory
from backend.signal.sender import NotificationSender, LogSender, NullSender, create_sender_from_config

__all__ = [
    # 接口
    'ISignalRepository',
    'ISignalSender',
    'ISignalManager',
    'ISignalEvaluator',
    # 实现
    'FileSignalRepository',
    'InMemorySignalRepository',
    'SignalManager',
    'SignalEvaluator',
    'SignalEvaluatorFactory',
    'NotificationSender',
    'LogSender',
    'NullSender',
    'create_sender_from_config',
]
