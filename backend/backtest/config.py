"""
回测配置 - 简化版
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

from backend.market import CandidateETF


@dataclass
class BacktestConfig:
    """
    回测配置（简化版）

    只支持日级别回测，持仓数据固定或 mock
    """
    start_date: str  # "YYYYMMDD"
    end_date: str    # "YYYYMMDD"
    stock_codes: List[str]  # 股票代码列表
    etf_codes: List[str]    # ETF代码列表

    # 持仓数据（可选）
    # 格式: {stock_code: [CandidateETF, ...]}
    stock_etf_mapping: Optional[Dict[str, List[CandidateETF]]] = None

    # 策略参数
    min_weight: float = 0.05  # 最小持仓权重
    evaluator_type: str = "default"  # 信号评估器类型

    # 数据源配置
    use_mock_data: bool = True  # 是否使用 mock 持仓数据
    mock_etf_count: int = 4  # 每只股票随机关联的 ETF 数量

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
        获取交易日列表（简化版：排除周末）

        Returns:
            日期字符串列表 ["YYYYMMDD", ...]
        """
        start_dt = datetime.strptime(self.start_date, "%Y%m%d")
        end_dt = datetime.strptime(self.end_date, "%Y%m%d")

        days = []
        current = start_dt
        while current <= end_dt:
            # 排除周末（周六=5, 周日=6）
            if current.weekday() < 5:
                days.append(current.strftime("%Y%m%d"))
            current += __import__("datetime").timedelta(days=1)

        return days
