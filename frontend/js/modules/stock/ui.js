/**
 * Stock Module - UI
 *
 * Rendering and interaction for stock table
 */

const StockUI = {
    /**
     * Load stocks into table
     */
    async loadStocks() {
        showTableLoading('stocksTableBody', Config.TABLE.STOCKS_COLUMNS);

        try {
            const stocks = await StockService.getStocks();
            AppState.data.stocks = stocks;
            this.renderStocksTable(stocks);
        } catch (error) {
            showTableError('stocksTableBody', '加载失败', Config.TABLE.STOCKS_COLUMNS);
        }
    },

    /**
     * Render stocks table
     * @param {Array} stocks - Array of stock objects
     */
    renderStocksTable(stocks) {
        renderTableBody('stocksTableBody', stocks, this.createStockTableRow, Config.TABLE.STOCKS_COLUMNS);

        // Update refresh time
        const refreshTimeEl = document.getElementById('stocksRefreshTime');
        if (refreshTimeEl) {
            refreshTimeEl.textContent = `更新: ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`;
        }

        // Initialize sorting
        CommonUI.initTableSorting('stocksTableBody', 'stocks');
    },

    /**
     * Create table row for stock
     * @param {Object} stock - Stock object
     * @param {boolean} isLimitUp - Whether this is a limit-up stock
     */
    createStockTableRow(stock, isLimitUp = false) {
        const changeClass = stock.change_percent >= 0 ? 'up' : 'down';
        const changeIcon = stock.change_percent >= 0 ? '↑' : '↓';
        const limitUpClass = stock.is_limit_up ? 'limit-up-badge' : '';
        const limitUpText = stock.is_limit_up ? '涨停' : '';

        return `
            <tr class="${limitUpClass}">
                <td>
                    <button class="terminal-btn terminal-action-btn" onclick="StockUI.showRelatedETFs('${stock.code}', '${stock.name}')">
                        ${stock.code}
                    </button>
                </td>
                <td>${stock.name}</td>
                <td class="price-cell">${stock.current_price ? stock.current_price.toFixed(2) : '-'}</td>
                <td class="${changeClass}">
                    ${changeIcon} ${Math.abs(stock.change_percent).toFixed(2)}%
                </td>
                <td>${stock.volume ? (stock.volume / 10000).toFixed(0) + '万' : '-'}</td>
                <td>${stock.is_limit_up ? '<span class="terminal-badge terminal-badge-success">涨停</span>' : '-'}</td>
            </tr>
        `;
    },

    /**
     * Show related ETFs modal
     * @param {string} code - Stock code
     * @param {string} name - Stock name
     */
    async showRelatedETFs(code, name) {
        const modal = document.getElementById('etfModal');
        const title = document.getElementById('etfModalTitle');
        const body = document.getElementById('etfModalBody');

        // Save the currently focused element to return focus later
        AppState.lastFocusedElement = document.activeElement;

        title.textContent = `${name} (${code}) - 相关ETF`;
        body.innerHTML = Templates.loading('加载中...');
        modal.classList.add('active');

        // Focus the close button for keyboard users
        const closeButton = modal.querySelector('.modal-close');
        if (closeButton) {
            closeButton.focus();
        }

        try {
            const etfs = await StockService.getRelatedETFs(code);

            if (!etfs || etfs.length === 0) {
                body.innerHTML = Templates.empty('未找到相关ETF');
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
                        ${etfs.map(this.createEtfTableRow).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            body.innerHTML = Templates.error('加载失败');
        }
    },

    /**
     * Create table row for ETF
     * @param {Object} etf - ETF object
     */
    createEtfTableRow(etf) {
        const changeClass = etf.change_percent >= 0 ? 'up' : 'down';
        const changeIcon = etf.change_percent >= 0 ? '↑' : '↓';

        return `
            <tr>
                <td>
                    <button class="terminal-btn terminal-action-btn" onclick="StockUI.showRelatedETFs('${etf.code}', '${etf.name}')">
                        ${etf.code}
                    </button>
                </td>
                <td>${etf.name}</td>
                <td>${etf.weight ? (etf.weight * 100).toFixed(2) + '%' : '-'}</td>
                <td class="price-cell">${etf.current_price ? etf.current_price.toFixed(2) : '-'}</td>
                <td class="${changeClass}">
                    ${changeIcon} ${Math.abs(etf.change_percent).toFixed(2)}%
                </td>
            </tr>
        `;
    },

    /**
     * Close ETF modal
     */
    closeEtfModal() {
        const modal = document.getElementById('etfModal');
        modal.classList.remove('active');

        // Return focus to the button that opened the modal
        if (AppState.lastFocusedElement) {
            AppState.lastFocusedElement.focus();
            AppState.lastFocusedElement = null;
        }
    }
};
