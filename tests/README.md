# 测试目录结构

本目录包含ETF套利监控系统的所有测试代码。

## 目录结构

```
tests/
├── __init__.py
├── conftest.py                 # pytest配置和共享fixtures
├── fixtures/                   # 测试工具和Mock类
│   └── mocks.py               # 可复用的Mock实现
├── integration/                # 集成测试（待添加）
└── unit/                       # 单元测试
    ├── test_arbitrage_engine_cn.py   # A股套利引擎测试
    ├── test_backtest_cn.py            # A股回测测试
    ├── test_backtest_hk.py            # 港股回测测试（框架）
    ├── test_backtest_us.py            # 美股回测测试（框架）
    ├── test_market_strategies_cn.py  # A股市场策略测试
    ├── test_market_hk.py              # 港股市场测试（框架）
    ├── test_market_us.py              # 美股市场测试（框架）
    ├── test_signal_evaluator.py      # 信号评估器测试（跨市场）
    └── test_utils.py                  # 工具函数测试（跨市场）
```

## 命名约定

### 测试文件命名

- **市场特定模块**: 使用 `_cn`、`_hk`、`_us` 后缀
  - `test_arbitrage_engine_cn.py` - A股套利引擎
  - `test_market_strategies_cn.py` - A股市场策略
  - `test_backtest_cn.py` - A股回测

- **跨市场模块**: 不使用市场后缀
  - `test_signal_evaluator.py` - 信号评估器（通用）
  - `test_utils.py` - 工具函数（通用）

### 测试类命名

- 使用 `Test{ClassName}` 格式
- 例如: `TestArbitrageEngineCN`, `TestTTLCache`

### 测试函数命名

- 使用 `test_{what_is_tested}` 格式
- 例如: `test_detect_limit_up_stock`, `test_cache_expiration`

## 运行测试

```bash
# 运行所有单元测试
pytest tests/unit/

# 运行特定市场的测试
pytest tests/unit/test_*_cn.py

# 运行特定模块的测试
pytest tests/unit/test_arbitrage_engine_cn.py

# 生成覆盖率报告
pytest tests/unit/ --cov=backend --cov-report=html

# 只运行标记的测试
pytest -m "not slow"
```

## 测试标记

- `unit` - 单元测试（快速，隔离）
- `integration` - 集成测试（较慢，可能使用外部服务）
- `slow` - 慢速测试（运行时间 > 1秒）
- `api` - API端点测试
- `market` - 市场数据测试
- `backtest` - 回测测试
- `signal` - 信号生成测试
- `arbitrage` - 套利引擎测试

## 当前测试覆盖

### 单元测试 (272个 - 全部通过)

| 测试模块 | 测试文件 | 测试数 | 状态 |
|---------|---------|-------|------|
| **引擎测试** | test_arbitrage_engine_cn.py | 9 | ✅ 完整 |
| **市场策略** | test_market_strategies_cn.py | 6 | ✅ 完整 |
| **回测** | test_backtest_cn.py | 11 | ✅ 完整 |
| **信号评估** | test_signal_evaluator.py | 14 | ✅ 完整 |
| **信号过滤** | test_signal_filters_cn.py | 24 | ✅ 完整 |
| **信号管理** | test_signal_manager.py | 9 | ✅ 完整 |
| **信号发送** | test_signal_sender.py | 20 | ✅ 完整 |
| **数据源** | test_etf_holding_provider_cn.py | 4 | ✅ 完整 |
| | test_etf_quote_cn.py | 9 | ✅ 完整 |
| | test_quote_fetcher_cn.py | 4 | ✅ 完整 |
| **仓储** | test_db_repositories.py | 18 | ✅ 完整 |
| | test_memory_repository.py | 27 | ✅ 完整 |
| | test_mapping_repository.py | 34 | ✅ 完整 |
| **API状态** | test_api_state.py | 16 | ✅ 完整 |
| **模块导入** | test_module_imports.py | 12 | ✅ 完整 |
| **配置** | test_config_validation.py | 9 | ✅ 完整 |
| **工具** | test_utils.py | 56 | ✅ 完整 |

### 集成测试 (32个)

| 测试模块 | 测试文件 | 测试数 | 状态 |
|---------|---------|-------|------|
| **API路由** | test_api_routes.py | 18 | ✅ 完整 (1个需重构) |
| **套利工作流** | test_arbitrage_workflow.py | 14 | ✅ 完整 |

**完整测试结果**: 31/32 通过 (96.9%)
**运行耗时**: ~121秒 (2分钟)

**已知问题**:
- `test_start_monitor_endpoint` - 需要重构，添加超时或mock机制

## 待补充测试

- [ ] 港股/美股功能测试（待实现功能）
- [ ] 集成测试性能优化 (当前每个测试30-60秒)
- [ ] 端到端完整流程测试（实际服务器启动）

## 测试同步状态 (2026-02-25)

### 已验证 ✅
- **单元测试**: 272个测试全部通过
- **测试用例**: 与代码实现同步
- **测试覆盖**: 核心功能覆盖完整

### 已知问题 ⚠️
1. **test_start_monitor_endpoint**: 测试会实际启动监控服务，需要重构
   - 建议: 添加超时机制或使用mock

2. **集成测试性能**: 完整运行约需2分钟
   - 原因: FastAPI TestClient开销
   - 建议: 使用共享fixtures或mock减少初始化开销

3. **测试依赖**: httpx必须安装才能运行集成测试
   - 状态: 已在requirements.txt中包含
   - 建议: 添加CI依赖检查

### 测试用例清单

#### 单元测试 (tests/unit/)
- `test_api_state.py` - API状态管理 (16个测试)
- `test_arbitrage_engine_cn.py` - A股套利引擎 (9个测试)
- `test_backtest_cn.py` - A股回测 (11个测试)
- `test_config_validation.py` - 配置验证 (9个测试)
- `test_db_repositories.py` - 数据库仓储 (18个测试)
- `test_etf_holding_provider_cn.py` - ETF持仓数据源 (4个测试)
- `test_etf_quote_cn.py` - ETF行情 (9个测试)
- `test_mapping_repository.py` - 股票-ETF映射仓储 (34个测试)
- `test_market_strategies_cn.py` - A股市场策略 (6个测试)
- `test_memory_repository.py` - 内存仓储 (27个测试)
- `test_module_imports.py` - 模块导入 (12个测试)
- `test_quote_fetcher_cn.py` - 行情获取器 (4个测试)
- `test_signal_evaluator.py` - 信号评估器 (14个测试)
- `test_signal_filters_cn.py` - 信号过滤器 (24个测试)
- `test_signal_manager.py` - 信号管理器 (9个测试)
- `test_signal_sender.py` - 信号发送器 (20个测试)
- `test_utils.py` - 工具函数 (56个测试)

#### 集成测试 (tests/integration/)
- `test_api_routes.py` - API路由集成测试 (18个测试)
  - 健康检查、状态查询
  - 自选股管理
  - 股票行情、相关ETF
  - 信号列表、ETF分类
  - 回测API
  - 监控控制API
  - 配置管理API
- `test_arbitrage_workflow.py` - 套利工作流集成测试 (14个测试)
  - 端到端涨停套利流程
  - 信号生成工作流
  - 策略过滤工作流
  - 多股票批量扫描
  - 基金选择优先级
  - 错误处理工作流
  - 信号持久化工作流
  - 基于时间的工作流
  - 配置工作流
