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
        
        var fields = {
            'daily-btc-mined': data.btc_mined || data.daily_btc_mined || data.daily_btc,
            'monthly-btc-mined': data.monthly_btc_mined || (data.daily_btc * 30),
            'yearly-btc-mined': data.yearly_btc_mined || (data.daily_btc * 365),
            'daily-revenue': data.daily_revenue_usd || data.daily_revenue,
            'monthly-revenue': data.monthly_revenue_usd || data.monthly_revenue,
            'yearly-revenue': data.yearly_revenue_usd || data.yearly_revenue,
            'daily-electricity-cost': data.daily_electricity_cost_usd || data.daily_electricity_cost,
            'monthly-electricity-cost': data.monthly_electricity_cost_usd || data.monthly_electricity_cost,
            'yearly-electricity-cost': data.yearly_electricity_cost_usd || data.yearly_electricity_cost,
            'daily-profit': data.daily_profit_usd || data.daily_profit,
            'monthly-profit': data.monthly_profit_usd || data.monthly_profit,
            'yearly-profit': data.yearly_profit_usd || data.yearly_profit,
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