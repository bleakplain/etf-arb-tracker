"""套利模块 - A股套利业务逻辑"""

# 核心模型
from backend.arbitrage.models import TradingSignal, ChosenETF

# 配置
from backend.arbitrage.config import ArbitrageEngineConfig

# 策略接口
from backend.arbitrage.cn.strategies.interfaces import (
    IEventDetector,
    IFundSelector,
    ISignalFilter,
)

# 事件类型
from backend.market.events import MarketEvent
from backend.market.cn.events import LimitUpEvent

# A股套利引擎
from backend.arbitrage.cn import ArbitrageEngineCN

# 向后兼容：默认使用A股引擎
ArbitrageEngine = ArbitrageEngineCN

__all__ = [
    # 核心模型
    'TradingSignal',
    'ChosenETF',
    'ArbitrageEngineConfig',
    # 策略接口
    'IEventDetector',
    'IFundSelector',
    'ISignalFilter',
    # 事件类型
    'MarketEvent',
    'LimitUpEvent',
    # 市场引擎
    'ArbitrageEngineCN',
    'ArbitrageEngine',  # 向后兼容，默认A股
]
