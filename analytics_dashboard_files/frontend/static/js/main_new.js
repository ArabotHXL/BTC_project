// Bitcoin Mining Calculator - Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('[MAIN_NEW.JS] DOMContentLoaded event fired!');
    console.log('[MAIN_NEW.JS] Starting execution...');
    
    try {
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
        console.log('[MAIN_NEW.JS] Form element found:', calculatorForm);
        
        // 隐藏字段（用于提交）
        var totalHashrateInput = document.getElementById('total-hashrate');
        var totalPowerInput = document.getElementById('total-power');
        
        // 显示字段（用于UI显示）
        var totalHashrateDisplay = document.getElementById('total-hashrate-display');
        var totalPowerDisplay = document.getElementById('total-power-display');
        
        // 在控制台输出所有dom元素，用于调试
        console.log("DOM元素获取结果:");
        console.log("总算力隐藏输入框:", totalHashrateInput ? "找到" : "未找到");
        console.log("总功耗隐藏输入框:", totalPowerInput ? "找到" : "未找到");
        console.log("总算力显示输入框:", totalHashrateDisplay ? "找到" : "未找到");
        console.log("总功耗显示输入框:", totalPowerDisplay ? "找到" : "未找到");
        
        var resultsCard = document.getElementById('results-card');
        var chartCard = document.getElementById('chart-card');
    
    // 初始化 (Initialization)
    function init() {
        console.log('[INIT] Starting initialization...');
        console.log('[INIT] calculatorForm element:', calculatorForm);
        console.log('[INIT] Form lookup result:', document.getElementById('mining-calculator-form'));
        
        // 加载网络数据 (Load network data)
        fetchNetworkStats();
        
        // 加载矿机型号列表 (Load miner models)
        fetchMiners();
        
        // 事件绑定 (Event bindings)
        if (calculatorForm) {
            console.log('[INIT] Binding form submit event...');
            calculatorForm.addEventListener('submit', handleCalculateSubmit);
            console.log('[INIT] Form submit event bound successfully');
            
            // 备用方案：直接绑定按钮点击事件
            var submitButton = calculatorForm.querySelector('button[type="submit"]');
            if (submitButton) {
                console.log('[INIT] Submit button found, adding backup click handler...');
                submitButton.addEventListener('click', function(event) {
                    console.log('[CLICK] Submit button clicked! (backup event)');
                    if (event.target.form) {
                        event.preventDefault();
                        handleCalculateSubmit(event);
                    }
                });
            }
        } else {
            console.error('[ERROR] Cannot find calculator form element! ID: mining-calculator-form');
            
            // 尝试延迟查找表单元素
            setTimeout(function() {
                console.log('🔄 延迟重试查找表单元素...');
                var delayedForm = document.getElementById('mining-calculator-form');
                if (delayedForm) {
                    console.log(' 延迟查找成功! 绑定事件...');
                    delayedForm.addEventListener('submit', handleCalculateSubmit);
                } else {
                    console.error(' 延迟查找仍然失败');
                }
            }, 1000);
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
                if (!minerModelSelect || !minerCountInput || !clientElectricityCostInput) {
                    showError('页面元素未完全加载，请刷新页面重试。(Page elements not fully loaded, please refresh.)');
                    return;
                }
                
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
        if (!useRealTimeCheckbox || !btcPriceInput) return;
        
        if (useRealTimeCheckbox.checked) {
            btcPriceInput.disabled = true;
            fetchNetworkStats();
        } else {
            btcPriceInput.disabled = false;
        }
    }
    
    // 计算总算力和总功耗
    function calculateTotalHashrateAndPower() {
        if (!minerCountInput || !hashrateInput || !powerConsumptionInput) return null;
        
        var minerCount = parseInt(minerCountInput.value) || 0;
        var hashrate = parseFloat(hashrateInput.value) || 0;
        var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
        
        console.log("计算总算力和总功耗 - 矿机数量:", minerCount, "单矿机算力:", hashrate, "单矿机功耗:", powerWatt);
        
        if (minerCount > 0 && hashrate > 0 && powerWatt > 0) {
            // 计算总算力和总功耗
            var totalHashrate = minerCount * hashrate;
            var totalPower = minerCount * powerWatt;
            
            console.log("计算结果 - 总算力:", totalHashrate, "总功耗:", totalPower);
            
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
    
    // 更新矿机规格 (Update miner specifications)
    function updateMinerSpecs() {
        if (!minerModelSelect) return;
        
        var selectedMiner = minerModelSelect.value;
        
        if (selectedMiner) {
            // 从localStorage获取矿机数据 (Get miner data from localStorage)
            var miners = JSON.parse(localStorage.getItem('miners') || '[]');
            var miner = miners.find(function(m) { return m.name === selectedMiner; });
            
            if (miner) {
                if (hashrateInput) hashrateInput.value = miner.hashrate;
                if (powerConsumptionInput) powerConsumptionInput.value = miner.power_watt;
                
                // 禁用手动输入 (Disable manual input)
                if (hashrateInput) hashrateInput.disabled = true;
                if (hashrateUnitSelect) hashrateUnitSelect.disabled = true;
                if (powerConsumptionInput) powerConsumptionInput.disabled = true;
                
                // 基于矿机功率和数量更新显示 (Update based on miner power and count)
                updateMinerCount();
                // 计算并更新总算力和总功耗
                calculateTotalHashrateAndPower();
            }
        } else {
            // 启用手动输入 (Enable manual input)
            if (hashrateInput) hashrateInput.disabled = false;
            if (hashrateUnitSelect) hashrateUnitSelect.disabled = false;
            if (powerConsumptionInput) powerConsumptionInput.disabled = false;
        }
    }
    
    // 更新矿机数量 (Update miner count)
    function updateMinerCount() {
        if (!sitePowerMwInput || !powerConsumptionInput || !minerCountInput) return;
        
        var sitePowerMw = parseFloat(sitePowerMwInput.value) || 0;
        var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
        
        if (sitePowerMw > 0 && powerWatt > 0) {
            // 计算最大矿机数量 (Calculate maximum miner count)
            // Formula: (site_power_mw * 1000) / (power_watt / 1000)
            var maxMiners = Math.floor((sitePowerMw * 1000000) / powerWatt);
            minerCountInput.value = maxMiners;
            
            // 计算并更新总算力和总功耗
            calculateTotalHashrateAndPower();
        }
    }
    
    // 处理计算表单提交 (Handle calculation form submission)
    function handleCalculateSubmit(event) {
        event.preventDefault();
        console.log(' 开始处理表单提交...');
        
        // 在提交表单前重新计算总算力和总功耗
        console.log(" 表单提交前重新计算总算力和总功耗");
        calculateTotalHashrateAndPower();
        
        // 表单验证 (Form validation)
        var hasErrors = false;
        
        if (minerModelSelect && minerModelSelect.value === "") {
            if (!hashrateInput || !hashrateInput.value || parseFloat(hashrateInput.value) <= 0) {
                showError('请输入有效的算力值。(Please enter a valid hashrate value.)');
                hasErrors = true;
            }
            
            if (!powerConsumptionInput || !powerConsumptionInput.value || parseFloat(powerConsumptionInput.value) <= 0) {
                showError('请输入有效的功率值。(Please enter a valid power consumption value.)');
                hasErrors = true;
            }
        }
        
        if (electricityCostInput && (!electricityCostInput.value || parseFloat(electricityCostInput.value) < 0)) {
            showError('请输入有效的电费。(Please enter a valid electricity cost.)');
            hasErrors = true;
        }
        
        if (useRealTimeCheckbox && btcPriceInput && !useRealTimeCheckbox.checked && (!btcPriceInput.value || parseFloat(btcPriceInput.value) <= 0)) {
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
        
        // 手动确保总算力和总功耗已添加到表单
        var minerCount = parseInt(minerCountInput.value) || 0;
        var hashrate = parseFloat(hashrateInput.value) || 0;
        var powerWatt = parseFloat(powerConsumptionInput.value) || 0;
        
        if (minerCount > 0 && hashrate > 0 && powerWatt > 0) {
            var totalHashrate = minerCount * hashrate;
            var totalPower = minerCount * powerWatt;
            
            console.log("提交表单前手动重新计算 - 总算力:", totalHashrate, "总功耗:", totalPower);
            
            // 确保表单中有最新值
            formData.set('total_hashrate', totalHashrate.toFixed(0));
            formData.set('total_power', totalPower.toFixed(0));
        }
        
        // 请求计算 (Request calculation)
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/calculate', true);
        
        xhr.onload = function() {
            console.log(' 收到服务器响应，状态码:', xhr.status);
            console.log('📦 响应内容:', xhr.responseText);
            try {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    console.log(' 解析后的计算结果:', data);
                    
                    if (data.success) {
                        console.log('🎯 开始显示计算结果...');
                        // 显示结果 (Display results)
                        displayResults(data);
                        console.log(' 结果显示完成');
                    } else {
                        console.error(' 服务器返回失败结果:', data.error);
                        showError(data.error || '计算过程中发生错误。(An error occurred during calculation.)');
                    }
                } else {
                    throw new Error('服务器返回状态码: ' + xhr.status);
                }
            } catch (error) {
                console.error(' 处理响应时出错:', error);
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
            if (el) {
                el.innerHTML = '';  // Clear content first
                const loadingElement = document.createElement('small');
                loadingElement.className = 'text-muted';
                loadingElement.textContent = 'Loading...';
                el.appendChild(loadingElement);
            }
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
                        if (networkDifficultyEl) networkDifficultyEl.textContent = formatNumber(data.difficulty / 1e12, 1) + 'T';
                        if (networkHashrateEl) networkHashrateEl.textContent = formatNumber(data.hashrate) + ' EH/s';
                        if (blockRewardEl) blockRewardEl.textContent = formatNumber(data.block_reward) + ' BTC';
                        
                        // 更新BTC价格输入框 (Update BTC price input)
                        if (useRealTimeCheckbox && useRealTimeCheckbox.checked && btcPriceInput) {
                            btcPriceInput.value = data.price.toFixed(2);
                            btcPriceInput.disabled = true;
                        }
                        
                        // 清除旧的缓存并保存最新数据 (Clear old cache and save latest data)
                        localStorage.removeItem('last_btc_price');
                        localStorage.removeItem('last_network_difficulty');
                        localStorage.removeItem('last_network_hashrate');
                        localStorage.removeItem('last_block_reward');
                        
                        localStorage.setItem('last_btc_price', data.price);
                        localStorage.setItem('last_network_difficulty', data.difficulty);
                        localStorage.setItem('last_network_hashrate', data.hashrate);
                        localStorage.setItem('last_block_reward', data.block_reward);
                        
                        console.log('已更新价格缓存:', data.price);
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
            networkDifficultyEl.textContent = formatNumber(parseFloat(lastDifficulty) / 1e12, 1) + 'T';
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
        console.log(' 检查接收到的数据结构:', data);
        console.log(' resultsCard元素状态:', resultsCard);
        
        if (!data || !data.btc_mined) {
            console.error(' 数据验证失败 - data:', data, 'btc_mined:', data?.btc_mined);
            showError('服务器返回的数据无效。(Invalid data received from server.)');
            return;
        }
        
        try {
            console.log(' 开始处理计算结果数据:', data);
            
            // 显示结果卡片 (Show results card)
            console.log('🎯 准备显示结果卡片...');
            if (resultsCard) {
                console.log('📺 设置results-card为可见...');
                resultsCard.style.display = 'block';
                console.log(' results-card已设置为可见，当前样式:', resultsCard.style.display);
            } else {
                console.error(' 无法找到results-card元素!');
                return;
            }
            
            // ===== 1. 基本BTC挖矿产出 =====
            updateBtcOutputDisplay(data);
            
            // ===== 2. 网络和挖矿信息 =====
            updateNetworkAndMiningInfo(data);
            
            // ===== 3. 电力削减详情 =====
            updateCurtailmentDetails(data);
            
            // ===== 4. 矿场主(Host)数据 =====
            updateHostData(data);
            
            // 生成矿场主ROI图表
            if (data.roi && data.roi.host && data.roi.host.cumulative_roi && data.inputs && data.inputs.host_investment) {
                generateRoiChart(
                    data.roi.host.cumulative_roi, 
                    'host-roi-chart', 
                    '矿场主投资回报分析 (Host ROI Analysis)', 
                    data.inputs.host_investment
                );
            }
            
            // ===== 4. 客户(Customer)数据 =====
            updateCustomerData(data);
            
            // 生成客户ROI图表
            if (data.roi && data.roi.client && data.roi.client.cumulative_roi && data.inputs && data.inputs.client_investment) {
                generateRoiChart(
                    data.roi.client.cumulative_roi, 
                    'client-roi-chart', 
                    '客户投资回报分析 (Client ROI Analysis)', 
                    data.inputs.client_investment
                );
            }
            
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
            var tooltipText = '基于API网络算力 - 每月约: ' + formatNumber(monthlyOutput1, 8) + ' BTC';
            
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
            var tooltipText = '基于网络难度计算 - 每月约: ' + formatNumber(monthlyOutput2, 8) + ' BTC';
            
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
        
        // 计算和显示算法差异分析
        if (data.btc_mined && data.btc_mined.method1 && data.btc_mined.method2) {
            var method1Daily = data.btc_mined.method1.daily;
            var method2Daily = data.btc_mined.method2.daily;
            var difference = Math.abs(method1Daily - method2Daily);
            var percentageDiff = method2Daily > 0 ? (difference / method2Daily * 100) : 0;
            
            // 更新算法差异显示
            var algorithmDiffEl = document.getElementById('algorithm-difference');
            if (algorithmDiffEl) {
                var diffText = '';
                var diffClass = 'small';
                var tooltipText = '';
                
                if (percentageDiff < 0.01) {
                    diffText = '✓ 算法一致 (差异 < 0.01%)';
                    diffClass += ' text-success';
                    tooltipText = '当前API网络算力与基于难度计算的算力一致，两算法产生相同结果';
                } else if (percentageDiff < 1) {
                    diffText = ' 微小差异 (' + formatNumber(percentageDiff, 3) + '%)';
                    diffClass += ' text-warning';
                    tooltipText = 'API数据与难度计算存在微小差异，系统使用平均值';
                } else if (percentageDiff < 5) {
                    diffText = '△ 小幅差异 (' + formatNumber(percentageDiff, 2) + '%)';
                    diffClass += ' text-info';
                    tooltipText = 'API与难度计算存在一定差异，系统智能选择或平均';
                } else {
                    diffText = '! 显著差异 (' + formatNumber(percentageDiff, 2) + '%)';
                    diffClass += ' text-danger';
                    tooltipText = '算法差异较大，系统优先使用更稳定的难度算法';
                }
                
                algorithmDiffEl.textContent = diffText;
                algorithmDiffEl.className = diffClass;
                algorithmDiffEl.title = tooltipText + '\n算法1: ' + formatNumber(method1Daily, 8) + ' BTC\n算法2: ' + formatNumber(method2Daily, 8) + ' BTC';
                
                console.log("算法差异分析:", diffText, "差异值:", difference, "百分比:", percentageDiff.toFixed(4) + "%");
                
                // 如果有网络数据，显示更多信息
                if (data.network_data) {
                    var detailText = '\n网络算力: ' + formatNumber(data.network_data.network_hashrate, 2) + ' EH/s';
                    detailText += '\n网络难度: ' + formatNumber(data.network_data.network_difficulty, 2) + ' T';
                    algorithmDiffEl.title += detailText;
                }
            }
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
        
        // 处理ROI数据
        var hostInvestmentAmountEl = document.getElementById('host-investment-amount');
        var hostAnnualRoiEl = document.getElementById('host-annual-roi');
        var hostPaybackMonthsEl = document.getElementById('host-payback-months');
        var hostPaybackYearsEl = document.getElementById('host-payback-years');
        
        // 如果存在ROI数据并且有矿场主ROI数据
        if (data.roi && data.roi.host) {
            var hostRoi = data.roi.host;
            
            // 显示投资金额
            if (hostInvestmentAmountEl && data.inputs && data.inputs.host_investment) {
                hostInvestmentAmountEl.textContent = formatCurrency(data.inputs.host_investment);
            }
            
            // 显示年化ROI百分比
            if (hostAnnualRoiEl && hostRoi.roi_percent_annual) {
                hostAnnualRoiEl.textContent = formatNumber(hostRoi.roi_percent_annual, 2) + '%';
            }
            
            // 显示回收期（月）
            if (hostPaybackMonthsEl && hostRoi.payback_period_months) {
                var months = hostRoi.payback_period_months;
                // 处理无限回收期的情况
                if (months === Infinity || months > 9999) {
                    hostPaybackMonthsEl.textContent = 'N/A';
                } else {
                    hostPaybackMonthsEl.textContent = formatNumber(months, 1) + ' months';
                }
            }
            
            // 显示回收期（年）
            if (hostPaybackYearsEl && hostRoi.payback_period_years) {
                var years = hostRoi.payback_period_years;
                // 处理无限回收期的情况
                if (years === Infinity || years > 999) {
                    hostPaybackYearsEl.textContent = 'N/A';
                } else {
                    hostPaybackYearsEl.textContent = formatNumber(years, 2) + ' years';
                }
            }
            
            // 如果有forecast数据，生成矿场主ROI图表
            if (hostRoi.forecast && Array.isArray(hostRoi.forecast)) {
                console.log('矿场主ROI数据可用，生成图表', hostRoi.forecast.length, '个数据点');
                // 调用生成ROI图表函数
                generateRoiChart(
                    hostRoi.forecast, 
                    'host-roi-chart', 
                    '矿场主投资回收曲线 / Host Investment Recovery', 
                    data.inputs.host_investment
                );
            }
        } else {
            // 如果没有ROI数据，显示默认值
            if (hostInvestmentAmountEl) hostInvestmentAmountEl.textContent = '$0.00';
            if (hostAnnualRoiEl) hostAnnualRoiEl.textContent = '0.00%';
            if (hostPaybackMonthsEl) hostPaybackMonthsEl.textContent = 'N/A';
            if (hostPaybackYearsEl) hostPaybackYearsEl.textContent = 'N/A';
        }
    }
    
    // 更新电力削减详情
    function updateCurtailmentDetails(data) {
        try {
            console.log("更新电力削减详情 - 开始", data.curtailment_details);
            // 获取削减百分比
            const curtailmentPercentage = data?.inputs?.curtailment || 0;
            console.log("削减百分比:", curtailmentPercentage);
            
            // 获取电力削减详情部分
            const curtailmentSection = document.getElementById('curtailment-details-section');
            if (!curtailmentSection) {
                // 静默处理，可能因为权限限制而不显示此元素
                console.debug('电力削减详情部分不可用 (可能因权限限制)');
                return;
            }
            
            // 如果没有削减或没有详情数据，则隐藏部分
            if (curtailmentPercentage <= 0 || !data.curtailment_details || Object.keys(data.curtailment_details).length === 0) {
                curtailmentSection.style.display = 'none';
                return;
            }
            
            // 显示削减详情部分
            curtailmentSection.style.display = 'block';
            
            // 关机策略翻译映射
            const strategyTranslation = {
                'efficiency': '按效率关机 (Efficiency-based)',
                'proportional': '按比例关机 (Proportional)',
                'random': '随机关机 (Random)'
            };
            
            // 检查元素是否存在并更新
            const strategyEl = document.getElementById('curtailment-strategy');
            if (strategyEl) {
                const strategy = data.curtailment_details.strategy || '';
                strategyEl.textContent = strategyTranslation[strategy] || strategy;
            }
            
            const savedElectricityEl = document.getElementById('saved-electricity');
            if (savedElectricityEl) {
                savedElectricityEl.textContent = formatNumber(data.curtailment_details.saved_electricity_kwh || 0, 2) + ' kWh';
            }
            
            const savedCostEl = document.getElementById('saved-electricity-cost');
            if (savedCostEl) {
                savedCostEl.textContent = formatCurrency(data.curtailment_details.saved_electricity_cost || 0);
            }
            
            const revenueLossEl = document.getElementById('revenue-loss');
            if (revenueLossEl) {
                revenueLossEl.textContent = formatCurrency(data.curtailment_details.revenue_loss || 0);
            }
            
            const netImpactEl = document.getElementById('net-impact');
            if (netImpactEl) {
                netImpactEl.textContent = formatCurrency(data.curtailment_details.net_impact || 0);
            }
            
            // 更新关闭的矿机详情
            const shutdownMinersTable = document.getElementById('shutdown-miners-list');
            if (shutdownMinersTable) {
                shutdownMinersTable.innerHTML = '';
                
                // 如果有关闭的矿机数据
                if (data.curtailment_details.shutdown_miners && Array.isArray(data.curtailment_details.shutdown_miners) && data.curtailment_details.shutdown_miners.length > 0) {
                    data.curtailment_details.shutdown_miners.forEach(miner => {
                        try {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${miner.model || 'Unknown'}</td>
                                <td>${miner.count || 0}</td>
                                <td>${formatNumber(miner.hashrate_th || 0, 2)} TH/s</td>
                                <td>${formatNumber(miner.power_kw || 0, 2)} kW</td>
                            `;
                            shutdownMinersTable.appendChild(row);
                        } catch (minerError) {
                            console.error('处理关机矿机数据时出错:', minerError, miner);
                        }
                    });
                } else {
                    // 如果没有关闭的矿机数据，显示提示
                    const row = document.createElement('tr');
                    row.innerHTML = `<td colspan="4" class="text-center">无关闭矿机数据</td>`;
                    shutdownMinersTable.appendChild(row);
                }
            }
            
        } catch (error) {
            console.error('显示电力削减详情时出错:', error);
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
        
        // 处理客户ROI数据
        var clientInvestmentAmountEl = document.getElementById('client-investment-amount');
        var clientAnnualRoiEl = document.getElementById('client-annual-roi');
        var clientPaybackMonthsEl = document.getElementById('client-payback-months');
        var clientPaybackYearsEl = document.getElementById('client-payback-years');
        
        // 如果存在ROI数据并且有客户ROI数据
        if (data.roi && data.roi.client) {
            var clientRoi = data.roi.client;
            
            // 显示投资金额
            if (clientInvestmentAmountEl && data.inputs && data.inputs.client_investment) {
                clientInvestmentAmountEl.textContent = formatCurrency(data.inputs.client_investment);
            }
            
            // 显示年化ROI百分比
            if (clientAnnualRoiEl && clientRoi.roi_percent_annual) {
                clientAnnualRoiEl.textContent = formatNumber(clientRoi.roi_percent_annual, 2) + '%';
            }
            
            // 显示回收期（月）
            if (clientPaybackMonthsEl && clientRoi.payback_period_months) {
                var months = clientRoi.payback_period_months;
                // 处理无限回收期的情况
                if (months === Infinity || months > 9999) {
                    clientPaybackMonthsEl.textContent = 'N/A';
                } else {
                    clientPaybackMonthsEl.textContent = formatNumber(months, 1) + ' months';
                }
            }
            
            // 显示回收期（年）
            if (clientPaybackYearsEl && clientRoi.payback_period_years) {
                var years = clientRoi.payback_period_years;
                // 处理无限回收期的情况
                if (years === Infinity || years > 999) {
                    clientPaybackYearsEl.textContent = 'N/A';
                } else {
                    clientPaybackYearsEl.textContent = formatNumber(years, 2) + ' years';
                }
            }
            
            // 如果有forecast数据，生成客户ROI图表
            if (clientRoi.forecast && Array.isArray(clientRoi.forecast)) {
                console.log('客户ROI数据可用，生成图表', clientRoi.forecast.length, '个数据点');
                // 调用生成ROI图表函数
                generateRoiChart(
                    clientRoi.forecast, 
                    'client-roi-chart', 
                    '客户投资回收曲线 / Client Investment Recovery', 
                    data.inputs.client_investment
                );
            }
        } else {
            // 如果没有ROI数据，显示默认值
            if (clientInvestmentAmountEl) clientInvestmentAmountEl.textContent = '$0.00';
            if (clientAnnualRoiEl) clientAnnualRoiEl.textContent = '0.00%';
            if (clientPaybackMonthsEl) clientPaybackMonthsEl.textContent = 'N/A';
            if (clientPaybackYearsEl) clientPaybackYearsEl.textContent = 'N/A';
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
                        // 清空容器
                        chartContainer.innerHTML = '';
                        
                        // 添加Canvas
                        var canvasElement = document.createElement('canvas');
                        canvasElement.id = 'heatmap-canvas';
                        canvasElement.width = '100%';
                        canvasElement.height = '400';
                        chartContainer.appendChild(canvasElement);
                        
                        // 添加说明区域
                        var descriptionCard = document.createElement('div');
                        descriptionCard.className = 'mt-3 mb-2 text-center card p-3 bg-dark text-light border-secondary';
                        descriptionCard.style.fontSize = '0.9rem';
                        descriptionCard.innerHTML = '<p class="mb-1">' + 
                            '此热力图显示不同BTC价格和电价组合下的月度利润变化情况。点的颜色表示盈利状况：深绿色表示高盈利，浅绿色表示低盈利，红色表示亏损。' + 
                            '点的大小与盈利金额成正比。将鼠标悬停在点上可查看详细信息。</p>' +
                            '<p class="mb-0">' + 
                            'This chart shows how monthly profits change with different BTC prices and electricity costs. ' +
                            'Point colors indicate profitability: dark green for high profits, light green for low profits, red for losses. ' +
                            'Point sizes are proportional to profit amount. Hover over points for details.</p>';
                        chartContainer.appendChild(descriptionCard);
                        
                        // 添加版权信息
                        var copyrightElement = document.createElement('div');
                        copyrightElement.className = 'text-center text-muted small mt-1 mb-3';
                        copyrightElement.innerText = 'Bitcoin Mining Profitability Calculator © 2025';
                        chartContainer.appendChild(copyrightElement);
                        
                        var canvas = document.getElementById('heatmap-canvas');
                        
                        // 创建一个热图效果的高级散点图
                        // 定义颜色函数 
                        function getColor(profit) {
                            if (profit > 500000) return 'rgba(0, 100, 0, 0.9)';      // 非常深绿色
                            if (profit > 300000) return 'rgba(0, 128, 0, 0.9)';      // 深绿色
                            if (profit > 200000) return 'rgba(34, 139, 34, 0.9)';    // 森林绿
                            if (profit > 100000) return 'rgba(50, 168, 82, 0.9)';    // 中绿色
                            if (profit > 50000) return 'rgba(60, 179, 113, 0.9)';    // 中绿色
                            if (profit > 10000) return 'rgba(92, 184, 92, 0.9)';     // 浅绿色 
                            if (profit > 0) return 'rgba(144, 238, 144, 0.9)';       // 非常浅绿色
                            if (profit > -10000) return 'rgba(255, 182, 193, 0.9)';  // 浅红色
                            if (profit > -50000) return 'rgba(255, 105, 97, 0.9)';   // 中红色
                            if (profit > -100000) return 'rgba(220, 20, 60, 0.9)';   // 暗红色
                            return 'rgba(139, 0, 0, 0.9)';                           // 深红色
                        }
                        
                        // 添加色标图例
                        var legendHTML = '<div class="profit-legend mt-3 mb-2 d-flex justify-content-center">' +
                            '<div class="d-flex align-items-center">' +
                            '<span style="background:rgba(139,0,0,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">亏损 &lt; -100K</span>' +
                            
                            '<span style="background:rgba(220,20,60,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">-100K ~ -50K</span>' +
                            
                            '<span style="background:rgba(255,105,97,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">-50K ~ -10K</span>' +
                            
                            '<span style="background:rgba(255,182,193,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">-10K ~ 0</span>' +
                            '</div></div>' +
                            
                            '<div class="profit-legend mb-3 d-flex justify-content-center">' +
                            '<div class="d-flex align-items-center">' +
                            '<span style="background:rgba(144,238,144,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">0 ~ 10K</span>' +
                            
                            '<span style="background:rgba(92,184,92,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">10K ~ 50K</span>' +
                            
                            '<span style="background:rgba(60,179,113,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">50K ~ 100K</span>' +
                            
                            '<span style="background:rgba(34,139,34,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">100K ~ 300K</span>' +
                            
                            '<span style="background:rgba(0,100,0,0.9);width:20px;height:20px;display:inline-block;margin-right:5px;"></span>' +
                            '<span class="me-3" style="font-size:0.8rem;">&gt; 300K</span>' +
                            '</div></div>';
                        
                        // 添加到图表底部
                        chartContainer.insertAdjacentHTML('beforeend', legendHTML);
                        
                        // 安全检查canvas元素
                        if (canvas && typeof canvas.getContext === 'function') {
                            new Chart(canvas, {
                            type: 'bubble',
                            data: {
                                datasets: [{
                                    label: '月利润 (Monthly Profit) $',
                                    data: scatterData.map(function(item) {
                                        return {
                                            x: item.x,
                                            y: item.y,
                                            r: 15, // 统一的大小以避免视觉误导，形成热图效果
                                            profit: item.profit
                                        };
                                    }),
                                    backgroundColor: function(context) {
                                        if (!context.raw) return 'rgba(128, 128, 128, 0.7)';
                                        return getColor(context.raw.profit);
                                    },
                                    borderColor: 'rgba(20, 30, 40, 0.3)',
                                    borderWidth: 1,
                                    hoverRadius: 18,
                                    hoverBorderWidth: 2
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {
                                    x: {
                                        title: {
                                            display: true,
                                            text: '电价 ($/kWh)',
                                            font: {
                                                weight: 'bold'
                                            }
                                        },
                                        ticks: {
                                            callback: function(value) {
                                                return '$' + value.toFixed(2);
                                            }
                                        }
                                    },
                                    y: {
                                        title: {
                                            display: true,
                                            text: '比特币价格 ($)',
                                            font: {
                                                weight: 'bold'
                                            }
                                        },
                                        ticks: {
                                            callback: function(value) {
                                                return '$' + value.toLocaleString();
                                            }
                                        }
                                    }
                                },
                                plugins: {
                                    tooltip: {
                                        callbacks: {
                                            label: function(context) {
                                                var profit = context.raw.profit;
                                                var btcPrice = context.raw.y;
                                                var electricityCost = context.raw.x;
                                                
                                                var lines = [
                                                    '电价: $' + electricityCost.toFixed(3) + '/kWh',
                                                    'BTC价格: $' + btcPrice.toLocaleString(),
                                                    '月利润: $' + profit.toLocaleString(undefined, {
                                                        minimumFractionDigits: 2,
                                                        maximumFractionDigits: 2
                                                    }),
                                                    '年利润: $' + (profit * 12).toLocaleString(undefined, {
                                                        minimumFractionDigits: 2,
                                                        maximumFractionDigits: 2
                                                    })
                                                ];
                                                
                                                if (profit > 0) {
                                                    return lines;
                                                } else {
                                                    // 添加标记表示亏损
                                                    return [' 亏损运营 / Loss Operation'].concat(lines);
                                                }
                                            },
                                            title: function() {
                                                // 清空标题，使用自定义标签替代
                                                return '';
                                            }
                                        },
                                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                        titleFont: {
                                            weight: 'bold',
                                            size: 13
                                        },
                                        bodyFont: {
                                            size: 12
                                        },
                                        padding: 10
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
                            console.error('Canvas element or getContext method not available for heatmap');
                            chartContainer.innerHTML = '<div class="alert alert-warning text-center">图表功能暂时不可用。(Chart feature temporarily unavailable.)</div>';
                        }
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
    
    // 生成ROI图表函数
    function generateRoiChart(roiData, elementId, title, investmentAmount) {
        try {
            // 判断是否有ROI数据
            if (!roiData || !Array.isArray(roiData) || roiData.length === 0) {
                console.error('没有有效的ROI数据用于生成图表');
                var container = document.getElementById(elementId);
                if (container) {
                    container.innerHTML = '<div class="alert alert-warning text-center">没有有效的ROI数据可显示。(No valid ROI data to display.)</div>';
                }
                return;
            }
            
            // 查找容器
            var container = document.getElementById(elementId);
            if (!container) {
                // 静默处理，可能因为权限限制而不显示此元素
                console.debug('ROI图表容器不可用:', elementId, '(可能因权限限制)');
                return;
            }
            
            // 完全重置容器内容
            container.innerHTML = '';
            
            // 创建图表区域，设置固定高度，避免内容溢出影响布局
            var chartArea = document.createElement('div');
            chartArea.style.width = '100%';
            chartArea.style.height = '300px';
            chartArea.style.position = 'relative';
            container.appendChild(chartArea);
            
            // 创建画布元素
            var canvasEl = document.createElement('canvas');
            canvasEl.width = 400;
            canvasEl.height = 300;
            chartArea.appendChild(canvasEl);
            
            // 分离月度和累积ROI数据
            var labels = [];
            var cumulativeRoiValues = [];
            var cumulativeProfitValues = [];
            var breakEvenPoint = null;
            
            // 准备图表数据
            roiData.forEach(function(point, index) {
                labels.push(point.month);
                cumulativeRoiValues.push(point.roi_percent);
                cumulativeProfitValues.push(point.cumulative_profit);
                
                // 查找回收期点
                if (breakEvenPoint === null && point.cumulative_profit >= investmentAmount) {
                    breakEvenPoint = index;
                }
            });
            
            // 安全检查并创建图表
            if (canvasEl && typeof canvasEl.getContext === 'function') {
                var ctx = canvasEl.getContext('2d');
            var chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'ROI (%)',
                        data: cumulativeRoiValues,
                        borderColor: 'rgba(52, 152, 219, 1)',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderWidth: 2,
                        pointRadius: 1,
                        pointHoverRadius: 5,
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: '累积利润 / Cumulative Profit ($)',
                        data: cumulativeProfitValues,
                        borderColor: 'rgba(46, 204, 113, 1)',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        borderWidth: 2,
                        pointRadius: 1,
                        pointHoverRadius: 5,
                        fill: true,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: title,
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                var label = context.dataset.label || '';
                                var value = context.raw;
                                
                                if (label.includes('ROI')) {
                                    return label + ': ' + formatNumber(value, 2) + '%';
                                } else if (label.includes('Profit')) {
                                    return label + ': $' + formatNumber(value, 2);
                                }
                                return label + ': ' + value;
                            }
                        }
                    },
                    annotation: {
                        annotations: breakEvenPoint !== null ? {
                            breakEven: {
                                type: 'line',
                                xMin: breakEvenPoint,
                                xMax: breakEvenPoint,
                                borderColor: 'rgba(255, 99, 132, 0.8)',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    content: '回收期 / Payback',
                                    enabled: true,
                                    position: 'top',
                                    backgroundColor: 'rgba(255, 99, 132, 0.8)',
                                    color: 'white',
                                    font: {
                                        size: 11
                                    }
                                }
                            },
                            investment: {
                                type: 'line',
                                yMin: investmentAmount,
                                yMax: investmentAmount,
                                borderColor: 'rgba(255, 159, 64, 0.8)',
                                borderWidth: 2,
                                borderDash: [3, 3],
                                yScaleID: 'y1',
                                label: {
                                    content: '投资金额 / Investment: $' + formatNumber(investmentAmount),
                                    enabled: true,
                                    position: 'left',
                                    backgroundColor: 'rgba(255, 159, 64, 0.8)',
                                    color: 'white',
                                    font: {
                                        size: 11
                                    }
                                }
                            }
                        } : {}
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '月份 / Month',
                            font: {
                                weight: 'bold'
                            }
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '累计ROI (%) / Cumulative ROI (%)',
                            font: {
                                weight: 'bold'
                            }
                        },
                        beginAtZero: true,
                        position: 'left',
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    y1: {
                        title: {
                            display: true,
                            text: '累计利润 ($) / Cumulative Profit ($)',
                            font: {
                                weight: 'bold'
                            }
                        },
                        beginAtZero: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + formatNumber(value, 0);
                            }
                        }
                    }
                }
            }
        });
        
        // 添加图表描述 - 放在容器最后，这样就不会与图表重叠
        var description = document.createElement('div');
        description.className = 'roi-chart-description small text-center mt-5 pt-4 text-muted';
        description.style.marginBottom = '60px'; // 强制添加大间距
        description.style.paddingBottom = '30px'; // 额外填充
        description.style.marginTop = '50px'; // 顶部额外空间
        description.style.clear = 'both'; // 确保不会有浮动元素
        description.innerHTML = '此图表显示了投资回报随时间的变化情况。蓝线表示累计ROI百分比，绿线表示累计利润金额。' +
                              '<br>This chart shows how ROI changes over time. Blue line represents cumulative ROI percentage, green line shows cumulative profit.';
        container.appendChild(description);
        
        return chart;
            } else {
                console.error('Canvas element or getContext method not available');
                var container = document.getElementById(elementId);
                if (container) {
                    container.innerHTML = '<div class="alert alert-warning text-center">图表功能暂时不可用。(Chart feature temporarily unavailable.)</div>';
                }
                return null;
            }
        } catch (error) {
            console.error('生成ROI图表时出错:', error);
            var container = document.getElementById(elementId);
            if (container) {
                container.innerHTML = '<div class="alert alert-danger text-center">生成投资回报图表时出错。(Error generating ROI chart.)</div>';
            }
            return null;
        }
    }
    
        // 调用初始化函数 (Call init function)
        console.log('🔧🔧🔧 准备调用init()函数...');
        init();
        console.log(' init()函数调用完成!');
        
    } catch (error) {
        console.error(' JavaScript执行错误:', error);
        console.error('错误堆栈:', error.stack);
    }
});