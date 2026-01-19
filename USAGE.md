# 快速开始指南

## 一、环境准备

### 1. 安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt
```

### 2. 配置文件

#### 编辑自选股 `config/stocks.yaml`
```yaml
my_stocks:
  - code: "300750"
    name: "宁德时代"
    market: "sz"

watch_etfs:
  - code: "510300"
    name: "沪深300ETF"
```

#### 编辑系统配置 `config/settings.yaml`
```yaml
strategy:
  min_weight: 0.05           # 最小权重5%
  min_order_amount: 10       # 最小封单10亿
  min_time_to_close: 1800    # 距收盘30分钟

notification:
  dingtalk:
    enabled: true
    webhook: "your_webhook_url"
```

## 二、运行系统

### 方式1: 一键启动（推荐）
```bash
python start.py
```

访问: http://localhost:8000/frontend/index.html

### 方式2: 分步启动

**终端1 - 启动API服务**
```bash
python start.py api
```

**终端2 - 启动监控器**
```bash
python start.py monitor
```

### 方式3: 初始化数据
```bash
python start.py init
```

## 三、使用说明

### 1. Web界面操作

**控制面板**
- 点击"启动监控"开始实时监控
- 点击"立即扫描"手动触发一次扫描
- 点击"停止监控"停止监控

**查看相关ETF**
- 在自选股列表中点击"查看"按钮
- 查看该股票对应的所有ETF及权重

### 2. 信号推送

当检测到涨停时，系统会:
1. 在Web界面显示信号卡片
2. 通过配置的渠道推送通知（钉钉/邮件/企业微信）
3. 记录到信号历史

### 3. 策略参数调整

在控制面板实时调整:
- 最小权重: 过滤权重太小的ETF
- 最小封单: 确保涨停的有效性
- 距收盘时间: 控制风险敞口

## 四、API接口

系统提供RESTful API:

```bash
# 获取系统状态
curl http://localhost:8000/api/status

# 获取自选股行情
curl http://localhost:8000/api/stocks

# 获取信号历史
curl http://localhost:8000/api/signals

# 手动扫描
curl -X POST http://localhost:8000/api/monitor/scan

# 启动监控
curl -X POST http://localhost:8000/api/monitor/start
```

完整API文档: http://localhost:8000/docs

## 五、常见问题

### Q1: 行情数据不更新?
A: 检查网络连接，确认在交易时间内

### Q2: 没有信号产生?
A: 可能当前没有股票涨停，可以手动扫描测试

### Q3: 如何添加更多股票?
A: 编辑 `config/stocks.yaml`，重启系统生效

### Q4: 钉钉通知不发送?
A: 检查webhook配置是否正确，确认机器人未过期

## 六、风险提示

⚠️ **重要声明**
- 本工具仅供学习研究使用
- 不构成任何投资建议
- 溢价套利存在亏损风险
- 请根据自身风险承受能力谨慎决策
