"""
回测模块

提供基于历史数据的策略回测功能。

主要组件：
- SimulationClock: 模拟时钟，支持日级别和分钟级别时间推进
- HistoricalDataLoader: 历史数据加载器（支持AKShare和Tushare）
- HistoricalQuoteFetcher: 实现IQuoteFetcher接口的历史数据适配器
- HoldingsSnapshotManager: ETF持仓快照管理器，支持历史权重查询
- SignalRecorder: 信号记录器
- BacktestEngine: 回测引擎核心
- BacktestRepository: 回测结果持久化存储仓库
"""

from .clock import TimeGranularity, SimulationClock
from .metrics import SignalStatistics, BacktestResult
from .engine import BacktestEngine, BacktestConfig, create_backtest_engine
from .signal_recorder import SignalRecorder
from .holdings_snapshot import HoldingsSnapshotManager
from .data_loader import HistoricalDataLoader
from .repository import BacktestRepository, get_backtest_repository

__all__ = [
    "TimeGranularity",
    "SimulationClock",
    "SignalStatistics",
    "BacktestResult",
    "BacktestEngine",
    "BacktestConfig",
    "create_backtest_engine",
    "SignalRecorder",
    "HoldingsSnapshotManager",
    "HistoricalDataLoader",
    "BacktestRepository",
    "get_backtest_repository",
]
