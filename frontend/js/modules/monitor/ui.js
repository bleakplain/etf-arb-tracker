/**
 * Monitor Module - UI
 *
 * Rendering and interaction for monitor controls
 */

const MonitorUI = {
    polling: null,

    /**
     * Start monitor
     */
    async startMonitor() {
        const btn = document.getElementById('btnStart');
        const stopBtn = document.getElementById('btnStop');
        const grid = document.querySelector('.terminal-grid');

        try {
            await MonitorService.startMonitor();
            AppState.monitor.isRunning = true;

            if (btn) btn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;

            this.updateStatusBadge(true);

            // Add visual monitoring state
            if (grid) grid.classList.add('monitoring-active');

            // Start polling for status
            this.startStatusPolling();

            // Show live indicator
            const liveIndicator = document.getElementById('liveIndicator');
            if (liveIndicator) liveIndicator.style.display = 'inline-flex';
        } catch (error) {
            console.error('Failed to start monitor:', error);
            showToast('启动监控失败', 'error');
        }
    },

    /**
     * Stop monitor
     */
    async stopMonitor() {
        const btn = document.getElementById('btnStart');
        const stopBtn = document.getElementById('btnStop');
        const grid = document.querySelector('.terminal-grid');

        try {
            await MonitorService.stopMonitor();
            AppState.monitor.isRunning = false;

            if (btn) btn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;

            this.updateStatusBadge(false);

            // Remove visual monitoring state
            if (grid) grid.classList.remove('monitoring-active');

            // Stop polling
            this.stopStatusPolling();

            // Hide live indicator
            const liveIndicator = document.getElementById('liveIndicator');
            if (liveIndicator) liveIndicator.style.display = 'none';
        } catch (error) {
            console.error('Failed to stop monitor:', error);
            showToast('停止监控失败', 'error');
        }
    },

    /**
     * Manual scan
     */
    async manualScan() {
        const btn = document.getElementById('btnScan');

        try {
            DOMUtils.setButtonLoading('btnScan', true, '扫描中...');

            await MonitorService.manualScan();

            // Reload data
            await loadStatus();
            if (AppState.ui.currentTab === 'watchlist') {
                await StockUI.loadStocks();
            } else if (AppState.ui.currentTab === 'limitup') {
                await LimitUpUI.loadLimitUpStocks();
            }

            showToast('扫描完成', 'success');
        } catch (error) {
            console.error('Manual scan failed:', error);
            showToast('扫描失败', 'error');
        } finally {
            DOMUtils.setButtonLoading('btnScan', false);
        }
    },

    /**
     * Update status badge
     * @param {boolean} isRunning - Whether monitor is running
     */
    updateStatusBadge(isRunning) {
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
    },

    /**
     * Start status polling
     */
    startStatusPolling() {
        if (this.polling) {
            this.polling.stop();
        }

        this.polling = new PollingManager({
            callback: async () => {
                if (document.hidden) return;
                await loadStatus();
                if (AppState.ui.currentTab === 'watchlist') {
                    await StockUI.loadStocks();
                }
            },
            interval: Config.POLLING.STATUS
        });

        this.polling.start();
    },

    /**
     * Stop status polling
     */
    stopStatusPolling() {
        if (this.polling) {
            this.polling.stop();
            this.polling = null;
        }
    }
};
