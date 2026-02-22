"""
Unit tests for Market Strategy Components

Tests the event detectors, fund selectors, and signal filters.
"""

import pytest
from datetime import datetime

from backend.arbitrage.cn.strategies.event_detectors import LimitUpDetectorCN
from backend.arbitrage.cn.strategies.fund_selectors import HighestWeightSelector
from backend.market.cn.events import LimitUpEvent
from tests.fixtures.mocks import create_candidate_etf


@pytest.mark.unit
class TestLimitUpDetectorCN:
    """测试涨停检测器"""

    @pytest.fixture
    def detector(self):
        return LimitUpDetectorCN(min_change_pct=0.095)

    def test_detect_limit_up_stock(self, detector):
        """测试检测涨停股票"""
        quote = {
            'code': '600519',
            'name': '贵州茅台',
            'price': 1800.0,
            'change_pct': 0.1001,
            'is_limit_up': True,
            'timestamp': '14:00:00',
        }

        event = detector.detect(quote)

        assert event is not None
        assert isinstance(event, LimitUpEvent)
        assert event.stock_code == '600519'

    def test_detect_non_limit_up_stock(self, detector):
        """测试检测非涨停股票"""
        quote = {
            'code': '000001',
            'name': '平安银行',
            'price': 12.50,
            'change_pct': 0.015,
            'is_limit_up': False,
            'timestamp': '14:30:00',
        }

        event = detector.detect(quote)

        assert event is None

    def test_is_valid_always_true(self, detector):
        """测试验证总是返回True"""
        from tests.fixtures.mocks import create_mock_limit_up_event
        event = create_mock_limit_up_event('600519')

        assert detector.is_valid(event) is True


@pytest.mark.unit
class TestHighestWeightSelector:
    """测试最高权重选择器"""

    @pytest.fixture
    def selector(self):
        return HighestWeightSelector()

    @pytest.fixture
    def mock_event(self):
        from tests.fixtures.mocks import create_mock_limit_up_event
        return create_mock_limit_up_event('600519')

    def test_select_highest_weight_etf(self, selector, mock_event):
        """测试选择权重最高的ETF"""
        funds = [
            create_candidate_etf('510300', weight=0.05, rank=3),
            create_candidate_etf('510500', weight=0.08, rank=1),
            create_candidate_etf('516160', weight=0.06, rank=2),
        ]

        selected = selector.select(funds, mock_event)

        assert selected is not None
        assert selected.etf_code == '510500'
        assert selected.weight == 0.08

    def test_select_returns_none_for_empty_list(self, selector, mock_event):
        """测试空列表返回None"""
        selected = selector.select([], mock_event)
        assert selected is None

    def test_get_selection_reason(self, selector):
        """测试获取选择原因"""
        fund = create_candidate_etf('510500', weight=0.08, rank=1)
        reason = selector.get_selection_reason(fund)

        assert '权重最高' in reason
