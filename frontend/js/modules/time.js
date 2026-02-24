/**
 * ETF Arbitrage Terminal - Time Module
 *
 * Time and status updates
 */

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

async function loadBacktestJobs() {
    // Placeholder - backtest jobs loading
}

