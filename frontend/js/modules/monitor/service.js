/**
 * Monitor Module - Service
 *
 * API calls for monitor control
 */

const MonitorService = {
    /**
     * Start continuous monitoring
     */
    async startMonitor() {
        return await API.startMonitor();
    },

    /**
     * Stop continuous monitoring
     */
    async stopMonitor() {
        return await API.stopMonitor();
    },

    /**
     * Trigger manual scan
     */
    async manualScan() {
        return await API.manualScan();
    }
};
