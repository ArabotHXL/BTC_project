// Bitcoin Mining Calculator - Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 元素引用 (Element references)
    var btcPriceEl = document.getElementById('btc-price');
    var networkDifficultyEl = document.getElementById('network-difficulty');
    var networkHashrateEl = document.getElementById('network-hashrate');
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
    
    var resultsCard = document.getElementById('results-card');
    var chartCard = document.getElementById('chart-card');
    
    // 初始化 (Initialization)
    function init() {
        // 加载网络数据 (Load network data)
        fetchNetworkStats();
        
        // 加载矿机型号列表 (Load miner models)
        fetchMiners();
        
        // 事件绑定 (Event bindings)
        if (calculatorForm) {
            calculatorForm.addEventListener('submit', handleCalculateSubmit);
        }
        
        if (minerModelSelect) {
            minerModelSelect.addEventListener('change', updateMinerSpecs);
        }
        
        if (sitePowerMwInput) {
            sitePowerMwInput.addEventListener('input', updateMinerCount);
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
        var sitePowerMw = parseFloat(sitePowerMwInput.value) || 0;
        var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
        
        if (sitePowerMw > 0 && powerWatt > 0) {
            // 计算最大矿机数量 (Calculate maximum miner count)
            // Formula: (site_power_mw * 1000) / (power_watt / 1000)
            var maxMiners = Math.floor((sitePowerMw * 1000000) / powerWatt);
            minerCountInput.value = maxMiners;
        }
    }
    
    // 处理计算表单提交 (Handle calculation form submission)
    function handleCalculateSubmit(event) {
        event.preventDefault();
        
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
        
        // 请求计算 (Request calculation)
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/calculate', true);
        
        xhr.onload = function() {
            try {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    
                    if (data.success) {
                        // 显示结果 (Display results)
                        displayResults(data);
                    } else {
                        showError(data.error || '计算过程中发生错误。(An error occurred during calculation.)');
                        console.error('服务器返回错误:', data.error);
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
        
        xhr.send(formData);
    }
    
    // 获取网络状态 (Fetch network status)
    function fetchNetworkStats() {
        // 显示加载状态 (Show loading state)
        var networkStatsElements = [btcPriceEl, networkDifficultyEl, networkHashrateEl, blockRewardEl];
        networkStatsElements.forEach(function(el) {
            if (el) el.innerHTML = '<small class="text-muted">Loading...</small>';
        });
        
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/network_stats', true);
        
        xhr.onload = function() {
            try {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    
                    if (data.success) {
                        // 更新UI (Update UI)
                        if (btcPriceEl) btcPriceEl.textContent = formatCurrency(data.price);
                        if (networkDifficultyEl) networkDifficultyEl.textContent = formatNumber(data.difficulty) + 'T';
                        if (networkHashrateEl) networkHashrateEl.textContent = formatNumber(data.hashrate) + ' EH/s';
                        if (blockRewardEl) blockRewardEl.textContent = formatNumber(data.block_reward) + ' BTC';
                        
                        // 更新BTC价格输入框 (Update BTC price input)
                        if (useRealTimeCheckbox && useRealTimeCheckbox.checked) {
                            btcPriceInput.value = data.price.toFixed(2);
                            btcPriceInput.disabled = true;
                        }
                        
                        // 保存到localStorage作为备用 (Save to localStorage as backup)
                        localStorage.setItem('last_btc_price', data.price);
                        localStorage.setItem('last_network_difficulty', data.difficulty);
                        localStorage.setItem('last_network_hashrate', data.hashrate);
                        localStorage.setItem('last_block_reward', data.block_reward);
                    } else {
                        useFallbackNetworkStats();
                        console.error('获取网络状态时服务器返回错误:', data.error);
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
        
        xhr.send();
    }
    
    // 使用备用网络状态 (Use fallback network status)
    function useFallbackNetworkStats() {
        var lastBtcPrice = localStorage.getItem('last_btc_price');
        var lastDifficulty = localStorage.getItem('last_network_difficulty');
        var lastHashrate = localStorage.getItem('last_network_hashrate');
        var lastBlockReward = localStorage.getItem('last_block_reward');
        
        if (lastBtcPrice && btcPriceEl) {
            btcPriceEl.textContent = formatCurrency(parseFloat(lastBtcPrice));
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
            blockRewardEl.textContent = formatNumber(parseFloat(lastBlockReward), 4) + ' BTC';
        } else if (blockRewardEl) {
            blockRewardEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
        }
    }
    
    // 获取矿机列表 (Fetch miner list)
    function fetchMiners() {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/miners', true);
        
        xhr.onload = function() {
            try {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    
                    if (data.success && data.miners) {
                        // 保存到localStorage (Save to localStorage)
                        localStorage.setItem('miners', JSON.stringify(data.miners));
                        
                        // 清空选项 (Clear options)
                        minerModelSelect.innerHTML = '<option value="">选择矿机型号 (Select a miner model)</option>';
                        
                        // 添加矿机选项 (Add miner options)
                        data.miners.forEach(function(miner) {
                            var option = document.createElement('option');
                            option.value = miner.name;
                            option.textContent = miner.name + ' (' + miner.hashrate + ' TH/s, ' + miner.power_watt + 'W)';
                            minerModelSelect.appendChild(option);
                        });
                        
                        console.log('矿机列表加载成功:', data.miners.length);
                    } else {
                        console.error('获取矿机数据失败:', data);
                    }
                } else {
                    throw new Error('服务器返回状态码: ' + xhr.status);
                }
            } catch (error) {
                console.error('获取矿机列表失败:', error);
            }
        };
        
        xhr.onerror = function() {
            console.error('矿机列表请求失败');
        };
        
        xhr.send();
    }
    
    // 显示计算结果 (Display calculation results)
    function displayResults(data) {
        if (!data || !data.btc_mined) {
            showError('服务器返回的数据无效。(Invalid data received from server.)');
            console.error('数据结构无效:', data);
            return;
        }
        
        try {
            console.log('收到计算结果数据:', data);
            
            // 显示结果卡片 (Show results card)
            if (resultsCard) resultsCard.style.display = 'block';
            
            // ===== 1. 基本BTC挖矿产出 =====
            updateBtcOutputDisplay(data);
            
            // ===== 2. 网络和挖矿信息 =====
            updateNetworkAndMiningInfo(data);
            
            // ===== 3. 矿场主(Host)数据 =====
            updateHostData(data);
            
            // ===== 4. 客户(Customer)数据 =====
            updateCustomerData(data);
            
        } catch (error) {
            console.error('显示结果时出错:', error);
            showError('显示计算结果时发生错误。(Error displaying calculation results.)');
        }
    }
    
    // 更新BTC产出显示
    function updateBtcOutputDisplay(data) {
        // 算法1和算法2的BTC产出 - 详细表格中的元素
        var btcMethod1CardEl = document.getElementById('btc-method1-daily');
        var btcMethod2CardEl = document.getElementById('btc-method2-daily');
        var dailyBtcTotalEl = document.getElementById('daily-btc-value');
        
        // 主卡片中的元素
        var btcMethod1CardMainEl = document.getElementById('btc-method1-daily-card');
        var btcMethod2CardMainEl = document.getElementById('btc-method2-daily-card');
        
        console.log("更新BTC产出显示:", data.btc_mined);
        
        // 日产BTC总量
        if (dailyBtcTotalEl && data.btc_mined) {
            dailyBtcTotalEl.textContent = formatNumber(data.btc_mined.daily, 8);
            console.log("已更新日产BTC总量:", data.btc_mined.daily);
        } else {
            console.error("无法更新日产BTC总量", dailyBtcTotalEl, data.btc_mined);
        }
        
        // 算法1: 按算力占比 - 同时更新详情和主卡片
        if (data.btc_mined && data.btc_mined.method1) {
            var method1Value = formatNumber(data.btc_mined.method1.daily, 8);
            var monthlyOutput1 = data.btc_mined.method1.daily * 30.5;
            var tooltipText = '每月约: ' + formatNumber(monthlyOutput1, 8) + ' BTC';
            
            // 更新详情表格中的元素
            if (btcMethod1CardEl) {
                btcMethod1CardEl.textContent = method1Value;
                btcMethod1CardEl.title = tooltipText;
                console.log("已更新详情表格算法1产出:", method1Value);
            }
            
            // 更新主卡片中的元素
            if (btcMethod1CardMainEl) {
                btcMethod1CardMainEl.textContent = method1Value;
                btcMethod1CardMainEl.title = tooltipText;
                console.log("已更新主卡片算法1产出:", method1Value);
            }
        } else {
            console.error("无法更新算法1产出，数据缺失", data.btc_mined);
        }
        
        // 算法2: 按难度公式 - 同时更新详情和主卡片
        if (data.btc_mined && data.btc_mined.method2) {
            var method2Value = formatNumber(data.btc_mined.method2.daily, 8);
            var monthlyOutput2 = data.btc_mined.method2.daily * 30.5;
            var tooltipText = '每月约: ' + formatNumber(monthlyOutput2, 8) + ' BTC';
            
            // 更新详情表格中的元素
            if (btcMethod2CardEl) {
                btcMethod2CardEl.textContent = method2Value;
                btcMethod2CardEl.className = "text-end text-info";
                btcMethod2CardEl.title = tooltipText;
                console.log("已更新详情表格算法2产出:", method2Value);
            }
            
            // 更新主卡片中的元素
            if (btcMethod2CardMainEl) {
                btcMethod2CardMainEl.textContent = method2Value;
                btcMethod2CardMainEl.title = tooltipText;
                console.log("已更新主卡片算法2产出:", method2Value);
            }
        } else {
            console.error("无法更新算法2产出，数据缺失", data.btc_mined);
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
        var siteTotalHashrateEl = document.getElementById('total-hashrate-result');
        var btcPerThDailyEl = document.getElementById('btc-per-th-daily');
        var optimalElectricityRateEl = document.getElementById('optimal-electricity-rate');
        
        // 更新比特币网络信息
        if (data.network_data) {
            if (networkDifficultyEl) {
                networkDifficultyEl.textContent = formatNumber(data.network_data.network_difficulty, 2) + ' T';
            }
            if (networkHashrateEl) {
                networkHashrateEl.textContent = formatNumber(data.network_data.network_hashrate, 2) + ' EH/s';
            }
            if (currentBtcPriceEl) {
                currentBtcPriceEl.textContent = formatCurrency(data.network_data.btc_price);
            }
            if (blockRewardEl) {
                blockRewardEl.textContent = formatNumber(data.network_data.block_reward, 4) + ' BTC';
            }
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
        if (minerCountEl && data.inputs) {
            minerCountEl.textContent = formatNumber(data.inputs.miner_count, 0);
        }
    }
    
    // 更新矿场主数据
    function updateHostData(data) {
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
        var hostMonthlyCostEl = document.getElementById('monthly-electricity');
        var operationCostEl = document.getElementById('operation-cost');
        var totalExpensesEl = document.getElementById('host-total-expenses');
        
        // 矿场主盈亏平衡点
        var hostBreakEvenElectricityEl = document.getElementById('break-even-electricity');
        var hostBreakEvenBtcEl = document.getElementById('break-even-btc');
        var optimalCurtailmentEl = document.getElementById('optimal-curtailment');
        
        // 电费差计算 (Electricity differential)
        if (data.client_electricity_cost && data.electricity_cost) {
            // 计算电费差收益 - 客户电费减去实际电费
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
            
            // 矿场主月度净收益 = 电费差收益 - 运维成本
            var hostMonthlyNetProfit = hostElectricProfit - operationCostValue;
            if (hostProfitCardEl) {
                hostProfitCardEl.textContent = formatCurrency(hostMonthlyNetProfit);
            }
            
            // 更新月度净收益显示
            if (hostMonthlyProfitDisplayEl) {
                hostMonthlyProfitDisplayEl.textContent = formatCurrency(hostMonthlyNetProfit);
            }
            
            // 矿场主年度收益 = 月度净收益 * 12
            if (hostYearlyProfitEl) {
                var hostYearlyNetProfit = hostMonthlyNetProfit * 12;
                hostYearlyProfitEl.textContent = formatCurrency(hostYearlyNetProfit);
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
            hostBreakEvenBtcEl.textContent = formatCurrency(data.break_even.btc_price);
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
        var clientMonthlyBtcEl = document.getElementById('monthly-btc');
        var clientMonthlyBtcRevenueEl = document.getElementById('monthly-revenue');
        var clientTotalIncomeEl = document.getElementById('client-total-income');
        
        // 客户电费和成本
        var clientMonthlyElectricityEl = document.getElementById('client-monthly-electricity');
        var clientTotalExpensesEl = document.getElementById('client-total-expenses');
        
        // 客户利润详情
        var clientMonthlyProfitEl = document.getElementById('client-monthly-profit');
        var clientYearlyProfitEl = document.getElementById('client-yearly-profit');
        
        // 客户盈亏平衡点
        var clientBreakEvenElectricityEl = document.getElementById('client-break-even-electricity');
        var clientBreakEvenBtcEl = document.getElementById('client-break-even-btc');
        
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
        
        if (clientTotalExpensesEl && data.client_electricity_cost) {
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
            
            // 更新客户年度收益 = 月度收益 * 12
            if (clientYearlyProfitEl) {
                var clientYearlyProfit = clientMonthlyProfitValue * 12;
                clientYearlyProfitEl.textContent = formatCurrency(clientYearlyProfit);
            }
        }
        
        // 客户盈亏平衡点
        if (clientBreakEvenElectricityEl && data.break_even) {
            clientBreakEvenElectricityEl.textContent = '$' + formatNumber(data.break_even.electricity_cost, 4) + '/kWh';
        }
        
        if (clientBreakEvenBtcEl && data.break_even) {
            clientBreakEvenBtcEl.textContent = formatCurrency(data.break_even.btc_price);
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
                        chartContainer.innerHTML = '<div class="alert alert-warning text-center">无法生成热力图数据。(Could not generate heatmap data.)</div>';
                    }
                } else {
                    throw new Error('服务器返回状态码: ' + xhr.status);
                }
            } catch (error) {
                console.error('生成热力图失败:', error);
                chartContainer.innerHTML = '<div class="alert alert-danger text-center">生成热力图时出错。(Error generating heatmap.)</div>';
            }
        };
        
        xhr.onerror = function() {
            console.error('热力图请求失败');
            chartContainer.innerHTML = '<div class="alert alert-danger text-center">网络错误，请重试。(Network error, please try again.)</div>';
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
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 计算中... / Calculating...';
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
        errorDiv.innerHTML = message + 
            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
        
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
    
    // 格式化货币值 (Format currency value)
    function formatCurrency(value) {
        return '$' + formatNumber(value);
    }
    
    // 格式化数字 (Format number)
    function formatNumber(value, decimals) {
        if (decimals === undefined) decimals = 2;
        
        var formatter = new Intl.NumberFormat('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
        
        return formatter.format(value);
    }
    
    // 调用初始化函数 (Call init function)
    init();
});