# ETF Arbitrage MCP Server - 完整实现文档

## 项目信息

**服务器名称**: `etf_arbitrage_mcp`
**包名**: `etf_arbitrage`
**版本**: 0.1.0
**状态**: ✅ 完整实现

## 完整工具列表

### 1. 市场数据工具 (Market Data) - 3个工具

| 工具名 | 功能 | 只读 | 幂等 |
|--------|------|------|------|
| `etf_arbitrage_get_stock_quote` | 获取股票实时行情 | ✅ | ✅ |
| `etf_arbitrage_get_etf_quote` | 获取ETF实时行情 | ✅ | ✅ |
| `etf_arbitrage_list_limit_up_stocks` | 列出今日涨停股 | ✅ | ✅ |

### 2. 套利分析工具 (Arbitrage Analysis) - 2个工具

| 工具名 | 功能 | 只读 | 幂等 |
|--------|------|------|------|
| `etf_arbitrage_find_related_etfs` | 查找持有特定股票的ETF | ✅ | ✅ |
| `etf_arbitrage_analyze_opportunity` | 分析套利机会 | ✅ | ✅ |

### 3. 信号管理工具 (Signal Management) - 2个工具

| 工具名 | 功能 | 只读 | 幂等 |
|--------|------|------|------|
| `etf_arbitrage_list_signals` | 列出历史交易信号 | ✅ | ✅ |
| `etf_arbitrage_get_signal` | 获取信号详情 | ✅ | ✅ |

### 4. 回测工具 (Backtesting) - 3个工具

| 工具名 | 功能 | 只读 | 幂等 | 破坏性 |
|--------|------|------|------|--------|
| `etf_arbitrage_run_backtest` | 运行回测 | ❌ | ❌ | ❌ |
| `etf_arbitrage_get_backtest_result` | 获取回测结果 | ✅ | ✅ | ❌ |
| `etf_arbitrage_list_backtests` | 列出回测任务 | ✅ | ✅ | ❌ |

### 5. 配置管理工具 (Configuration) - 4个工具

| 工具名 | 功能 | 只读 | 幂等 | 破坏性 |
|--------|------|------|------|--------|
| `etf_arbitrage_get_stock_etf_mapping` | 获取股票-ETF映射 | ✅ | ✅ | ❌ |
| `etf_arbitrage_list_watchlist` | 列出自选股 | ✅ | ✅ | ❌ |
| `etf_arbitrage_add_watchlist_stock` | 添加自选股 | ❌ | ❌ | ❌ |
| `etf_arbitrage_remove_watchlist_stock` | 删除自选股 | ❌ | ✅ | ✅ |

### 6. 监控控制工具 (Monitor Control) - 4个工具

| 工具名 | 功能 | 只读 | 幂等 | 破坏性 |
|--------|------|------|------|--------|
| `etf_arbitrage_get_monitor_status` | 获取监控状态 | ✅ | ✅ | ❌ |
| `etf_arbitrage_start_monitor` | 启动监控 | ❌ | ❌ | ❌ |
| `etf_arbitrage_stop_monitor` | 停止监控 | ❌ | ✅ | ❌ |
| `etf_arbitrage_trigger_scan` | 触发手动扫描 | ❌ | ✅ | ❌ |

**总计**: 18个工具

## 项目结构

```
servers/mcp/
├── etf_arbitrage/              # Python包
│   ├── __init__.py             ✅
│   ├── server.py               ✅ MCP服务器入口
│   ├── config.py               ✅ 配置管理
│   ├── tools/                  ✅ 工具定义
│   │   ├── __init__.py         ✅
│   │   ├── base.py             ✅ 基础工具类
│   │   ├── market.py           ✅ 市场数据工具 (3)
│   │   ├── arbitrage.py        ✅ 套利分析工具 (2)
│   │   ├── signal.py           ✅ 信号管理工具 (2)
│   │   ├── backtest.py         ✅ 回测工具 (3)
│   │   ├── watchlist.py        ✅ 配置工具 (4)
│   │   └── monitor.py          ✅ 监控工具 (4)
│   ├── models/                 ✅ Pydantic模型
│   │   ├── __init__.py         ✅
│   │   ├── requests.py         ✅ 请求模型
│   │   ├── responses.py        ✅ 响应模型
│   │   └── enums.py            ✅ 枚举类型
│   ├── resources/              ⏸️ MCP资源 (预留)
│   └── utils/                  ✅ 工具函数
│       ├── __init__.py         ✅
│       ├── formatters.py       ✅ 格式化
│       └── errors.py           ✅ 错误处理
├── pyproject.toml              ✅ 项目配置
├── requirements.txt            ✅ 依赖
└── README.md                   ✅ 文档
```

