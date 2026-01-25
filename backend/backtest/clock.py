"""
模拟时钟 - 支持多种时间粒度的时间推进

用于回测中模拟交易时间的推进。
"""

from datetime import datetime, time, timedelta
from enum import Enum
from typing import List, Optional, Tuple, Set

from loguru import logger


class TimeGranularity(Enum):
    """时间粒度"""
    DAILY = "daily"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"

    @property
    def delta_minutes(self) -> int:
        """获取时间粒度对应的分钟数"""
        mapping = {
            TimeGranularity.MINUTE_5: 5,
            TimeGranularity.MINUTE_15: 15,
            TimeGranularity.MINUTE_30: 30,
        }
        return mapping.get(self, 0)

    @property
    def is_daily(self) -> bool:
        """是否为日级别"""
        return self == TimeGranularity.DAILY


class ChineseHolidays:
    """
    中国A股节假日管理

    包含主要节假日，用于排除非交易日
    """

    # 2024年主要节假日（YYYYMMDD格式）
    HOLIDAYS_2024: Set[str] = {
        # 元旦
        "20240101",
        # 春节
        "20240210", "20240212", "20240213", "20240214", "20240215", "20240216",
        "20240217",
        # 清明节
        "20240404", "20240405", "20240406",
        # 劳动节
        "20240501", "20240502", "20240503", "20240504", "20240505",
        # 端午节
        "20240610",
        # 中秋节
        "20240915", "20240916", "20240917",
        # 国庆节
        "20241001", "20241002", "20241003", "20241004", "20241005",
        "20241006", "20241007",
    }

    @classmethod
    def get_holidays(cls, year: int) -> Set[str]:
        """
        获取指定年份的节假日

        Args:
            year: 年份

        Returns:
            节假日日期集合（YYYYMMDD格式）
        """
        # 返回已知年份的节假日
        known_holidays = {
            2024: cls.HOLIDAYS_2024,
        }

        holidays = known_holidays.get(year, set())

        # 对于未知年份，返回空集合（假设无节假日）
        if year not in known_holidays:
            logger.warning(
                f"年份 {year} 的节假日数据未配置，"
                f"将使用简化交易日历（可能包含节假日）"
            )

        return holidays

    @classmethod
    def is_holiday(cls, date: datetime) -> bool:
        """
        判断是否为节假日

        Args:
            date: 日期

        Returns:
            是否为节假日
        """
        date_str = date.strftime("%Y%m%d")
        return date_str in cls.get_holidays(date.year)


