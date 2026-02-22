"""
时间工具模块
提供timezone-aware的datetime处理功能
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# 引入时钟抽象
from backend.utils.clock import get_clock, CHINA_TZ


def now_china() -> datetime:
    """
    获取中国时区的当前时间

    Returns:
        timezone-aware的datetime对象
    """
    return get_clock().now(CHINA_TZ)


def now_china_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取中国时区的当前时间字符串

    Args:
        fmt: 时间格式字符串

    Returns:
        格式化后的时间字符串
    """
    return now_china().strftime(fmt)


def today_china() -> str:
    """
    获取中国时区的今天日期字符串

    Returns:
        YYYY-MM-DD格式的日期字符串
    """
    return now_china_str("%Y-%m-%d")


def today_china_compact() -> str:
    """
    获取中国时区的今天日期字符串（紧凑格式）

    Returns:
        YYYYMMDD格式的日期字符串
    """
    return now_china_str("%Y%m%d")


def timestamp_now() -> str:
    """
    获取当前时间戳（毫秒）

    Returns:
        毫秒时间戳字符串
    """
    return str(int(now_china().timestamp() * 1000))


def is_trading_time(
    morning_start: tuple = (9, 30),
    morning_end: tuple = (11, 30),
    afternoon_start: tuple = (13, 0),
    afternoon_end: tuple = (15, 0)
) -> bool:
    """
    判断当前是否是交易时间（中国时区）

    Args:
        morning_start: 上午开盘时间 (时, 分)
        morning_end: 上午收盘时间 (时, 分)
        afternoon_start: 下午开盘时间 (时, 分)
        afternoon_end: 下午收盘时间 (时, 分)

    Returns:
        是否在交易时间
    """
    now = now_china()
    current_time = now.time()

    from datetime import time
    morning_start_time = time(*morning_start)
    morning_end_time = time(*morning_end)
    afternoon_start_time = time(*afternoon_start)
    afternoon_end_time = time(*afternoon_end)

    # 检查是否在上午交易时段
    if morning_start_time <= current_time <= morning_end_time:
        return True

    # 检查是否在下午交易时段
    if afternoon_start_time <= current_time <= afternoon_end_time:
        return True

    return False


def time_to_close(
    morning_end: tuple = (11, 30),
    afternoon_end: tuple = (15, 0)
) -> Optional[int]:
    """
    计算距离收盘的时间（秒）

    Args:
        morning_end: 上午收盘时间 (时, 分)
        afternoon_end: 下午收盘时间 (时, 分)

    Returns:
        距离收盘的秒数，如果不在交易时间返回None
    """
    now = now_china()
    current_time = now.time()

    from datetime import time, datetime as dt
    morning_end_time = time(*morning_end)
    afternoon_end_time = time(*afternoon_end)

    # 判断当前是哪个交易时段
    if current_time <= morning_end_time:
        # 上午交易时段
        close_time = dt.combine(now.date(), morning_end_time, tzinfo=CHINA_TZ)
    elif current_time <= afternoon_end_time:
        # 下午交易时段
        close_time = dt.combine(now.date(), afternoon_end_time, tzinfo=CHINA_TZ)
    else:
        # 已收盘
        return None

    return int((close_time - now).total_seconds())
