"""市场模块 - 按市场拆分的行情数据"""

# 通用接口和模型
from backend.market.events import MarketEvent
from backend.market.interfaces import IQuoteFetcher, IETFHoldingProvider
from backend.market.models import (
    ETFCategory, StockQuote, ETFQuote, ETFHolding,
    CandidateETF, ETF, TradingPeriod
)

# A股
from backend.market.cn import (
    LimitUpEvent, LimitUpStock, CNQuoteFetcher,
    CNETFQuoteFetcher, CNETFHoldingProvider
)

# 港股
from backend.market.hk import BreakoutEvent, HKQuoteFetcher

# 美股
from backend.market.us import MomentumEvent, USQuoteFetcher

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
    'CNQuoteFetcher',
    'CNETFQuoteFetcher',
    'CNETFHoldingProvider',
    # 港股
    'BreakoutEvent',
    'HKQuoteFetcher',
    # 美股
    'MomentumEvent',
    'USQuoteFetcher',
]
