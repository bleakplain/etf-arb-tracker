"""A股回测模块"""

from .engine import CNBacktestEngine, create_cn_backtest_engine
from .adapters import ETFReference, HistoricalQuoteFetcherAdapter, HistoricalHoldingProviderAdapter

__all__ = [
    'CNBacktestEngine',
    'create_cn_backtest_engine',
    'ETFReference',
    'HistoricalQuoteFetcherAdapter',
    'HistoricalHoldingProviderAdapter',
]
