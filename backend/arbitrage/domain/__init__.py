"""套利领域模块"""

from backend.arbitrage.domain.models import TradingSignal, ChosenETF
from backend.arbitrage.domain.interfaces import (
    IEventDetectorStrategy,
    IFundSelectionStrategy,
    ISignalFilterStrategy,
    StrategyChainConfig,
    EventInfo,
)

__all__ = [
    'TradingSignal',
    'ChosenETF',
    'IEventDetectorStrategy',
    'IFundSelectionStrategy',
    'ISignalFilterStrategy',
    'StrategyChainConfig',
    'EventInfo',
]
