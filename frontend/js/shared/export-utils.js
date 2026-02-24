/**
 * ETF Arbitrage Terminal - Export Utilities
 *
 * Common export functionality for data export
 */

const ExportUtils = {
    /**
     * Export backtest signals to CSV
     * @param {Array} signals - Array of signal objects
     * @param {string} filename - Optional filename
     */
    exportSignalsToCSV(signals, filename = 'backtest_signals.csv') {
        if (!signals || signals.length === 0) {
            showToast('没有数据可导出', 'warning');
            return;
        }

        // CSV header
        const headers = [
            '时间',
            '股票代码',
            '股票名称',
            '股票价格',
            'ETF代码',
            'ETF名称',
            'ETF权重',
            '置信度',
            '风险等级',
            '原因'
        ];

        // CSV rows
        const rows = signals.map(signal => [
            signal.timestamp || '',
            signal.stock_code || '',
            signal.stock_name || '',
            signal.stock_price ? signal.stock_price.toFixed(2) : '',
            signal.etf_code || '',
            signal.etf_name || '',
            signal.etf_weight ? (signal.etf_weight * 100).toFixed(2) + '%' : '',
            signal.confidence || '',
            signal.risk_level || '',
            signal.reason || ''
        ]);

        // Combine header and rows
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        // Create blob and download
        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        showToast('导出成功', 'success');
    },

    /**
     * Export data to JSON
     * @param {Array} data - Array of data objects
     * @param {string} filename - Optional filename
     */
    exportToJSON(data, filename = 'export.json') {
        if (!data || data.length === 0) {
            showToast('没有数据可导出', 'warning');
            return;
        }

        const jsonContent = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        showToast('导出成功', 'success');
    },

    /**
     * Export table data to CSV
     * @param {string} tableId - Table element ID
     * @param {string} filename - Optional filename
     */
    exportTableToCSV(tableId, filename) {
        const table = document.getElementById(tableId);
        if (!table) {
            showToast('找不到表格', 'error');
            return;
        }

        const rows = Array.from(table.querySelectorAll('tr'));
        if (rows.length === 0) {
            showToast('表格为空', 'warning');
            return;
        }

        const csvContent = rows.map(row => {
            const cells = Array.from(row.querySelectorAll('td, th'));
            return cells.map(cell => `"${cell.textContent.trim()}"`).join(',');
        }).join('\n');

        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename || `${tableId}.csv`;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        showToast('导出成功', 'success');
    }
};

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ExportUtils };
}
