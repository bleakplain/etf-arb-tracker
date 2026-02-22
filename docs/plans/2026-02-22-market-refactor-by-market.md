# Market 模块按市场拆分重构 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 market 模块按市场（cn/hk/us）拆分，去掉 DDD 分层，参考 arbitrage 的简单结构

**Architecture:** 保持顶层通用文件（events基类、interfaces、models），将A股特定实现移至 cn/ 目录，hk/us 作为框架目录

**Tech Stack:** Python 3.12+, pytest

---

## Task 1: 创建新的顶层通用文件结构

**Files:**
- Create: `backend/market/events.py`
- Create: `backend/market/interfaces.py`
- Create: `backend/market/models.py`
- Modify: `backend/market/__init__.py`

**Step 1: 创建 backend/market/events.py（通用事件基类）**

```python
"""
市场事件基类 - 跨市场通用
"""

from abc import ABC, abstractmethod
from typing import Dict


class MarketEvent(ABC):
    """市场事件基类"""

    @property
    @abstractmethod
    def event_type(self) -> str:
        """事件类型"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict:
        """转换为字典"""
        pass
```

**Step 2: 创建 backend/market/interfaces.py（通用接口）**

```python
"""
市场数据接口 - 跨市场通用
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass


class IQuoteFetcher(ABC):
    """行情数据获取接口"""

    @abstractmethod
    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取单个股票行情"""
        pass

    @abstractmethod
    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情"""
        pass


class IHoldingProvider(ABC):
    """持仓数据提供接口"""

    @abstractmethod
    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """获取ETF前十大持仓"""
        pass

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """加载证券-ETF映射关系"""
        pass

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """保存证券-ETF映射关系"""
        pass

    def build_stock_etf_mapping(self, stock_codes: List[str], etf_codes: List[str]) -> Dict:
        """构建证券-ETF映射关系"""
        pass
```

**Step 3: 创建 backend/market/models.py（通用模型）**

```python
"""
市场数据模型 - 跨市场通用
"""

from dataclasses import dataclass
from typing import Dict
from enum import Enum


class ETFCategory(Enum):
    """ETF类别"""
    BROAD_INDEX = "broad_index"
    SECTOR = "sector"
    THEME = "theme"
    STRATEGY = "strategy"
    OTHER = "other"


@dataclass
class StockQuote:
    """股票行情"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float = 0
    amount: float = 0
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'volume': self.volume,
            'amount': self.amount,
            'timestamp': self.timestamp
        }


@dataclass
class ETFQuote:
    """ETF行情"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float = 0
    premium: float = 0
    timestamp: str = ""


@dataclass
class Holding:
    """ETF持仓"""
    stock_code: str
    stock_name: str
    weight: float
    rank: int = -1
```

**Step 4: 更新 backend/market/__init__.py（临时导出）**

```python
"""市场模块 - 行情数据"""

# 通用导出（临时，保持向后兼容）
from backend.market.events import MarketEvent
from backend.market.interfaces import IQuoteFetcher, IHoldingProvider
from backend.market.models import ETFCategory, StockQuote, ETFQuote, Holding

__all__ = [
    'MarketEvent',
    'IQuoteFetcher',
    'IHoldingProvider',
    'ETFCategory',
    'StockQuote',
    'ETFQuote',
    'Holding',
]
```

**Step 5: 运行测试验证**

```bash
source venv/bin/activate && python -c "from backend.market import MarketEvent; print('OK')"
```

Expected: 输出 "OK"，无导入错误

**Step 6: 提交**

```bash
git add backend/market/events.py backend/market/interfaces.py backend/market/models.py backend/market/__init__.py
git commit -m "refactor(market): 创建顶层通用文件结构"
```

---

## Task 2: 创建 cn/ 目录结构并迁移A股特定代码

**Files:**
- Create: `backend/market/cn/__init__.py`
- Create: `backend/market/cn/events.py`
- Create: `backend/market/cn/models.py`
- Create: `backend/market/cn/quote_fetcher.py`
- Create: `backend/market/cn/etf_quote.py`
- Create: `backend/market/cn/holding_provider.py`
- Create: `backend/market/cn/sources/__init__.py`

**Step 1: 创建 backend/market/cn/events.py（A股事件）**

从 `backend/market/domain/events.py` 提取 A股特定事件：

