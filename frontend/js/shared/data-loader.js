/**
 * ETF Arbitrage Terminal - Data Loader
 *
 * Unified data loading with loading states and error handling
 */

/**
 * Load data with loading state management
 * @param {Object} options - Loading options
 * @param {Function} options.apiCall - API call function that returns data
 * @param {Function} options.renderFn - Function to render the data
 * @param {string} options.containerId - Container element ID
 * @param {Function} options.onSuccess - Optional success callback
 * @param {Function} options.onError - Optional error callback
 * @param {string} options.loadingMessage - Optional loading message
 * @param {string} options.errorMessage - Optional error message
 * @param {string} options.emptyMessage - Optional empty message
 * @returns {Promise<boolean>} - Success status
 */
async function loadDataWithState({
    apiCall,
    renderFn,
    containerId,
    onSuccess,
    onError,
    loadingMessage = '加载中...',
    errorMessage = '加载失败',
    emptyMessage = '暂无数据'
}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container not found: ${containerId}`);
        return false;
    }

    try {
        // Show loading state
        container.innerHTML = Templates.loading(loadingMessage);

        // Fetch data
        const data = await apiCall();

        // Check for empty data
        if (!data || (Array.isArray(data) && data.length === 0)) {
            container.innerHTML = Templates.empty(emptyMessage);
            return true;
        }

        // Render data
        container.innerHTML = renderFn(data);

        // Call success callback if provided
        if (onSuccess) {
            onSuccess(data);
        }

        return true;

    } catch (error) {
        console.error(`Data loading failed for ${containerId}:`, error);

        // Show error state
        container.innerHTML = Templates.error(errorMessage);

        // Call error callback if provided
        if (onError) {
            onError(error);
        }

        return false;
    }
}

/**
 * Load data for table with tbody
 * @param {Object} options - Loading options
 * @param {Function} options.apiCall - API call function
 * @param {Function} options.rowRenderer - Function to render a single row
 * @param {string} options.tbodyId - Table body element ID
 * @param {number} options.colspan - Column span for loading/error states
 * @param {Function} options.onSuccess - Optional success callback
 * @returns {Promise<boolean>} - Success status
 */
async function loadTableData({
    apiCall,
    rowRenderer,
    tbodyId,
    colspan = 1,
    onSuccess
}) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) {
        console.error(`Table body not found: ${tbodyId}`);
        return false;
    }

    try {
        // Show loading state
        tbody.innerHTML = `
            <tr>
                <td colspan="${colspan}">
                    ${Templates.loading()}
                </td>
            </tr>
        `;

        // Fetch data
        const data = await apiCall();

        // Check for empty data
        if (!data || (Array.isArray(data) && data.length === 0)) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${colspan}">
                        ${Templates.empty()}
                    </td>
                </tr>
            `;
            return true;
        }

        // Render rows
        tbody.innerHTML = data.map((item, index) => rowRenderer(item, index)).join('');

        // Store data for sorting
        if (tbodyId === 'stocksTableBody') {
            AppState.data.stocks = data;
        } else if (tbodyId === 'limitupTableBody') {
            AppState.data.limitupStocks = data;
        }

        // Call success callback if provided
        if (onSuccess) {
            onSuccess(data);
        }

        return true;

    } catch (error) {
        console.error(`Table data loading failed for ${tbodyId}:`, error);

        // Show error state
        tbody.innerHTML = `
            <tr>
                <td colspan="${colspan}">
                    ${Templates.error()}
                </td>
            </tr>
        `;

        return false;
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { loadDataWithState, loadTableData };
}
