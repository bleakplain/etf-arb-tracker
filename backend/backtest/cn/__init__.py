"""A股回测模块（简化版）"""

from .engine import CNBacktestEngine, create_cn_backtest_engine
from .data_provider import BacktestDataProvider

__all__ = [
    'CNBacktestEngine',
    'create_cn_backtest_engine',
    'BacktestDataProvider',
]
