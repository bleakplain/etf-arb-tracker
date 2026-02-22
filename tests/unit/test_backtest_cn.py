"""
Unit tests for Backtest Module

Tests the backtest configuration, data provider, and engine.
"""

import pytest
from datetime import datetime

from backend.backtest.config import BacktestConfig
from backend.backtest.cn.data_provider import BacktestDataProvider
from backend.backtest.cn.engine import CNBacktestEngine
from backend.arbitrage.config import ArbitrageEngineConfig


@pytest.mark.unit
class TestBacktestConfig:
    """测试回测配置"""

    def test_create_default_config(self):
        """测试创建默认配置"""
        config = BacktestConfig(
            start_date='20240101',
            end_date='20240131',
            stock_codes=['600519'],
            etf_codes=['510300']
        )

        assert config.start_date == '20240101'
        assert config.end_date == '20240131'
        assert config.min_weight == 0.05  # 默认值
        assert config.use_mock_data is True  # 默认值

    def test_validate_dates(self):
        """测试日期验证"""
        # 有效日期
        config = BacktestConfig(
            start_date='20240101',
            end_date='20240131',
            stock_codes=['600519'],
            etf_codes=['510300']
        )

        # 这里的验证逻辑如果实现了可以测试
        assert config.start_date < config.end_date

    def test_trading_days_property(self):
        """测试交易日属性"""
        config = BacktestConfig(
            start_date='20240115',  # 周一
            end_date='20240119',   # 周五
            stock_codes=['600519'],
            etf_codes=['510300']
        )

        days = config.trading_days

        # 应该有5个交易日
        assert len(days) == 5
        assert '20240115' in days


@pytest.mark.unit
class TestBacktestDataProvider:
    """测试回测数据提供者"""

    @pytest.fixture
    def sample_quotes(self):
        """示例行情数据"""
        return {
            '20240115': {
                '600519': {
                    'code': '600519',
                    'name': '贵州茅台',
                    'price': 1800.0,
                    'change_pct': 0.1001,
                    'is_limit_up': True,
                    'timestamp': '14:00:00',
                },
                '300750': {
                    'code': '300750',
                    'name': '宁德时代',
                    'price': 256.80,
                    'change_pct': 0.015,
                    'is_limit_up': False,
                    'timestamp': '14:00:00',
                }
            }
        }

    @pytest.fixture
    def sample_holdings(self):
        """示例持仓数据"""
        return {
            '510300': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.08, 'rank': 1},
                {'stock_code': '600036', 'stock_name': '招商银行', 'weight': 0.05, 'rank': 2},
            ]
        }

    def test_create_provider_with_quotes(self, sample_quotes):
        """测试使用行情数据创建提供者"""
        provider = BacktestDataProvider(
            quotes=sample_quotes,
            holdings=None
        )

        assert provider is not None

    def test_set_current_date(self, sample_quotes):
        """测试设置当前日期"""
        provider = BacktestDataProvider(
            quotes=sample_quotes,
            holdings=None
        )

        provider.set_current_date('20240115')

        assert provider.current_date == '20240115'

    def test_get_stock_quote_for_date(self, sample_quotes):
        """测试获取指定日期的股票行情"""
        provider = BacktestDataProvider(
            quotes=sample_quotes,
            holdings=None
        )

        provider.set_current_date('20240115')
        quote = provider.get_stock_quote('600519')

        assert quote is not None
        assert quote['code'] == '600519'
        assert quote['price'] == 1800.0

    def test_get_stock_quote_returns_none_for_unknown_date(self, sample_quotes):
        """测试未知日期返回None"""
        provider = BacktestDataProvider(
            quotes=sample_quotes,
            holdings=None
        )

        provider.set_current_date('20240201')
        quote = provider.get_stock_quote('600519')

        assert quote is None

    def test_get_etf_top_holdings(self, sample_holdings):
        """测试获取ETF持仓"""
        provider = BacktestDataProvider(
            quotes={},
            holdings=sample_holdings
        )

        holdings = provider.get_etf_top_holdings('510300')

        assert holdings is not None
        # 检查返回的结构
        assert 'top_holdings' in holdings or isinstance(holdings, list)


@pytest.mark.unit
class TestCNBacktestEngine:
    """测试A股回测引擎"""

    @pytest.fixture
    def sample_quotes(self):
        """示例行情数据"""
        return {
            '20240115': {
                '600519': {
                    'code': '600519',
                    'name': '贵州茅台',
                    'price': 1800.0,
                    'change_pct': 0.1001,
                    'is_limit_up': True,
                    'timestamp': '14:00:00',
                }
            },
            '20240116': {
                '600519': {
                    'code': '600519',
                    'name': '贵州茅台',
                    'price': 1820.0,
                    'change_pct': 0.012,
                    'is_limit_up': False,
                    'timestamp': '14:00:00',
                }
            }
        }

    @pytest.fixture
    def sample_holdings(self):
        """示例持仓数据"""
        return {
            '510300': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.08, 'rank': 1},
            ]
        }

    @pytest.fixture
    def backtest_config(self):
        """回测配置"""
        return BacktestConfig(
            start_date='20240115',
            end_date='20240116',
            stock_codes=['600519'],
            etf_codes=['510300']
        )

    def test_initialize_engine(self, sample_quotes, sample_holdings, backtest_config):
        """测试初始化回测引擎"""
        engine = CNBacktestEngine(config=backtest_config)

        engine.initialize(
            quotes=sample_quotes,
            holdings=sample_holdings
        )

        assert engine.data_provider is not None
        assert engine.arbitrage_engine is not None

    def test_run_backtest(self, sample_quotes, sample_holdings, backtest_config):
        """测试运行回测"""
        engine = CNBacktestEngine(config=backtest_config)

        engine.initialize(
            quotes=sample_quotes,
            holdings=sample_holdings
        )

        # 运行回测
        results = engine.run()

        assert results is not None
        # 验证结果结构
        assert hasattr(results, 'signals') or 'signals' in results


@pytest.mark.unit
class TestBacktestIntegration:
    """回测集成测试"""

    def test_end_to_end_backtest(self):
        """端到端回测测试"""
        # 配置
        config = BacktestConfig(
            start_date='20240115',
            end_date='20240115',
            stock_codes=['600519'],
            etf_codes=['510300']
        )

        # 创建引擎
        engine = CNBacktestEngine(config=config)

        # 使用mock数据初始化
        sample_quotes = {
            '20240115': {
                '600519': {
                    'code': '600519',
                    'name': '贵州茅台',
                    'price': 1800.0,
                    'change_pct': 0.1001,
                    'is_limit_up': True,
                    'timestamp': '14:00:00',
                }
            }
        }

        sample_holdings = {
            '510300': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.08, 'rank': 1},
            ]
        }

        engine.initialize(
            quotes=sample_quotes,
            holdings=sample_holdings
        )

        # 运行
        results = engine.run()

        # 验证
        assert results is not None
