# A股ETF套利策略可扩展性设计文档

**日期**: 2025-02-21
**目标**: 实现策略可插拔架构，支持扩展至美股、港股等市场

---

## 一、当前架构问题分析

### 1.1 硬编码的业务逻辑

| 组件 | 硬编码内容 | 位置 | 扩展性评分 |
|------|----------|------|-----------|
| 涨停判断 | `is_limit_up()` 函数 | `data/utils.py:47-69` | 2/10 |
| ETF分类 | 宽基/科技/消费列表 | `etf_selector.py:221-236` | 3/10 |
| ETF选择 | `eligible_etfs[0]` | `signal_generator.py:76` | 4/10 |
| 时间检查 | `hour=15` 硬编码 | `signal_evaluators.py:127` | 5/10 |

### 1.2 当前流程

```
股票行情 → is_limit_up(硬编码) → ETF筛选(部分配置) → 选最高权重(固定) → 信号生成
              ↑ 问题                  ↑ 问题                ↑ 问题
         A股专用逻辑            分类硬编码              选择逻辑单一
```

### 1.3 扩展到美股/港股的障碍

| 市场 | 涨停机制 | 交易时间 | 币种 | 代码规则 |
|------|---------|---------|------|---------|
| A股 | 10%/20%/30% | 9:30-15:00 | CNY | 6位数字 |
| 美股 | 无涨停/熔断机制 | 21:30-04:00(EST) | USD | 字母+数字 |
| 港股 | 无涨跌幅限制 | 9:30-16:00 | HKD | 5位数字/4位数字 |

**结论**: 当前代码中A股特定的逻辑阻碍了多市场扩展。

---

## 二、策略可插拔架构设计

### 2.1 核心接口

```python
# backend/domain/strategy_interfaces.py

class IEventDetectorStrategy(ABC):
    """事件检测策略 - 检测套利机会事件"""
    def detect(quote: Dict) -> Optional[EventInfo]

class IFundSelectionStrategy(ABC):
    """基金选择策略 - 从候选中选择最优"""
    def select(eligible_funds: List[ETFReference], event: EventInfo) -> Optional[ETFReference]

class ISignalFilterStrategy(ABC):
    """信号过滤策略 - 过滤不符合条件的信号"""
    def should_filter(event: EventInfo, fund: ETFReference, signal: TradingSignal) -> tuple[bool, str]
```

### 2.2 策略链架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    ArbitrageEngine (套利引擎)                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              StrategyChain (策略链)                       │    │
│  │                                                           │    │
│  │  配置:                                                     │    │
│  │  event_detector: "limit_up"     # 可选: breakout, squeeze │    │
│  │  fund_selector: "highest_weight" # 可选: best_liquidity   │    │
│  │  signal_filters:                  # 可组合多个             │    │
│  │    - time_filter                                              │    │
│  │    - liquidity_filter                                        │    │
│  │    - risk_filter                                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  执行流程:                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │EventDetector │→ │FundSelector  │→ │SignalFilters │          │
│  │(可插拔策略)   │  │(可插拔策略)   │  │(可插拔策略)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 策略注册表

```python
# backend/core/strategy_registry.py (新增)

event_detector_registry = PluginRegistry("EventDetector")
fund_selector_registry = PluginRegistry("FundSelector")
signal_filter_registry = PluginRegistry("SignalFilter")
```

---

## 三、A股策略实现（向后兼容）

### 3.1 事件检测策略

```python
# backend/strategies/event_detectors.py

@event_detector_registry.register(
    "limit_up",
    priority=100,
    description="A股涨停检测策略"
)
class LimitUpEventDetector(IEventDetectorStrategy):
    """涨停事件检测器"""

    def detect(self, quote: Dict) -> Optional[EventInfo]:
        if not quote.get('is_limit_up'):
            return None

        return EventInfo(
            event_type="limit_up",
            security_code=quote['code'],
            security_name=quote['name'],
            price=quote['price'],
            change_pct=quote['change_pct'],
            trigger_price=quote['price'],
            trigger_time=quote.get('timestamp', ''),
            volume=quote.get('volume', 0),
            amount=quote.get('amount', 0)
        )

    def is_valid(self, event: EventInfo) -> bool:
        # 可配置的验证逻辑
        return event.change_pct >= 0.095
```

### 3.2 基金选择策略

```python
# backend/strategies/fund_selectors.py

@fund_selector_registry.register(
    "highest_weight",
    priority=100,
    description="选择权重最高的ETF"
)
class HighestWeightStrategy(IFundSelectionStrategy):
    """最高权重选择策略"""

    def select(self, eligible_funds: List[ETFReference], event: EventInfo) -> Optional[ETFReference]:
        if not eligible_funds:
            return None
        # 按权重降序排序，选择第一个
        return sorted(eligible_funds, key=lambda x: x.weight, reverse=True)[0]

    def get_selection_reason(self, fund: ETFReference) -> str:
        return f"权重最高({fund.weight_pct:.2f}%)"
```

### 3.3 信号过滤策略

```python
# backend/strategies/signal_filters.py

@signal_filter_registry.register(
    "time_filter",
    priority=100,
    description="时间过滤（距收盘时间检查）"
)
class TimeFilterStrategy(ISignalFilterStrategy):
    """时间过滤器"""

    def __init__(self, min_time_to_close: int = 1800):
        self.min_time_to_close = min_time_to_close

    def should_filter(self, event: EventInfo, fund: ETFReference, signal: TradingSignal) -> tuple[bool, str]:
        time_to_close = self._get_time_to_close()
        if 0 < time_to_close < self.min_time_to_close:
            return True, f"距收盘仅{time_to_close//60}分钟，时间不足"
        return False, ""

    @property
    def is_required(self) -> bool:
        return True  # 时间过滤是必需的
```

