/**
 * Backtest Module - Service
 *
 * API calls for backtest functionality
 */

const BacktestService = {
    /**
     * Start backtest
     * @param {Object} config - Backtest configuration
     */
    async startBacktest(config) {
        return await API.startBacktest(config);
    },

    /**
     * Get backtest status
     * @param {string} jobId - Backtest job ID
     */
    async getBacktestStatus(jobId) {
        return await API.getBacktestStatus(jobId);
    },

    /**
     * Get backtest result
     * @param {string} jobId - Backtest job ID
     */
    async getBacktestResult(jobId) {
        return await API.getBacktestResult(jobId);
    },

    /**
     * Get backtest signals
     * @param {string} jobId - Backtest job ID
     */
    async getBacktestSignals(jobId) {
        return await API.getBacktestSignals(jobId);
    },

    /**
     * Get all backtest jobs
     */
    async getBacktestJobs() {
        return await API.getBacktestJobs();
    }
};
