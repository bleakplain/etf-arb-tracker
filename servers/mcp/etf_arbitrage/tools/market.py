"""
Market data tools for ETF Arbitrage MCP Server.

Provides tools for querying stock/ETF quotes and limit-up stocks.
"""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..models.requests import (
    GetStockQuoteRequest,
    GetETFQuoteRequest,
    ListLimitUpStocksRequest,
)
from ..models.enums import ResponseFormat
from ..utils.formatters import StockFormatter
from .base import (
    fetch_stock_quotes,
    fetch_etf_quotes,
    ToolResponse,
    get_backend,
)


def register_market_tools(mcp: FastMCP):
    """Register all market data tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool(
        name="etf_arbitrage_get_stock_quote",
        annotations={
            "title": "Get Stock Quotes",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def get_stock_quote(params: GetStockQuoteRequest) -> str:
        """Get real-time quotes for multiple stocks.

        This tool fetches current market data for the specified stock codes,
        including price, change, volume, and limit-up/down status. It does NOT
        create or modify stocks, only retrieves existing market data.

        Args:
            params (GetStockQuoteRequest): Validated input parameters containing:
                - codes (List[str]): List of stock codes (6 digits each, e.g., ['600519', '000001'])
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing stock quotes with the following schema:

            Success response (Markdown):
            # Stock Quotes
            Found 2 stocks

            ## 贵州茅台 (600519)
            - **Price**: 1680.50
            - **Change**: +15.30 (+0.92%)
            - **Volume**: 2,500,000
            - **Status**: 🔴 涨停

            ## 平安银行 (000001)
            - **Price**: 12.45
            - **Change**: -0.15 (-1.19%)
            - **Volume**: 15,800,000

            Success response (JSON):
            {
              "quotes": [
                {
                  "code": "600519",
                  "name": "贵州茅台",
                  "price": 1680.50,
                  "change": 15.30,
                  "change_pct": 0.92,
                  "volume": 2500000,
                  "is_limit_up": true
                }
              ]
            }

            Error response:
            "Error: Stock '600519' not found. Suggestion: Verify the stock code is correct"

        Examples:
            - Use when: "Get quotes for Kweichow Moutai and CITIC Securities" -> params with codes=['600519', '600030']
            - Use when: "Check if 000001 is limit-up" -> params with codes=['000001']
            - Don't use when: You need to modify stock data (use watchlist tools instead)
            - Don't use when: You have a stock code and need related ETFs (use etf_arbitrage_find_related_etfs instead)

        Error Handling:
            - Input validation errors are handled by Pydantic model
            - Returns "Error: Stock 'XXX' not found" if code doesn't exist
            - Returns formatted list of quotes or "No quotes found" for empty results
        """
        try:
            # Fetch quotes
            quotes = await fetch_stock_quotes(params.codes)

            if not quotes:
                return ToolResponse.error("No stock quotes found", "Verify the stock codes are correct")

            # Convert to dict format
            quote_dicts = []
            for q in quotes:
                quote_dicts.append({
                    'code': q.code,
                    'name': q.name,
                    'price': q.price,
                    'change': q.change,
                    'change_pct': q.change_pct,
                    'volume': q.volume,
                    'amount': q.amount,
                    'high': q.high,
                    'low': q.low,
                    'open': q.open,
                    'pre_close': q.pre_close,
                    'market': q.market,
                    'is_limit_up': getattr(q, 'is_limit_up', False),
                    'is_limit_down': getattr(q, 'is_limit_down', False),
                    'timestamp': getattr(q, 'timestamp', None),
                })

            # Format response
            if params.response_format == ResponseFormat.JSON:
                import json
                return json.dumps({'quotes': quote_dicts}, indent=2, ensure_ascii=False, default=str)

            # Markdown format
            return StockFormatter.format_quotes(quote_dicts, 'markdown')

        except Exception as e:
            return ToolResponse.error(f"Failed to get stock quotes: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_get_etf_quote",
        annotations={
            "title": "Get ETF Quotes",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def get_etf_quote(params: GetETFQuoteRequest) -> str:
        """Get real-time quotes for multiple ETFs.

        This tool fetches current market data for the specified ETF codes,
        including price, change, volume, and premium rate to NAV. It does NOT
        create or modify ETFs, only retrieves existing market data.

        Args:
            params (GetETFQuoteRequest): Validated input parameters containing:
                - codes (List[str]): List of ETF codes (6 digits each, e.g., ['510300', '159915'])
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing ETF quotes

        Examples:
            - Use when: "Get quotes for CSI 300 ETF and CSI 500 ETF" -> params with codes=['510300', '510500']
            - Use when: "Check the premium rate of 159915" -> params with codes=['159915']
            - Don't use when: You need to find ETFs holding a stock (use etf_arbitrage_find_related_etfs instead)

        Error Handling:
            - Returns "Error: ETF 'XXX' not found" if code doesn't exist
            - Returns formatted list of quotes or "No quotes found" for empty results
        """
        try:
            # Fetch quotes
            quotes = await fetch_etf_quotes(params.codes)

            if not quotes:
                return ToolResponse.error("No ETF quotes found", "Verify the ETF codes are correct")

            # Convert to dict format
            quote_dicts = []
            for q in quotes:
                quote_dicts.append({
                    'code': q.code,
                    'name': q.name,
                    'price': q.price,
                    'change': q.change,
                    'change_pct': q.change_pct,
                    'volume': q.volume,
                    'amount': q.amount,
                    'high': q.high,
                    'low': q.low,
                    'open': q.open,
                    'pre_close': q.pre_close,
                    'market': q.market,
                    'premium_rate': getattr(q, 'premium_rate', None),
                    'timestamp': getattr(q, 'timestamp', None),
                })

            # Format response
            if params.response_format == ResponseFormat.JSON:
                import json
                return json.dumps({'quotes': quote_dicts}, indent=2, ensure_ascii=False, default=str)

            # Markdown format
            lines = ["# ETF Quotes", "", f"Found {len(quote_dicts)} ETFs", ""]
            for q in quote_dicts:
                lines.append(f"## {q['name']} ({q['code']})")
                lines.append(f"- **Price**: {q['price']:.2f}")
                lines.append(f"- **Change**: {q['change']:+.2f} ({q['change_pct']:+.2f}%)")
                lines.append(f"- **Volume**: {q['volume']:,}")
                if q.get('premium_rate') is not None:
                    lines.append(f"- **Premium Rate**: {q['premium_rate']:+.2f}%")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to get ETF quotes: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_list_limit_up_stocks",
        annotations={
            "title": "List Limit-Up Stocks",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def list_limit_up_stocks(params: ListLimitUpStocksRequest) -> str:
        """List today's limit-up stocks.

        This tool retrieves a list of stocks that hit the daily limit-up price,
        which are potential arbitrage opportunities. It does NOT create or modify
        stocks, only retrieves existing market data.

        Args:
            params (ListLimitUpStocksRequest): Validated input parameters containing:
                - limit (int): Maximum results to return (1-100, default=20)
                - offset (int): Number of results to skip for pagination (default=0)
                - min_change_pct (Optional[float]): Minimum change percentage filter
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing limit-up stocks with pagination info

        Examples:
            - Use when: "Show me today's limit-up stocks" -> params with default values
            - Use when: "List limit-up stocks with at least 9.5% gain" -> params with min_change_pct=9.5
            - Don't use when: You need related ETFs for a specific stock (use etf_arbitrage_find_related_etfs instead)

        Error Handling:
            - Returns empty list if no limit-up stocks found
            - Returns formatted list with pagination metadata
        """
        try:
            backend = get_backend()
            fetcher = backend.get_quote_fetcher()

            # Get limit-up stocks from data source
            # This uses the Eastmoney source which provides limit-up lists
            from backend.market.cn.sources.eastmoney_source import EastmoneySource
            source = EastmoneySource()

            limit_up_stocks = await source.get_limit_up_stocks()

            # Apply filter if specified
            if params.min_change_pct is not None:
                limit_up_stocks = [
                    s for s in limit_up_stocks
                    if s.change_pct >= params.min_change_pct
                ]

            # Apply pagination
            total = len(limit_up_stocks)
            start = params.offset
            end = start + params.limit
            paginated_stocks = limit_up_stocks[start:end]

            # Convert to dict format
            stock_dicts = []
            for s in paginated_stocks:
                # Get related ETF count
                engine = backend.get_arbitrage_engine()
                mapping = await engine.get_stock_etf_mapping(s.code)
                related_count = len(mapping.get('etfs', {}))

                stock_dicts.append({
                    'code': s.code,
                    'name': s.name,
                    'price': s.price,
                    'change_pct': s.change_pct,
                    'volume': s.volume,
                    'amount': s.amount,
                    'market': s.market,
                    'limit_up_time': getattr(s, 'limit_up_time', None),
                    'related_etf_count': related_count,
                })

            # Build response
            if params.response_format == ResponseFormat.JSON:
                import json
                response = {
                    'stocks': stock_dicts,
                    'pagination': {
                        'total': total,
                        'count': len(stock_dicts),
                        'offset': params.offset,
                        'has_more': end < total,
                        'next_offset': end if end < total else None,
                    }
                }
                return json.dumps(response, indent=2, ensure_ascii=False, default=str)

            # Markdown format
            lines = ["# Limit-Up Stocks", "", f"Found {total} limit-up stocks (showing {len(stock_dicts)})", ""]
            for s in stock_dicts:
                lines.append(f"## {s['name']} ({s['code']})")
                lines.append(f"- **Price**: {s['price']:.2f}")
                lines.append(f"- **Change**: +{s['change_pct']:.2f}% 🔴")
                lines.append(f"- **Volume**: {s['volume']:,}")
                lines.append(f"- **Related ETFs**: {s['related_etf_count']}")
                lines.append("")

            # Add pagination info
            if end < total:
                lines.append(f"---\n**Pagination**: Use offset={end} to see more results")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to list limit-up stocks: {str(e)}")
