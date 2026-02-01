"""
回测数据预览值对象

用于向用户展示回测将使用的数据质量和覆盖情况
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
from enum import Enum


class DataStatus(Enum):
    """数据状态"""
    COMPLETE = "complete"  # 完整 (>90%)
    PARTIAL = "partial"    # 部分缺失 (50%-90%)
    MISSING = "missing"    # 缺失/不足 (<50%)


@dataclass
class MonthCoverage:
    """月度覆盖度"""
    year: int
    month: int
    total_days: int
    covered_days: int
    percentage: float

    @classmethod
    def create(cls, year: int, month: int, covered_days: int, total_days: int) -> "MonthCoverage":
        """创建月度覆盖度"""
        percentage = (covered_days / total_days * 100) if total_days > 0 else 0.0
        return cls(
            year=year,
            month=month,
            total_days=total_days,
            covered_days=covered_days,
            percentage=round(percentage, 2)
        )


@dataclass
class DataCoverage:
    """数据覆盖度"""
    trading_days_total: int
    trading_days_covered: int
    coverage_percentage: float
    monthly_coverage: List[MonthCoverage]
    missing_dates: List[str]  # YYYYMMDD格式的缺失日期列表

    @property
    def coverage_rate(self) -> float:
        """覆盖率"""
        return self.coverage_percentage / 100


@dataclass
class StockDataStatus:
    """股票数据状态"""
    code: str
    name: str
    data_points: int
    expected_points: int
    status: Literal["complete", "partial", "missing"]
    missing_dates: List[str]

    @property
    def completeness_rate(self) -> float:
        """完整率"""
        if self.expected_points == 0:
            return 0.0
        return self.data_points / self.expected_points


@dataclass
class ETFDataStatus:
    """ETF数据状态"""
    code: str
    name: str
    data_points: int
    expected_points: int
    status: Literal["complete", "partial", "missing"]
    missing_dates: List[str]

    @property
    def completeness_rate(self) -> float:
        """完整率"""
        if self.expected_points == 0:
            return 0.0
        return self.data_points / self.expected_points


@dataclass
class QualityScore:
    """数据质量评分"""
    overall_score: int  # 0-100
    grade: str  # A+, A, B+, B, C, D
    stocks_complete_rate: float
    etfs_complete_rate: float
    trading_days_coverage: float

    @classmethod
    def calculate(
        cls,
        stocks_complete_rate: float,
        etfs_complete_rate: float,
        trading_days_coverage: float
    ) -> "QualityScore":
        """计算数据质量评分

        评分标准:
        - 股票完整率: 40分
        - ETF完整率: 30分
        - 交易日覆盖: 30分
        """
        # 加权计算总分
        stock_score = stocks_complete_rate * 40
        etf_score = etfs_complete_rate * 30
        trading_score = trading_days_coverage * 30

        total = int(stock_score + etf_score + trading_score)

        # 确定等级
        if total >= 95:
            grade = "A+"
        elif total >= 90:
            grade = "A"
        elif total >= 85:
            grade = "B+"
        elif total >= 75:
            grade = "B"
        elif total >= 60:
            grade = "C"
        else:
            grade = "D"

        return cls(
            overall_score=total,
            grade=grade,
            stocks_complete_rate=stocks_complete_rate,
            etfs_complete_rate=etfs_complete_rate,
            trading_days_coverage=trading_days_coverage
        )


@dataclass
class DataPreviewResponse:
    """数据预览响应"""
    preview_id: str
    date_range: Dict[str, str]
    coverage: DataCoverage
    stocks_status: List[StockDataStatus]
    etfs_status: List[ETFDataStatus]
    quality_score: QualityScore
