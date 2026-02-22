# 统一命名风格 - 市场后缀重命名 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重命名引擎类和策略类，统一使用市场后缀格式（CN/HK/US）

**Architecture:** 批量重命名类、注册名称和导入引用，确保测试通过

**Tech Stack:** Python 3.12+, pytest

---

## Task 1: 重命名 A股引擎类 CNStockArbitrageEngine → ArbitrageEngineCN

**Files:**
- Modify: `backend/arbitrage/cn/arbitrage_engine.py:57`
- Modify: `backend/arbitrage/cn/__init__.py:7`
- Modify: `backend/arbitrage/__init__.py:30,35`
- Modify: `tests/test_arbitrage_engine.py:19`

**Step 1: 修改 cn/arbitrage_engine.py 类名**

将第57行的类名从 `CNStockArbitrageEngine` 改为 `ArbitrageEngineCN`:

```python
class ArbitrageEngineCN:
    """
    A股套利引擎

    专门处理A股市场的涨停套利机会。
    当股票涨停时，通过买入包含该股票的ETF来获取套利机会。
    """
```

**Step 2: 修改 cn/__init__.py 导入**

更新 `backend/arbitrage/cn/__init__.py`:

```python
from backend.arbitrage.cn.arbitrage_engine import ArbitrageEngineCN, ScanResult

__all__ = [
    'ArbitrageEngineCN',
    'ScanResult',
    'ArbitrageEngineConfig',
]
```

**Step 3: 修改主 arbitrage/__init__.py 导入**

更新 `backend/arbitrage/__init__.py`:

```python
from backend.arbitrage.cn import ArbitrageEngineCN

# 向后兼容：默认使用A股引擎
ArbitrageEngine = ArbitrageEngineCN
```

**Step 4: 修改测试文件**

更新 `tests/test_arbitrage_engine.py`:

```python
from backend.arbitrage.cn import ArbitrageEngineCN as ArbitrageEngine, ScanResult
```

**Step 5: 运行测试验证**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过

**Step 6: 提交**

```bash
git add backend/arbitrage/cn/arbitrage_engine.py backend/arbitrage/cn/__init__.py backend/arbitrage/__init__.py tests/test_arbitrage_engine.py
git commit -m "refactor: 重命名 CNStockArbitrageEngine → ArbitrageEngineCN"
```

---

## Task 2: 重命名港股引擎类 HKStockArbitrageEngine → ArbitrageEngineHK

**Files:**
- Modify: `backend/arbitrage/hk/arbitrage_engine.py:15`
- Modify: `backend/arbitrage/hk/__init__.py:6`
- Modify: `backend/arbitrage/__init__.py:31`

**Step 1: 修改 hk/arbitrage_engine.py 类名**

将第15行的类名从 `HKStockArbitrageEngine` 改为 `ArbitrageEngineHK`:

```python
class ArbitrageEngineHK:
    """
    港股套利引擎

    港股市场套利框架（待实现）
    """
```

**Step 2: 修改 hk/__init__.py 导入**

更新 `backend/arbitrage/hk/__init__.py`:

```python
from backend.arbitrage.hk.arbitrage_engine import ArbitrageEngineHK

__all__ = ['ArbitrageEngineHK']
```

**Step 3: 修改主 arbitrage/__init__.py 导入**

更新 `backend/arbitrage/__init__.py`:

```python
from backend.arbitrage.hk import ArbitrageEngineHK
```

**Step 4: 运行测试验证**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过

**Step 5: 提交**

```bash
git add backend/arbitrage/hk/arbitrage_engine.py backend/arbitrage/hk/__init__.py backend/arbitrage/__init__.py
git commit -m "refactor: 重命名 HKStockArbitrageEngine → ArbitrageEngineHK"
```

---

## Task 3: 重命名美股引擎类 USStockArbitrageEngine → ArbitrageEngineUS