```python
"""
A股市场事件
"""

from dataclasses import dataclass
from backend.market.events import MarketEvent


@dataclass
class LimitUpEvent(MarketEvent):
    """
    涨停事件 - A股涨停套利的核心事件

    业务含义：股票价格达到当日涨幅限制（主板10%，创业板20%）

    特有属性：
    - limit_time: 涨停时间
    - seal_amount: 封单金额（未成交的卖出委托金额）
    - open_count: 打开次数（"炸板"次数）
    """
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    limit_time: str
    seal_amount: float = 0
    open_count: int = 0
    is_first_limit: bool = True
    timestamp: str = ""

    @property
    def event_type(self) -> str:
        return "limit_up"

    def to_dict(self) -> dict:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'price': self.price,
            'change_pct': self.change_pct,
            'limit_time': self.limit_time,
            'seal_amount': self.seal_amount,
            'open_count': self.open_count,
            'is_first_limit': self.is_first_limit,
            'timestamp': self.timestamp
        }
```

**Step 2: 创建 backend/market/cn/models.py（A股模型）**

从 `backend/market/domain/models.py` 提取 A股特定模型：

```python
"""
A股市场模型
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class LimitUpStock:
    """涨停股票实体"""
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    limit_time: str
    seal_amount: float = 0
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return {
            'code': self.stock_code,
            'name': self.stock_name,
            'price': self.price,
            'time': self.limit_time,
            'change_pct': self.change_pct
        }
```

**Step 3: 创建 backend/market/cn/quote_fetcher.py（A股行情获取）**

整合 `backend/market/infrastructure/stock_quote.py` 和 `backend/market/infrastructure/limit_up_stocks.py`：

```python
"""
A股行情数据获取
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from backend.market.interfaces import IQuoteFetcher
from backend.market.cn.models import LimitUpStock


class CNQuoteFetcher(IQuoteFetcher):
    """A股行情数据获取器"""

    def __init__(self):
        self._tencent_source = None

    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取单个股票行情"""
        source = self._get_tencent_source()
        return source.get_quote(code)

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情"""
        source = self._get_tencent_source()
        return source.get_batch_quotes(codes)

    def _get_tencent_source(self):
        """获取腾讯数据源"""
        if self._tencent_source is None:
            from backend.market.cn.sources.tencent_source import TencentSource
            self._tencent_source = TencentSource()
        return self._tencent_source

    def get_today_limit_ups(self) -> List[Dict]:
        """获取今日涨停股票"""
        source = self._get_tencent_source()
        return source.get_limit_ups()
```

**Step 4: 创建 backend/market/cn/sources/ 目录和文件**

创建目录并移动数据源文件：

```bash
mkdir -p backend/market/cn/sources
```

将 `backend/market/infrastructure/sources/tencent_source.py` 内容复制到 `backend/market/cn/sources/tencent_source.py`，类名改为 `TencentSource`。

将 `backend/market/infrastructure/sources/eastmoney_source.py` 内容复制到 `backend/market/cn/sources/eastmoney_source.py`，类名改为 `EastMoneySource`。

将 `backend/market/infrastructure/sources/tushare_source.py` 内容复制到 `backend/market/cn/sources/tushare_source.py`。

**Step 5: 创建 backend/market/cn/etf_quote.py**

```python
"""
A股ETF行情数据获取
"""

from typing import Optional, Dict
from loguru import logger


class CNETFQuoteFetcher:
    """A股ETF行情获取器"""

    def get_etf_quote(self, code: str) -> Optional[Dict]:
        """获取ETF行情"""
        # 实现逻辑
        pass

    def get_etf_batch_quotes(self, codes: list) -> Dict[str, Optional[Dict]]:
        """批量获取ETF行情"""
        # 实现逻辑
        pass
```

**Step 6: 创建 backend/market/cn/holding_provider.py**

```python
"""
A股持仓数据提供
"""

from typing import Optional, Dict, List
from loguru import logger


class CNHoldingProvider:
    """A股持仓数据提供器"""

    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """获取ETF前十大持仓"""
        # 实现逻辑
        pass
```

**Step 7: 创建 __init__.py 文件**

创建 `backend/market/cn/__init__.py`:

