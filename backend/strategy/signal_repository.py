"""
信号仓储 - 专职管理信号存储
"""

import json
import os
import threading
from typing import List
from loguru import logger

from backend.domain.interfaces import ISignalRepository
from backend.domain.value_objects import TradingSignal
from backend.utils.time_utils import today_china


class FileSignalRepository(ISignalRepository):
    """
    基于文件的信号仓储实现

    职责：
    1. 保存信号到文件
    2. 从文件读取信号
    3. 按日期筛选信号
    """

    def __init__(self, filepath: str = "data/signals.json"):
        """
        初始化仓储

        Args:
            filepath: 信号文件路径
        """
        self._filepath = filepath
        self._signals: List[TradingSignal] = []
        self._lock = threading.Lock()  # 线程安全锁
        self._load()

    def _load(self) -> None:
        """从文件加载信号历史"""
        if not os.path.exists(self._filepath):
            logger.debug(f"信号文件不存在: {self._filepath}")
            return

        try:
            with open(self._filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._signals = [TradingSignal.from_dict(s) for s in data]
            logger.info(f"加载信号历史，共 {len(self._signals)} 条")

        except Exception as e:
            logger.error(f"加载信号历史失败: {e}")
            self._signals = []

    def _save_to_file(self) -> None:
        """保存信号到文件"""
        os.makedirs(os.path.dirname(self._filepath) or '.', exist_ok=True)

        data = [s.to_dict() for s in self._signals]

        with open(self._filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save(self, signal: TradingSignal) -> None:
        """保存单个信号（线程安全）"""
        with self._lock:
            self._signals.append(signal)
            self._save_to_file()
        logger.debug(f"保存信号: {signal.stock_name} -> {signal.etf_name}")

    def save_all(self, signals: List[TradingSignal]) -> None:
        """批量保存信号（线程安全）"""
        with self._lock:
            self._signals.extend(signals)
            self._save_to_file()
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
            # 按时间倒序
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
            self._save_to_file()
        logger.info("已清空信号历史")

    def get_count(self) -> int:
        """获取信号总数（线程安全）"""
        with self._lock:
            return len(self._signals)
