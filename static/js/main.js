// Bitcoin Mining Calculator - Main JavaScript (Fixed Version)
document.addEventListener('DOMContentLoaded', function() {
    console.log("页面已加载，初始化应用...");
    
    // 等待DOM完全渲染后再初始化
    setTimeout(function() {
        try {
            initializeApplication();
        } catch (error) {
            console.error("Application initialization failed:", error);
        }
    }, 500);
    
    function initializeApplication() {
        console.log("开始初始化应用程序...");
        
        // 获取所有必需的DOM元素
        const elements = getDOMElements();
        
        // 验证关键元素是否存在
        if (!validateElements(elements)) {
            console.warn("Some required DOM elements are missing, retrying in 1 second...");
            setTimeout(initializeApplication, 1000);
            return;
        }
        
        // 初始化应用
        initializeApp(elements);
    }
    
    function getDOMElements() {
        return {
            // 网络信息显示元素
            btcPriceEl: document.getElementById('btc-price'),
            networkDifficultyEl: document.getElementById('network-difficulty'),
            networkHashrateEl: document.getElementById('network-hashrate'),
            blockRewardEl: document.getElementById('block-reward'),
            
            // 表单输入元素
            minerModelSelect: document.getElementById('miner-model'),
            sitePowerMwInput: document.getElementById('site-power-mw'),
            minerCountInput: document.getElementById('miner-count'),
            hashrateInput: document.getElementById('hashrate'),
            hashrateUnitSelect: document.getElementById('hashrate-unit'),
            powerConsumptionInput: document.getElementById('power-consumption'),
            electricityCostInput: document.getElementById('electricity-cost'),
            clientElectricityCostInput: document.getElementById('client-electricity-cost'),
            btcPriceInput: document.getElementById('btc-price-input'),
            useRealTimeCheckbox: document.getElementById('use-real-time'),
            calculatorForm: document.getElementById('mining-calculator-form'),
            
            // 总算力和总功耗元素
            totalHashrateInput: document.getElementById('total-hashrate'),
            totalPowerInput: document.getElementById('total-power'),
            totalHashrateDisplay: document.getElementById('total-hashrate-display'),
            totalPowerDisplay: document.getElementById('total-power-display'),
            
            // 结果显示元素
            resultsCard: document.getElementById('results-card'),
            chartCard: document.getElementById('chart-card')
        };
    }
    
    function validateElements(elements) {
        const requiredElements = [
            'minerModelSelect', 'minerCountInput', 'hashrateInput', 
            'powerConsumptionInput', 'calculatorForm'
        ];
        
        for (let key of requiredElements) {
            if (!elements[key]) {
                console.warn(`Required element missing: ${key}`);
                return false;
            }
        }
        return true;
    }
    
    function initializeApp(elements) {
        console.log("DOM元素验证成功，开始初始化功能...");
        
        // 防止无限循环的标志
        let isUpdatingMinerCount = false;
        let isUpdatingSitePower = false;
        
        // 安全的元素访问函数
        function safeAccess(element, callback) {
            if (element && typeof callback === 'function') {
                try {
                    callback(element);
                } catch (error) {
                    console.warn('Element access error:', error);
                }
            }
        }
        
        // 安全的样式设置函数
        function safeSetStyle(elementId, property, value) {
            const element = document.getElementById(elementId);
            if (element && element.style) {
                element.style[property] = value;
            }
        }
        
        // 初始化功能
        function init() {
            // 获取当前语言设置
            const currentLang = document.querySelector('meta[name="language"]')?.content || 'zh';
            console.log("当前语言设置:", currentLang);
            
            // 加载网络数据
            fetchNetworkStats();
            
            // 启动网络统计数据自动刷新
            startNetworkStatsAutoRefresh();
            
            // 加载矿机型号列表
            fetchMiners();
            
            // 初始化总算力和总功耗计算
            setTimeout(function() {
                calculateTotalHashrateAndPower();
            }, 1000);
            
            // 绑定事件监听器
            bindEventListeners();
        }
        
        // 绑定事件监听器
        function bindEventListeners() {
            // 表单提交事件
            if (elements.calculatorForm) {
                elements.calculatorForm.addEventListener('submit', handleCalculateSubmit);
            }
            
            // 矿机型号选择事件
            if (elements.minerModelSelect) {
                elements.minerModelSelect.addEventListener('change', updateMinerSpecs);
            }
            
            // 矿场功率输入事件
            if (elements.sitePowerMwInput) {
                elements.sitePowerMwInput.addEventListener('input', updateMinerCount);
            }
            
            // 矿机数量输入事件
            if (elements.minerCountInput) {
                elements.minerCountInput.addEventListener('input', function() {
                    updateSitePower();
                    calculateTotalHashrateAndPower();
                });
            }
            
            // 算力和功耗输入事件
            if (elements.hashrateInput) {
                elements.hashrateInput.addEventListener('input', calculateTotalHashrateAndPower);
            }
            
            if (elements.powerConsumptionInput) {
                elements.powerConsumptionInput.addEventListener('input', calculateTotalHashrateAndPower);
            }
            
            // 实时数据切换事件
            if (elements.useRealTimeCheckbox) {
                elements.useRealTimeCheckbox.addEventListener('change', handleRealTimeToggle);
            }
            
            // 图表生成按钮
            const chartBtn = document.getElementById('generate-chart-btn');
            if (chartBtn) {
                chartBtn.addEventListener('click', function() {
                    const minerModel = elements.minerModelSelect.value;
                    const minerCount = elements.minerCountInput.value || 1;
                    const clientElectricityCost = elements.clientElectricityCostInput.value || 0;
                    
                    if (!minerModel) {
                        showError('请先选择矿机型号再生成热力图。');
                        return;
                    }
                    
                    generateProfitChart(minerModel, minerCount, clientElectricityCost);
                });
            }
        }
        
        // 处理实时数据切换
        function handleRealTimeToggle() {
            if (elements.useRealTimeCheckbox && elements.useRealTimeCheckbox.checked) {
                if (elements.btcPriceInput) elements.btcPriceInput.disabled = true;
                fetchNetworkStats();
            } else {
                if (elements.btcPriceInput) elements.btcPriceInput.disabled = false;
            }
        }
        
        // 更新矿机规格
        function updateMinerSpecs() {
            if (!elements.minerModelSelect) return;
            
            const selectedMiner = elements.minerModelSelect.value;
            
            if (selectedMiner) {
                const miners = JSON.parse(localStorage.getItem('miners') || '[]');
                const miner = miners.find(m => m.name === selectedMiner);
                
                if (miner) {
                    if (elements.hashrateInput) elements.hashrateInput.value = miner.hashrate;
                    if (elements.powerConsumptionInput) elements.powerConsumptionInput.value = miner.power_watt;
                    
                    // 禁用手动输入
                    if (elements.hashrateInput) elements.hashrateInput.disabled = true;
                    if (elements.hashrateUnitSelect) elements.hashrateUnitSelect.disabled = true;
                    if (elements.powerConsumptionInput) elements.powerConsumptionInput.disabled = true;
                    
                    updateMinerCount();
                    calculateTotalHashrateAndPower();
                }
            } else {
                // 启用手动输入
                if (elements.hashrateInput) elements.hashrateInput.disabled = false;
                if (elements.hashrateUnitSelect) elements.hashrateUnitSelect.disabled = false;
                if (elements.powerConsumptionInput) elements.powerConsumptionInput.disabled = false;
            }
        }
        
        // 更新矿机数量
        function updateMinerCount() {
            if (isUpdatingSitePower || !elements.sitePowerMwInput || !elements.powerConsumptionInput || !elements.minerCountInput) {
                return;
            }
            
            isUpdatingMinerCount = true;
            
            const sitePowerMw = parseFloat(elements.sitePowerMwInput.value) || 0;
            const powerWatt = parseFloat(elements.powerConsumptionInput.value) || 0;
            
            if (sitePowerMw > 0 && powerWatt > 0) {
                const maxMiners = Math.floor((sitePowerMw * 1000000) / powerWatt);
                elements.minerCountInput.value = maxMiners;
                calculateTotalHashrateAndPower();
            }
            
            isUpdatingMinerCount = false;
        }
        
        // 更新矿场功率
        function updateSitePower() {
            if (isUpdatingMinerCount || !elements.minerCountInput || !elements.powerConsumptionInput || !elements.sitePowerMwInput) {
                return;
            }
            
            isUpdatingSitePower = true;
            
            const minerCount = parseInt(elements.minerCountInput.value) || 0;
            const powerWatt = parseFloat(elements.powerConsumptionInput.value) || 0;
            
            if (minerCount > 0 && powerWatt > 0) {
                const requiredPowerMw = (minerCount * powerWatt) / 1000000;
                elements.sitePowerMwInput.value = requiredPowerMw.toFixed(2);
            }
            
            isUpdatingSitePower = false;
        }
        
        // 计算总算力和总功耗
        function calculateTotalHashrateAndPower() {
            if (!elements.minerCountInput || !elements.hashrateInput || !elements.powerConsumptionInput) {
                return;
            }
            
            const minerCount = parseInt(elements.minerCountInput.value) || 0;
            const hashrate = parseFloat(elements.hashrateInput.value) || 0;
            const powerWatt = parseFloat(elements.powerConsumptionInput.value) || 0;
            
            if (minerCount > 0 && hashrate > 0 && powerWatt > 0) {
                const totalHashrate = minerCount * hashrate;
                const totalPower = minerCount * powerWatt;
                
                // 更新隐藏字段
                if (elements.totalHashrateInput) {
                    elements.totalHashrateInput.value = totalHashrate.toFixed(0);
                }
                
                if (elements.totalPowerInput) {
                    elements.totalPowerInput.value = totalPower.toFixed(0);
                }
                
                // 更新显示字段
                if (elements.totalHashrateDisplay) {
                    elements.totalHashrateDisplay.value = totalHashrate.toFixed(0);
                }
                
                if (elements.totalPowerDisplay) {
                    elements.totalPowerDisplay.value = totalPower.toFixed(0);
                }
                
                return { totalHashrate, totalPower };
            }
            
            return null;
        }
        
        // 处理计算表单提交
        function handleCalculateSubmit(event) {
            event.preventDefault();
            
            console.log("开始处理计算请求...");
            
            const formData = new FormData(elements.calculatorForm);
            
            fetch('/calculate', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log("计算结果:", data);
                displayResults(data);
            })
            .catch(error => {
                console.error('计算请求失败:', error);
                showError('计算请求失败，请稍后重试。');
            });
        }
        
        // 显示计算结果
        function displayResults(data) {
            if (!data.success) {
                showError(data.error || '计算失败');
                return;
            }
            
            // 安全显示结果卡片
            safeSetStyle('results-card', 'display', 'block');
            
            // 更新BTC挖矿产出显示
            updateBtcOutputDisplay(data);
            
            // 更新网络和挖矿信息
            updateNetworkInfo(data);
            
            // 更新收益分析
            updateProfitAnalysis(data);
            
            // 更新ROI分析
            updateROIAnalysis(data);
            
            // 更新限电分析
            updateCurtailmentAnalysis(data);
        }
        
        // 显示错误信息
        function showError(message) {
            console.error("Error:", message);
            // 可以在这里添加用户界面错误显示逻辑
        }
        
        // 获取网络统计数据
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
        
        // 更新网络数据显示
        function updateNetworkDisplay(data) {
            if (elements.btcPriceEl && data.btc_price) {
                elements.btcPriceEl.textContent = '$' + formatNumber(data.btc_price, 0);
            }
            
            if (elements.networkDifficultyEl && data.difficulty) {
                elements.networkDifficultyEl.textContent = formatNumber(data.difficulty / 1e12, 2) + 'T';
            }
            
            if (elements.networkHashrateEl && data.hashrate_eh) {
                elements.networkHashrateEl.textContent = formatNumber(data.hashrate_eh, 1) + ' EH/s';
            }
            
            if (elements.blockRewardEl && data.block_reward) {
                elements.blockRewardEl.textContent = data.block_reward + ' BTC';
            }
        }
        
        // 获取矿机列表
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
        
        // 填充矿机选择列表
        function populateMinerSelect(miners) {
            if (!elements.minerModelSelect) return;
            
            // 清空现有选项
            elements.minerModelSelect.innerHTML = '<option value="">选择矿机型号 / Select Miner Model</option>';
            
            miners.forEach(miner => {
                const option = document.createElement('option');
                option.value = miner.name;
                option.textContent = `${miner.name} (${miner.hashrate} TH/s, ${miner.power_watt}W)`;
                elements.minerModelSelect.appendChild(option);
            });
        }
        
        // 启动网络统计数据自动刷新
        function startNetworkStatsAutoRefresh() {
            setInterval(fetchNetworkStats, 30000); // 每30秒刷新一次
        }
        
        // 工具函数：格式化数字
        function formatNumber(value, decimals = 2) {
            if (decimals === undefined) decimals = 2;
            
            const formatter = new Intl.NumberFormat('en-US', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            });
            
            return formatter.format(value);
        }
        
        // 工具函数：格式化货币
        function formatCurrency(value, decimals = 2) {
            return '$' + formatNumber(value, decimals);
        }
        
        // 占位符函数 - 这些需要根据具体需求实现
        function updateBtcOutputDisplay(data) {
            // BTC产出显示逻辑
        }
        
        function updateNetworkInfo(data) {
            // 网络信息显示逻辑
        }
        
        function updateProfitAnalysis(data) {
            // 收益分析显示逻辑
        }
        
        function updateROIAnalysis(data) {
            // ROI分析显示逻辑
        }
        
        function updateCurtailmentAnalysis(data) {
            // 限电分析显示逻辑
        }
        
        function generateProfitChart(minerModel, minerCount, clientElectricityCost) {
            // 热力图生成逻辑
        }
        
        // 初始化应用
        init();
    }
});