```python
"""A股市场模块"""

from backend.market.cn.events import LimitUpEvent
from backend.market.cn.models import LimitUpStock
from backend.market.cn.quote_fetcher import CNQuoteFetcher
from backend.market.cn.etf_quote import CNETFQuoteFetcher
from backend.market.cn.holding_provider import CNHoldingProvider

__all__ = [
    'LimitUpEvent',
    'LimitUpStock',
    'CNQuoteFetcher',
    'CNETFQuoteFetcher',
    'CNHoldingProvider',
]
```

创建 `backend/market/cn/sources/__init__.py`:

```python
"""A股数据源"""
```

**Step 8: 运行测试验证**

```bash
source venv/bin/activate && python -c "from backend.market.cn import LimitUpEvent; print('CN OK')"
```

Expected: 输出 "CN OK"

**Step 9: 提交**

```bash
git add backend/market/cn/
git commit -m "refactor(market): 创建cn目录，迁移A股特定代码"
```

---

## Task 3: 创建 hk/ 和 us/ 框架目录

**Files:**
- Create: `backend/market/hk/__init__.py`
- Create: `backend/market/hk/events.py`
- Create: `backend/market/hk/quote_fetcher.py`
- Create: `backend/market/hk/sources/__init__.py`
- Create: `backend/market/us/__init__.py`
- Create: `backend/market/us/events.py`
- Create: `backend/market/us/quote_fetcher.py`
- Create: `backend/market/us/sources/__init__.py`

**Step 1: 创建 backend/market/hk/__init__.py**

```python
"""港股市场模块（框架）"""

from backend.market.hk.events import BreakoutEvent
from backend.market.hk.quote_fetcher import HKQuoteFetcher

__all__ = [
    'BreakoutEvent',
    'HKQuoteFetcher',
]
```

**Step 2: 创建 backend/market/hk/events.py**

```python
"""
港股市场事件
"""

from dataclasses import dataclass
from backend.market.events import MarketEvent


@dataclass
class BreakoutEvent(MarketEvent):
    """
    突破事件 - 港股市场

    业务含义：股票价格突破关键阻力位
    """
    stock_code: str
    stock_name: str
    price: float
    change_pct: float
    breakout_level: float
    timestamp: str = ""

    @property
    def event_type(self) -> str:
        return "breakout"

    def to_dict(self) -> dict:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'price': self.price,
            'change_pct': self.change_pct,
            'breakout_level': self.breakout_level,
            'timestamp': self.timestamp
        }
```

**Step 3: 创建 backend/market/hk/quote_fetcher.py**

```python
"""
港股行情数据获取（框架）
"""

from typing import List, Dict, Optional
from backend.market.interfaces import IQuoteFetcher


class HKQuoteFetcher(IQuoteFetcher):
    """港股行情数据获取器（框架）"""

    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取单个股票行情（待实现）"""
        raise NotImplementedError("港股行情获取待实现")

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情（待实现）"""
        raise NotImplementedError("港股行情获取待实现")
```

**Step 4: 创建 hk/sources/__init__.py**

```bash
mkdir -p backend/market/hk/sources
```

```python
"""港股数据源（框架）"""
```

**Step 5: 创建 us/ 目录结构（类似 hk）**

创建 `backend/market/us/__init__.py`, `events.py`, `quote_fetcher.py`, `sources/__init__.py`，内容类似 hk 但使用美股事件类型。

**Step 6: 运行测试验证**

```bash
source venv/bin/activate && python -c "from backend.market.hk import HKQuoteFetcher; from backend.market.us import USQuoteFetcher; print('HK/US OK')"
```

Expected: 输出 "HK/US OK"

**Step 7: 提交**

```bash
git add backend/market/hk/ backend/market/us/
git commit -m "refactor(market): 创建hk和us框架目录"
```

---

## Task 4: 更新主 market/__init__.py 导出

**Files:**
- Modify: `backend/market/__init__.py`

**Step 1: 更新 backend/market/__init__.py**

```python
"""市场模块 - 按市场拆分的行情数据"""

# 通用接口和模型
from backend.market.events import MarketEvent
from backend.market.interfaces import IQuoteFetcher, IHoldingProvider
from backend.market.models import ETFCategory, StockQuote, ETFQuote, Holding

# A股
from backend.market.cn import LimitUpEvent, LimitUpStock, CNQuoteFetcher

# 港股
from backend.market.hk import BreakoutEvent, HKQuoteFetcher

# 美股
from backend.market.us import MomentumEvent, USQuoteFetcher

__all__ = [
    # 通用
    'MarketEvent',
    'IQuoteFetcher',
    'IHoldingProvider',
    'ETFCategory',
    'StockQuote',
    'ETFQuote',
    'Holding',
    # A股
    'LimitUpEvent',
    'LimitUpStock',
    'CNQuoteFetcher',
    # 港股
    'BreakoutEvent',
    'HKQuoteFetcher',
    # 美股
    'MomentumEvent',
    'USQuoteFetcher',
]
```

