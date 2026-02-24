/**
 * Common Module - Table Sorting
 *
 * Shared table sorting functionality
 */

const CommonUI = {
    /**
     * Initialize table sorting
     * @param {string} tbodyId - Table body element ID
     * @param {string} tableType - Table type for state management
     */
    initTableSorting(tbodyId, tableType) {
        const table = document.querySelector(`#${tbodyId}`).closest('.terminal-table');
        if (!table) return;

        const headers = table.querySelectorAll('thead th.sortable');
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const column = header.dataset.sort;
                const type = header.dataset.type;

                // Update sort state
                const currentSort = AppState.ui.sortState[tableType];
                let direction = 'asc';

                if (currentSort.column === column) {
                    if (currentSort.direction === 'asc') {
                        direction = 'desc';
                    } else if (currentSort.direction === 'desc') {
                        // Clear sort
                        AppState.ui.sortState[tableType] = { column: null, direction: null };
                        headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                        return;
                    }
                }

                AppState.ui.sortState[tableType] = { column, direction };

                // Update header classes
                headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                header.classList.add(direction === 'asc' ? 'sort-asc' : 'sort-desc');

                // Sort and re-render
                const data = tableType === 'stocks' ? AppState.data.stocks : AppState.data.limitupStocks;
                const sortedData = this.sortData(data, column, direction, type);

                if (tableType === 'stocks') {
                    StockUI.renderStocksTable(sortedData);
                } else {
                    LimitUpUI.renderLimitupTable(sortedData);
                }
            });
        });
    },

    /**
     * Sort data array
     * @param {Array} data - Data to sort
     * @param {string} column - Column name
     * @param {string} direction - Sort direction ('asc' or 'desc')
     * @param {string} type - Data type
     */
    sortData(data, column, direction, type) {
        const sorted = [...data];

        sorted.sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];

            // Handle special cases
            if (type === 'boolean') {
                aVal = aVal ? 1 : 0;
                bVal = bVal ? 1 : 0;
            }

            if (aVal === undefined || aVal === null) aVal = '';
            if (bVal === undefined || bVal === null) bVal = '';

            // Compare
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return aVal - bVal;
            }

            return String(aVal).localeCompare(String(bVal), 'zh-CN');
        });

        return direction === 'desc' ? sorted.reverse() : sorted;
    }
};
