/**
 * ETF Arbitrage Terminal - Core Configuration
 *
 * Centralized application configuration constants
 */

const Config = {
    // Polling intervals (milliseconds)
    POLLING: {
        STATUS: 5000,           // Status check interval
        BACKTEST: 3000,         // Backtest status check interval
        SEARCH_DEBOUNCE: 300    // Search input debounce
    },

    // Table configuration
    TABLE: {
        STOCKS_COLUMNS: 6,      // Number of columns in stocks table
        LIMITUP_COLUMNS: 6,     // Number of columns in limit-up table
    },

    // API endpoints
    API: {
        STATUS: '/api/status',
        STOCKS: '/api/stocks',
        LIMIT_UP: '/api/limit-up',
        SIGNALS: '/api/signals',
        MONITOR_START: '/api/monitor/start',
        MONITOR_STOP: '/api/monitor/stop',
        MONITOR_SCAN: '/api/monitor/scan',
        BACKTEST_START: '/api/backtest/start',
        BACKTEST_STATUS: '/api/backtest',
        BACKTEST_JOBS: '/api/backtest/jobs',
        BACKTEST_RESULT: '/api/backtest/result',
        BACKTEST_SIGNALS: '/api/backtest/signals',
        WATCHLIST: '/api/watchlist',
        WATCHLIST_ADD: '/api/watchlist/add',
        WATCHLIST_DELETE: '/api/watchlist',
    },

    // Display thresholds
    THRESHOLDS: {
        MIN_WEIGHT_FOR_SIGNAL: 0.05,  // 5% minimum weight for signal
        MAX_RECENT_SIGNALS: 20,        // Maximum recent signals to display
        MAX_SIGNALS_PER_GROUP: 50,     // Maximum signals per group
    },

    // UI timeouts
    TIMEOUT: {
        TOAST: 3000,                  // Toast display duration
        MODAL_TRANSITION: 300,        // Modal animation duration
        LOADING_MINIMUM: 500,         // Minimum loading display time
    },

    // Date formats
    DATE: {
        TIME_FORMAT: 'HH:mm:ss',
        DATE_FORMAT: 'YYYY/MM/DD',
        DATETIME_FORMAT: 'YYYY-MM-DD HH:mm:ss',
    },

    // Validation
    VALIDATION: {
        STOCK_CODE_PATTERN: /^\d{6}$/,
        STOCK_CODE_LENGTH: 6,
    }
};
