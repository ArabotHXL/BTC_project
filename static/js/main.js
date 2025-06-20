// Bitcoin Mining Calculator - Clean Version
(function() {
    'use strict';
    
    // 等待DOM完全加载
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initApp);
    } else {
        setTimeout(initApp, 100);
    }
    
    function initApp() {
        console.log("应用初始化开始");
        
        // DOM元素缓存
        const elements = {};
        
        // 安全获取元素
        function safeGet(id) {
            if (!elements[id]) {
                elements[id] = document.getElementById(id);
            }
            return elements[id];
        }
        
        // 安全设置样式
        function safeStyle(id, prop, val) {
            const el = safeGet(id);
            if (el && el.style) {
                el.style[prop] = val;
            }
        }
        
        // 安全设置值
        function safeValue(id, val) {
            const el = safeGet(id);
            if (el && 'value' in el) {
                el.value = val;
            }
        }
        
        // 安全获取值
        function getValue(id, defaultVal = '') {
            const el = safeGet(id);
            return el ? (el.value || defaultVal) : defaultVal;
        }
        
        // 安全事件绑定
        function safeEvent(id, event, handler) {
            const el = safeGet(id);
            if (el && el.addEventListener) {
                el.addEventListener(event, handler);
            }
        }
        
        // 初始化所有功能
        function initialize() {
            loadNetworkData();
            loadMinerData();
            bindEvents();
            startAutoRefresh();
        }
        
        // 绑定事件监听器
        function bindEvents() {
            safeEvent('mining-calculator-form', 'submit', handleSubmit);
            safeEvent('miner-model', 'change', updateMinerSpecs);
            safeEvent('miner-count', 'input', updateCalculations);
            safeEvent('hashrate', 'input', updateCalculations);
            safeEvent('power-consumption', 'input', updateCalculations);
            safeEvent('site-power-mw', 'input', updateMinerCount);
            safeEvent('use-real-time', 'change', toggleRealTime);
        }
        
        // 处理表单提交
        function handleSubmit(e) {
            e.preventDefault();
            
            const form = safeGet('mining-calculator-form');
            if (!form) return;
            
            const formData = new FormData(form);
            
            fetch('/calculate', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayResults(data);
                } else {
                    console.error('计算错误:', data.error);
                }
            })
            .catch(error => {
                console.error('请求失败:', error);
            });
        }
        
        // 显示计算结果
        function displayResults(data) {
            // 安全显示结果卡片
            safeStyle('results-card', 'display', 'block');
            
            // 更新各种结果显示
            if (data.btc_mined) {
                updateText('daily-btc', formatNumber(data.btc_mined.daily, 6) + ' BTC');
                updateText('monthly-btc', formatNumber(data.btc_mined.monthly, 4) + ' BTC');
                updateText('yearly-btc', formatNumber(data.btc_mined.yearly, 2) + ' BTC');
            }
            
            if (data.profitability) {
                updateText('daily-profit', formatCurrency(data.profitability.daily_profit));
                updateText('monthly-profit', formatCurrency(data.profitability.monthly_profit));
                updateText('yearly-profit', formatCurrency(data.profitability.yearly_profit));
            }
        }
        
        // 安全更新文本内容
        function updateText(id, text) {
            const el = safeGet(id);
            if (el) {
                el.textContent = text;
            }
        }
        
        // 更新矿机规格
        function updateMinerSpecs() {
            const model = getValue('miner-model');
            if (!model) return;
            
            const miners = JSON.parse(localStorage.getItem('miners') || '[]');
            const miner = miners.find(m => m.name === model);
            
            if (miner) {
                safeValue('hashrate', miner.hashrate);
                safeValue('power-consumption', miner.power_watt);
                updateCalculations();
            }
        }
        
        // 更新计算
        function updateCalculations() {
            const count = parseInt(getValue('miner-count', '0')) || 0;
            const hashrate = parseFloat(getValue('hashrate', '0')) || 0;
            const power = parseFloat(getValue('power-consumption', '0')) || 0;
            
            if (count > 0 && hashrate > 0 && power > 0) {
                const totalHashrate = count * hashrate;
                const totalPower = count * power;
                
                safeValue('total-hashrate', totalHashrate.toFixed(0));
                safeValue('total-power', totalPower.toFixed(0));
                safeValue('total-hashrate-display', totalHashrate.toFixed(0));
                safeValue('total-power-display', totalPower.toFixed(0));
            }
        }
        
        // 更新矿机数量
        function updateMinerCount() {
            const sitePower = parseFloat(getValue('site-power-mw', '0')) || 0;
            const minerPower = parseFloat(getValue('power-consumption', '0')) || 0;
            
            if (sitePower > 0 && minerPower > 0) {
                const maxMiners = Math.floor((sitePower * 1000000) / minerPower);
                safeValue('miner-count', maxMiners);
                updateCalculations();
            }
        }
        
        // 切换实时数据
        function toggleRealTime() {
            const useRealTime = safeGet('use-real-time');
            const btcInput = safeGet('btc-price-input');
            
            if (useRealTime && btcInput) {
                btcInput.disabled = useRealTime.checked;
                if (useRealTime.checked) {
                    loadNetworkData();
                }
            }
        }
        
        // 加载网络数据
        function loadNetworkData() {
            fetch('/network_stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateNetworkDisplay(data);
                    }
                })
                .catch(error => {
                    console.warn('网络数据加载失败:', error);
                });
        }
        
        // 更新网络数据显示
        function updateNetworkDisplay(data) {
            updateText('btc-price', '$' + formatNumber(data.btc_price || 0, 0));
            updateText('network-difficulty', formatNumber((data.difficulty || 0) / 1e12, 2) + 'T');
            updateText('network-hashrate', formatNumber(data.hashrate_eh || 0, 1) + ' EH/s');
            updateText('block-reward', (data.block_reward || 0) + ' BTC');
        }
        
        // 加载矿机数据
        function loadMinerData() {
            fetch('/miners')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.miners) {
                        localStorage.setItem('miners', JSON.stringify(data.miners));
                        populateMinerSelect(data.miners);
                        console.log("矿机列表加载成功:", data.miners.length);
                    }
                })
                .catch(error => {
                    console.warn('矿机数据加载失败:', error);
                });
        }
        
        // 填充矿机选择列表
        function populateMinerSelect(miners) {
            const select = safeGet('miner-model');
            if (!select) return;
            
            select.innerHTML = '<option value="">选择矿机型号</option>';
            
            miners.forEach(miner => {
                const option = document.createElement('option');
                option.value = miner.name;
                option.textContent = `${miner.name} (${miner.hashrate} TH/s, ${miner.power_watt}W)`;
                select.appendChild(option);
            });
        }
        
        // 启动自动刷新
        function startAutoRefresh() {
            setInterval(loadNetworkData, 30000);
        }
        
        // 工具函数
        function formatNumber(value, decimals = 2) {
            return new Intl.NumberFormat('en-US', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            }).format(value);
        }
        
        function formatCurrency(value, decimals = 2) {
            return '$' + formatNumber(value, decimals);
        }
        
        // 启动初始化
        setTimeout(initialize, 500);
    }
})();