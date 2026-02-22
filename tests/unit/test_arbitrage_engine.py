"""
Unit tests for ArbitrageEngineCN

Tests the arbitrage engine with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, patch

from backend.arbitrage.cn import ArbitrageEngineCN
from backend.arbitrage.config import ArbitrageEngineConfig
from backend.arbitrage.interfaces import InMemoryMappingRepository
from tests.fixtures.mocks import (
    MockQuoteFetcher,
    MockETFHolderProvider,
    MockETFHoldingsProvider,
    MockETFQuoteProvider,
    MockSignalEvaluator,
)


@pytest.mark.unit
class TestArbitrageEngineCN:
    """测试ArbitrageEngineCN"""

    @pytest.fixture
    def mock_providers(self):
        """创建模拟提供者"""
        return {
            'quote_fetcher': MockQuoteFetcher(),
            'etf_holder_provider': MockETFHolderProvider(),
            'etf_holdings_provider': MockETFHoldingsProvider(),
            'etf_quote_provider': MockETFQuoteProvider(),
        }

    @pytest.fixture
    def engine_config(self):
        """创建引擎配置"""
        return ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight",
            signal_filters=[],  # 不使用过滤器
            event_config={'min_change_pct': 0.095},
            fund_config={'min_weight': 0.05}
        )

    @pytest.fixture
    def mock_mapping_repository(self):
        """创建模拟映射仓储"""
        return InMemoryMappingRepository()

    def test_engine_initialization(self, mock_providers, engine_config, mock_mapping_repository):
        """测试引擎初始化"""
        engine = ArbitrageEngineCN(
            quote_fetcher=mock_providers['quote_fetcher'],
            etf_holder_provider=mock_providers['etf_holder_provider'],
            etf_holdings_provider=mock_providers['etf_holdings_provider'],
            etf_quote_provider=mock_providers['etf_quote_provider'],
            watch_securities=['600519', '300750'],
            engine_config=engine_config,
            mapping_repository=mock_mapping_repository,
        )

        assert engine is not None
        assert len(engine._watch_securities) == 2

    def test_scan_security_with_limit_up(self, mock_providers, engine_config, mock_mapping_repository):
        """测试扫描涨停股票"""
        engine = ArbitrageEngineCN(
            quote_fetcher=mock_providers['quote_fetcher'],
            etf_holder_provider=mock_providers['etf_holder_provider'],
            etf_holdings_provider=mock_providers['etf_holdings_provider'],
            etf_quote_provider=mock_providers['etf_quote_provider'],
            watch_securities=['600519'],
            engine_config=engine_config,
            mapping_repository=mock_mapping_repository,
        )

        signal = engine.scan_security('600519')

        # 600519是涨停股票，应该生成信号
        assert signal is not None
        assert signal.stock_code == '600519'

    def test_scan_security_without_limit_up(self, mock_providers, engine_config, mock_mapping_repository):
        """测试扫描非涨停股票"""
        engine = ArbitrageEngineCN(
            quote_fetcher=mock_providers['quote_fetcher'],
            etf_holder_provider=mock_providers['etf_holder_provider'],
            etf_holdings_provider=mock_providers['etf_holdings_provider'],
            etf_quote_provider=mock_providers['etf_quote_provider'],
            watch_securities=['000001'],
            engine_config=engine_config,
            mapping_repository=mock_mapping_repository,
        )

        signal = engine.scan_security('000001')

        # 000001不是涨停股票，不应该生成信号
        assert signal is None

    def test_scan_all_returns_result(self, mock_providers, engine_config, mock_mapping_repository):
        """测试扫描所有证券"""
        engine = ArbitrageEngineCN(
            quote_fetcher=mock_providers['quote_fetcher'],
            etf_holder_provider=mock_providers['etf_holder_provider'],
            etf_holdings_provider=mock_providers['etf_holdings_provider'],
            etf_quote_provider=mock_providers['etf_quote_provider'],
            watch_securities=['600519', '300750', '000001'],
            engine_config=engine_config,
            mapping_repository=mock_mapping_repository,
        )

        result = engine.scan_all()

        assert result is not None
        assert result.total_scanned == 3
        # 600519和300750是涨停，应该至少生成2个信号
        assert len(result.signals) >= 2

    def test_scan_result_to_dict(self, mock_providers, engine_config, mock_mapping_repository):
        """测试扫描结果转换为字典"""
        engine = ArbitrageEngineCN(
            quote_fetcher=mock_providers['quote_fetcher'],
            etf_holder_provider=mock_providers['etf_holder_provider'],
            etf_holdings_provider=mock_providers['etf_holdings_provider'],
            etf_quote_provider=mock_providers['etf_quote_provider'],
            watch_securities=['600519'],
            engine_config=engine_config,
            mapping_repository=mock_mapping_repository,
        )

        result = engine.scan_all()
        result_dict = result.to_dict()

        assert 'signals' in result_dict
        assert 'total_scanned' in result_dict
        assert 'total_events' in result_dict
        assert result_dict['total_scanned'] == 1

    def test_get_eligible_funds(self, mock_providers, engine_config, mock_mapping_repository):
        """测试获取符合条件的基金"""
        engine = ArbitrageEngineCN(
            quote_fetcher=mock_providers['quote_fetcher'],
            etf_holder_provider=mock_providers['etf_holder_provider'],
            etf_holdings_provider=mock_providers['etf_holdings_provider'],
            etf_quote_provider=mock_providers['etf_quote_provider'],
            watch_securities=['600519'],
            engine_config=engine_config,
            mapping_repository=mock_mapping_repository,
        )

        funds = engine.get_eligible_funds('600519')

        assert len(funds) > 0
        # 检查权重阈值
        for fund in funds:
            assert fund.weight >= 0.05

    def test_with_signal_evaluator(self, mock_providers, engine_config, mock_mapping_repository):
        """测试使用信号评估器"""
        evaluator = MockSignalEvaluator(confidence='高', risk_level='低')

        engine = ArbitrageEngineCN(
            quote_fetcher=mock_providers['quote_fetcher'],
            etf_holder_provider=mock_providers['etf_holder_provider'],
            etf_holdings_provider=mock_providers['etf_holdings_provider'],
            etf_quote_provider=mock_providers['etf_quote_provider'],
            watch_securities=['600519'],
            engine_config=engine_config,
            signal_evaluator=evaluator,
            mapping_repository=mock_mapping_repository,
        )

        signal = engine.scan_security('600519')

        assert signal is not None
        assert signal.confidence == '高'
        assert signal.risk_level == '低'
        # 验证评估器被调用
        assert len(evaluator.evaluate_calls) > 0


@pytest.mark.unit
class TestArbitrageEngineFactory:
    """测试ArbitrageEngineFactory"""

    def test_create_test_engine(self):
        """测试创建测试引擎"""
        from backend.arbitrage.cn.factory import ArbitrageEngineFactory

        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=['600519', '300750']
        )

        assert engine is not None
        assert len(engine._watch_securities) == 2

    def test_create_test_engine_with_predefined_mapping(self):
        """测试使用预定义映射创建测试引擎"""
        from backend.arbitrage.cn.factory import ArbitrageEngineFactory

        mapping = {
            '600519': [
                {'etf_code': '510300', 'etf_name': '沪深300ETF'},
            ]
        }

        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=['600519'],
            predefined_mapping=mapping
        )

        assert engine is not None
        funds = engine.get_eligible_funds('600519')
        assert len(funds) > 0
