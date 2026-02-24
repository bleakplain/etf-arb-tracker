/**
 * Signal Module - Service
 *
 * API calls for trading signals
 */

const SignalService = {
    /**
     * Get all trading signals
     */
    async getSignals() {
        return await API.getSignals();
    }
};
