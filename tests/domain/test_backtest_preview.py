"""测试回测数据预览值对象"""
import pytest
from datetime import datetime
from backend.domain.backtest_preview import (
    DataPreviewResponse,
    DataCoverage,
    MonthCoverage,
    StockDataStatus,
    ETFDataStatus,
    QualityScore,
    DataStatus
)


def test_month_coverage_creation():
    """月度覆盖度可以创建"""
    coverage = MonthCoverage(
        year=2024,
        month=1,
        total_days=22,
        covered_days=22,
        percentage=100.0
    )
    assert coverage.year == 2024
    assert coverage.month == 1
    assert coverage.percentage == 100.0


def test_data_coverage_calculation():
    """数据覆盖度计算正确"""
    coverage = DataCoverage(
        trading_days_total=244,
        trading_days_covered=220,
        coverage_percentage=90.16,
        monthly_coverage=[],
        missing_dates=["20240115", "20240116"]
    )
    assert coverage.trading_days_total == 244
    assert coverage.trading_days_covered == 220
    assert len(coverage.missing_dates) == 2


def test_stock_data_status_complete():
    """完整数据状态"""
    status = StockDataStatus(
        code="600519",
        name="贵州茅台",
        data_points=242,
        expected_points=244,
        status="complete",
        missing_dates=[]
    )
    assert status.status == "complete"
    assert status.completeness_rate > 0.99


def test_stock_data_status_partial():
    """部分缺失数据状态"""
    status = StockDataStatus(
        code="000858",
        name="五粮液",
        data_points=180,
        expected_points=244,
        status="partial",
        missing_dates=["20240101", "20240102"]
    )
    assert status.status == "partial"
    assert len(status.missing_dates) == 2


def test_quality_score_calculation():
    """数据质量评分计算"""
    score = QualityScore.calculate(
        stocks_complete_rate=0.95,
        etfs_complete_rate=0.90,
        trading_days_coverage=0.92
    )
    assert 80 <= score.overall_score <= 100
    assert score.grade in ["A+", "A", "B+"]


def test_quality_score_low():
    """低质量数据评分"""
    score = QualityScore.calculate(
        stocks_complete_rate=0.4,
        etfs_complete_rate=0.3,
        trading_days_coverage=0.5
    )
    assert score.overall_score < 60
    assert score.grade in ["C", "D"]


def test_data_preview_response_structure():
    """数据预览响应结构正确"""
    response = DataPreviewResponse(
        preview_id="test-preview-123",
        date_range={"start": "20240101", "end": "20241231"},
        coverage=DataCoverage(
            trading_days_total=244,
            trading_days_covered=244,
            coverage_percentage=100.0,
            monthly_coverage=[],
            missing_dates=[]
        ),
        stocks_status=[],
        etfs_status=[],
        quality_score=QualityScore(
            overall_score=95,
            grade="A",
            stocks_complete_rate=1.0,
            etfs_complete_rate=1.0,
            trading_days_coverage=1.0
        )
    )
    assert response.preview_id == "test-preview-123"
    assert response.quality_score.grade == "A"
