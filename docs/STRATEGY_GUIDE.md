# 策略扩展指南

本文档详细介绍如何为 ETF 套利追踪系统添加新的交易策略。

## 目录

1. [概述](#概述)
2. [策略类型](#策略类型)
3. [创建新策略](#创建新策略)
4. [策略注册](#策略注册)
5. [策略配置](#策略配置)
6. [测试策略](#测试策略)
7. [最佳实践](#最佳实践)
8. [示例](#示例)

---

## 概述

系统采用插件式架构，所有策略通过装饰器自动注册到全局注册表。添加新策略无需修改核心代码，只需：

1. 创建策略类并实现相应接口
2. 使用 `@register` 装饰器注册策略
3. 实现策略逻辑
4. 编写测试验证功能

---

## 策略类型

系统支持三种策略类型：

### 1. 事件检测策略 (IEventDetector)

检测市场中的套利机会事件，如涨停、突破等。

**接口定义**：`backend/arbitrage/cn/strategies/interfaces.py`

```python
class IEventDetector(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @abstractmethod
    def detect(self, quote: Dict) -> Optional[MarketEvent]:
        """检测单个证券的市场事件"""
        pass

    @abstractmethod
    def is_valid(self, event: MarketEvent) -> bool:
        """验证事件是否有效"""
        pass

    @classmethod
    def from_config(cls, config: Optional[Dict] = None) -> 'IEventDetector':
        """从配置创建策略实例"""
        return cls(**(config or {}))
```

### 2. 基金选择策略 (IFundSelector)

从符合条件的 ETF 中选择最优的一个。

```python
class IFundSelector(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @abstractmethod
    def select(
        self,
        eligible_funds: List[CandidateETF],
        event: MarketEvent
    ) -> Optional[CandidateETF]:
        """从符合条件的基金中选择最优的"""
        pass

    @abstractmethod
    def get_selection_reason(self, fund: CandidateETF) -> str:
        """获取选择原因说明"""
        pass
```

### 3. 信号过滤策略 (ISignalFilter)

对生成的信号进行过滤验证。

```python
class ISignalFilter(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @property
    @abstractmethod
    def is_required(self) -> bool:
        """是否必须执行"""
        pass

    @abstractmethod
    def filter(
        self,
        event: MarketEvent,
        fund: CandidateETF,
        signal: TradingSignal
    ) -> Tuple[bool, str]:
        """
        过滤信号
        Returns:
            (是否通过, 原因说明)
        """
        pass
```

---

## 创建新策略

### 步骤 1：创建策略文件

在相应市场目录下创建策略文件：

```bash
# A股策略
backend/arbitrage/cn/strategies/event_detectors/my_detector.py
backend/arbitrage/cn/strategies/fund_selectors/my_selector.py
backend/arbitrage/cn/strategies/signal_filters/my_filter.py
```

### 步骤 2：实现策略类

```python
"""
自定义事件检测策略
"""

from typing import Dict, Optional
from backend.arbitrage.cn.strategies.interfaces import IEventDetector
from backend.arbitrage.strategy_registry import event_detector_registry
from backend.market.events import MarketEvent

@event_detector_registry.register(
    "my_custom_detector",
    priority=100,
    description="我的自定义检测策略",
    version="1.0.0"
)
class MyCustomDetector(IEventDetector):
    """自定义事件检测器"""

    def __init__(self, threshold: float = 0.05):
        """
        初始化检测器

        Args:
            threshold: 检测阈值，默认5%
        """
        self._threshold = threshold

    @property
    def strategy_name(self) -> str:
        return "my_custom_detector"

    def detect(self, quote: Dict) -> Optional[MarketEvent]:
        """
        检测市场事件

        Args:
            quote: 股票行情数据

        Returns:
            MarketEvent 或 None
        """
        change_pct = quote.get('change_pct', 0)

        # 检测是否超过阈值
        if abs(change_pct) >= self._threshold:
            return MarketEvent(
                code=quote['code'],
                name=quote['name'],
                price=quote['price'],
                change_pct=change_pct,
                timestamp=quote.get('timestamp', '')
            )

        return None

    def is_valid(self, event: MarketEvent) -> bool:
        """验证事件有效性"""
        return event.change_pct != 0

    @classmethod
    def from_config(cls, config: Optional[Dict] = None) -> 'MyCustomDetector':
        """从配置创建实例"""
        config = config or {}
        return cls(threshold=config.get('threshold', 0.05))
```

---

## 策略注册

使用装饰器自动注册策略：

```python
@event_detector_registry.register(
    "strategy_name",           # 策略唯一标识符
    priority=100,              # 优先级（越高越优先）
    description="策略描述",    # 人类可读描述
    version="1.0.0"            # 版本号
)
class MyStrategy(IEventDetector):
    pass
```

### 注册表参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | str | 策略唯一标识符，用于配置文件引用 |
| `priority` | int | 优先级，越高越优先（默认0） |
| `description` | str | 策略描述，用于文档和日志 |
| `version` | str | 策略版本号（默认"1.0.0"） |

---

## 策略配置

### 1. 创建配置对象

```python
from backend.arbitrage.config import ArbitrageEngineConfig

config = ArbitrageEngineConfig(
    event_detector="my_custom_detector",     # 使用自定义检测器
    fund_selector="highest_weight",           # 使用现有选择器
    signal_filters=["time_filter_cn"],        # 使用现有过滤器
    event_config={
        "threshold": 0.08                     # 自定义参数
    }
)
```

### 2. 验证配置

```python
# 验证策略是否存在
is_valid, errors = config.validate()
if not is_valid:
    for error in errors:
        print(f"配置错误: {error}")

# 或直接断言（失败时抛出异常）
config.assert_valid()
```

### 3. 使用配置创建引擎

```python
from backend.arbitrage.cn.arbitrage_engine import ArbitrageEngineCN

engine = ArbitrageEngineCN(
    quote_fetcher=my_fetcher,
    etf_holder_provider=my_holder,
    etf_holdings_provider=my_holdings,
    etf_quote_provider=my_quote_provider,
    engine_config=config  # 使用自定义配置
)
```

---

## 测试策略

### 单元测试

```python
import pytest
from backend.arbitrage.cn.strategies.event_detectors.my_detector import MyCustomDetector

@pytest.mark.unit
class TestMyCustomDetector:
    """测试自定义检测器"""

    def test_detect_event_above_threshold(self):
        """测试检测超过阈值的事件"""
        detector = MyCustomDetector(threshold=0.05)

        quote = {
            'code': '600519',
            'name': '贵州茅台',
            'price': 1800.0,
            'change_pct': 0.06,  # 6% > 5%
            'timestamp': '14:30:00'
        }

        event = detector.detect(quote)
        assert event is not None
        assert event.code == '600519'

    def test_detect_event_below_threshold(self):
        """测试检测低于阈值的事件"""
        detector = MyCustomDetector(threshold=0.05)

        quote = {
            'code': '600519',
            'name': '贵州茅台',
            'price': 1800.0,
            'change_pct': 0.03,  # 3% < 5%
            'timestamp': '14:30:00'
        }

        event = detector.detect(quote)
        assert event is None

    def test_from_config(self):
        """测试从配置创建"""
        config = {'threshold': 0.08}
        detector = MyCustomDetector.from_config(config)
        assert detector._threshold == 0.08
```

### 集成测试

```python
@pytest.mark.integration
class TestMyStrategyIntegration:
    """集成测试"""

    def test_strategy_in_engine_workflow(self):
        """测试策略在引擎工作流中的表现"""
        from backend.arbitrage.cn.factory import ArbitrageEngineFactory

        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=["600519"],
            engine_config=ArbitrageEngineConfig(
                event_detector="my_custom_detector",
                event_config={"threshold": 0.05}
            )
        )

        # 执行扫描
        result = engine.scan_all()
        assert result is not None
```

---

## 最佳实践

### 1. 命名规范

- **类名**：描述性名称 + 类型后缀
  - `MyCustomDetector`、`BestLiquiditySelector`
- **文件名**：小写下划线分隔
  - `my_detector.py`、`best_liquidity_selector.py`
- **策略名**：小写下划线 + 市场后缀
  - `my_detector_cn`、`time_filter_cn`

### 2. 错误处理

```python
def detect(self, quote: Dict) -> Optional[MarketEvent]:
    try:
        change_pct = quote.get('change_pct', 0)
        # 检测逻辑...
    except KeyError as e:
        logger.warning(f"行情数据缺失字段: {e}")
        return None
    except Exception as e:
        logger.error(f"检测失败: {e}")
        return None
```

### 3. 配置验证

```python
def __init__(self, threshold: float = 0.05):
    if not 0 < threshold < 1:
        raise ValueError(f"阈值必须在0-1之间: {threshold}")
    self._threshold = threshold
```

### 4. 文档字符串

```python
def detect(self, quote: Dict) -> Optional[MarketEvent]:
    """
    检测价格异动事件

    当股票价格变动超过指定阈值时触发事件。

    Args:
        quote: 股票行情数据，必须包含以下字段:
            - code: 股票代码
            - name: 股票名称
            - price: 当前价格
            - change_pct: 涨跌幅（小数形式）

    Returns:
        MarketEvent 如果检测到事件，否则返回 None

    Example:
        >>> detector = MyCustomDetector(threshold=0.05)
        >>> event = detector.detect({'code': '600519', 'change_pct': 0.06})
        >>> assert event is not None
    """
```

### 5. 日志记录

```python
from loguru import logger

def detect(self, quote: Dict) -> Optional[MarketEvent]:
    event = self._do_detect(quote)
    if event:
        logger.info(
            f"[{self.strategy_name}] 检测到事件: "
            f"{event.code} 涨幅 {event.change_pct:.2%}"
        )
    return event
```

---

## 示例

### 完整示例：港股突破检测器

```python
"""
港股突破检测策略

检测价格突破阻力位的港股。
"""

from typing import Dict, Optional
from loguru import logger

from backend.arbitrage.hk.strategies.interfaces import IEventDetector
from backend.arbitrage.strategy_registry import event_detector_registry
from backend.market.events import MarketEvent


@event_detector_registry.register(
    "breakout_hk",
    priority=100,
    description="港股突破检测策略",
    version="1.0.0"
)
class BreakoutDetectorHK(IEventDetector):
    """港股突破检测器"""

    def __init__(
        self,
        resistance_days: int = 20,
        breakout_threshold: float = 0.02
    ):
        """
        初始化检测器

        Args:
            resistance_days: 阻力位计算天数
            breakout_threshold: 突破确认阈值
        """
        self._resistance_days = resistance_days
        self._breakout_threshold = breakout_threshold

    @property
    def strategy_name(self) -> str:
        return "breakout_hk"

    def detect(self, quote: Dict) -> Optional[MarketEvent]:
        """
        检测突破事件

        Args:
            quote: 包含以下字段的字典:
                - code: 股票代码
                - name: 股票名称
                - price: 当前价格
                - high_20d: 20日最高价
                - volume: 成交量

        Returns:
            MarketEvent 或 None
        """
        try:
            price = quote.get('price', 0)
            high_20d = quote.get('high_20d', 0)

            if not price or not high_20d:
                return None

            # 计算突破幅度
            breakout_pct = (price - high_20d) / high_20d

            # 确认突破
            if breakout_pct >= self._breakout_threshold:
                logger.info(
                    f"[{self.strategy_name}] {quote['code']} "
                    f"突破 {high_20d:.2f} → {price:.2f} "
                    f"(+{breakout_pct:.2%})"
                )

                return MarketEvent(
                    code=quote['code'],
                    name=quote['name'],
                    price=price,
                    change_pct=breakout_pct,
                    timestamp=quote.get('timestamp', ''),
                    metadata={
                        'resistance_level': high_20d,
                        'breakout_pct': breakout_pct
                    }
                )

        except Exception as e:
            logger.error(f"[{self.strategy_name}] 检测失败: {e}")

        return None

    def is_valid(self, event: MarketEvent) -> bool:
        """验证事件有效性"""
        # 检查是否有成交量的配合
        volume = event.metadata.get('volume', 0) if event.metadata else 0
        return volume > 0

    @classmethod
    def from_config(cls, config: Optional[Dict] = None) -> 'BreakoutDetectorHK':
        """从配置创建实例"""
        config = config or {}
        return cls(
            resistance_days=config.get('resistance_days', 20),
            breakout_threshold=config.get('breakout_threshold', 0.02)
        )
```

### 使用示例

```python
# 1. 创建配置
config = ArbitrageEngineConfig(
    event_detector="breakout_hk",
    fund_selector="highest_weight",
    event_config={
        "resistance_days": 20,
        "breakout_threshold": 0.02
    }
)

# 2. 验证配置
config.assert_valid()

# 3. 创建引擎
engine = ArbitrageEngineHK(
    quote_fetcher=hk_fetcher,
    etf_holder_provider=hk_holder,
    etf_holdings_provider=hk_holdings,
    etf_quote_provider=hk_quote,
    engine_config=config
)

# 4. 执行扫描
result = engine.scan_all()
```

---

## 调试技巧

### 查看已注册策略

```python
from backend.arbitrage.strategy_registry import (
    event_detector_registry,
    fund_selector_registry,
    signal_filter_registry,
)

# 列出所有已注册策略
print("事件检测器:", event_detector_registry.list_names())
print("基金选择器:", fund_selector_registry.list_names())
print("信号过滤器:", signal_filter_registry.list_names())

# 获取策略元数据
metadata = event_detector_registry.get_metadata("limit_up_cn")
print(metadata)
# {
#     'priority': 100,
#     'description': 'A股涨停检测策略',
#     'version': '1.0.0',
#     'class_name': 'LimitUpDetectorCN',
#     'module': 'backend.arbitrage.cn.strategies.event_detectors.limit_up'
# }
```

### 策略日志

```python
from loguru import logger

# 添加详细日志
logger.add("strategy_debug.log", level="DEBUG")

# 运行引擎
engine.scan_all()

# 检查日志文件
# cat strategy_debug.log
```

---

## 常见问题

### Q: 策略没有生效？

A: 检查以下几点：
1. 策略是否正确注册（查看注册表）
2. 配置文件中策略名称是否正确
3. 策略优先级是否过低
4. 策略参数是否有效

### Q: 如何动态切换策略？

A: 使用配置对象：
```python
# 创建不同配置
config_a = ArbitrageEngineConfig(event_detector="detector_a")
config_b = ArbitrageEngineConfig(event_detector="detector_b")

# 创建不同引擎
engine_a = ArbitrageEngineCN(..., engine_config=config_a)
engine_b = ArbitrageEngineCN(..., engine_config=config_b)
```

### Q: 策略如何访问历史数据？

A: 通过 provider 注入：
```python
def __init__(self, data_provider=None):
    self._data_provider = data_provider

def detect(self, quote):
    # 使用 provider 获取历史数据
    history = self._data_provider.get_history(quote['code'], days=20)
```

---

## 参考资源

- **接口定义**：`backend/arbitrage/cn/strategies/interfaces.py`
- **现有策略**：`backend/arbitrage/cn/strategies/`
- **注册表实现**：`backend/utils/plugin_registry.py`
- **测试示例**：`tests/unit/test_market_strategies_cn.py`
