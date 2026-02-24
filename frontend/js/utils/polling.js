/**
 * ETF Arbitrage Terminal - Polling Manager
 *
 * Manages polling operations with automatic cleanup
 */

class PollingManager {
    /**
     * Create a new polling manager
     * @param {Object} options - Configuration options
     * @param {Function} options.callback - Function to call on each interval
     * @param {number} options.interval - Polling interval in milliseconds
     * @param {boolean} options.immediate - Whether to call immediately on start
     * @param {Function} options.condition - Optional condition to continue polling
     */
    constructor(options = {}) {
        this.callback = options.callback || (() => {});
        this.interval = options.interval || 5000;
        this.immediate = options.immediate !== false;
        this.condition = options.condition || (() => true);
        this.timerId = null;
        this.isRunning = false;
    }

    /**
     * Start polling
     */
    start() {
        if (this.isRunning) {
            return;
        }

        this.isRunning = true;

        // Call immediately if configured
        if (this.immediate) {
            this.execute();
        }

        // Set up interval
        this.timerId = setInterval(() => {
            if (this.condition()) {
                this.execute();
            } else {
                this.stop();
            }
        }, this.interval);
    }

    /**
     * Stop polling
     */
    stop() {
        if (!this.isRunning) {
            return;
        }

        if (this.timerId) {
            clearInterval(this.timerId);
            this.timerId = null;
        }

        this.isRunning = false;
    }

    /**
     * Execute the callback
     */
    async execute() {
        try {
            await this.callback();
        } catch (error) {
            console.error('Polling callback error:', error);
        }
    }

    /**
     * Check if polling is running
     */
    isActive() {
        return this.isRunning;
    }

    /**
     * Update the interval and restart if running
     */
    setInterval(newInterval) {
        const wasRunning = this.isRunning;
        if (wasRunning) {
            this.stop();
        }
        this.interval = newInterval;
        if (wasRunning) {
            this.start();
        }
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PollingManager };
}