---

## 四、配置文件设计

### 4.1 策略配置 (config/strategies.yaml)

```yaml
# 策略链配置
strategy_chain:
  # 事件检测策略
  event_detector: "limit_up"
  event_config:
    min_change_pct: 0.095

  # 基金选择策略
  fund_selector: "highest_weight"
  fund_config:
    min_weight: 0.05

  # 信号过滤策略（按顺序执行）
  signal_filters:
    - name: "time_filter"
      config:
        min_time_to_close: 1800  # 30分钟
    - name: "liquidity_filter"
      config:
        min_volume: 50000000  # 5000万元
    - name: "risk_filter"
      config:
        max_top10_ratio: 0.70
```

### 4.2 市场配置 (config/markets.yaml)

```yaml
# 市场配置
markets:
  cn:  # A股
    trading_hours:
      morning:
        start: "09:30"
        end: "11:30"
      afternoon:
        start: "13:00"
        end: "15:00"
    currency: "CNY"
    limit_rules:
      default: 0.10      # 10%
      star: 0.20         # 科创板 20%
      chi_next: 0.20     # 创业板 20%
      bse: 0.30          # 北交所 30%

  us:  # 美股
    trading_hours:
      regular:
        start: "09:30"
        end: "16:00"
      after_hours:
        start: "16:00"
        end: "20:00"
    currency: "USD"
    limit_rules:
      circuit_breaker: [0.07, 0.13, 0.20]  # 熔断阈值

  hk:  # 港股
    trading_hours:
      morning:
        start: "09:30"
        end: "12:00"
      afternoon:
        start: "13:00"
        end: "16:00"
    currency: "HKD"
    limit_rules: null  # 无涨跌幅限制
```

---

## 五、扩展到美股/港股

### 5.1 美股突破策略示例

```python
# backend/strategies/us/event_detectors.py

@event_detector_registry.register(
    "us_breakout",
    priority=50,
    description="美股突破策略"
)
class USBreakoutEventDetector(IEventDetectorStrategy):
    """美股突破检测器"""

    def __init__(self, breakout_pct: float = 0.10):
        self.breakout_pct = breakout_pct

    def detect(self, quote: Dict) -> Optional[EventInfo]:
        change_pct = quote.get('change_pct', 0)
        if change_pct < self.breakout_pct:
            return None

        return EventInfo(
            event_type="breakout",
            security_code=quote['symbol'],
            security_name=quote['name'],
            price=quote['price'],
            change_pct=change_pct,
            trigger_price=quote.get('prev_close', 0) * (1 + self.breakout_pct),
            trigger_time=quote.get('timestamp'),
            metadata={'market': 'US'}
        )

    def is_valid(self, event: EventInfo) -> bool:
        # 突破后回调不超过2%
        return True
```

### 5.2 配置示例

```yaml
# config/us_strategy.yaml
strategy_chain:
  event_detector: "us_breakout"
  event_config:
    breakout_pct: 0.10  # 突破10%

  fund_selector: "best_liquidity"  # 选择流动性最好的
  fund_config:
    min_daily_volume: 1000000  # 100万美元

  signal_filters:
    - name: "time_filter"
      config:
        min_time_to_close: 3600  # 1小时
    - name: "us_trading_hours_filter"
      config:
        market: "US"
```

---

## 六、实现计划

### Phase 1: 接口和注册表（当前）
- [x] 创建策略接口定义
- [ ] 创建策略注册表
- [ ] 更新 domain/__init__.py

### Phase 2: A股策略迁移
- [ ] 实现 LimitUpEventDetector
- [ ] 实现 HighestWeightStrategy
- [ ] 实现 TimeFilterStrategy
- [ ] 实现 LiquidityFilterStrategy
- [ ] 保持向后兼容

### Phase 3: 引擎重构
- [ ] 创建 ArbitrageEngine
- [ ] 重构 LimitUpMonitor 使用策略链
- [ ] 配置文件支持

### Phase 4: 美股/港股支持
- [ ] 实现美股突破策略
- [ ] 实现港股策略
- [ ] 市场配置支持
- [ ] 文档更新

---

## 七、使用示例

### 添加自定义策略

```python
# 1. 创建自定义事件检测器
from backend.domain.strategy_interfaces import IEventDetectorStrategy, EventInfo
from backend.core.registry import event_detector_registry

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

# 2. 配置使用
# config/strategies.yaml
strategy_chain:
  event_detector: "my_breakout"  # 使用自定义策略
```

### 组合多个过滤条件

```yaml
strategy_chain:
  event_detector: "limit_up"
  fund_selector: "highest_weight"
  signal_filters:
    - name: "time_filter"
      config:
        min_time_to_close: 1800
    - name: "liquidity_filter"
      config:
        min_volume: 50000000
    - name: "my_custom_filter"  # 自定义过滤器
      config:
        my_param: 100
```

---

## 八、优势总结

| 特性 | 当前架构 | 新架构 |
|------|---------|--------|
| 添加新事件类型 | 修改核心代码 | 实现接口+注册 |
| 添加选择策略 | 修改核心代码 | 实现接口+注册 |
| 添加过滤条件 | 修改核心代码 | 实现接口+注册 |
| 多市场支持 | A股硬编码 | 配置驱动 |
| 策略组合 | 不支持 | 完全支持 |
| 测试隔离 | 困难 | 策略独立可测 |
