"""
Unit tests for CNETFQuoteFetcher

Tests the ETF quote fetcher for A-share market.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.market.cn.etf_quote import CNETFQuoteFetcher


@pytest.mark.unit
class TestCNETFQuoteFetcher:
    """测试A股ETF行情获取器"""

    @pytest.fixture
    def fetcher(self):
        return CNETFQuoteFetcher()

    def test_init(self, fetcher):
        """测试初始化"""
        assert fetcher._source is None

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_source_lazy_initialization(self, mock_tencent_class, fetcher):
        """测试数据源延迟初始化"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        # 第一次调用应该初始化
        source1 = fetcher._get_source()
        assert source1 == mock_source
        mock_tencent_class.assert_called_once()

        # 第二次调用应该返回缓存的实例
        source2 = fetcher._get_source()
        assert source2 == source1
        assert mock_tencent_class.call_count == 1

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_etf_quote(self, mock_tencent_class, fetcher):
        """测试获取ETF行情"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        expected_quote = {
            'code': '510300',
            'name': '沪深300ETF',
            'price': 4.5,
            'change_pct': 1.2,
            'amount': 100000000
        }
        mock_source.get_etf_quote.return_value = expected_quote

        result = fetcher.get_etf_quote('510300')

        assert result == expected_quote
        mock_source.get_etf_quote.assert_called_once_with('510300')

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_etf_quote_none(self, mock_tencent_class, fetcher):
        """测试获取不存在的ETF行情"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source
        mock_source.get_etf_quote.return_value = None

        result = fetcher.get_etf_quote('999999')

        assert result is None
        mock_source.get_etf_quote.assert_called_once_with('999999')

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_etf_batch_quotes(self, mock_tencent_class, fetcher):
        """测试批量获取ETF行情"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        expected_quotes = {
            '510300': {'code': '510300', 'name': '沪深300ETF', 'price': 4.5},
            '510500': {'code': '510500', 'name': '中证500ETF', 'price': 7.2},
        }
        mock_source.get_etf_batch_quotes.return_value = expected_quotes

        codes = ['510300', '510500']
        result = fetcher.get_etf_batch_quotes(codes)

        assert result == expected_quotes
        mock_source.get_etf_batch_quotes.assert_called_once_with(codes)

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_etf_batch_quotes_empty(self, mock_tencent_class, fetcher):
        """测试批量获取空列表"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source
        mock_source.get_etf_batch_quotes.return_value = {}

        result = fetcher.get_etf_batch_quotes([])

        assert result == {}
        mock_source.get_etf_batch_quotes.assert_called_once_with([])

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_check_liquidity_sufficient(self, mock_tencent_class, fetcher):
        """测试流动性充足"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        # 模拟成交额1亿元，超过默认阈值5000万/4=1250万
        mock_source.get_etf_quote.return_value = {
            'code': '510300',
            'amount': 100000000  # 1亿
        }

        result = fetcher.check_liquidity('510300', min_amount=50000000)

        assert result is True

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_check_liquidity_insufficient(self, mock_tencent_class, fetcher):
        """测试流动性不足"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        # 模拟成交额1000万，低于阈值5000万/4=1250万
        mock_source.get_etf_quote.return_value = {
            'code': '510300',
            'amount': 10000000  # 1000万
        }

        result = fetcher.check_liquidity('510300', min_amount=50000000)

        assert result is False

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_check_liquidity_no_quote(self, mock_tencent_class, fetcher):
        """测试无行情数据时流动性检查失败"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source
        mock_source.get_etf_quote.return_value = None

        result = fetcher.check_liquidity('999999')

        assert result is False

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_check_liquidity_no_amount_field(self, mock_tencent_class, fetcher):
        """测试行情数据缺少amount字段"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        # 模拟行情数据没有amount字段
        mock_source.get_etf_quote.return_value = {
            'code': '510300',
            'price': 4.5
            # 缺少amount字段
        }

        result = fetcher.check_liquidity('510300')

        assert result is False

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_check_liquidity_custom_threshold(self, mock_tencent_class, fetcher):
        """测试自定义流动性阈值"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        # 使用自定义阈值1亿，成交额2000万（低于2500万阈值）
        mock_source.get_etf_quote.return_value = {
            'code': '510300',
            'amount': 20000000  # 2000万 < 1亿/4=2500万
        }

        result = fetcher.check_liquidity('510300', min_amount=100000000)

        assert result is False

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_check_liquidity_exactly_threshold(self, mock_tencent_class, fetcher):
        """测试流动性刚好等于阈值"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        # 成交额刚好等于阈值
        mock_source.get_etf_quote.return_value = {
            'code': '510300',
            'amount': 12500000  # 5000万/4 = 1250万
        }

        result = fetcher.check_liquidity('510300', min_amount=50000000)

        assert result is True
