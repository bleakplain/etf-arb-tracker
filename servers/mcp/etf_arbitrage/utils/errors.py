"""
Error handling utilities for ETF Arbitrage MCP Server.
"""

from typing import Optional


class MCPError(Exception):
    """Base exception for MCP server errors."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.suggestion:
            return f"{self.message}. Suggestion: {self.suggestion}"
        return self.message


class ValidationError(MCPError):
    """Raised when input validation fails."""


class NotFoundError(MCPError):
    """Raised when a resource is not found."""


class RateLimitError(MCPError):
    """Raised when rate limit is exceeded."""


class APIError(MCPError):
    """Raised when an API call fails."""


class TradingHoursError(MCPError):
    """Raised when operation is not allowed outside trading hours."""


def format_error(error: Exception) -> str:
    """Format an exception into a user-friendly error message.

    Args:
        error: The exception to format

    Returns:
        str: Formatted error message with suggestions
    """
    if isinstance(error, MCPError):
        return f"Error: {error.message}"

    # Handle common exception types
    error_messages = {
        ValueError: "Invalid input value",
        TypeError: "Invalid input type",
        KeyError: "Missing required field",
        AttributeError: "Invalid attribute access",
        ConnectionError: "Connection failed",
        TimeoutError: "Request timed out",
    }

    error_type = type(error)
    if error_type in error_messages:
        return f"Error: {error_messages[error_type]} - {str(error)}"

    # Generic error
    return f"Error: {str(error)}"


# Error response templates
ERROR_TEMPLATES = {
    "stock_not_found": {
        "message": "Stock '{code}' not found",
        "suggestion": "Verify the stock code is correct and the stock is actively trading"
    },
    "etf_not_found": {
        "message": "ETF '{code}' not found",
        "suggestion": "Verify the ETF code is correct and the ETF is actively trading"
    },
    "no_related_etfs": {
        "message": "No ETFs found holding stock '{code}' above weight threshold",
        "suggestion": "Try lowering the min_weight parameter (current: {weight})"
    },
    "signal_not_found": {
        "message": "Signal '{signal_id}' not found",
        "suggestion": "Check the signal ID is correct"
    },
    "backtest_not_found": {
        "message": "Backtest job '{job_id}' not found",
        "suggestion": "Check the job ID is correct"
    },
    "invalid_date_range": {
        "message": "Invalid date range: start_date '{start}' is after end_date '{end}'",
        "suggestion": "Ensure start_date is before end_date"
    },
    "monitor_not_running": {
        "message": "Monitor is not currently running",
        "suggestion": "Use etf_arbitrage_start_monitor to start monitoring"
    },
    "monitor_already_running": {
        "message": "Monitor is already running",
        "suggestion": "Use etf_arbitrage_stop_monitor first, or check status with etf_arbitrage_get_monitor_status"
    },
}


def get_error_response(error_type: str, **kwargs) -> str:
    """Get a formatted error response from a template.

    Args:
        error_type: Type of error from ERROR_TEMPLATES
        **kwargs: Values to substitute in the template

    Returns:
        str: Formatted error message
    """
    if error_type not in ERROR_TEMPLATES:
        return f"Error: {error_type}"

    template = ERROR_TEMPLATES[error_type]
    message = template["message"].format(**kwargs)
    suggestion = template.get("suggestion", "").format(**kwargs)

    if suggestion:
        return f"Error: {message}. Suggestion: {suggestion}"
    return f"Error: {message}"
