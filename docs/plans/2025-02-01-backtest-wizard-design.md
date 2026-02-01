# 回测功能向导式改造设计文档

**日期**: 2025-02-01
**目标**: 改造回测功能，使其对小白用户更友好、可解释、可观测

---

## 一、需求概述

当前回测页面存在的问题：
- 策略参数专业术语多，小白用户不理解含义
- 数据来源不透明，用户不知道用了哪些数据
- 信号结果缺乏解释，不知道为什么产生信号

改造目标：
1. **策略配置更清晰** - 向导式流程，分步引导
2. **数据来源透明化** - 数据覆盖度可视化 + 股票/ETF数据预览
3. **信号结果可解释** - 信号原因说明 + 置信度计算逻辑 + 多维度分组统计 + 信号详情展开

---

## 二、UI设计方案

### 2.1 整体布局

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 ETF套利策略回测                                        步骤 1/4 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  进度指示器: ●━━━○━━━○━━━○                                       │
│             1.选择时间  2.配置策略  3.预览数据  4.查看结果       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     步骤内容区域                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [上一步]                    [下一步]  [开始回测]                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Step 1: 选择时间范围

**功能**：
- 快捷选项：近1个月、近3个月、近6个月、近1年、自定义
- 自定义日期选择器
- 显示预估处理时间和交易日数量

**UI元素**：
```html
快捷选择按钮组
├── [近1个月] [近3个月] [近6个月] [近1年]
│
自定义日期
├── 开始日期: [2024-01-01]
├── 结束日期: [2024-12-31]
│
ℹ️ 预计需要处理约 244 个交易日
```

### 2.3 Step 2: 配置策略参数

**功能**：
- 预设模板：保守型/平衡型/激进型
- 每个参数显示中文说明 + 推荐值
- 高级选项折叠隐藏

**策略模板定义**：

| 模板 | min_weight | min_etf_volume | evaluator_type | 说明 |
|------|------------|----------------|----------------|------|
| 保守型 | 8% | 8000万 | conservative | 更严格筛选，信号少但质量高 |
| 平衡型 | 5% | 5000万 | default | 推荐设置，平衡数量和质量 |
| 激进型 | 3% | 3000万 | aggressive | 更多信号，可能含低质量机会 |

**UI元素**：
```html
策略模板选择
├── ○ 保守型 - 更严格的筛选，信号少但质量高
├── ● 平衡型 - 推荐设置，平衡信号数量和质量
└── ○ 激进型 - 更多信号，可能包含低质量机会

高级选项 (可折叠)
├── 最小持仓权重: [5%]
│   ℹ️ ETF持有该股票的比例必须≥此值才会产生信号
├── 信号评估器: [平衡型 ▼]
│   ℹ️ 控制信号的置信度评分标准
└── 最小ETF成交额: [5000万元]
    ℹ️ 确保ETF有足够流动性可以交易
```

### 2.4 Step 3: 预览数据

**功能**：
- 数据覆盖度可视化（月度覆盖度条形图）
- 股票/ETF数据状态表格
- 数据质量评分

**UI元素**：
```html
📊 数据覆盖度评估
├── 数据来源: akshare (免费)
├── 数据质量: ★★★★☆ (B+)
├── 股票数据: 12/15 只有完整数据 ⚠️ 3只部分缺失
├── ETF数据: 8/10 个有完整数据 ✓
└── 交易日历覆盖:
    ├── 2024年1月 ████████████████████████████ 100%
    ├── 2024年2月 ████████████████████████████ 100%
    └── 2024年3月 ████████████████████░░░░░░░░ 85% ⚠️

📈 股票数据详情
┌──────────────────────────────────────────────────────┐
│ 股票代码  股票名称  数据点数  数据范围      状态      │
│──────────────────────────────────────────────────────│
│ 600519   贵州茅台  242 天    2024-01~12    ✓ 完整    │
│ 300750   宁德时代  242 天    2024-01~12    ✓ 完整    │
│ 000858   五粮液    180 天    2024-04~12    ⚠️ 部分缺失│
└──────────────────────────────────────────────────────┘

📊 ETF数据详情
└── [同上表格结构]
```

