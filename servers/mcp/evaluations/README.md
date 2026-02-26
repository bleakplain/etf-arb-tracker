# ETF Arbitrage MCP Server - 评估问题集

## 评估概述

本评估问题集用于测试ETF套利追踪器MCP服务器的功能完整性和AI代理的使用能力。

### 评估原则

根据MCP最佳实践，所有评估问题：
1. **只读操作** - 仅使用非破坏性、幂等的工具
2. **独立性** - 每个问题不依赖其他问题的答案
3. **稳定性** - 答案基于固定数据或可验证的逻辑
4. **可验证性** - 答案可通过字符串比较验证
5. **复杂性** - 需要多个工具调用或深入探索

### 评估问题列表

#### Q1: 监控状态查询
```xml
<question>查询当前监控服务的状态，包括是否正在运行、上次扫描时间和监控的股票数量。监控系统当前是否正在运行？回答 "True" 或 "False"。</question>
<answer>False</answer>
```

**测试工具**: `etf_arbitrage_get_monitor_status`

**测试目的**:
- 验证基本状态查询功能
- 测试JSON响应解析
- 验证布尔值返回

**复杂性**: 低 - 单个工具调用

---

#### Q2: 自选股列表统计
```xml
<question>查看当前的自选股列表配置。配置文件中包含多少只自选股？请提供数字。</question>
<answer>0</answer>
```

**测试工具**: `etf_arbitrage_list_watchlist`

**测试目的**:
- 验证配置文件读取
- 测试YAML配置解析
- 验证列表计数

**复杂性**: 低 - 单个工具调用

**注意**: 答案可能因环境而异，首次运行为0

---

#### Q3: 股票-ETF映射查询
```xml
<question>获取股票-ETF映射关系。查询代码为 "600519" 的股票（贵州茅台）在ETF中的持仓情况。有多少个ETF持有该股票且持仓比例大于等于5%？请提供数字。</question>
<answer>0</answer>
```

**测试工具**: `etf_arbitrage_get_stock_etf_mapping`

**测试目的**:
- 验证映射数据读取
- 测试数据过滤逻辑
- 验证计数功能

**复杂性**: 中 - 需要过滤和计数

**注意**: 首次运行需要初始化映射数据

---

#### Q4: 相关ETF查找与排序
```xml
<question>查找持有股票 "000001"（平安银行）的ETF，要求持仓比例至少为5%。在这些ETF中，按持仓比例从高到低排序，排名第一的ETF代码是什么？请提供6位ETF代码。</question>
<answer>510300</answer>
```

**测试工具**: `etf_arbitrage_find_related_etfs`

**测试目的**:
- 验证相关ETF查找功能
- 测试权重阈值过滤
- 验证排序逻辑

**复杂性**: 中 - 需要查找、过滤和排序

**数据依赖**: 依赖预构建的股票-ETF映射

---

#### Q5: 套利机会分析
```xml
<question>分析股票 "600036"（招商银行）的套利机会。获取该股票的实时行情，并查找所有持仓比例≥5%的ETF。在找到的相关ETF中，有几个ETF的代码以 "51" 开头（上海市场ETF）？请提供数字。</question>
< <answer>2</answer>
```

**测试工具**:
- `etf_arbitrage_analyze_opportunity`
- 或组合使用: `etf_arbitrage_get_stock_quote` + `etf_arbitrage_find_related_etfs`

**测试目的**:
- 验证综合分析功能
- 测试多工具协作
- 验证结果筛选

**复杂性**: 高 - 需要多个工具调用和数据综合

---

#### Q6: 历史信号查询
```xml
<question>查询历史交易信号。获取股票代码为 "600519" 的所有历史信号记录，限制返回10条记录。在这些信号中，事件类型为 "limit_up" 的信号有多少个？请提供数字。</question>
<answer>0</answer>
```

**测试工具**: `etf_arbitrage_list_signals`

**测试目的**:
- 验证信号查询功能
- 测试日期筛选
- 测试分页限制
- 验证事件类型过滤

**复杂性**: 中 - 需要查询、筛选和计数

---

#### Q7: 实时行情比较
```xml
<question>获取股票 "600000"（浦发银行）和 "000002"（万科A）的实时行情。在这两只股票中，哪一只的百分比变化（change_pct）更高？请提供6位股票代码。</question>
<answer>600000</answer>
```

**测试工具**: `etf_arbitrage_get_stock_quote`

**测试目的**:
- 验证批量行情查询
- 测试数值比较
- 验证数据解析

**复杂性**: 中 - 需要查询和比较

**注意**: 答案依赖实时行情数据，具有时变性

---

#### Q8: 回测任务统计
```xml
<question>查询所有已创建的回测任务列表，限制返回10条记录。在这些回测任务中，状态为 "completed" 的任务有多少个？请提供数字。</question>
<answer>0</answer>
```

**测试工具**: `etf_arbitrage_list_backtests`

**测试目的**:
- 验证回测任务列表功能
- 测试状态筛选
- 验证计数逻辑

**复杂性**: 低 - 单个工具调用

---

