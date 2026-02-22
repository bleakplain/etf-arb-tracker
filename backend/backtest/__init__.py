"""
回测模块 - 简化版

只保留核心配置和各市场回测引擎，最大化复用现有模块。
"""

# 通用配置
from .config import BacktestConfig

# A股回测
from .cn import CNBacktestEngine, create_cn_backtest_engine

# 港股回测（框架）
from .hk import HKBacktestEngine

# 美股回测（框架）
from .us import USBacktestEngine

__all__ = [
    "BacktestConfig",
    "CNBacktestEngine",
    "create_cn_backtest_engine",
    "HKBacktestEngine",
    "USBacktestEngine",
]
