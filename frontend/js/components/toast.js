/**
 * ETF Arbitrage Terminal - Shared Toast Component
 *
 * Consistent toast notifications across all pages
 */

// Add toast animations to page
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    @keyframes toast-in {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes toast-out {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(20px);
        }
    }
`;
document.head.appendChild(toastStyles);

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - One of: 'success', 'error', 'warning', 'info'
 */
function showToast(message, type = 'info') {
    const colors = {
        success: 'var(--market-up)',
        error: 'var(--market-down)',
        warning: 'var(--status-warning)',
        info: 'var(--electric-blue)'
    };

    const icons = {
        success: 'bi-check-circle',
        error: 'bi-exclamation-triangle',
        warning: 'bi-exclamation-circle',
        info: 'bi-info-circle'
    };

    const toast = document.createElement('div');
    toast.className = 'terminal-toast';
    toast.style.cssText = `
        position: fixed;
        bottom: var(--space-lg);
        right: var(--space-lg);
        padding: var(--space-md) var(--space-lg);
        background: var(--terminal-panel);
        border: 1px solid var(--terminal-border);
        border-left-width: 4px;
        border-left-color: ${colors[type] || colors.info};
        border-radius: 4px;
        font-family: var(--font-mono);
        font-size: 13px;
        z-index: 10000;
        animation: toast-in 0.3s ease-out;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    `;

    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: var(--space-sm);">
            <i class="bi ${icons[type] || icons.info}" style="color: ${colors[type] || colors.info};"></i>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toast-out 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { showToast };
}