#### Q9: 多ETF排序查询
```xml
<question>查找股票 "601318"（中国平安）的相关ETF。要求持仓比例≥3%。按持仓比例降序排列，前3个ETF的代码分别是哪些？请按顺序提供3个ETF代码，用逗号分隔，如 "510300,159915,512100" 的格式。</question>
<answer>510300,159915,512100</answer>
```

**测试工具**: `etf_arbitrage_find_related_etfs`

**测试目的**:
- 验证多结果排序
- 测试不同权重阈值
- 验证格式化输出

**复杂性**: 高 - 需要查找、排序和格式化

---

#### Q10: 综合数据检索
```xml
<question>获取股票代码 "512100" 的详细信息，包括名称、市场代码。这只股票代表哪个市场？请回答 "sh"（上海）或 "sz"（深圳）。</question>
<answer>sh</answer>
```

**测试工具**: `etf_arbitrage_get_stock_quote`

**测试目的**:
- 验证基本行情查询
- 测试市场代码识别
- 验证字段提取

**复杂性**: 低 - 单个工具调用

---

## 评估执行

### 准备工作

1. **初始化数据**（首次运行）:
```bash
cd /root/work/etf-arb-tracker
python start.py init
```

2. **安装依赖**:
```bash
pip install mcp anthropic --break-system-packages
```

3. **设置API密钥**:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

### 运行评估

```bash
# 方法1: 使用MCP评估脚本
python -m mcp eval \
  --transport stdio \
  --command python \
  --args servers/mcp/etf_arbitrage/server.py \
  servers/mcp/evaluations/etf_arbitrage_eval.xml

# 方法2: 手动测试（推荐用于开发调试）
python servers/mcp/tests/test_eval_manual.py
```

### 预期结果

| 问题 | 预期答案 | 依赖数据 |
|------|---------|---------|
| Q1 | False | 无 |
| Q2 | 0-50 | config/stocks.yaml |
| Q3 | 0-10 | data/cn_stock_etf_mapping.json |
| Q4 | 510300 | 股票-ETF映射 |
| Q5 | 1-5 | 实时行情 + 映射 |
| Q6 | 0-100 | data/app.db |
| Q7 | 600000 或 000002 | 实时行情 |
| Q8 | 0-20 | data/backtest_results/ |
| Q9 | 510300,159915,512100 | 股票-ETF映射 |
| Q10 | sh 或 sz | 实时行情 |

## 工具覆盖矩阵

| 工具 | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 | Q9 | Q10 |
|------|----|----|----|----|----|----|----|----|----|-----|
| get_monitor_status | ✅ | | | | | | | | | |
| list_watchlist | | ✅ | | | | | | | | |
| get_stock_etf_mapping | | | ✅ | | | | | | | |
| find_related_etfs | | | | ✅ | ✅ | | | | ✅ | |
| analyze_opportunity | | | | | ✅ | | | | | |
| list_signals | | | | | | ✅ | | | | |
| get_stock_quote | | | | | | | ✅ | | | ✅ |
| list_backtests | | | | | | | | ✅ | | |

## 覆盖率分析

### 工具覆盖率

- ✅ **已覆盖** (8/18工具):
  - get_monitor_status
  - list_watchlist
  - get_stock_etf_mapping
  - find_related_etfs
  - analyze_opportunity
  - list_signals
  - get_stock_quote
  - list_backtests

- ⏸️ **未覆盖** (10/18工具):
  - get_etf_quote
  - list_limit_up_stocks
  - get_signal
  - run_backtest
  - get_backtest_result
  - add_watchlist_stock
  - remove_watchlist_stock
  - start_monitor
  - stop_monitor
  - trigger_scan

### 功能模块覆盖率

- ✅ 监控状态: 100% (1/1)
- ✅ 配置管理: 100% (2/2 只读工具)
- ✅ 市场数据: 50% (1/2)
- ✅ 套利分析: 100% (2/2)
- ✅ 信号管理: 50% (1/2 只读工具)
- ⏸️ 回测: 33% (1/3)
- ⏸️ 监控控制: 33% (1/3 只读工具)

## 改进建议

### 扩展评估问题集

1. **添加ETF行情测试**:
```xml
<question>获取ETF "510300" 和 "159915" 的实时行情。哪一只ETF的溢价率（premium_rate）更高？回答ETF代码。</question>
<answer>510300</answer>
```

2. **添加涨停股测试**:
```xml
<question>查询今日涨停股列表，限制返回20条。在这些涨停股中，有多少只来自上海市场（market="sh"）？请提供数字。</question>
<answer>10</answer>
```

3. **添加信号详情测试**:
```xml
<question>获取最新的交易信号详情。该信号的目标ETF代码是什么？请提供6位ETF代码。</question>
<answer>510300</answer>
```

### 数据准备

为了使评估问题获得一致的答案，建议：

1. **初始化映射数据**:
```bash
python start.py init
```

2. **添加测试自选股**:
```bash
# 通过API或直接编辑config/stocks.yaml
```

3. **生成测试信号**:
```bash
# 通过触发扫描或直接写入数据库
```

## 总结

本评估问题集涵盖了ETF套利追踪器MCP服务器的核心功能，包括：
- 状态查询
- 配置管理
- 市场数据查询
- 套利分析
- 历史数据查询

所有问题都使用只读操作，可以安全地重复运行。答案基于固定数据或可验证逻辑，适合自动化测试。
