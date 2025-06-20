// Bitcoin Mining Calculator - Main JavaScript (Final Fixed Version)
document.addEventListener('DOMContentLoaded', function() {
    console.log("页面已加载，初始化应用...");
    
    // 使用更长的延迟确保DOM完全加载
    setTimeout(function() {
        initializeApplication();
    }, 1000);
    
    function initializeApplication() {
        console.log("开始初始化应用程序...");
        
        // 获取所有DOM元素并验证
        const elements = getDOMElements();
        
        // 全局变量
        let isUpdatingMinerCount = false;
        let isUpdatingSitePower = false;
        
        // 安全的DOM操作函数
        function safeQuery(selector) {
            try {
                return document.querySelector(selector);
            } catch (e) {
                console.warn('Query failed for:', selector);
                return null;
            }
        }
        
        function safeGetById(id) {
            try {
                return document.getElementById(id);
            } catch (e) {
                console.warn('getElementById failed for:', id);
                return null;
            }
        }
        
        function safeSetStyle(elementOrId, property, value) {
            try {
                const element = typeof elementOrId === 'string' ? safeGetById(elementOrId) : elementOrId;
                if (element && element.style) {
                    element.style[property] = value;
                    return true;
                }
            } catch (e) {
                console.warn('Style setting failed:', e);
            }
            return false;
        }
        
        function safeSetValue(elementOrId, value) {
            try {
                const element = typeof elementOrId === 'string' ? safeGetById(elementOrId) : elementOrId;
                if (element && typeof element.value !== 'undefined') {
                    element.value = value;
                    return true;
                }
            } catch (e) {
                console.warn('Value setting failed:', e);
            }
            return false;
        }
        
        function safeAddEventListener(elementOrId, event, handler) {
            try {
                const element = typeof elementOrId === 'string' ? safeGetById(elementOrId) : elementOrId;
                if (element && typeof element.addEventListener === 'function') {
                    element.addEventListener(event, handler);
                    return true;
                }
            } catch (e) {
                console.warn('Event listener failed:', e);
            }
            return false;
        }
        
        function getDOMElements() {
            const ids = [
                'btc-price', 'network-difficulty', 'network-hashrate', 'block-reward',
                'miner-model', 'site-power-mw', 'miner-count', 'hashrate', 'hashrate-unit',
                'power-consumption', 'electricity-cost', 'client-electricity-cost',
                'btc-price-input', 'use-real-time', 'mining-calculator-form',
                'total-hashrate', 'total-power', 'total-hashrate-display', 'total-power-display',
                'results-card', 'chart-card'
            ];
            
            const elements = {};
            ids.forEach(id => {
                elements[id.replace(/-/g, '_')] = safeGetById(id);
                if (!elements[id.replace(/-/g, '_')]) {
                    console.warn(`Element not found: ${id}`);
                }
            });
            
            return elements;
        }
        
        // 初始化函数
        function init() {
            console.log("初始化应用功能...");
            
            // 加载网络数据
            fetchNetworkStats();
            
            // 启动自动刷新
            setInterval(fetchNetworkStats, 30000);
            
            // 加载矿机列表
            fetchMiners();
            
            // 延迟初始化计算
            setTimeout(calculateTotalHashrateAndPower, 2000);
            
            // 绑定事件
            bindEventListeners();
        }
        
        function bindEventListeners() {
            // 表单提交
            safeAddEventListener('mining-calculator-form', 'submit', handleCalculateSubmit);
            
            // 矿机型号选择
            safeAddEventListener('miner-model', 'change', updateMinerSpecs);
            
            // 输入框事件
            safeAddEventListener('site-power-mw', 'input', updateMinerCount);
            safeAddEventListener('miner-count', 'input', function() {
                updateSitePower();
                calculateTotalHashrateAndPower();
            });
            safeAddEventListener('hashrate', 'input', calculateTotalHashrateAndPower);
            safeAddEventListener('power-consumption', 'input', calculateTotalHashrateAndPower);
            safeAddEventListener('use-real-time', 'change', handleRealTimeToggle);
            
            // 图表按钮
            safeAddEventListener('generate-chart-btn', 'click', function() {
                const minerModel = elements.miner_model ? elements.miner_model.value : '';
                const minerCount = elements.miner_count ? elements.miner_count.value || 1 : 1;
                const clientElectricityCost = elements.client_electricity_cost ? elements.client_electricity_cost.value || 0 : 0;
                
                if (!minerModel) {
                    showError('请先选择矿机型号');
                    return;
                }
                
                generateProfitChart(minerModel, minerCount, clientElectricityCost);
            });
        }
        
        function handleRealTimeToggle() {
            if (elements.use_real_time && elements.use_real_time.checked) {
                if (elements.btc_price_input) elements.btc_price_input.disabled = true;
                fetchNetworkStats();
            } else {
                if (elements.btc_price_input) elements.btc_price_input.disabled = false;
            }
        }
        
        function updateMinerSpecs() {
            if (!elements.miner_model) return;
            
            const selectedMiner = elements.miner_model.value;
            
            if (selectedMiner) {
                const miners = JSON.parse(localStorage.getItem('miners') || '[]');
                const miner = miners.find(m => m.name === selectedMiner);
                
                if (miner) {
                    safeSetValue(elements.hashrate, miner.hashrate);
                    safeSetValue(elements.power_consumption, miner.power_watt);
                    
                    // 禁用手动输入
                    if (elements.hashrate) elements.hashrate.disabled = true;
                    if (elements.hashrate_unit) elements.hashrate_unit.disabled = true;
                    if (elements.power_consumption) elements.power_consumption.disabled = true;
                    
                    updateMinerCount();
                    calculateTotalHashrateAndPower();
                }
            } else {
                // 启用手动输入
                if (elements.hashrate) elements.hashrate.disabled = false;
                if (elements.hashrate_unit) elements.hashrate_unit.disabled = false;
                if (elements.power_consumption) elements.power_consumption.disabled = false;
            }
        }
        
        function updateMinerCount() {
            if (isUpdatingSitePower || !elements.site_power_mw || !elements.power_consumption || !elements.miner_count) {
                return;
            }
            
            isUpdatingMinerCount = true;
            
            const sitePowerMw = parseFloat(elements.site_power_mw.value) || 0;
            const powerWatt = parseFloat(elements.power_consumption.value) || 0;
            
            if (sitePowerMw > 0 && powerWatt > 0) {
                const maxMiners = Math.floor((sitePowerMw * 1000000) / powerWatt);
                safeSetValue(elements.miner_count, maxMiners);
                calculateTotalHashrateAndPower();
            }
            
            isUpdatingMinerCount = false;
        }
        
        function updateSitePower() {
            if (isUpdatingMinerCount || !elements.miner_count || !elements.power_consumption || !elements.site_power_mw) {
                return;
            }
            
            isUpdatingSitePower = true;
            
            const minerCount = parseInt(elements.miner_count.value) || 0;
            const powerWatt = parseFloat(elements.power_consumption.value) || 0;
            
            if (minerCount > 0 && powerWatt > 0) {
                const requiredPowerMw = (minerCount * powerWatt) / 1000000;
                safeSetValue(elements.site_power_mw, requiredPowerMw.toFixed(2));
            }
            
            isUpdatingSitePower = false;
        }
        
        function calculateTotalHashrateAndPower() {
            if (!elements.miner_count || !elements.hashrate || !elements.power_consumption) {
                return;
            }
            
            const minerCount = parseInt(elements.miner_count.value) || 0;
            const hashrate = parseFloat(elements.hashrate.value) || 0;
            const powerWatt = parseFloat(elements.power_consumption.value) || 0;
            
            if (minerCount > 0 && hashrate > 0 && powerWatt > 0) {
                const totalHashrate = minerCount * hashrate;
                const totalPower = minerCount * powerWatt;
                
                safeSetValue(elements.total_hashrate, totalHashrate.toFixed(0));
                safeSetValue(elements.total_power, totalPower.toFixed(0));
                safeSetValue(elements.total_hashrate_display, totalHashrate.toFixed(0));
                safeSetValue(elements.total_power_display, totalPower.toFixed(0));
                
                return { totalHashrate, totalPower };
            }
            
            return null;
        }
        
        function handleCalculateSubmit(event) {
            event.preventDefault();
            
            if (!elements.mining_calculator_form) return;
            
            const formData = new FormData(elements.mining_calculator_form);
            
            fetch('/calculate', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                displayResults(data);
            })
            .catch(error => {
                console.error('计算请求失败:', error);
                showError('计算请求失败，请稍后重试。');
            });
        }
        
        function displayResults(data) {
            if (!data.success) {
                showError(data.error || '计算失败');
                return;
            }
            
            // 安全显示结果卡片
            safeSetStyle('results-card', 'display', 'block');
            
            // 更新结果显示
            updateResultDisplay(data);
        }
        
        function updateResultDisplay(data) {
            // 基本BTC挖矿产出
            if (data.btc_mined) {
                updateElementText('daily-btc', (data.btc_mined.daily || 0).toFixed(6) + ' BTC');
                updateElementText('monthly-btc', (data.btc_mined.monthly || 0).toFixed(4) + ' BTC');
                updateElementText('yearly-btc', (data.btc_mined.yearly || 0).toFixed(2) + ' BTC');
            }
            
            // 收益信息
            if (data.profitability) {
                updateElementText('daily-profit', formatCurrency(data.profitability.daily_profit || 0));
                updateElementText('monthly-profit', formatCurrency(data.profitability.monthly_profit || 0));
                updateElementText('yearly-profit', formatCurrency(data.profitability.yearly_profit || 0));
            }
            
            // 网络信息
            if (data.network_info) {
                updateElementText('btc-price-result', formatCurrency(data.network_info.btc_price || 0, 0));
                updateElementText('network-difficulty-result', formatNumber(data.network_info.difficulty / 1e12, 2) + 'T');
                updateElementText('network-hashrate-result', formatNumber(data.network_info.hashrate_eh, 1) + ' EH/s');
            }
        }
        
        function updateElementText(id, text) {
            const element = safeGetById(id);
            if (element) {
                element.textContent = text;
            }
        }
        
        function showError(message) {
            console.error("Error:", message);
            // 可以添加用户界面错误显示
        }
        
        function fetchNetworkStats() {
            fetch('/get_network_stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateNetworkDisplay(data);
                    }
                })
                .catch(error => {
                    console.error('Failed to fetch network stats:', error);
                });
        }
        
        function updateNetworkDisplay(data) {
            updateElementText('btc-price', '$' + formatNumber(data.btc_price || 0, 0));
            updateElementText('network-difficulty', formatNumber((data.difficulty || 0) / 1e12, 2) + 'T');
            updateElementText('network-hashrate', formatNumber(data.hashrate_eh || 0, 1) + ' EH/s');
            updateElementText('block-reward', (data.block_reward || 0) + ' BTC');
        }
        
        function fetchMiners() {
            fetch('/get_miners')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.miners) {
                        localStorage.setItem('miners', JSON.stringify(data.miners));
                        populateMinerSelect(data.miners);
                        console.log("矿机列表加载成功:", data.miners.length);
                    }
                })
                .catch(error => {
                    console.error('Failed to fetch miners:', error);
                });
        }
        
        function populateMinerSelect(miners) {
            if (!elements.miner_model) return;
            
            elements.miner_model.innerHTML = '<option value="">选择矿机型号 / Select Miner Model</option>';
            
            miners.forEach(miner => {
                const option = document.createElement('option');
                option.value = miner.name;
                option.textContent = `${miner.name} (${miner.hashrate} TH/s, ${miner.power_watt}W)`;
                elements.miner_model.appendChild(option);
            });
        }
        
        function generateProfitChart(minerModel, minerCount, clientElectricityCost) {
            // 热力图生成逻辑
            console.log('Generating profit chart for:', minerModel, minerCount, clientElectricityCost);
        }
        
        function formatNumber(value, decimals = 2) {
            const formatter = new Intl.NumberFormat('en-US', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            });
            return formatter.format(value);
        }
        
        function formatCurrency(value, decimals = 2) {
            return '$' + formatNumber(value, decimals);
        }
        
        // 初始化应用
        init();
    }
});