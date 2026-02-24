/**
 * ETF Arbitrage Terminal - Main Application
 *
 * A trading terminal-inspired interface for monitoring ETF arbitrage opportunities
 */

// ============================================================================
// STOCKS TABLE
// ============================================================================

async function loadStocks() {
    showTableLoading('stocksTableBody', Config.TABLE.STOCKS_COLUMNS);

    try {
        const stocks = await API.getStocks();
        AppState.data.stocks = stocks;
        renderStocksTable(stocks);
    } catch (error) {
        showTableError('stocksTableBody', '加载失败', Config.TABLE.STOCKS_COLUMNS);
    }
}

function renderStocksTable(stocks) {
    renderTableBody('stocksTableBody', stocks, createStockTableRow, Config.TABLE.STOCKS_COLUMNS);

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
    showTableLoading('limitupTableBody', Config.TABLE.LIMITUP_COLUMNS);

    try {
        const stocks = await API.getLimitUpStocks();
        AppState.data.limitupStocks = stocks;
        renderLimitupTable(stocks);

        // Update badge count
        updateBadge('limitupBadge', stocks.length, stocks.length > 0);
        updateMetric('limitupCount', stocks.length);
    } catch (error) {
        showTableError('limitupTableBody', '加载失败', Config.TABLE.LIMITUP_COLUMNS);
    }
}

function renderLimitupTable(stocks) {
    renderTableBody('limitupTableBody', stocks, (stock) => createStockTableRow(stock, true), Config.TABLE.LIMITUP_COLUMNS);

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
        DOMUtils.setButtonLoading('btnScan', true, '扫描中...');

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
        DOMUtils.setButtonLoading('btnScan', false);
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
    if (AppState.monitor.statusPolling) {
        AppState.monitor.statusPolling.stop();
    }

    AppState.monitor.statusPolling = new PollingManager({
        callback: async () => {
            if (document.hidden) return;
            await loadStatus();
            if (AppState.ui.currentTab === 'watchlist') {
                await loadStocks();
            }
        },
        interval: Config.POLLING.STATUS
    });

    AppState.monitor.statusPolling.start();
}

function stopStatusPolling() {
    if (AppState.monitor.statusPolling) {
        AppState.monitor.statusPolling.stop();
        AppState.monitor.statusPolling = null;
    }
}

// ============================================================================
// STOCK SEARCH
// ============================================================================

const debouncedSearch = DOMUtils.debounce(async (query, resultsContainer) => {
    performStockSearch(query, resultsContainer);
}, Config.POLLING.SEARCH_DEBOUNCE);

function searchStock(event) {
    const input = event.target;
    const query = input.value.trim();
    const resultsContainer = document.getElementById('searchResults');

    // Clear results if empty
    if (query.length === 0) {
        resultsContainer.innerHTML = '';
        return;
    }

    // Debounce search
    debouncedSearch(query, resultsContainer);
}

async function performStockSearch(query, resultsContainer) {
    // Check if query is valid stock code
    if (!Config.VALIDATION.STOCK_CODE_PATTERN.test(query)) {
        resultsContainer.innerHTML = `
            <div style="padding: var(--space-md); background: var(--terminal-panel-light); border: 1px solid var(--terminal-border); border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 12px; color: var(--status-inactive);">
                请输入完整6位股票代码添加到自选股<br>
                <span style="color: var(--electric-blue);">示例: 600519</span>
            </div>
        `;
        return;
    }

    // Show add button for valid stock code
    resultsContainer.innerHTML = `
        <button class="terminal-btn terminal-btn-primary" style="margin-top: var(--space-sm);" onclick="addStockToWatchlist('${query}')">
            <i class="bi bi-plus"></i> 添加 ${query} 到自选股
        </button>
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
    if (AppState.backtest.statusPolling) {
        AppState.backtest.statusPolling.stop();
    }

    AppState.backtest.statusPolling = new PollingManager({
        callback: async () => {
            const jobId = AppState.backtest.currentJob;
            if (!jobId) return false;

            try {
                const status = await API.getBacktestStatus(jobId);

                if (status.status === 'completed') {
                    await viewBacktestResult(jobId);
                    await loadBacktestJobs();
                    return false;
                } else if (status.status === 'failed') {
                    const resultsContainer = document.getElementById('backtestResults');
                    resultsContainer.innerHTML = `
                        <div class="terminal-empty">
                            <i class="bi bi-exclamation-triangle"></i>
                            <div class="terminal-empty-text">回测失败: ${status.message || '未知错误'}</div>
                        </div>
                    `;
                    return false;
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
                    return true;
                }
            } catch (error) {
                console.error('Failed to check backtest status:', error);
                return false;
            }
        },
        interval: Config.POLLING.BACKTEST,
        immediate: true
    });

    AppState.backtest.statusPolling.start();
}

function stopBacktestStatusCheck() {
    if (AppState.backtest.statusPolling) {
        AppState.backtest.statusPolling.stop();
        AppState.backtest.statusPolling = null;
    }
}

async function checkBacktestStatus() {
    // Deprecated: Use startBacktestStatusCheck() instead
    // Kept for backward compatibility
    if (!AppState.backtest.statusPolling) {
        startBacktestStatusCheck();
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
        const response = await API.getBacktestSignals(jobId);
        ExportUtils.exportSignalsToCSV(response, `backtest_signals_${jobId}.csv`);
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
