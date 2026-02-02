/**
 * ETF Arbitrage Terminal - Backtest Wizard
 *
 * 4-step wizard for backtesting ETF arbitrage strategies
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const WizardState = {
    currentStep: 1,
    totalSteps: 4,
    data: {
        // Step 1: Date Range
        startDate: null,
        endDate: null,

        // Step 2: Strategy Configuration
        template: 'balanced',
        minWeight: 0.05,
        minVolume: 5000,
        evaluatorType: 'default',
        interpolation: 'linear',

        // Step 4: Results
        backtestId: null,
        results: null
    },
    datePickers: {
        start: null,
        end: null
    }
};

// ============================================================================
// API CLIENT
// ============================================================================

const API = {
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl || ''}${endpoint}`;
        const defaults = {
            headers: {
                'Content-Type': 'application/json'
            }
        };

        try {
            const response = await fetch(url, { ...defaults, ...options });
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    },

    startBacktest(config) {
        return this.request('/api/backtest/start', {
            method: 'POST',
            body: JSON.stringify(config)
        });
    },

    getBacktestStatus(jobId) {
        return this.request(`/api/backtest/${jobId}`);
    },

    getBacktestResult(jobId) {
        return this.request(`/api/backtest/${jobId}/result`);
    },

    getBacktestSignals(jobId) {
        return this.request(`/api/backtest/${jobId}/signals`);
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================

function init() {
    initDatePickers();
    initEventListeners();
    initStrategyTemplates();
    setDatePreset(3); // Default to 3 months
}

function initDatePickers() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');

    if (!startDateInput || !endDateInput) return;

    const commonConfig = {
        locale: 'zh',
        dateFormat: 'Y-m-d',
        maxDate: 'today',
        disableMobile: true,
        theme: 'dark'
    };

    WizardState.datePickers.start = flatpickr(startDateInput, {
        ...commonConfig,
        onChange: (selectedDates, dateStr) => {
            WizardState.data.startDate = dateStr;
            updateTradingDaysHint();

            // Update end date picker minimum
            if (WizardState.datePickers.end && selectedDates.length > 0) {
                WizardState.datePickers.end.set('minDate', selectedDates[0]);
            }

            // Update preset buttons
            updatePresetButtons();
        }
    });

    WizardState.datePickers.end = flatpickr(endDateInput, {
        ...commonConfig,
        onChange: (selectedDates, dateStr) => {
            WizardState.data.endDate = dateStr;
            updateTradingDaysHint();
            updatePresetButtons();
        }
    });
}

function initEventListeners() {
    // Date preset buttons
    document.querySelectorAll('.date-preset').forEach(btn => {
        btn.addEventListener('click', () => {
            const months = parseInt(btn.dataset.months);
            setDatePreset(months);
        });
    });

    // Step navigation
    const step1Next = document.getElementById('step1Next');
    const step2Prev = document.getElementById('step2Prev');
    const step2Next = document.getElementById('step2Next');
    const step3Prev = document.getElementById('step3Prev');
    const startBacktest = document.getElementById('startBacktest');
    const exportSignals = document.getElementById('exportSignals');

    if (step1Next) step1Next.addEventListener('click', () => goToStep(2));
    if (step2Prev) step2Prev.addEventListener('click', () => goToStep(1));
    if (step2Next) step2Next.addEventListener('click', () => goToStep(3));
    if (step3Prev) step3Prev.addEventListener('click', () => goToStep(2));
    if (startBacktest) startBacktest.addEventListener('click', runBacktest);
    if (exportSignals) exportSignals.addEventListener('click', exportBacktestSignals);
}

function initStrategyTemplates() {
    document.querySelectorAll('.strategy-template').forEach(template => {
        template.addEventListener('click', () => {
            // Remove selection from all templates
            document.querySelectorAll('.strategy-template').forEach(t => {
                t.classList.remove('selected');
            });

            // Select clicked template
            template.classList.add('selected');
            selectTemplate(template.dataset.template);
        });
    });
}

// ============================================================================
// DATE PICKER FUNCTIONS
// ============================================================================

function setDatePreset(months) {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - months);

    if (WizardState.datePickers.start) {
        WizardState.datePickers.start.setDate(start);
        WizardState.data.startDate = WizardState.datePickers.start.formatDate(start);
    }

    if (WizardState.datePickers.end) {
        WizardState.datePickers.end.setDate(end);
        WizardState.data.endDate = WizardState.datePickers.end.formatDate(end);
    }

    updateTradingDaysHint();
    updatePresetButtons();
}

function updatePresetButtons() {
    const start = WizardState.data.startDate ? new Date(WizardState.data.startDate) : null;
    const end = WizardState.data.endDate ? new Date(WizardState.data.endDate) : null;

    if (!start || !end) return;

    const monthsDiff = (end.getFullYear() - start.getFullYear()) * 12 +
                       (end.getMonth() - start.getMonth());

    document.querySelectorAll('.date-preset').forEach(btn => {
        const btnMonths = parseInt(btn.dataset.months);
        btn.classList.toggle('active', btnMonths === monthsDiff);
    });
}

function updateTradingDaysHint() {
    const hint = document.getElementById('tradingDaysHint');
    if (!hint) return;

    const startDate = WizardState.data.startDate;
    const endDate = WizardState.data.endDate;

    if (!startDate || !endDate) {
        hint.innerHTML = '<i class="bi bi-info-circle"></i> 请选择日期范围';
        return;
    }

    const start = new Date(startDate);
    const end = new Date(endDate);

    if (start > end) {
        hint.innerHTML = '<i class="bi bi-exclamation-triangle" style="color: var(--status-error);"></i> 开始日期不能晚于结束日期';
        return;
    }

    // Estimate trading days (approximately 21 per month)
    const months = (end.getFullYear() - start.getFullYear()) * 12 +
                   (end.getMonth() - start.getMonth()) + 1;
    const estimatedDays = months * 21;

    hint.innerHTML = `<i class="bi bi-info-circle"></i> 预计需要处理约 ${estimatedDays} 个交易日`;
}

// ============================================================================
// STRATEGY TEMPLATES
// ============================================================================

function selectTemplate(templateId) {
    WizardState.data.template = templateId;

    const templates = {
        conservative: { minWeight: 0.08, minVolume: 8000, evaluatorType: 'conservative' },
        balanced: { minWeight: 0.05, minVolume: 5000, evaluatorType: 'default' },
        aggressive: { minWeight: 0.03, minVolume: 3000, evaluatorType: 'aggressive' }
    };

    const template = templates[templateId];
    if (template) {
        WizardState.data.minWeight = template.minWeight;
        WizardState.data.minVolume = template.minVolume;
        WizardState.data.evaluatorType = template.evaluatorType;

        // Update form fields
        const minWeightInput = document.getElementById('minWeight');
        const minVolumeInput = document.getElementById('minVolume');
        const evaluatorSelect = document.getElementById('evaluatorType');

        if (minWeightInput) minWeightInput.value = template.minWeight * 100;
        if (minVolumeInput) minVolumeInput.value = template.minVolume;
        if (evaluatorSelect) evaluatorSelect.value = template.evaluatorType;
    }
}

function toggleAdvancedOptions() {
    const container = document.getElementById('advancedOptions');
    const icon = document.getElementById('advancedOptionsIcon');

    container.classList.toggle('open');
    icon.classList.toggle('bi-chevron-down');
    icon.classList.toggle('bi-chevron-up');
}

// ============================================================================
// STEP NAVIGATION
// ============================================================================

function goToStep(step) {
    // Validate current step before moving
    if (step > WizardState.currentStep) {
        if (!validateCurrentStep()) {
            return;
        }
    }

    // Save current step data
    saveCurrentStepData();

    // Hide all panels
    document.querySelectorAll('.wizard-panel').forEach(panel => {
        panel.classList.remove('active');
    });

    // Show target panel
    const targetPanel = document.getElementById(`step-${step}`);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }

    // Update step indicators
    document.querySelectorAll('.wizard-step').forEach((stepEl, index) => {
        stepEl.classList.remove('active', 'completed');
        if (index + 1 < step) {
            stepEl.classList.add('completed');
        } else if (index + 1 === step) {
            stepEl.classList.add('active');
        }
    });

    WizardState.currentStep = step;

    // Load step-specific data
    if (step === 3) {
        loadPreviewData();
    }
}

function validateCurrentStep() {
    if (WizardState.currentStep === 1) {
        const startDate = WizardState.data.startDate;
        const endDate = WizardState.data.endDate;

        if (!startDate || !endDate) {
            showToast('请选择日期范围', 'warning');
            return false;
        }

        const start = new Date(startDate);
        const end = new Date(endDate);

        if (start > end) {
            showToast('开始日期不能晚于结束日期', 'warning');
            return false;
        }

        return true;
    }

    return true;
}

function saveCurrentStepData() {
    if (WizardState.currentStep === 2) {
        const minWeightInput = document.getElementById('minWeight');
        const minVolumeInput = document.getElementById('minVolume');
        const evaluatorSelect = document.getElementById('evaluatorType');
        const interpolationSelect = document.getElementById('interpolation');

        if (minWeightInput) {
            WizardState.data.minWeight = parseFloat(minWeightInput.value) / 100;
        }
        if (minVolumeInput) {
            WizardState.data.minVolume = parseInt(minVolumeInput.value);
        }
        if (evaluatorSelect) {
            WizardState.data.evaluatorType = evaluatorSelect.value;
        }
        if (interpolationSelect) {
            WizardState.data.interpolation = interpolationSelect.value;
        }
    }
}

// ============================================================================
// DATA PREVIEW
// ============================================================================

function loadPreviewData() {
    const container = document.getElementById('previewContent');
    if (!container) return;

    // Show loading state
    container.innerHTML = `
        <div class="progress-display">
            <div class="progress-spinner"></div>
            <div class="progress-text">正在分析数据覆盖度...</div>
        </div>
    `;

    // Simulate data analysis
    setTimeout(() => {
        const startDate = new Date(WizardState.data.startDate);
        const endDate = new Date(WizardState.data.endDate);
        const months = (endDate.getFullYear() - startDate.getFullYear()) * 12 +
                      (endDate.getMonth() - startDate.getMonth()) + 1;
        const estimatedDays = months * 21;

        container.innerHTML = `
            <div style="background: var(--terminal-panel-light); border: 1px solid var(--terminal-border); border-radius: 8px; padding: var(--space-lg);">
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-lg); margin-bottom: var(--space-lg);">
                    <div style="text-align: center;">
                        <div style="font-family: var(--font-mono); font-size: 32px; font-weight: 700; color: var(--electric-blue);">${estimatedDays}</div>
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--status-inactive); margin-top: var(--space-sm);">预计交易日</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-family: var(--font-mono); font-size: 32px; font-weight: 700; color: var(--status-active);">${months}</div>
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--status-inactive); margin-top: var(--space-sm);">月数</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-family: var(--font-mono); font-size: 32px; font-weight: 700; color: white;">${(WizardState.data.minWeight * 100).toFixed(0)}%</div>
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--status-inactive); margin-top: var(--space-sm);">最小权重</div>
                    </div>
                </div>

                <div style="padding-top: var(--space-lg); border-top: 1px solid var(--terminal-border);">
                    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--status-inactive); margin-bottom: var(--space-sm);">
                        <i class="bi bi-info-circle"></i> 回测配置
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); font-size: 13px;">
                        <div><span style="color: var(--status-inactive);">日期范围:</span> ${WizardState.data.startDate} 至 ${WizardState.data.endDate}</div>
                        <div><span style="color: var(--status-inactive);">策略模板:</span> ${getTemplateName(WizardState.data.template)}</div>
                        <div><span style="color: var(--status-inactive);">最小权重:</span> ${(WizardState.data.minWeight * 100).toFixed(0)}%</div>
                        <div><span style="color: var(--status-inactive);">最小成交额:</span> ${WizardState.data.minVolume}万</div>
                        <div><span style="color: var(--status-inactive);">评估器:</span> ${getEvaluatorName(WizardState.data.evaluatorType)}</div>
                        <div><span style="color: var(--status-inactive);">插值方式:</span> ${getInterpolationName(WizardState.data.interpolation)}</div>
                    </div>
                </div>
            </div>
        `;
    }, 1000);
}

function getTemplateName(template) {
    const names = {
        conservative: '保守型',
        balanced: '平衡型',
        aggressive: '激进型'
    };
    return names[template] || template;
}

function getEvaluatorName(evaluator) {
    const names = {
        default: '默认',
        conservative: '保守',
        aggressive: '激进'
    };
    return names[evaluator] || evaluator;
}

function getInterpolationName(interpolation) {
    const names = {
        linear: '线性插值',
        step: '阶梯插值'
    };
    return names[interpolation] || interpolation;
}

// ============================================================================
// BACKTEST EXECUTION
// ============================================================================

async function runBacktest() {
    // Save current step data
    saveCurrentStepData();

    const container = document.getElementById('resultsContent');
    if (!container) return;

    // Move to step 4
    goToStep(4);

    // Show progress
    container.innerHTML = `
        <div class="progress-display">
            <div class="progress-spinner"></div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" id="backtestProgressBar" style="width: 0%"></div>
            </div>
            <div class="progress-text" id="backtestStatusText">初始化中...</div>
        </div>
    `;

    // Build request config
    const config = {
        start_date: WizardState.data.startDate.replace(/-/g, ''),
        end_date: WizardState.data.endDate.replace(/-/g, ''),
        granularity: 'daily',
        min_weight: WizardState.data.minWeight,
        evaluator_type: WizardState.data.evaluatorType,
        interpolation: WizardState.data.interpolation
    };

    try {
        const result = await API.startBacktest(config);
        WizardState.data.backtestId = result.job_id || result.backtest_id;

        // Start polling for status
        pollBacktestStatus(WizardState.data.backtestId);
    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-exclamation-triangle"></i>
                <div class="empty-state-text">启动回测失败: ${error.message}</div>
            </div>
            <div style="text-align: center; margin-top: var(--space-lg);">
                <button class="wizard-btn wizard-btn-prev" onclick="goToStep(2)">
                    <i class="bi bi-arrow-left"></i> 返回修改配置
                </button>
            </div>
        `;
    }
}

function pollBacktestStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const status = await API.getBacktestStatus(jobId);

            const progressBar = document.getElementById('backtestProgressBar');
            const statusText = document.getElementById('backtestStatusText');

            if (progressBar && status.progress !== undefined) {
                progressBar.style.width = `${status.progress * 100}%`;
            }

            if (statusText && status.message) {
                statusText.textContent = status.message;
            }

            if (status.status === 'completed') {
                clearInterval(interval);
                WizardState.data.results = status;
                displayResults(status);
            } else if (status.status === 'failed') {
                clearInterval(interval);
                throw new Error(status.message || '回测失败');
            }
        } catch (error) {
            clearInterval(interval);
            const container = document.getElementById('resultsContent');
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-exclamation-triangle"></i>
                    <div class="empty-state-text">回测失败: ${error.message}</div>
                </div>
                <div style="text-align: center; margin-top: var(--space-lg);">
                    <button class="wizard-btn wizard-btn-prev" onclick="goToStep(2)">
                        <i class="bi bi-arrow-left"></i> 返回修改配置
                    </button>
                </div>
            `;
        }
    }, 2000);
}

function displayResults(result) {
    const container = document.getElementById('resultsContent');
    if (!container) return;

    const stats = result.result?.statistics || {};

    container.innerHTML = `
        <div class="results-summary">
            <div class="result-card">
                <div class="result-value">${stats.total_signals || 0}</div>
                <div class="result-label">总信号数</div>
            </div>
            <div class="result-card">
                <div class="result-value up">${stats.high_confidence_count || 0}</div>
                <div class="result-label">高置信度</div>
            </div>
            <div class="result-card">
                <div class="result-value" style="color: var(--status-warning);">${stats.medium_confidence_count || 0}</div>
                <div class="result-label">中置信度</div>
            </div>
            <div class="result-card">
                <div class="result-value" style="color: var(--status-inactive);">${stats.low_confidence_count || 0}</div>
                <div class="result-label">低置信度</div>
            </div>
        </div>

        <div style="background: var(--terminal-panel-light); border: 1px solid var(--terminal-border); border-radius: 8px; padding: var(--space-lg); text-align: center;">
            <i class="bi bi-check-circle" style="font-size: 32px; color: var(--status-active);"></i>
            <div style="margin-top: var(--space-md); font-family: var(--font-mono); font-size: 14px;">
                回测完成！共生成 ${stats.total_signals || 0} 个交易信号
            </div>
        </div>
    `;
}

async function exportBacktestSignals() {
    const jobId = WizardState.data.backtestId;
    if (!jobId) return;

    try {
        const response = await fetch(`/api/backtest/${jobId}/signals`);
        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `backtest_signals_${jobId}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);

        showToast('信号导出成功', 'success');
    } catch (error) {
        console.error('Export failed:', error);
        showToast('导出失败', 'error');
    }
}

function resetWizard() {
    WizardState.currentStep = 1;
    WizardState.data.backtestId = null;
    WizardState.data.results = null;
    goToStep(1);
}

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'wizard-toast';
    toast.style.cssText = `
        position: fixed;
        bottom: var(--space-lg);
        right: var(--space-lg);
        padding: var(--space-md) var(--space-lg);
        background: var(--terminal-panel);
        border: 1px solid var(--terminal-border);
        border-left-width: 4px;
        border-radius: 4px;
        font-family: var(--font-mono);
        font-size: 13px;
        z-index: 10000;
        animation: toast-in 0.3s ease-out;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    `;

    const colors = {
        success: 'var(--market-up)',
        error: 'var(--market-down)',
        warning: 'var(--status-warning)',
        info: 'var(--electric-blue)'
    };
    toast.style.borderLeftColor = colors[type] || colors.info;

    const icons = {
        success: 'bi-check-circle',
        error: 'bi-exclamation-triangle',
        warning: 'bi-exclamation-circle',
        info: 'bi-info-circle'
    };
    const icon = icons[type] || icons.info;

    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: var(--space-sm);">
            <i class="bi ${icon}" style="color: ${colors[type] || colors.info};"></i>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toast-out 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add toast animations
const style = document.createElement('style');
style.textContent = `
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
document.head.appendChild(style);

// ============================================================================
// START
// ============================================================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