class SimulationClock:
    """
    模拟时钟

    支持日级别和分钟级别的时间推进，自动跳过非交易日。
    """

    # 交易时间定义
    MORNING_START = time(9, 30)
    MORNING_END = time(11, 30)
    AFTERNOON_START = time(13, 0)
    AFTERNOON_END = time(15, 0)

    def __init__(
        self,
        start_date: str,
        end_date: str,
        granularity: TimeGranularity = TimeGranularity.DAILY,
        trading_calendar: Optional[List[datetime]] = None,
        use_real_holidays: bool = True
    ):
        """
        初始化模拟时钟

        Args:
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
            granularity: 时间粒度
            trading_calendar: 交易日历（可选），如果不提供则自动生成工作日
            use_real_holidays: 是否使用真实节假日（默认True）
        """
        self.start = self._parse_date(start_date)
        self.end = self._parse_date(end_date)
        self.current = self.start
        self.granularity = granularity
        self.use_real_holidays = use_real_holidays

        # 构建交易日历
        self.trading_calendar = trading_calendar or self._build_trading_calendar()
        self._current_index = 0

        logger.info(
            f"模拟时钟初始化: {start_date} -> {end_date}, "
            f"粒度: {granularity.value}, 交易日数: {len(self.trading_calendar)}, "
            f"节假日过滤: {'开启' if use_real_holidays else '关闭'}"
        )

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """解析日期字符串"""
        if len(date_str) == 8:
            return datetime.strptime(date_str, "%Y%m%d")
        return datetime.strptime(date_str, "%Y-%m-%d")

    def _build_trading_calendar(self) -> List[datetime]:
        """
        构建交易日历

        排除周末和中国主要节假日
        """
        calendar = []
        current = self.start

        while current <= self.end:
            # 排除周末（周六=5, 周日=6）
            if current.weekday() < 5:
                # 排除节假日（如果启用）
                if not self.use_real_holidays or not ChineseHolidays.is_holiday(current):
                    calendar.append(current)
            current += timedelta(days=1)

        return calendar

    def advance(self, steps: int = 1) -> datetime:
        """
        推进时间

        Args:
            steps: 推进步数

        Returns:
            当前时间
        """
        if self.granularity.is_daily:
            # 日级别：直接移动到下一个交易日
            self._current_index = min(
                self._current_index + steps,
                len(self.trading_calendar) - 1
            )
            self.current = self.trading_calendar[self._current_index]
        else:
            # 分钟级别：在同一天内推进
            self._advance_minutes(steps)

        return self.current

    def _advance_minutes(self, steps: int) -> None:
        """分钟级别推进"""
        delta_minutes = self.granularity.delta_minutes * steps

        # 先尝试在当天推进
        new_time = self.current + timedelta(minutes=delta_minutes)

        # 检查是否跨天
        if new_time.date() != self.current.date():
            # 移动到下一个交易日
            self._current_index = min(
                self._current_index + 1,
                len(self.trading_calendar) - 1
            )
            next_day = self.trading_calendar[self._current_index]

            # 从早上9:30开始
            self.current = next_day.replace(
                hour=self.MORNING_START.hour,
                minute=self.MORNING_START.minute,
                second=0,
                microsecond=0
            )
        else:
            # 检查是否超出交易时间
            if new_time.time() > self.AFTERNOON_END:
                # 移动到下一个交易日
                self._current_index = min(
                    self._current_index + 1,
                    len(self.trading_calendar) - 1
                )
                next_day = self.trading_calendar[self._current_index]
                self.current = next_day.replace(
                    hour=self.MORNING_START.hour,
                    minute=self.MORNING_START.minute,
                    second=0,
                    microsecond=0
                )
            else:
                # 跳过午休时间
                if (
                    self.current.time() < self.AFTERNOON_START and
                    new_time.time() >= self.MORNING_END
                ):
                    # 午休，直接跳到下午开盘
                    self.current = self.current.replace(
                        hour=self.AFTERNOON_START.hour,
                        minute=self.AFTERNOON_START.minute
                    )
                else:
                    self.current = new_time

    def has_next(self) -> bool:
        """是否还有下一个时间点"""
        if self.granularity.is_daily:
            return self._current_index < len(self.trading_calendar) - 1

        # 分钟级别检查
        if self._current_index >= len(self.trading_calendar) - 1:
            return False

        # 检查当天是否还有时间
        current_day_end = self.current.replace(
            hour=self.AFTERNOON_END.hour,
            minute=self.AFTERNOON_END.minute
        )
        return self.current < current_day_end

    def is_trading_time(self) -> bool:
        """判断当前是否在交易时间内"""
        current_time = self.current.time()

        if self.granularity.is_daily:
            return True

        return (
            self.MORNING_START <= current_time <= self.MORNING_END or
            self.AFTERNOON_START <= current_time <= self.AFTERNOON_END
        )

    def get_time_to_close(self) -> int:
        """
        获取距离收盘的秒数

        Returns:
            距离收盘的秒数，不在交易时间返回-1
        """
        if not self.is_trading_time():
            return -1

        current_time = self.current.time()

        # 上午时段，计算到上午收盘
        if current_time <= self.MORNING_END:
            close_time = self.current.replace(
                hour=self.MORNING_END.hour,
                minute=self.MORNING_END.minute,
                second=0
            )
        else:
            # 下午时段，计算到下午收盘
            close_time = self.current.replace(
                hour=self.AFTERNOON_END.hour,
                minute=self.AFTERNOON_END.minute,
                second=0
            )

        return int((close_time - self.current).total_seconds())

    def reset(self) -> None:
        """重置时钟到开始时间"""
        self._current_index = 0
        self.current = self.trading_calendar[0] if self.trading_calendar else self.start

    def get_progress(self) -> float:
        """获取回测进度"""
        if self.granularity.is_daily:
            return self._current_index / len(self.trading_calendar) if self.trading_calendar else 0

        # 分钟级别进度估算（简化版）
        total_days = len(self.trading_calendar)
        if total_days == 0:
            return 0.0

        # 已完成的整天数 + 当天进度
        completed_days = self._current_index
        current_day_progress = 0.0

        # 简化：每天平均交易4小时（240分钟）
        if self.granularity == TimeGranularity.MINUTE_5:
            total_minutes_per_day = 240  # 假设交易时段总时长
            elapsed_minutes = (self.current.hour - 9) * 60 + self.current.minute - 30
            current_day_progress = max(0, min(1, elapsed_minutes / total_minutes_per_day))
        elif self.granularity == TimeGranularity.MINUTE_15:
            total_slots = 16  # 4小时 / 15分钟
            slot = (self.current.hour - 9) * 4 + (self.current.minute // 15) - 2
            current_day_progress = max(0, min(1, slot / total_slots))
        elif self.granularity == TimeGranularity.MINUTE_30:
            total_slots = 8  # 4小时 / 30分钟
            slot = (self.current.hour - 9) * 2 + (self.current.minute // 30) - 1
            current_day_progress = max(0, min(1, slot / total_slots))

        return (completed_days + current_day_progress) / total_days

    @property
    def current_date_str(self) -> str:
        """获取当前日期字符串"""
        return self.current.strftime("%Y-%m-%d")

    @property
    def current_datetime_str(self) -> str:
        """获取当前日期时间字符串"""
        return self.current.strftime("%Y-%m-%d %H:%M:%S")

    def get_date_range(self) -> Tuple[str, str]:
        """获取日期范围"""
        return (
            self.start.strftime("%Y-%m-%d"),
            self.end.strftime("%Y-%m-%d")
        )
