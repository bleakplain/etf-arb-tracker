# ETF Arbitrage MCP Server - 设计总结

## 项目概述

**服务器名称**: `etf_arbitrage_mcp`
**包名**: `etf_arbitrage`
**版本**: 0.1.0

基于FastMCP框架开发的MCP服务器，将ETF套利追踪器的核心能力通过Model Context Protocol暴露给外部AI代理和技能使用。

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| **框架** | FastMCP | 装饰器语法简洁，Pydantic集成良好 |
| **语言** | Python | 与现有代码库一致，直接复用模块 |
| **传输** | Streamable HTTP | 支持多客户端，便于云部署 |
| **验证** | Pydantic v2 | 类型安全，已在项目中使用 |
| **异步** | asyncio | 高性能I/O操作 |

## 项目结构

```
servers/mcp/
├── etf_arbitrage/              # Python包
│   ├── __init__.py
│   ├── server.py               # FastMCP服务器入口
│   ├── config.py               # 配置管理
│   ├── tools/                  # 工具定义
│   │   ├── __init__.py
│   │   ├── base.py             # 基础工具类和后端桥接
│   │   ├── market.py           # 市场数据工具 ✅
│   │   ├── arbitrage.py        # 套利分析工具 ✅
│   │   ├── signal.py           # 信号管理工具 (TODO)
│   │   ├── backtest.py         # 回测工具 (TODO)
│   │   ├── watchlist.py        # 自选股管理工具 (TODO)
│   │   └── monitor.py          # 监控控制工具 (TODO)
│   ├── models/                 # Pydantic模型
│   │   ├── __init__.py
│   │   ├── requests.py         # 请求模型 ✅
│   │   ├── responses.py        # 响应模型 ✅
│   │   └── enums.py            # 枚举类型 ✅
│   ├── resources/              # MCP资源 (TODO)
│   │   └── data.py
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── formatters.py       # 格式化 ✅
│       └── errors.py           # 错误处理 ✅
├── pyproject.toml              # 项目配置
├── requirements.txt            # 依赖
└── README.md                   # 文档
```

## 已实现工具

### 市场数据工具 (tools/market.py)

1. **etf_arbitrage_get_stock_quote**
   - 功能: 获取股票实时行情
   - 输入: codes (List[str]), response_format
   - 输出: 股票报价（价格、涨跌幅、成交量、涨停状态）

2. **etf_arbitrage_get_etf_quote**
   - 功能: 获取ETF实时行情
   - 输入: codes (List[str]), response_format
   - 输出: ETF报价（包含溢价率）

3. **etf_arbitrage_list_limit_up_stocks**
   - 功能: 列出今日涨停股
   - 输入: limit, offset, min_change_pct, response_format
   - 输出: 涨停股票列表（带分页）

### 套利分析工具 (tools/arbitrage.py)

1. **etf_arbitrage_find_related_etfs**
   - 功能: 查找持有特定股票的ETF
   - 输入: stock_code, min_weight, response_format
   - 输出: 相关ETF列表（按权重排序）

2. **etf_arbitrage_analyze_opportunity**
   - 功能: 分析套利机会
   - 输入: stock_code, include_signals, response_format
   - 输出: 综合分析（股票状态、相关ETF、推荐标的）

## 待实现工具

### 信号管理工具
- etf_arbitrage_list_signals - 列出历史信号
- etf_arbitrage_get_signal - 获取信号详情

### 回测工具
- etf_arbitrage_run_backtest - 运行回测
- etf_arbitrage_get_backtest_result - 获取回测结果
- etf_arbitrage_list_backtests - 列出回测任务

### 配置工具
- etf_arbitrage_get_stock_etf_mapping - 获取映射关系
- etf_arbitrage_list_watchlist - 列出自选股
- etf_arbitrage_add_watchlist_stock - 添加自选股
- etf_arbitrage_remove_watchlist_stock - 删除自选股

### 监控工具
- etf_arbitrage_get_monitor_status - 获取监控状态
- etf_arbitrage_start_monitor - 启动监控
- etf_arbitrage_stop_monitor - 停止监控
- etf_arbitrage_trigger_scan - 触发扫描

## 核心设计

### 1. 后端桥接 (BackendBridge)

通过`BackendBridge`类桥接现有后端模块：

```python
class BackendBridge:
    def get_quote_fetcher() -> QuoteFetcherCN
    def get_arbitrage_engine() -> ArbitrageEngineCN
    def get_signal_repository() -> DBSignalRepository
    def get_mapping_repository() -> StockETFMappingRepository
    def get_backtest_engine() -> CNBacktestEngine
    def get_config() -> Dict
```

### 2. 响应格式化

所有查询工具支持两种输出格式：
- **JSON**: 机器可读的结构化数据
- **Markdown**: 人类可读的格式化文本

### 3. 错误处理

统一的错误处理机制：
- Pydantic模型验证输入
- 可操作的错误消息和建议
- 标准化错误响应格式

### 4. 分页支持

列表类工具实现分页：
```python
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

## 使用示例

### 启动服务器

```bash
# stdio传输（本地工具）
python -m etf_arbitrage.server

# HTTP传输（远程服务）
python -m etf_arbitrage.server --transport streamable-http --port 8000
```

### 工具调用示例

```python
# 查询股票行情
etf_arbitrage_get_stock_quote(
    codes=["600519", "000001"],
    response_format="markdown"
)

# 查找相关ETF
etf_arbitrage_find_related_etfs(
    stock_code="600519",
    min_weight=0.05,
    response_format="json"
)

# 分析套利机会
etf_arbitrage_analyze_opportunity(
    stock_code="600519",
    include_signals=True
)
```

## 下一步工作

1. **完成剩余工具实现**
   - 信号管理工具
   - 回测工具
   - 配置工具
   - 监控工具

2. **添加MCP资源**
   - ETF分类信息
   - 系统配置
   - 交易时间

3. **编写测试**
   - 单元测试
   - 集成测试
   - 评估问题集

4. **部署和文档**
   - Docker镜像
   - API文档
   - 使用指南
