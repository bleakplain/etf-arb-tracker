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
    ListMyStocksRequest,
    AddMyStockRequest,
    RemoveMyStockRequest,
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
    MyStock,
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
    "ListMyStocksRequest",
    "AddMyStockRequest",
    "RemoveMyStockRequest",
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
    "MyStock",
    "MonitorStatus",
    "PaginatedResponse",
]
