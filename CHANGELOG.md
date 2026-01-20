# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-20

### Added
- **Structured logging system** - JSON format log output for better log analysis
  - Console output with color-coded, human-readable format
  - Separate error log file (`logs/app_error.log`)
  - Automatic log rotation (100MB) and retention (30 days)
- **Modular configuration system** - Split `config/` into separate modules:
  - `config/logger.py` - `LoggerSettings`, `LoggerManager`
  - `config/strategy.py` - `StrategySettings`, `TradingHours`, `RiskControlSettings`
  - `config/alert.py` - `AlertSettings`, `DingTalkSettings`, `EmailSettings`, `WeChatWorkSettings`
  - `config/__init__.py` - Unified `Config` class and `get()` function

### Changed
- **Config management** - Replace dict-based configuration with type-safe dataclasses
  - `LimitUpMonitor` now accepts `Config` object instead of file path
  - `create_sender()` renamed from `create_sender_from_config()` with typed parameter
  - All config access now uses property notation (e.g., `config.strategy.min_weight`)
- Remove hardcoded default values from `LimitUpMonitor`
- Remove internal config loading methods (`_load_config`, `_load_watch_stocks`, `_get_watch_etf_codes`)

### Removed
- `backend/logger_config.py` - Replaced by `config/logger.py`

## [0.1.0] - 2025-12-XX

### Added
- Multi-source data fetching with automatic fallback
- Real-time A-share and ETF quote monitoring
- Limit-up stock detection and ETF arbitrage signal generation
- Notification channels (DingTalk, Email, WeChat Work)
- Web dashboard for signal monitoring

### Performance
- A-share quote fetching speed improved by 30x through multi-source strategy
- Limit-up stock loading optimized with quote cache reuse
- Homepage loading speed improved

### Fixed
- Stock price display when market is closed
- Associated ETF list filtering (only ETFs with >=5% holdings)
- Table styling optimization

[Unreleased]: https://github.com/bleakplain/etf-arb-tracker/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/bleakplain/etf-arb-tracker/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bleakplain/etf-arb-tracker/releases/tag/v0.1.0
