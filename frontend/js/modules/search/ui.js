/**
 * Search Module - UI
 *
 * Rendering and interaction for stock search
 */

const SearchUI = {
    debouncedSearch: null,

    /**
     * Initialize search functionality
     */
    init() {
        // Create debounced search function
        this.debouncedSearch = DOMUtils.debounce((query) => {
            this.performSearch(query);
        }, Config.POLLING.SEARCH_DEBOUNCE);
    },

    /**
     * Handle search input event
     * @param {Event} event - Input event
     */
    handleSearch(event) {
        const input = event.target;
        const query = input.value.trim();
        const resultsContainer = document.getElementById('searchResults');

        // Clear results if empty
        if (query.length === 0) {
            resultsContainer.innerHTML = '';
            return;
        }

        // Debounce search
        this.debouncedSearch(query);
    },

    /**
     * Perform stock search
     * @param {string} query - Search query
     */
    async performSearch(query) {
        const resultsContainer = document.getElementById('searchResults');

        // Check if query is valid stock code
        if (!Config.VALIDATION.STOCK_CODE_PATTERN.test(query)) {
            resultsContainer.innerHTML = `
                <div style="padding: var(--space-md); background: var(--terminal-panel-light); border: 1px solid var(--terminal-border); border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 12px; color: var(--status-inactive);">
                    请输入完整6位股票代码添加到自选股<br>
                    <span style="color: var(--electric-blue);">示例: 600519</span>
                </div>
            `;
            return;
        }

        // Show add button for valid stock code
        resultsContainer.innerHTML = `
            <button class="terminal-btn terminal-btn-primary" style="margin-top: var(--space-sm);" onclick="SearchUI.addStockToWatchlist('${query}')">
                <i class="bi bi-plus"></i> 添加 ${query} 到自选股
            </button>
        `;
    },

    /**
     * Add stock to watchlist
     * @param {string} code - Stock code
     */
    async addStockToWatchlist(code) {
        try {
            // First get stock info to validate code
            const stocks = await API.getStocks();
            const stock = stocks.find(s => s.code === code);

            const response = await SearchService.addToWatchlist(code, stock?.name || '');

            if (response.status === 'already_exists') {
                showToast(response.message, 'warning');
            } else if (response.status === 'success') {
                showToast(response.message, 'success');
                // Reload stocks to show the newly added stock
                await StockUI.loadStocks();
            } else {
                showToast('添加失败', 'error');
            }
        } catch (error) {
            console.error('Failed to add stock to watchlist:', error);
            showToast('添加失败', 'error');
        }
    }
};
