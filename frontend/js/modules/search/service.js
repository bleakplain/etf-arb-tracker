/**
 * Search Module - Service
 *
 * API calls for stock search functionality
 */

const SearchService = {
    /**
     * Add stock to watchlist
     * @param {string} code - Stock code
     * @param {string} name - Stock name
     */
    async addToWatchlist(code, name) {
        return await API.addToWatchlist(code, name, 'sh', '');
    }
};
