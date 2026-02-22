"""
回测配置 - 跨市场通用
"""

from dataclasses import dataclass
from typing import List, Optional, Any
from datetime import datetime

from .clock import TimeGranularity


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: str
    end_date: str
    time_granularity: TimeGranularity = TimeGranularity.DAILY
    min_weight: float = 0.05
    min_time_to_close: int = 1800
    min_etf_volume: float = 50000000
    evaluator_type: str = "default"
    snapshot_dates: Optional[List[str]] = None
    interpolation: str = "linear"
    use_watchlist: bool = True

    # 常量定义
    MIN_DATE = "20000101"
    MAX_DATE = "20991231"
    MIN_WEIGHT_THRESHOLD = 0.001
    MAX_WEIGHT_THRESHOLD = 1.0

    def __post_init__(self):
        """配置验证"""
        self._validate_dates()
        self._validate_weights()
        self._validate_interpolation()

    def _validate_dates(self) -> None:
        """验证日期范围"""
        try:
            start_dt = datetime.strptime(self.start_date, "%Y%m%d")
            end_dt = datetime.strptime(self.end_date, "%Y%m%d")

            if start_dt < datetime.strptime(self.MIN_DATE, "%Y%m%d"):
                raise ValueError(f"开始日期不能早于 {self.MIN_DATE}")
            if end_dt > datetime.strptime(self.MAX_DATE, "%Y%m%d"):
                raise ValueError(f"结束日期不能晚于 {self.MAX_DATE}")
            if start_dt > end_dt:
                raise ValueError(f"开始日期 {self.start_date} 不能晚于结束日期 {self.end_date}")

        except ValueError as e:
            if "time data" in str(e):
                raise ValueError(f"日期格式错误，应为YYYYMMDD格式")
            raise

    def _validate_weights(self) -> None:
        """验证权重参数"""
        if not (self.MIN_WEIGHT_THRESHOLD <= self.min_weight <= self.MAX_WEIGHT_THRESHOLD):
            raise ValueError(
                f"权重必须在 {self.MIN_WEIGHT_THRESHOLD} 到 {self.MAX_WEIGHT_THRESHOLD} 之间"
            )

    def _validate_interpolation(self) -> None:
        """验证插值方式"""
        valid_interpolations = ["linear", "step"]
        if self.interpolation not in valid_interpolations:
            raise ValueError(f"插值方式必须是 {valid_interpolations} 之一")

    @classmethod
    def from_dict(cls, data: dict) -> "BacktestConfig":
        """从字典创建配置"""
        granularity = TimeGranularity(data.get("time_granularity", "daily"))

        return cls(
            start_date=data["start_date"],
            end_date=data["end_date"],
            time_granularity=granularity,
            min_weight=data.get("min_weight", 0.05),
            min_time_to_close=data.get("min_time_to_close", 1800),
            min_etf_volume=data.get("min_etf_volume", 50000000),
            evaluator_type=data.get("evaluator_type", "default"),
            snapshot_dates=data.get("snapshot_dates"),
            interpolation=data.get("interpolation", "linear"),
            use_watchlist=data.get("use_watchlist", True)
        )
