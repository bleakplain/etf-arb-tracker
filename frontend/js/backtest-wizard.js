/**
 * 回测向导控制器
 *
 * 管理4步向导流程，处理步骤切换和数据收集
 */

class BacktestWizard {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.data = {
            // 步骤1: 日期范围
            dateRange: {
                startDate: null,
                endDate: null
            },
            // 步骤2: 策略配置
            strategy: {
                template: 'balanced',
                minWeight: 0.05,
                minEtfVolume: 5000,
                evaluatorType: 'default',
                interpolation: 'linear'
            },
            // 步骤3: 数据预览
            preview: null,
            // 步骤4: 回测结果
            result: {
                backtestId: null
            }
        };

        this.init();
    }

    /**
     * 初始化向导
     */
    init() {
        this.bindEvents();
        this.loadStrategyTemplates();
        this.initDefaultDates();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 快捷日期按钮
        document.querySelectorAll('.date-preset').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const months = parseInt(e.target.dataset.months);
                this.setDatePreset(months);
            });
        });

        // 日期输入变化
        const startDateInput = document.getElementById('wizard-start-date');
        const endDateInput = document.getElementById('wizard-end-date');
        startDateInput?.addEventListener('change', () => this.updateTradingDaysHint());
        endDateInput?.addEventListener('change', () => this.updateTradingDaysHint());

        // 上一步/下一步按钮
        document.getElementById('wizard-prev-btn')?.addEventListener('click', () => this.prevStep());
        document.getElementById('wizard-next-btn')?.addEventListener('click', () => this.nextStep());
        document.getElementById('wizard-start-btn')?.addEventListener('click', () => this.startBacktest());
    }

    /**
     * 加载策略模板
     */
    async loadStrategyTemplates() {
        try {
            const response = await fetch('/api/backtest/templates');
            const data = await response.json();

            const container = document.getElementById('strategy-templates');
            if (!container) return;

            container.innerHTML = data.templates.map(template => `
                <div class="col-md-4">
                    <div class="strategy-template-card ${template.id === 'balanced' ? 'selected' : ''}"
                         data-template-id="${template.id}">
                        <div class="template-name">${template.name}</div>
                        <div class="template-desc">${template.description}</div>
                        <div class="template-params">
                            最小权重: ${(template.min_weight * 100).toFixed(0)}%<br>
                            最小成交额: ${template.min_etf_volume}万
                        </div>
                    </div>
                </div>
            `).join('');

            // 绑定模板选择事件
            container.querySelectorAll('.strategy-template-card').forEach(card => {
                card.addEventListener('click', () => {
                    container.querySelectorAll('.strategy-template-card').forEach(c =>
                        c.classList.remove('selected'));
                    card.classList.add('selected');
                    this.selectTemplate(card.dataset.templateId);
                });
            });

        } catch (error) {
            console.error('加载策略模板失败:', error);
        }
    }

    /**
     * 初始化默认日期（近3个月）
     */
    initDefaultDates() {
        this.setDatePreset(3);
    }

    /**
     * 设置快捷日期
     */
    setDatePreset(months) {
        const end = new Date();
        const start = new Date();
        start.setMonth(start.getMonth() - months);

        const startDateStr = start.toISOString().split('T')[0];
        const endDateStr = end.toISOString().split('T')[0];

        const startDateInput = document.getElementById('wizard-start-date');
        const endDateInput = document.getElementById('wizard-end-date');

        if (startDateInput) startDateInput.value = startDateStr;
        if (endDateInput) endDateInput.value = endDateStr;

        this.data.dateRange.startDate = startDateStr;
        this.data.dateRange.endDate = endDateStr;

        this.updateTradingDaysHint();
    }

    /**
     * 更新交易日提示
     */
    updateTradingDaysHint() {
        const startDate = document.getElementById('wizard-start-date')?.value;
        const endDate = document.getElementById('wizard-end-date')?.value;
        const hint = document.getElementById('trading-days-hint');

        if (!startDate || !endDate || !hint) return;

        // 简单估算：每月约21个交易日
        const start = new Date(startDate);
        const end = new Date(endDate);
        const months = (end.getFullYear() - start.getFullYear()) * 12 +
                       (end.getMonth() - start.getMonth()) + 1;
        const estimatedDays = months * 21;

        hint.innerHTML = `<i class="bi bi-info-circle"></i> 预计需要处理约 ${estimatedDays} 个交易日`;
    }

    /**
     * 选择策略模板
     */
    selectTemplate(templateId) {
        this.data.strategy.template = templateId;

        // 根据模板更新高级选项的值
        const template = {
            conservative: { minWeight: 0.08, minEtfVolume: 8000, evaluatorType: 'conservative' },
            balanced: { minWeight: 0.05, minEtfVolume: 5000, evaluatorType: 'default' },
            aggressive: { minWeight: 0.03, minEtfVolume: 3000, evaluatorType: 'aggressive' }
        }[templateId];

        if (template) {
            this.data.strategy = { ...this.data.strategy, ...template };

            // 更新表单
            const minWeightInput = document.getElementById('wizard-min-weight');
            const minVolumeInput = document.getElementById('wizard-min-volume');
            const evaluatorSelect = document.getElementById('wizard-evaluator');

            if (minWeightInput) minWeightInput.value = template.minWeight * 100;
            if (minVolumeInput) minVolumeInput.value = template.minEtfVolume;
            if (evaluatorSelect) evaluatorSelect.value = template.evaluatorType;
        }
    }

    /**
     * 验证当前步骤
     */
    validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                const startDate = document.getElementById('wizard-start-date')?.value;
                const endDate = document.getElementById('wizard-end-date')?.value;
                if (!startDate || !endDate) {
                    this.showToast('请选择日期范围', 'warning');
                    return false;
                }
                if (new Date(startDate) > new Date(endDate)) {
                    this.showToast('开始日期不能晚于结束日期', 'warning');
                    return false;
                }
                return true;

            case 2:
                return true; // 策略有默认值，总是有效

            case 3:
                return true; // 数据预览总是可以继续

            default:
                return true;
        }
    }

    /**
     * 下一步
     */
    async nextStep() {
        if (!this.validateCurrentStep()) return;

        // 保存当前步骤的数据
        this.saveCurrentStepData();

        if (this.currentStep < this.totalSteps) {
            this.goToStep(this.currentStep + 1);
        }
    }

    /**
     * 上一步
     */
    prevStep() {
        if (this.currentStep > 1) {
            this.goToStep(this.currentStep - 1);
        }
    }

    /**
     * 跳转到指定步骤
     */
    goToStep(step) {
        // 隐藏所有步骤面板
        document.querySelectorAll('.wizard-step-panel').forEach(panel => {
            panel.classList.remove('active');
        });

        // 显示目标步骤面板
        const targetPanel = document.getElementById(`wizard-step-${step}`);
        if (targetPanel) {
            targetPanel.classList.add('active');
        }

        // 更新进度指示器
        document.querySelectorAll('.wizard-step').forEach((stepEl, index) => {
            stepEl.classList.remove('active', 'completed');
            if (index + 1 < step) {
                stepEl.classList.add('completed');
            } else if (index + 1 === step) {
                stepEl.classList.add('active');
            }
        });

        // 更新按钮状态
        this.updateNavigationButtons(step);

        // 如果进入步骤3，加载数据预览
        if (step === 3) {
            this.loadPreviewData();
        }

        this.currentStep = step;
    }

    /**
     * 更新导航按钮状态
     */
    updateNavigationButtons(step) {
        const prevBtn = document.getElementById('wizard-prev-btn');
        const nextBtn = document.getElementById('wizard-next-btn');
        const startBtn = document.getElementById('wizard-start-btn');

        // 上一步按钮
        if (prevBtn) {
            prevBtn.disabled = step === 1;
        }

        // 下一步/开始回测按钮切换
        if (nextBtn && startBtn) {
            if (step === 3) {
                nextBtn.classList.add('d-none');
                startBtn.classList.remove('d-none');
            } else {
                nextBtn.classList.remove('d-none');
                startBtn.classList.add('d-none');
            }
        }
    }

    /**
     * 保存当前步骤数据
     */
    saveCurrentStepData() {
        switch (this.currentStep) {
            case 1:
                this.data.dateRange.startDate = document.getElementById('wizard-start-date')?.value;
                this.data.dateRange.endDate = document.getElementById('wizard-end-date')?.value;
                break;

            case 2:
                this.data.strategy.minWeight = parseFloat(document.getElementById('wizard-min-weight')?.value) / 100;
                this.data.strategy.minEtfVolume = parseInt(document.getElementById('wizard-min-volume')?.value);
                this.data.strategy.evaluatorType = document.getElementById('wizard-evaluator')?.value;
                this.data.strategy.interpolation = document.getElementById('wizard-interpolation')?.value;
                break;
        }
    }

    /**
     * 加载数据预览
     */
    async loadPreviewData() {
        const container = document.getElementById('data-preview-content');
        if (!container) return;

        // 显示加载中
        container.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3">正在分析数据覆盖度...</p>
            </div>
        `;

        try {
            // TODO: 实现数据预览API调用
            // 暂时显示示例数据
            setTimeout(() => {
                container.innerHTML = `
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i>
                        数据预览功能将在后续实现中完成
                    </div>
                    <p>日期范围: ${this.data.dateRange.startDate} 至 ${this.data.dateRange.endDate}</p>
                    <p>策略模板: ${this.data.strategy.template}</p>
                `;
            }, 1000);

        } catch (error) {
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    加载数据预览失败: ${error.message}
                </div>
            `;
        }
    }

    /**
     * 开始回测
     */
    async startBacktest() {
        const container = document.getElementById('backtest-results-content');
        if (!container) return;

        // 切换到步骤4
        this.goToStep(4);

        // 显示进度
        container.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3">正在运行回测...</p>
                <div class="progress" style="max-width: 400px; margin: 20px auto;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated"
                         id="wizard-backtest-progress" style="width: 0%"></div>
                </div>
                <p class="text-secondary" id="wizard-backtest-status">初始化中...</p>
            </div>
        `;

        try {
            const response = await fetch('/api/backtest/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    start_date: this.data.dateRange.startDate.replace(/-/g, ''),
                    end_date: this.data.dateRange.endDate.replace(/-/g, ''),
                    granularity: 'daily',
                    min_weight: this.data.strategy.minWeight,
                    evaluator_type: this.data.strategy.evaluatorType,
                    interpolation: this.data.strategy.interpolation
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.data.result.backtestId = result.backtest_id;
                this.pollBacktestProgress(result.backtest_id);
            } else {
                throw new Error(result.detail || '启动回测失败');
            }

        } catch (error) {
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    启动回测失败: ${error.message}
                </div>
            `;
        }
    }

    /**
     * 轮询回测进度
     */
    pollBacktestProgress(backtestId) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/backtest/${backtestId}`);
                const result = await response.json();

                const progressBar = document.getElementById('wizard-backtest-progress');
                const statusText = document.getElementById('wizard-backtest-status');

                if (progressBar) {
                    progressBar.style.width = `${result.progress * 100}%`;
                }

                if (statusText && result.message) {
                    statusText.textContent = result.message;
                }

                if (result.status === 'completed') {
                    clearInterval(interval);
                    this.displayResults(result);
                } else if (result.status === 'failed') {
                    clearInterval(interval);
                    throw new Error(result.message || '回测失败');
                }

            } catch (error) {
                clearInterval(interval);
                document.getElementById('backtest-results-content').innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle"></i>
                        回测失败: ${error.message}
                    </div>
                `;
            }
        }, 2000);
    }

    /**
     * 显示回测结果
     */
    displayResults(result) {
        const container = document.getElementById('backtest-results-content');
        if (!container) return;

        const stats = result.result?.statistics || {};
        const signals = result.result?.signals || [];

        container.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="card-title text-primary">${stats.total_signals || 0}</h3>
                            <p class="card-text text-secondary">总信号数</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="card-title text-success">${stats.high_confidence_count || 0}</h3>
                            <p class="card-text text-secondary">高置信度</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="card-title text-warning">${stats.medium_confidence_count || 0}</h3>
                            <p class="card-text text-secondary">中置信度</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="card-title text-danger">${stats.low_confidence_count || 0}</h3>
                            <p class="card-text text-secondary">低置信度</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="alert alert-success">
                <i class="bi bi-check-circle"></i>
                回测完成！共生成 ${signals.length} 个交易信号
            </div>

            <div class="d-flex gap-2">
                <button class="btn btn-outline-primary" onclick="window.BacktestWizard?.instance?.exportSignals()">
                    <i class="bi bi-download"></i> 导出信号
                </button>
                <button class="btn btn-outline-secondary" onclick="window.BacktestWizard?.instance?.reset()">
                    <i class="bi bi-arrow-clockwise"></i> 重新开始
                </button>
            </div>
        `;
    }

    /**
     * 显示提示消息
     */
    showToast(message, type = 'info') {
        // 复用现有的toast函数
        if (typeof showToastMessage === 'function') {
            showToastMessage(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }

    /**
     * 重置向导
     */
    reset() {
        this.currentStep = 1;
        this.goToStep(1);
    }

    /**
     * 导出信号
     */
    async exportSignals() {
        if (!this.data.result.backtestId) return;

        try {
            const response = await fetch(`/api/backtest/${this.data.result.backtestId}/signals`);
            const blob = await response.blob();

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `backtest_signals_${this.data.result.backtestId}.csv`;
            a.click();
            window.URL.revokeObjectURL(url);

            this.showToast('信号导出成功', 'success');
        } catch (error) {
            this.showToast('导出失败: ' + error.message, 'danger');
        }
    }
}

// 全局实例
window.BacktestWizard = {
    instance: null,

    init() {
        if (document.getElementById('backtest')) {
            this.instance = new BacktestWizard();
        }
    }
};

// 页面加载后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.BacktestWizard.init();
});
