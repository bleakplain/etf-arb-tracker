# ETF Arbitrage MCP Server

A Model Context Protocol (MCP) server that exposes ETF arbitrage monitoring and analysis capabilities from the etf-arb-tracker system.

## Features

- **Market Data**: Query stock/ETF quotes and limit-up stocks
- **Arbitrage Analysis**: Find related ETFs and analyze opportunities
- **Signal Management**: Query historical trading signals
- **Backtesting**: Test strategies with historical data
- **Configuration**: Manage watchlist and stock-ETF mappings
- **Monitor Control**: Start/stop monitoring service

## Installation

```bash
# From the etf-arb-tracker repository root
cd servers/mcp
pip install -r requirements.txt
```

## Usage

### Running the Server

```bash
# stdio transport (for local tools)
python -m etf_arbitrage.server

# Streamable HTTP transport (for remote servers)
python -m etf_arbitrage.server --transport streamable-http --port 8000

# With MCP Inspector for testing
mcp-dev-tool etf_arbitrage/server.py
```

### Available Tools

#### Market Data
- `etf_arbitrage_get_stock_quote` - Get real-time stock quotes
- `etf_arbitrage_get_etf_quote` - Get real-time ETF quotes
- `etf_arbitrage_list_limit_up_stocks` - List today's limit-up stocks

#### Arbitrage Analysis
- `etf_arbitrage_find_related_etfs` - Find ETFs holding a stock
- `etf_arbitrage_analyze_opportunity` - Analyze arbitrage opportunity

#### Signal Management
- `etf_arbitrage_list_signals` - List historical signals
- `etf_arbitrage_get_signal` - Get signal details

#### Backtesting
- `etf_arbitrage_run_backtest` - Run a backtest
- `etf_arbitrage_get_backtest_result` - Get backtest results
- `etf_arbitrage_list_backtests` - List backtest jobs

#### Configuration
- `etf_arbitrage_get_stock_etf_mapping` - Get stock-ETF mappings
- `etf_arbitrage_list_watchlist` - List watchlist stocks
- `etf_arbitrage_add_watchlist_stock` - Add stock to watchlist
- `etf_arbitrage_remove_watchlist_stock` - Remove stock from watchlist

#### Monitor Control
- `etf_arbitrage_get_monitor_status` - Get monitor status
- `etf_arbitrage_start_monitor` - Start monitoring
- `etf_arbitrage_stop_monitor` - Stop monitoring
- `etf_arbitrage_trigger_scan` - Trigger manual scan

## Configuration

The server uses configuration files from the parent etf-arb-tracker project:

- `config/settings.yaml` - System settings
- `config/stocks.yaml` - Watchlist configuration
- `data/app.db` - Signal database
- `data/cn_stock_etf_mapping.json` - Stock-ETF mapping cache

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black etf_arbitrage/

# Type check
mypy etf_arbitrage/

# Lint
ruff check etf_arbitrage/
```

## License

This project is part of etf-arb-tracker.
