/**
 * Backtest Module - UI
 *
 * Rendering and interaction for backtest functionality
 */

const BacktestUI = {
    polling: null,

    /**
     * Initialize backtest form dates
     */
    initDates() {
        const startDateInput = document.getElementById('backtestStartDate');
        const endDateInput = document.getElementById('backtestEndDate');

        if (!startDateInput || !endDateInput) return;

        // Set default date range (last 3 months)
        const end = new Date();
        const start = new Date();
        start.setMonth(start.getMonth() - 3);

        endDateInput.value = end.toISOString().split('T')[0];
        startDateInput.value = start.toISOString().split('T')[0];
    },

    /**
     * Start backtest
     */
    async startBacktest() {
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
        resultsContainer.innerHTML = Templates.loading('启动回测...');

        try {
            const result = await BacktestService.startBacktest(config);
            AppState.backtest.currentJob = result.job_id || result.backtest_id;

            // Start polling for status
            this.startStatusCheck();
        } catch (error) {
            console.error('Failed to start backtest:', error);
            resultsContainer.innerHTML = Templates.error(`启动回测失败: ${error.message}`);
        }
    },

    /**
     * Start backtest status polling
     */
    startStatusCheck() {
        if (this.polling) {
            this.polling.stop();
        }

        this.polling = new PollingManager({
            callback: async () => {
                const jobId = AppState.backtest.currentJob;
                if (!jobId) return false;

                try {
                    const status = await BacktestService.getBacktestStatus(jobId);

                    if (status.status === 'completed') {
                        await this.viewResult(jobId);
                        return false;
                    } else if (status.status === 'failed') {
                        const resultsContainer = document.getElementById('backtestResults');
                        resultsContainer.innerHTML = Templates.error(`回测失败: ${status.message || '未知错误'}`);
                        return false;
                    } else {
                        // Update progress
                        this.showProgress(status);
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

        this.polling.start();
    },

    /**
     * Show backtest progress
     * @param {Object} status - Status object
     */
    showProgress(status) {
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
    },

    /**
     * Stop status polling
     */
    stopStatusCheck() {
        if (this.polling) {
            this.polling.stop();
            this.polling = null;
        }
    },

    /**
     * View backtest result
     * @param {string} jobId - Backtest job ID
     */
    async viewResult(jobId) {
        const resultsContainer = document.getElementById('backtestResults');

        try {
            const result = await BacktestService.getBacktestResult(jobId);
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
                            <button class="terminal-btn terminal-btn-primary" onclick="BacktestUI.exportSignals('${jobId}')">
                                <i class="bi bi-download"></i> 导出信号 (CSV)
                            </button>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Failed to load backtest result:', error);
            resultsContainer.innerHTML = Templates.error('加载结果失败');
        }
    },

    /**
     * Export backtest signals
     * @param {string} jobId - Backtest job ID
     */
    async exportSignals(jobId) {
        try {
            const response = await BacktestService.getBacktestSignals(jobId);
            ExportUtils.exportSignalsToCSV(response, `backtest_signals_${jobId}.csv`);
        } catch (error) {
            console.error('Export failed:', error);
            showToast('导出失败', 'error');
        }
    }
};
