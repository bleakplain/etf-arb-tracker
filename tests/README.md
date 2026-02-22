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

| 市场模块 | 测试文件 | 测试数 | 状态 |
|---------|---------|-------|------|
| **CN (A股)** | test_arbitrage_engine_cn.py | 9 | ✓ 完整 |
| | test_market_strategies_cn.py | 6 | ✓ 完整 |
| | test_backtest_cn.py | 11 | ✓ 完整 |
| **HK (港股)** | test_market_hk.py | 3 | 框架 |
| | test_backtest_hk.py | 1 | 框架 |
| **US (美股)** | test_market_us.py | 3 | 框架 |
| | test_backtest_us.py | 1 | 框架 |
| **跨市场** | test_signal_evaluator.py | 14 | ✓ 完整 |
| | test_utils.py | 29 | ✓ 完整 |

## 待补充测试

- [ ] API端点集成测试
- [ ] 信号管理器测试
- [ ] 信号仓储测试
- [ ] 港股/美股功能测试（待实现功能）
- [ ] 边界条件和错误处理测试
