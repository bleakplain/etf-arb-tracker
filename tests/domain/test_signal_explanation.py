"""测试信号解释值对象"""
import pytest
from backend.domain.signal_explanation import (
    SignalDetailResponse,
    SignalReason,
    ConfidenceBreakdown,
    ScoreItem,
    DataSourceInfo
)


def test_score_item_creation():
    """评分项可以创建"""
    item = ScoreItem(
        name="封单量评分",
        score=90,
        weight=0.3,
        value=12.5,
        threshold=10.0,
        passed=True
    )
    assert item.name == "封单量评分"
    assert item.score == 90
    assert item.passed is True


def test_confidence_breakdown_calculation():
    """置信度拆解计算正确"""
    breakdown = ConfidenceBreakdown(
        total_score=85,
        level="high",
        order_amount_score=ScoreItem(
            name="封单量评分",
            score=90,
            weight=0.3,
            value=12.5,
            threshold=10.0,
            passed=True
        ),
        weight_score=ScoreItem(
            name="权重评分",
            score=85,
            weight=0.3,
            value=0.08,
            threshold=0.05,
            passed=True
        ),
        liquidity_score=ScoreItem(
            name="流动性评分",
            score=88,
            weight=0.25,
            value=8500,
            threshold=5000,
            passed=True
        ),
        time_to_close_score=ScoreItem(
            name="距收盘评分",
            score=70,
            weight=0.15,
            value=7200,
            threshold=1800,
            passed=False
        )
    )
    assert breakdown.total_score == 85
    assert breakdown.level == "high"
    assert len([s for s in breakdown.scores() if s.passed]) == 3


def test_signal_reason_passed_checks():
    """信号原因包含通过的检查项"""
    reason = SignalReason(
        stock_code="600519",
        stock_name="贵州茅台",
        limit_up_price=1850.0,
        seal_amount=12.5,
        time_to_close=7200,
        etf_code="510300",
        etf_name="沪深300ETF",
        etf_weight=0.085,
        etf_volume=8500,
        all_checks_passed=[
            "股票涨停",
            "ETF持有该股票 (权重8.5% ≥ 5%)",
            "ETF流动性充足 (成交额8500万 ≥ 5000万)"
        ],
        warnings=[
            "距收盘时间较近，建议谨慎"
        ]
    )
    assert len(reason.all_checks_passed) == 3
    assert len(reason.warnings) == 1
    assert reason.stock_code == "600519"


def test_signal_detail_response_structure():
    """信号详情响应结构正确"""
    detail = SignalDetailResponse(
        signal_id="signal-123",
        timestamp="2024-03-15 14:30:00",
        reason=SignalReason(
            stock_code="600519",
            stock_name="贵州茅台",
            limit_up_price=1850.0,
            seal_amount=12.5,
            time_to_close=7200,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.085,
            etf_volume=8500,
            all_checks_passed=[],
            warnings=[]
        ),
        confidence=ConfidenceBreakdown(
            total_score=85,
            level="high",
            order_amount_score=ScoreItem(
                name="封单量评分", score=90, weight=0.3,
                value=12.5, threshold=10.0, passed=True
            ),
            weight_score=ScoreItem(
                name="权重评分", score=85, weight=0.3,
                value=0.08, threshold=0.05, passed=True
            ),
            liquidity_score=ScoreItem(
                name="流动性评分", score=88, weight=0.25,
                value=8500, threshold=5000, passed=True
            ),
            time_to_close_score=ScoreItem(
                name="距收盘评分", score=70, weight=0.15,
                value=7200, threshold=1800, passed=False
            )
        ),
        data_source=DataSourceInfo(
            stock_data_source="akshare",
            stock_data_complete=True,
            etf_data_source="akshare",
            etf_data_complete=True,
            holdings_data_source="quarterly_snapshot",
            holdings_interpolation="linear"
        )
    )
    assert detail.signal_id == "signal-123"
    assert detail.confidence.level == "high"
