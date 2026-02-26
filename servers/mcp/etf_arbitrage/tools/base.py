"""
Base utilities and shared functions for ETF Arbitrage MCP tools.

This module provides common functionality used across all tools,
including backend integration, error handling, and response formatting.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel

from ..models.enums import ResponseFormat
from ..utils.errors import format_error, NotFoundError, APIError
from ..utils.formatters import StockFormatter, ETFFormatter, SignalFormatter, PaginationFormatter


# ============================================================================
# Backend Integration
# ============================================================================

class BackendBridge:
    """Bridge to etf-arb-tracker backend functionality."""

    def __init__(self):
        """Initialize backend connections."""
        self._quote_fetcher = None
        self._arbitrage_engine = None
        self._signal_repository = None
        self._mapping_repository = None
        self._backtest_engine = None
        self._config = None

    def get_quote_fetcher(self):
        """Get or initialize quote fetcher."""
        if self._quote_fetcher is None:
            from backend.market.cn.fetcher import QuoteFetcherCN
            self._quote_fetcher = QuoteFetcherCN()
        return self._quote_fetcher

    def get_arbitrage_engine(self):
        """Get or initialize arbitrage engine."""
        if self._arbitrage_engine is None:
            from backend.arbitrage.cn.arbitrage_engine import ArbitrageEngineCN
            from backend.arbitrage.strategy_registry import (
                event_detector_registry,
                fund_selector_registry,
                signal_filter_registry,
            )
            from backend.api.dependencies import register_strategies

            # Register strategies
            register_strategies()

            # Create engine
            self._arbitrage_engine = ArbitrageEngineCN(
                event_detector=event_detector_registry.get("limit_up_cn"),
                fund_selector=fund_selector_registry.get("highest_weight"),
                signal_filters=[
                    signal_filter_registry.get("time_filter_cn"),
                    signal_filter_registry.get("liquidity_filter"),
                ],
            )
        return self._arbitrage_engine

    def get_signal_repository(self):
        """Get or initialize signal repository."""
        if self._signal_repository is None:
            from backend.signal.db_repository import DBSignalRepository
            self._signal_repository = DBSignalRepository()
        return self._signal_repository

    def get_mapping_repository(self):
        """Get or initialize mapping repository."""
        if self._mapping_repository is None:
            from backend.data.mapping_repository import StockETFMappingRepository
            self._mapping_repository = StockETFMappingRepository()
        return self._mapping_repository

    def get_backtest_engine(self):
        """Get or initialize backtest engine."""
        if self._backtest_engine is None:
            from backend.backtest.cn.engine import CNBacktestEngine
            self._backtest_engine = CNBacktestEngine()
        return self._backtest_engine

    def get_config(self):
        """Get or load configuration."""
        if self._config is None:
            import yaml
            config_path = project_root / "config" / "settings.yaml"
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        return self._config


# Global backend bridge instance
_backend_bridge = BackendBridge()


def get_backend() -> BackendBridge:
    """Get the global backend bridge instance."""
    return _backend_bridge


# ============================================================================
# Tool Response Helpers
# ============================================================================

class ToolResponse:
    """Helper for building tool responses."""

    @staticmethod
    def success(data: Any, format_type: ResponseFormat = ResponseFormat.JSON) -> str:
        """Build a successful response.

        Args:
            data: Response data (dict, list, or str)
            format_type: Output format (json or markdown)

        Returns:
            str: Formatted response
        """
        if format_type == ResponseFormat.JSON:
            if isinstance(data, str):
                return data
            import json
            return json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return data  # Already formatted as markdown

    @staticmethod
    def error(message: str, suggestion: Optional[str] = None) -> str:
        """Build an error response.

        Args:
            message: Error message
            suggestion: Optional suggestion for resolution

        Returns:
            str: Formatted error message
        """
        if suggestion:
            return f"Error: {message}. Suggestion: {suggestion}"
        return f"Error: {message}"

    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        offset: int,
        limit: int,
        format_type: ResponseFormat = ResponseFormat.JSON
    ) -> str:
        """Build a paginated response.

        Args:
            items: List of items for current page
            total: Total number of items
            offset: Current offset
            limit: Page size
            format_type: Output format

        Returns:
            str: Formatted paginated response
        """
        count = len(items)
        has_more = offset + count < total
        next_offset = offset + count if has_more else None

        pagination_meta = {
            "total": total,
            "count": count,
            "offset": offset,
            "has_more": has_more,
            "next_offset": next_offset,
        }

        if format_type == ResponseFormat.JSON:
            import json
            response = {
                "items": items,
                "pagination": pagination_meta,
            }
            return json.dumps(response, indent=2, ensure_ascii=False, default=str)

        # Markdown format
        lines = [str(items)]  # items should already be formatted
        lines.append(PaginationFormatter.format_pagination(pagination_meta, "markdown"))
        return "\n\n".join(lines)


# ============================================================================
# Async Tool Helpers
# ============================================================================

async def fetch_stock_quotes(codes: List[str]) -> List[Dict[str, Any]]:
    """Fetch quotes for multiple stocks.

    Args:
        codes: List of stock codes

    Returns:
        List of stock quote dictionaries
    """
    backend = get_backend()
    fetcher = backend.get_quote_fetcher()

    try:
        # Batch fetch (max 100 per request)
        results = []
        for i in range(0, len(codes), 100):
            batch = codes[i:i+100]
            quotes = await fetcher.fetch_batch(batch)
            results.extend(quotes)
        return results
    except Exception as e:
        raise APIError(f"Failed to fetch stock quotes: {str(e)}")


async def fetch_etf_quotes(codes: List[str]) -> List[Dict[str, Any]]:
    """Fetch quotes for multiple ETFs.

    Args:
        codes: List of ETF codes

    Returns:
        List of ETF quote dictionaries
    """
    backend = get_backend()
    fetcher = backend.get_quote_fetcher()

    try:
        # Batch fetch
        results = []
        for i in range(0, len(codes), 100):
            batch = codes[i:i+100]
            quotes = await fetcher.fetch_batch(batch)
            results.extend(quotes)
        return results
    except Exception as e:
        raise APIError(f"Failed to fetch ETF quotes: {str(e)}")


async def find_related_etfs(stock_code: str, min_weight: float = 0.05) -> List[Dict[str, Any]]:
    """Find ETFs that hold a specific stock.

    Args:
        stock_code: Stock code
        min_weight: Minimum weight threshold

    Returns:
        List of related ETFs with weight information
    """
    backend = get_backend()
    engine = backend.get_arbitrage_engine()

    try:
        # Get mapping
        mapping = await engine.get_stock_etf_mapping(stock_code)

        # Filter by weight
        etfs = []
        for etf_code, weight in mapping.get('etfs', {}).items():
            if weight >= min_weight:
                etf_info = await get_etf_info(etf_code)
                etf_info['weight'] = weight
                etf_info['weight_pct'] = weight * 100
                etfs.append(etf_info)

        return etfs
    except Exception as e:
        raise APIError(f"Failed to find related ETFs: {str(e)}")


async def get_etf_info(etf_code: str) -> Dict[str, Any]:
    """Get detailed information about an ETF.

    Args:
        etf_code: ETF code

    Returns:
        ETF information dictionary
    """
    backend = get_backend()
    fetcher = backend.get_quote_fetcher()

    try:
        quote = await fetcher.fetch_one(etf_code)
        return {
            'code': quote.code,
            'name': quote.name,
            'market': quote.market,
            'price': quote.price,
            'change': quote.change,
            'change_pct': quote.change_pct,
            'premium_rate': quote.premium_rate if hasattr(quote, 'premium_rate') else None,
        }
    except Exception as e:
        raise APIError(f"Failed to get ETF info: {str(e)}")


def validate_stock_code(code: str) -> bool:
    """Validate stock code format.

    Args:
        code: Stock code to validate

    Returns:
        bool: True if valid
    """
    return bool(code and len(code) == 6 and code.isdigit())


def validate_date(date_str: str) -> bool:
    """Validate date string format (YYYY-MM-DD).

    Args:
        date_str: Date string to validate

    Returns:
        bool: True if valid
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False
