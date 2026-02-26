"""
Pydantic request models for ETF Arbitrage MCP Server.

All input models use Pydantic for validation with proper constraints,
descriptions, and example values.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .enums import (
    ResponseFormat,
    MarketType,
    EventDetectorType,
    FundSelectorType,
    SignalFilterType,
    TimeGranularity,
)


# ============================================================================
# Base Models
# ============================================================================

class BaseRequest(BaseModel):
    """Base request model with common configuration."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )


class PaginatedRequest(BaseRequest):
    """Base model for paginated requests."""
    limit: int = Field(
        default=20,
        description="Maximum number of results to return",
        ge=1,
        le=100
    )
    offset: int = Field(
        default=0,
        description="Number of results to skip for pagination",
        ge=0
    )


class FormattedRequest(BaseRequest):
    """Base model for requests with response format option."""
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


# ============================================================================
# Market Data Requests
# ============================================================================

class GetStockQuoteRequest(FormattedRequest):
    """Request to get stock quotes."""
    codes: List[str] = Field(
        ...,
        description="List of stock codes (6 digits each, e.g., ['600519', '000001'])",
        min_length=1,
        max_length=100
    )

    @field_validator('codes')
    @classmethod
    def validate_codes(cls, v: List[str]) -> List[str]:
        """Validate stock codes are 6 digits."""
        for code in v:
            if not code.isdigit() or len(code) != 6:
                raise ValueError(f"Invalid stock code '{code}': must be 6 digits")
        return v


class GetETFQuoteRequest(FormattedRequest):
    """Request to get ETF quotes."""
    codes: List[str] = Field(
        ...,
        description="List of ETF codes (6 digits each, e.g., ['510300', '159915'])",
        min_length=1,
        max_length=100
    )

    @field_validator('codes')
    @classmethod
    def validate_codes(cls, v: List[str]) -> List[str]:
        """Validate ETF codes are 6 digits."""
        for code in v:
            if not code.isdigit() or len(code) != 6:
                raise ValueError(f"Invalid ETF code '{code}': must be 6 digits")
        return v


class ListLimitUpStocksRequest(PaginatedRequest, FormattedRequest):
    """Request to list today's limit-up stocks."""
    min_change_pct: Optional[float] = Field(
        default=None,
        description="Minimum change percentage to filter (e.g., 9.5 for near limit-up)",
        ge=0,
        le=20
    )


# ============================================================================
# Arbitrage Analysis Requests
# ============================================================================

class FindRelatedETFsRequest(FormattedRequest):
    """Request to find ETFs that hold a specific stock."""
    stock_code: str = Field(
        ...,
        description="Stock code (6 digits, e.g., '600519')",
        min_length=6,
        max_length=6
    )
    min_weight: float = Field(
        default=0.05,
        description="Minimum weight threshold (e.g., 0.05 for 5%)",
        ge=0.01,
        le=1.0
    )

    @field_validator('stock_code')
    @classmethod
    def validate_stock_code(cls, v: str) -> str:
        """Validate stock code is 6 digits."""
        if not v.isdigit():
            raise ValueError("Stock code must be 6 digits")
        return v


class AnalyzeOpportunityRequest(FormattedRequest):
    """Request to analyze arbitrage opportunity for a stock."""
    stock_code: str = Field(
        ...,
        description="Stock code (6 digits, e.g., '600519')",
        min_length=6,
        max_length=6
    )
    include_signals: bool = Field(
        default=True,
        description="Whether to include recent signals in analysis"
    )

    @field_validator('stock_code')
    @classmethod
    def validate_stock_code(cls, v: str) -> str:
        """Validate stock code is 6 digits."""
        if not v.isdigit():
            raise ValueError("Stock code must be 6 digits")
        return v


# ============================================================================
# Signal Management Requests
# ============================================================================

class ListSignalsRequest(PaginatedRequest, FormattedRequest):
    """Request to list historical signals."""
    start_date: Optional[str] = Field(
        default=None,
        description="Start date in YYYY-MM-DD format (e.g., '2024-01-01')",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    end_date: Optional[str] = Field(
        default=None,
        description="End date in YYYY-MM-DD format (e.g., '2024-12-31')",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    stock_code: Optional[str] = Field(
        default=None,
        description="Filter by stock code (6 digits)",
        min_length=6,
        max_length=6
    )


class GetSignalRequest(FormattedRequest):
    """Request to get signal details."""
    signal_id: str = Field(
        ...,
        description="Signal ID (UUID format)",
        min_length=1
    )


# ============================================================================
# Backtest Requests
# ============================================================================

class RunBacktestRequest(FormattedRequest):
    """Request to run a backtest."""
    start_date: str = Field(
        ...,
        description="Start date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    end_date: str = Field(
        ...,
        description="End date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    event_detector: EventDetectorType = Field(
        default=EventDetectorType.LIMIT_UP_CN,
        description="Event detector strategy to use"
    )
    fund_selector: FundSelectorType = Field(
        default=FundSelectorType.HIGHEST_WEIGHT,
        description="Fund selector strategy to use"
    )
    signal_filters: List[SignalFilterType] = Field(
        default_factory=lambda: [SignalFilterType.TIME_FILTER_CN, SignalFilterType.LIQUIDITY_FILTER],
        description="Signal filters to apply"
    )
    granularity: TimeGranularity = Field(
        default=TimeGranularity.DAILY,
        description="Time granularity for backtesting"
    )


class GetBacktestResultRequest(FormattedRequest):
    """Request to get backtest results."""
    job_id: str = Field(
        ...,
        description="Backtest job ID (UUID format)",
        min_length=1
    )


class ListBacktestsRequest(PaginatedRequest, FormattedRequest):
    """Request to list backtest jobs."""
    status: Optional[str] = Field(
        default=None,
        description="Filter by status (pending, running, completed, failed)"
    )


# ============================================================================
# Configuration Requests
# ============================================================================

class GetStockETFMappingRequest(FormattedRequest):
    """Request to get stock-ETF mapping."""
    stock_code: Optional[str] = Field(
        default=None,
        description="Filter by specific stock code (6 digits)",
        min_length=6,
        max_length=6
    )
    include_weights: bool = Field(
        default=True,
        description="Whether to include weight information"
    )


class ListWatchlistRequest(FormattedRequest):
    """Request to list watchlist stocks."""
    pass


class AddWatchlistStockRequest(BaseRequest):
    """Request to add a stock to watchlist."""
    code: str = Field(
        ...,
        description="Stock code (6 digits)",
        min_length=6,
        max_length=6
    )
    name: str = Field(
        ...,
        description="Stock name",
        min_length=1,
        max_length=50
    )
    market: MarketType = Field(
        ...,
        description="Market type (sh, sz, or bj)"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes about this stock",
        max_length=200
    )

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate stock code is 6 digits."""
        if not v.isdigit():
            raise ValueError("Stock code must be 6 digits")
        return v


class RemoveWatchlistStockRequest(BaseRequest):
    """Request to remove a stock from watchlist."""
    code: str = Field(
        ...,
        description="Stock code (6 digits)",
        min_length=6,
        max_length=6
    )

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate stock code is 6 digits."""
        if not v.isdigit():
            raise ValueError("Stock code must be 6 digits")
        return v
