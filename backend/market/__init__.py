"""市场模块 - A股行情数据"""

# 通用接口和模型
from backend.market.events import MarketEvent
from backend.market.interfaces import IQuoteFetcher, IETFHoldingProvider
from backend.market.models import (
    ETFCategory, StockQuote, ETFQuote, ETFHolding,
    CandidateETF, ETF, TradingPeriod
)

# A股
from backend.market.cn import (
    LimitUpEvent, LimitUpStock, CNStockQuoteProvider,
    CNETFQuoteProvider, CNETFHoldingProvider
)

__all__ = [
    # 通用
    'MarketEvent',
    'IQuoteFetcher',
    'IETFHoldingProvider',
    'ETFCategory',
    'StockQuote',
    'ETFQuote',
    'ETFHolding',
    'CandidateETF',
    'ETF',
    'TradingPeriod',
    # A股
    'LimitUpEvent',
    'LimitUpStock',
    'CNStockQuoteProvider',
    'CNETFQuoteProvider',
    'CNETFHoldingProvider',
]
