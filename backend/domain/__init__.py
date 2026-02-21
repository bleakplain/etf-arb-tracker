"""
领域层 - 定义核心业务概念和接口
"""

from .interfaces import (
    IQuoteFetcher,
    IETFHolderProvider,
    IETFHoldingsProvider,
    ISignalRepository,
    ISignalSender
)
from .strategy_interfaces import (
    IEventDetectorStrategy,
    IFundSelectionStrategy,
    ISignalFilterStrategy,
    IStrategyConfig,
    EventInfo,
    StrategyChainConfig
)
from .value_objects import (
    StockQuote,
    ETFReference,
    TradingSignal,
    ConfidenceLevel,
    RiskLevel,
    TradingHours
)
from .models import LimitUpStock

__all__ = [
    # Interfaces
    'IQuoteFetcher',
    'IETFHolderProvider',
    'IETFHoldingsProvider',
    'ISignalRepository',
    'ISignalSender',
    # Strategy Interfaces (新增)
    'IEventDetectorStrategy',
    'IFundSelectionStrategy',
    'ISignalFilterStrategy',
    'IStrategyConfig',
    'EventInfo',
    'StrategyChainConfig',
    # Value Objects
    'StockQuote',
    'ETFReference',
    'TradingSignal',
    'ConfidenceLevel',
    'RiskLevel',
    'TradingHours',
    # Models
    'LimitUpStock',
]

