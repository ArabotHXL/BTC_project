// Bitcoin Mining Calculator - Main JavaScript
document.addEventListener('DOMContentLoaded', () => {
    // Elements for network stats
    const btcPriceEl = document.getElementById('btc-price');
    const networkDifficultyEl = document.getElementById('network-difficulty');
    const blockRewardEl = document.getElementById('block-reward');
    
    // Form elements
    const minerModelSelect = document.getElementById('miner-model');
    const sitePowerMwInput = document.getElementById('site-power-mw');
    const minerCountInput = document.getElementById('miner-count');
    const hashrateInput = document.getElementById('hashrate');
    const hashrateUnitSelect = document.getElementById('hashrate-unit');
    const powerConsumptionInput = document.getElementById('power-consumption');
    const electricityCostInput = document.getElementById('electricity-cost');
    const clientElectricityCostInput = document.getElementById('client-electricity-cost');
    const btcPriceInput = document.getElementById('btc-price-input');
    const useRealTimeCheckbox = document.getElementById('use-real-time');
    const calculatorForm = document.getElementById('mining-calculator-form');
    
    // Results elements
    const resultsCard = document.getElementById('results-card');
    const chartCard = document.getElementById('chart-card');
    const resultsTimestamp = document.getElementById('results-timestamp');
    const btcMinedDailyEl = document.getElementById('btc-mined-daily');
    const dailyProfitEl = document.getElementById('daily-profit');
    const monthlyProfitEl = document.getElementById('monthly-profit');
    const yearlyProfitEl = document.getElementById('yearly-profit');
    const monthlyBtcEl = document.getElementById('monthly-btc');
    const monthlyRevenueEl = document.getElementById('monthly-revenue');
    const monthlyElectricityEl = document.getElementById('monthly-electricity');
    const breakEvenElectricityEl = document.getElementById('break-even-electricity');
    const optimalCurtailmentEl = document.getElementById('optimal-curtailment');
    const clientMonthlyProfitEl = document.getElementById('client-monthly-profit');
    const minerCountResultEl = document.getElementById('miner-count-result');
    
    // Chart element
    const profitHeatmapCanvas = document.getElementById('profit-heatmap');
    let profitHeatmapChart = null;
    
    // Load initial network stats
    fetchNetworkStats();
    
    // Load miner models
    fetchMiners();
    
    // Set up event listeners
    useRealTimeCheckbox.addEventListener('change', handleRealTimeToggle);
    minerModelSelect.addEventListener('change', updateMinerSpecs);
    sitePowerMwInput.addEventListener('change', updateMinerSpecs);
    calculatorForm.addEventListener('submit', handleCalculateSubmit);
    
    // Update BTC price input when real-time checkbox is toggled
    function handleRealTimeToggle() {
        if (useRealTimeCheckbox.checked) {
            btcPriceInput.disabled = true;
            btcPriceInput.value = btcPriceEl.textContent.replace('$', '').trim();
        } else {
            btcPriceInput.disabled = false;
        }
    }
    
    // Update hashrate and power consumption based on miner model and site power
    function updateMinerSpecs() {
        const selectedModel = minerModelSelect.value;
        const sitePowerMW = parseFloat(sitePowerMwInput.value) || 1;
        
        if (selectedModel) {
            // Find the selected miner in the loaded miners data
            const miners = JSON.parse(localStorage.getItem('miners') || '[]');
            const selectedMiner = miners.find(miner => miner.name === selectedModel);
            
            if (selectedMiner) {
                // Calculate miner count based on site power (MW) and miner power (W)
                // Convert site power from MW to W: sitePowerMW * 1,000,000
                // Calculate how many miners can fit into that power budget
                const singleMinerPower = selectedMiner.power_watt;
                const calculatedMinerCount = Math.floor((sitePowerMW * 1000000) / singleMinerPower);
                
                // Update the miner count field
                minerCountInput.value = calculatedMinerCount;
                
                // Calculate total hashrate and power based on calculated miner count
                const totalHashrate = selectedMiner.hashrate * calculatedMinerCount;
                const totalPower = selectedMiner.power_watt * calculatedMinerCount;
                
                // Convert hashrate to appropriate unit
                let displayHashrate = totalHashrate;
                let displayUnit = 'TH/s';
                
                if (totalHashrate >= 1000000) {
                    displayHashrate = totalHashrate / 1000000;
                    displayUnit = 'EH/s';
                } else if (totalHashrate >= 1000) {
                    displayHashrate = totalHashrate / 1000;
                    displayUnit = 'PH/s';
                }
                
                // Update the form inputs
                hashrateInput.value = displayHashrate.toFixed(2);
                hashrateUnitSelect.value = displayUnit;
                powerConsumptionInput.value = totalPower.toFixed(0);
                
                // Disable hashrate and power inputs when using a miner model
                hashrateInput.disabled = true;
                hashrateUnitSelect.disabled = true;
                powerConsumptionInput.disabled = true;
                
                console.log(`Calculated ${calculatedMinerCount} miners for ${sitePowerMW} MW using ${selectedMiner.name}`);
            }
        } else {
            // Enable manual input when no miner model is selected
            hashrateInput.disabled = false;
            hashrateUnitSelect.disabled = false;
            powerConsumptionInput.disabled = false;
        }
    }
    
    // Handle form submission for calculation
    async function handleCalculateSubmit(event) {
        event.preventDefault();
        
        // Show loading state
        setLoadingState(true);
        
        try {
            // Collect form data
            const formData = new FormData(calculatorForm);
            
            // Send request to calculate endpoint
            const response = await fetch('/calculate', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Display results
                displayResults(data);
                
                // Generate and display chart
                if (minerModelSelect.value) {
                    const clientElectricityCost = parseFloat(clientElectricityInput.value) || 0;
                    generateProfitChart(minerModelSelect.value, parseInt(minerCountInput.value) || 1, clientElectricityCost);
                }
            } else {
                showError(data.error || 'An error occurred during calculation.');
            }
        } catch (error) {
            console.error('Calculation error:', error);
            showError('Failed to calculate mining profitability. Please try again.');
        } finally {
            // Hide loading state
            setLoadingState(false);
        }
    }
    
    // Fetch current Bitcoin network statistics
    async function fetchNetworkStats() {
        try {
            const response = await fetch('/network_stats');
            const data = await response.json();
            
            if (data.success) {
                // Update the UI with network stats
                btcPriceEl.textContent = formatCurrency(data.price);
                networkDifficultyEl.textContent = formatNumber(data.difficulty) + 'T';
                blockRewardEl.textContent = formatNumber(data.block_reward) + ' BTC';
                
                // Update the BTC price input as well if real-time is checked
                if (useRealTimeCheckbox.checked) {
                    btcPriceInput.value = data.price.toFixed(2);
                    btcPriceInput.disabled = true;
                }
            }
        } catch (error) {
            console.error('Failed to fetch network stats:', error);
        }
    }
    
    // Fetch available miner models
    async function fetchMiners() {
        try {
            const response = await fetch('/miners');
            const data = await response.json();
            
            if (data.success && data.miners) {
                // Store miners data in localStorage for later use
                localStorage.setItem('miners', JSON.stringify(data.miners));
                
                // Clear existing options
                minerModelSelect.innerHTML = '<option value="">Select a miner model</option>';
                
                // Add miner options to the select
                data.miners.forEach(miner => {
                    const option = document.createElement('option');
                    option.value = miner.name;
                    option.textContent = `${miner.name} (${miner.hashrate} TH/s, ${miner.power_watt}W)`;
                    minerModelSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to fetch miners:', error);
        }
    }
    
    // Display calculation results
    function displayResults(data) {
        // Show results card
        resultsCard.style.display = 'block';
        
        // Format and display the timestamp
        const timestamp = new Date(data.timestamp);
        resultsTimestamp.textContent = `Calculated at ${timestamp.toLocaleString()}`;
        
        // Update results values
        btcMinedDailyEl.textContent = formatNumber(data.btc_mined.daily, 8);
        dailyProfitEl.textContent = formatCurrency(data.profit.daily);
        monthlyProfitEl.textContent = formatCurrency(data.profit.monthly);
        yearlyProfitEl.textContent = formatCurrency(data.profit.yearly);
        monthlyBtcEl.textContent = formatNumber(data.btc_mined.monthly, 8);
        monthlyRevenueEl.textContent = formatCurrency(data.revenue.monthly);
        monthlyElectricityEl.textContent = formatCurrency(data.electricity_cost.monthly);
        breakEvenElectricityEl.textContent = formatCurrency(data.break_even.electricity_cost) + '/kWh';
        optimalCurtailmentEl.textContent = formatNumber(data.optimization.optimal_curtailment, 2) + '%';
        
        // Update client profit and miner count
        if (data.client_profit) {
            clientMonthlyProfitEl.textContent = formatCurrency(data.client_profit.monthly);
        }
        
        if (data.inputs.miner_count) {
            minerCountResultEl.textContent = data.inputs.miner_count.toLocaleString();
        }
        
        // Color the profit values based on whether they're positive or negative
        [dailyProfitEl, monthlyProfitEl, yearlyProfitEl].forEach(el => {
            if (parseFloat(el.textContent.replace(/[^0-9.-]+/g, '')) >= 0) {
                el.classList.add('profit-positive');
                el.classList.remove('profit-negative');
            } else {
                el.classList.add('profit-negative');
                el.classList.remove('profit-positive');
            }
        });
    }
    
    // Generate profit heatmap chart
    async function generateProfitChart(minerModel, minerCount) {
        try {
            // Create form data with miner model and count
            const formData = new FormData();
            formData.append('miner_model', minerModel);
            formData.append('miner_count', minerCount);
            
            // Fetch chart data
            const response = await fetch('/profit_chart_data', {
                method: 'POST',
                body: formData
            });
            
            const chartData = await response.json();
            
            if (chartData.success) {
                // Show chart card
                chartCard.style.display = 'block';
                
                // Process data for heatmap
                const profitData = chartData.profit_data;
                
                // Get unique BTC prices and electricity costs
                const btcPrices = [...new Set(profitData.map(item => item.btc_price))];
                const electricityCosts = [...new Set(profitData.map(item => item.electricity_cost))];
                
                // Create a 2D array for heatmap data
                const profitValues = [];
                btcPrices.forEach(price => {
                    const row = [];
                    electricityCosts.forEach(cost => {
                        const item = profitData.find(data => data.btc_price === price && data.electricity_cost === cost);
                        row.push(item ? item.monthly_profit : 0);
                    });
                    profitValues.push(row);
                });
                
                // Destroy previous chart if it exists
                if (profitHeatmapChart) {
                    profitHeatmapChart.destroy();
                }
                
                // Create new chart
                profitHeatmapChart = new Chart(profitHeatmapCanvas, {
                    type: 'heatmap',
                    data: {
                        datasets: [{
                            label: 'Monthly Profit ($)',
                            data: profitData.map(item => ({
                                x: '$' + item.electricity_cost.toFixed(2) + '/kWh',
                                y: '$' + item.btc_price.toFixed(0),
                                v: item.monthly_profit
                            })),
                            backgroundColor: ({ raw }) => {
                                // Color based on profit value
                                if (raw?.v < 0) return 'rgba(220, 53, 69, 0.8)'; // Negative: red
                                const intensity = Math.min(1, raw?.v / 10000); // Normalize between 0 and 1
                                return `rgba(25, 135, 84, ${intensity})`;  // Positive: green with intensity
                            },
                            borderWidth: 1,
                            borderColor: 'rgba(0, 0, 0, 0.2)'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: 'Electricity Cost ($/kWh)'
                                }
                            },
                            y: {
                                title: {
                                    display: true,
                                    text: 'Bitcoin Price ($)'
                                }
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    title: (items) => {
                                        const item = items[0];
                                        return `BTC Price: ${item.label}`;
                                    },
                                    label: (item) => {
                                        const electricity = item.dataset.data[item.dataIndex].x;
                                        const profit = formatCurrency(item.dataset.data[item.dataIndex].v);
                                        return [`Electricity: ${electricity}`, `Monthly Profit: ${profit}`];
                                    }
                                }
                            },
                            legend: {
                                display: false
                            },
                            title: {
                                display: true,
                                text: [
                                    'Profitability Heatmap',
                                    `Current BTC Price: ${formatCurrency(chartData.current_network_data.btc_price)}, Optimal Electricity Rate: ${formatCurrency(chartData.optimal_electricity_rate)}/kWh`
                                ]
                            }
                        },
                        animation: {
                            duration: 500
                        }
                    }
                });
                
                // Add annotation line for optimal electricity rate
                const optimalRateIndex = electricityCosts.findIndex(cost => 
                    Math.abs(cost - chartData.optimal_electricity_rate) === 
                    Math.min(...electricityCosts.map(c => Math.abs(c - chartData.optimal_electricity_rate)))
                );
                
                if (optimalRateIndex >= 0) {
                    // Add annotation in the future if needed
                }
            }
        } catch (error) {
            console.error('Failed to generate profit chart:', error);
        }
    }
    
    // Helper function to show loading state
    function setLoadingState(isLoading) {
        const submitButton = calculatorForm.querySelector('button[type="submit"]');
        
        if (isLoading) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="loading-spinner me-2"></span> Calculating...';
        } else {
            submitButton.disabled = false;
            submitButton.textContent = 'Calculate Profitability';
        }
    }
    
    // Helper function to show error
    function showError(message) {
        alert(message);
    }
    
    // Helper function to format currency
    function formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }
    
    // Helper function to format numbers
    function formatNumber(value, decimals = 2) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(value);
    }
    
    // Run initial UI setup
    handleRealTimeToggle();
});