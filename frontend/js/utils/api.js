/**
 * ETF Arbitrage Terminal - Shared API Client
 *
 * Centralized API request handling with consistent error handling
 */

const API = {
    baseUrl: '',

    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
        const defaults = {
            headers: { 'Content-Type': 'application/json' }
        };

        try {
            const response = await fetch(url, { ...defaults, ...options });
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    },

    // Status endpoints
    getStatus() {
        return this.request('/api/status');
    },

    // Stock endpoints
    getStocks() {
        return this.request('/api/stocks');
    },

    getRelatedETFs(code) {
        return this.request(`/api/stocks/${code}/related-etfs`);
    },

    // Limit-up endpoints
    getLimitUpStocks() {
        return this.request('/api/limit-up');
    },

    // Signal endpoints
    getSignals() {
        return this.request('/api/signals');
    },

    // Monitor endpoints
    startMonitor() {
        return this.request('/api/monitor/start', { method: 'POST' });
    },

    stopMonitor() {
        return this.request('/api/monitor/stop', { method: 'POST' });
    },

    manualScan() {
        return this.request('/api/monitor/scan', { method: 'POST' });
    },

    // Backtest endpoints
    startBacktest(config) {
        return this.request('/api/backtest/start', {
            method: 'POST',
            body: JSON.stringify(config)
        });
    },

    getBacktestStatus(jobId) {
        return this.request(`/api/backtest/${jobId}`);
    },

    getBacktestJobs() {
        return this.request('/api/backtest/jobs');
    },

    getBacktestResult(jobId) {
        return this.request(`/api/backtest/${jobId}/result`);
    },

    getBacktestSignals(jobId) {
        return this.request(`/api/backtest/${jobId}/signals`);
    },

    deleteBacktestJob(jobId) {
        return this.request(`/api/backtest/${jobId}`, { method: 'DELETE' });
    },

    // Watchlist endpoints
    getWatchlist() {
        return this.request('/api/watchlist');
    },

    addToWatchlist(code, name, market = 'sh', notes = '') {
        return this.request('/api/watchlist/add', {
            method: 'POST',
            body: JSON.stringify({ code, name, market, notes })
        });
    },

    removeFromWatchlist(code) {
        return this.request(`/api/watchlist/${code}`, { method: 'DELETE' });
    }
};

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
