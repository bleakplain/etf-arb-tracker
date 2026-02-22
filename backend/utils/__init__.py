"""
工具模块

提供通用的辅助函数、常量和基础设施组件。
"""

from backend.utils.code_utils import normalize_stock_code, add_market_prefix
from backend.utils.constants import (
    DEFAULT_MIN_WEIGHT,
    DEFAULT_MIN_TIME_TO_CLOSE,
    DEFAULT_MIN_ETF_VOLUME,
    CacheConfig,
    DataSourceLimits,
    APIConfig,
    BacktestConfig,
    ETFHoldingConfig,
    RiskControl,
    SignalEvaluation,
)
from backend.utils.time_utils import (
    now_china,
    now_china_str,
    today_china,
    today_china_compact,
    timestamp_now,
    is_trading_time,
    time_to_close,
)
from backend.utils.plugin_registry import PluginRegistry

__all__ = [
    # 代码工具
    'normalize_stock_code',
    'add_market_prefix',
    # 常量
    'DEFAULT_MIN_WEIGHT',
    'DEFAULT_MIN_TIME_TO_CLOSE',
    'DEFAULT_MIN_ETF_VOLUME',
    'CacheConfig',
    'DataSourceLimits',
    'APIConfig',
    'BacktestConfig',
    'ETFHoldingConfig',
    'RiskControl',
    'SignalEvaluation',
    # 时间工具
    'now_china',
    'now_china_str',
    'today_china',
    'today_china_compact',
    'timestamp_now',
    'is_trading_time',
    'time_to_close',
    # 基础设施
    'PluginRegistry',
]
