"""
Pydantic response models for ETF Arbitrage MCP Server.

Define structured response schemas for consistent output formatting.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Market Data Responses
# ============================================================================

class StockQuote(BaseModel):
    """Individual stock quote data."""
    code: str = Field(..., description="Stock code (6 digits)")
    name: str = Field(..., description="Stock name")
    price: float = Field(..., description="Current price")
    change: float = Field(..., description="Price change")
    change_pct: float = Field(..., description="Percentage change")
    volume: int = Field(..., description="Trading volume")
    amount: float = Field(..., description="Trading amount")
    high: float = Field(..., description="Day high")
    low: float = Field(..., description="Day low")
    open: float = Field(..., description="Day open")
    pre_close: float = Field(..., description="Previous close")
    market: str = Field(..., description="Market (sh/sz/bj)")
    is_limit_up: bool = Field(default=False, description="Whether stock is limit-up")
    is_limit_down: bool = Field(default=False, description="Whether stock is limit-down")
    timestamp: Optional[str] = Field(default=None, description="Quote timestamp")


class ETFQuote(BaseModel):
    """Individual ETF quote data."""
    code: str = Field(..., description="ETF code (6 digits)")
    name: str = Field(..., description="ETF name")
    price: float = Field(..., description="Current price")
    change: float = Field(..., description="Price change")
    change_pct: float = Field(..., description="Percentage change")
    volume: int = Field(..., description="Trading volume")
    amount: float = Field(..., description="Trading amount")
    high: float = Field(..., description="Day high")
    low: float = Field(..., description="Day low")
    open: float = Field(..., description="Day open")
    pre_close: float = Field(..., description="Previous close")
    market: str = Field(..., description="Market (sh/sz)")
    premium_rate: Optional[float] = Field(default=None, description="Premium rate to NAV")
    timestamp: Optional[str] = Field(default=None, description="Quote timestamp")


class LimitUpStock(BaseModel):
    """Limit-up stock data."""
    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    price: float = Field(..., description="Current price")
    change_pct: float = Field(..., description="Percentage change")
    volume: int = Field(..., description="Trading volume")
    amount: float = Field(..., description="Trading amount")
    market: str = Field(..., description="Market (sh/sz)")
    limit_up_time: Optional[str] = Field(default=None, description="Time when limit-up was reached")
    related_etf_count: int = Field(default=0, description="Number of related ETFs")


# ============================================================================
# Arbitrage Analysis Responses
# ============================================================================

class RelatedETF(BaseModel):
    """ETF that holds the stock."""
    code: str = Field(..., description="ETF code")
    name: str = Field(..., description="ETF name")
    weight: float = Field(..., description="Weight of stock in ETF (0-1)")
    weight_pct: float = Field(..., description="Weight percentage (e.g., 5.2 for 5.2%)")
    market: str = Field(..., description="Market (sh/sz)")
    category: Optional[str] = Field(default=None, description="ETF category")
    daily_amount: Optional[float] = Field(default=None, description="Daily trading amount")
    premium_rate: Optional[float] = Field(default=None, description="Premium rate to NAV")


class ArbitrageOpportunity(BaseModel):
    """Arbitrage opportunity analysis."""
    stock_code: str = Field(..., description="Stock code")
    stock_name: str = Field(..., description="Stock name")
    is_limit_up: bool = Field(..., description="Whether stock is limit-up")
    change_pct: float = Field(..., description="Stock percentage change")
    related_etfs: List[RelatedETF] = Field(..., description="List of related ETFs")
    best_etf: Optional[RelatedETF] = Field(default=None, description="Recommended ETF (highest weight)")
    recent_signals: List[str] = Field(default_factory=list, description="Recent signal IDs")
    analysis_timestamp: str = Field(..., description="When analysis was performed")


# ============================================================================
# Signal Responses
# ============================================================================

class Signal(BaseModel):
    """Trading signal data."""
    id: str = Field(..., description="Signal ID (UUID)")
    stock_code: str = Field(..., description="Stock code")
    stock_name: str = Field(..., description="Stock name")
    etf_code: str = Field(..., description="ETF code")
    etf_name: str = Field(..., description="ETF name")
    weight: float = Field(..., description="Stock weight in ETF")
    event_type: str = Field(..., description="Event type (e.g., 'limit_up')")
    confidence: float = Field(..., description="Signal confidence (0-1)")
    timestamp: str = Field(..., description="Signal timestamp (ISO format)")
    created_at: str = Field(..., description="When signal was created")


# ============================================================================
# Backtest Responses
# ============================================================================

class BacktestSummary(BaseModel):
    """Backtest summary statistics."""
    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Job status")
    start_date: str = Field(..., description="Backtest start date")
    end_date: str = Field(..., description="Backtest end date")
    total_signals: int = Field(..., description="Total signals generated")
    event_detector: str = Field(..., description="Event detector used")
    fund_selector: str = Field(..., description="Fund selector used")
    signal_filters: List[str] = Field(..., description="Signal filters applied")
    created_at: str = Field(..., description="Job creation timestamp")
    completed_at: Optional[str] = Field(default=None, description="Job completion timestamp")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BacktestResult(BaseModel):
    """Detailed backtest results."""
    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Job status")
    summary: BacktestSummary = Field(..., description="Summary statistics")
    signals: List[Signal] = Field(default_factory=list, description="Generated signals")
    performance: Optional[Dict[str, Any]] = Field(default=None, description="Performance metrics")


# ============================================================================
# Configuration Responses
# ============================================================================

class StockETFMapping(BaseModel):
    """Stock to ETF mapping."""
    stock_code: str = Field(..., description="Stock code")
    stock_name: str = Field(..., description="Stock name")
    etfs: List[Dict[str, Any]] = Field(..., description="List of ETFs holding this stock")
    total_etfs: int = Field(..., description="Total number of related ETFs")


class WatchlistStock(BaseModel):
    """Watchlist stock entry."""
    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    market: str = Field(..., description="Market (sh/sz/bj)")
    notes: Optional[str] = Field(default=None, description="User notes")
    added_at: Optional[str] = Field(default=None, description="When added to watchlist")


# ============================================================================
# Monitor Responses
# ============================================================================

class MonitorStatus(BaseModel):
    """Monitor status information."""
    is_running: bool = Field(..., description="Whether monitor is running")
    last_scan: Optional[str] = Field(default=None, description="Last scan timestamp")
    next_scan: Optional[str] = Field(default=None, description="Next scheduled scan")
    scan_interval: int = Field(..., description="Scan interval in seconds")
    watched_stocks: int = Field(..., description="Number of stocks being watched")
    total_signals: int = Field(..., description="Total signals generated this session")
    is_trading_time: bool = Field(..., description="Whether currently in trading hours")
    time_to_close: Optional[int] = Field(default=None, description="Seconds until market close")


# ============================================================================
# Pagination Response Wrapper
# ============================================================================

class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    total: int = Field(..., description="Total number of items")
    count: int = Field(..., description="Number of items in this response")
    offset: int = Field(..., description="Current pagination offset")
    has_more: bool = Field(..., description="Whether more items exist")
    next_offset: Optional[int] = Field(default=None, description="Next offset for pagination")
