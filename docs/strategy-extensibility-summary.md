# A股ETF套利策略可扩展性 - 总结文档

## 概述

本文档总结了A股ETF套利策略可扩展性分析和设计方案。

## 问题分析

### 当前架构问题

| 问题 | 位置 | 影响 |
|------|------|------|
| 涨停判断硬编码 | `backend/data/utils.py:47` | 无法扩展到其他事件类型 |
| ETF分类硬编码 | `backend/strategy/etf_selector.py:221-236` | 新增类别需改代码 |
| ETF选择固定 | `backend/strategy/signal_generator.py:76` | 仅支持权重最高的选择 |
| A股特定逻辑 | 分散在多处 | 无法支持美股/港股 |

### 扩展性评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 事件检测 | 2/10 | 硬编码在 utils.py |
| ETF筛选 | 5/10 | 部分可配置 |
| ETF选择 | 4/10 | 逻辑固定 |
| 信号过滤 | 6/10 | 部分可配置 |
| 信号评估 | 9/10 | 已实现插件化 |
| **总体** | **5.2/10** | 需要引入策略抽象层 |

## 解决方案

### 核心接口设计

```
backend/domain/strategy_interfaces.py
├── IEventDetectorStrategy    # 事件检测策略接口
├── IFundSelectionStrategy    # 基金选择策略接口
├── ISignalFilterStrategy     # 信号过滤策略接口
├── EventInfo                 # 事件信息值对象
└── StrategyChainConfig       # 策略链配置
```

### 策略注册表

```
backend/core/strategy_registry.py
├── event_detector_registry   # 事件检测策略注册表
├── fund_selector_registry    # 基金选择策略注册表
├── signal_filter_registry    # 信号过滤策略注册表
└── StrategyManager           # 策略管理器
```

### 新增API端点

```
GET /api/strategies           # 列出所有策略
GET /api/strategies/validate  # 验证策略链
```

## 实现计划

### Phase 1: 接口和注册表 ✅
- [x] 创建策略接口定义
- [x] 创建策略注册表
- [x] 添加API端点
- [x] 更新文档

### Phase 2: A股策略迁移 (待实现)
- [ ] 实现LimitUpEventDetector
- [ ] 实现HighestWeightStrategy
- [ ] 实现TimeFilterStrategy
- [ ] 实现LiquidityFilterStrategy
- [ ] 保持向后兼容

### Phase 3: 引擎重构 (待实现)
- [ ] 创建ArbitrageEngine
- [ ] 重构LimitUpMonitor使用策略链
- [ ] 配置文件支持

### Phase 4: 美股/港股支持 (待实现)
- [ ] 实现美股突破策略
- [ ] 实现港股策略
- [ ] 市场配置支持

## 使用示例

### 添加自定义事件检测器

```python
from backend.domain.strategy_interfaces import IEventDetectorStrategy, EventInfo
from backend.core.strategy_registry import event_detector_registry

@event_detector_registry.register(
    "my_breakout",
    priority=50,
    description="我的突破策略"
)
class MyBreakoutDetector(IEventDetectorStrategy):
    def detect(self, quote: Dict) -> Optional[EventInfo]:
        # 实现检测逻辑
        pass

    def is_valid(self, event: EventInfo) -> bool:
        # 实现验证逻辑
        pass
```

### 配置使用

```yaml
# config/strategies.yaml
strategy_chain:
  event_detector: "my_breakout"
  fund_selector: "highest_weight"
  signal_filters:
    - "time_filter"
    - "liquidity_filter"
```

## 文件清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/domain/strategy_interfaces.py` | 策略接口定义 |
| `backend/core/strategy_registry.py` | 策略注册表 |
| `docs/strategy-extensibility-design.md` | 完整设计文档 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/domain/__init__.py` | 导出策略接口 |
| `backend/core/__init__.py` | 导出策略注册表 |
| `backend/api/app.py` | 添加策略API端点 |

## 下一步行动

1. **实现A股策略** - 将现有逻辑迁移到策略接口
2. **配置文件支持** - 支持 strategy_chain 配置
3. **向后兼容测试** - 确保现有功能不受影响
4. **文档更新** - 更新使用指南

## 参考资料

- 完整设计文档: `docs/strategy-extensibility-design.md`
- 插件系统文档: `docs/plugin-system.md`
