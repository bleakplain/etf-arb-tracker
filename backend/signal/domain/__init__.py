"""信号领域模块"""

from backend.signal.domain.interfaces import ISignalRepository, ISignalSender, ISignalManager, ISignalEvaluator

__all__ = [
    'ISignalRepository',
    'ISignalSender',
    'ISignalManager',
    'ISignalEvaluator',
]
