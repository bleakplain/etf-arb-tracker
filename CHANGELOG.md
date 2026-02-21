# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **插件注册表系统 (Plugin Registry)**
  - `backend/core/registry.py` - 通用插件注册表类，支持装饰器注册
  - `backend/core/plugin_manager.py` - 插件管理工具和查询接口
  - `backend/core/__init__.py` - 核心基础设施模块
  - 支持信号评估器、通知渠道的插件式扩展
  - 无需修改工厂代码即可添加新的插件类型
  - 提供插件元数据管理（名称、版本、优先级、描述）
- **API端点**
  - `GET /api/plugins` - 列出所有已注册插件
  - `GET /api/plugins/stats` - 获取插件统计信息
- **文档**
  - `docs/plugin-system.md` - 插件系统完整使用指南

### Changed
- **通知系统重构**
  - 移除钉钉、邮件、企业微信通知实现
  - 默认使用 `LogSender` 输出信号到日志
  - 提供 `NullSender` 用于禁用通知
  - 用户可通过插件注册表自定义通知方式
- **策略层**
  - `SignalEvaluatorFactory` 现在使用插件注册表动态获取评估器
  - 支持通过装饰器 `@evaluator_registry.register()` 自定义评估器
- **命名重构**
  - `LimitUpInfo` → `LimitUpStock` (领域实体)
  - `StockInfo` → `StockQuote` (领域值对象)
  - `StockInfo` → `StockQuoteResponse` (API模型)
  - `ETFInfo` → `ETFQuoteResponse` (API模型)
- **配置简化**
  - `config/alert.py` - 简化为仅包含 `enabled` 标志
  - `config/settings.yaml` - 移除通知渠道详细配置

### Removed
- 钉钉通知实现 (`DingTalkSender`)
- 邮件通知实现 (`EmailSender`)
- 企业微信通知实现 (`WeChatWorkSender`)
- **领域层 (Domain Layer)**
  - `backend/domain/interfaces.py` - 7个业务接口定义（IQuoteFetcher, IETFHolderProvider等）
  - `backend/domain/value_objects.py` - 值对象（StockQuote, ETFReference, TradingSignal等）
  - `backend/domain/models.py` - 领域模型（LimitUpStock）
- **基础设施层 (Infrastructure Layer)**
  - `backend/infrastructure/cache/ttl_cache.py` - 可复用的TTL缓存组件
  - 支持懒加载、自动过期、统计信息、LRU淘汰策略
- **策略组件重构**
  - `backend/strategy/limit_checker.py` - 涨停检查器（~70行）
  - `backend/strategy/etf_selector.py` - ETF选择器（~170行）
  - `backend/strategy/signal_generator.py` - 信号生成器（~110行）
  - `backend/strategy/signal_repository.py` - 信号仓储（~70行）
  - `backend/strategy/limit_monitor.py` - 重构为协调器模式（~300行）
- **API状态管理**
  - `backend/api/state.py` - API状态管理器（MonitorState, APIStateManager）
  - 消除全局变量，提供线程安全的状态管理
- **缓存适配器**
  - `backend/data/cache_adapter.py` - 使用TTLCache的缓存适配器

### Changed
- **架构重构** - 参考《重构》方法进行系统性重构
  - 最大类从567行减少到300行（↓47%）
  - 消除3个全局变量（-100%）
  - 减少约300行重复缓存代码（-67%）
- **依赖倒置** - 高层模块依赖接口而非具体实现
- **单一职责** - 每个类只负责一个明确的业务功能
- **线程安全** - 状态管理器和缓存组件都是线程安全的
- **可测试性** - 通过依赖注入和接口抽象提升可测试性

### Fixed
- 修复API层全局状态导致的测试困难问题
- 修复重复缓存逻辑导致的维护困难问题

## [0.3.0] - 2026-01-21

### Added
- **统一列名映射** (`backend/data/column_mappings.py`)
  - 集中管理所有数据源的列名转换规则
  - 支持 `TENCENT_COLUMN_MAPPING`, `SINA_COLUMN_MAPPING`, `TUSHARE_COLUMN_MAPPING`
- **通用解析器模块** (`backend/data/parsers.py`)
  - `parse_quote_row()` - 统一的行情行解析函数
  - `batch_parse_quotes()` - 批量解析行情数据
  - `add_limit_flags()` - 自动添加涨跌停标记
- **信号评估器模块** (`backend/strategy/signal_evaluators.py`)
  - 使用策略模式实现多种评估算法
  - `DefaultSignalEvaluator` - 默认评估器
  - `ConservativeEvaluator` - 保守型评估器（更严格标准）
  - `AggressiveEvaluator` - 激进型评估器（更宽松标准）
  - `SignalEvaluatorFactory` - 评估器工厂类
- **数据源评分配置** (`ScoringConfig`)
  - 可配置的成功率、速度、优先级权重
  - 可调整的速度评分参数
- **信号评估配置** (`SignalEvaluationConfig`)
  - 可配置的置信度阈值（权重、排名）
  - 可配置的风险阈值（时间、集中度）
- **缓存配置类** (`CacheConfig`)
  - 统一的缓存参数配置

### Changed
- **数据源代码简化**
  - 三个数据源文件使用统一的列名映射
  - 减少 200-300 行重复代码
- **行情模块重构**
  - `stock_quote.py` 和 `etf_quote.py` 使用通用解析器
  - 简化 `_parse_stock_row` 和 `_parse_etf_row` 方法
- **监控器改进**
  - `LimitUpMonitor` 支持可配置的评估器类型
  - 信号评估逻辑提取到独立的评估器类
- **配置系统增强**
  - `config/settings.yaml` 新增 `signal_evaluation` 配置段
  - `Config` 类新增 `signal_evaluation` 属性

### Fixed
- 修复行情数据解析中 `data_source` 字段缺失的问题
- 确保所有解析后的数据都包含数据源标识

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

[Unreleased]: https://github.com/bleakplain/etf-arb-tracker/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/bleakplain/etf-arb-tracker/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bleakplain/etf-arb-tracker/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bleakplain/etf-arb-tracker/releases/tag/v0.1.0
