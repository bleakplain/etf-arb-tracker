"""
时间提供者抽象

用于将时间依赖抽象化，便于测试时注入固定时间
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from abc import ABC, abstractmethod


class Clock(ABC):
    """时间提供者抽象接口"""

    @abstractmethod
    def now(self, tz: Optional[timezone] = None) -> datetime:
        """
        获取当前时间

        Args:
            tz: 时区，None表示本地时区

        Returns:
            当前时间
        """
        pass


class SystemClock(Clock):
    """系统时钟 - 使用真实的系统时间"""

    def now(self, tz: Optional[timezone] = None) -> datetime:
        """获取系统当前时间"""
        if tz:
            return datetime.now(tz)
        return datetime.now()


class FrozenClock(Clock):
    """固定时钟 - 用于测试，返回预设的时间"""

    def __init__(self, frozen_time: datetime):
        """
        初始化固定时钟

        Args:
            frozen_time: 固定的时间点
        """
        self._frozen_time = frozen_time

    def now(self, tz: Optional[timezone] = None) -> datetime:
        """返回固定的时间"""
        # 忽略时区参数，返回固定时间
        return self._frozen_time


class ShiftClock(Clock):
    """偏移时钟 - 基于基准时间进行偏移"""

    def __init__(self, base_clock: Clock, offset: timedelta = None):
        """
        初始化偏移时钟

        Args:
            base_clock: 基准时钟
            offset: 时间偏移量
        """
        self._base_clock = base_clock
        self._offset = offset or timedelta()

    def now(self, tz: Optional[timezone] = None) -> datetime:
        """获取偏移后的时间"""
        base_time = self._base_clock.now(tz)
        return base_time + self._offset

    def set_offset(self, offset: timedelta) -> None:
        """设置时间偏移"""
        self._offset = offset


# 默认时钟实例
_default_clock: Optional[Clock] = None


def get_clock() -> Clock:
    """
    获取默认时钟实例

    Returns:
        当前时钟实例
    """
    global _default_clock
    if _default_clock is None:
        _default_clock = SystemClock()
    return _default_clock


def set_clock(clock: Clock) -> None:
    """
    设置默认时钟实例

    Args:
        clock: 时钟实例
    """
    global _default_clock
    _default_clock = clock


def reset_clock() -> None:
    """重置为系统时钟"""
    global _default_clock
    _default_clock = SystemClock()


def now(tz: Optional[timezone] = None) -> datetime:
    """
    获取当前时间的便捷函数

    Args:
        tz: 时区

    Returns:
        当前时间
    """
    return get_clock().now(tz)


# 中国时区常量
CHINA_TZ = timezone(timedelta(hours=8))


def now_china() -> datetime:
    """获取中国时区当前时间"""
    return now(CHINA_TZ)
