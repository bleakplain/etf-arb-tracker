"""
Factory for creating ArbitrageEngineCN instances

Provides convenient methods for creating engine instances for different scenarios.
"""

from typing import List, Optional, Dict
from unittest.mock import Mock

from backend.arbitrage.cn import ArbitrageEngineCN
from backend.arbitrage.config import ArbitrageEngineConfig
from backend.arbitrage.interfaces import InMemoryMappingRepository
from backend.arbitrage.strategy_registry import StrategyManager, create_test_strategy_manager
from backend.market.interfaces import IQuoteFetcher, IETFHoldingProvider
from backend.signal.interfaces import ISignalEvaluator
from config import Config


class ArbitrageEngineFactory:
    """
    套利引擎工厂

    提供创建引擎实例的便捷方法
    """

    @staticmethod
    def create_engine(
        quote_fetcher: IQuoteFetcher,
        etf_holder_provider: IETFHoldingProvider,
        etf_holdings_provider: IETFHoldingProvider,
        etf_quote_provider: IQuoteFetcher,
        watch_securities: List[str] = None,
        engine_config: ArbitrageEngineConfig = None,
        signal_evaluator: ISignalEvaluator = None,
        config: Config = None
    ) -> ArbitrageEngineCN:
        """
        创建标准套利引擎实例

        Args:
            quote_fetcher: 行情数据获取器
            etf_holder_provider: ETF持仓关系提供者
            etf_holdings_provider: ETF持仓详情提供者
            etf_quote_provider: ETF行情提供者
            watch_securities: 监控的证券代码列表
            engine_config: 套利引擎配置
            signal_evaluator: 信号评估器
            config: 应用配置

        Returns:
            ArbitrageEngineCN 实例
        """
        return ArbitrageEngineCN(
            quote_fetcher=quote_fetcher,
            etf_holder_provider=etf_holder_provider,
            etf_holdings_provider=etf_holdings_provider,
            etf_quote_provider=etf_quote_provider,
            watch_securities=watch_securities,
            engine_config=engine_config,
            signal_evaluator=signal_evaluator,
            config=config
        )

    @staticmethod
    def create_test_engine(
        watch_securities: List[str] = None,
        use_mock_providers: bool = True,
        engine_config: ArbitrageEngineConfig = None,
        predefined_mapping: Dict[str, List[Dict]] = None
    ) -> ArbitrageEngineCN:
        """
        创建测试用套利引擎实例

        使用模拟提供者和内存仓储，避免外部依赖

        Args:
            watch_securities: 监控的证券代码列表
            use_mock_providers: 是否使用模拟提供者
            engine_config: 套利引擎配置
            predefined_mapping: 预定义的股票-ETF映射

        Returns:
            ArbitrageEngineCN 实例
        """
        # 创建模拟提供者
        if use_mock_providers:
            quote_fetcher = ArbitrageEngineFactory._create_mock_quote_fetcher()
            etf_holder_provider = ArbitrageEngineFactory._create_mock_etf_holder_provider(predefined_mapping)
            etf_holdings_provider = ArbitrageEngineFactory._create_mock_etf_holdings_provider()
            etf_quote_provider = ArbitrageEngineFactory._create_mock_etf_quote_provider()
        else:
            raise NotImplementedError("Custom providers not yet supported")

        # 创建测试专用的策略管理器和仓储
        strategy_manager = create_test_strategy_manager()
        mapping_repository = InMemoryMappingRepository()

        # 如果有预定义映射，直接设置
        if predefined_mapping:
            mapping_repository.save_mapping(predefined_mapping)

        # 创建引擎（内部使用）
        engine = ArbitrageEngineCN(
            quote_fetcher=quote_fetcher,
            etf_holder_provider=etf_holder_provider,
            etf_holdings_provider=etf_holdings_provider,
            etf_quote_provider=etf_quote_provider,
            watch_securities=watch_securities or ['600519', '300750'],
            engine_config=engine_config or ArbitrageEngineFactory._get_default_test_config(),
            signal_evaluator=None,
            config=None,
            strategy_manager_instance=strategy_manager,
            mapping_repository=mapping_repository
        )

        return engine

    @staticmethod
    def _create_mock_quote_fetcher() -> IQuoteFetcher:
        """创建模拟行情获取器"""
        fetcher = Mock()

        fetcher.get_stock_quote.side_effect = lambda code: {
            '600519': {
                'code': '600519',
                'name': '贵州茅台',
                'price': 1800.0,
                'change_pct': 0.1001,
                'is_limit_up': True,
                'timestamp': '14:00:00',
                'volume': 1000000,
                'amount': 1800000000
            },
            '300750': {
                'code': '300750',
                'name': '宁德时代',
                'price': 256.80,
                'change_pct': 0.2001,
                'is_limit_up': True,
                'timestamp': '13:30:00',
                'volume': 5000000,
                'amount': 1284000000
            }
        }.get(code)

        fetcher.get_batch_quotes.side_effect = lambda codes: {
            c: fetcher.get_stock_quote(c) for c in codes
        }

        fetcher.is_trading_time.return_value = True

        return fetcher

    @staticmethod
    def _create_mock_etf_holder_provider(predefined_mapping: Dict = None) -> IETFHoldingProvider:
        """创建模拟ETF持仓关系提供者"""
        provider = Mock()

        mapping = predefined_mapping or {
            '600519': [
                {'etf_code': '510300', 'etf_name': '沪深300ETF'},
                {'etf_code': '510500', 'etf_name': '中证500ETF'},
            ],
            '300750': [
                {'etf_code': '516160', 'etf_name': '新能源车ETF'},
            ]
        }

        provider.load_mapping.return_value = mapping
        provider.build_stock_etf_mapping.return_value = mapping

        return provider

    @staticmethod
    def _create_mock_etf_holdings_provider() -> IETFHoldingProvider:
        """创建模拟ETF持仓详情提供者"""
        provider = Mock()

        holdings_map = {
            '510300': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.08},
                {'stock_code': '600036', 'stock_name': '招商银行', 'weight': 0.05},
            ],
            '510500': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.04},
            ],
            '516160': [
                {'stock_code': '300750', 'stock_name': '宁德时代', 'weight': 0.085},
            ]
        }

        def get_holdings(etf_code):
            holdings = holdings_map.get(etf_code, [])
            return {
                'etf_code': etf_code,
                'etf_name': f'ETF_{etf_code}',
                'top_holdings': holdings,
                'total_weight': sum(h['weight'] for h in holdings)
            }

        provider.get_etf_top_holdings.side_effect = get_holdings

        return provider

    @staticmethod
    def _create_mock_etf_quote_provider() -> IQuoteFetcher:
        """创建模拟ETF行情提供者"""
        provider = Mock()

        quotes = {
            '510300': {
                'code': '510300',
                'name': '沪深300ETF',
                'price': 4.567,
                'change_pct': 1.2,
                'premium': 0.5,
                'volume': 100000000,
                'amount': 456700000
            },
            '510500': {
                'code': '510500',
                'name': '中证500ETF',
                'price': 7.123,
                'change_pct': 0.8,
                'premium': -0.3,
                'volume': 80000000,
                'amount': 569840000
            },
            '516160': {
                'code': '516160',
                'name': '新能源车ETF',
                'price': 1.234,
                'change_pct': 2.5,
                'premium': 1.2,
                'volume': 50000000,
                'amount': 61700000
            }
        }

        provider.get_etf_quote.side_effect = lambda code: quotes.get(code)
        provider.get_etf_batch_quotes.side_effect = lambda codes: {
            c: quotes.get(c) for c in codes
        }
        provider.check_liquidity.return_value = True

        return provider

    @staticmethod
    def _get_default_test_config() -> ArbitrageEngineConfig:
        """获取默认测试配置"""
        from backend.utils.constants import CNMarketConstants

        return ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight",
            signal_filters=[],  # 测试时不使用过滤器
            event_config={'min_change_pct': CNMarketConstants.DEFAULT_LIMIT_UP_THRESHOLD},
            fund_config={'min_weight': CNMarketConstants.DEFAULT_MIN_WEIGHT}
        )