**数据状态定义**：
- ✓ 完整：数据点 > 90% 预期值
- ⚠️ 部分缺失：数据点 50%-90% 预期值
- ✗ 缺失/不足：数据点 < 50% 预期值

### 2.5 Step 4: 查看结果

**功能**：
- 总览统计卡片
- 多维度分组查看（按股票/按时间/按ETF）
- 信号详情展开弹窗
- 最常触发股票/ETF图表

**UI元素**：
```html
📊 总览统计
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│   总信号   │ │   高置信   │ │   中置信   │ │   低置信   │
│    47      │ │    18      │ │    22      │ │     7      │
└────────────┘ └────────────┘ └────────────┘ └────────────┘

回测期间: 2024-01-01 至 2024-12-31 (244个交易日)
策略配置: 平衡型 | 最小权重5% | 评估器: default

🔍 多维度查看
分组方式: [按股票 ▼]  [按时间]  [按ETF]

┌──────────────────────────────────────────────────────────┐
│ 📊 贵州茅台 (600519) - 共触发 8 次信号                  │
├──────────────────────────────────────────────────────────┤
│ 日期       ETF      权重   置信度   理由         [详情] │
│──────────────────────────────────────────────────────────│
│ 2024-03-15  510300   8.5%   高     涨停+流动充足  [展开]│
│ 2024-05-20  510300   8.2%   高     涨停+流动充足  [展开]│
└──────────────────────────────────────────────────────────┘
```

### 2.6 信号详情弹窗

点击信号「展开」后显示：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📋 信号详情 - 2024-03-15 贵州茅台 → 沪深300ETF                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  💡 为什么产生这个信号？                                                │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ✅ 贵州茅台 (600519) 在 2024-03-15 涨停                           │ │
│  │     • 涨停价格: ¥1,850.00                                           │ │
│  │     • 封单量: ¥12.5 亿                                              │ │
│  │     • 距收盘时间: 2小时15分                                         │ │
│  │                                                                      │ │
│  │  ✅ 沪深300ETF (510300) 持有该股票                                 │ │
│  │     • 持仓权重: 8.5% (超过5%阈值 ✓)                                 │ │
│  │     • ETF成交额: ¥8,500万 (超过5000万阈值 ✓)                        │ │
│  │     • 当前价格: ¥4.12                                               │ │
│  │                                                                      │ │
│  │  ✅ 数据来源可靠                                                    │ │
│  │     • 股票数据: akshare 完整 ✓                                      │ │
│  │     • ETF数据:  akshare 完整 ✓                                      │ │
│  │     • 持仓数据: 季度快照+线性插值                                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  📊 置信度评分详解                                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  总分: 85分 (高置信度)                                              │ │
│  │                                                                      │ │
│  │  封单量评分     ████████████████████  90分                         │ │
│  │  权重评分       ██████████████████    85分                         │ │
│  │  流动性评分     ████████████████████  88分                         │ │
│  │  距收盘评分     ████████████░░░░░░░░░  70分                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、技术实现方案

### 3.1 后端API改造

#### 新增API端点

```python
# 策略模板API
GET    /api/backtest/templates
       → 返回保守型/平衡型/激进型模板配置

# 数据预览API
POST   /api/backtest/preview
       → 请求：日期范围、策略参数
       → 返回：preview_id（异步处理）

GET    /api/backtest/preview/{preview_id}
       → 返回：数据覆盖度、股票/ETF数据状态、质量评分

# 信号详情API
GET    /api/backtest/{backtest_id}/signals/{signal_id}
       → 返回：单个信号的完整解释信息
```

#### 修改现有API

