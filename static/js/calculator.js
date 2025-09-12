// Bitcoin Mining Calculator - Clean Version
document.addEventListener('DOMContentLoaded', function() {
    console.log('[CALCULATOR.JS] Loading...');
    
    // Get form element
    var form = document.getElementById('mining-calculator-form');
    var resultsCard = document.getElementById('results-card');
    
    if (!form) {
        console.error('[CALCULATOR.JS] Form not found!');
        return;
    }
    
    console.log('[CALCULATOR.JS] Form found, initializing...');
    
    // Load network stats
    fetch('/network_stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 更新页面顶部显示数据
                document.getElementById('btc-price').textContent = '$' + data.btc_price.toLocaleString();
                document.getElementById('network-difficulty').textContent = (data.network_difficulty / 1e12).toFixed(2) + 'T';
                document.getElementById('network-hashrate').textContent = data.network_hashrate + ' EH/s';
                document.getElementById('block-reward').textContent = data.block_reward + ' BTC';
                
                // 重要：更新表单字段中的实时数据
                updateFormWithRealTimeData(data);
                
                // 强制立即更新BTC价格字段，无论开关状态
                var btcPriceField = document.getElementById('btc-price-input');
                if (btcPriceField && data.btc_price) {
                    btcPriceField.value = Math.round(data.btc_price);
                    console.log('[CALCULATOR.JS] Force updated BTC price to:', data.btc_price);
                }
                
                console.log('[CALCULATOR.JS] Network stats loaded');
            }
        })
        .catch(error => console.error('[CALCULATOR.JS] Error loading network stats:', error));
    
    // 存储实时数据
    var latestNetworkData = null;
    
    // 更新表单字段的实时数据
    function updateFormWithRealTimeData(networkData) {
        try {
            // 存储最新数据
            latestNetworkData = networkData;
            
            // 检查是否启用实时数据
            var useRealTimeData = document.getElementById('use-real-time');
            console.log('[CALCULATOR.JS] Use real-time checkbox state:', useRealTimeData ? useRealTimeData.checked : 'not found');
            
            if (useRealTimeData && useRealTimeData.checked) {
                // 更新BTC价格字段
                var btcPriceField = document.getElementById('btc-price-input');
                console.log('[CALCULATOR.JS] BTC price field found:', btcPriceField ? 'yes' : 'no');
                console.log('[CALCULATOR.JS] Network data BTC price:', networkData.btc_price);
                
                if (btcPriceField && networkData.btc_price) {
                    btcPriceField.value = Math.round(networkData.btc_price);
                    console.log('[CALCULATOR.JS] Updated BTC price to:', networkData.btc_price);
                } else {
                    console.log('[CALCULATOR.JS] Failed to update BTC price - field or data missing');
                }
                
                // 更新手动输入字段的默认值
                var manualHashrateField = document.getElementById('manual-hashrate');
                if (manualHashrateField && networkData.network_hashrate) {
                    manualHashrateField.value = networkData.network_hashrate;
                }
                
                var manualDifficultyField = document.getElementById('manual-difficulty');
                if (manualDifficultyField && networkData.network_difficulty) {
                    manualDifficultyField.value = networkData.network_difficulty;
                }
                
                console.log('[CALCULATOR.JS] Real-time data updated in form fields');
            }
        } catch (error) {
            console.error('[CALCULATOR.JS] Error updating form with real-time data:', error);
        }
    }
    
    // 监听"Use Real Time Data"开关变化
    var useRealTimeSwitch = document.getElementById('use-real-time');
    if (useRealTimeSwitch) {
        useRealTimeSwitch.addEventListener('change', function() {
            if (this.checked && latestNetworkData) {
                console.log('[CALCULATOR.JS] Real-time data enabled, updating fields...');
                updateFormWithRealTimeData(latestNetworkData);
                
                // 强制更新BTC价格
                var btcPriceField = document.getElementById('btc-price-input');
                if (btcPriceField && latestNetworkData.btc_price) {
                    btcPriceField.value = Math.round(latestNetworkData.btc_price);
                    console.log('[CALCULATOR.JS] Switch: Force updated BTC price to:', latestNetworkData.btc_price);
                }
            } else {
                console.log('[CALCULATOR.JS] Real-time data disabled');
            }
        });
    }
    
    // 立即检查实时数据开关状态并更新
    setTimeout(function() {
        var useRealTimeSwitch = document.getElementById('use-real-time');
        if (useRealTimeSwitch && useRealTimeSwitch.checked && latestNetworkData) {
            var btcPriceField = document.getElementById('btc-price-input');
            if (btcPriceField && latestNetworkData.btc_price) {
                btcPriceField.value = Math.round(latestNetworkData.btc_price);
                console.log('[CALCULATOR.JS] Delayed: Force updated BTC price to:', latestNetworkData.btc_price);
            }
        }
    }, 2000);
    
    // Load miners list
    fetch('/miners')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.miners) {
                var select = document.getElementById('miner-model');
                if (select) {
                    data.miners.forEach(function(miner) {
                        var option = document.createElement('option');
                        option.value = miner.name;
                        option.textContent = miner.name + ' (' + miner.hashrate + ' TH/s, ' + miner.power_consumption + 'W)';
                        select.appendChild(option);
                    });
                    console.log('[CALCULATOR.JS] Miners loaded:', data.miners.length);
                }
            }
        })
        .catch(error => console.error('[CALCULATOR.JS] Error loading miners:', error));
    
    // Handle miner selection
    var minerSelect = document.getElementById('miner-model');
    if (minerSelect) {
        minerSelect.addEventListener('change', function() {
            var selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.value) {
                // Parse miner specs from option text
                var text = selectedOption.textContent;
                var hashrate = text.match(/(\d+(?:\.\d+)?)\s*TH\/s/);
                var power = text.match(/(\d+)\s*W/);
                
                if (hashrate && power) {
                    document.getElementById('hashrate').value = hashrate[1];
                    document.getElementById('power-consumption').value = power[1];
                    console.log('[CALCULATOR.JS] Miner selected:', selectedOption.textContent, 'Hashrate:', hashrate[1], 'Power:', power[1]);
                    updateTotals();
                }
            }
        });
    }
    
    // Update totals and sync power calculations
    function updateTotals() {
        var hashrate = parseFloat(document.getElementById('hashrate').value) || 0;
        var power = parseFloat(document.getElementById('power-consumption').value) || 0;
        var minerCount = parseFloat(document.getElementById('miner-count').value) || 1;
        
        var totalHashrate = hashrate * minerCount;
        var totalPower = power * minerCount;
        
        // 更新总算力和总功耗显示
        var totalHashrateField = document.getElementById('total-hashrate');
        var totalPowerField = document.getElementById('total-power');
        
        if (totalHashrateField) totalHashrateField.value = totalHashrate.toFixed(2);
        if (totalPowerField) totalPowerField.value = totalPower.toFixed(0);
        
        // 更新显示字段
        var totalHashrateDisplay = document.getElementById('total-hashrate-display');
        var totalPowerDisplay = document.getElementById('total-power-display');
        
        if (totalHashrateDisplay) totalHashrateDisplay.value = totalHashrate.toFixed(2);
        if (totalPowerDisplay) totalPowerDisplay.value = totalPower.toFixed(0);
        
        // 更新Site Power (MW) 基于矿机数量和单台功耗
        var sitePowerField = document.getElementById('site-power-mw');
        if (sitePowerField && power > 0 && !sitePowerField.dataset.userModified) {
            var sitePowerMW = (totalPower / 1000000).toFixed(3); // 转换为MW
            sitePowerField.value = sitePowerMW;
            console.log('[CALCULATOR.JS] Auto-updated Site Power to:', sitePowerMW, 'MW');
        }
        
        console.log('[CALCULATOR.JS] Totals updated:', totalHashrate.toFixed(2), 'TH/s,', totalPower, 'W,', (totalPower/1000000).toFixed(3), 'MW');
        console.log('[CALCULATOR.JS] Fields updated - Display hashrate:', totalHashrateDisplay ? totalHashrateDisplay.value : 'N/A', 'Display power:', totalPowerDisplay ? totalPowerDisplay.value : 'N/A');
    }
    
    // 根据Site Power (MW) 自动计算矿机数量
    function updateMinerCountFromSitePower() {
        var sitePowerMW = parseFloat(document.getElementById('site-power-mw').value) || 0;
        var power = parseFloat(document.getElementById('power-consumption').value) || 3250; // 默认功耗
        
        if (sitePowerMW > 0 && power > 0) {
            var sitePowerWatts = sitePowerMW * 1000000; // MW转换为W
            var calculatedMinerCount = Math.floor(sitePowerWatts / power);
            
            var minerCountField = document.getElementById('miner-count');
            if (minerCountField) {
                minerCountField.value = calculatedMinerCount;
                console.log('[CALCULATOR.JS] Updated miner count from site power:', calculatedMinerCount, 'miners for', sitePowerMW, 'MW');
                updateTotals(); // 更新其他字段
            }
        }
    }
    
    // Watch for changes in miner-related fields
    ['hashrate', 'power-consumption', 'miner-count'].forEach(function(id) {
        var element = document.getElementById(id);
        if (element) {
            element.addEventListener('input', updateTotals);
        }
    });
    
    // Watch for Site Power (MW) changes
    var sitePowerField = document.getElementById('site-power-mw');
    if (sitePowerField) {
        sitePowerField.addEventListener('input', function() {
            this.dataset.userModified = 'true'; // 标记为用户手动修改
            console.log('[CALCULATOR.JS] Site Power changed by user to:', this.value, 'MW');
            updateMinerCountFromSitePower();
        });
    }
    
    // 初始化时调用一次updateTotals
    setTimeout(function() {
        console.log('[CALCULATOR.JS] Initializing calculations...');
        
        // 确保有默认值
        var minerCountField = document.getElementById('miner-count');
        var powerField = document.getElementById('power-consumption');
        var hashrateField = document.getElementById('hashrate');
        
        if (minerCountField && !minerCountField.value) minerCountField.value = '1';
        if (powerField && !powerField.value) powerField.value = '3068';
        if (hashrateField && !hashrateField.value) hashrateField.value = '100';
        
        updateTotals();
        console.log('[CALCULATOR.JS] Initial totals calculation completed');
        
        // 强制更新实时数据
        if (latestNetworkData) {
            updateFormWithRealTimeData(latestNetworkData);
            console.log('[CALCULATOR.JS] Force updated real-time data');
        }
    }, 1000);
    
    // Handle form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        console.log('[CALCULATOR.JS] Form submitted');
        
        // Update totals before submission
        updateTotals();
        
        // Prepare form data
        var formData = new FormData(form);
        var data = {};
        for (var pair of formData.entries()) {
            data[pair[0]] = pair[1];
        }
        
        console.log('[CALCULATOR.JS] Sending data:', data);
        
        // Send calculation request
        // 获取CSRF令牌
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                         document.querySelector('input[name="csrf_token"]')?.value;
        
        fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            console.log('[CALCULATOR.JS] Calculation result:', result);
            
            if (result.success !== false) {
                displayResults(result);
                if (resultsCard) {
                    resultsCard.style.display = 'block';
                }
            } else {
                alert('Calculation error: ' + (result.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('[CALCULATOR.JS] Error:', error);
            alert('Network error: ' + error.message);
        });
    });
    
    // Display results
    function displayResults(data) {
        var fields = {
            'daily-btc-mined': data.btc_mined || data.daily_btc_mined,
            'monthly-btc-mined': data.monthly_btc_mined,
            'yearly-btc-mined': data.yearly_btc_mined,
            'daily-revenue': data.daily_revenue_usd,
            'monthly-revenue': data.monthly_revenue_usd,
            'yearly-revenue': data.yearly_revenue_usd,
            'daily-electricity-cost': data.daily_electricity_cost_usd,
            'monthly-electricity-cost': data.monthly_electricity_cost_usd,
            'yearly-electricity-cost': data.yearly_electricity_cost_usd,
            'daily-profit': data.daily_profit_usd,
            'monthly-profit': data.monthly_profit_usd,
            'yearly-profit': data.yearly_profit_usd,
            'roi-days': data.roi_days,
            'monthly-roi': data.monthly_roi_percentage,
            'breakeven-btc-price': data.breakeven_btc_price
        };
        
        for (var id in fields) {
            var element = document.getElementById(id);
            if (element && fields[id] !== undefined) {
                if (id.includes('btc')) {
                    element.textContent = fields[id].toFixed(8) + ' BTC';
                } else if (id.includes('revenue') || id.includes('cost') || id.includes('profit') || id.includes('breakeven')) {
                    element.textContent = '$' + fields[id].toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                } else if (id === 'roi-days') {
                    element.textContent = fields[id] > 0 ? fields[id].toFixed(0) + ' days' : 'Never';
                } else if (id === 'monthly-roi') {
                    element.textContent = fields[id].toFixed(2) + '%';
                }
            }
        }
        
        console.log('[CALCULATOR.JS] Results displayed');
    }
    
    console.log('[CALCULATOR.JS] Initialization complete');
});