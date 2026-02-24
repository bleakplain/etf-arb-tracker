/**
 * ETF Arbitrage Terminal - Core State Management
 *
 * Centralized application state management
 */

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
