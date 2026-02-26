"""
ETF Arbitrage MCP Server

A Model Context Protocol server that exposes ETF arbitrage monitoring
and analysis capabilities.

This server provides tools for:
- Market data queries (stock/ETF quotes, limit-up stocks)
- Arbitrage analysis (related ETFs, opportunity detection)
- Signal management (historical signals, signal details)
- Backtesting (strategy testing with historical data)
- Configuration (watchlist, stock-ETF mapping)
- Monitor control (start/stop/status)

Server Name: etf_arbitrage_mcp
Package Name: etf_arbitrage
"""

__version__ = "0.1.0"

from .server import mcp

__all__ = ["mcp", "__version__"]