```python
# 回测启动API（增强返回信息）
POST   /api/backtest/start
       → 返回增加：预估完成时间、数据质量信息

# 回测结果API（增加分组字段）
GET    /api/backtest/{backtest_id}
       → 返回增加：按股票/ETF/时间分组的信号
```

### 3.2 数据模型定义

#### 策略模板模型

```python
@dataclass
class StrategyTemplate:
    """策略模板"""
    id: str  # conservative, balanced, aggressive
    name: str  # 保守型, 平衡型, 激进型
    description: str
    min_weight: float
    min_etf_volume: float  # 万元
    min_order_amount: float  # 亿元
    evaluator_type: str

STRATEGY_TEMPLATES = {
    "conservative": StrategyTemplate(
        id="conservative",
        name="保守型",
        description="更严格的筛选，信号少但质量高",
        min_weight=0.08,
        min_etf_volume=8000,
        min_order_amount=15,
        evaluator_type="conservative"
    ),
    "balanced": StrategyTemplate(
        id="balanced",
        name="平衡型",
        description="推荐设置，平衡信号数量和质量",
        min_weight=0.05,
        min_etf_volume=5000,
        min_order_amount=10,
        evaluator_type="default"
    ),
    "aggressive": StrategyTemplate(
        id="aggressive",
        name="激进型",
        description="更多信号，可能包含低质量机会",
        min_weight=0.03,
        min_etf_volume=3000,
        min_order_amount=5,
        evaluator_type="aggressive"
    ),
}
```

#### 数据预览响应模型

```python
@dataclass
class DataPreviewResponse:
    """数据预览响应"""
    preview_id: str
    date_range: DateRange

    # 数据覆盖度
    coverage: DataCoverage

    # 股票数据状态
    stocks_status: List[StockDataStatus]

    # ETF数据状态
    etfs_status: List[ETFDataStatus]

    # 数据质量评分
    quality_score: QualityScore

@dataclass
class DataCoverage:
    """数据覆盖度"""
    trading_days_total: int
    trading_days_covered: int
    coverage_percentage: float
    monthly_coverage: List[MonthCoverage]
    missing_dates: List[str]

@dataclass
class MonthCoverage:
    """月度覆盖度"""
    year: int
    month: int
    total_days: int
    covered_days: int
    percentage: float

@dataclass
class StockDataStatus:
    """股票数据状态"""
    code: str
    name: str
    data_points: int
    expected_points: int
    date_range: DateRange
    status: Literal["complete", "partial", "missing"]
    missing_dates: List[str]

@dataclass
class QualityScore:
    """数据质量评分"""
    overall_score: int  # 0-100
    grade: str  # A+, A, B+, B, C, D
    stocks_complete_rate: float
    etfs_complete_rate: float
    trading_days_coverage: float
```

#### 信号详情响应模型

```python
@dataclass
class SignalDetailResponse:
    """信号详情（带解释）"""
    signal: TradingSignal

    # 为什么产生这个信号
    reason: SignalReason

    # 置信度评分详情
    confidence_breakdown: ConfidenceBreakdown

    # 数据来源说明
    data_sources: DataSourceInfo

@dataclass
class SignalReason:
    """信号产生原因"""
    stock_limit_up: LimitUpInfo
    etf_holdings: ETFHoldingInfo
    liquidity_check: LiquidityInfo

    # 所有通过的检查项
    all_checks_passed: List[str]

    # 警告信息
    warnings: List[str]

@dataclass
class ConfidenceBreakdown:
    """置信度评分详解"""
    total_score: int
    level: Literal["high", "medium", "low"]

    # 各项评分
    order_amount_score: ScoreItem
    weight_score: ScoreItem
    liquidity_score: ScoreItem
    time_to_close_score: ScoreItem

@dataclass
class ScoreItem:
    """评分项"""
    name: str
    score: int  # 0-100
    weight: float  # 该项在总分中的权重
    value: float  # 原始值
    threshold: float  # 阈值
```

