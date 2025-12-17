// Bitcoin Mining Calculator - Restored Clean Version
document.addEventListener('DOMContentLoaded', function() {
    console.log('[CALCULATOR] Loading...');
    
    var form = document.getElementById('mining-calculator-form');
    if (!form) {
        console.error('[CALCULATOR] Form not found');
        return;
    }
    
    console.log('[CALCULATOR] Form found, initializing...');
    
    // Load and update real-time data
    function loadNetworkStats() {
        fetch('/network_stats')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update display with proper formatting
                    document.getElementById('btc-price').textContent = '$' + Math.round(data.btc_price).toLocaleString();
                    document.getElementById('network-difficulty').textContent = (data.network_difficulty / 1e12).toFixed(2) + 'T';
                    document.getElementById('network-hashrate').textContent = data.network_hashrate + ' EH/s';
                    document.getElementById('block-reward').textContent = data.block_reward + ' BTC';
                    
                    // Update BTC price in form
                    var btcField = document.getElementById('btc-price-input');
                    if (btcField) {
                        btcField.value = Math.round(data.btc_price);
                        console.log('[CALCULATOR] Updated BTC price to:', data.btc_price);
                    }
                    
                    console.log('[CALCULATOR] Network stats loaded');
                }
            })
            .catch(error => console.error('[CALCULATOR] Error loading network stats:', error));
    }
    
    // Load miners list
    function loadMiners() {
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
                        console.log('[CALCULATOR] Miners loaded:', data.miners.length);
                    }
                }
            })
            .catch(error => console.error('[CALCULATOR] Error loading miners:', error));
    }
    
    // Update totals calculation
    function updateTotals() {
        var hashrate = parseFloat(document.getElementById('hashrate').value) || 0;
        var power = parseFloat(document.getElementById('power-consumption').value) || 0;
        var minerCount = parseFloat(document.getElementById('miner-count').value) || 1;
        
        var totalHashrate = hashrate * minerCount;
        var totalPower = power * minerCount;
        
        // Update hidden fields
        document.getElementById('total-hashrate').value = totalHashrate.toFixed(2);
        document.getElementById('total-power').value = totalPower.toFixed(0);
        
        // Update display fields
        var displayHashrate = document.getElementById('total-hashrate-display');
        var displayPower = document.getElementById('total-power-display');
        
        if (displayHashrate) displayHashrate.value = totalHashrate.toFixed(2);
        if (displayPower) displayPower.value = totalPower.toFixed(0);
        
        // Update Site Power (MW) automatically
        var sitePowerField = document.getElementById('site-power-mw');
        if (sitePowerField && !sitePowerField.dataset.userEditing) {
            var sitePowerMW = (totalPower / 1000000).toFixed(3);
            sitePowerField.value = sitePowerMW;
        }
        
        console.log('[CALCULATOR] Totals updated:', totalHashrate.toFixed(2), 'TH/s,', totalPower, 'W,', (totalPower/1000000).toFixed(3), 'MW');
    }
    
    // Update miner count from site power
    function updateMinerCountFromSitePower() {
        var sitePowerMW = parseFloat(document.getElementById('site-power-mw').value) || 0;
        var power = parseFloat(document.getElementById('power-consumption').value) || 3250;
        
        if (sitePowerMW > 0 && power > 0) {
            var sitePowerWatts = sitePowerMW * 1000000;
            var calculatedMinerCount = Math.floor(sitePowerWatts / power);
            
            var minerCountField = document.getElementById('miner-count');
            if (minerCountField) {
                minerCountField.value = calculatedMinerCount;
                console.log('[CALCULATOR] Updated miner count from site power:', calculatedMinerCount);
                updateTotals();
            }
        }
    }
    
    // Handle miner selection
    var minerSelect = document.getElementById('miner-model');
    if (minerSelect) {
        minerSelect.addEventListener('change', function() {
            var selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.value) {
                var text = selectedOption.textContent;
                var hashrate = text.match(/(\d+(?:\.\d+)?)\s*TH\/s/);
                var power = text.match(/(\d+)\s*W/);
                
                if (hashrate && power) {
                    document.getElementById('hashrate').value = hashrate[1];
                    document.getElementById('power-consumption').value = power[1];
                    console.log('[CALCULATOR] Miner selected:', selectedOption.textContent);
                    updateTotals();
                }
            }
        });
    }
    
    // Watch for input changes
    ['hashrate', 'power-consumption', 'miner-count'].forEach(function(id) {
        var element = document.getElementById(id);
        if (element) {
            element.addEventListener('input', updateTotals);
        }
    });
    
    // Watch for Site Power changes
    var sitePowerField = document.getElementById('site-power-mw');
    if (sitePowerField) {
        sitePowerField.addEventListener('focus', function() {
            this.dataset.userEditing = 'true';
        });
        
        sitePowerField.addEventListener('input', function() {
            console.log('[CALCULATOR] Site Power changed to:', this.value, 'MW');
            updateMinerCountFromSitePower();
        });
        
        sitePowerField.addEventListener('blur', function() {
            setTimeout(() => {
                delete this.dataset.userEditing;
            }, 1000);
        });
    }
    
    // Handle form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        console.log('[CALCULATOR] Form submitted');
        
        updateTotals(); // Ensure totals are current
        
        // Show loading state
        var submitBtn = form.querySelector('button[type="submit"]');
        var originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Calculating...';
        
        var formData = new FormData(form);
        var data = {};
        for (var pair of formData.entries()) {
            data[pair[0]] = pair[1];
        }
        
        // 添加计算出的总值，确保正确传递
        data['total-hashrate'] = document.getElementById('total-hashrate').value || '0';
        data['total-power'] = document.getElementById('total-power').value || '0';
        data['miner-count'] = document.getElementById('miner-count').value || '1';
        
        console.log('[CALCULATOR] Final form data being sent:', data);
        
        console.log('[CALCULATOR] Sending data:', data);
        
        fetch('/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            console.log('[CALCULATOR] Result:', result);
            if (result.success !== false) {
                displayResults(result);
                var resultsCard = document.getElementById('results-card');
                if (resultsCard) resultsCard.style.display = 'block';
            } else {
                alert('Calculation error: ' + (result.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('[CALCULATOR] Error:', error);
            alert('Network error: ' + error.message);
        })
        .finally(function() {
            // Restore button state
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });
    });
    
    // Display results
    function displayResults(data) {
        console.log('[CALCULATOR] Displaying results, received data:', data);
        
        // BTC Mining Cards - 算法1和算法2
        if (data.btc_mined) {
            console.log('[CALCULATOR] btc_mined data found:', data.btc_mined);
            
            // 算法1 (Method 1)
            var method1Card = document.getElementById('btc-method1-daily-card');
            console.log('[CALCULATOR] method1Card element:', method1Card);
            if (method1Card && data.btc_mined.method1) {
                console.log('[CALCULATOR] Updating method1 with:', data.btc_mined.method1.daily);
                method1Card.textContent = data.btc_mined.method1.daily.toFixed(8);
                console.log('[CALCULATOR] method1Card after update:', method1Card.textContent);
            }
            
            // 算法2 (Method 2)
            var method2Card = document.getElementById('btc-method2-daily-card');
            console.log('[CALCULATOR] method2Card element:', method2Card);
            if (method2Card && data.btc_mined.method2) {
                console.log('[CALCULATOR] Updating method2 with:', data.btc_mined.method2.daily);
                method2Card.textContent = data.btc_mined.method2.daily.toFixed(8);
                console.log('[CALCULATOR] method2Card after update:', method2Card.textContent);
            }
            
            // 算法对比
            var diffElement = document.getElementById('algorithm-difference');
            if (diffElement && data.btc_mined.method1 && data.btc_mined.method2) {
                var diff = Math.abs(data.btc_mined.method1.daily - data.btc_mined.method2.daily);
                var percent = (diff / data.btc_mined.method1.daily * 100).toFixed(2);
                if (currentLang === 'en') {
                    diffElement.textContent = 'Difference: ' + percent + '%';
                } else {
                    diffElement.textContent = '差异: ' + percent + '%';
                }
            }
        }
        
        // Top Cards - 顶部卡片
        // Host Profit Card (矿场主月度收益)
        var hostProfitCard = document.getElementById('host-profit-card');
        if (hostProfitCard && data.profit && data.profit.host_monthly) {
            hostProfitCard.textContent = '$' + data.profit.host_monthly.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // Client Profit Card (客户月度收益)
        var clientProfitCard = document.getElementById('client-profit-card');
        console.log('[CALCULATOR] clientProfitCard element:', clientProfitCard);
        if (clientProfitCard && data.client_profit && data.client_profit.monthly) {
            console.log('[CALCULATOR] Updating client profit with:', data.client_profit.monthly);
            clientProfitCard.textContent = '$' + data.client_profit.monthly.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            console.log('[CALCULATOR] clientProfitCard after update:', clientProfitCard.textContent);
        }
        
        // Your Profit Information Table - 客户信息表格
        // Monthly BTC Output
        var monthlyBtc = document.getElementById('monthly-btc');
        if (monthlyBtc && data.btc_mined) {
            monthlyBtc.textContent = data.btc_mined.monthly.toFixed(8);
        }
        
        // Monthly Revenue
        var monthlyRevenue = document.getElementById('monthly-revenue');
        if (monthlyRevenue && data.revenue) {
            monthlyRevenue.textContent = '$' + data.revenue.monthly.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // Client Total Income
        var clientTotalIncome = document.getElementById('client-total-income');
        if (clientTotalIncome && data.revenue) {
            clientTotalIncome.textContent = '$' + data.revenue.monthly.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // Client Monthly Electricity
        var clientMonthlyElec = document.getElementById('client-monthly-electricity');
        if (clientMonthlyElec && data.client_electricity_cost) {
            clientMonthlyElec.textContent = '$' + data.client_electricity_cost.monthly.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // Client Total Expenses
        var clientTotalExpenses = document.getElementById('client-total-expenses');
        if (clientTotalExpenses && data.client_electricity_cost) {
            clientTotalExpenses.textContent = '$' + data.client_electricity_cost.monthly.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // Client Monthly/Yearly Profit
        var clientMonthlyProfit = document.getElementById('client-monthly-profit');
        if (clientMonthlyProfit && data.client_profit) {
            clientMonthlyProfit.textContent = '$' + data.client_profit.monthly.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        var clientYearlyProfit = document.getElementById('client-yearly-profit');
        if (clientYearlyProfit && data.client_profit) {
            clientYearlyProfit.textContent = '$' + data.client_profit.yearly.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // ROI Information
        var clientInvestmentAmount = document.getElementById('client-investment-amount');
        if (clientInvestmentAmount && data.inputs) {
            var investment = data.inputs.client_investment || 0;
            console.log('[CALCULATOR] Client investment:', investment);
            clientInvestmentAmount.textContent = '$' + investment.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        var clientAnnualRoi = document.getElementById('client-annual-roi');
        if (clientAnnualRoi && data.roi) {
            var roi = data.roi.client_annual_roi;
            console.log('[CALCULATOR] Client annual ROI:', roi);
            if (roi !== undefined && roi !== null && isFinite(roi)) {
                clientAnnualRoi.textContent = roi.toFixed(2) + '%';
            } else {
                clientAnnualRoi.textContent = '0.00%';
            }
        }
        
        var clientPaybackMonths = document.getElementById('client-payback-months');
        if (clientPaybackMonths && data.roi) {
            var months = data.roi.client_payback_months;
            console.log('[CALCULATOR] Client payback months:', months);
            if (months !== undefined && months !== null && isFinite(months) && months > 0) {
                clientPaybackMonths.textContent = months.toFixed(0) + ' months';
            } else {
                clientPaybackMonths.textContent = '0 months';
            }
        }
        
        var clientPaybackYears = document.getElementById('client-payback-years');
        if (clientPaybackYears && data.roi) {
            var years = data.roi.client_payback_years;
            console.log('[CALCULATOR] Client payback years:', years);
            if (years !== undefined && years !== null && isFinite(years) && years > 0) {
                clientPaybackYears.textContent = years.toFixed(2) + ' years';
            } else {
                clientPaybackYears.textContent = '0.00 years';
            }
        }
        
        // Additional Client Info
        var clientMinerCount = document.getElementById('client-miner-count');
        if (clientMinerCount && data.inputs) {
            clientMinerCount.textContent = data.inputs.miner_count || 0;
        }
        
        var clientRunningMiners = document.getElementById('client-running-miners');
        if (clientRunningMiners && data.curtailment_details) {
            clientRunningMiners.textContent = data.curtailment_details.running_miners || data.inputs.miner_count || 0;
        }
        
        var clientShutdownMiners = document.getElementById('client-shutdown-miners');
        if (clientShutdownMiners && data.curtailment_details) {
            clientShutdownMiners.textContent = data.curtailment_details.shutdown_miners || 0;
        }
        
        var clientBreakEvenElec = document.getElementById('client-break-even-electricity');
        if (clientBreakEvenElec && data.break_even) {
            clientBreakEvenElec.textContent = '$' + (data.break_even.electricity_cost || 0).toFixed(4) + '/kWh';
        }
        
        var clientBreakEvenBtc = document.getElementById('client-break-even-btc');
        if (clientBreakEvenBtc && data.break_even) {
            clientBreakEvenBtc.textContent = '$' + (data.break_even.btc_price || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // Mining Details
        var minerCountResult = document.getElementById('miner-count-result');
        if (minerCountResult && data.inputs) {
            minerCountResult.textContent = data.inputs.miner_count || 0;
        }
        
        var breakEvenElec = document.getElementById('break-even-electricity');
        if (breakEvenElec && data.break_even) {
            breakEvenElec.textContent = '$' + (data.break_even.electricity_cost || 0).toFixed(4) + '/kWh';
        }
        
        var breakEvenBtc = document.getElementById('break-even-btc');
        if (breakEvenBtc && data.break_even) {
            breakEvenBtc.textContent = '$' + (data.break_even.btc_price || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // Network and Mining Details Table
        var networkDifficulty = document.getElementById('network-difficulty-value');
        if (networkDifficulty && data.network_data) {
            networkDifficulty.textContent = (data.network_data.difficulty / 1e12).toFixed(1) + ' T';
        }
        
        var networkHashrate = document.getElementById('network-hashrate-value');
        if (networkHashrate && data.network_data) {
            networkHashrate.textContent = data.network_data.hashrate.toFixed(2) + ' EH/s';
        }
        
        var btcPriceResult = document.getElementById('current-btc-price-value');
        if (btcPriceResult && data.btc_price) {
            btcPriceResult.textContent = '$' + data.btc_price.toLocaleString('en-US');
        }
        
        var blockReward = document.getElementById('block-reward-value');
        if (blockReward && data.network_data) {
            blockReward.textContent = (data.network_data.block_reward || 3.125).toFixed(3) + ' BTC';
        }
        
        // Total Site Hashrate  
        var totalHashrate = document.getElementById('total-hashrate-result');
        if (totalHashrate && data.inputs) {
            totalHashrate.textContent = (data.inputs.effective_hashrate || 0).toLocaleString('en-US') + ' TH/s';
        }
        
        // BTC per TH daily
        var btcPerTh = document.getElementById('btc-per-th-daily');
        if (btcPerTh && data.btc_mined) {
            btcPerTh.textContent = (data.btc_mined.per_th_daily || 0).toFixed(8);
        }
        
        // Timestamp
        var timestamp = document.getElementById('results-timestamp');
        if (timestamp && data.timestamp) {
            timestamp.textContent = new Date(data.timestamp).toLocaleString();
        }
        
        console.log('[CALCULATOR] Results displayed');
    }
    
    // Initialize
    loadNetworkStats();
    loadMiners();
    
    // Set default values and calculate
    setTimeout(function() {
        var minerCountField = document.getElementById('miner-count');
        var powerField = document.getElementById('power-consumption');
        var hashrateField = document.getElementById('hashrate');
        
        if (minerCountField && !minerCountField.value) minerCountField.value = '1';
        if (powerField && !powerField.value) powerField.value = '3068';
        if (hashrateField && !hashrateField.value) hashrateField.value = '100';
        
        updateTotals();
        console.log('[CALCULATOR] Initialization complete');
    }, 500);
});