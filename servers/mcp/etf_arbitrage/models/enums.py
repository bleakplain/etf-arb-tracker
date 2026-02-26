"""
Enumerations for ETF Arbitrage MCP Server.
"""

from enum import Enum


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class MarketType(str, Enum):
    """Market type for securities."""
    SH = "sh"  # Shanghai Stock Exchange
    SZ = "sz"  # Shenzhen Stock Exchange
    BJ = "bj"  # Beijing Stock Exchange


class EventDetectorType(str, Enum):
    """Event detector types for backtesting."""
    LIMIT_UP_CN = "limit_up_cn"


class FundSelectorType(str, Enum):
    """Fund selector strategies."""
    HIGHEST_WEIGHT = "highest_weight"
    BEST_LIQUIDITY = "best_liquidity"
    LOWEST_PREMIUM = "lowest_premium"
    BALANCED = "balanced"


class SignalFilterType(str, Enum):
    """Signal filter types."""
    TIME_FILTER_CN = "time_filter_cn"
    LIQUIDITY_FILTER = "liquidity_filter"
    CONFIDENCE_FILTER = "confidence_filter"
    RISK_FILTER = "risk_filter"


class BacktestStatus(str, Enum):
    """Backtest job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TimeGranularity(str, Enum):
    """Time granularity for backtesting."""
    DAILY = "daily"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
