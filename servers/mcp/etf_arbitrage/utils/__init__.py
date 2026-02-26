"""
Utility functions for ETF Arbitrage MCP Server.
"""

from .errors import (
    MCPError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    APIError,
    TradingHoursError,
    format_error,
    get_error_response,
)
from .formatters import (
    ResponseFormatter,
    StockFormatter,
    ETFFormatter,
    SignalFormatter,
    PaginationFormatter,
    format_timestamp,
    format_number,
)

__all__ = [
    # Errors
    "MCPError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "APIError",
    "TradingHoursError",
    "format_error",
    "get_error_response",
    # Formatters
    "ResponseFormatter",
    "StockFormatter",
    "ETFFormatter",
    "SignalFormatter",
    "PaginationFormatter",
    "format_timestamp",
    "format_number",
]
