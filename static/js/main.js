// Bitcoin Mining Calculator - Main JavaScript

// 格式化数字函数 - 确保在页面加载前定义
function formatNumber(value, decimals) {
    if (decimals === undefined) decimals = 2;
    
    var formatter = new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
    
    return formatter.format(value);
}

// 格式化货币值函数
function formatCurrency(value, decimals) {
    return '$' + formatNumber(value, decimals);
}

document.addEventListener('DOMContentLoaded', function() {
    console.log("页面已加载，初始化应用...");
    
    // 元素引用 (Element references)
    var btcPriceEl = document.getElementById('btc-price');
    var networkDifficultyEl = document.getElementById('network-difficulty');
    // 第二个difficulty元素已移除（重复卡片）
    var networkHashrateEl = document.getElementById('network-hashrate');
    var networkHashrateValueEl = document.getElementById('network-hashrate-value'); // 第二个hashrate元素
    var blockRewardEl = document.getElementById('block-reward');
    
    var minerModelSelect = document.getElementById('miner-model');
    var sitePowerMwInput = document.getElementById('site-power-mw');
    var minerCountInput = document.getElementById('miner-count');
    var hashrateInput = document.getElementById('hashrate');
    var hashrateUnitSelect = document.getElementById('hashrate-unit');
    var powerConsumptionInput = document.getElementById('power-consumption');
    var electricityCostInput = document.getElementById('electricity-cost');
    var clientElectricityCostInput = document.getElementById('client-electricity-cost');
    var btcPriceInput = document.getElementById('btc-price-input');
    var useRealTimeCheckbox = document.getElementById('use-real-time');
    var calculatorForm = document.getElementById('mining-calculator-form');
    
    // 检查总算力和总功耗输入框
    var totalHashrateInput = document.getElementById('total-hashrate');
    var totalPowerInput = document.getElementById('total-power');
    
    console.log("元素检查 - 矿机数量:", minerCountInput ? "已找到" : "未找到");
    console.log("元素检查 - 单矿机算力:", hashrateInput ? "已找到" : "未找到");
    console.log("元素检查 - 单矿机功耗:", powerConsumptionInput ? "已找到" : "未找到");
    console.log("元素检查 - 总算力输入框:", totalHashrateInput ? "已找到" : "未找到");
    console.log("元素检查 - 总功耗输入框:", totalPowerInput ? "已找到" : "未找到");
    
    // 网络统计元素检查
    console.log("=== 网络统计元素检查 ===");
    console.log("btcPriceEl:", btcPriceEl ? "已找到" : "未找到", btcPriceEl ? btcPriceEl.textContent : "N/A");
    console.log("networkDifficultyEl:", networkDifficultyEl ? "已找到" : "未找到", networkDifficultyEl ? networkDifficultyEl.textContent : "N/A");
    console.log("networkDifficultyValueEl:", networkDifficultyValueEl ? "已找到" : "未找到", networkDifficultyValueEl ? networkDifficultyValueEl.textContent : "N/A");
    console.log("networkHashrateEl:", networkHashrateEl ? "已找到" : "未找到", networkHashrateEl ? networkHashrateEl.textContent : "N/A");
    console.log("networkHashrateValueEl:", networkHashrateValueEl ? "已找到" : "未找到", networkHashrateValueEl ? networkHashrateValueEl.textContent : "N/A");
    console.log("blockRewardEl:", blockRewardEl ? "已找到" : "未找到", blockRewardEl ? blockRewardEl.textContent : "N/A");
    
    // formatNumber函数测试
    console.log("=== formatNumber函数测试 ===");
    if (typeof formatNumber === 'function') {
        console.log("formatNumber(129.4352355803448):", formatNumber(129.4352355803448));
        console.log("formatNumber(129435235580344):", formatNumber(129435235580344));
        console.log("formatNumber(129435235580344, 0):", formatNumber(129435235580344, 0));
    } else {
        console.error("formatNumber函数未定义!");
    }
    
    var resultsCard = document.getElementById('results-card');
    var chartCard = document.getElementById('chart-card');
    
    // 防止无限循环的标志
    var isUpdatingMinerCount = false;
    var isUpdatingSitePower = false;
    
    // 清除旧的网络统计缓存 (Clear old network stats cache)
    function clearNetworkStatsCache() {
        localStorage.removeItem('last_btc_price');
        localStorage.removeItem('last_network_difficulty');
        localStorage.removeItem('last_network_hashrate');
        localStorage.removeItem('last_block_reward');
        localStorage.removeItem('lastNetworkStatsUpdate');
        localStorage.removeItem('lastBtcPrice');
        localStorage.removeItem('lastDifficulty');
        localStorage.removeItem('lastHashrate');
        localStorage.removeItem('lastBlockReward');
        console.log('已清除网络统计数据缓存');
        
        // 同时清除元素的更新标记
        var elements = ['network-difficulty', 'network-difficulty-value'];
        elements.forEach(function(id) {
            var el = document.getElementById(id);
            if (el) {
                el.removeAttribute('data-updated');
                console.log('清除元素', id, '的更新标记');
            }
        });
    }
    
    // 优化的初始化 (Optimized Initialization)
    function init() {
        console.log("页面加载优化器启动");
        const startTime = performance.now();
        
        // 检查并清除无效的网络统计缓存
        var cachedDifficulty = localStorage.getItem('last_network_difficulty');
        if (cachedDifficulty && parseFloat(cachedDifficulty) < 10) {
            console.log('页面加载时检测到无效的难度缓存，清除所有网络统计缓存');
            clearNetworkStatsCache();
        }
        
        // 获取当前语言设置 (Get current language setting)
        const currentLang = document.querySelector('meta[name="language"]')?.content || 'zh';
        
        // 并行加载数据，避免阻塞
        Promise.all([
            // 立即获取网络数据，无延迟
            fetchNetworkStatsOptimized(),
            // 并行加载矿机数据
            fetchMinersOptimized()
        ]).then(function() {
            const loadTime = performance.now() - startTime;
            console.log("DOM加载完成，用时:", loadTime.toFixed(2), "ms");
            
            // 检查关键DOM元素
            const totalHashrateInput = document.getElementById('total-hashrate');
            const totalPowerInput = document.getElementById('total-power');
            const totalHashrateDisplay = document.getElementById('total-hashrate-display');
            const totalPowerDisplay = document.getElementById('total-power-display');
            
            console.log("DOM元素获取结果:");
            console.log("总算力隐藏输入框:", totalHashrateInput ? "找到" : "未找到");
            console.log("总功耗隐藏输入框:", totalPowerInput ? "找到" : "未找到");
            console.log("总算力显示输入框:", totalHashrateDisplay ? "找到" : "未找到");
            console.log("总功耗显示输入框:", totalPowerDisplay ? "找到" : "未找到");
        }).catch(function(error) {
            console.error("初始化过程中出错:", error);
        });
        
        // 延迟加载次要功能，避免阻塞主要内容
        setTimeout(function() {
            console.log("开始加载次要功能");
            initializeSecondaryFeatures();
        }, 100);
        
        // 立即绑定关键事件
        bindCriticalEvents();
        
        // 立即强制清除所有网络统计缓存
        console.log('立即清除所有网络统计缓存');
        clearNetworkStatsCache();
        
        // 立即强制刷新网络统计数据
        setTimeout(function() {
            console.log('立即强制刷新网络统计数据');
            fetchNetworkStats(true); // 显示loading状态，确保用户看到更新
        }, 100);
        
        // 启动网络统计数据自动刷新
        setTimeout(function() {
            console.log('启动网络统计数据自动刷新');
            startNetworkStatsAutoRefresh();
        }, 500);
    }
    
    // 优化的网络数据获取
    function fetchNetworkStatsOptimized() {
        return new Promise(function(resolve, reject) {
            console.log("网络数据预加载成功");
            
            fetch('/api/get-btc-price', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 缓存价格数据
                    const price = Math.round(data.btc_price);
                    localStorage.setItem('last_btc_price', price);
                    console.log("已更新价格缓存:", price);
                    
                    // 更新BTC价格显示
                    if (btcPriceDisplay) {
                        btcPriceDisplay.textContent = formatCurrency(price);
                    }
                }
                resolve(data);
            })
            .catch(error => {
                console.error("获取价格数据失败:", error);
                resolve(null); // 不阻塞其他加载
            });
        });
    }
    
    // 优化的矿机数据获取
    function fetchMinersOptimized() {
        return new Promise(function(resolve, reject) {
            console.log("开始加载矿机数据");
            
            fetch('/api/miners', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    localStorage.setItem('miners', JSON.stringify(data));
                    populateMinerOptions(data);
                    console.log("矿机列表加载成功:", data.length);
                }
                resolve(data);
            })
            .catch(error => {
                console.error("加载矿机数据失败:", error);
                resolve(null);
            });
        });
    }
    
    // 次要功能初始化
    function initializeSecondaryFeatures() {
        // 开始初始化图表
        console.log("开始初始化图表");
        initializeChart();
        
        // 获取分析数据并更新小部件
        fetch('/api/analytics-data')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log("Analytics data received:", [data]);
                    updateAnalyticsWidget(data.data);
                }
            })
            .catch(error => console.error("获取分析数据失败:", error));
    }
    
    // 绑定关键事件
    function bindCriticalEvents() {
        // 事件绑定 (Event bindings)
        if (calculatorForm) {
            calculatorForm.addEventListener('submit', handleCalculateSubmit);
        }
        
        if (minerModelSelect) {
            minerModelSelect.addEventListener('change', updateMinerSpecs);
        }
        
        if (sitePowerMwInput) {
            sitePowerMwInput.addEventListener('input', debounce(updateMinerCount, 300));
        }
        
        if (minerCountInput) {
            // 使用防抖优化性能
            minerCountInput.addEventListener('input', debounce(function() {
                updateSitePower();
                calculateTotalHashrateAndPower();
            }, 300));
        }
        
        if (hashrateInput) {
            hashrateInput.addEventListener('input', debounce(calculateTotalHashrateAndPower, 300));
        }
        
        if (powerConsumptionInput) {
            powerConsumptionInput.addEventListener('input', debounce(calculateTotalHashrateAndPower, 300));
        }
    }
    
    // 防抖函数优化性能
    function debounce(func, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }
        
        if (useRealTimeCheckbox) {
            useRealTimeCheckbox.addEventListener('change', handleRealTimeToggle);
        }
        
        // 图表生成按钮
        var chartBtn = document.getElementById('generate-chart-btn');
        if (chartBtn) {
            chartBtn.addEventListener('click', function() {
                var minerModel = minerModelSelect.value;
                var minerCount = minerCountInput.value || 1;
                var clientElectricityCost = clientElectricityCostInput.value || 0;
                
                if (!minerModel) {
                    showError('请先选择矿机型号再生成热力图。(Please select a miner model first.)');
                    return;
                }
                
                generateProfitChart(minerModel, minerCount, clientElectricityCost);
            });
        }
    }
    
    // 处理实时数据切换 (Handle real-time data toggle)
    function handleRealTimeToggle() {
        if (useRealTimeCheckbox.checked) {
            btcPriceInput.disabled = true;
            fetchNetworkStats();
        } else {
            btcPriceInput.disabled = false;
        }
    }
    
    // 更新矿机规格 (Update miner specifications)
    function updateMinerSpecs() {
        var selectedMiner = minerModelSelect.value;
        
        if (selectedMiner) {
            // 从localStorage获取矿机数据 (Get miner data from localStorage)
            var miners = JSON.parse(localStorage.getItem('miners') || '[]');
            var miner = miners.find(function(m) { return m.name === selectedMiner; });
            
            if (miner) {
                hashrateInput.value = miner.hashrate;
                powerConsumptionInput.value = miner.power_watt;
                
                // 禁用手动输入 (Disable manual input)
                hashrateInput.disabled = true;
                hashrateUnitSelect.disabled = true;
                powerConsumptionInput.disabled = true;
                
                // 基于矿机功率和数量更新显示 (Update based on miner power and count)
                updateMinerCount();
                
                // 计算总算力和总功耗
                calculateTotalHashrateAndPower();
            }
        } else {
            // 启用手动输入 (Enable manual input)
            hashrateInput.disabled = false;
            hashrateUnitSelect.disabled = false;
            powerConsumptionInput.disabled = false;
        }
    }
    
    // 更新矿机数量 (Update miner count)
    function updateMinerCount() {
        // 如果已经在更新矿场功率，则退出以防止循环
        if (isUpdatingSitePower) {
            return;
        }
        
        // 设置标志，表示正在更新矿机数量
        isUpdatingMinerCount = true;
        
        var sitePowerMw = parseFloat(sitePowerMwInput.value) || 0;
        var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
        
        if (sitePowerMw > 0 && powerWatt > 0) {
            // 计算最大矿机数量 (Calculate maximum miner count)
            // Formula: (site_power_mw * 1000) / (power_watt / 1000)
            var maxMiners = Math.floor((sitePowerMw * 1000000) / powerWatt);
            minerCountInput.value = maxMiners;
            
            // 计算总算力和总功耗
            calculateTotalHashrateAndPower();
        }
        
        // 清除标志
        isUpdatingMinerCount = false;
    }
    
    // 根据矿机数量更新矿场功率 (Update site power based on miner count)
    function updateSitePower() {
        try {
            // 如果已经在更新矿机数量，则退出以防止循环
            if (isUpdatingMinerCount) {
                console.log("矿机数量正在更新中，跳过矿场功率更新");
                return;
            }
            
            // 设置标志，表示正在更新矿场功率
            isUpdatingSitePower = true;
            
            // 获取必要的值
            var minerCount = parseInt(minerCountInput.value) || 0;
            var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
            
            console.log("矿机数量发生变化 - 更新矿场功率...");
            console.log("  矿机数量:", minerCount);
            console.log("  单机功率:", powerWatt);
            console.log("  功率输入框元素:", powerConsumptionInput ? "已找到" : "未找到");
            console.log("  矿场功率输入框元素:", sitePowerMwInput ? "已找到" : "未找到");
            
            if (minerCount > 0 && powerWatt > 0) {
                // 计算所需的矿场功率 (Calculate required site power)
                var requiredPowerMw = (minerCount * powerWatt) / 1000000;
                
                console.log("计算得到的新矿场功率:", requiredPowerMw.toFixed(2), "MW");
                console.log("当前矿场功率:", parseFloat(sitePowerMwInput.value).toFixed(2), "MW");
                
                // 设置新的矿场功率
                sitePowerMwInput.value = requiredPowerMw.toFixed(2);
                console.log("矿场功率已更新为:", requiredPowerMw.toFixed(2), "MW");
            } else {
                console.log("无法更新矿场功率 - 矿机数量或单机功率为0");
            }
        } catch (error) {
            console.error("更新矿场功率时发生错误:", error);
        } finally {
            // 清除标志
            isUpdatingSitePower = false;
        }
    }
    
    // 计算总算力和总功耗
    function calculateTotalHashrateAndPower() {
        var minerCount = parseInt(minerCountInput.value) || 0;
        var hashrate = parseFloat(hashrateInput.value) || 0;
        var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
        
        console.log("计算总算力和总功耗 - 矿机数量:", minerCount, "单矿机算力:", hashrate, "单矿机功耗:", powerWatt);
        
        if (minerCount > 0 && hashrate > 0 && powerWatt > 0) {
            // 计算总算力和总功耗
            var totalHashrate = minerCount * hashrate;
            var totalPower = minerCount * powerWatt;
            
            console.log("计算结果 - 总算力:", totalHashrate, "总功耗:", totalPower);
            
            // 更新隐藏字段
            var totalHashrateInput = document.getElementById('total-hashrate');
            var totalPowerInput = document.getElementById('total-power');
            
            // 更新显示字段
            var totalHashrateDisplay = document.getElementById('total-hashrate-display');
            var totalPowerDisplay = document.getElementById('total-power-display');
            
            // 日志输出字段状态
            console.log("总算力隐藏字段:", totalHashrateInput ? "已找到" : "未找到", 
                        "总功耗隐藏字段:", totalPowerInput ? "已找到" : "未找到");
            console.log("总算力显示字段:", totalHashrateDisplay ? "已找到" : "未找到", 
                        "总功耗显示字段:", totalPowerDisplay ? "已找到" : "未找到");
            
            // 更新隐藏字段（用于表单提交）
            if (totalHashrateInput) {
                totalHashrateInput.value = totalHashrate.toFixed(0);
                console.log("总算力隐藏字段已更新为:", totalHashrate.toFixed(0));
            }
            
            if (totalPowerInput) {
                totalPowerInput.value = totalPower.toFixed(0);
                console.log("总功耗隐藏字段已更新为:", totalPower.toFixed(0));
            }
            
            // 更新显示字段（用于用户界面）
            if (totalHashrateDisplay) {
                totalHashrateDisplay.value = totalHashrate.toFixed(0);
                console.log("总算力显示字段已更新为:", totalHashrate.toFixed(0));
            }
            
            if (totalPowerDisplay) {
                totalPowerDisplay.value = totalPower.toFixed(0);
                console.log("总功耗显示字段已更新为:", totalPower.toFixed(0));
            }
            
            return { totalHashrate: totalHashrate, totalPower: totalPower };
        } else {
            console.log("计算条件不满足 - 矿机数量、算力或功耗有一项为0");
            return null;
        }
    }
    
    // 处理计算表单提交 (Handle calculation form submission)
    function handleCalculateSubmit(event) {
        event.preventDefault();
        
        // 在提交表单前重新计算一次总算力和总功耗
        console.log("表单提交前重新计算总算力和总功耗");
        calculateTotalHashrateAndPower();
        
        // 直接设置总算力和总功耗
        var minerCount = parseInt(minerCountInput.value) || 0;
        var hashrate = parseFloat(hashrateInput.value) || 0;
        var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
        
        if (minerCount > 0 && hashrate > 0 && powerWatt > 0) {
            var totalHashrate = minerCount * hashrate;
            var totalPower = minerCount * powerWatt;
            
            // 获取总算力和总功耗输入框
            var totalHashrateInput = document.getElementById('total-hashrate');
            var totalPowerInput = document.getElementById('total-power');
            
            console.log("表单提交前检查总算力和总功耗输入框");
            console.log("总算力输入框:", totalHashrateInput ? "存在" : "不存在");
            console.log("总功耗输入框:", totalPowerInput ? "存在" : "不存在");
            
            if (totalHashrateInput) {
                console.log("设置总算力为:", totalHashrate);
                totalHashrateInput.value = totalHashrate.toFixed(0);
            }
            
            if (totalPowerInput) {
                console.log("设置总功耗为:", totalPower);
                totalPowerInput.value = totalPower.toFixed(0);
            }
        }
        
        // 表单验证 (Form validation)
        var hasErrors = false;
        
        if (minerModelSelect.value === "") {
            if (!hashrateInput.value || parseFloat(hashrateInput.value) <= 0) {
                showError('请输入有效的算力值。(Please enter a valid hashrate value.)');
                hasErrors = true;
            }
            
            if (!powerConsumptionInput.value || parseFloat(powerConsumptionInput.value) <= 0) {
                showError('请输入有效的功率值。(Please enter a valid power consumption value.)');
                hasErrors = true;
            }
        }
        
        if (!electricityCostInput.value || parseFloat(electricityCostInput.value) < 0) {
            showError('请输入有效的电费。(Please enter a valid electricity cost.)');
            hasErrors = true;
        }
        
        if (!useRealTimeCheckbox.checked && (!btcPriceInput.value || parseFloat(btcPriceInput.value) <= 0)) {
            showError('请输入有效的比特币价格。(Please enter a valid Bitcoin price.)');
            hasErrors = true;
        }
        
        if (hasErrors) {
            return;
        }
        
        // 显示加载状态 (Show loading state)
        setLoadingState(true);
        
        // 收集表单数据 (Collect form data)
        var formData = new FormData(calculatorForm);
        
        // 手动添加总算力和总功耗数据到表单
        var minerCount = parseInt(minerCountInput.value) || 0;
        var hashrate = parseFloat(hashrateInput.value) || 0;
        var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
        
        if (minerCount > 0 && hashrate > 0 && powerWatt > 0) {
            var totalHashrate = minerCount * hashrate;
            var totalPower = minerCount * powerWatt;
            
            // 移除之前的值（如果存在）
            if (formData.has('total_hashrate')) {
                formData.delete('total_hashrate');
            }
            if (formData.has('total_power')) {
                formData.delete('total_power');
            }
            
            // 添加计算出的值
            formData.append('total_hashrate', totalHashrate.toFixed(0));
            formData.append('total_power', totalPower.toFixed(0));
            
            console.log("手动添加到表单数据 - 总算力:", totalHashrate.toFixed(0), "总功耗:", totalPower.toFixed(0));
        }
        
        // 请求计算 (Request calculation)
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/calculate', true);
        
        // 设置30秒超时
        xhr.timeout = 30000;
        
        xhr.onload = function() {
            try {
                if (xhr.status === 200) {
                    // 确保响应不为空
                    if (!xhr.responseText || xhr.responseText.trim() === '') {
                        throw new Error('服务器返回空响应');
                    }
                    
                    var data = JSON.parse(xhr.responseText);
                    
                    if (data && data.success) {
                        // 显示结果 (Display results)
                        displayResults(data);
                    } else {
                        showError(data && data.error ? data.error : '计算过程中发生错误。(An error occurred during calculation.)');
                        console.error('服务器返回错误:', data && data.error ? data.error : null);
                    }
                } else {
                    throw new Error('服务器返回状态码: ' + xhr.status);
                }
            } catch (error) {
                console.error('计算错误:', error);
                showError('计算过程中发生错误，请重试。(An error occurred during calculation, please try again.)');
            } finally {
                // 隐藏加载状态 (Hide loading state)
                setLoadingState(false);
            }
        };
        
        xhr.onerror = function() {
            console.error('请求失败');
            showError('网络错误，请重试。(Network error, please try again.)');
            setLoadingState(false);
        };
        
        xhr.ontimeout = function() {
            console.error('请求超时');
            showError('请求超时，这可能是由于服务器繁忙。请稍后再试。(Request timed out. The server might be busy. Please try again later.)');
            setLoadingState(false);
        };
        
        xhr.send(formData);
    }
    
    // 获取网络状态 (Fetch network status)
    // 用于网络统计数据自动刷新的计时器
    var networkStatsRefreshTimer = null;
    // 网络统计数据刷新间隔（毫秒）
    var networkStatsRefreshInterval = 30000; // 30秒刷新一次
    
    // 启动网络统计数据自动刷新
    function startNetworkStatsAutoRefresh() {
        // 清除可能存在的旧计时器
        stopNetworkStatsAutoRefresh();
        
        // 设置新的自动刷新计时器
        networkStatsRefreshTimer = setInterval(function() {
            // 后台静默刷新，不显示加载状态
            fetchNetworkStats(false);
        }, networkStatsRefreshInterval);
        
        console.log("已启动网络统计数据自动刷新，间隔: " + (networkStatsRefreshInterval/1000) + "秒");
    }
    
    // 停止网络统计数据自动刷新
    function stopNetworkStatsAutoRefresh() {
        if (networkStatsRefreshTimer) {
            clearInterval(networkStatsRefreshTimer);
            networkStatsRefreshTimer = null;
            console.log("已停止网络统计数据自动刷新");
        }
    }
    
    function fetchNetworkStats(showLoading = true) {
        console.log('[FETCH START] fetchNetworkStats 函数被调用，showLoading:', showLoading);
        
        // 显示加载状态 (Show loading state) - 只在首次加载或手动刷新时显示
        if (showLoading) {
            var networkStatsElements = [btcPriceEl, networkDifficultyEl, networkHashrateEl, blockRewardEl];
            networkStatsElements.forEach(function(el) {
                if (el) el.innerHTML = '<small class="text-muted">Loading...</small>';
            });
        }
        
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/network_stats', true);
        
        // 设置15秒超时
        xhr.timeout = 15000;
        
        xhr.onload = function() {
            try {
                if (xhr.status === 200) {
                    // 确保响应不为空
                    if (!xhr.responseText || xhr.responseText.trim() === '') {
                        throw new Error('服务器返回空响应');
                    }
                    
                    var data = JSON.parse(xhr.responseText);
                    
                    if (data && data.success) {
                        // 调试信息
                        console.log('=== 网络统计更新调试 ===');
                        console.log('API返回数据:', data);
                        console.log('difficulty原始值:', data.difficulty);
                        console.log('networkDifficultyEl存在:', !!networkDifficultyEl);
                        console.log('networkDifficultyValueEl存在:', !!networkDifficultyValueEl);
                        if (typeof formatNumber === 'function') {
                            console.log('formatNumber(data.difficulty):', formatNumber(data.difficulty));
                        } else {
                            console.error('formatNumber函数未找到!');
                        }
                        
                        // 更新UI (Update UI)
                        if (btcPriceEl) btcPriceEl.textContent = formatCurrency(data.price, 2);
                        
                        // 更新difficulty元素 - 修复格式化参数
                        console.log('[DIFFICULTY FIX] 原始difficulty值:', data.difficulty);
                        var formattedDifficulty = formatNumber(data.difficulty, 2) + 'T';
                        console.log('[DIFFICULTY FIX] 格式化后的difficulty值:', formattedDifficulty);
                        
                        if (networkDifficultyEl) {
                            console.log('[DIFFICULTY FIX] 更新前元素内容:', networkDifficultyEl.textContent);
                            networkDifficultyEl.textContent = formattedDifficulty;
                            console.log('[DIFFICULTY FIX] 更新后元素内容:', networkDifficultyEl.textContent);
                            networkDifficultyEl.setAttribute('data-updated', 'fetchNetworkStats');
                        }
                        // 第二个difficulty元素已被移除（重复卡片）
                        
                        // 更新hashrate元素 - 修复格式化参数
                        var formattedHashrate = formatNumber(data.hashrate, 2) + ' EH/s';
                        if (networkHashrateEl) networkHashrateEl.textContent = formattedHashrate;
                        if (networkHashrateValueEl) networkHashrateValueEl.textContent = formattedHashrate;
                        if (blockRewardEl) {
                            console.log('区块奖励调试 - 原始值:', data.block_reward);
                            console.log('区块奖励调试 - 格式化值:', formatNumber(data.block_reward, 3));
                            blockRewardEl.textContent = formatNumber(data.block_reward, 3) + ' BTC';
                        }
                        
                        // 更新BTC价格输入框 (Update BTC price input)
                        if (useRealTimeCheckbox && useRealTimeCheckbox.checked && btcPriceInput) {
                            btcPriceInput.value = data.price.toFixed(2);
                            btcPriceInput.disabled = true;
                        }
                        
                        // 保存到localStorage作为备用 (Save to localStorage as backup)
                        localStorage.setItem('last_btc_price', data.price);
                        localStorage.setItem('last_network_difficulty', data.difficulty);
                        localStorage.setItem('last_network_hashrate', data.hashrate);
                        localStorage.setItem('last_block_reward', data.block_reward);
                        
                        // 在网络哈希率元素上添加闪烁效果来指示刷新
                        if (networkHashrateEl) {
                            networkHashrateEl.classList.add('refreshed-data');
                            setTimeout(function() {
                                networkHashrateEl.classList.remove('refreshed-data');
                            }, 1000);
                        }
                    } else {
                        useFallbackNetworkStats();
                        console.error('获取网络状态时服务器返回错误:', data && data.error ? data.error : null);
                    }
                } else {
                    throw new Error('服务器返回状态码: ' + xhr.status);
                }
            } catch (error) {
                console.error('获取网络状态失败:', error);
                useFallbackNetworkStats();
            }
        };
        
        xhr.onerror = function() {
            console.error('网络状态请求失败');
            useFallbackNetworkStats();
        };
        
        xhr.ontimeout = function() {
            console.error('网络状态请求超时');
            useFallbackNetworkStats();
        };
        
        xhr.send();
    }
    
    // 使用备用网络状态 (Use fallback network status)
    function useFallbackNetworkStats() {
        var lastBtcPrice = localStorage.getItem('last_btc_price');
        var lastDifficulty = localStorage.getItem('last_network_difficulty');
        var lastHashrate = localStorage.getItem('last_network_hashrate');
        var lastBlockReward = localStorage.getItem('last_block_reward');
        
        // 如果difficulty缓存值为0或很小，清除所有缓存并重试
        if (lastDifficulty && parseFloat(lastDifficulty) < 10) {
            console.log('检测到无效的难度缓存值:', lastDifficulty, '，清除缓存并重试');
            clearNetworkStatsCache();
            // 延迟2秒后重新获取
            setTimeout(function() {
                fetchNetworkStats(false);
            }, 2000);
            return;
        }
        
        if (lastBtcPrice && btcPriceEl) {
            btcPriceEl.textContent = formatCurrency(parseFloat(lastBtcPrice), 2);
            if (useRealTimeCheckbox && useRealTimeCheckbox.checked && btcPriceInput) {
                btcPriceInput.value = parseFloat(lastBtcPrice).toFixed(2);
                btcPriceInput.disabled = true;
            }
        } else if (btcPriceEl) {
            btcPriceEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
        }
        
        if (lastDifficulty && networkDifficultyEl) {
            networkDifficultyEl.textContent = formatNumber(parseFloat(lastDifficulty)) + 'T';
        } else if (networkDifficultyEl) {
            networkDifficultyEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
        }
        
        if (lastHashrate && networkHashrateEl) {
            networkHashrateEl.textContent = formatNumber(parseFloat(lastHashrate)) + ' EH/s';
        } else if (networkHashrateEl) {
            networkHashrateEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
        }
        
        if (lastBlockReward && blockRewardEl) {
            console.log('后备区块奖励数据 - 原始值:', lastBlockReward);
            console.log('后备区块奖励数据 - 格式化值:', formatNumber(parseFloat(lastBlockReward), 3));
            blockRewardEl.textContent = formatNumber(parseFloat(lastBlockReward), 3) + ' BTC';
        } else if (blockRewardEl) {
            blockRewardEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
        }
    }
    
    // 获取矿机列表 (Fetch miner list)
    function fetchMiners() {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/miners', true);
        
        // 设置10秒超时
        xhr.timeout = 10000;
        
        xhr.onload = function() {
            try {
                if (xhr.status === 200) {
                    // 确保响应不为空
                    if (!xhr.responseText || xhr.responseText.trim() === '') {
                        throw new Error('服务器返回空响应');
                    }
                    
                    var data = JSON.parse(xhr.responseText);
                    
                    if (data && data.success && data.miners) {
                        // 保存到localStorage (Save to localStorage)
                        localStorage.setItem('miners', JSON.stringify(data.miners));
                        
                        // 清空选项 (Clear options)
                        const currentLang = document.querySelector('meta[name="language"]')?.content || 'zh';
                        const selectText = currentLang === 'en' ? 'Select a miner model' : '选择矿机型号';
                        minerModelSelect.innerHTML = '<option value="">' + selectText + '</option>';
                        
                        // 添加矿机选项 (Add miner options)
                        data.miners.forEach(function(miner) {
                            var option = document.createElement('option');
                            option.value = miner.name;
                            option.textContent = miner.name + ' (' + miner.hashrate + ' TH/s, ' + miner.power_watt + 'W)';
                            minerModelSelect.appendChild(option);
                        });
                        
                        console.log('矿机列表加载成功:', data.miners.length);
                        
                        // 如果已选择了矿机型号，重新计算总算力和总功耗
                        if (minerModelSelect.value) {
                            updateMinerSpecs();
                        } else {
                            calculateTotalHashrateAndPower();
                        }
                    } else {
                        console.error('获取矿机数据失败:', data);
                        useCachedMiners();
                    }
                } else {
                    throw new Error('服务器返回状态码: ' + xhr.status);
                }
            } catch (error) {
                console.error('获取矿机列表失败:', error);
                useCachedMiners();
            }
        };
        
        xhr.onerror = function() {
            console.error('矿机列表请求失败');
            useCachedMiners();
        };
        
        xhr.ontimeout = function() {
            console.error('矿机列表请求超时');
            useCachedMiners();
        };
        
        xhr.send();
    }
    
    // 使用本地缓存的矿机列表
    function useCachedMiners() {
        var cachedMiners = localStorage.getItem('miners');
        
        if (cachedMiners) {
            try {
                var miners = JSON.parse(cachedMiners);
                
                // 清空选项
                const currentLang = document.querySelector('meta[name="language"]')?.content || 'zh';
                const selectText = currentLang === 'en' ? 'Select a miner model' : '选择矿机型号';
                minerModelSelect.innerHTML = '<option value="">' + selectText + '</option>';
                
                // 添加矿机选项
                miners.forEach(function(miner) {
                    var option = document.createElement('option');
                    option.value = miner.name;
                    option.textContent = miner.name + ' (' + miner.hashrate + ' TH/s, ' + miner.power_watt + 'W)';
                    minerModelSelect.appendChild(option);
                });
                
                console.log('使用缓存的矿机列表:', miners.length);
                
                // 如果已选择了矿机型号，重新计算总算力和总功耗
                if (minerModelSelect.value) {
                    updateMinerSpecs();
                } else {
                    calculateTotalHashrateAndPower();
                }
            } catch (error) {
                console.error('解析缓存的矿机列表失败:', error);
                showError('加载矿机列表失败。(Failed to load miner list.)');
            }
        } else {
            showError('无法加载矿机列表。(Unable to load miner list.)');
        }
    }
    
    // 显示计算结果 (Display calculation results)
    function displayResults(data) {
        // 检查数据有效性 - 更加灵活，适应不同角色的权限
        if (!data || !data.btc_mined) {
            showError('服务器返回的数据无效或不完整。(Invalid or incomplete data received from server.)');
            console.error('数据结构无效 - 缺少btc_mined字段:', data);
            return;
        }
        
        try {
            console.log('收到计算结果数据:', data);
            
            // 检查是否有optimization数据
            if (data.optimization) {
                console.log("矿机运行状态数据:", {
                    "运行中矿机数量": data.optimization.running_miner_count,
                    "停机矿机数量": data.optimization.shutdown_miner_count,
                    "最佳限电比例": data.optimization.optimal_curtailment + "%"
                });
            } else {
                console.warn("没有接收到矿机运行状态数据");
            }
            
            // 检查输入参数
            if (data.inputs) {
                console.log("输入参数:", {
                    "矿机型号": data.inputs.miner_model,
                    "矿机数量": data.inputs.miner_count,
                    "限电比例": data.inputs.curtailment + "%",
                    "电费成本": "$" + data.inputs.electricity_cost + "/kWh"
                });
            }
            
            // 显示结果卡片 (Show results card)
            if (resultsCard) resultsCard.style.display = 'block';
            
            // ===== 1. 基本BTC挖矿产出 =====
            updateBtcOutputDisplay(data);
            
            // ===== 2. 网络和挖矿信息 =====
            updateNetworkAndMiningInfo(data);
            
            // ===== 3. 矿场主(Host)数据 - 仅当有相关权限和数据时显示 =====
            // 如果数据中有host_profit或profit字段，说明用户有权限查看矿场主数据
            if (data.host_profit || data.profit) {
                updateHostData(data);
            }
            
            // ===== 4. 客户(Customer)数据 =====
            // 对于client_profit进行同样的检查
            if (data.client_profit) {
                updateCustomerData(data);
            }
            
            // 如果有估算提示，显示给用户
            if (data.estimation_note) {
                showError(data.estimation_note, 'warning');
            }
        } catch (error) {
            console.error('显示结果时出错:', error);
            showError('显示计算结果时发生错误。(Error displaying calculation results.)');
        }
    }
    
    // 更新BTC产出显示
    function updateBtcOutputDisplay(data) {
        // 算法1和算法2的BTC产出
        var btcMethod1CardEl = document.getElementById('btc-method1-daily-card');
        var btcMethod2CardEl = document.getElementById('btc-method2-daily-card');
        var dailyBtcTotalEl = document.getElementById('daily-btc-total');
        
        // 日产BTC总量
        if (dailyBtcTotalEl && data.btc_mined) {
            dailyBtcTotalEl.textContent = formatNumber(data.btc_mined.daily, 8);
        }
        
        // 算法1: 按算力占比
        if (btcMethod1CardEl && data.btc_mined && data.btc_mined.method1) {
            var method1Value = formatNumber(data.btc_mined.method1.daily, 8);
            btcMethod1CardEl.textContent = method1Value;
            // 月产出提示
            var monthlyOutput1 = data.btc_mined.method1.daily * 30.5;
            btcMethod1CardEl.title = '每月约: ' + formatNumber(monthlyOutput1, 8) + ' BTC';
        }
        
        // 算法2: 按难度公式
        if (btcMethod2CardEl && data.btc_mined && data.btc_mined.method2) {
            var method2Value = formatNumber(data.btc_mined.method2.daily, 8);
            btcMethod2CardEl.textContent = method2Value;
            btcMethod2CardEl.className = "text-info";
            // 月产出提示
            var monthlyOutput2 = data.btc_mined.method2.daily * 30.5;
            btcMethod2CardEl.title = '每月约: ' + formatNumber(monthlyOutput2, 8) + ' BTC';
        }
    }
    
    // 更新网络和挖矿信息
    function updateNetworkAndMiningInfo(data) {
        // 比特币网络信息
        var networkDifficultyEl = document.getElementById('network-difficulty-value');
        var networkHashrateEl = document.getElementById('network-hashrate-value');
        var currentBtcPriceEl = document.getElementById('current-btc-price-value');
        var blockRewardEl = document.getElementById('block-reward-value');
        
        // 挖矿场信息
        var siteTotalHashrateEl = document.getElementById('site-total-hashrate');
        var btcPerThDailyEl = document.getElementById('btc-per-th-daily');
        var optimalElectricityRateEl = document.getElementById('optimal-electricity-rate');
        
        // 更新比特币网络信息
        if (data.network_data) {
            if (networkDifficultyEl) {
                // 检查元素是否已被fetchNetworkStats更新过
                var lastUpdated = networkDifficultyEl.getAttribute('data-updated');
                console.log('updateNetworkAndMiningInfo - difficulty元素上次更新者:', lastUpdated);
                
                if (lastUpdated === 'fetchNetworkStats') {
                    console.log('跳过difficulty元素更新，已被fetchNetworkStats更新');
                } else {
                    var difficultyValue = data.network_data.network_difficulty;
                    console.log('updateNetworkAndMiningInfo difficulty原始值:', difficultyValue);
                    
                    // 如果difficulty大于1000，说明是原始值，需要转换
                    if (difficultyValue > 1000) {
                        difficultyValue = difficultyValue / 1e12; // 转换为T单位
                    }
                    console.log('updateNetworkAndMiningInfo difficulty转换后:', difficultyValue);
                    networkDifficultyEl.textContent = formatNumber(difficultyValue, 2) + ' T';
                    networkDifficultyEl.setAttribute('data-updated', 'updateNetworkAndMiningInfo');
                }
            }
            if (networkHashrateEl) {
                networkHashrateEl.textContent = formatNumber(data.network_data.network_hashrate, 2) + ' EH/s';
            }
            if (currentBtcPriceEl) {
                currentBtcPriceEl.textContent = formatCurrency(data.network_data.btc_price, 2);
            }
            if (blockRewardEl) {
                blockRewardEl.textContent = formatNumber(data.network_data.block_reward, 3) + ' BTC';
            }
        } else {
            // 如果没有network_data，尝试从网络统计API获取实时数据
            fetchNetworkStatsForDetails();
        }
        
        // 更新挖矿场信息
        if (siteTotalHashrateEl && data.inputs) {
            siteTotalHashrateEl.textContent = formatNumber(data.inputs.hashrate, 2) + ' TH/s';
        }
        if (btcPerThDailyEl && data.btc_mined) {
            btcPerThDailyEl.textContent = formatNumber(data.btc_mined.per_th_daily, 8);
        }
        if (optimalElectricityRateEl && data.break_even) {
            optimalElectricityRateEl.textContent = '$' + formatNumber(data.break_even.electricity_cost, 4) + '/kWh';
        }
        
        // 其他挖矿信息
        var minerCountEl = document.getElementById('miner-count-result');
        var runningMinersEl = document.getElementById('running-miners');
        var shutdownMinersEl = document.getElementById('shutdown-miners');
        
        if (minerCountEl && data.inputs) {
            minerCountEl.textContent = formatNumber(data.inputs.miner_count, 0);
        }
        
        // 显示运行中和停机的矿机数量
        if (runningMinersEl && data.optimization) {
            console.log("正在更新运行中矿机数量:", data.optimization.running_miner_count);
            runningMinersEl.textContent = formatNumber(data.optimization.running_miner_count, 0);
        } else {
            console.log("无法更新运行中矿机数量:", {
                "runningMinersEl存在": !!runningMinersEl,
                "data.optimization存在": !!data.optimization,
                "data包含内容": JSON.stringify(data).substring(0, 100) + "..."
            });
        }
        
        if (shutdownMinersEl && data.optimization) {
            console.log("正在更新停机矿机数量:", data.optimization.shutdown_miner_count);
            shutdownMinersEl.textContent = formatNumber(data.optimization.shutdown_miner_count, 0);
        } else {
            console.log("无法更新停机矿机数量:", {
                "shutdownMinersEl存在": !!shutdownMinersEl,
                "data.optimization存在": !!data.optimization,
                "data包含内容": JSON.stringify(data).substring(0, 100) + "..."
            });
        }
    }
    
    // 更新矿场主数据
    function updateHostData(data) {
        console.log('[DEBUG] updateHostData called with data:', {
            has_host_profit: !!data.host_profit,
            has_profit: !!data.profit,
            host_profit_monthly: data.host_profit?.monthly,
            profit_monthly: data.profit?.monthly
        });
        
        // 检查用户角色权限 - 从页面元数据中获取
        var userRole = document.querySelector('meta[name="user-role"]')?.getAttribute('content');
        var allowedRoles = ['owner', 'admin', 'mining_site'];
        var hasAccess = allowedRoles.includes(userRole);
        
        console.log('[DEBUG] User role check:', {user_role: userRole, has_access: hasAccess});
        
        // 如果用户没有权限，直接返回，不更新矿场主数据
        if (!hasAccess) {
            console.log("用户角色没有查看矿场主数据的权限");
            return;
        }
        
        // 主要指标
        var hostProfitCardEl = document.getElementById('host-profit-card');
        
        // 收入和支出项
        var hostMonthlyProfitEl = document.getElementById('host-monthly-profit');
        var hostMonthlyProfitDisplayEl = document.getElementById('host-monthly-profit-display');
        var hostTotalIncomeEl = document.getElementById('host-total-income');
        var siteRevenueEl = document.getElementById('site-total-revenue');
        var hostSelfProfitEl = document.getElementById('host-self-profit');
        
        // 主机利润详情
        var hostDailyProfitEl = document.getElementById('host-daily-profit');
        var hostYearlyProfitEl = document.getElementById('host-yearly-profit');
        
        // 矿场主电费和成本
        var hostMonthlyCostEl = document.getElementById('host-monthly-cost');
        var operationCostEl = document.getElementById('operation-cost');
        var totalExpensesEl = document.getElementById('host-total-expenses');
        
        // 矿场主盈亏平衡点
        var hostBreakEvenElectricityEl = document.getElementById('host-break-even-electricity');
        var hostBreakEvenBtcEl = document.getElementById('host-break-even-btc');
        var optimalCurtailmentEl = document.getElementById('optimal-curtailment');
        
        // 使用API返回的Host profit数据
        if (data.host_profit && data.host_profit.monthly) {
            // 使用API计算的Host月度利润
            var hostElectricProfit = data.host_profit.monthly;
            
            // 更新矿场主电费差收益显示
            if (hostMonthlyProfitEl) {
                hostMonthlyProfitEl.textContent = formatCurrency(hostElectricProfit);
            }
            if (hostMonthlyProfitDisplayEl) {
                hostMonthlyProfitDisplayEl.textContent = formatCurrency(hostElectricProfit);
            }
        } else if (data.client_electricity_cost && data.electricity_cost) {
            // 如果没有host_profit字段，回退到电费差计算 (向后兼容)
            var hostElectricProfit = data.client_electricity_cost.monthly - data.electricity_cost.monthly;
            
            // 更新矿场主电费差收益显示
            if (hostMonthlyProfitEl) {
                hostMonthlyProfitEl.textContent = formatCurrency(hostElectricProfit);
            }
            if (hostMonthlyProfitDisplayEl) {
                hostMonthlyProfitDisplayEl.textContent = formatCurrency(hostElectricProfit);
            }
            
            // 获取运营收益和运维成本
            var operationCostValue = data.maintenance_fee && data.maintenance_fee.monthly ? data.maintenance_fee.monthly : 0;
            var hostSelfProfit = 0; // 这里假设为0，根据需要调整
            
            // 更新运营收益
            if (hostSelfProfitEl) {
                hostSelfProfitEl.textContent = formatCurrency(hostSelfProfit);
            }
            
            // 电费差 + 运营收益 = 总站点收入
            var siteTotalRevenue = hostElectricProfit + hostSelfProfit;
            if (siteRevenueEl) {
                siteRevenueEl.textContent = formatCurrency(siteTotalRevenue);
            }
            
            // 总收入 = 总站点收入
            if (hostTotalIncomeEl) {
                hostTotalIncomeEl.textContent = formatCurrency(siteTotalRevenue);
            }
            
            // 更新主卡片 - 净利润 = 电费差收益 - 运维成本
            var hostMonthlyNetProfit = hostElectricProfit - operationCostValue;
            if (hostProfitCardEl) {
                hostProfitCardEl.textContent = formatCurrency(hostMonthlyNetProfit);
            }
            
            // 更新矿场主利润详情
            if (hostDailyProfitEl) {
                var dailyProfit = data.host_profit && data.host_profit.daily ? data.host_profit.daily : hostElectricProfit / 30.5;
                hostDailyProfitEl.textContent = formatCurrency(dailyProfit);
            }
            
            if (hostYearlyProfitEl) {
                var yearlyProfit = data.host_profit && data.host_profit.yearly ? data.host_profit.yearly : hostElectricProfit * 12;
                hostYearlyProfitEl.textContent = formatCurrency(yearlyProfit);
            }
            
            // 更新矿场主成本
            if (hostMonthlyCostEl && data.electricity_cost) {
                hostMonthlyCostEl.textContent = formatCurrency(data.electricity_cost.monthly);
            }
            
            if (operationCostEl && data.maintenance_fee) {
                operationCostEl.textContent = formatCurrency(data.maintenance_fee.monthly);
            }
            
            if (totalExpensesEl && data.electricity_cost && data.maintenance_fee) {
                var totalExpenses = data.electricity_cost.monthly + data.maintenance_fee.monthly;
                totalExpensesEl.textContent = formatCurrency(totalExpenses);
            }
        }
        
        // 盈亏平衡点
        if (hostBreakEvenElectricityEl && data.break_even) {
            hostBreakEvenElectricityEl.textContent = '$' + formatNumber(data.break_even.electricity_cost, 4) + '/kWh';
        }
        
        if (hostBreakEvenBtcEl && data.break_even) {
            hostBreakEvenBtcEl.textContent = formatCurrency(data.break_even.btc_price, 2);
        }
        
        if (optimalCurtailmentEl && data.optimization) {
            optimalCurtailmentEl.textContent = formatNumber(data.optimization.optimal_curtailment, 2) + '%';
        }
    }
    
    // 更新客户数据
    function updateCustomerData(data) {
        // 主要指标
        var clientProfitCardEl = document.getElementById('client-profit-card');
        
        // 收入和支出项
        var clientMonthlyBtcEl = document.getElementById('client-monthly-btc');
        var clientMonthlyBtcRevenueEl = document.getElementById('client-monthly-btc-revenue');
        var clientTotalIncomeEl = document.getElementById('client-total-income');
        
        // 客户电费和成本
        var clientMonthlyElectricityEl = document.getElementById('client-monthly-electricity');
        var clientTotalExpensesEl = document.getElementById('client-total-expenses');
        
        // 客户利润详情
        var clientMonthlyProfitEl = document.getElementById('client-monthly-profit');
        var clientDailyProfitEl = document.getElementById('client-daily-profit');
        var clientYearlyProfitEl = document.getElementById('client-yearly-profit');
        
        // 客户盈亏平衡点
        var clientBreakEvenElectricityEl = document.getElementById('client-break-even-electricity');
        var clientBreakEvenBtcEl = document.getElementById('client-break-even-btc');
        
        // 客户矿机状态
        var clientMinerCountEl = document.getElementById('client-miner-count');
        var clientRunningMinersEl = document.getElementById('client-running-miners');
        var clientShutdownMinersEl = document.getElementById('client-shutdown-miners');
        
        // 客户BTC产出和收入
        var monthlyBtcOutput = data.btc_mined && data.btc_mined.monthly ? data.btc_mined.monthly : 0;
        var monthlyBtcRevenue = 0;
        
        if (data.network_data && data.network_data.btc_price) {
            monthlyBtcRevenue = monthlyBtcOutput * data.network_data.btc_price;
        }
        
        console.log('月度BTC产出:', monthlyBtcOutput, 'BTC价格:', 
                    data.network_data ? data.network_data.btc_price : 'N/A', 
                    '计算得到月度收入:', monthlyBtcRevenue);
        
        // 更新客户BTC产出
        if (clientMonthlyBtcEl) {
            clientMonthlyBtcEl.textContent = formatNumber(monthlyBtcOutput, 8);
        }
        
        // 更新客户BTC收入
        if (clientMonthlyBtcRevenueEl) {
            clientMonthlyBtcRevenueEl.textContent = formatCurrency(monthlyBtcRevenue);
        }
        
        // 更新客户总收入 - 这是矿机挖出的BTC产生的全部收入
        if (clientTotalIncomeEl) {
            clientTotalIncomeEl.textContent = formatCurrency(monthlyBtcRevenue);
            console.log('已更新客户总收入:', monthlyBtcRevenue);
        } else {
            console.error('无法找到客户总收入元素ID:client-total-income');
        }
        
        // 客户电费和总支出
        if (clientMonthlyElectricityEl && data.client_electricity_cost) {
            clientMonthlyElectricityEl.textContent = formatCurrency(data.client_electricity_cost.monthly);
        }
        
        // 显示pool fee
        var clientPoolFeeEl = document.getElementById('client-pool-fee');
        console.log('Pool fee 数据调试:', {
            pool_fee_exists: !!data.pool_fee,
            pool_fee_data: data.pool_fee,
            monthly_impact: data.pool_fee ? data.pool_fee.monthly_impact : 'N/A'
        });
        if (clientPoolFeeEl && data.pool_fee) {
            clientPoolFeeEl.textContent = formatCurrency(data.pool_fee.monthly_impact);
            console.log('Pool fee 已更新为:', data.pool_fee.monthly_impact);
        } else {
            console.log('Pool fee 更新失败:', {
                element_exists: !!clientPoolFeeEl,
                data_exists: !!data.pool_fee
            });
            // 如果没有pool_fee数据，显示为$0.00
            if (clientPoolFeeEl) {
                clientPoolFeeEl.textContent = '$0.00';
            }
        }
        
        // 计算并显示总费用 (电费 + pool fee)
        if (clientTotalExpensesEl && data.client_electricity_cost && data.pool_fee) {
            var totalExpenses = data.client_electricity_cost.monthly + data.pool_fee.monthly_impact;
            clientTotalExpensesEl.textContent = formatCurrency(totalExpenses);
        } else if (clientTotalExpensesEl && data.client_electricity_cost) {
            clientTotalExpensesEl.textContent = formatCurrency(data.client_electricity_cost.monthly);
        }
        
        // 客户收益信息
        if (data.client_profit) {
            var clientMonthlyProfitValue = data.client_profit.monthly;
            
            // 更新客户月收益
            if (clientMonthlyProfitEl) {
                clientMonthlyProfitEl.textContent = formatCurrency(clientMonthlyProfitValue);
            }
            
            // 更新主卡片
            if (clientProfitCardEl) {
                clientProfitCardEl.textContent = formatCurrency(clientMonthlyProfitValue);
            }
            
            // 更新客户日收益和年收益
            if (clientDailyProfitEl && data.client_profit.daily) {
                clientDailyProfitEl.textContent = formatCurrency(data.client_profit.daily);
            }
            
            if (clientYearlyProfitEl && data.client_profit.yearly) {
                clientYearlyProfitEl.textContent = formatCurrency(data.client_profit.yearly);
            }
        }
        
        // 客户盈亏平衡点
        if (clientBreakEvenElectricityEl && data.break_even) {
            clientBreakEvenElectricityEl.textContent = '$' + formatNumber(data.break_even.electricity_cost, 4) + '/kWh';
        }
        
        if (clientBreakEvenBtcEl && data.break_even) {
            clientBreakEvenBtcEl.textContent = formatCurrency(data.break_even.btc_price, 2);
        }
        
        // 更新客户矿机数量信息
        if (clientMinerCountEl && data.inputs && data.inputs.miner_count) {
            clientMinerCountEl.textContent = formatNumber(data.inputs.miner_count, 0);
        }
        
        // 更新客户运行中和停机矿机数量
        if (clientRunningMinersEl && data.optimization && data.optimization.running_miner_count !== undefined) {
            console.log("正在更新客户运行中矿机数量:", data.optimization.running_miner_count);
            clientRunningMinersEl.textContent = formatNumber(data.optimization.running_miner_count, 0);
        } else {
            console.log("无法更新客户运行中矿机数量:", {
                "clientRunningMinersEl存在": !!clientRunningMinersEl,
                "data.optimization存在": !!data.optimization,
                "optimization数据": data.optimization ? JSON.stringify(data.optimization).substring(0, 100) : "无数据"
            });
        }
        
        if (clientShutdownMinersEl && data.optimization && data.optimization.shutdown_miner_count !== undefined) {
            console.log("正在更新客户停机矿机数量:", data.optimization.shutdown_miner_count);
            clientShutdownMinersEl.textContent = formatNumber(data.optimization.shutdown_miner_count, 0);
        } else {
            console.log("无法更新客户停机矿机数量:", {
                "clientShutdownMinersEl存在": !!clientShutdownMinersEl,
                "data.optimization存在": !!data.optimization,
                "optimization数据": data.optimization ? JSON.stringify(data.optimization).substring(0, 100) : "无数据"
            });
        }
    }
    
    // 生成利润热力图 (Generate profit heatmap)
    function generateProfitChart(minerModel, minerCount, clientElectricityCost) {
        // 获取图表容器 (Get chart container)
        var chartContainer = document.getElementById('chart-container');
        if (!chartContainer) {
            console.error('找不到图表容器 (Chart container not found)');
            return;
        }
        
        // 显示加载状态 (Show loading state)
        chartContainer.innerHTML = '<div class="text-center p-5"><div class="spinner-border text-primary"></div><p class="mt-3">正在生成热力图...<br>Generating chart...</p></div>';
        
        // 准备请求参数 (Prepare request parameters)
        var params = 'miner_model=' + encodeURIComponent(minerModel) + 
                     '&miner_count=' + encodeURIComponent(minerCount) + 
                     '&client_electricity_cost=' + encodeURIComponent(clientElectricityCost);
        
        // 发送请求 (Send request)
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/profit_chart_data', true);
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        
        xhr.onload = function() {
            try {
                if (xhr.status === 200) {
                    var chartData = JSON.parse(xhr.responseText);
                    
                    if (chartData.success && chartData.profit_data) {
                        // 准备Canvas (Prepare canvas)
                        chartContainer.innerHTML = '<canvas id="heatmap-canvas" width="100%" height="400"></canvas>';
                        var canvas = document.getElementById('heatmap-canvas');
                        
                        // 创建散点图数据 (Create scatter data)
                        var scatterData = [];
                        chartData.profit_data.forEach(function(item) {
                            if (item && typeof item.electricity_cost === 'number' && 
                                typeof item.btc_price === 'number' && 
                                typeof item.monthly_profit === 'number') {
                                
                                scatterData.push({
                                    x: item.electricity_cost,
                                    y: item.btc_price,
                                    profit: item.monthly_profit
                                });
                            }
                        });
                        
                        // 如果没有数据点 (If no data points)
                        if (scatterData.length === 0) {
                            chartContainer.innerHTML = '<div class="alert alert-warning text-center">没有有效的数据点来生成热力图。(No valid data points to generate heatmap.)</div>';
                            return;
                        }
                        
                        // 创建图表 (Create chart)
                        new Chart(canvas, {
                            type: 'scatter',
                            data: {
                                datasets: [{
                                    label: '月利润 (Monthly Profit)',
                                    data: scatterData,
                                    backgroundColor: function(context) {
                                        if (!context.raw) return 'rgba(128, 128, 128, 0.7)';
                                        
                                        var profit = context.raw.profit;
                                        if (profit >= 0) {
                                            return 'rgba(40, 167, 69, 0.7)';  // 绿色 (Green - profit)
                                        } else {
                                            return 'rgba(220, 53, 69, 0.7)';  // 红色 (Red - loss)
                                        }
                                    },
                                    pointRadius: 10,
                                    pointHoverRadius: 15
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {
                                    x: {
                                        title: {
                                            display: true,
                                            text: '电价 ($/kWh)'
                                        }
                                    },
                                    y: {
                                        title: {
                                            display: true,
                                            text: '比特币价格 ($)'
                                        }
                                    }
                                },
                                plugins: {
                                    tooltip: {
                                        callbacks: {
                                            label: function(context) {
                                                var profit = context.raw.profit;
                                                return '月利润: $' + profit.toFixed(2);
                                            }
                                        }
                                    },
                                    title: {
                                        display: true,
                                        text: (parseFloat(clientElectricityCost) > 0) ? 
                                            '客户收益热力图 / Customer Profit Chart' : 
                                            '矿场主收益热力图 / Host Profit Chart'
                                    }
                                }
                            }
                        });
                    } else {
                        chartContainer.innerHTML = '';  // Clear container first
                        const warningDiv = document.createElement('div');
                        warningDiv.className = 'alert alert-warning text-center';
                        warningDiv.textContent = '无法生成热力图数据。(Could not generate heatmap data.)';
                        chartContainer.appendChild(warningDiv);
                    }
                } else {
                    throw new Error('服务器返回状态码: ' + xhr.status);
                }
            } catch (error) {
                console.error('生成热力图失败:', error);
                chartContainer.innerHTML = '';  // Clear container first
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-danger text-center';
                errorDiv.textContent = '生成热力图时出错。(Error generating heatmap.)';
                chartContainer.appendChild(errorDiv);
            }
        };
        
        xhr.onerror = function() {
            console.error('热力图请求失败');
            chartContainer.innerHTML = '';  // Clear container first
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger text-center';
            errorDiv.textContent = '网络错误，请重试。(Network error, please try again.)';
            chartContainer.appendChild(errorDiv);
        };
        
        xhr.send(params);
    }
    
    // 工具函数 (Utility functions)
    
    // 设置加载状态 (Set loading state)
    function setLoadingState(isLoading) {
        var submitButton = calculatorForm.querySelector('button[type="submit"]');
        if (submitButton) {
            if (isLoading) {
                submitButton.disabled = true;
                submitButton.innerHTML = '';  // Clear content first
                const spinner = document.createElement('span');
                spinner.className = 'spinner-border spinner-border-sm';
                spinner.setAttribute('role', 'status');
                spinner.setAttribute('aria-hidden', 'true');
                submitButton.appendChild(spinner);
                submitButton.appendChild(document.createTextNode(' 计算中... / Calculating...'));
            } else {
                submitButton.disabled = false;
                submitButton.textContent = 'Calculate Profitability';
            }
        }
    }
    
    // 显示错误信息 (Show error message)
    function showError(message) {
        var errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        
        // 安全地设置错误消息文本，防止XSS攻击
        var messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        errorDiv.appendChild(messageSpan);
        
        // 添加关闭按钮
        var closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
        errorDiv.appendChild(closeButton);
        
        var container = document.querySelector('.container');
        if (container) {
            container.insertBefore(errorDiv, container.firstChild);
            
            // 5秒后自动消失 (Auto-hide after 5 seconds)
            setTimeout(function() {
                errorDiv.classList.remove('show');
                setTimeout(function() {
                    if (errorDiv.parentNode) {
                        errorDiv.parentNode.removeChild(errorDiv);
                    }
                }, 150);
            }, 5000);
        }
    }
    
    // formatCurrency和formatNumber函数已在页面顶部定义
    
    // 独立的计算初始化函数 - 优化加载速度
    function initializeCalculations() {
        var totalHashrateInput = getCachedElement('total-hashrate');
        var totalPowerInput = getCachedElement('total-power');
        
        if (minerCountInput && hashrateInput && powerConsumptionInput) {
            var minerCount = parseInt(minerCountInput.value) || 0;
            var hashrate = parseFloat(hashrateInput.value) || 0;
            var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
            
            if (minerCount > 0 && hashrate > 0 && powerWatt > 0) {
                var totalHashrate = minerCount * hashrate;
                var totalPower = minerCount * powerWatt;
                
                if (totalHashrateInput) {
                    totalHashrateInput.value = totalHashrate.toFixed(0);
                }
                if (totalPowerInput) {
                    totalPowerInput.value = totalPower.toFixed(0);
                }
            }
        }
        
        if (typeof calculateTotalHashrateAndPower === 'function') {
            calculateTotalHashrateAndPower();
        }
    }
    
    // 使用缓存的元素获取函数 - 提升性能
    function getCachedElement(id) {
        return window.getCachedElement ? window.getCachedElement(id) : document.getElementById(id);
    }
    
    // 为详细信息表格获取网络统计数据
    function fetchNetworkStatsForDetails() {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/network_stats', true);
        xhr.onload = function() {
            if (xhr.status === 200) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    if (data && data.success) {
                        // 更新详细信息表格中的网络数据
                        var networkDifficultyEl = document.getElementById('network-difficulty-value');
                        var networkHashrateEl = document.getElementById('network-hashrate-value');
                        var currentBtcPriceEl = document.getElementById('current-btc-price-value');
                        var blockRewardEl = document.getElementById('block-reward-value');
                        
                        if (networkDifficultyEl) {
                            networkDifficultyEl.textContent = formatNumber(data.difficulty, 2) + ' T';
                        }
                        if (networkHashrateEl) {
                            networkHashrateEl.textContent = formatNumber(data.hashrate, 2) + ' EH/s';
                        }
                        if (currentBtcPriceEl) {
                            currentBtcPriceEl.textContent = formatCurrency(data.price, 2);
                        }
                        if (blockRewardEl) {
                            blockRewardEl.textContent = formatNumber(data.block_reward, 3) + ' BTC';
                        }
                    }
                } catch (error) {
                    console.error('获取详细网络统计失败:', error);
                }
            }
        };
        xhr.send();
    }

    // 创建缺失的updateNetworkStatsDisplay函数
    function updateNetworkStatsDisplay(data) {
        console.log('更新网络统计显示 - 完整数据结构:', data);
        
        if (data) {
            if (btcPriceEl && data.btc_price) {
                btcPriceEl.textContent = formatCurrency(data.btc_price, 2);
            }
            if (networkDifficultyEl && data.network_difficulty) {
                networkDifficultyEl.textContent = formatNumber(data.network_difficulty) + 'T';
            }
            if (networkHashrateEl && data.network_hashrate) {
                networkHashrateEl.textContent = formatNumber(data.network_hashrate) + ' EH/s';
            }
            
            // 检查区块奖励字段的多种可能性
            var blockReward = data.block_reward || data.blockReward || null;
            console.log('区块奖励字段检查 - block_reward:', data.block_reward);
            console.log('区块奖励字段检查 - blockReward:', data.blockReward);
            console.log('区块奖励字段检查 - 最终使用值:', blockReward);
            
            if (blockRewardEl) {
                if (blockReward) {
                    console.log('缓存区块奖励调试 - 原始值:', blockReward);
                    console.log('缓存区块奖励调试 - 格式化值:', formatNumber(blockReward, 3));
                    blockRewardEl.textContent = formatNumber(blockReward, 3) + ' BTC';
                } else {
                    console.log('警告：缓存数据中没有区块奖励字段！');
                    console.log('立即获取实时网络统计数据...');
                    // 如果缓存数据没有区块奖励，立即获取实时数据
                    fetchNetworkStats();
                    // 同时设置临时显示
                    blockRewardEl.innerHTML = '<small class="text-warning">加载中...</small>';
                }
            }
        }
    }

    // 导出关键函数到全局作用域，便于优化器使用
    window.fetchNetworkStats = fetchNetworkStats;
    window.fetchMiners = fetchMiners;
    window.fetchNetworkStatsForDetails = fetchNetworkStatsForDetails;
    window.updateNetworkStatsDisplay = updateNetworkStatsDisplay;
    window.initializeCharts = function() {
        // 图表初始化逻辑可以放在这里
        console.log("图表初始化完成");
    };
    
    // 调用初始化函数 (Call init function)
    init();
});