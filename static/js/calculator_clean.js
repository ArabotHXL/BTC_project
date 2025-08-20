// Bitcoin Mining Calculator - Restored Clean Version
document.addEventListener('DOMContentLoaded', function() {
    console.log('[CALCULATOR] Loading...');
    
    // Load enhanced heatmap script
    if (!window.createEnhancedHeatmap) {
        const script = document.createElement('script');
        script.src = '/static/js/enhanced_heatmap.js';
        document.head.appendChild(script);
    }
    
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
                    document.getElementById('block-reward').textContent = parseFloat(data.block_reward).toFixed(3) + ' BTC';
                    
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
                try {
                    displayResults(result);
                    var resultsCard = document.getElementById('results-card');
                    if (resultsCard) resultsCard.style.display = 'block';
                } catch (displayError) {
                    console.error('[CALCULATOR] Display error details:', {
                        message: displayError.message,
                        stack: displayError.stack,
                        name: displayError.name
                    });
                    alert('Display error: ' + displayError.message);
                }
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
                // Add defensive programming to prevent toFixed() error on NaN/Infinity
                var percent = 0;
                if (data.btc_mined.method1.daily > 0 && isFinite(diff) && isFinite(data.btc_mined.method1.daily)) {
                    percent = (diff / data.btc_mined.method1.daily * 100);
                    if (isFinite(percent)) {
                        percent = percent.toFixed(2);
                    } else {
                        percent = '0.00';
                    }
                } else {
                    percent = '0.00';
                }
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
        
        // Client ROI Information - 客户投资回报信息  
        var clientInvestmentAmount = document.getElementById('client-investment-amount');
        if (clientInvestmentAmount && data.inputs) {
            var investment = data.inputs.client_investment || 0;
            console.log('[CALCULATOR] Client investment:', investment);
            clientInvestmentAmount.textContent = '$' + investment.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        var clientAnnualRoi = document.getElementById('client-annual-roi');
        if (clientAnnualRoi) {
            // Check if ROI data exists and handle both structures
            var clientROI = null;
            if (data.roi && data.roi.client) {
                clientROI = data.roi.client;
            }
            
            if (clientROI && clientROI.roi_percent_annual !== null && clientROI.roi_percent_annual !== undefined && isFinite(clientROI.roi_percent_annual)) {
                var roi = clientROI.roi_percent_annual;
                console.log('[CALCULATOR] Client annual ROI:', roi);
                clientAnnualRoi.textContent = roi.toFixed(2) + '%';
            } else if (data.inputs && data.inputs.client_investment > 0) {
                // Calculate ROI manually if not provided
                if (data.client_profit && data.client_profit.yearly) {
                    var manualRoi = (data.client_profit.yearly / data.inputs.client_investment) * 100;
                    clientAnnualRoi.textContent = manualRoi.toFixed(2) + '%';
                } else {
                    clientAnnualRoi.textContent = '0.00%';
                }
            } else {
                clientAnnualRoi.textContent = 'N/A (No Investment)';
            }
        }
        
        var clientPaybackMonths = document.getElementById('client-payback-months');
        if (clientPaybackMonths) {
            // Check if ROI data exists and handle both structures
            var clientROI = null;
            if (data.roi && data.roi.client) {
                clientROI = data.roi.client;
            }
            
            if (clientROI && clientROI.payback_period_months !== null && clientROI.payback_period_months !== undefined && isFinite(clientROI.payback_period_months) && clientROI.payback_period_months > 0) {
                var months = clientROI.payback_period_months;
                console.log('[CALCULATOR] Client payback months:', months);
                clientPaybackMonths.textContent = months.toFixed(0) + ' months';
            } else if (data.inputs && data.inputs.client_investment > 0) {
                // Calculate payback manually if not provided
                if (data.client_profit && data.client_profit.monthly && data.client_profit.monthly > 0) {
                    var manualMonths = data.inputs.client_investment / data.client_profit.monthly;
                    clientPaybackMonths.textContent = manualMonths.toFixed(0) + ' months';
                } else {
                    clientPaybackMonths.textContent = 'N/A';
                }
            } else {
                clientPaybackMonths.textContent = 'N/A (No Investment)';
            }
        }
        
        var clientPaybackYears = document.getElementById('client-payback-years');
        if (clientPaybackYears) {
            // Check if ROI data exists and handle both structures
            var clientROI = null;
            if (data.roi && data.roi.client) {
                clientROI = data.roi.client;
            }
            
            if (clientROI && clientROI.payback_period_years !== null && clientROI.payback_period_years !== undefined && isFinite(clientROI.payback_period_years) && clientROI.payback_period_years > 0) {
                var years = clientROI.payback_period_years;
                console.log('[CALCULATOR] Client payback years:', years);
                clientPaybackYears.textContent = years.toFixed(2) + ' years';
            } else if (data.inputs && data.inputs.client_investment > 0) {
                // Calculate payback manually if not provided
                if (data.client_profit && data.client_profit.yearly && data.client_profit.yearly > 0) {
                    var manualYears = data.inputs.client_investment / data.client_profit.yearly;
                    clientPaybackYears.textContent = manualYears.toFixed(2) + ' years';
                } else {
                    clientPaybackYears.textContent = 'N/A';
                }
            } else {
                clientPaybackYears.textContent = 'N/A (No Investment)';
            }
        }

        // 月度ROI百分比
        var clientMonthlyRoi = document.getElementById('client-monthly-roi');
        if (clientMonthlyRoi && data.client_profit && data.inputs) {
            var monthlyReturn = (data.client_profit.monthly / data.inputs.client_investment) * 100;
            clientMonthlyRoi.textContent = monthlyReturn.toFixed(2) + '%';
        }

        // 盈亏平衡月份
        var clientBreakevenMonth = document.getElementById('client-breakeven-month');
        if (clientBreakevenMonth && data.roi && data.roi.client && data.roi.client.forecast) {
            var breakeven = data.roi.client.forecast.find(point => point.break_even === true);
            if (breakeven) {
                clientBreakevenMonth.textContent = 'Month ' + breakeven.month;
            } else {
                clientBreakevenMonth.textContent = 'Month ' + Math.ceil(data.roi.client.payback_period_months || 0);
            }
        }

        // Break Even Point详细信息
        if (data.roi && data.roi.client) {
            var forecast = data.roi.client.forecast || [];
            var breakeven = forecast.find(point => point.break_even === true);
            var paybackMonths = data.roi.client.payback_period_months || 0;
            var paybackYears = data.roi.client.payback_period_years || 0;
            
            console.log('[BREAK-EVEN] Analysis data:', {
                hasBreakeven: !!breakeven,
                paybackMonths: paybackMonths,
                paybackYears: paybackYears,
                forecastLength: forecast.length
            });
            
            // Break-even Month Display
            var breakevenMonthDisplay = document.getElementById('breakeven-month-display');
            if (breakevenMonthDisplay) {
                if (breakeven) {
                    breakevenMonthDisplay.textContent = 'Month ' + breakeven.month;
                } else if (paybackMonths && paybackMonths !== Infinity) {
                    breakevenMonthDisplay.textContent = 'Month ' + Math.ceil(paybackMonths);
                } else {
                    breakevenMonthDisplay.textContent = 'N/A';
                }
            }
            
            // Cumulative Investment Recovery
            var breakevenRecoveryAmount = document.getElementById('breakeven-recovery-amount');
            if (breakevenRecoveryAmount) {
                if (breakeven) {
                    breakevenRecoveryAmount.textContent = '$' + breakeven.cumulative_profit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                } else {
                    // 从data中获取客户投资金额，而不是DOM元素
                    var clientInvestment = (data.inputs && data.inputs.client_investment) || 0;
                    breakevenRecoveryAmount.textContent = '$' + clientInvestment.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                }
            }
            
            // Break-even ROI Percentage
            var breakevenRoiPercent = document.getElementById('breakeven-roi-percent');
            if (breakevenRoiPercent) {
                if (breakeven) {
                    breakevenRoiPercent.textContent = breakeven.roi_percent.toFixed(2) + '%';
                } else if (paybackMonths && paybackMonths !== Infinity) {
                    // 计算盈亏平衡时的ROI%: 100% (完全回收投资)
                    breakevenRoiPercent.textContent = '100.00%';
                } else {
                    breakevenRoiPercent.textContent = 'N/A';
                }
            }
            
            // Time to Break-even
            var breakevenTimeDisplay = document.getElementById('breakeven-time-display');
            if (breakevenTimeDisplay) {
                if (paybackYears && paybackYears !== Infinity) {
                    breakevenTimeDisplay.textContent = paybackYears.toFixed(1) + ' years';
                } else {
                    breakevenTimeDisplay.textContent = 'N/A';
                }
            }
        }

        // 6个月、12个月、24个月、36个月的利润和ROI
        if (data.roi && data.roi.client && data.roi.client.forecast) {
            var forecast = data.roi.client.forecast;
            
            // 6个月
            var month6 = forecast.find(p => p.month === 6);
            if (month6) {
                var elem6Profit = document.getElementById('client-6month-profit');
                var elem6Roi = document.getElementById('client-6month-roi');
                if (elem6Profit) elem6Profit.textContent = '$' + month6.cumulative_profit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                if (elem6Roi) elem6Roi.textContent = month6.roi_percent.toFixed(2) + '%';
            }
            
            // 12个月
            var month12 = forecast.find(p => p.month === 12);
            if (month12) {
                var elem12Profit = document.getElementById('client-12month-profit');
                var elem12Roi = document.getElementById('client-12month-roi');
                if (elem12Profit) elem12Profit.textContent = '$' + month12.cumulative_profit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                if (elem12Roi) elem12Roi.textContent = month12.roi_percent.toFixed(2) + '%';
            }
            
            // 24个月
            var month24 = forecast.find(p => p.month === 24);
            if (month24) {
                var elem24Profit = document.getElementById('client-24month-profit');
                var elem24Roi = document.getElementById('client-24month-roi');
                if (elem24Profit) elem24Profit.textContent = '$' + month24.cumulative_profit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                if (elem24Roi) elem24Roi.textContent = month24.roi_percent.toFixed(2) + '%';
            }
            
            // 36个月
            var month36 = forecast.find(p => p.month === 36);
            if (month36) {
                var elem36Profit = document.getElementById('client-36month-profit');
                var elem36Roi = document.getElementById('client-36month-roi');
                if (elem36Profit) elem36Profit.textContent = '$' + month36.cumulative_profit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                if (elem36Roi) elem36Roi.textContent = month36.roi_percent.toFixed(2) + '%';
            }
        }

        // 风险分析和敏感性分析
        if (data.inputs && data.client_profit) {
            // 电价敏感性分析 - 电价上涨10%对年度利润的影响
            var electricityImpact = document.getElementById('electricity-impact-profit');
            if (electricityImpact && data.inputs.client_electricity_cost) {
                var currentElectricityCost = data.inputs.client_electricity_cost;
                var newElectricityCost = currentElectricityCost * 1.1; // 上涨10%
                var costIncrease = newElectricityCost - currentElectricityCost;
                var annualPowerConsumption = (data.inputs.total_power || 0) / 1000 * 24 * 365; // kWh per year
                var annualImpact = costIncrease * annualPowerConsumption;
                electricityImpact.textContent = '-$' + annualImpact.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
            }

            // BTC价格敏感性分析 - BTC价格下跌20%对年度利润的影响
            var btcImpact = document.getElementById('btc-impact-profit');
            if (btcImpact && data.btc_mined && data.btc_price) {
                var currentBtcPrice = data.btc_price;
                var newBtcPrice = currentBtcPrice * 0.8; // 下跌20%
                var priceDecrease = currentBtcPrice - newBtcPrice; // 价格差
                var annualBtcOutput = data.btc_mined.yearly || 0; // 年度BTC产出
                var annualImpact = priceDecrease * annualBtcOutput; // 年度损失 = 价格差 × 年产量
                
                // 显示详细计算信息
                console.log('[SENSITIVITY] BTC Price Sensitivity Calculation:');
                console.log('[SENSITIVITY] Current BTC Price: $' + currentBtcPrice.toLocaleString());
                console.log('[SENSITIVITY] New BTC Price (-20%): $' + newBtcPrice.toLocaleString());
                console.log('[SENSITIVITY] Price Decrease: $' + priceDecrease.toLocaleString());
                console.log('[SENSITIVITY] Annual BTC Output: ' + annualBtcOutput.toFixed(3) + ' BTC');
                console.log('[SENSITIVITY] Annual Impact: -$' + annualImpact.toLocaleString());
                
                btcImpact.textContent = '-$' + annualImpact.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
            }

            // 安全边际计算
            var safetyMargin = document.getElementById('safety-margin');
            if (safetyMargin && data.client_profit && data.break_even) {
                var currentProfit = data.client_profit.monthly || 0;
                var breakEvenElectricity = data.break_even.electricity_cost || 0;
                var currentElectricity = data.inputs.client_electricity_cost || 0;
                
                if (currentElectricity > 0 && breakEvenElectricity > 0) {
                    var margin = ((breakEvenElectricity - currentElectricity) / currentElectricity) * 100;
                    safetyMargin.textContent = margin.toFixed(1) + '%';
                } else {
                    safetyMargin.textContent = 'N/A';
                }
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
            // Try multiple possible field names for difficulty
            var difficulty = data.network_data.difficulty || data.network_data.network_difficulty;
            if (difficulty !== undefined && difficulty !== null) {
                networkDifficulty.textContent = (difficulty / 1e12).toFixed(1) + ' T';
            }
        }
        
        var networkHashrate = document.getElementById('network-hashrate-value');
        if (networkHashrate && data.network_data) {
            // Try multiple possible field names for hashrate
            var hashrate = data.network_data.hashrate || data.network_data.network_hashrate;
            if (hashrate !== undefined && hashrate !== null) {
                networkHashrate.textContent = hashrate.toFixed(2) + ' EH/s';
            }
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
        
        // Daily BTC Total
        var dailyBtcValue = document.getElementById('daily-btc-value');
        if (dailyBtcValue && data.btc_mined) {
            dailyBtcValue.textContent = (data.btc_mined.daily || 0).toFixed(8);
        }
        
        // Algorithm 1 - Method 1 Daily BTC
        var btcMethod1Daily = document.getElementById('btc-method1-daily');
        if (btcMethod1Daily && data.btc_mined && data.btc_mined.method1) {
            btcMethod1Daily.textContent = (data.btc_mined.method1.daily || 0).toFixed(8);
        }
        
        // Algorithm 2 - Method 2 Daily BTC
        var btcMethod2Daily = document.getElementById('btc-method2-daily');
        if (btcMethod2Daily && data.btc_mined && data.btc_mined.method2) {
            btcMethod2Daily.textContent = (data.btc_mined.method2.daily || 0).toFixed(8);
        }
        
        // Optimal Electricity Rate (Break-even electricity cost)
        var optimalElectricityRate = document.getElementById('optimal-electricity-rate');
        if (optimalElectricityRate && data.break_even) {
            optimalElectricityRate.textContent = '$' + (data.break_even.electricity_cost || 0).toFixed(4) + '/kWh';
        }
        
        // Timestamp
        var timestamp = document.getElementById('results-timestamp');
        if (timestamp && data.timestamp) {
            timestamp.textContent = new Date(data.timestamp).toLocaleString();
        }
        
        console.log('[CALCULATOR] Results displayed');
        
        // Generate ROI Charts if chart functionality is available
        if (typeof generateRoiCharts === 'function') {
            console.log('[CALCULATOR] Generating ROI charts...');
            generateRoiCharts(data);
        }
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