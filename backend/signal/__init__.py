"""信号模块 - 信号管理、通知"""

from backend.signal.interfaces import ISignalRepository, ISignalSender, ISignalEvaluator
from backend.signal.repository import InMemorySignalRepository
from backend.signal.db_repository import DBSignalRepository
from backend.signal.manager import SignalManager
from backend.signal.evaluator import SignalEvaluator, SignalEvaluatorFactory
from backend.signal.sender import NotificationSender, LogSender, NullSender, create_sender_from_config

__all__ = [
    # 接口
    'ISignalRepository',
    'ISignalSender',
    'ISignalEvaluator',
    # 实现
    'InMemorySignalRepository',
    'DBSignalRepository',
    'SignalManager',
    'SignalEvaluator',
    'SignalEvaluatorFactory',
    'NotificationSender',
    'LogSender',
    'NullSender',
    'create_sender_from_config',
]
