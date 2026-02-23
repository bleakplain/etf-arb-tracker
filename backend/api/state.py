"""
API状态管理器 - 消除全局状态

采用单例模式管理API的运行状态，提供线程安全的状态访问
"""

import threading
from typing import Optional
from dataclasses import dataclass, field
from loguru import logger
from datetime import datetime


@dataclass
class MonitorState:
    """
    监控器状态

    管理监控器的运行状态和相关元数据
    """
    _running: bool = False
    _start_time: Optional[datetime] = None
    _stop_time: Optional[datetime] = None
    _scan_count: int = 0
    _lock: threading.RLock = field(default_factory=threading.RLock)

    @property
    def is_running(self) -> bool:
        """获取运行状态"""
        with self._lock:
            return self._running

    @property
    def start_time(self) -> Optional[datetime]:
        """获取启动时间"""
        with self._lock:
            return self._start_time

    @property
    def stop_time(self) -> Optional[datetime]:
        """获取停止时间"""
        with self._lock:
            return self._stop_time

    @property
    def scan_count(self) -> int:
        """获取扫描次数"""
        with self._lock:
            return self._scan_count

    @property
    def uptime_seconds(self) -> Optional[float]:
        """获取运行时长（秒）"""
        with self._lock:
            if self._start_time is None:
                return None
            # 运行时：计算从启动到现在；停止时：计算从启动到停止
            if self._running:
                end = datetime.now()
            else:
                # 已停止，但没有stop_time的情况返回None
                if self._stop_time is None:
                    return None
                end = self._stop_time
            return (end - self._start_time).total_seconds()

    def start(self) -> bool:
        """
        启动监控

        Returns:
            是否成功启动（False表示已在运行）
        """
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._start_time = datetime.now()
            self._stop_time = None
            logger.info(f"监控器已启动: {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return True

    def stop(self) -> bool:
        """
        停止监控

        Returns:
            是否成功停止（False表示未在运行）
        """
        with self._lock:
            if not self._running:
                return False
            self._running = False
            self._stop_time = datetime.now()
            logger.info(f"监控器已停止: {self._stop_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return True

    def increment_scan_count(self) -> int:
        """
        增加扫描计数

        Returns:
            当前扫描次数
        """
        with self._lock:
            self._scan_count += 1
            return self._scan_count

    def reset(self) -> None:
        """重置状态"""
        with self._lock:
            was_running = self._running
            self._running = False
            self._start_time = None
            self._stop_time = None
            self._scan_count = 0
            if was_running:
                logger.info("监控器状态已重置")

    def get_status_info(self) -> dict:
        """
        获取状态信息摘要

        Returns:
            包含状态信息的字典
        """
        with self._lock:
            return {
                'is_running': self._running,
                'start_time': self._start_time.isoformat() if self._start_time else None,
                'stop_time': self._stop_time.isoformat() if self._stop_time else None,
                'scan_count': self._scan_count,
                'uptime_seconds': self.uptime_seconds
            }


class APIStateManager:
    """
    API状态管理器

    单例模式，管理API的全局状态
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._monitor_state = MonitorState()
        self._initialized = True
        logger.info("API状态管理器已初始化")

    @property
    def monitor_state(self) -> MonitorState:
        """获取监控器状态"""
        return self._monitor_state


# 全局访问点
_api_state_manager: Optional[APIStateManager] = None


def get_api_state_manager() -> APIStateManager:
    """
    获取API状态管理器单例

    Returns:
        APIStateManager实例
    """
    global _api_state_manager
    if _api_state_manager is None:
        _api_state_manager = APIStateManager()
    return _api_state_manager


def reset_api_state_manager() -> None:
    """
    重置API状态管理器（主要用于测试）

    警告：此方法会清空所有状态，仅应在测试环境中使用
    """
    global _api_state_manager
    if _api_state_manager is not None:
        _api_state_manager._monitor_state.reset()
    _api_state_manager = None
