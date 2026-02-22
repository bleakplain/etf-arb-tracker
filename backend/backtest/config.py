"""
回测配置
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

from backend.market import CandidateETF


@dataclass
class BacktestConfig:
    """
    回测配置

    支持日级别回测，持仓数据可为固定映射或自动生成 mock 数据。
    """
    start_date: str
    end_date: str
    stock_codes: List[str]
    etf_codes: List[str]

    # 持仓数据（可选）
    stock_etf_mapping: Optional[Dict[str, List[CandidateETF]]] = None

    # 策略参数
    min_weight: float = 0.05
    evaluator_type: str = "default"

    # 数据源配置
    use_mock_data: bool = True
    mock_etf_count: int = 4

    def __post_init__(self):
        """配置验证"""
        self._validate_dates()

    def _validate_dates(self) -> None:
        """验证日期范围"""
        try:
            start_dt = datetime.strptime(self.start_date, "%Y%m%d")
            end_dt = datetime.strptime(self.end_date, "%Y%m%d")

            if start_dt > end_dt:
                raise ValueError(f"开始日期 {self.start_date} 不能晚于结束日期 {self.end_date}")

        except ValueError as e:
            if "time data" in str(e):
                raise ValueError(f"日期格式错误，应为YYYYMMDD格式")
            raise

    @property
    def trading_days(self) -> List[str]:
        """
        获取交易日列表（排除周末）

        Returns:
            日期字符串列表 ["YYYYMMDD", ...]
        """
        start_dt = datetime.strptime(self.start_date, "%Y%m%d")
        end_dt = datetime.strptime(self.end_date, "%Y%m%d")

        days = []
        current = start_dt
        while current <= end_dt:
            if current.weekday() < 5:
                days.append(current.strftime("%Y%m%d"))
            current += __import__("datetime").timedelta(days=1)

        return days
