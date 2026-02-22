"""
回测模块 - 按市场拆分的回测引擎

通用组件 + 各市场特定实现
"""

# 通用组件
from .clock import TimeGranularity, SimulationClock
from .config import BacktestConfig
from .metrics import SignalStatistics, BacktestResult
from .data_loader import HistoricalDataLoader
from .holdings_snapshot import HoldingsSnapshotManager
from .signal_recorder import SignalRecorder
from .repository import BacktestRepository, get_backtest_repository

# A股回测
from .cn import CNBacktestEngine, create_cn_backtest_engine

__all__ = [
    # 通用
    "TimeGranularity",
    "SimulationClock",
    "BacktestConfig",
    "SignalStatistics",
    "BacktestResult",
    "HistoricalDataLoader",
    "HoldingsSnapshotManager",
    "SignalRecorder",
    "BacktestRepository",
    "get_backtest_repository",
    # A股
    "CNBacktestEngine",
    "create_cn_backtest_engine",
]
