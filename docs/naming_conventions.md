# Naming Conventions

本文档定义了项目中的命名约定，确保代码风格一致。

## 变量命名

### ETF相关命名

| 上下文 | 参数名/变量名 | 说明 |
|--------|---------------|------|
| 类型为 `CandidateETF` 时 | `candidate_etf` | 清晰表达这是一个候选ETF对象 |
| 类型为 `str`（ETF代码）时 | `etf_code` | ETF代码字符串 |
| 多个ETF的列表 | `eligible_funds` / `candidate_etfs` | 符合条件的ETF列表 |
| 选中的ETF | `selected_fund` / `selected_etf` | 最终选择的ETF |

**示例**：
```python
# 推荐：新代码使用 candidate_etf
def get_selection_reason(self, candidate_etf: CandidateETF) -> str:
    return f"{candidate_etf.etf_name} 权重达 {candidate_etf.weight_pct:.2f}%"

# 现有代码可保持 fund 兼容性
def get_selection_reason(self, fund: CandidateETF) -> str:
    return f"{fund.etf_name} 权重达 {fund.weight_pct:.2f}%"
```

### 股票相关命名

| 上下文 | 参数名/变量名 | 说明 |
|--------|---------------|------|
| 股票代码（字符串） | `stock_code` / `code` | 6位数字代码 |
| 股票名称（字符串） | `stock_name` / `name` | 股票名称 |
| Stock对象 | `stock` | 股票实体对象 |

### 信号相关命名

| 上下文 | 参数名/变量名 | 说明 |
|--------|---------------|------|
| TradingSignal对象 | `signal` | 交易信号对象 |
| MarketEvent对象 | `event` / `market_event` | 市场事件对象 |

## 类命名

### 实体类
- 使用名词单数形式：`TradingSignal`, `LimitUpEvent`, `CandidateETF`
- 避免缩写，完整单词：`Holdings` 而非 `Hld`

### 策略类
- 以功能结尾：`HighestWeightSelector`, `TimeFilter`, `LimitUpDetector`
- 市场特定类添加后缀：`LimitUpDetectorCN`, `TimeFilterCN`

### 仓储类
- 接口以 `I` 开头：`IStockETFMappingRepository`, `ISignalRepository`
- 实现类添加存储类型：`DBSignalRepository`, `InMemorySignalRepository`

## 方法命名

### CRUD操作
| 操作 | 方法名 | 返回值 |
|------|--------|--------|
| 创建 | `create_*` / `save_*` | 创建的对象 / bool |
| 读取 | `get_*` / `find_*` / `fetch_*` | 对象 / None |
| 更新 | `update_*` / `modify_*` | bool / 更新后的对象 |
| 删除 | `delete_*` / `remove_*` | bool |

### 查询操作
| 操作 | 方法名 | 返回值 |
|------|--------|--------|
| 获取单个 | `get_*` / `find_*` | 对象 / None |
| 获取列表 | `get_all_*` / `list_*` / `find_*` | 列表 |
| 检查存在 | `has_*` / `exists_*` | bool |
| 计数 | `count_*` / `get_*_count` | int |

**示例**：
```python
def get_etf_list(self, stock_code: str) -> List[Dict]:
    """获取包含指定股票的ETF列表"""

def has_stock(self, stock_code: str) -> bool:
    """检查映射中是否包含指定股票"""

def get_all_stocks(self) -> List[str]:
    """获取所有已映射的股票代码列表"""
```

### 布尔方法
- 以 `is_` 开头：`is_valid`, `is_trading_time`, `is_required`
- 使用 `has_` 表示拥有：`has_stock`, `has_mapping`
- 使用 `can_` 表示能力：`can_execute`, `can_filter`

### 工厂方法
- 以 `create_*` 命名：`create_monitor`, `create_evaluator`
- 以 `from_*` 命名（类方法）：`from_dict`, `from_config`, `from_quote`

## 常量命名

- 全大写，下划线分隔
- 添加类型后缀（可选）
- 添加单位注释

```python
HIGH_RISK_TIME_THRESHOLD: int = 1800  # 30分钟，高风险时间阈值
STRONG_LIMIT_SEAL_AMOUNT_THRESHOLD: int = 1_000_000  # 100万元，强势涨停封单金额阈值
DEFAULT_MIN_TIME_TO_CLOSE: int = 1800  # 默认距收盘最小时间（秒）
```

## 私有成员命名

- 单前导下划线：`_signals`, `_lock`, `_load()`
- 双前导下划线（仅用于避免命名冲突）：`__name`

## 迁移指南

### 现有代码
- 可以保持现有命名以避免破坏性变更
- 在重构时逐步采用新命名

### 新代码
- 严格遵循本约定
- 特别是 `candidate_etf` 用于 `CandidateETF` 类型参数

### 代码审查检查点
- [ ] ETF相关参数是否使用 `candidate_etf`
- [ ] 查询方法是否遵循 `get_*/has_*/find_*` 模式
- [ ] 布尔方法是否以 `is_/has_/can_` 开头
- [ ] 常量是否全大写并添加注释
