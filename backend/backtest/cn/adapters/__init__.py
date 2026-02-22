"""回测适配器模块"""

from .models import ETFReference
from .quote_fetcher import HistoricalQuoteFetcherAdapter
from .holding_provider import HistoricalHoldingProviderAdapter

__all__ = [
    'ETFReference',
    'HistoricalQuoteFetcherAdapter',
    'HistoricalHoldingProviderAdapter',
]
