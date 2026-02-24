/**
 * ETF Arbitrage Terminal - Main Entry Point
 *
 * Application initialization and bootstrap
 */

async function init() {
    // Initialize navigation
    initNavigation();

    // Initialize search
    SearchUI.init();

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
                await StockUI.loadStocks();
                break;
            case 'limitup':
                await LimitUpUI.loadLimitUpStocks();
                break;
            case 'signals':
                await SignalUI.loadSignals();
                break;
            case 'backtest':
                BacktestUI.initDates();
                await loadBacktestJobs();
                break;
        }
    }

    // Close modal on outside click
    const modal = document.getElementById('etfModal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            StockUI.closeEtfModal();
        }
    });

    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            StockUI.closeEtfModal();
        }
    });
}

// Start the application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
