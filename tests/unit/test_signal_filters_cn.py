"""
Unit tests for Signal Filter Components

Tests the signal filters that validate trading signals.
"""

import pytest
from datetime import datetime

from backend.arbitrage.cn.strategies.signal_filters import (
    TimeFilterCN,
    ConfidenceFilter,
    RiskFilter,
)
from backend.arbitrage.models import TradingSignal
from backend.market.cn.events import LimitUpEvent
from backend.market import CandidateETF
from tests.fixtures.mocks import create_candidate_etf, create_mock_limit_up_event
from backend.utils.clock import FrozenClock
from backend.utils.clock import set_clock, reset_clock
import pytz


@pytest.mark.unit
class TestTimeFilterCN:
    """测试A股时间过滤器"""

    @pytest.fixture
    def filter(self):
        return TimeFilterCN(min_time_to_close=1800)

    @pytest.fixture
    def mock_event(self):
        return create_mock_limit_up_event('600519')

    @pytest.fixture
    def mock_fund(self):
        return create_candidate_etf('510300', weight=0.05, rank=1)

    @pytest.fixture
    def mock_signal(self):
        return TradingSignal(
            signal_id="TEST_001",
            timestamp="2024-01-01 10:00:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1800.0,
            limit_time="10:00:00",
            locked_amount=1000000,
            change_pct=0.10,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.05,
            etf_price=4.5,
            etf_premium=0.5,
            reason="测试信号",
            confidence="高",
            risk_level="中",
            actual_weight=0.05,
            weight_rank=1,
            top10_ratio=0.5
        )

    def test_filter_when_sufficient_time_to_close(self, filter, mock_event, mock_fund, mock_signal):
        """测试距收盘时间充足时不过滤"""
        # 设置时间为14:00 (距15:00收盘还有60分钟)
        frozen_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=pytz.timezone("Asia/Shanghai"))
        from backend.utils.clock import FrozenClock
        from backend.arbitrage.cn.strategies.signal_filters.time_filter import TimeFilterCN
        filter_with_clock = TimeFilterCN(min_time_to_close=1800, clock=FrozenClock(frozen_time))

        should_filter, reason = filter_with_clock.filter(mock_event, mock_fund, mock_signal)
        assert should_filter is False
        assert reason == ""

    def test_filter_when_not_trading_time(self, mock_event, mock_fund, mock_signal):
        """测试非交易时间时过滤"""
        # 设置时间为8:00 (交易时间前)
        frozen_time = datetime(2024, 1, 1, 8, 0, 0, tzinfo=pytz.timezone("Asia/Shanghai"))
        from backend.utils.clock import FrozenClock
        from backend.arbitrage.cn.strategies.signal_filters.time_filter import TimeFilterCN
        filter_with_clock = TimeFilterCN(min_time_to_close=1800, clock=FrozenClock(frozen_time))

        should_filter, reason = filter_with_clock.filter(mock_event, mock_fund, mock_signal)
        assert should_filter is True
        assert "交易时间" in reason

    def test_filter_when_too_close_to_close(self, mock_event, mock_fund, mock_signal):
        """测试距收盘时间太近时过滤"""
        # 设置时间为14:40 (距15:00收盘只有20分钟)
        frozen_time = datetime(2024, 1, 1, 14, 40, 0, tzinfo=pytz.timezone("Asia/Shanghai"))
        from backend.utils.clock import FrozenClock
        from backend.arbitrage.cn.strategies.signal_filters.time_filter import TimeFilterCN
        filter_with_clock = TimeFilterCN(min_time_to_close=1800, clock=FrozenClock(frozen_time))

        should_filter, reason = filter_with_clock.filter(mock_event, mock_fund, mock_signal)
        assert should_filter is True
        assert "时间不足" in reason

    def test_is_required(self, filter):
        """测试时间过滤是必需的"""
        assert filter.is_required is True


