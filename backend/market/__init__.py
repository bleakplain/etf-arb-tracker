"""市场模块 - 行情数据（股票、ETF）、涨停检测"""

# 通用导出（临时，保持向后兼容）
from backend.market.events import MarketEvent
from backend.market.interfaces import IQuoteFetcher, IHoldingProvider
from backend.market.models import ETFCategory, StockQuote, ETFQuote, Holding

# 兼容旧导入
from backend.market.domain import (
    LimitUpStock, ETF, CandidateETF, TradingHours, LimitUpEvent
)

__all__ = [
    # 通用
    'MarketEvent',
    'IQuoteFetcher',
    'IHoldingProvider',
    'ETFCategory',
    'StockQuote',
    'ETFQuote',
    'Holding',
    # 旧导入（兼容）
    'LimitUpStock',
    'ETF',
    'CandidateETF',
    'TradingHours',
    'LimitUpEvent',
]