**Step 2: 运行测试验证**

```bash
source venv/bin/activate && python -c "from backend.market import LimitUpEvent, HKQuoteFetcher; print('All OK')"
```

Expected: 输出 "All OK"

**Step 3: 提交**

```bash
git add backend/market/__init__.py
git commit -m "refactor(market): 更新主__init__.py导出"
```

---

## Task 5: 删除旧的 domain/ 和 infrastructure/ 目录

**Files:**
- Remove: `backend/market/domain/`
- Remove: `backend/market/infrastructure/`

**Step 1: 删除旧目录**

```bash
rm -rf backend/market/domain/ backend/market/infrastructure/
```

**Step 2: 运行测试验证**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过（如果有错误，需要修复导入路径）

**Step 3: 提交**

```bash
git add backend/market/
git commit -m "refactor(market): 删除旧的domain和infrastructure目录"
```

---

## Task 6: 修复导入路径和引用

**Files:**
- Modify: 所有引用旧 market 模块路径的文件

**Step 1: 搜索并修复导入**

查找所有需要修复的导入：

```bash
grep -r "from backend.market.domain" --include="*.py" backend/ tests/
grep -r "from backend.market.infrastructure" --include="*.py" backend/ tests/
```

根据搜索结果，逐个修复导入路径：
- `backend.market.domain.events` → `backend.market.events` 或 `backend.market.cn.events`
- `backend.market.domain.interfaces` → `backend.market.interfaces`
- `backend.market.domain.models` → `backend.market.models` 或 `backend.market.cn.models`
- `backend.market.domain.value_objects` → `backend.market.models`
- `backend.market.infrastructure.*` → `backend.market.cn.*`

**Step 2: 运行测试验证**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过

**Step 3: 提交**

```bash
git add backend/ tests/
git commit -m "refactor(market): 修复导入路径"
```

---

## Task 7: 最终验证

**Files:**
- Check: 所有导入和引用

**Step 1: 验证目录结构**

```bash
find backend/market -type f -name "*.py" | grep -v __pycache__ | sort
```

Expected输出：
```
backend/market/cn/events.py
backend/market/cn/etf_quote.py
backend/market/cn/holding_provider.py
backend/market/cn/models.py
backend/market/cn/quote_fetcher.py
backend/market/cn/sources/tencent_source.py
backend/market/cn/sources/eastmoney_source.py
...
```

**Step 2: 验证导入**

```bash
source venv/bin/activate && python -c "
from backend.market import MarketEvent, IQuoteFetcher
from backend.market.cn import LimitUpEvent, CNQuoteFetcher
from backend.market.hk import HKQuoteFetcher
from backend.market.us import USQuoteFetcher
print('All imports OK')
"
```

Expected: 输出 "All imports OK"

**Step 3: 运行完整测试**

```bash
source venv/bin/activate && python tests/test_arbitrage_engine.py
```

Expected: 所有测试通过

**Step 4: 提交最终变更**

```bash
git add .
git commit -m "refactor(market): 完成按市场拆分重构"
```

---

## 最终结构

```
market/
├── events.py                  # 通用事件基类
├── interfaces.py              # 通用接口
├── models.py                  # 通用模型
├── cn/                        # A股市场
│   ├── events.py              # LimitUpEvent
│   ├── models.py              # LimitUpStock
│   ├── quote_fetcher.py       # CNQuoteFetcher
│   ├── etf_quote.py
│   ├── holding_provider.py
│   └── sources/               # A股数据源
│       ├── tencent_source.py
│       ├── eastmoney_source.py
│       └── tushare_source.py
├── hk/                        # 港股市场（框架）
│   ├── events.py              # BreakoutEvent
│   ├── quote_fetcher.py       # HKQuoteFetcher
│   └── sources/
└── us/                        # 美股市场（框架）
    ├── events.py              # MomentumEvent
    ├── quote_fetcher.py       # USQuoteFetcher
    └── sources/
```
