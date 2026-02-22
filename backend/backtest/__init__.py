"""
回测模块

提供 A股/港股/美股的回测引擎。
"""

# 通用配置
from .config import BacktestConfig

# A股回测
from .cn import CNBacktestEngine, create_cn_backtest_engine

# 港股回测
from .hk import HKBacktestEngine

# 美股回测
from .us import USBacktestEngine

__all__ = [
    "BacktestConfig",
    "CNBacktestEngine",
    "create_cn_backtest_engine",
    "HKBacktestEngine",
    "USBacktestEngine",
]
