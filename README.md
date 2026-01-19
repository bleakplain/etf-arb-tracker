# A股涨停ETF溢价监控系统

## 产品概述

监控A股个股涨停情况，当核心持仓个股涨停时，通过买入对应ETF获取溢价收益的辅助工具。

## 核心功能

### 1. 自动获取涨停股
- 实时抓取当日所有涨停股票
- 显示涨停价格、成交额、换手率
- 支持点击查看详情和K线图

### 2. 自选股监控
- 支持用户添加自定义自选股
- 实时监控自选股涨停情况
- 涨停自动触发ETF套利信号

### 3. K线图展示
- 支持日K、周K、月K切换
- 显示MA5、MA10、MA20均线
- 成交量柱状图
- 鼠标悬停查看详细数据

### 4. ETF关联分析
- 自动查找股票关联的ETF
- 显示持仓权重
- 实时ETF价格和涨跌幅

### 5. 信号推送
- 涨停触发自动生成信号
- 支持钉钉、邮件、企业微信推送
- Web界面实时弹窗提醒

## 界面预览

### 三个主要标签页

| 标签页 | 功能 |
|--------|------|
| **自选股** | 显示自选股实时行情，支持监控控制 |
| **涨停股** | 显示当日所有涨停股票列表 |
| **信号** | 历史信号记录和详情 |

## 快速开始

### 1. 安装依赖
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置自选股
编辑 `config/stocks.yaml`:
```yaml
my_stocks:
  - code: "300750"
    name: "宁德时代"
    market: "sz"
```

### 3. 启动服务
```bash
# 使用启动脚本
./run_server.sh

# 或手动启动
python -m uvicorn backend.api.app:app --host 0.0.0.0 --port 8000
```

### 4. 访问界面
打开浏览器: http://localhost:8000

## API接口

| 接口 | 说明 |
|------|------|
| `GET /` | 前端界面 |
| `GET /api/status` | 系统状态 |
| `GET /api/stocks` | 自选股行情 |
| `GET /api/limit-up` | 今日涨停股 |
| `GET /api/stocks/{code}/kline` | K线数据 |
| `GET /api/stocks/{code}/related-etfs` | 关联ETF |
| `POST /api/monitor/start` | 启动监控 |
| `POST /api/monitor/stop` | 停止监控 |

## 项目结构

```
etf-monitor/
├── backend/
│   ├── data/
│   │   ├── stock_quote.py      # 行情数据
│   │   ├── etf_quote.py        # ETF行情
│   │   ├── etf_holder.py       # ETF持仓
│   │   ├── limit_up_stocks.py  # 涨停股获取
│   │   └── kline.py            # K线数据
│   ├── strategy/
│   │   └── limit_monitor.py    # 涨停监控
│   ├── notification/
│   │   └── sender.py           # 消息推送
│   └── api/
│       └── app.py              # FastAPI服务
├── frontend/
│   └── index.html              # Web界面
├── config/
│   ├── stocks.yaml             # 自选股配置
│   └── settings.yaml           # 系统配置
└── start.py                    # 启动脚本
```

## 风险提示

⚠️ **重要声明**
- 本工具仅供学习研究使用
- 不构成任何投资建议
- 溢价套利存在亏损风险
- 请根据自身情况谨慎决策

## License

MIT License
