"""信号领域模块"""

from backend.signal.domain.interfaces import ISignalRepository, ISignalSender, ISignalManager

__all__ = [
    'ISignalRepository',
    'ISignalSender',
    'ISignalManager',
]
