"""
Unit tests for CNQuoteFetcher

Tests the quote fetcher for A-share market.
"""

import pytest
from unittest.mock import Mock, patch

from backend.market.cn.quote_fetcher import CNQuoteFetcher
from backend.utils.clock import SystemClock


@pytest.mark.unit
class TestCNQuoteFetcher:
    """测试A股行情获取器"""

    @pytest.fixture
    def fetcher(self):
        return CNQuoteFetcher()

    @pytest.fixture
    def fetcher_with_clock(self):
        from backend.utils.clock import FrozenClock
        from datetime import datetime
        frozen_time = datetime(2024, 1, 1, 10, 0, 0)
        return CNQuoteFetcher(clock=FrozenClock(frozen_time))

    def test_init_default_clock(self, fetcher):
        """测试默认使用SystemClock初始化"""
        assert fetcher._tencent_source is None
        assert isinstance(fetcher._clock, SystemClock)

    def test_init_custom_clock(self, fetcher_with_clock):
        """测试使用自定义时钟初始化"""
        assert fetcher_with_clock._tencent_source is None
        # 自定义时钟已注入

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_tencent_source_lazy_initialization(self, mock_tencent_class, fetcher):
        """测试腾讯数据源延迟初始化"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        # 第一次调用应该初始化
        source1 = fetcher._get_tencent_source()
        assert source1 == mock_source
        mock_tencent_class.assert_called_once()

        # 第二次调用应该返回缓存的实例
        source2 = fetcher._get_tencent_source()
        assert source2 == source1
        assert mock_tencent_class.call_count == 1

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_stock_quote(self, mock_tencent_class, fetcher):
        """测试获取单个股票行情"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        expected_quote = {
            'code': '600519',
            'name': '贵州茅台',
            'price': 1800.0,
            'change_pct': 1.2
        }
        mock_source.get_quote.return_value = expected_quote

        result = fetcher.get_stock_quote('600519')

        assert result == expected_quote
        mock_source.get_quote.assert_called_once_with('600519')

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_stock_quote_none(self, mock_tencent_class, fetcher):
        """测试获取不存在的股票行情"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source
        mock_source.get_quote.return_value = None

        result = fetcher.get_stock_quote('999999')

        assert result is None
        mock_source.get_quote.assert_called_once_with('999999')

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_batch_quotes(self, mock_tencent_class, fetcher):
        """测试批量获取股票行情"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        expected_quotes = {
            '600519': {'code': '600519', 'name': '贵州茅台', 'price': 1800.0},
            '000001': {'code': '000001', 'name': '平安银行', 'price': 12.50},
        }
        mock_source.get_batch_quotes.return_value = expected_quotes

        codes = ['600519', '000001']
        result = fetcher.get_batch_quotes(codes)

        assert result == expected_quotes
        mock_source.get_batch_quotes.assert_called_once_with(codes)

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_batch_quotes_empty(self, mock_tencent_class, fetcher):
        """测试批量获取空列表"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source
        mock_source.get_batch_quotes.return_value = {}

        result = fetcher.get_batch_quotes([])

        assert result == {}
        mock_source.get_batch_quotes.assert_called_once_with([])

    @patch('backend.market.cn.quote_fetcher.is_trading_time')
    def test_is_trading_time(self, mock_is_trading, fetcher):
        """测试判断是否交易时间"""
        mock_is_trading.return_value = True

        result = fetcher.is_trading_time()

        assert result is True
        mock_is_trading.assert_called_once()

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_today_limit_ups(self, mock_tencent_class, fetcher):
        """测试获取今日涨停股票"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        expected_limit_ups = [
            {'code': '600519', 'name': '贵州茅台', 'change_pct': 10.01},
            {'code': '000001', 'name': '平安银行', 'change_pct': 10.05},
        ]
        mock_source.get_limit_ups.return_value = expected_limit_ups

        result = fetcher.get_today_limit_ups()

        assert result == expected_limit_ups
        mock_source.get_limit_ups.assert_called_once()

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_today_limit_ups_empty(self, mock_tencent_class, fetcher):
        """测试获取涨停股票空列表"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source
        mock_source.get_limit_ups.return_value = []

        result = fetcher.get_today_limit_ups()

        assert result == []
        mock_source.get_limit_ups.assert_called_once()

    def test_implements_iquote_fetcher_interface(self, fetcher):
        """测试实现IQuoteFetcher接口"""
        from backend.market.interfaces import IQuoteFetcher
        assert isinstance(fetcher, IQuoteFetcher)
