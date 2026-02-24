# Frontend 代码组织重构方案

## 当前结构分析

### 问题识别

1. **app.js 过大** (791行) - 包含8个不同的功能区域
   - 股票表格 (STOCKS TABLE)
   - 涨停股 (LIMIT-UP STOCKS)
   - 信号 (SIGNALS)
   - 监控控制 (MONITOR CONTROLS)
   - 股票搜索 (STOCK SEARCH)
   - 表格排序 (TABLE SORTING)
   - 回测 (BACKTEST)
   - 初始化 (INITIALIZATION)

2. **shared/ 目录扁平** - 10个文件平铺，缺少分组
   - 工具函数按功能分散
   - 缺少业务领域分组

3. **backtest-wizard.js 过大** (576行) - 单个文件包含所有向导逻辑

### 依赖关系分析

```
app.js 依赖:
├── modules/state.js
├── shared/table-helpers.js
├── shared/templates.js
├── shared/constants.js
└── shared/polling-manager.js

backtest-wizard.js 依赖:
├── shared/polling-manager.js
├── shared/export-utils.js
└── shared/templates.js
```

## 建议的新结构

### 按业务领域划分 (features/)

```
js/
├── core/
│   ├── state.js          # 应用状态管理
│   ├── config.js         # 配置常量
│   └── events.js         # 事件总线（新增）
│
├── utils/                 # 通用工具（重组shared/）
│   ├── api.js            # API客户端
│   ├── dom.js            # DOM操作
│   ├── polling.js        # 轮询管理
│   ├── templates.js      # HTML模板
│   ├── formatters.js     # 格式化工具
│   └── export.js         # 导出工具
│
├── components/           # UI组件
│   ├── toast.js          # Toast通知
│   ├── modal.js          # 模态框
│   └── loading.js        # 加载指示器
│
└── features/             # 业务功能
    ├── stocks/           # 股票功能
    │   ├── service.js     # 股票API调用
    │   ├── ui.js           # 渲染逻辑
    │   └── table.js       # 表格特定逻辑
    │
    ├── limitup/          # 涨停股功能
    │   ├── service.js     # 涨停股API调用
    │   ├── ui.js           # 渲染逻辑
    │   └── table.js       # 表格特定逻辑
    │
    ├── signals/          # 信号功能
    │   ├── service.js     # 信号API调用
    │   └── ui.js           # 渲染逻辑
    │
    ├── monitor/          # 监控控制
    │   ├── service.js     # 监控API调用
    │   └── ui.js           # 控制面板逻辑
    │
    ├── search/           # 搜索功能
    │   ├── service.js     # 搜索API
    │   └── ui.js           # 搜索结果
    │
    ├── backtest/          # 回测功能
    │   ├── service.js     # 回测API调用
    │   ├── wizard.js       # 向导逻辑
    │   ├── ui.js           # 结果显示
    │   └── export.js       # 导出功能
    │
    └── common/            # 共享UI功能
        ├── table-sorting.js # 表格排序
        └── modal.js          # 模态框管理
```

### 核心设计原则

1. **按业务领域分组** - 每个功能模块独立
2. **服务层分离** - service.js 负责API调用
3. **UI层分离** - ui.js 负责渲染逻辑
4. **共享组件** - common/ 存放共享功能

### 模块职责说明

**core/** - 核心层**
- `state.js` - 应用全局状态
- `config.js` - 配置常量
- `events.js` - 组件间通信

**utils/** - 工具层**
- `api.js` - API请求封装
- `dom.js` - DOM操作工具
- `polling.js` - 轮询管理
- `templates.js` - HTML模板
- `formatters.js` - 数据格式化
- `export.js` - 导出功能

**components/** - 组件层**
- `toast.js` - Toast通知组件
- `modal.js` - 模态框组件
- `loading.js` - 加载指示器

**features/** - 业务层**
每个业务功能模块包含：
- `service.js` - API调用和数据获取
- `ui.js` - UI渲染和交互
- `table.js` - 特定表格逻辑（如有）
- `wizard.js` - 向导逻辑（如需要）

**features/common/** - 共享UI**
- `table-sorting.js` - 表格排序
- `modal.js` - 模态框管理

## 迁移步骤

### 第一阶段：创建核心结构
1. 创建 `js/core/` 目录
2. 移动 `modules/state.js` → `core/state.js`
3. 移动 `shared/constants.js` → `core/config.js`
4. 创建 `js/events.js` 事件总线

### 第二阶段：重组工具层
1. 创建 `js/utils/` 目录
2. 移动所有 `shared/*` 到 `js/utils/`
3. 创建 `js/formatters.js` 整合格式化函数
4. 更新所有导入路径

### 第三阶段：拆分业务功能
1. 创建 `js/features/stocks/` - 从 app.js 提取股票相关代码
2. 创建 `js/features/limitup/` - 从 app.js 提取涨停股相关代码
3. 创建 `js/features/signals/` - 从 app.js 提取信号相关代码
4. 创建 `js/features/monitor/` - 从 app.js 提取监控相关代码
5. 创建 `js/features/search/` - 从 app.js 提取搜索相关代码
6. 创建 `js/features/backtest/` - 从 backtest-wizard.js 拆分
7. 创建 `js/features/common/` - 提取共享UI功能

### 第四阶段：组件化
1. 创建 `js/components/` 目录
2. 移动 `toast.js` → `components/toast.js`
3. 创建 `components/modal.js`
4. 创建 `components/loading.js`

### 第五阶段：清理
1. 删除旧的 `modules/` 和 `shared/` 目录
2. 更新 `index.html` 和 `backtest.html` 引用
3. 创建 `main.js` 作为应用入口
4. 删除或最小化 `app.js`

## 预期效果

### 代码组织改进

**之前**:
```
app.js (791 lines) - 所有功能混合
backtest-wizard.js (576 lines) - 所有向导逻辑
shared/ (10 files) - 扁平结构
modules/ (3 files) - 部分状态管理
```

**之后**:
```
main.js (~20 lines) - 仅引导应用
core/ (3 files) - 核心功能
utils/ (7 files) - 工具函数
components/ (3 files) - UI组件
features/ (8 domains) - 业务功能，每个50-100行
```

### 可维护性提升

1. **清晰的职责分离** - 每个文件只负责一个功能
2. **易于定位** - 按业务领域找代码，而不是按技术类型
3. **易于扩展** - 添加新功能只需在 features/ 下创建新目录
4. **易于测试** - 每个模块可独立测试

### 示例：添加新功能

**之前** - 需要在多个文件中添加代码：
```
app.js (添加功能逻辑)
shared/api-client.js (添加API方法)
shared/constants.js (添加常量)
shared/templates.js (添加模板)
```

**之后** - 只需在一个目录中添加：
```
features/new-feature/
  ├── service.js    # API调用
  ├── ui.js          # UI渲染
  └── table.js      # 表格逻辑
```
