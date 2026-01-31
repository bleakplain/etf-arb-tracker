"""
工具模块
提供通用的辅助函数和常量
"""

from backend.utils.code_utils import normalize_stock_code, add_market_prefix
from backend.utils.constants import (
    DEFAULT_MIN_WEIGHT,
    DEFAULT_MIN_TIME_TO_CLOSE,
    DEFAULT_MIN_ETF_VOLUME,
    CacheConfig,
    TradingHours,
    DataSourceLimits,
    APIConfig,
    BacktestConfig,
    HoldingConfig,
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

__all__ = [
    'normalize_stock_code',
    'add_market_prefix',
    'DEFAULT_MIN_WEIGHT',
    'DEFAULT_MIN_TIME_TO_CLOSE',
    'DEFAULT_MIN_ETF_VOLUME',
    'CacheConfig',
    'TradingHours',
    'DataSourceLimits',
    'APIConfig',
    'BacktestConfig',
    'HoldingConfig',
    'RiskControl',
    'SignalEvaluation',
    'now_china',
    'now_china_str',
    'today_china',
    'today_china_compact',
    'timestamp_now',
    'is_trading_time',
    'time_to_close',
]