## 核心特性

### 1. 双格式输出

所有查询工具支持两种输出格式：
- **JSON**: 机器可读的结构化数据
- **Markdown**: 人类可读的格式化文本

```python
# JSON格式示例
{
  "quotes": [
    {"code": "600519", "name": "贵州茅台", "price": 1680.50}
  ]
}

# Markdown格式示例
# Stock Quotes
## 贵州茅台 (600519)
- **Price**: 1680.50
- **Change**: +15.30 (+0.92%)
```

### 2. 分页支持

列表类工具实现标准分页：
```json
{
  "items": [...],
  "pagination": {
    "total": 150,
    "count": 20,
    "offset": 0,
    "has_more": true,
    "next_offset": 20
  }
}
```

### 3. 错误处理

统一的错误处理机制：
```python
# 错误响应格式
"Error: Stock '600519' not found. Suggestion: Verify the stock code is correct"
```

### 4. 后端集成

通过`BackendBridge`类桥接现有后端模块：
- `QuoteFetcherCN` - 行情数据
- `ArbitrageEngineCN` - 套利引擎
- `DBSignalRepository` - 信号存储
- `CNBacktestEngine` - 回测引擎

### 5. 异步支持

所有工具使用`async/await`：
```python
@mcp.tool()
async def get_stock_quote(params: GetStockQuoteRequest) -> str:
    quotes = await fetch_stock_quotes(params.codes)
    return format_response(quotes)
```

## 使用方法

### 安装依赖

```bash
cd servers/mcp
pip install -r requirements.txt
```

### 启动服务器

```bash
# stdio传输（本地工具）
python -m etf_arbitrage.server

# HTTP传输（远程服务）
python -m etf_arbitrage.server --transport streamable-http --port 8000

# 使用MCP Inspector测试
mcp-dev-tool etf_arbitrage/server.py
```

### 工具调用示例

```python
# 1. 查询股票行情
etf_arbitrage_get_stock_quote(
    codes=["600519", "000001"],
    response_format="markdown"
)

# 2. 查找相关ETF
etf_arbitrage_find_related_etfs(
    stock_code="600519",
    min_weight=0.05,
    response_format="json"
)

# 3. 分析套利机会
etf_arbitrage_analyze_opportunity(
    stock_code="600519",
    include_signals=True
)

# 4. 列出历史信号
etf_arbitrage_list_signals(
    start_date="2024-01-01",
    stock_code="600519",
    limit=50
)

# 5. 运行回测
etf_arbitrage_run_backtest(
    start_date="2024-01-01",
    end_date="2024-01-31",
    fund_selector="highest_weight"
)

# 6. 添加自选股
etf_arbitrage_add_watchlist_stock(
    code="600519",
    name="贵州茅台",
    market="sh",
    notes="白酒龙头"
)

# 7. 启动监控
etf_arbitrage_start_monitor()

# 8. 触发手动扫描
etf_arbitrage_trigger_scan()
```

## 技术实现细节

### Pydantic模型

所有输入使用Pydantic v2模型验证：
```python
class GetStockQuoteRequest(FormattedRequest):
    codes: List[str] = Field(..., min_length=1, max_length=100)

    @field_validator('codes')
    @classmethod
    def validate_codes(cls, v: List[str]) -> List[str]:
        for code in v:
            if not code.isdigit() or len(code) != 6:
                raise ValueError(f"Invalid stock code '{code}'")
        return v
```

### 工具装饰器

使用FastMCP装饰器注册工具：
```python
@mcp.tool(
    name="etf_arbitrage_get_stock_quote",
    annotations={
        "title": "Get Stock Quotes",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def get_stock_quote(params: GetStockQuoteRequest) -> str:
    """Tool docstring becomes the description."""
    pass
```

### 生命周期管理

使用`lifespan`上下文管理器：
```python
@asynccontextmanager
async def server_lifespan():
    # Startup: Initialize resources
    register_strategies()
    yield {}
    # Shutdown: Cleanup resources
```

## 下一步工作

1. **测试**
   - 单元测试
   - 集成测试
   - 使用MCP Inspector进行手动测试

2. **部署**
   - Docker容器化
   - CI/CD配置
   - 文档完善

3. **资源**
   - 实现MCP资源端点
   - 静态数据暴露

4. **优化**
   - 性能优化
   - 缓存策略
   - 错误恢复

## 相关文档

- [MCP Best Practices](https://modelcontextprotocol.io/best-practices)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [项目README](./README.md)
- [设计总结](./DESIGN_SUMMARY.md)
