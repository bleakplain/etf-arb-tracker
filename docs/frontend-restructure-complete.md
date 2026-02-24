# Frontend 代码组织重构完成

## 实施摘要

本次重构将frontend代码从扁平结构转换为按业务域组织的模块化结构。

## 新目录结构

```
frontend/js/
├── core/                  # 核心层 (3个文件)
│   ├── config.js         # 应用配置常量
│   ├── state.js          # 全局状态管理
│   └── events.js         # 事件总线
│
├── utils/                 # 工具层 (6个文件)
│   ├── api.js            # API客户端
│   ├── dom.js            # DOM操作工具
│   ├── polling.js        # 轮询管理
│   ├── templates.js      # HTML模板
│   ├── table.js          # 表格工具
│   └── export.js         # 导出工具
│
├── components/            # 组件层 (1个文件)
│   └── toast.js          # Toast通知
│
├── modules/               # 业务模块层 (13个文件)
│   ├── navigation.js     # 导航管理
│   ├── time.js           # 时间和状态更新
│   ├── stock/            # 股票功能
│   │   ├── service.js    # API调用
│   │   └── ui.js         # UI渲染
│   ├── limitup/          # 涨停股功能
│   │   ├── service.js
│   │   └── ui.js
│   ├── signal/           # 信号功能
│   │   ├── service.js
│   │   └── ui.js
│   ├── monitor/          # 监控控制
│   │   ├── service.js
│   │   └── ui.js
│   ├── search/           # 搜索功能
│   │   ├── service.js
│   │   └── ui.js
│   ├── backtest/         # 回测功能
│   │   ├── service.js
│   │   └── ui.js
│   └── common/           # 共享UI
│       └── sorting.js    # 表格排序
│
└── main.js               # 应用入口 (~60行)
```

## 模块职责

### core/ - 核心层
- `config.js` - 所有配置常量（轮询间隔、API端点、阈值等）
- `state.js` - 全局应用状态（监控状态、回测状态、UI状态、数据缓存）
- `events.js` - 简单事件总线用于组件间通信

### utils/ - 工具层
- `api.js` - API客户端，封装所有HTTP请求
- `dom.js` - DOM操作工具（debounce、按钮loading状态等）
- `polling.js` - PollingManager类，统一轮询管理
- `templates.js` - 可重用HTML模板（loading、empty、error）
- `table.js` - 表格渲染工具
- `export.js` - CSV/JSON导出功能

### components/ - 组件层
- `toast.js` - Toast通知组件

### modules/ - 业务模块层
每个业务模块采用统一模式：
- `service.js` - 负责API调用和数据获取
- `ui.js` - 负责UI渲染和用户交互

**模块列表：**
- `stock/` - 自选股表格和相关ETF查看
- `limitup/` - 涨停股列表
- `signal/` - 交易信号卡片
- `monitor/` - 监控控制面板
- `search/` - 股票搜索和添加
- `backtest/` - 回测功能
- `common/sorting.js` - 表格排序共享逻辑

## 主要改进

### 1. 清晰的职责分离
- 每个文件只负责一个明确的功能
- service/ui分离：API调用与UI渲染解耦
- 业务域内聚：相关代码在同一目录

### 2. 易于定位
- 按业务域找代码，而不是按技术类型
- 例如：股票相关代码都在 `modules/stock/` 下

### 3. 易于扩展
- 添加新功能只需创建新的feature目录
- 遵循现有模式（service.js + ui.js）

### 4. 代码行数优化
- `main.js` 仅~60行（引导应用）
- 业务模块每个50-150行
- 从单个791行文件拆分为多个小文件

## 迁移前后对比

### 迁移前
```
app.js (791行) - 所有功能混合
backtest-wizard.js (576行) - 所有向导逻辑
shared/ (10个文件) - 扁平结构
modules/ (3个文件) - 部分工具
```

### 迁移后
```
main.js (~60行) - 仅引导应用
core/ (3个文件) - 核心功能
utils/ (6个文件) - 工具函数
components/ (1个文件) - UI组件
modules/ (13个文件) - 业务功能模块
```

## 保留的旧文件

以下文件暂时保留以确保兼容性：
- `app.js` - 旧主应用文件
- `backtest-wizard.js` - 旧向导文件
- `shared/` 目录 - 旧的共享工具

这些文件可以在确认新结构工作正常后删除。

## HTML更新

`index.html` 已更新为加载新结构：
```html
<!-- Core -->
<script src="/frontend/js/core/config.js"></script>
<script src="/frontend/js/core/state.js"></script>
<script src="/frontend/js/core/events.js"></script>
<!-- Utils -->
<script src="/frontend/js/utils/api.js"></script>
...
<!-- Feature Modules -->
<script src="/frontend/js/modules/stock/service.js"></script>
<script src="/frontend/js/modules/stock/ui.js"></script>
...
<!-- Main Entry Point -->
<script src="/frontend/js/main.js"></script>
```

## 函数命名更新

所有模块函数使用模块前缀：
- `StockUI.loadStocks()` 替代 `loadStocks()`
- `MonitorUI.startMonitor()` 替代 `startMonitor()`
- `SearchUI.handleSearch()` 替代 `searchStock()`
- 等等...

## 后续步骤

1. **测试** - 确保所有功能正常工作
2. **删除旧文件** - 移除 `app.js`, `backtest-wizard.js`, `shared/` 目录
3. **更新backtest.html** - 应用相同的新结构
4. **考虑ES6模块** - 可选：使用ES6 import/export替代全局变量
