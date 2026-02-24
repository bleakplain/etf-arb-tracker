/**
 * ETF Arbitrage Terminal - HTML Templates
 *
 * Reusable HTML template generators
 */

const Templates = {
    /**
     * Loading indicator HTML
     */
    loading(message = '加载中...') {
        return `
            <div class="terminal-loading">
                <div class="terminal-loading-spinner"></div>
                <div class="terminal-loading-text">${message}</div>
            </div>
        `;
    },

    /**
     * Empty state HTML
     */
    empty(message = '暂无数据', icon = 'bi-inbox') {
        return `
            <div class="terminal-empty">
                <i class="${icon}" style="font-size: 48px; color: var(--status-inactive);"></i>
                <div style="margin-top: var(--space-md); color: var(--status-inactive);">${message}</div>
            </div>
        `;
    },

    /**
     * Error state HTML
     */
    error(message = '加载失败') {
        return `
            <div class="terminal-error">
                <i class="bi bi-exclamation-triangle" style="font-size: 48px; color: var(--status-error);"></i>
                <div style="margin-top: var(--space-md); color: var(--status-error);">${message}</div>
            </div>
        `;
    },

    /**
     * Stock row HTML
     */
    stockRow(stock, index) {
        const changeClass = stock.change_pct >= 0 ? 'price-up' : 'price-down';
        const limitUpBadge = stock.is_limit_up ? '<span class="terminal-badge limitup">涨停</span>' : '';

        return `
            <tr class="${index % 2 === 0 ? 'even' : 'odd'}">
                <td>
                    <div class="stock-name">${stock.name || stock.code}</div>
                    <div class="stock-code">${stock.code}</div>
                </td>
                <td class="${changeClass}">${stock.price ? stock.price.toFixed(2) : '-'}</td>
                <td class="${changeClass}">${stock.change_pct ? (stock.change_pct * 100).toFixed(2) + '%' : '-'}</td>
                <td>${limitUpBadge}</td>
                <td>
                    <button class="terminal-btn terminal-btn-sm" onclick="showRelatedETFs('${stock.code}', '${stock.name || ''}')">
                        <i class="bi bi-list-ul"></i> 查看
                    </button>
                </td>
            </tr>
        `;
    },

    /**
     * Limit-up stock row HTML
     */
    limitUpRow(stock, index) {
        const changeClass = 'price-up';

        return `
            <tr class="${index % 2 === 0 ? 'even' : 'odd'}">
                <td>
                    <div class="stock-name">${stock.name || stock.code}</div>
                    <div class="stock-code">${stock.code}</div>
                </td>
                <td class="${changeClass}">${stock.price ? stock.price.toFixed(2) : '-'}</td>
                <td class="${changeClass}">${stock.change_pct ? (stock.change_pct * 100).toFixed(2) + '%' : '-'}</td>
                <td>${stock.limit_time || '-'}</td>
                <td>
                    <button class="terminal-btn terminal-btn-sm" onclick="showRelatedETFs('${stock.code}', '${stock.name || ''}')">
                        <i class="bi bi-list-ul"></i> 查看
                    </button>
                </td>
            </tr>
        `;
    },

    /**
     * Signal card HTML
     */
    signalCard(signal, index) {
        const confidenceClass = (s) => {
            if (s.confidence === '高') return 'confidence-high';
            if (s.confidence === '中') return 'confidence-medium';
            return 'confidence-low';
        };

        const confidenceText = (s) => {
            const score = s.confidence_score || s.evaluation_score || 0;
            return score.toFixed(2);
        };

        return `
            <div class="terminal-signal-card" style="animation-delay: ${index * 50}ms">
                <div class="terminal-signal-header">
                    <div class="terminal-signal-time">${signal.timestamp}</div>
                    <div class="terminal-signal-route">
                        <span>${signal.stock_code}</span>
                        <span style="margin: 0 var(--space-sm);">→</span>
                        <span>${signal.etf_code}</span>
                    </div>
                    <div class="terminal-signal-confidence ${confidenceClass(signal)}">
                        <i class="bi bi-lightning"></i>
                        ${confidenceText(signal)}
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
     * ETF list item HTML
     */
    etfItem(etf) {
        const changeClass = etf.change_pct >= 0 ? 'price-up' : 'price-down';
        const top10Badge = etf.in_top10 ? '<span class="terminal-badge success">前10</span>' : '';

        return `
            <div class="etf-item">
                <div class="etf-header">
                    <div class="etf-name">${etf.etf_name || etf.etf_code}</div>
                    <div class="etf-code">${etf.etf_code}</div>
                </div>
                <div class="etf-metrics">
                    <div class="etf-metric">
                        <span class="label">权重</span>
                        <span class="value ${(etf.weight * 100).toFixed(2)}%">${(etf.weight * 100).toFixed(2)}%</span>
                    </div>
                    <div class="etf-metric">
                        <span class="label">排名</span>
                        <span class="value">${etf.rank || '-'}</span>
                    </div>
                    <div class="etf-metric">
                        <span class="label">价格</span>
                        <span class="value ${changeClass}">${etf.price ? etf.price.toFixed(3) : '-'}</span>
                    </div>
                    <div class="etf-metric">
                        <span class="label">涨幅</span>
                        <span class="value ${changeClass}">${etf.change_pct ? (etf.change_pct * 100).toFixed(2) + '%' : '-'}</span>
                    </div>
                </div>
                <div class="etf-footer">
                    <span class="etf-category">${etf.category || '-'}</span>
                    ${top10Badge}
                </div>
            </div>
        `;
    }
};
