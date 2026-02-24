"""
信号仓储 - 专职管理信号存储
"""

import threading
from typing import List, Optional
from loguru import logger

from backend.signal.interfaces import ISignalRepository
from backend.arbitrage.models import TradingSignal
from backend.utils.time_utils import today_china


class InMemorySignalRepository(ISignalRepository):
    """
    内存信号仓储实现 - 用于测试

    不依赖文件I/O，所有数据存储在内存中。
    适合单元测试和集成测试使用。
    """

    def __init__(self):
        """初始化内存仓储"""
        self._signals: List[TradingSignal] = []
        self._lock = threading.Lock()

    def save(self, signal: TradingSignal) -> bool:
        """保存单个信号（线程安全）"""
        with self._lock:
            self._signals.append(signal)
        logger.debug(f"保存信号: {signal.stock_name} -> {signal.etf_name}")
        return True

    def save_all(self, signals: List[TradingSignal]) -> None:
        """批量保存信号（线程安全）"""
        with self._lock:
            self._signals.extend(signals)
        logger.info(f"批量保存 {len(signals)} 个信号")

    def get_all_signals(self) -> List[TradingSignal]:
        """获取所有信号（线程安全）"""
        with self._lock:
            return self._signals.copy()

    def get_today_signals(self) -> List[TradingSignal]:
        """获取今天的所有信号（线程安全）"""
        with self._lock:
            today = today_china()
            return [s for s in self._signals if s.timestamp.startswith(today)]

    def get_recent_signals(self, limit: int = 20) -> List[TradingSignal]:
        """获取最近的信号（线程安全）"""
        with self._lock:
            sorted_signals = sorted(
                self._signals,
                key=lambda x: x.timestamp,
                reverse=True
            )
            return sorted_signals[:limit]

    def clear(self) -> None:
        """清空所有信号（线程安全）"""
        with self._lock:
            self._signals.clear()
        logger.info("已清空内存信号")

    def get_count(self) -> int:
        """获取信号总数（线程安全）"""
        with self._lock:
            return len(self._signals)

    def get_signal(self, signal_id: str) -> Optional[TradingSignal]:
        """获取单个信号（线程安全）"""
        with self._lock:
            for signal in self._signals:
                if signal.signal_id == signal_id:
                    return signal
            return None
