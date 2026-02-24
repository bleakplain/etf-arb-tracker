/**
 * Limit-Up Module - UI
 *
 * Rendering and interaction for limit-up stocks
 */

const LimitUpUI = {
    /**
     * Load limit-up stocks into table
     */
    async loadLimitUpStocks() {
        showTableLoading('limitupTableBody', Config.TABLE.LIMITUP_COLUMNS);

        try {
            const stocks = await LimitUpService.getLimitUpStocks();
            AppState.data.limitupStocks = stocks;
            this.renderLimitupTable(stocks);

            // Update badge count
            this.updateBadge('limitupBadge', stocks.length, stocks.length > 0);
            this.updateMetric('limitupCount', stocks.length);
        } catch (error) {
            showTableError('limitupTableBody', '加载失败', Config.TABLE.LIMITUP_COLUMNS);
        }
    },

    /**
     * Render limit-up stocks table
     * @param {Array} stocks - Array of stock objects
     */
    renderLimitupTable(stocks) {
        renderTableBody('limitupTableBody', stocks, (stock) => StockUI.createStockTableRow(stock, true), Config.TABLE.LIMITUP_COLUMNS);

        // Initialize sorting
        CommonUI.initTableSorting('limitupTableBody', 'limitup');
    },

    /**
     * Update badge count
     * @param {string} badgeId - Badge element ID
     * @param {number} count - Count to display
     * @param {boolean} isVisible - Whether badge should be visible
     */
    updateBadge(badgeId, count, isVisible) {
        const badge = document.getElementById(badgeId);
        if (badge) {
            badge.textContent = count;
            badge.style.display = isVisible ? 'inline-flex' : 'none';
        }
    },

    /**
     * Update metric value
     * @param {string} metricId - Metric element ID
     * @param {number} value - Value to display
     */
    updateMetric(metricId, value) {
        const metric = document.getElementById(metricId);
        if (metric) {
            metric.textContent = value;
        }
    }
};
