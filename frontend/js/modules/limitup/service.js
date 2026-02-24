/**
 * Limit-Up Module - Service
 *
 * API calls for limit-up stock data
 */

const LimitUpService = {
    /**
     * Get all limit-up stocks
     */
    async getLimitUpStocks() {
        return await API.getLimitUpStocks();
    }
};
