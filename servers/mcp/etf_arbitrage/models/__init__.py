"""
Pydantic models for ETF Arbitrage MCP Server.
"""

from .enums import (
    ResponseFormat,
    MarketType,
    EventDetectorType,
    FundSelectorType,
    SignalFilterType,
    BacktestStatus,
    TimeGranularity,
)
from .requests import (
    GetStockQuoteRequest,
    GetETFQuoteRequest,
    ListLimitUpStocksRequest,
    FindRelatedETFsRequest,
    AnalyzeOpportunityRequest,
    ListSignalsRequest,
    GetSignalRequest,
    RunBacktestRequest,
    GetBacktestResultRequest,
    ListBacktestsRequest,
    GetStockETFMappingRequest,
    ListWatchlistRequest,
    AddWatchlistStockRequest,
    RemoveWatchlistStockRequest,
)
from .responses import (
    StockQuote,
    ETFQuote,
    LimitUpStock,
    RelatedETF,
    ArbitrageOpportunity,
    Signal,
    BacktestSummary,
    BacktestResult,
    StockETFMapping,
    WatchlistStock,
    MonitorStatus,
    PaginatedResponse,
)

__all__ = [
    # Enums
    "ResponseFormat",
    "MarketType",
    "EventDetectorType",
    "FundSelectorType",
    "SignalFilterType",
    "BacktestStatus",
    "TimeGranularity",
    # Requests
    "GetStockQuoteRequest",
    "GetETFQuoteRequest",
    "ListLimitUpStocksRequest",
    "FindRelatedETFsRequest",
    "AnalyzeOpportunityRequest",
    "ListSignalsRequest",
    "GetSignalRequest",
    "RunBacktestRequest",
    "GetBacktestResultRequest",
    "ListBacktestsRequest",
    "GetStockETFMappingRequest",
    "ListWatchlistRequest",
    "AddWatchlistStockRequest",
    "RemoveWatchlistStockRequest",
    # Responses
    "StockQuote",
    "ETFQuote",
    "LimitUpStock",
    "RelatedETF",
    "ArbitrageOpportunity",
    "Signal",
    "BacktestSummary",
    "BacktestResult",
    "StockETFMapping",
    "WatchlistStock",
    "MonitorStatus",
    "PaginatedResponse",
]
