# Error Handling Standards

本文档定义了项目中统一的错误处理标准。

## 原则

1. **明确区分错误类型**：数据获取失败、参数验证失败、系统错误
2. **提供有用的错误信息**：错误信息应包含足够的上下文以便调试
3. **不要静默失败**：所有错误都应该被记录或以适当方式处理

## 标准规范

### 1. 数据获取操作（返回 None）

适用于从外部API、数据库、文件系统等获取数据的场景。

```python
def get_stock_quote(self, code: str) -> Optional[Dict]:
    """
    获取股票行情

    Returns:
        行情数据字典，获取失败时返回None
    """
    try:
        response = self.session.get(url, timeout=10)
        if response.status_code == 200:
            return parse_response(response.text)
    except Exception as e:
        logger.error(f"获取股票{code}行情失败: {e}")
    return None
```

**规则**：
- 外部调用失败时返回 `None`
- 必须记录错误日志（使用 `logger.error` 或 `logger.warning`）
- 不要让异常传播到调用方

### 2. 参数验证（抛出 ValueError）

适用于验证业务规则和输入参数的场景。

```python
def __post_init__(self):
    if not self.stock_code:
        raise ValueError("股票代码不能为空")
    if not 0 <= self.weight <= 1:
        raise ValueError("权重必须在0-1之间")
```

**规则**：
- 使用 `ValueError` 表示无效输入
- 错误信息应清楚说明问题所在
- 在 `__post_init__` 或业务逻辑入口处验证

### 3. 系统错误（记录并返回默认值）

适用于非预期但可恢复的错误场景。

```python
def process_signal(self, signal: TradingSignal) -> Optional[Result]:
    try:
        return self._do_process(signal)
    except Exception as e:
        logger.error(f"处理信号失败: {e}", exc_info=True)
        return None  # 或返回适当的默认值
```

**规则**：
- 捕获具体异常类型，而非裸露的 `except:`
- 使用 `exc_info=True` 记录完整堆栈
- 返回安全的默认值或 None

## 实施清单

### 当前符合标准的代码

- [x] `backend/market/cn/sources/tencent.py` - 数据获取返回 None
- [x] `backend/market/cn/models.py` - 验证抛出 ValueError
- [x] `backend/arbitrage/models.py` - 验证抛出 ValueError
- [x] `backend/arbitrage/interfaces.py` - FileMappingRepository 错误处理

### 需要检查/改进的代码

- [ ] 检查所有 API 调用是否正确处理超时
- [ ] 检查所有文件操作是否正确处理 IO 错误
- [ ] 统一日志级别使用（error/warning/info/debug）

## 最佳实践

### 日志级别选择

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| `error` | 错误导致功能失败 | `logger.error(f"获取数据失败: {e}")` |
| `warning` | 错误但功能可继续 | `logger.warning(f"使用缓存数据，API调用失败")` |
| `info` | 正常业务流程 | `logger.info(f"处理了 {len(signals)} 个信号")` |
| `debug` | 调试信息 | `logger.debug(f"信号详情: {signal.to_dict()}")` |

### 异常捕获优先级

1. 优先捕获具体异常类型（如 `requests.RequestException`）
2. 仅在最外层使用 `Exception` 作为兜底
3. 绝不使用裸露的 `except:` 语句

### 返回值约定

| 场景 | 返回值 | 说明 |
|------|--------|------|
| 数据获取失败 | `None` | 调用方需判断返回值 |
| 列表/集合操作失败 | `[]` 或 `{}` | 空容器，避免调用方 None 检查 |
| 布尔判断 | `False` | 明确的否定结果 |
