/**
 * ETF Arbitrage Terminal - Navigation Module
 *
 * Tab navigation management
 */

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
            StockUI.loadStocks();
            break;
        case 'limitup':
            LimitUpUI.loadLimitUpStocks();
            break;
        case 'signals':
            SignalUI.loadSignals();
            break;
        case 'backtest':
            BacktestUI.initDates();
            break;
    }
}
