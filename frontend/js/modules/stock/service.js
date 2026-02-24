/**
 * Stock Module - Service
 *
 * API calls for stock data
 */

const StockService = {
    /**
     * Get all stocks from watchlist
     */
    async getStocks() {
        return await API.getStocks();
    },

    /**
     * Get related ETFs for a stock
     * @param {string} code - Stock code
     */
    async getRelatedETFs(code) {
        return await API.getRelatedETFs(code);
    },

    /**
     * Add stock to watchlist
     * @param {string} code - Stock code
     * @param {string} name - Stock name
     */
    async addToWatchlist(code, name) {
        return await API.addToWatchlist(code, name, 'sh', '');
    }
};
