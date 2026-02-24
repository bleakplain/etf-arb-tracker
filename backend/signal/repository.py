"""
信号仓储 - 专职管理信号存储
"""

import json
import os
import threading
import tempfile
from typing import List, Optional
from abc import ABC, abstractmethod
from pathlib import Path
from loguru import logger

from backend.signal.interfaces import ISignalRepository
from backend.arbitrage.models import TradingSignal
from backend.utils.time_utils import today_china


class BaseSignalRepository(ISignalRepository, ABC):
    """
    信号仓储基类 - 提供公共的线程安全和数据管理逻辑
    """

    def __init__(self):
        """初始化基类仓储"""
        self._signals: List[TradingSignal] = []
        self._lock = threading.Lock()

    def save(self, signal: TradingSignal) -> bool:
        """保存单个信号（线程安全）"""
        with self._lock:
            self._do_save(signal)
            self._post_save(signal)
        logger.debug(f"保存信号: {signal.stock_name} -> {signal.etf_name}")
        return True

    def save_all(self, signals: List[TradingSignal]) -> None:
        """批量保存信号（线程安全）"""
        with self._lock:
            for signal in signals:
                self._do_save(signal)
            self._post_save_all(signals)
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
            self._post_clear()

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

    # 子类需要实现的抽象方法

    @abstractmethod
    def _do_save(self, signal: TradingSignal) -> None:
        """实际保存信号的实现（由子类实现）"""
        pass

    @abstractmethod
    def _post_save(self, signal: TradingSignal) -> None:
        """保存后处理（如持久化到文件），由子类实现"""
        pass

    @abstractmethod
    def _post_save_all(self, signals: List[TradingSignal]) -> None:
        """批量保存后处理，由子类实现"""
        pass

    @abstractmethod
    def _post_clear(self) -> None:
        """清空后处理，由子类实现"""
        pass


class FileSignalRepository(BaseSignalRepository):
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
        super().__init__()
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

    def _do_save(self, signal: TradingSignal) -> None:
        """添加信号到内存列表"""
        self._signals.append(signal)

    def _post_save(self, signal: TradingSignal) -> None:
        """保存后处理：持久化到文件"""
        self._save_to_file()

    def _post_save_all(self, signals: List[TradingSignal]) -> None:
        """批量保存后处理：持久化到文件"""
        self._save_to_file()

    def _post_clear(self) -> None:
        """清空后处理：删除文件"""
        self._save_to_file()

    def _save_to_file(self) -> None:
        """保存信号到文件（原子操作）"""
        os.makedirs(os.path.dirname(self._filepath) or '.', exist_ok=True)

        data = [s.to_dict() for s in self._signals]

        # 使用临时文件实现原子写入
        try:
            # 先写入临时文件
            temp_path = f"{self._filepath}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # 确保数据写入磁盘

            # 原子性替换原文件
            if os.path.exists(self._filepath):
                os.replace(temp_path, self._filepath)
            else:
                os.rename(temp_path, self._filepath)

        except Exception as e:
            logger.error(f"保存信号文件失败: {e}")
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise


class InMemorySignalRepository(BaseSignalRepository):
    """
    内存信号仓储实现 - 用于测试

    不依赖文件I/O，所有数据存储在内存中。
    适合单元测试和集成测试使用。
    """

    def __init__(self):
        """初始化内存仓储"""
        super().__init__()

    def _do_save(self, signal: TradingSignal) -> None:
        """添加信号到内存列表"""
        self._signals.append(signal)

    def _post_save(self, signal: TradingSignal) -> None:
        """内存仓储无需保存后处理"""
        pass

    def _post_save_all(self, signals: List[TradingSignal]) -> None:
        """内存仓储无需批量保存后处理"""
        pass

    def _post_clear(self) -> None:
        """内存仓储无需清空后处理"""
        pass
