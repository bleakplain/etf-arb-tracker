/**
 * ETF Arbitrage Terminal - DOM Utilities
 *
 * Reusable DOM manipulation utilities
 */

const DOMUtils = {
    /**
     * Show element by ID
     */
    show(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = '';
    },

    /**
     * Hide element by ID
     */
    hide(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    },

    /**
     * Toggle element visibility
     */
    toggle(id, visible) {
        if (visible) {
            this.show(id);
        } else {
            this.hide(id);
        }
    },

    /**
     * Set element text content
     */
    setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    },

    /**
     * Set element HTML content
     */
    setHTML(id, html) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
    },

    /**
     * Add class to element
     */
    addClass(id, className) {
        const el = document.getElementById(id);
        if (el) el.classList.add(className);
    },

    /**
     * Remove class from element
     */
    removeClass(id, className) {
        const el = document.getElementById(id);
        if (el) el.classList.remove(className);
    },

    /**
     * Toggle class on element
     */
    toggleClass(id, className, force) {
        const el = document.getElementById(id);
        if (el) el.classList.toggle(className, force);
    },

    /**
     * Check if element has class
     */
    hasClass(id, className) {
        const el = document.getElementById(id);
        return el ? el.classList.contains(className) : false;
    },

    /**
     * Disable button
     */
    disableButton(id) {
        const el = document.getElementById(id);
        if (el) {
            el.disabled = true;
            el.dataset.originalText = el.innerHTML;
        }
    },

    /**
     * Enable button
     */
    enableButton(id) {
        const el = document.getElementById(id);
        if (el) {
            el.disabled = false;
            if (el.dataset.originalText) {
                el.innerHTML = el.dataset.originalText;
            }
        }
    },

    /**
     * Set button loading state
     */
    setButtonLoading(id, loading, text = '处理中...') {
        const el = document.getElementById(id);
        if (el) {
            if (loading) {
                el.disabled = true;
                el.dataset.originalText = el.innerHTML;
                el.innerHTML = `<div class="terminal-loading-spinner" style="width: 16px; height: 16px;"></div> ${text}`;
            } else {
                el.disabled = false;
                if (el.dataset.originalText) {
                    el.innerHTML = el.dataset.originalText;
                }
            }
        }
    },

    /**
     * Clear element content
     */
    clear(id) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '';
    },

    /**
     * Create element with attributes
     */
    create(tag, attributes = {}, content = '') {
        const el = document.createElement(tag);

        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                el.className = value;
            } else if (key === 'style' && typeof value === 'object') {
                Object.assign(el.style, value);
            } else if (key.startsWith('data-')) {
                el.setAttribute(key, value);
            } else {
                el[key] = value;
            }
        });

        if (content) {
            el.innerHTML = content;
        }

        return el;
    },

    /**
     * Query selector shortcut
     */
    query(selector, parent = document) {
        return parent.querySelector(selector);
    },

    /**
     * Query all shortcut
     */
    queryAll(selector, parent = document) {
        return parent.querySelectorAll(selector);
    },

    /**
     * Add event listener
     */
    on(id, event, handler) {
        const el = typeof id === 'string' ? document.getElementById(id) : id;
        if (el) el.addEventListener(event, handler);
    },

    /**
     * Remove event listener
     */
    off(id, event, handler) {
        const el = typeof id === 'string' ? document.getElementById(id) : id;
        if (el) el.removeEventListener(event, handler);
    },

    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};