**Files:**
- Modify: `backend/arbitrage/us/arbitrage_engine.py:15`
- Modify: `backend/arbitrage/us/__init__.py:6`
- Modify: `backend/arbitrage/__init__.py:32`

**Step 1: 修改 us/arbitrage_engine.py 类名**

将第15行的类名从 `USStockArbitrageEngine` 改为 `ArbitrageEngineUS`:

```python
class ArbitrageEngineUS:
    """
    美股套利引擎

    美股市场套利框架（待实现）
    """
```

**Step 2: 修改 us/__init__.py 导入**

更新 `backend/arbitrage/us/__init__.py`:

```python
from backend.arbitrage.us.arbitrage_engine import ArbitrageEngineUS

__all__ = ['ArbitrageEngineUS']
```

**Step 3: 修改主 arbitrage/__init__.py 导入**

更新 `backend/arbitrage/__init__.py`:

```python
from backend.arbitrage.us import ArbitrageEngineUS
```

**Step 4: 运行测试验证**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过

**Step 5: 提交**

```bash
git add backend/arbitrage/us/arbitrage_engine.py backend/arbitrage/us/__init__.py backend/arbitrage/__init__.py
git commit -m "refactor: 重命名 USStockArbitrageEngine → ArbitrageEngineUS"
```

---

## Task 4: 重命名A股事件检测器 LimitUpDetector → LimitUpDetectorCN

**Files:**
- Modify: `backend/arbitrage/cn/strategies/event_detectors/limit_up.py:28`
- Modify: `backend/arbitrage/cn/strategies/event_detectors/__init__.py:3`
- Modify: `backend/arbitrage/cn/strategies/__init__.py`
- Modify: `tests/test_arbitrage_engine.py:16`

**Step 1: 修改 limit_up.py 类名和注册名称**

更新 `backend/arbitrage/cn/strategies/event_detectors/limit_up.py`:

```python
@event_detector_registry.register(
    "limit_up_cn",  # 改为 limit_up_cn
    priority=100,
    description="A股涨停检测策略",
    version="1.0.0"
)
class LimitUpDetectorCN(IEventDetector):
    """
    A股涨停事件检测器
    """
```

**Step 2: 修改 cn/strategies/event_detectors/__init__.py**

更新 `backend/arbitrage/cn/strategies/event_detectors/__init__.py`:

```python
"""A股事件检测策略包"""

from backend.arbitrage.cn.strategies.event_detectors.limit_up import LimitUpDetectorCN

__all__ = ['LimitUpDetectorCN']
```

**Step 3: 修改 cn/strategies/__init__.py（如果有导出）**

检查并更新 `backend/arbitrage/cn/strategies/__init__.py`，如果有导出则需要更新。

**Step 4: 修改测试文件导入**

更新 `tests/test_arbitrage_engine.py`:

```python
from backend.arbitrage.cn.strategies.event_detectors import LimitUpDetectorCN
```

**Step 5: 更新 cn/arbitrage_engine.py 中的默认配置**

更新 `backend/arbitrage/cn/arbitrage_engine.py` 中 `_get_default_config()` 方法:

```python
def _get_default_config(self) -> ArbitrageEngineConfig:
    return ArbitrageEngineConfig(
        event_detector="limit_up_cn",  # 改为 limit_up_cn
        ...
    )
```

**Step 6: 运行测试验证**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过

**Step 7: 提交**

```bash
git add backend/arbitrage/cn/strategies/event_detectors/limit_up.py backend/arbitrage/cn/strategies/event_detectors/__init__.py backend/arbitrage/cn/arbitrage_engine.py tests/test_arbitrage_engine.py
git commit -m "refactor: 重命名 LimitUpDetector → LimitUpDetectorCN，注册名改为 limit_up_cn"
```

---

## Task 5: 重命名A股时间过滤器 CNTimeFilter → TimeFilterCN

**Files:**
- Modify: `backend/arbitrage/cn/strategies/signal_filters/time_filter.py:17`
- Modify: `backend/arbitrage/cn/strategies/signal_filters/__init__.py:3`