### 3.3 前端组件结构

```
frontend/
├── js/
│   └── backtest-wizard.js          # 新增：向导式回测控制器
│       ├── BacktestWizard           # 主控制器类
│       ├── Step1_DateRange          # 步骤1：日期选择
│       ├── Step2_StrategyConfig     # 步骤2：策略配置
│       ├── Step3_DataPreview        # 步骤3：数据预览
│       ├── Step4_Results            # 步骤4：结果展示
│       └── components/
│           ├── DataCoverageChart    # 数据覆盖度图表
│           ├── SignalDetailModal    # 信号详情弹窗
│           ├── SignalGroupView      # 信号分组视图
│           └── ConfidenceBar        # 置信度可视化组件
│
├── index.html                       # 修改：回测Tab改用向导组件
└── css/
    └── backtest-wizard.css          # 新增：向导样式
```

### 3.4 前端主控制器设计

```javascript
class BacktestWizard {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.data = {
            // 步骤1: 日期范围
            dateRange: {
                startDate: null,
                endDate: null,
                preset: null
            },
            // 步骤2: 策略配置
            strategy: {
                template: 'balanced',
                minWeight: 0.05,
                minEtfVolume: 5000,
                evaluatorType: 'default'
            },
            // 步骤3: 数据预览
            preview: {
                previewId: null,
                coverage: null,
                stocksStatus: [],
                etfsStatus: []
            },
            // 步骤4: 回测结果
            result: {
                backtestId: null,
                signals: [],
                statistics: null
            }
        };
    }

    // 步骤导航
    goToStep(step) { /* ... */ }
    nextStep() { /* ... */ }
    prevStep() { /* ... */ }

    // 步骤1方法
    selectDateRange(startDate, endDate) { /* ... */ }
    selectPreset(preset) { /* ... */ }

    // 步骤2方法
    selectTemplate(templateId) { /* ... */ }
    updateStrategyParam(key, value) { /* ... */ }

    // 步骤3方法
    async loadPreview() { /* ... */ }
    renderDataCoverage() { /* ... */ }
    renderStocksTable() { /* ... */ }

    // 步骤4方法
    async startBacktest() { /* ... */ }
    pollProgress() { /* ... */ }
    renderResults() { /* ... */ }
    showSignalDetail(signalId) { /* ... */ }
}
```

### 3.5 数据流设计

```
用户操作流程：

[Step 1] 选择日期
    ↓ 用户点击快捷选项或自定义日期
    保存到 this.data.dateRange
    ↓ 用户点击"下一步"

[Step 2] 选择策略模板
    ↓ 用户选择模板
    自动填充参数到表单
    ↓ 用户可手动调整高级选项
    保存到 this.data.strategy
    ↓ 用户点击"下一步"

[Step 3] 点击"预览数据"
    ↓ POST /api/backtest/preview
    {
        date_range: {...},
        strategy: {...}
    }
    ↓
    后台创建预览任务（异步）
    返回 preview_id
    ↓
    轮询 GET /api/backtest/preview/{preview_id}
    ↓
    显示：
    - 数据覆盖度图表
    - 股票/ETF状态表
    - 质量评分
    ↓
    用户确认数据OK → 点击"开始回测"

[Step 4] POST /api/backtest/start
    ↓
    实时显示进度条 + 当前处理日期
    轮询 GET /api/backtest/{backtest_id}
    ↓
    完成后显示结果
    - 分组展示信号（按股票/时间/ETF）
    - 点击信号 → 展开详情弹窗
```

---

## 四、实现计划

### 阶段一：核心向导流程（优先）

**后端**：
1. 创建 `StrategyTemplate` 模型和常量定义
2. 实现 `GET /api/backtest/templates` API
3. 实现 `POST /api/backtest/preview` API
4. 实现数据预览服务（数据加载、覆盖度计算）

