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
                document.getElementById('btc-price').textContent = '$' + data.btc_price.toLocaleString();
                document.getElementById('network-difficulty').textContent = (data.network_difficulty / 1e12).toFixed(2) + 'T';
                document.getElementById('network-hashrate').textContent = data.network_hashrate + ' EH/s';
                document.getElementById('block-reward').textContent = data.block_reward + ' BTC';
                console.log('[CALCULATOR.JS] Network stats loaded');
            }
        })
        .catch(error => console.error('[CALCULATOR.JS] Error loading network stats:', error));
    
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
                    updateTotals();
                }
            }
        });
    }
    
    // Update totals
    function updateTotals() {
        var hashrate = parseFloat(document.getElementById('hashrate').value) || 0;
        var power = parseFloat(document.getElementById('power-consumption').value) || 0;
        var minerCount = parseFloat(document.getElementById('miner-count').value) || 1;
        
        var totalHashrate = hashrate * minerCount;
        var totalPower = power * minerCount;
        
        document.getElementById('total-hashrate').value = totalHashrate;
        document.getElementById('total-power').value = totalPower;
        document.getElementById('total-hashrate-display').value = totalHashrate.toFixed(2) + ' TH/s';
        document.getElementById('total-power-display').value = (totalPower / 1000).toFixed(2) + ' kW';
        
        console.log('[CALCULATOR.JS] Totals updated:', totalHashrate, 'TH/s,', totalPower, 'W');
    }
    
    // Watch for changes
    ['hashrate', 'power-consumption', 'miner-count'].forEach(function(id) {
        var element = document.getElementById(id);
        if (element) {
            element.addEventListener('input', updateTotals);
        }
    });
    
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
        fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
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