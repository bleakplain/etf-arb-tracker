#!/usr/bin/env python3
"""
ETF Arbitrage MCP Server - Main Entry Point

This server exposes ETF arbitrage monitoring and analysis capabilities
through the Model Context Protocol (MCP).

Usage:
    # stdio transport (for local tools)
    python -m etf_arbitrage.server

    # Streamable HTTP transport (for remote servers)
    python -m etf_arbitrage.server --transport streamable-http --port 8000

    # With MCP Inspector for testing
    mcp-dev-tool etf_arbitrage/server.py
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from .config import Config


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def server_lifespan():
    """Manage server lifespan and initialize resources.

    This context manager is called when the server starts and stops.
    Use it to initialize connections, load configuration, etc.
    """
    import logging
    from .config import Config

    # Configure logging
    log_level = Config.get_log_level()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr  # Log to stderr for stdio transport
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Starting {Config.SERVER_NAME} v{Config.SERVER_VERSION}")

    # Verify configuration files exist
    if not Config.get_settings_path().exists():
        logger.warning(f"Settings file not found: {Config.get_settings_path()}")

    if not Config.get_stocks_path().exists():
        logger.warning(f"Stocks file not found: {Config.get_stocks_path()}")

    # Create data directory if needed
    Config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Register strategies
    try:
        from backend.api.dependencies import register_strategies
        register_strategies()
        logger.info("Strategies registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register strategies: {e}")

    # Initialize backend bridge (will lazy-load on first use)
    logger.info("Backend bridge initialized (lazy loading)")

    # Yield control back to server
    yield {}

    # Shutdown: Cleanup resources
    logger.info(f"Stopping {Config.SERVER_NAME}")


# ============================================================================
# Server Initialization
# ============================================================================

# Create FastMCP server instance
mcp = FastMCP(
    name=Config.SERVER_NAME,
    lifespan=server_lifespan,
)


# Register tool groups
def register_all_tools():
    """Register all tool groups with the MCP server."""
    from .tools import market, arbitrage, signal, backtest, my_stocks, monitor

    market.register_market_tools(mcp)
    arbitrage.register_arbitrage_tools(mcp)
    signal.register_signal_tools(mcp)
    backtest.register_backtest_tools(mcp)
    my_stocks.register_config_tools(mcp)
    monitor.register_monitor_tools(mcp)


# Register tools on module load
register_all_tools()


# ============================================================================
# Server Info
# ============================================================================

def get_server_info() -> dict:
    """Get server information.

    Returns:
        dict: Server metadata
    """
    return {
        "name": Config.SERVER_NAME,
        "version": Config.SERVER_VERSION,
        "tools": [
            # Market Data
            "etf_arbitrage_get_stock_quote",
            "etf_arbitrage_get_etf_quote",
            "etf_arbitrage_list_limit_up_stocks",
            # Arbitrage Analysis
            "etf_arbitrage_find_related_etfs",
            "etf_arbitrage_analyze_opportunity",
            # Signal Management
            "etf_arbitrage_list_signals",
            "etf_arbitrage_get_signal",
            # Backtesting
            "etf_arbitrage_run_backtest",
            "etf_arbitrage_get_backtest_result",
            "etf_arbitrage_list_backtests",
            # Configuration
            "etf_arbitrage_get_stock_etf_mapping",
            "etf_arbitrage_list_my_stocks",
            "etf_arbitrage_add_my_stock",
            "etf_arbitrage_remove_my_stock",
            # Monitor Control
            "etf_arbitrage_get_monitor_status",
            "etf_arbitrage_start_monitor",
            "etf_arbitrage_stop_monitor",
            "etf_arbitrage_trigger_scan",
        ]
    }


# ============================================================================
# Server Entry Point
# ============================================================================

def main():
    """Main entry point for the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(
        description=f"{Config.SERVER_NAME} - ETF Arbitrage MCP Server"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=Config.get_transport(),
        help="Transport type (default: from MCP_TRANSPORT env var or 'stdio')"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=Config.DEFAULT_PORT,
        help=f"Port for HTTP transport (default: {Config.DEFAULT_PORT})"
    )
    parser.add_argument(
        "--host",
        default=Config.DEFAULT_HOST,
        help=f"Host for HTTP transport (default: {Config.DEFAULT_HOST})"
    )

    args = parser.parse_args()

    # Run server with specified transport
    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", port=args.port, host=args.host)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
