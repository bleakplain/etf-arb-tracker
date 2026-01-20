# ETF Arbitrage Tracker

<div align="center">

**A股涨停ETF溢价监控系统**

当核心持仓个股涨停时，通过买入对应ETF获取溢价收益的辅助工具

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[功能概述](#功能概述) • [快速开始](#快速开始) • [API 接口](#api-接口) • [配置说明](#配置说明) • [部署指南](#部署指南)

</div>

## 功能概述

- **涨停股检测** - 实时抓取当日所有涨停股票
- **自选股追踪** - 自定义监控列表，涨停自动触发套利信号
- **ETF关联分析** - 自动查找股票关联ETF，显示持仓权重
- **K线图表** - 日K/周K/月K切换，MA均线，成交量分析
- **多渠道通知** - 钉钉、邮件、企业微信推送

## 快速开始

### 安装

```bash
git clone https://github.com/bleakplain/etf-arb-tracker.git
cd etf-arb-tracker

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 配置

编辑 `config/stocks.yaml` 添加自选股：

```yaml
my_stocks:
  - code: "600519"
    name: "贵州茅台"
    market: "sh"
```

编辑 `config/settings.yaml` 配置通知渠道：

```yaml
notification:
  dingtalk:
    enabled: true
    webhook: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

### 启动

```bash
./run_server.sh
```

访问: http://localhost:8000

## 项目结构

```
etf-arb-tracker/
├── backend/
│   ├── data/                      # 数据获取模块
│   │   ├── stock_quote.py         # A股行情（多数据源）
│   │   ├── etf_quote.py           # ETF行情
│   │   ├── etf_holder.py          # 股票-ETF映射
│   │   ├── etf_holdings.py        # ETF持仓数据
│   │   ├── limit_up_stocks.py     # 涨停股获取
│   │   ├── kline.py               # K线数据
│   │   └── multi_source_fetcher.py # 多数据源管理器
│   ├── strategy/
│   │   └── limit_monitor.py       # 涨停监控策略引擎
│   ├── notification/
│   │   └── sender.py              # 消息推送（钉钉/邮件/企业微信）
│   └── api/
│       └── app.py                 # FastAPI服务
├── config/                        # 配置模块
│   ├── __init__.py                # 统一配置入口
│   ├── stocks.yaml                # 自选股配置
│   ├── settings.yaml              # 系统配置
│   ├── strategy.py                # 策略配置类
│   ├── alert.py                   # 通知配置类
│   └── logger.py                  # 日志配置类
├── frontend/
│   └── index.html                 # Web监控界面
├── data/                          # 数据目录
│   ├── stock_etf_mapping.json     # 股票-ETF映射缓存
│   └── signals.json               # 交易信号历史
├── logs/                          # 日志目录
├── start.py                       # 命令行启动脚本
├── run_server.sh                  # 服务启动脚本
├── requirements.txt               # Python依赖
├── CHANGELOG.md                   # 版本变更记录
└── README.md                      # 本文档
```

## API 接口

系统提供 RESTful API，访问 `http://localhost:8000/docs` 查看完整 API 文档。

### 核心接口

| 方法 | 接口 | 说明 |
|------|------|------|
| `GET` | `/api/status` | 系统状态（监控状态、交易时间、信号数量） |
| `GET` | `/api/stocks` | 自选股实时行情列表 |
| `GET` | `/api/limit-up` | 今日所有涨停股票 |
| `GET` | `/api/signals` | 交易信号历史（支持 `limit` 和 `today_only` 参数） |
| `GET` | `/api/stocks/{code}/related-etfs` | 股票关联ETF（持仓≥5%） |
| `GET` | `/api/stocks/{code}/kline` | 股票K线数据（支持 `days` 参数） |
| `GET` | `/api/etfs/{code}/kline` | ETF K线数据 |
| `GET` | `/api/etfs/{code}/holdings` | ETF前十大持仓 |
| `GET` | `/api/etfs/categories` | ETF分类列表 |
| `GET` | `/api/config` | 系统配置（敏感信息已隐藏） |
| `POST` | `/api/monitor/scan` | 手动触发一次扫描 |
| `POST` | `/api/monitor/start` | 启动持续监控 |
| `POST` | `/api/monitor/stop` | 停止持续监控 |
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/` 或 `/frontend` | Web监控界面 |

### 响应示例

**系统状态 (`/api/status`)**

```json
{
  "is_running": true,
  "is_trading_time": true,
  "watch_stocks_count": 11,
  "covered_etfs_count": 7,
  "today_signals_count": 2,
  "last_scan_time": "2026-01-21 14:30:00"
}
```

**关联ETF (`/api/stocks/{code}/related-etfs`)**

```json
[
  {
    "etf_code": "510300",
    "etf_name": "沪深300ETF",
    "weight": 0.0523,
    "rank": 5,
    "in_top10": true,
    "category": "宽基",
    "price": 4.123,
    "change_pct": 1.23,
    "volume": 1234567890,
    "premium": 0.15
  }
]
```

## 套利策略逻辑

### 核心策略

1. **个股涨停** → 无法直接买入个股
2. **查找关联ETF** → 筛选持仓占比 ≥ 5% 的ETF
3. **评估信号质量** → 综合权重、排名、流动性等因素
4. **发送买入建议** → 多渠道推送通知

### 策略验证

系统会从以下维度验证信号质量：

| 维度 | 说明 |
|------|------|
| **持仓权重** | 股票在ETF中的实际占比（≥5%） |
| **持仓排名** | 在ETF持仓中的排名位置 |
| **流动性** | ETF日成交额要求（默认≥5000万） |
| **时间因素** | 距收盘时间（避免尾盘风险） |
| **持仓集中度** | 前十大持仓总占比 |

### 信号评级

- **置信度**：高/中/低（基于权重和排名）
- **风险等级**：高/中/低（基于时间和集中度）

## 配置说明

### 自选股配置 (`config/stocks.yaml`)

```yaml
my_stocks:
  - code: "300750"      # 股票代码（6位）
    name: "宁德时代"     # 股票名称
    market: "sz"        # 市场：sz=深圳, sh=上海
    notes: "新能源龙头"  # 备注（可选）

watch_etfs:              # 关注的ETF列表
  - code: "510300"
    name: "沪深300ETF"
```

### 系统配置 (`config/settings.yaml`)

```yaml
# 策略参数
strategy:
  min_weight: 0.05          # ETF中最小持仓权重（5%）
  min_etf_volume: 5000      # ETF最小日成交额（万元）
  min_time_to_close: 1800   # 距收盘最小时间（30分钟）
  scan_interval: 60         # 扫描间隔（秒）

# 交易时间
trading_hours:
  morning:
    start: "09:30"
    end: "11:30"
  afternoon:
    start: "13:00"
    end: "15:00"

# 通知配置
notification:
  enabled: true
  dingtalk:
    enabled: false
    webhook: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
    secret: ""
  email:
    enabled: false
    smtp_server: "smtp.qq.com"
    smtp_port: 465
    sender: "your@email.com"
    password: "your_password"
    receivers: ["receiver@email.com"]

# 日志配置
logging:
  level: "INFO"             # DEBUG, INFO, WARNING, ERROR
  file: "logs/monitor.log"
  rotation: "100 MB"
  retention: "30 days"
```

## 部署指南

### 方式一：使用启动脚本（推荐）

```bash
./run_server.sh
```

脚本会自动检查虚拟环境、依赖和配置文件，然后启动服务。

### 方式二：使用 start.py

```bash
# 初始化数据（构建股票-ETF映射）
python start.py init

# 同时启动API服务和监控
python start.py both

# 仅启动API服务
python start.py api

# 仅启动监控
python start.py monitor
```

### 方式三：直接使用 uvicorn

```bash
python -m uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 生产环境部署

建议使用 systemd 或 supervisor 管理服务：

**systemd 示例 (`/etc/systemd/system/etf-arb-tracker.service`)**

```ini
[Unit]
Description=ETF Arbitrage Tracker
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/etf-arb-tracker
Environment="PATH=/path/to/etf-arb-tracker/venv/bin"
ExecStart=/path/to/etf-arb-tracker/venv/bin/python -m uvicorn backend.api.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable etf-arb-tracker
sudo systemctl start etf-arb-tracker
sudo systemctl status etf-arb-tracker
```

### Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

构建并运行：

```bash
docker build -t etf-arb-tracker .
docker run -d -p 8000:8000 --name etf-arb-tracker etf-arb-tracker
```

## 开发指南

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/bleakplain/etf-arb-tracker.git
cd etf-arb-tracker

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest black flake8 mypy
```

### 代码规范

```bash
# 代码格式化
black backend/ config/ start.py

# 代码检查
flake8 backend/ config/ start.py

# 类型检查
mypy backend/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_limit_monitor.py
```

### 添加新功能

1. 数据源：在 `backend/data/` 添加新的 fetcher 类
2. 策略：在 `backend/strategy/` 修改策略逻辑
3. 通知：在 `backend/notification/` 添加新的通知渠道
4. API：在 `backend/api/app.py` 添加新的接口

## 故障排查

### 常见问题

**Q: 启动时提示缺少依赖**

```bash
pip install -r requirements.txt
```

**Q: 无法获取股票行情**

- 检查网络连接
- 确认当前为交易时间
- 查看日志文件 `logs/monitor.log`

**Q: 映射文件不存在**

```bash
python start.py init
```

**Q: 通知发送失败**

- 检查 `config/settings.yaml` 中的通知配置
- 确认 webhook 地址正确
- 验证密钥/密码设置

**Q: API 端口被占用**

修改 `run_server.sh` 或使用以下命令指定端口：

```bash
python -m uvicorn backend.api.app:app --port 8001
```

### 日志查看

```bash
# 查看主日志
tail -f logs/monitor.log

# 查看错误日志
tail -f logs/app_error.log
```

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 报告问题

在 [Issues](https://github.com/bleakplain/etf-arb-tracker/issues) 中报告问题时，请包含：

- 问题描述和重现步骤
- 系统环境（OS、Python 版本）
- 相关日志输出
- 预期行为 vs 实际行为

### 提交代码

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码审查标准

- 代码符合 PEP 8 规范
- 添加必要的测试用例
- 更新相关文档
- 通过所有现有测试

## 数据来源

| 数据类型 | 主要数据源 | 备用数据源 |
|----------|-----------|-----------|
| **A股行情** | EFinance | AKShare |
| **ETF行情** | EFinance | AKShare |
| **涨停股** | AKShare (东方财富) | - |
| **K线数据** | AKShare | - |
| **ETF持仓** | 天天基金 (fundf10.eastmoney.com) | 东方财富 (push2.eastmoney.com) |

> 本项目仅供学习研究使用，不构成投资建议。

## 风险提示

> **免责声明**：本工具仅供学习研究使用，不构成投资建议。溢价套利存在亏损风险，请谨慎决策。投资有风险，入市需谨慎。

## License

[MIT](LICENSE)

---

<div align="center">

**[⬆ 返回顶部](#etf-arbitrage-tracker)**

Made with ❤️ by [bleakplain](https://github.com/bleakplain)

</div>
