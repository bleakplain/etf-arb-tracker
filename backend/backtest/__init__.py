"""
回测模块 - A股回测引擎
"""

# 通用配置
from .config import BacktestConfig

# A股回测
from .cn import CNBacktestEngine, create_cn_backtest_engine

__all__ = [
    "BacktestConfig",
    "CNBacktestEngine",
    "create_cn_backtest_engine",
]
