// 企业级Bitcoin挖矿计算器JavaScript
class BitcoinMiningCalculator {
    constructor() {
        this.currentPrice = 0;
        this.networkHashrate = 0;
        this.difficulty = 0;
        this.blockReward = 3.125;
        this.initializeEventListeners();
        this.loadInitialData();
    }

    initializeEventListeners() {
        // 表单提交事件
        const form = document.querySelector('#mining-calculator-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleCalculation(e));
        }

        // 矿机选择事件
        const minerSelect = document.querySelector('#miner_model');
        if (minerSelect) {
            minerSelect.addEventListener('change', (e) => this.updateMinerSpecs(e));
        }

        // 实时数据切换
        const realTimeToggle = document.querySelector('#use_real_time_data');
        if (realTimeToggle) {
            realTimeToggle.addEventListener('change', (e) => this.toggleRealTimeData(e));
        }
    }

    async loadInitialData() {
        try {
            // 加载网络统计数据
            await this.loadNetworkStats();
            
            // 加载矿机列表
            await this.loadMinerList();
            
            // 更新页面显示
            this.updateDisplay();
        } catch (error) {
            console.error('初始数据加载失败:', error);
        }
    }

    async loadNetworkStats() {
        try {
            const response = await fetch('/api/network-stats');
            const data = await response.json();
            
            if (data.success) {
                this.currentPrice = data.btc_price;
                this.networkHashrate = data.network_hashrate;
                this.difficulty = data.difficulty;
                this.blockReward = data.block_reward || 3.125;
            }
        } catch (error) {
            console.error('网络统计加载失败:', error);
        }
    }

    async loadMinerList() {
        try {
            const response = await fetch('/api/miners');
            const data = await response.json();
            
            if (data.success && data.miners) {
                this.populateMinerSelect(data.miners);
            }
        } catch (error) {
            console.error('矿机列表加载失败:', error);
        }
    }

    populateMinerSelect(miners) {
        const select = document.querySelector('#miner_model');
        if (!select) return;

        // 清空现有选项
        select.innerHTML = '<option value="">选择矿机型号</option>';

        // 添加矿机选项
        miners.forEach(miner => {
            const option = document.createElement('option');
            option.value = miner.name;
            option.textContent = `${miner.name} (${miner.hashrate}TH/s, ${miner.power_consumption}W)`;
            option.dataset.hashrate = miner.hashrate;
            option.dataset.power = miner.power_consumption;
            select.appendChild(option);
        });
    }

    updateMinerSpecs(event) {
        const selectedOption = event.target.selectedOptions[0];
        if (!selectedOption) return;

        const hashrate = selectedOption.dataset.hashrate;
        const power = selectedOption.dataset.power;

        // 更新单机规格显示
        const hashrateInput = document.querySelector('#hashrate');
        const powerInput = document.querySelector('#power_consumption');

        if (hashrateInput && hashrate) {
            hashrateInput.value = hashrate;
        }
        if (powerInput && power) {
            powerInput.value = power;
        }
    }

    async handleCalculation(event) {
        event.preventDefault();
        
        const submitButton = event.target.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        
        try {
            // 显示加载状态
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="loading"></span> 计算中...';

            // 收集表单数据
            const formData = new FormData(event.target);
            
            // 发送计算请求
            const response = await fetch('/calculate', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (result.success) {
                this.displayResults(result);
            } else {
                this.showError(result.error || '计算失败');
            }
        } catch (error) {
            console.error('计算请求失败:', error);
            this.showError('计算请求失败，请重试');
        } finally {
            // 恢复按钮状态
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    displayResults(result) {
        const resultsContainer = document.querySelector('#calculation-results');
        if (!resultsContainer) return;

        const html = `
            <div class="card">
                <h3>计算结果</h3>
                <div class="row">
                    <div class="col-md-6">
                        <h4>收益分析</h4>
                        <p><strong>日产BTC:</strong> ${result.daily_btc_output?.toFixed(6) || 'N/A'}</p>
                        <p><strong>日收益:</strong> $${result.daily_profit?.toFixed(2) || 'N/A'}</p>
                        <p><strong>月收益:</strong> $${result.monthly_profit?.toFixed(2) || 'N/A'}</p>
                        <p><strong>年收益:</strong> $${result.yearly_profit?.toFixed(2) || 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <h4>成本分析</h4>
                        <p><strong>日电费:</strong> $${result.daily_electricity_cost?.toFixed(2) || 'N/A'}</p>
                        <p><strong>月电费:</strong> $${result.monthly_electricity_cost?.toFixed(2) || 'N/A'}</p>
                        <p><strong>年电费:</strong> $${result.yearly_electricity_cost?.toFixed(2) || 'N/A'}</p>
                    </div>
                </div>
                ${result.roi_analysis ? this.generateROIAnalysis(result.roi_analysis) : ''}
            </div>
        `;

        resultsContainer.innerHTML = html;
        resultsContainer.style.display = 'block';
    }

    generateROIAnalysis(roi) {
        return `
            <div class="mt-4">
                <h4>投资回报分析</h4>
                <div class="row">
                    <div class="col-md-4">
                        <p><strong>年化ROI:</strong> ${roi.annual_roi?.toFixed(2) || 'N/A'}%</p>
                    </div>
                    <div class="col-md-4">
                        <p><strong>回本周期:</strong> ${roi.payback_months?.toFixed(1) || 'N/A'} 个月</p>
                    </div>
                    <div class="col-md-4">
                        <p><strong>盈亏平衡电价:</strong> $${roi.breakeven_electricity?.toFixed(4) || 'N/A'}/kWh</p>
                    </div>
                </div>
            </div>
        `;
    }

    showError(message) {
        const errorContainer = document.querySelector('#error-messages');
        if (!errorContainer) return;

        // Create elements safely to prevent XSS
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger';
        alertDiv.setAttribute('role', 'alert');
        alertDiv.textContent = message; // Use textContent instead of innerHTML
        
        errorContainer.innerHTML = ''; // Clear previous errors
        errorContainer.appendChild(alertDiv);
        errorContainer.style.display = 'block';
    }

    updateDisplay() {
        // 更新页面上的实时数据显示
        const priceElement = document.querySelector('#current-btc-price');
        const hashrateElement = document.querySelector('#network-hashrate');
        const difficultyElement = document.querySelector('#network-difficulty');

        if (priceElement) {
            priceElement.textContent = `$${this.currentPrice.toLocaleString()}`;
        }
        if (hashrateElement) {
            hashrateElement.textContent = `${this.networkHashrate.toFixed(2)} EH/s`;
        }
        if (difficultyElement) {
            difficultyElement.textContent = `${(this.difficulty / 1e12).toFixed(2)}T`;
        }
    }

    toggleRealTimeData(event) {
        const isRealTime = event.target.checked;
        const manualInputs = document.querySelectorAll('.manual-input');
        
        manualInputs.forEach(input => {
            input.disabled = isRealTime;
            if (isRealTime) {
                input.classList.add('disabled');
            } else {
                input.classList.remove('disabled');
            }
        });
    }
}

// 初始化计算器
document.addEventListener('DOMContentLoaded', () => {
    new BitcoinMiningCalculator();
});

// 通用工具函数
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatNumber(number, decimals = 2) {
    return Number(number).toFixed(decimals);
}

function showLoading(element) {
    element.innerHTML = '<span class="loading"></span>';
}

function hideLoading(element, originalText) {
    element.innerHTML = originalText;
}