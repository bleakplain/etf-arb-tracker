"""市场模块 - 按市场拆分的行情数据"""

# 通用接口和模型
from backend.market.events import MarketEvent
from backend.market.interfaces import IQuoteFetcher, IHoldingProvider
from backend.market.models import ETFCategory, StockQuote, ETFQuote, Holding

# A股
from backend.market.cn import LimitUpEvent, LimitUpStock, CNQuoteFetcher

# 港股
from backend.market.hk import BreakoutEvent, HKQuoteFetcher

# 美股
from backend.market.us import MomentumEvent, USQuoteFetcher

# 兼容旧导入
from backend.market.domain import ETF, CandidateETF, TradingHours

__all__ = [
    # 通用
    'MarketEvent',
    'IQuoteFetcher',
    'IHoldingProvider',
    'ETFCategory',
    'StockQuote',
    'ETFQuote',
    'Holding',
    # A股
    'LimitUpEvent',
    'LimitUpStock',
    'CNQuoteFetcher',
    # 港股
    'BreakoutEvent',
    'HKQuoteFetcher',
    # 美股
    'MomentumEvent',
    'USQuoteFetcher',
    # 旧导入（兼容）
    'ETF',
    'CandidateETF',
    'TradingHours',
]