@pytest.mark.unit
class TestConfidenceFilter:
    """测试置信度过滤器"""

    @pytest.fixture
    def filter(self):
        return ConfidenceFilter(min_confidence="中")

    @pytest.fixture
    def mock_event(self):
        return create_mock_limit_up_event('600519')

    @pytest.fixture
    def mock_fund(self):
        return create_candidate_etf('510300', weight=0.05, rank=1)

    def create_signal(self, confidence="高", risk_level="中"):
        """创建测试信号"""
        return TradingSignal(
            signal_id="TEST_001",
            timestamp="2024-01-01 10:00:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1800.0,
            limit_time="10:00:00",
            locked_amount=1000000,
            change_pct=0.10,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.05,
            etf_price=4.5,
            etf_premium=0.5,
            reason="测试信号",
            confidence=confidence,
            risk_level=risk_level,
            actual_weight=0.05,
            weight_rank=1,
            top10_ratio=0.5
        )

    def test_filter_when_confidence_too_low(self, filter, mock_event, mock_fund):
        """测试置信度过低时过滤"""
        signal = self.create_signal(confidence="低", risk_level="中")

        should_filter, reason = filter.filter(mock_event, mock_fund, signal)
        assert should_filter is True
        assert "置信度过低" in reason
        assert "低" in reason

    def test_pass_when_confidence_meets_minimum(self, filter, mock_event, mock_fund):
        """测试置信度达标时通过"""
        signal = self.create_signal(confidence="中", risk_level="中")

        should_filter, reason = filter.filter(mock_event, mock_fund, signal)
        assert should_filter is False
        assert reason == ""

    def test_pass_when_confidence_high(self, filter, mock_event, mock_fund):
        """测试高置信度通过"""
        signal = self.create_signal(confidence="高", risk_level="中")

        should_filter, reason = filter.filter(mock_event, mock_fund, signal)
        assert should_filter is False
        assert reason == ""

    def test_custom_min_confidence(self, mock_event, mock_fund):
        """测试自定义最低置信度"""
        filter_high = ConfidenceFilter(min_confidence="高")
        signal = self.create_signal(confidence="中", risk_level="中")

        should_filter, reason = filter_high.filter(mock_event, mock_fund, signal)
        assert should_filter is True
        assert "置信度过低" in reason

    def test_is_required(self, filter):
        """测试置信度过滤不是必需的"""
        assert filter.is_required is False


@pytest.mark.unit
class TestRiskFilter:
    """测试风险过滤器"""

    @pytest.fixture
    def filter(self):
        return RiskFilter(max_top10_ratio=0.70, min_rank=1)

    @pytest.fixture
    def mock_event(self):
        return create_mock_limit_up_event('600519')

    @pytest.fixture
    def mock_fund(self):
        return create_candidate_etf('510300', weight=0.05, rank=1)

    def create_signal(self, top10_ratio=0.5, rank=1):
        """创建测试信号"""
        return TradingSignal(
            signal_id="TEST_001",
            timestamp="2024-01-01 10:00:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1800.0,
            limit_time="10:00:00",
            locked_amount=1000000,
            change_pct=0.10,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.05,
            etf_price=4.5,
            etf_premium=0.5,
            reason="测试信号",
            confidence="高",
            risk_level="中",
            actual_weight=0.05,
            weight_rank=rank,
            top10_ratio=top10_ratio
        )

    def test_filter_when_top10_ratio_too_high(self, filter, mock_event):
        """测试持仓过于集中时过滤"""
        fund = create_candidate_etf('510300', weight=0.05, rank=1, top10_ratio=0.75)
        signal = self.create_signal(top10_ratio=0.75, rank=1)

        should_filter, reason = filter.filter(mock_event, fund, signal)
        assert should_filter is True
        assert "持仓过于集中" in reason
        assert "75.0%" in reason

    def test_filter_when_rank_too_low(self, filter, mock_event):
        """测试排名过低时过滤"""
        fund = create_candidate_etf('510300', weight=0.05, rank=5, top10_ratio=0.5)
        signal = self.create_signal(top10_ratio=0.5, rank=5)

        should_filter, reason = filter.filter(mock_event, fund, signal)
        assert should_filter is True
        assert "排名过低" in reason
        assert "第5名" in reason

    def test_pass_when_risk_acceptable(self, filter, mock_event, mock_fund):
        """测试风险可接受时通过"""
        signal = self.create_signal(top10_ratio=0.5, rank=1)

        should_filter, reason = filter.filter(mock_event, mock_fund, signal)
        assert should_filter is False
        assert reason == ""

    def test_custom_risk_thresholds(self, mock_event):
        """测试自定义风险阈值"""
        filter_strict = RiskFilter(max_top10_ratio=0.50, min_rank=3)
        fund = create_candidate_etf('510300', weight=0.05, rank=2, top10_ratio=0.6)
        signal = self.create_signal(top10_ratio=0.6, rank=2)

        should_filter, reason = filter_strict.filter(mock_event, fund, signal)
        # top10_ratio超过阈值
        assert should_filter is True

    def test_no_rank_limit(self, mock_event):
        """测试不限制排名"""
        filter_no_rank = RiskFilter(max_top10_ratio=0.70, min_rank=0)
        fund = create_candidate_etf('510300', weight=0.05, rank=10, top10_ratio=0.5)
        signal = self.create_signal(top10_ratio=0.5, rank=10)

        should_filter, reason = filter_no_rank.filter(mock_event, fund, signal)
        # 不检查排名，应该通过
        assert should_filter is False

    def test_is_required(self, filter):
        """测试风险过滤不是必需的"""
        assert filter.is_required is False
