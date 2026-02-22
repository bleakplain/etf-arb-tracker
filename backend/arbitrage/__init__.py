"""套利模块 - 核心业务逻辑

按市场拆分的套利模块：
- cn: A股套利引擎和策略
- hk: 港股套利引擎和策略（框架）
- us: 美股套利引擎和策略（框架）
"""

# 核心模型（跨市场通用）
from backend.arbitrage.models import TradingSignal, ChosenETF

# 配置（跨市场通用）
from backend.arbitrage.config import ArbitrageEngineConfig

# 策略接口（从cn导入）
from backend.arbitrage.cn.strategies.interfaces import (
    IEventDetector,
    IFundSelector,
    ISignalFilter,
)

# 事件类型
from backend.market.domain.events import (
    MarketEvent,
    LimitUpEvent,
    BreakoutEvent,
)

# 各市场引擎
from backend.arbitrage.cn import ArbitrageEngineCN
from backend.arbitrage.hk import ArbitrageEngineHK
from backend.arbitrage.us import USStockArbitrageEngine

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
    'BreakoutEvent',
    # 市场引擎
    'ArbitrageEngineCN',
    'ArbitrageEngineHK',
    'USStockArbitrageEngine',
    'ArbitrageEngine',  # 向后兼容，默认A股
]