**Step 1: 修改 time_filter.py 类名和注册名称**

更新 `backend/arbitrage/cn/strategies/signal_filters/time_filter.py`:

```python
@signal_filter_registry.register(
    "time_filter_cn",  # 改为 time_filter_cn
    priority=100,
    description="A股时间过滤（距收盘时间检查）",
    version="1.0.0"
)
class TimeFilterCN(ISignalFilter):
    """
    A股时间过滤器

    检查距离A股收盘的时间（15:00），避免在收盘前太短时间内发出信号。
    """
```

同时更新 `_get_time_to_close` 方法的文档注释，确保没有使用旧的类名引用。

**Step 2: 修改 cn/strategies/signal_filters/__init__.py**

更新 `backend/arbitrage/cn/strategies/signal_filters/__init__.py`:

```python
"""A股信号过滤策略包"""

from backend.arbitrage.cn.strategies.signal_filters.time_filter import TimeFilterCN
from backend.arbitrage.cn.strategies.signal_filters.liquidity import LiquidityFilter
from backend.arbitrage.cn.strategies.signal_filters.confidence import ConfidenceFilter
from backend.arbitrage.cn.strategies.signal_filters.risk import RiskFilter

__all__ = [
    'TimeFilterCN',
    'LiquidityFilter',
    'ConfidenceFilter',
    'RiskFilter',
]
```

**Step 3: 更新 cn/arbitrage_engine.py 中的默认配置**

更新 `backend/arbitrage/cn/arbitrage_engine.py` 中 `_get_default_config()` 方法:

```python
def _get_default_config(self) -> ArbitrageEngineConfig:
    return ArbitrageEngineConfig(
        event_detector="limit_up_cn",
        fund_selector="highest_weight",
        signal_filters=["time_filter_cn", "liquidity_filter"],  # 改为 time_filter_cn
        event_config={'min_change_pct': 0.095},
        fund_config={'min_weight': 0.05},
        filter_configs={
            'time_filter_cn': {'min_time_to_close': 1800},  # 改为 time_filter_cn
            'liquidity_filter': {'min_daily_amount': 50000000}
        }
    )
```

**Step 4: 运行测试验证**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过

**Step 5: 提交**

```bash
git add backend/arbitrage/cn/strategies/signal_filters/time_filter.py backend/arbitrage/cn/strategies/signal_filters/__init__.py backend/arbitrage/cn/arbitrage_engine.py
git commit -m "refactor: 重命名 CNTimeFilter → TimeFilterCN，注册名改为 time_filter_cn"
```

---

## Task 6: 最终验证和文档更新

**Files:**
- Check: 所有导入和引用

**Step 1: 全量搜索验证旧类名**

搜索确保没有遗漏的旧类名引用：

```bash
grep -r "CNStockArbitrageEngine" --include="*.py" backend/ tests/
grep -r "HKStockArbitrageEngine" --include="*.py" backend/ tests/
grep -r "USStockArbitrageEngine" --include="*.py" backend/ tests/
grep -r "LimitUpDetector[^C]" --include="*.py" backend/ tests/
grep -r "CNTimeFilter" --include="*.py" backend/ tests/
```

Expected: 没有结果（除了可能的注释）

**Step 2: 运行完整测试**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过

**Step 3: 提交最终变更**

如果有任何遗漏，修复后提交：

```bash
git add .
git commit -m "refactor: 完成命名风格统一，全部使用市场后缀"
```

---

## 测试验证

每个任务完成后运行：
```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

所有任务完成后，确认：
- [ ] 引擎类：`ArbitrageEngineCN`, `ArbitrageEngineHK`, `ArbitrageEngineUS`
- [ ] 策略类：`LimitUpDetectorCN`, `TimeFilterCN`
- [ ] 注册名：`limit_up_cn`, `time_filter_cn`
- [ ] 所有测试通过
- [ ] 无旧类名残留引用
