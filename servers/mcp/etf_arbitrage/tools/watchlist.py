"""
Configuration and watchlist management tools for ETF Arbitrage MCP Server.

Provides tools for managing watchlist and accessing stock-ETF mappings.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP

from ..models.requests import (
    GetStockETFMappingRequest,
    ListWatchlistRequest,
    AddWatchlistStockRequest,
    RemoveWatchlistStockRequest,
)
from ..models.enums import ResponseFormat, MarketType
from ..utils.errors import get_error_response, ValidationError
from .base import (
    get_backend,
    ToolResponse,
)


def register_config_tools(mcp: FastMCP):
    """Register all configuration management tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool(
        name="etf_arbitrage_get_stock_etf_mapping",
        annotations={
            "title": "Get Stock-ETF Mapping",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def get_stock_etf_mapping(params: GetStockETFMappingRequest) -> str:
        """Get stock to ETF mapping relationships.

        This tool retrieves the mapping between stocks and ETFs that hold them.
        The mapping includes weight information and is used for arbitrage analysis.
        It does NOT create or modify mappings, only retrieves existing data.

        Args:
            params (GetStockETFMappingRequest): Validated input parameters containing:
                - stock_code (Optional[str]): Filter by specific stock code (6 digits)
                - include_weights (bool): Whether to include weight information (default=True)
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing stock-ETF mappings

        Examples:
            - Use when: "Get all stock-ETF mappings" -> params with default values
            - Use when: "Show ETFs holding stock 600519" -> params with stock_code='600519'
            - Don't use when: You need real-time ETF quotes (use etf_arbitrage_get_etf_quote instead)
            - Don't use when: You need to find related ETFs with analysis (use etf_arbitrage_find_related_etfs instead)

        Error Handling:
            - Returns empty mapping if no relationships found
            - Returns filtered results if stock_code is specified
        """
        try:
            backend = get_backend()
            mapping_repo = backend.get_mapping_repository()
            config = backend.get_config()

            # Load mapping
            mapping_path = backend.PROJECT_ROOT / "data" / "cn_stock_etf_mapping.json"

            if not mapping_path.exists():
                return "# Stock-ETF Mapping\n\nNo mapping data available. Run initialization first."

            import json
            with open(mapping_path, 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)

            # Filter by stock code if specified
            if params.stock_code:
                if params.stock_code not in mapping_data:
                    return f"# Stock-ETF Mapping\n\nNo mapping found for stock {params.stock_code}"

                mapping_data = {
                    params.stock_code: mapping_data[params.stock_code]
                }

            # Build response
            if params.response_format == ResponseFormat.JSON:
                return json.dumps(mapping_data, indent=2, ensure_ascii=False)

            # Markdown format
            lines = ["# Stock-ETF Mapping", ""]

            for stock_code, etfs in mapping_data.items():
                # Get stock name if available
                stock_name = etfs.get('stock_name', stock_code)
                lines.append(f"## {stock_name} ({stock_code})")
                lines.append("")
                lines.append(f"**Total ETFs**: {len(etfs.get('etfs', {}))}")
                lines.append("")

                if params.include_weights:
                    # Sort by weight descending
                    etf_list = sorted(
                        etfs.get('etfs', {}).items(),
                        key=lambda x: x[1],
                        reverse=True
                    )

                    for etf_code, weight in etf_list[:20]:  # Show top 20
                        weight_pct = weight * 100
                        lines.append(f"- **{etf_code}**: {weight_pct:.2f}%")

                    if len(etf_list) > 20:
                        lines.append(f"- *... and {len(etf_list) - 20} more ETFs*")

                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to get mapping: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_list_watchlist",
        annotations={
            "title": "List Watchlist",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def list_watchlist(params: ListWatchlistRequest) -> str:
        """List stocks in the watchlist.

        This tool retrieves the current watchlist configuration, including
        all monitored stocks and their metadata. It does NOT create or modify
        the watchlist, only retrieves existing entries.

        Args:
            params (ListWatchlistRequest): Validated input parameters containing:
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing watchlist stocks

        Examples:
            - Use when: "Show my watchlist" -> params with default values
            - Use when: "What stocks am I monitoring?" -> params with default values
            - Don't use when: You need to add a stock (use etf_arbitrage_add_watchlist_stock instead)
            - Don't use when: You need to remove a stock (use etf_arbitrage_remove_watchlist_stock instead)

        Error Handling:
            - Returns empty list if watchlist is not configured
            - Returns all watchlist entries with metadata
        """
        try:
            backend = get_backend()
            stocks_path = backend.get_stocks_path()

            if not stocks_path.exists():
                return "# Watchlist\n\nNo watchlist configured."

            with open(stocks_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            watchlist = config.get('my_stocks', [])

            if not watchlist:
                return "# Watchlist\n\nWatchlist is empty."

            # Build response
            if params.response_format == ResponseFormat.JSON:
                import json
                return json.dumps({'stocks': watchlist}, indent=2, ensure_ascii=False)

            # Markdown format
            lines = ["# Watchlist", "", f"Total stocks: {len(watchlist)}", ""]

            for stock in watchlist:
                lines.append(f"## {stock['name']} ({stock['code']})")
                lines.append(f"- **Market**: {stock['market'].upper()}")
                if stock.get('notes'):
                    lines.append(f"- **Notes**: {stock['notes']}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to list watchlist: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_add_watchlist_stock",
        annotations={
            "title": "Add Stock to Watchlist",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    async def add_watchlist_stock(params: AddWatchlistStockRequest) -> str:
        """Add a stock to the watchlist.

        This tool adds a new stock to the watchlist configuration. The stock
        will be monitored for arbitrage opportunities. If the stock already
        exists in the watchlist, it will be updated with the new information.

        Args:
            params (AddWatchlistStockRequest): Validated input parameters containing:
                - code (str): Stock code (6 digits, e.g., '600519')
                - name (str): Stock name (e.g., '贵州茅台')
                - market (MarketType): Market type ('sh', 'sz', or 'bj')
                - notes (Optional[str]): Optional notes about this stock

        Returns:
            str: Formatted response confirming the addition

        Examples:
            - Use when: "Add Kweichow Moutai to my watchlist" -> params with code='600519', name='贵州茅台', market='sh'
            - Use when: "Monitor China Merchants Bank" -> params with code='600036', name='招商银行', market='sh'
            - Don't use when: You need to list all watchlist stocks (use etf_arbitrage_list_watchlist instead)
            - Don't use when: You need to remove a stock (use etf_arbitrage_remove_watchlist_stock instead)

        Error Handling:
            - Validates stock code format (6 digits)
            - Validates market type
            - Creates or updates watchlist entry
        """
        try:
            backend = get_backend()
            stocks_path = backend.get_stocks_path()

            # Load existing config
            if stocks_path.exists():
                with open(stocks_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            else:
                config = {'my_stocks': [], 'watch_etfs': []}

            watchlist = config.get('my_stocks', [])

            # Check if stock already exists
            existing_index = None
            for i, stock in enumerate(watchlist):
                if stock['code'] == params.code:
                    existing_index = i
                    break

            # Prepare stock entry
            stock_entry = {
                'code': params.code,
                'name': params.name,
                'market': params.market.value,
            }

            if params.notes:
                stock_entry['notes'] = params.notes

            # Add or update
            if existing_index is not None:
                watchlist[existing_index] = stock_entry
                message = f"Updated stock {params.name} ({params.code}) in watchlist"
            else:
                watchlist.append(stock_entry)
                message = f"Added stock {params.name} ({params.code}) to watchlist"

            # Save config
            config['my_stocks'] = watchlist
            stocks_path.parent.mkdir(parents=True, exist_ok=True)

            with open(stocks_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            return f"✅ {message}\n\nTotal stocks in watchlist: {len(watchlist)}"

        except Exception as e:
            return ToolResponse.error(f"Failed to add stock to watchlist: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_remove_watchlist_stock",
        annotations={
            "title": "Remove Stock from Watchlist",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def remove_watchlist_stock(params: RemoveWatchlistStockRequest) -> str:
        """Remove a stock from the watchlist.

        This tool removes a stock from the watchlist configuration. The stock
        will no longer be monitored for arbitrage opportunities.

        Args:
            params (RemoveWatchlistStockRequest): Validated input parameters containing:
                - code (str): Stock code (6 digits, e.g., '600519')

        Returns:
            str: Formatted response confirming the removal

        Examples:
            - Use when: "Remove stock 600519 from my watchlist" -> params with code='600519'
            - Use when: "Stop monitoring Kweichow Moutai" -> params with code='600519'
            - Don't use when: You need to list watchlist stocks (use etf_arbitrage_list_watchlist instead)
            - Don't use when: You need to add a stock (use etf_arbitrage_add_watchlist_stock instead)

        Error Handling:
            - Validates stock code format (6 digits)
            - Returns success even if stock not in watchlist (idempotent)
            - Returns remaining count
        """
        try:
            backend = get_backend()
            stocks_path = backend.get_stocks_path()

            if not stocks_path.exists():
                return "✅ Stock not in watchlist (watchlist is empty)"

            # Load existing config
            with open(stocks_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            watchlist = config.get('my_stocks', [])

            # Find and remove stock
            original_length = len(watchlist)
            watchlist = [s for s in watchlist if s['code'] != params.code]

            if len(watchlist) == original_length:
                return f"ℹ️ Stock {params.code} not found in watchlist"

            # Save config
            config['my_stocks'] = watchlist

            with open(stocks_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            return f"✅ Removed stock {params.code} from watchlist\n\nTotal stocks in watchlist: {len(watchlist)}"

        except Exception as e:
            return ToolResponse.error(f"Failed to remove stock from watchlist: {str(e)}")
