/**
 * ETF Arbitrage Terminal - Main Application
 *
 * A trading terminal-inspired interface for monitoring ETF arbitrage opportunities
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const AppState = {
    monitor: {
        isRunning: false,
        statusCheckInterval: null
    },
    backtest: {
        currentJob: null,
        statusCheckInterval: null
    },
    ui: {
        currentTab: 'watchlist',
        sortState: {
            stocks: { column: null, direction: null },
            limitup: { column: null, direction: null }
        }
    },
    data: {
        stocks: [],
        limitupStocks: [],
        signals: [],
        status: null
    },
    lastFocusedElement: null
};

// ============================================================================
// NAVIGATION
// ============================================================================

function initNavigation() {
    const navItems = document.querySelectorAll('.terminal-nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabName = item.dataset.tab;
            if (tabName) {
                switchTab(tabName);
            }
        });
    });
}

function switchTab(tabName) {
    // Update navigation
    document.querySelectorAll('.terminal-nav-item').forEach(item => {
        item.classList.remove('active');
        item.removeAttribute('aria-current');
        if (item.dataset.tab === tabName) {
            item.classList.add('active');
            item.setAttribute('aria-current', 'page');
        }
    });

    // Update tab panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
        if (pane.id === tabName) {
            pane.classList.add('active');
        }
    });

    AppState.ui.currentTab = tabName;

    // Load tab-specific data
    switch (tabName) {
        case 'watchlist':
            loadStocks();
            break;
        case 'limitup':
            loadLimitUpStocks();
            break;
        case 'signals':
            loadSignals();
            break;
        case 'backtest':
            initBacktestDates();
            loadBacktestJobs();
            break;
    }
}

// ============================================================================
// STATUS & TIME UPDATES
// ============================================================================

function updateCurrentTime() {
    const now = new Date();
    const timeEl = document.getElementById('currentTime');
    const dateEl = document.getElementById('currentDate');

    if (timeEl) {
        timeEl.textContent = now.toLocaleTimeString('zh-CN', { hour12: false });
    }

    if (dateEl) {
        dateEl.textContent = now.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        }).replace(/\//g, '/');
    }
}

function updateStatusBar(data) {
    // Update monitor status
    const statusDot = document.getElementById('monitorStatusDot');
    const statusText = document.getElementById('monitorStatusText');

    if (statusDot && statusText) {
        if (data.monitor_running) {
            statusDot.classList.add('active');
            statusText.textContent = 'RUNNING';
        } else {
            statusDot.classList.remove('active');
            statusText.textContent = 'STOPPED';
        }
    }

    // Update trading time status
    const tradingTimeEl = document.getElementById('tradingTimeStatus');
    if (tradingTimeEl && data.is_trading_time !== undefined) {
        tradingTimeEl.textContent = data.is_trading_time ? '交易中' : '非交易';
        tradingTimeEl.className = 'terminal-badge';
        if (data.is_trading_time) {
            tradingTimeEl.classList.add('limitup');
        } else {
            tradingTimeEl.classList.add('normal');
        }
    }

    // Update metrics
    updateMetric('stockCount', data.watchlist_count);
    updateMetric('limitupCount', data.limitup_count);
    updateMetric('etfCount', data.covered_etf_count);
    updateMetric('todaySignals', data.today_signals);

    // Update last scan time
    const lastScanEl = document.getElementById('lastScanTime');
    if (lastScanEl && data.last_scan_time) {
        lastScanEl.textContent = data.last_scan_time;
    }

    // Update badges
    updateBadge('limitupBadge', data.limitup_count, data.limitup_count > 0);
    updateBadge('signalsBadge', data.today_signals, data.today_signals > 0);
}

function updateMetric(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value !== undefined ? value : '-';
    }
}

function updateBadge(id, value, isAlert) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value !== undefined ? value : '0';
        el.classList.toggle('alert', isAlert);
    }
}

async function loadStatus() {
    try {
        const data = await API.getStatus();
        AppState.data.status = data;
        updateStatusBar(data);
    } catch (error) {
        console.error('Failed to load status:', error);
    }
}

// ============================================================================
// STOCKS TABLE
// ============================================================================

async function loadStocks() {
    const tbody = document.getElementById('stocksTableBody');
    if (!tbody) return;

    try {
        const stocks = await API.getStocks();
        AppState.data.stocks = stocks;
        renderStocksTable(stocks);
    } catch (error) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="terminal-empty">
                        <i class="bi bi-exclamation-triangle"></i>
                        <div class="terminal-empty-text">加载失败</div>
                    </div>
                </td>
            </tr>
        `;
    }
}

function renderStocksTable(stocks) {
    const tbody = document.getElementById('stocksTableBody');
    if (!tbody) return;

    if (!stocks || stocks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="terminal-empty">
                        <i class="bi bi-inbox"></i>
                        <div class="terminal-empty-text">暂无自选股</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = stocks.map(stock => {
        const priceClass = stock.change_pct > 0 ? 'up' : stock.change_pct < 0 ? 'down' : '';
        const percentClass = stock.change_pct > 0 ? 'up' : stock.change_pct < 0 ? 'down' : '';
        const percentSign = stock.change_pct > 0 ? '+' : '';
        const statusBadge = stock.is_limit_up
            ? '<span class="terminal-badge limitup">涨停</span>'
            : '<span class="terminal-badge normal">正常</span>';

        return `
            <tr>
                <td><span class="terminal-table-code">${stock.code}</span></td>
                <td><span class="terminal-table-name">${stock.name}</span></td>
                <td><span class="terminal-table-price ${priceClass}">${stock.price ? stock.price.toFixed(2) : '-'}</span></td>
                <td><span class="terminal-table-percent ${percentClass}">${stock.change_pct !== undefined ? percentSign + stock.change_pct.toFixed(2) + '%' : '-'}</span></td>
                <td>${statusBadge}</td>
                <td>
                    <button class="terminal-action-btn" onclick="showRelatedETFs('${stock.code}', '${stock.name}')">
                        <i class="bi bi-list-ul"></i> ETF
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Update refresh time
    const refreshTimeEl = document.getElementById('stocksRefreshTime');
    if (refreshTimeEl) {
        refreshTimeEl.textContent = `更新: ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`;
    }

    // Initialize sorting
    initTableSorting('stocksTableBody', 'stocks');
}

async function showRelatedETFs(code, name) {
    const modal = document.getElementById('etfModal');
    const title = document.getElementById('etfModalTitle');
    const body = document.getElementById('etfModalBody');

    // Save the currently focused element to return focus later
    AppState.lastFocusedElement = document.activeElement;

    title.textContent = `${name} (${code}) - 相关ETF`;
    body.innerHTML = `
        <div class="terminal-loading">
            <div class="terminal-loading-spinner"></div>
            <div class="terminal-loading-text">加载中...</div>
        </div>
    `;
    modal.classList.add('active');

    // Focus the close button for keyboard users
    const closeButton = modal.querySelector('.modal-close');
    if (closeButton) {
        closeButton.focus();
    }

    try {
        const etfs = await API.getRelatedETFs(code);

        if (!etfs || etfs.length === 0) {
            body.innerHTML = `
                <div class="terminal-empty">
                    <i class="bi bi-inbox"></i>
                    <div class="terminal-empty-text">未找到相关ETF</div>
                </div>
            `;
            return;
        }

        body.innerHTML = `
            <table class="terminal-table">
                <thead>
                    <tr>
                        <th>ETF代码</th>
                        <th>ETF名称</th>
                        <th>持仓权重</th>
                        <th>现价</th>
                        <th>涨跌幅</th>
                    </tr>
                </thead>
                <tbody>
                    ${etfs.map(etf => {
                        const weightClass = etf.weight >= 0.1 ? 'text-up' : etf.weight >= 0.05 ? '' : 'text-muted';
                        const priceClass = etf.change_pct > 0 ? 'up' : etf.change_pct < 0 ? 'down' : '';
                        const percentSign = etf.change_pct > 0 ? '+' : '';

                        return `
                            <tr>
                                <td><span class="terminal-table-code">${etf.etf_code}</span></td>
                                <td><span class="terminal-table-name">${etf.etf_name || '-'}</span></td>
                                <td><span class="${weightClass}">${(etf.weight * 100).toFixed(2)}%</span></td>
                                <td><span class="terminal-table-price ${priceClass}">${etf.price ? etf.price.toFixed(2) : '-'}</span></td>
                                <td><span class="terminal-table-percent ${priceClass}">${etf.change_pct !== undefined ? percentSign + etf.change_pct.toFixed(2) + '%' : '-'}</span></td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        body.innerHTML = `
            <div class="terminal-empty">
                <i class="bi bi-exclamation-triangle"></i>
                <div class="terminal-empty-text">加载失败</div>
            </div>
        `;
    }
}

function closeEtfModal() {
    const modal = document.getElementById('etfModal');
    modal.classList.remove('active');

    // Return focus to the button that opened the modal
    if (AppState.lastFocusedElement) {
        AppState.lastFocusedElement.focus();
        AppState.lastFocusedElement = null;
    }
}

// ============================================================================
// LIMIT-UP STOCKS
// ============================================================================

async function loadLimitUpStocks() {
    const tbody = document.getElementById('limitupTableBody');
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="7">
                <div class="terminal-loading">
                    <div class="terminal-loading-spinner"></div>
                    <div class="terminal-loading-text">加载中...</div>
                </div>
            </td>
        </tr>
    `;

    try {
        const stocks = await API.getLimitUpStocks();
        AppState.data.limitupStocks = stocks;
        renderLimitupTable(stocks);

        // Update badge count
        updateBadge('limitupBadge', stocks.length, stocks.length > 0);
        updateMetric('limitupCount', stocks.length);
    } catch (error) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7">
                    <div class="terminal-empty">
                        <i class="bi bi-exclamation-triangle"></i>
                        <div class="terminal-empty-text">加载失败</div>
                    </div>
                </td>
            </tr>
        `;
    }
}

function renderLimitupTable(stocks) {
    const tbody = document.getElementById('limitupTableBody');
    if (!tbody) return;

    if (!stocks || stocks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7">
                    <div class="terminal-empty">
                        <i class="bi bi-fire"></i>
                        <div class="terminal-empty-text">今日暂无涨停股</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = stocks.map(stock => {
        const amountStr = stock.amount
            ? (stock.amount >= 100000000
                ? (stock.amount / 100000000).toFixed(2) + '亿'
                : (stock.amount / 10000).toFixed(2) + '万')
            : '-';
        const turnoverStr = stock.turnover !== undefined ? stock.turnover.toFixed(2) + '%' : '-';

        return `
            <tr>
                <td><span class="terminal-table-code">${stock.code}</span></td>
                <td><span class="terminal-table-name">${stock.name}</span></td>
                <td><span class="terminal-table-price up">${stock.price ? stock.price.toFixed(2) : '-'}</span></td>
                <td><span class="terminal-table-percent up">+${stock.change_pct ? stock.change_pct.toFixed(2) : '-'}%</span></td>
                <td>${amountStr}</td>
                <td>${turnoverStr}</td>
                <td>
                    <button class="terminal-action-btn" onclick="showRelatedETFs('${stock.code}', '${stock.name}')">
                        <i class="bi bi-list-ul"></i> ETF
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Initialize sorting
    initTableSorting('limitupTableBody', 'limitup');
}

// ============================================================================
// SIGNALS
// ============================================================================

async function loadSignals() {
    const container = document.getElementById('signalsContainer');
    if (!container) return;

    try {
        const signals = await API.getSignals();
        AppState.data.signals = signals;
        renderSignals(signals);
    } catch (error) {
        container.innerHTML = `
            <div class="terminal-empty">
                <i class="bi bi-exclamation-triangle"></i>
                <div class="terminal-empty-text">加载失败</div>
            </div>
        `;
    }
}

function renderSignals(signals) {
    const container = document.getElementById('signalsContainer');
    if (!container) return;

    if (!signals || signals.length === 0) {
        container.innerHTML = `
            <div class="terminal-empty">
                <i class="bi bi-inbox"></i>
                <div class="terminal-empty-text">暂无信号</div>
            </div>
        `;
        return;
    }

    // Group signals by date
    const groupedSignals = {};
    signals.forEach(signal => {
        const date = signal.timestamp ? signal.timestamp.split('T')[0] : '未知日期';
        if (!groupedSignals[date]) {
            groupedSignals[date] = [];
        }
        groupedSignals[date].push(signal);
    });

    container.innerHTML = Object.entries(groupedSignals).map(([date, daySignals]) => {
        const confidenceClass = signal => {
            const level = signal.confidence_level || signal.evaluation_score;
            if (level >= 0.7) return 'high';
            if (level >= 0.4) return 'medium';
            return 'low';
        };

        const confidenceText = signal => {
            const level = signal.confidence_level || signal.evaluation_score;
            if (level >= 0.7) return 'HIGH';
            if (level >= 0.4) return 'MEDIUM';
            return 'LOW';
        };

        return `
            <div style="margin-bottom: var(--space-lg);">
                <div style="font-family: var(--font-mono); font-size: 12px; color: var(--status-inactive); margin-bottom: var(--space-sm);">${date}</div>
                ${daySignals.map(signal => `
                    <div class="terminal-signal-card ${confidenceClass(signal)}" style="margin-bottom: var(--space-md);">
                        <div class="terminal-signal-header">
                            <div class="terminal-signal-title">
                                <span style="color: var(--electric-blue);">${signal.stock_code}</span>
                                <span style="margin: 0 var(--space-sm);">→</span>
                                <span>${signal.etf_code}</span>
                            </div>
                            <div class="terminal-signal-confidence ${confidenceClass(signal)}">
                                <i class="bi bi-lightning"></i>
                                ${confidenceText(signal)}
                            </div>
                        </div>
                        <div class="terminal-signal-body">
                            <div class="terminal-signal-field">
                                <div class="terminal-signal-field-label">股票</div>
                                <div class="terminal-signal-field-value">${signal.stock_name || signal.stock_code}</div>
                            </div>
                            <div class="terminal-signal-field">
                                <div class="terminal-signal-field-label">ETF</div>
                                <div class="terminal-signal-field-value">${signal.etf_name || signal.etf_code}</div>
                            </div>
                            <div class="terminal-signal-field">
                                <div class="terminal-signal-field-label">权重</div>
                                <div class="terminal-signal-field-value">${signal.weight ? (signal.weight * 100).toFixed(2) + '%' : '-'}</div>
                            </div>
                            <div class="terminal-signal-field">
                                <div class="terminal-signal-field-label">置信度</div>
                                <div class="terminal-signal-field-value">${(signal.confidence_score || signal.evaluation_score || 0).toFixed(2)}</div>
                            </div>
                            ${signal.reason ? `
                                <div class="terminal-signal-field" style="grid-column: 1 / -1;">
                                    <div class="terminal-signal-field-label">原因</div>
                                    <div class="terminal-signal-field-value" style="font-size: 12px;">${signal.reason}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }).join('');

    // Update badge
    updateBadge('signalsBadge', signals.length, signals.length > 0);
}

// ============================================================================
// MONITOR CONTROLS
// ============================================================================

async function startMonitor() {
    const btn = document.getElementById('btnStart');
    const stopBtn = document.getElementById('btnStop');
    const grid = document.querySelector('.terminal-grid');

    try {
        await API.startMonitor();
        AppState.monitor.isRunning = true;

        if (btn) btn.disabled = true;
        if (stopBtn) stopBtn.disabled = false;

        updateStatusBadge(true);

        // Add visual monitoring state
        if (grid) grid.classList.add('monitoring-active');

        // Start polling for status
        startStatusPolling();

        // Show live indicator
        const liveIndicator = document.getElementById('liveIndicator');
        if (liveIndicator) liveIndicator.style.display = 'inline-flex';
    } catch (error) {
        console.error('Failed to start monitor:', error);
        showToast('启动监控失败', 'error');
    }
}

async function stopMonitor() {
    const btn = document.getElementById('btnStart');
    const stopBtn = document.getElementById('btnStop');
    const grid = document.querySelector('.terminal-grid');

    try {
        await API.stopMonitor();
        AppState.monitor.isRunning = false;

        if (btn) btn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;

        updateStatusBadge(false);

        // Remove visual monitoring state
        if (grid) grid.classList.remove('monitoring-active');

        // Stop polling
        stopStatusPolling();

        // Hide live indicator
        const liveIndicator = document.getElementById('liveIndicator');
        if (liveIndicator) liveIndicator.style.display = 'none';
    } catch (error) {
        console.error('Failed to stop monitor:', error);
        showToast('停止监控失败', 'error');
    }
}

async function manualScan() {
    const btn = document.getElementById('btnScan');

    try {
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<div class="terminal-loading-spinner" style="width: 16px; height: 16px;"></div> 扫描中...';
        }

        await API.manualScan();

        // Reload data
        await loadStatus();
        if (AppState.ui.currentTab === 'watchlist') {
            await loadStocks();
        } else if (AppState.ui.currentTab === 'limitup') {
            await loadLimitUpStocks();
        }

        showToast('扫描完成', 'success');
    } catch (error) {
        console.error('Manual scan failed:', error);
        showToast('扫描失败', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-search"></i> 立即扫描';
        }
    }
}

function updateStatusBadge(isRunning) {
    const statusDot = document.getElementById('monitorStatusDot');
    const statusText = document.getElementById('monitorStatusText');

    if (statusDot && statusText) {
        if (isRunning) {
            statusDot.classList.add('active');
            statusText.textContent = 'RUNNING';
        } else {
            statusDot.classList.remove('active');
            statusText.textContent = 'STOPPED';
        }
    }
}

function startStatusPolling() {
    if (AppState.monitor.statusCheckInterval) {
        clearInterval(AppState.monitor.statusCheckInterval);
    }

    // Define polling function
    const poll = async () => {
        // Skip if page is hidden
        if (document.hidden) return;

        await loadStatus();
        if (AppState.ui.currentTab === 'watchlist') {
            await loadStocks();
        }
    };

    AppState.monitor.statusCheckInterval = setInterval(poll, 5000);
}

function stopStatusPolling() {
    if (AppState.monitor.statusCheckInterval) {
        clearInterval(AppState.monitor.statusCheckInterval);
        AppState.monitor.statusCheckInterval = null;
    }
}

// ============================================================================
// STOCK SEARCH
// ============================================================================

let searchDebounceTimer = null;

function searchStock(event) {
    const input = event.target;
    const query = input.value.trim();
    const resultsContainer = document.getElementById('searchResults');

    // Clear previous timer
    if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
    }

    // Clear results if empty
    if (query.length === 0) {
        resultsContainer.innerHTML = '';
        return;
    }

    // Debounce search
    searchDebounceTimer = setTimeout(() => {
        performStockSearch(query, resultsContainer);
    }, 300);
}

async function performStockSearch(query, resultsContainer) {
    // This is a simplified search - in production, you'd call a search API
    // For now, just show a message
    resultsContainer.innerHTML = `
        <div style="padding: var(--space-md); background: var(--terminal-panel-light); border: 1px solid var(--terminal-border); border-radius: 4px; font-family: var(--font-mono); font-size: 12px; color: var(--status-inactive);">
            请输入完整6位股票代码添加到自选股<br>
            <span style="color: var(--electric-blue);">示例: 600519</span>
        </div>
    `;

    // If query is 6 digits, show add button
    if (/^\d{6}$/.test(query)) {
        resultsContainer.innerHTML = `
            <button class="terminal-btn terminal-btn-primary" style="margin-top: var(--space-sm);" onclick="addStockToWatchlist('${query}')">
                <i class="bi bi-plus"></i> 添加 ${query} 到自选股
            </button>
        `;
    }
}

async function addStockToWatchlist(code) {
    showToast(`添加股票 ${code} 功能需要后端支持`, 'info');
    // In production, this would call an API endpoint
}

// ============================================================================
// TABLE SORTING
// ============================================================================

function initTableSorting(tbodyId, tableType) {
    const table = document.querySelector(`#${tbodyId}`).closest('.terminal-table');
    if (!table) return;

    const headers = table.querySelectorAll('thead th.sortable');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            const type = header.dataset.type;

            // Update sort state
            const currentSort = AppState.ui.sortState[tableType];
            let direction = 'asc';

            if (currentSort.column === column) {
                if (currentSort.direction === 'asc') {
                    direction = 'desc';
                } else if (currentSort.direction === 'desc') {
                    // Clear sort
                    AppState.ui.sortState[tableType] = { column: null, direction: null };
                    headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                    return;
                }
            }

            AppState.ui.sortState[tableType] = { column, direction };

            // Update header classes
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            header.classList.add(direction === 'asc' ? 'sort-asc' : 'sort-desc');

            // Sort and re-render
            const data = tableType === 'stocks' ? AppState.data.stocks : AppState.data.limitupStocks;
            const sortedData = sortData(data, column, direction, type);

            if (tableType === 'stocks') {
                renderStocksTable(sortedData);
            } else {
                renderLimitupTable(sortedData);
            }
        });
    });
}

function sortData(data, column, direction, type) {
    const sorted = [...data];

    sorted.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];

        // Handle special cases
        if (type === 'boolean') {
            aVal = aVal ? 1 : 0;
            bVal = bVal ? 1 : 0;
        }

        if (aVal === undefined || aVal === null) aVal = '';
        if (bVal === undefined || bVal === null) bVal = '';

        // Compare
        if (typeof aVal === 'number' && typeof bVal === 'number') {
            return aVal - bVal;
        }

        return String(aVal).localeCompare(String(bVal), 'zh-CN');
    });

    return direction === 'desc' ? sorted.reverse() : sorted;
}

// ============================================================================
// BACKTEST
// ============================================================================

function initBacktestDates() {
    const startDateInput = document.getElementById('backtestStartDate');
    const endDateInput = document.getElementById('backtestEndDate');

    if (!startDateInput || !endDateInput) return;

    // Set default date range (last 3 months)
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 3);

    endDateInput.value = end.toISOString().split('T')[0];
    startDateInput.value = start.toISOString().split('T')[0];
}

async function startBacktest() {
    const startDateInput = document.getElementById('backtestStartDate');
    const endDateInput = document.getElementById('backtestEndDate');
    const granularityInput = document.getElementById('backtestGranularity');
    const minWeightInput = document.getElementById('backtestMinWeight');
    const evaluatorInput = document.getElementById('backtestEvaluator');
    const interpolationInput = document.getElementById('backtestInterpolation');

    if (!startDateInput.value || !endDateInput.value) {
        showToast('请选择日期范围', 'error');
        return;
    }

    const config = {
        start_date: startDateInput.value.replace(/-/g, ''),
        end_date: endDateInput.value.replace(/-/g, ''),
        granularity: granularityInput.value,
        min_weight: parseFloat(minWeightInput.value),
        evaluator_type: evaluatorInput.value,
        interpolation: interpolationInput.value
    };

    const resultsContainer = document.getElementById('backtestResults');
    resultsContainer.innerHTML = `
        <div class="terminal-loading">
            <div class="terminal-loading-spinner"></div>
            <div class="terminal-loading-text">启动回测...</div>
        </div>
    `;

    try {
        const result = await API.startBacktest(config);
        AppState.backtest.currentJob = result.job_id || result.backtest_id;

        // Start polling for status
        startBacktestStatusCheck();
    } catch (error) {
        console.error('Failed to start backtest:', error);
        resultsContainer.innerHTML = `
            <div class="terminal-empty">
                <i class="bi bi-exclamation-triangle"></i>
                <div class="terminal-empty-text">启动回测失败: ${error.message}</div>
            </div>
        `;
    }
}

function startBacktestStatusCheck() {
    if (AppState.backtest.statusCheckInterval) {
        clearInterval(AppState.backtest.statusCheckInterval);
    }

    checkBacktestStatus();
    AppState.backtest.statusCheckInterval = setInterval(checkBacktestStatus, 3000);
}

async function checkBacktestStatus() {
    const jobId = AppState.backtest.currentJob;
    if (!jobId) return;

    try {
        const status = await API.getBacktestStatus(jobId);

        if (status.status === 'completed') {
            stopBacktestStatusCheck();
            await viewBacktestResult(jobId);
            await loadBacktestJobs();
        } else if (status.status === 'failed') {
            stopBacktestStatusCheck();
            const resultsContainer = document.getElementById('backtestResults');
            resultsContainer.innerHTML = `
                <div class="terminal-empty">
                    <i class="bi bi-exclamation-triangle"></i>
                    <div class="terminal-empty-text">回测失败: ${status.message || '未知错误'}</div>
                </div>
            `;
        } else {
            // Update progress
            const resultsContainer = document.getElementById('backtestResults');
            const progress = status.progress !== undefined ? Math.round(status.progress * 100) : 0;
            resultsContainer.innerHTML = `
                <div class="terminal-panel">
                    <div class="terminal-panel-header">
                        <span class="terminal-panel-title">回测进行中</span>
                    </div>
                    <div class="terminal-panel-body">
                        <div class="progress" style="margin-bottom: var(--space-md);">
                            <div class="progress-bar" style="width: ${progress}%"></div>
                        </div>
                        <div style="text-align: center; font-family: var(--font-mono); font-size: 12px; color: var(--status-inactive);">
                            ${status.message || '处理中...'} (${progress}%)
                        </div>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to check backtest status:', error);
    }
}

function stopBacktestStatusCheck() {
    if (AppState.backtest.statusCheckInterval) {
        clearInterval(AppState.backtest.statusCheckInterval);
        AppState.backtest.statusCheckInterval = null;
    }
}

async function loadBacktestJobs() {
    // This would show a list of historical backtest jobs
    // For now, just keep the current view
}

async function viewBacktestResult(jobId) {
    const resultsContainer = document.getElementById('backtestResults');

    try {
        const result = await API.getBacktestResult(jobId);
        const stats = result.statistics || {};

        resultsContainer.innerHTML = `
            <div class="terminal-panel">
                <div class="terminal-panel-header">
                    <span class="terminal-panel-title">
                        <i class="bi bi-check-circle" style="color: var(--status-active);"></i>
                        回测完成
                    </span>
                    <span style="font-family: var(--font-mono); font-size: 11px; color: var(--status-inactive);">ID: ${jobId}</span>
                </div>
                <div class="terminal-panel-body">
                    <div class="terminal-metrics" style="margin-bottom: var(--space-lg);">
                        <div class="terminal-metric">
                            <div class="terminal-metric-value">${stats.total_signals || 0}</div>
                            <div class="terminal-metric-label">总信号</div>
                        </div>
                        <div class="terminal-metric">
                            <div class="terminal-metric-value up">${stats.high_confidence_count || 0}</div>
                            <div class="terminal-metric-label">高置信度</div>
                        </div>
                        <div class="terminal-metric">
                            <div class="terminal-metric-value" style="color: var(--status-warning);">${stats.medium_confidence_count || 0}</div>
                            <div class="terminal-metric-label">中置信度</div>
                        </div>
                        <div class="terminal-metric">
                            <div class="terminal-metric-value" style="color: var(--status-inactive);">${stats.low_confidence_count || 0}</div>
                            <div class="terminal-metric-label">低置信度</div>
                        </div>
                    </div>

                    <div class="terminal-btn-group">
                        <button class="terminal-btn terminal-btn-primary" onclick="exportBacktestSignals('${jobId}')">
                            <i class="bi bi-download"></i> 导出信号 (CSV)
                        </button>
                        <button class="terminal-btn terminal-action-btn" onclick="loadBacktestJobs()">
                            <i class="bi bi-arrow-clockwise"></i> 返回列表
                        </button>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load backtest result:', error);
        resultsContainer.innerHTML = `
            <div class="terminal-empty">
                <i class="bi bi-exclamation-triangle"></i>
                <div class="terminal-empty-text">加载结果失败</div>
            </div>
        `;
    }
}

async function exportBacktestSignals(jobId) {
    try {
        const response = await fetch(`/api/backtest/${jobId}/signals`);
        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `backtest_signals_${jobId}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);

        showToast('导出成功', 'success');
    } catch (error) {
        console.error('Export failed:', error);
        showToast('导出失败', 'error');
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

async function init() {
    // Initialize navigation
    initNavigation();

    // Start time updates
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // Load initial status
    await loadStatus();

    // Load initial data for active tab
    const activeTab = document.querySelector('.terminal-nav-item.active');
    if (activeTab) {
        const tabName = activeTab.dataset.tab;
        switch (tabName) {
            case 'watchlist':
                await loadStocks();
                break;
            case 'limitup':
                await loadLimitUpStocks();
                break;
            case 'signals':
                await loadSignals();
                break;
            case 'backtest':
                initBacktestDates();
                await loadBacktestJobs();
                break;
        }
    }

    // Close modal on outside click
    const modal = document.getElementById('etfModal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeEtfModal();
        }
    });

    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeEtfModal();
        }
    });
}

// Start the application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
