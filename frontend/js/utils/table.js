/**
 * ETF Arbitrage Terminal - Shared Table Helpers
 *
 * Common table rendering and formatting utilities
 */

// Constants for formatting
const AMOUNT_UNITS = {
    YI: 100000000,
    WAN: 10000
};

/**
 * Get CSS class for price based on change percentage
 * @param {number} changePct - The change percentage
 * @returns {string} - The CSS class ('up', 'down', or '')
 */
function getPriceClass(changePct) {
    if (changePct > 0) return 'up';
    if (changePct < 0) return 'down';
    return '';
}

/**
 * Format price with sign
 * @param {number} changePct - The change percentage
 * @returns {string} - Formatted percentage with sign
 */
function formatPercentage(changePct) {
    if (changePct === undefined || changePct === null) return '-';
    const sign = changePct > 0 ? '+' : '';
    return `${sign}${changePct.toFixed(2)}%`;
}

/**
 * Format amount to Chinese units (亿/万)
 * @param {number} amount - The amount to format
 * @returns {string} - Formatted amount string
 */
function formatAmount(amount) {
    if (!amount) return '-';
    if (amount >= AMOUNT_UNITS.YI) {
        return (amount / AMOUNT_UNITS.YI).toFixed(2) + '亿';
    }
    return (amount / AMOUNT_UNITS.WAN).toFixed(2) + '万';
}

/**
 * Format price value
 * @param {number} price - The price to format
 * @returns {string} - Formatted price string
 */
function formatPrice(price) {
    return price ? price.toFixed(2) : '-';
}

/**
 * Get status badge HTML
 * @param {boolean} isLimitUp - Whether the stock is limit-up
 * @returns {string} - Badge HTML string
 */
function getStatusBadge(isLimitUp) {
    return isLimitUp
        ? '<span class="terminal-badge limitup">涨停</span>'
        : '<span class="terminal-badge normal">正常</span>';
}

/**
 * Get action button HTML for showing related ETFs
 * @param {string} code - Stock code
 * @param {string} name - Stock name
 * @returns {string} - Button HTML string
 */
function getEtfActionButton(code, name) {
    return `
        <button class="terminal-action-btn" onclick="showRelatedETFs('${code}', '${name}')">
            <i class="bi bi-list-ul"></i> ETF
        </button>
    `;
}

/**
 * Create table row HTML for stock/limitup tables
 * @param {Object} stock - Stock data object
 * @param {boolean} isLimitUp - Whether this is a limit-up table (includes amount/turnover)
 * @returns {string} - Table row HTML
 */
function createStockTableRow(stock, isLimitUp = false) {
    const priceClass = getPriceClass(stock.change_pct);
    const formattedPercent = formatPercentage(stock.change_pct);
    const formattedPrice = formatPrice(stock.price);

    if (isLimitUp) {
        // Limit-up table row with limit time
        const limitTime = stock.limit_time || '-';

        return `
            <tr>
                <td><span class="terminal-table-code">${stock.code}</span></td>
                <td><span class="terminal-table-name">${stock.name}</span></td>
                <td><span class="terminal-table-price ${priceClass}">${formattedPrice}</span></td>
                <td><span class="terminal-table-percent ${priceClass}">${formattedPercent}</span></td>
                <td>${limitTime}</td>
                <td>${getEtfActionButton(stock.code, stock.name)}</td>
            </tr>
        `;
    }

    // Watchlist table row with status badge
    return `
        <tr>
            <td><span class="terminal-table-code">${stock.code}</span></td>
            <td><span class="terminal-table-name">${stock.name}</span></td>
            <td><span class="terminal-table-price ${priceClass}">${formattedPrice}</span></td>
            <td><span class="terminal-table-percent ${priceClass}">${formattedPercent}</span></td>
            <td>${getStatusBadge(stock.is_limit_up)}</td>
            <td>${getEtfActionButton(stock.code, stock.name)}</td>
        </tr>
    `;
}

/**
 * Create ETF table row for modal
 * @param {Object} etf - ETF data object
 * @returns {string} - Table row HTML
 */
function createEtfTableRow(etf) {
    const weightClass = etf.weight >= 0.1 ? 'text-up' : etf.weight >= 0.05 ? '' : 'text-muted';
    const priceClass = getPriceClass(etf.change_pct);
    const percentSign = etf.change_pct > 0 ? '+' : '';
    const changePercent = etf.change_pct !== undefined ? `${percentSign}${etf.change_pct.toFixed(2)}%` : '-';

    return `
        <tr>
            <td><span class="terminal-table-code">${etf.etf_code}</span></td>
            <td><span class="terminal-table-name">${etf.etf_name || '-'}</span></td>
            <td><span class="${weightClass}">${(etf.weight * 100).toFixed(2)}%</span></td>
            <td><span class="terminal-table-price ${priceClass}">${formatPrice(etf.price)}</span></td>
            <td><span class="terminal-table-percent ${priceClass}">${changePercent}</span></td>
        </tr>
    `;
}

/**
 * Render table body with rows
 * @param {string} tbodyId - The ID of the tbody element
 * @param {Array} data - Array of data objects
 * @param {Function} rowFn - Function to create row HTML
 * @param {number} colSpan - Number of columns for empty/loading states
 */
function renderTableBody(tbodyId, data, rowFn, colSpan = 6) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;

    if (!data || data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="${colSpan}">
                    <div class="terminal-empty">
                        <i class="bi bi-inbox"></i>
                        <div class="terminal-empty-text">暂无数据</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = data.map(item => rowFn(item)).join('');
}

/**
 * Show loading state in table body
 * @param {string} tbodyId - The ID of the tbody element
 * @param {number} colSpan - Number of columns for the loading cell
 */
function showTableLoading(tbodyId, colSpan = 6) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="${colSpan}">
                <div class="terminal-loading">
                    <div class="terminal-loading-spinner"></div>
                    <div class="terminal-loading-text">加载中...</div>
                </div>
            </td>
        </tr>
    `;
}

/**
 * Show error state in table body
 * @param {string} tbodyId - The ID of the tbody element
 * @param {string} message - Error message to display
 * @param {number} colSpan - Number of columns for the error cell
 */
function showTableError(tbodyId, message = '加载失败', colSpan = 6) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="${colSpan}">
                <div class="terminal-empty">
                    <i class="bi bi-exclamation-triangle"></i>
                    <div class="terminal-empty-text">${message}</div>
                </div>
            </td>
        </tr>
    `;
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getPriceClass,
        formatPercentage,
        formatAmount,
        formatPrice,
        getStatusBadge,
        getEtfActionButton,
        createStockTableRow,
        createEtfTableRow,
        renderTableBody,
        showTableLoading,
        showTableError,
        AMOUNT_UNITS
    };
}
