"""
套利引擎包

包含套利策略的核心执行引擎：
- ArbitrageEngine: 主引擎，使用策略链处理套利机会
- StrategyExecutor: 策略链执行器
"""

from backend.arbitrage.strategy_registry import strategy_manager

__all__ = [
    'ArbitrageEngine',
    'StrategyExecutor',
    'strategy_manager',
]
