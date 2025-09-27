/**
 * 计算器模块专用JavaScript
 * 独立的JS文件，不依赖其他模块
 */

// 计算器模块命名空间
const CalculatorModule = {
    // 配置
    config: {
        apiBase: '/calculator/api',
        updateInterval: 30000, // 30秒更新一次网络数据
        chartColors: {
            profit: '#4CAF50',
            cost: '#F44336',
            revenue: '#2196F3'
        }
    },

    // 初始化
    init() {
        console.log('[Calculator Module] 初始化中...');
        this.bindEvents();
        this.loadMiners();
        this.loadNetworkStats();
        this.startAutoUpdate();
    },

    // 绑定事件
    bindEvents() {
        // 计算按钮
        const calcBtn = document.getElementById('calc-btn');
        if (calcBtn) {
            calcBtn.addEventListener('click', () => this.calculate());
        }

        // 矿机选择变化
        const minerSelect = document.getElementById('miner-select');
        if (minerSelect) {
            minerSelect.addEventListener('change', (e) => this.onMinerChange(e));
        }

        // 保存预设
        const saveBtn = document.getElementById('save-preset-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.savePreset());
        }
    },

    // 加载矿机列表
    async loadMiners() {
        try {
            const response = await fetch(`${this.config.apiBase}/miners`);
            const data = await response.json();
            
            if (data.success && data.miners) {
                this.updateMinerSelect(data.miners);
                console.log('[Calculator Module] 矿机列表加载成功:', data.miners.length);
            }
        } catch (error) {
            console.error('[Calculator Module] 加载矿机失败:', error);
            this.showError('无法加载矿机列表');
        }
    },

    // 更新矿机下拉框
    updateMinerSelect(miners) {
        const select = document.getElementById('miner-select');
        if (!select) return;

        select.innerHTML = '<option value="">选择矿机型号</option>';
        
        miners.forEach(miner => {
            const option = document.createElement('option');
            option.value = miner.name;
            option.textContent = `${miner.name} (${miner.hashrate} TH/s, ${miner.power_consumption}W)`;
            option.dataset.hashrate = miner.hashrate;
            option.dataset.power = miner.power_consumption;
            option.dataset.price = miner.price || 0;
            select.appendChild(option);
        });
    },

    // 加载网络统计
    async loadNetworkStats() {
        try {
            const response = await fetch(`${this.config.apiBase}/network-stats`);
            const data = await response.json();
            
            if (data.success) {
                this.updateNetworkDisplay(data);
                console.log('[Calculator Module] 网络数据已更新');
            }
        } catch (error) {
            console.error('[Calculator Module] 加载网络数据失败:', error);
        }
    },

    // 更新网络数据显示
    updateNetworkDisplay(data) {
        const elements = {
            'btc-price': `$${this.formatNumber(data.btc_price)}`,
            'network-hashrate': `${this.formatHashrate(data.network_hashrate)}`,
            'network-difficulty': this.formatDifficulty(data.network_difficulty),
            'block-reward': `${data.block_reward} BTC`
        };

        Object.entries(elements).forEach(([id, value]) => {
            const elem = document.getElementById(id);
            if (elem) {
                elem.textContent = value;
            }
        });
    },

    // 矿机选择变化处理
    onMinerChange(event) {
        const select = event.target;
        const option = select.options[select.selectedIndex];
        
        if (option && option.value) {
            // 自动填充参数
            document.getElementById('hashrate-input').value = option.dataset.hashrate || '';
            document.getElementById('power-input').value = option.dataset.power || '';
            document.getElementById('price-input').value = option.dataset.price || '';
        }
    },

    // 执行计算
    async calculate() {
        const params = this.getFormData();
        
        if (!this.validateForm(params)) {
            return;
        }

        this.showLoading(true);

        try {
            const response = await fetch(`${this.config.apiBase}/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayResults(data.result);
                this.updateChart(data.result);
                console.log('[Calculator Module] 计算完成');
            } else {
                this.showError(data.error || '计算失败');
            }
        } catch (error) {
            console.error('[Calculator Module] 计算错误:', error);
            this.showError('计算请求失败');
        } finally {
            this.showLoading(false);
        }
    },

    // 获取表单数据
    getFormData() {
        return {
            miner_model: document.getElementById('miner-select')?.value,
            hashrate: parseFloat(document.getElementById('hashrate-input')?.value) || 0,
            power_consumption: parseFloat(document.getElementById('power-input')?.value) || 0,
            electricity_cost: parseFloat(document.getElementById('electricity-input')?.value) || 0.06,
            miner_count: parseInt(document.getElementById('count-input')?.value) || 1,
            miner_price: parseFloat(document.getElementById('price-input')?.value) || 0
        };
    },

    // 验证表单
    validateForm(data) {
        if (!data.miner_model) {
            this.showError('请选择矿机型号');
            return false;
        }

        if (data.hashrate <= 0) {
            this.showError('请输入有效的算力');
            return false;
        }

        if (data.power_consumption <= 0) {
            this.showError('请输入有效的功耗');
            return false;
        }

        return true;
    },

    // 显示结果
    displayResults(result) {
        const resultsDiv = document.getElementById('results-container');
        if (!resultsDiv) return;

        resultsDiv.innerHTML = `
            <div class="result-card">
                <div class="result-label">日产BTC</div>
                <div class="result-value">${result.daily_btc.toFixed(8)} BTC</div>
            </div>
            <div class="result-card">
                <div class="result-label">日收益</div>
                <div class="result-value">$${result.daily_revenue.toFixed(2)}</div>
            </div>
            <div class="result-card">
                <div class="result-label">日成本</div>
                <div class="result-value">$${result.daily_cost.toFixed(2)}</div>
            </div>
            <div class="result-card">
                <div class="result-label">日利润</div>
                <div class="result-value" style="color: ${result.daily_profit > 0 ? '#4CAF50' : '#F44336'}">
                    $${result.daily_profit.toFixed(2)}
                </div>
            </div>
            <div class="result-card">
                <div class="result-label">回本天数</div>
                <div class="result-value">${result.roi_days || '∞'} 天</div>
            </div>
        `;

        resultsDiv.style.display = 'block';
    },

    // 保存预设
    async savePreset() {
        const presetName = prompt('请输入预设名称:');
        if (!presetName) return;

        const params = this.getFormData();
        params.preset_name = presetName;

        try {
            const response = await fetch(`${this.config.apiBase}/save-preset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('预设保存成功');
                this.loadPresets();
            } else {
                this.showError(data.error || '保存失败');
            }
        } catch (error) {
            console.error('[Calculator Module] 保存预设失败:', error);
            this.showError('保存预设失败');
        }
    },

    // 自动更新
    startAutoUpdate() {
        setInterval(() => {
            this.loadNetworkStats();
        }, this.config.updateInterval);
    },

    // 工具函数
    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num);
    },

    formatHashrate(hashrate) {
        return `${(hashrate / 1000000).toFixed(2)} EH/s`;
    },

    formatDifficulty(difficulty) {
        return (difficulty / 1e12).toFixed(2) + 'T';
    },

    showLoading(show) {
        const btn = document.getElementById('calc-btn');
        if (btn) {
            btn.disabled = show;
            btn.textContent = show ? '计算中...' : '开始计算';
        }
    },

    showError(message) {
        alert(`错误: ${message}`);
    },

    showSuccess(message) {
        alert(`成功: ${message}`);
    },

    updateChart(result) {
        // 图表更新逻辑
        console.log('[Calculator Module] 更新图表', result);
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    CalculatorModule.init();
});