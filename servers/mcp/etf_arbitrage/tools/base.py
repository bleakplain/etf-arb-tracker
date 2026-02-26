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
        self._etf_holder_provider = None
        self._etf_holdings_provider = None
        self._etf_quote_provider = None
        self._arbitrage_engine = None
        self._signal_repository = None
        self._mapping_repository = None
        self._backtest_engine = None
        self._config = None
        self._backtest_repo = None

    def get_quote_fetcher(self):
        """Get or initialize quote fetcher."""
        if self._quote_fetcher is None:
            from backend.market.cn.quote_fetcher import QuoteFetcherCN
            self._quote_fetcher = QuoteFetcherCN()
        return self._quote_fetcher

    def get_etf_holder_provider(self):
        """Get or initialize ETF holder provider."""
        if self._etf_holder_provider is None:
            from backend.market.cn.etf_holder_provider import ETFHolderProvider
            self._etf_holder_provider = ETFHolderProvider()
        return self._etf_holder_provider

    def get_etf_holdings_provider(self):
        """Get or initialize ETF holdings provider."""
        if self._etf_holdings_provider is None:
            from backend.market.cn.etf_holdings_provider import ETFHoldingsProvider
            self._etf_holdings_provider = ETFHoldingsProvider()
        return self._etf_holdings_provider

    def get_etf_quote_provider(self):
        """Get or initialize ETF quote provider."""
        if self._etf_quote_provider is None:
            from backend.market.cn.etf_quote_provider import ETFQuoteProvider
            self._etf_quote_provider = ETFQuoteProvider()
        return self._etf_quote_provider

    def get_arbitrage_engine(self):
        """Get or initialize arbitrage engine."""
        if self._arbitrage_engine is None:
            from backend.arbitrage.cn.arbitrage_engine import ArbitrageEngineCN
            from backend.arbitrage.cn.factory import ArbitrageEngineFactory
            from backend.api.dependencies import get_config, get_clock

            # Register strategies
            from backend.api.dependencies import register_strategies
            register_strategies()

            # Use factory to create engine
            config = get_config()
            clock = get_clock()
            self._arbitrage_engine = ArbitrageEngineFactory.create_engine(config, clock)
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
            from backend.arbitrage.interfaces import InMemoryMappingRepository
            self._mapping_repository = InMemoryMappingRepository()
        return self._mapping_repository

    def get_backtest_engine(self):
        """Get or initialize backtest engine."""
        if self._backtest_engine is None:
            from backend.backtest.cn.engine import CNBacktestEngine
            self._backtest_engine = CNBacktestEngine()
        return self._backtest_engine

    def get_backtest_repository(self):
        """Get or initialize backtest repository."""
        if self._backtest_repo is None:
            from backend.data.backtest_repository import BacktestRepository
            self._backtest_repo = BacktestRepository()
        return self._backtest_repo

    def get_config(self):
        """Get or load configuration."""
        if self._config is None:
            import yaml
            config_path = project_root / "config" / "settings.yaml"
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        return self._config

    @property
    def PROJECT_ROOT(self):
        """Get project root path."""
        return project_root

    @property
    def CONFIG_DIR(self):
        """Get config directory."""
        return project_root / "config"

    @property
    def DATA_DIR(self):
        """Get data directory."""
        return project_root / "data"

    def get_stocks_path(self):
        """Get stocks configuration file path."""
        return self.CONFIG_DIR / "stocks.yaml"


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
    fetcher = backend.get_etf_quote_provider()

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


async def get_stock_info(stock_code: str) -> Optional[Dict[str, Any]]:
    """Get stock information from available sources.

    Args:
        stock_code: Stock code

    Returns:
        Stock information dict or None
    """
    backend = get_backend()

    try:
        # Try to fetch quote
        quotes = await fetch_stock_quotes([stock_code])
        if quotes:
            q = quotes[0]
            return {
                'code': q.code,
                'name': q.name,
                'price': q.price,
                'change': q.change,
                'change_pct': q.change_pct,
                'is_limit_up': getattr(q, 'is_limit_up', False),
                'market': q.market,
            }
    except:
        pass

    return None


async def get_etf_info(etf_code: str) -> Dict[str, Any]:
    """Get detailed information about an ETF.

    Args:
        etf_code: ETF code

    Returns:
        ETF information dictionary
    """
    backend = get_backend()
    fetcher = backend.get_etf_quote_provider()

    try:
        quote = await fetcher.fetch_one(etf_code)
        return {
            'code': quote.code,
            'name': quote.name,
            'market': quote.market,
            'price': quote.price,
            'change': quote.change,
            'change_pct': quote.change_pct,
            'premium_rate': getattr(quote, 'premium_rate', None),
        }
    except Exception as e:
        # Return minimal info if fetch fails
        return {
            'code': etf_code,
            'name': etf_code,
            'market': 'unknown',
        }


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