**前端**：
1. 创建 `BacktestWizard` 主控制器
2. 实现 Step 1（日期选择）UI
3. 实现 Step 2（策略配置）UI，包含模板选择
4. 实现 Step 3（数据预览）基本表格
5. 实现 Step 4（结果展示）基础版本

### 阶段二：增强功能

**后端**：
1. 实现 `GET /api/backtest/{backtest_id}/signals/{signal_id}` API
2. 扩展回测结果，增加按分组统计
3. 实现置信度评分拆解逻辑

**前端**：
1. 实现数据覆盖度可视化图表
2. 实现信号详情弹窗组件
3. 实现多维度切换（按时间/按ETF）
4. 实现置信度评分可视化组件

### 阶段三：优化完善

1. 性能优化（大数据量场景）
2. 错误处理优化
3. 移动端适配
4. 导出功能增强

---

## 五、文件结构

### 后端新增/修改文件

```
backend/
├── api/
│   └── app.py                        # 修改：新增preview、templates等API
│
├── backtest/
│   ├── engine.py                     # 修改：增加数据预览功能
│   ├── data_preview.py               # 新增：数据预览服务
│   └── strategy_templates.py         # 新增：策略模板定义
│
└── domain/
    └── value_objects.py              # 修改：增加SignalReason等数据类
```

### 前端新增/修改文件

```
frontend/
├── index.html                        # 修改：回测Tab改用向导组件
│
├── js/
│   ├── backtest-wizard.js            # 新增：向导主控制器
│   └── backtest-wizard/
│       ├── Step1_DateRange.js
│       ├── Step2_StrategyConfig.js
│       ├── Step3_DataPreview.js
│       ├── Step4_Results.js
│       └── components/
│           ├── DataCoverageChart.js
│           ├── SignalDetailModal.js
│           ├── SignalGroupView.js
│           └── ConfidenceBar.js
│
└── css/
    └── backtest-wizard.css           # 新增：向导样式
```

---

## 六、配置变更

### 新增配置文件

`config/backtest_templates.yaml`:
```yaml
templates:
  conservative:
    name: "保守型"
    description: "更严格的筛选，信号少但质量高"
    min_weight: 0.08
    min_etf_volume: 8000  # 万元
    min_order_amount: 15  # 亿元
    evaluator_type: "conservative"

  balanced:
    name: "平衡型"
    description: "推荐设置，平衡信号数量和质量"
    min_weight: 0.05
    min_etf_volume: 5000
    min_order_amount: 10
    evaluator_type: "default"

  aggressive:
    name: "激进型"
    description: "更多信号，可能包含低质量机会"
    min_weight: 0.03
    min_etf_volume: 3000
    min_order_amount: 5
    evaluator_type: "aggressive"
```

---

## 七、验收标准

### 功能验收

1. **向导流程**
   - [ ] 4个步骤可以正常切换
   - [ ] 步骤之间数据正确传递
   - [ ] 上一步/下一步按钮状态正确

2. **策略配置**
   - [ ] 选择模板后参数自动填充
   - [ ] 手动修改参数后保持修改
   - [ ] 高级选项可以展开/收起

3. **数据预览**
   - [ ] 正确显示数据覆盖度
   - [ ] 股票/ETF状态表正确显示
   - [ ] 数据质量评分准确

4. **结果展示**
   - [ ] 信号可以按不同维度分组
   - [ ] 点击信号可展开详情
   - [ ] 详情弹窗信息完整

### 用户体验验收

1. **小白用户可用**
   - [ ] 不需要查文档就能完成回测
   - [ ] 所有专业术语有说明
   - [ ] 错误信息友好易懂

2. **可观测性**
   - [ ] 数据来源清楚
   - [ ] 数据质量可评估
   - [ ] 信号产生原因可解释

3. **性能**
   - [ ] 数据预览响应 < 5秒
   - [ ] 回测进度实时更新
   - [ ] 大量信号时页面不卡顿
