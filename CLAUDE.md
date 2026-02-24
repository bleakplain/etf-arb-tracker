# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ETF Arbitrage Tracker** - A Python-based system that monitors A-share limit-up stocks and identifies arbitrage opportunities through associated ETFs. When a core holding stock hits its daily trading limit, the system automatically finds ETFs with significant exposure to those stocks.

### Key Concepts

- **Limit-up stocks** (涨停股): A-share stocks that hit their daily maximum price increase (typically 10% for main board, 20% for STAR/ChiNext)
- **ETF arbitrage**: When a stock is limit-up (cannot buy directly), buy the ETF that holds it to capture the premium
- **Strategy requirement**: Stock must have >=5% weight in the ETF for the signal to be valid (configurable via `strategy.min_weight`)

## Running the Application

### Development Commands

```bash
# Initialize data (build stock-ETF mapping cache)
python start.py init

# Run both API server and monitoring service
python start.py both

# Run API server only
python start.py api

# Run monitoring service only
python start.py monitor

# Or use the shell script (checks venv, dependencies, config)
./run_server.sh
```

### Access Points

- Web Dashboard: http://localhost:8000/frontend/index.html
- API Documentation: http://localhost:8000/docs
- API Root: http://localhost:8000/

### Code Quality

```bash
# Format code
black backend/ config/ start.py

# Lint code
flake8 backend/ config/ start.py

# Type checking
mypy backend/
```

## Architecture

The system follows **Clean Architecture** with clear layer separation:

```
backend/
├── domain/           # Domain layer - interfaces and value objects
├── infrastructure/   # Infrastructure - caching utilities
├── data/             # Data layer - fetchers and sources
├── strategy/         # Strategy layer - business logic
├── notification/     # Notification layer
└── api/              # API layer - FastAPI endpoints
```

### Key Components

1. **`LimitUpMonitor`** (`backend/strategy/limit_monitor.py`) - Main orchestrator
   - Coordinates: `LimitChecker` → `ETFSelector` → `SignalGenerator`
   - Uses dependency injection pattern
   - Manages stock-ETF mapping

2. **Data Flow**:
   - `LimitChecker` checks if stock is limit-up
   - `ETFSelector` finds ETFs with stock weight >= 5%
   - `SignalGenerator` creates trading signals
   - `DBSignalRepository` persists signals to `data/app.db` (SQLite)

3. **Data Sources** (`backend/data/sources/`):
   - `tencent_source.py` - Primary: Tencent Finance API (free, high-frequency)
   - `eastmoney_source.py` - Backup: Eastmoney API (limit-up stocks)
   - `sina_source.py` - Removed (deprecated)
   - Automatic failover between sources

### Critical Files

| File | Purpose |
|------|---------|
| `backend/strategy/limit_monitor.py:57-388` | `LimitUpMonitor` class - core orchestration |
| `backend/api/app.py:1-622` | FastAPI application and all endpoints |
| `config/settings.yaml` | System configuration (strategy params, trading hours) |
| `config/stocks.yaml` | User watchlist configuration |
| `data/app.db` | 信号和自选股数据库 (SQLite) |

## Configuration

### `config/stocks.yaml` - Watchlist

```yaml
my_stocks:
  - code: "600519"
    name: "贵州茅台"
    market: "sh"
    notes: "白酒龙头"

watch_etfs:
  - code: "510300"
    name: "沪深300ETF"
```

### `config/settings.yaml` - System Settings

Key sections:
- `strategy.*` - Strategy parameters (min_weight, scan_interval, etc.)
- `trading_hours` - Trading time windows
- `data_sources.*` - Data source priorities and rate limits
- `refresh.*` - Cache intervals (anti-scraping measures)
- `signal_evaluation.*` - Confidence and risk thresholds
- `notification.*` - DingTalk, Email, WeChat Work settings

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/status` | System status, trading time, signal count |
| `GET` | `/api/stocks` | Watchlist real-time quotes |
| `GET` | `/api/stocks/{code}/related-etfs` | ETFs holding stock (weight >= 5%) |
| `GET` | `/api/limit-up` | Today's limit-up stocks (TTL cached) |
| `GET` | `/api/signals` | Trading signal history |
| `POST` | `/api/monitor/scan` | Trigger manual scan |
| `POST` | `/api/monitor/start` | Start continuous monitoring |
| `POST` | `/api/monitor/stop` | Stop monitoring |

## Important Gotchas

1. **Stock codes are 6 digits only** - No exchange prefix (use "600519", not "sh600519")
2. **Market codes**: "sh" for Shanghai, "sz" for Shenzhen
3. **Trading hours**: 09:30-11:30, 13:00-15:00 China time
4. **Weight threshold**: Default 5% (`strategy.min_weight`) - hardcoded policy
5. **Rate limiting**: `strategy.scan_interval` (default 120s) prevents API bans

## Extension Points

1. **New data source**: Implement interface in `backend/data/sources/`, register in fetcher
2. **New signal evaluator**: Add to `backend/strategy/signal_evaluators.py`, register in `SignalEvaluatorFactory`
3. **New notification channel**: Implement `ISignalSender` in `backend/notification/sender.py`
4. **New API endpoint**: Add route in `backend/api/app.py`

## Design Patterns Used

- **Strategy Pattern**: `signal_evaluators.py` - Different evaluation strategies
- **Factory Pattern**: `SignalEvaluatorFactory`, data source factories
- **Repository Pattern**: `DBSignalRepository` - Signal persistence (SQLite)
- **Dependency Injection**: All monitor dependencies injected via constructor
- **Adapter Pattern**: Multiple data sources with unified interface
- **Singleton**: `get_api_state_manager()` for state management
