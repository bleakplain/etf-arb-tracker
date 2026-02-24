/**
 * Signal Module - UI
 *
 * Rendering and interaction for trading signals
 */

const SignalUI = {
    /**
     * Load signals into container
     */
    async loadSignals() {
        const container = document.getElementById('signalsContainer');
        if (!container) return;

        try {
            const signals = await SignalService.getSignals();
            AppState.data.signals = signals;
            this.renderSignals(signals);
        } catch (error) {
            container.innerHTML = Templates.error('加载失败');
        }
    },

    /**
     * Render signals grouped by date
     * @param {Array} signals - Array of signal objects
     */
    renderSignals(signals) {
        const container = document.getElementById('signalsContainer');
        if (!container) return;

        if (!signals || signals.length === 0) {
            container.innerHTML = Templates.empty('暂无信号', 'bi-inbox');
            return;
        }

        // Group signals by date
        const groupedSignals = {};
        signals.forEach(signal => {
            const date = signal.timestamp ? signal.timestamp.split('T')[0] : '未知日期';
            if (!groupedSignals[date]) {
                groupedSignals[date] = [];
            }
            groupedSignals[date].push(signal);
        });

        container.innerHTML = Object.entries(groupedSignals).map(([date, daySignals]) => {
            return `
                <div style="margin-bottom: var(--space-lg);">
                    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--status-inactive); margin-bottom: var(--space-sm);">${date}</div>
                    ${daySignals.map(signal => this.createSignalCard(signal)).join('')}
                </div>
            `;
        }).join('');

        // Update badge
        this.updateBadge('signalsBadge', signals.length, signals.length > 0);
    },

    /**
     * Create signal card HTML
     * @param {Object} signal - Signal object
     */
    createSignalCard(signal) {
        const confidenceClass = this.getConfidenceClass(signal);
        const confidenceText = this.getConfidenceText(signal);

        return `
            <div class="terminal-signal-card ${confidenceClass}" style="margin-bottom: var(--space-md);">
                <div class="terminal-signal-header">
                    <div class="terminal-signal-title">
                        <span style="color: var(--electric-blue);">${signal.stock_code}</span>
                        <span style="margin: 0 var(--space-sm);">→</span>
                        <span>${signal.etf_code}</span>
                    </div>
                    <div class="terminal-signal-confidence ${confidenceClass}">
                        <i class="bi bi-lightning"></i>
                        ${confidenceText}
                    </div>
                </div>
                <div class="terminal-signal-body">
                    <div class="terminal-signal-field">
                        <div class="terminal-signal-field-label">股票</div>
                        <div class="terminal-signal-field-value">${signal.stock_name || signal.stock_code}</div>
                    </div>
                    <div class="terminal-signal-field">
                        <div class="terminal-signal-field-label">ETF</div>
                        <div class="terminal-signal-field-value">${signal.etf_name || signal.etf_code}</div>
                    </div>
                    <div class="terminal-signal-field">
                        <div class="terminal-signal-field-label">权重</div>
                        <div class="terminal-signal-field-value">${signal.weight ? (signal.weight * 100).toFixed(2) + '%' : '-'}</div>
                    </div>
                    <div class="terminal-signal-field">
                        <div class="terminal-signal-field-label">置信度</div>
                        <div class="terminal-signal-field-value">${(signal.confidence_score || signal.evaluation_score || 0).toFixed(2)}</div>
                    </div>
                    ${signal.reason ? `
                        <div class="terminal-signal-field" style="grid-column: 1 / -1;">
                            <div class="terminal-signal-field-label">原因</div>
                            <div class="terminal-signal-field-value" style="font-size: 12px;">${signal.reason}</div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    },

    /**
     * Get confidence class for styling
     * @param {Object} signal - Signal object
     */
    getConfidenceClass(signal) {
        const level = signal.confidence_level || signal.evaluation_score;
        if (level >= 0.7) return 'high';
        if (level >= 0.4) return 'medium';
        return 'low';
    },

    /**
     * Get confidence text
     * @param {Object} signal - Signal object
     */
    getConfidenceText(signal) {
        const level = signal.confidence_level || signal.evaluation_score;
        if (level >= 0.7) return 'HIGH';
        if (level >= 0.4) return 'MEDIUM';
        return 'LOW';
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
    }
};
