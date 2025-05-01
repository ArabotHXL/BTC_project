// Bitcoin Mining Calculator - Main JavaScript
document.addEventListener('DOMContentLoaded', () => {
    // Elements for network stats
    const btcPriceEl = document.getElementById('btc-price');
    const networkDifficultyEl = document.getElementById('network-difficulty');
    const networkHashrateEl = document.getElementById('network-hashrate');
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
    
    // 客户相关元素 (Customer-related elements)
    const clientMonthlyProfitEl = document.getElementById('client-monthly-profit');
    const clientYearlyProfitEl = document.getElementById('client-yearly-profit');
    const hostMonthlyProfitEl = document.getElementById('host-monthly-profit');
    const clientMonthlyRevenueEl = document.getElementById('client-monthly-revenue');
    const clientMonthlyElectricityEl = document.getElementById('client-monthly-electricity');
    const clientBreakEvenElectricityEl = document.getElementById('client-break-even-electricity');
    const clientBreakEvenBtcEl = document.getElementById('client-break-even-btc');
    
    // 通用和网络相关元素 (Common and network-related elements)
    const breakEvenBtcEl = document.getElementById('break-even-btc');
    const networkDifficultyValueEl = document.getElementById('network-difficulty-value');
    const networkHashrateValueEl = document.getElementById('network-hashrate-value');
    const btcPerThDailyEl = document.getElementById('btc-per-th-daily');
    const currentBtcPriceValueEl = document.getElementById('current-btc-price-value');
    const blockRewardValueEl = document.getElementById('block-reward-value');
    const dailyBtcValueEl = document.getElementById('daily-btc-value');
    const optimalElectricityRateEl = document.getElementById('optimal-electricity-rate');
    const minerCountResultEl = document.getElementById('miner-count-result');
    const totalHashrateResultEl = document.getElementById('total-hashrate-result');
    
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
            // 安全获取BTC价格，避免null错误
            if (btcPriceEl && btcPriceEl.textContent) {
                btcPriceInput.value = btcPriceEl.textContent.replace('$', '').trim();
            } else {
                // 如果尚未加载价格，则使用默认或从localStorage获取
                const lastBtcPrice = localStorage.getItem('last_btc_price');
                btcPriceInput.value = lastBtcPrice ? parseFloat(lastBtcPrice).toFixed(2) : "90000.00";
            }
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
                // Formula from original code: site_miner_count = int((site_power_mw * 1000) / (power_watt / 1000))
                // Convert megawatts to kilowatts, and watts to kilowatts, then divide
                const singleMinerPower = selectedMiner.power_watt;
                const calculatedMinerCount = Math.floor((sitePowerMW * 1000) / (singleMinerPower / 1000));
                
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
        
        // Validate inputs before submission
        let hasErrors = false;
        
        // Basic input validation
        if (minerModelSelect.value === "") {
            // If no miner model is selected, validate manual inputs
            if (!hashrateInput.value || parseFloat(hashrateInput.value) <= 0) {
                showError('Please enter a valid hashrate greater than 0.');
                hasErrors = true;
            }
            
            if (!powerConsumptionInput.value || parseFloat(powerConsumptionInput.value) <= 0) {
                showError('Please enter a valid power consumption greater than 0.');
                hasErrors = true;
            }
        }
        
        if (!electricityCostInput.value || parseFloat(electricityCostInput.value) < 0) {
            showError('Please enter a valid electricity cost (must be 0 or greater).');
            hasErrors = true;
        }
        
        if (!useRealTimeCheckbox.checked && (!btcPriceInput.value || parseFloat(btcPriceInput.value) <= 0)) {
            showError('Please enter a valid Bitcoin price greater than 0.');
            hasErrors = true;
        }
        
        if (hasErrors) {
            return;
        }
        
        // Show loading state
        setLoadingState(true);
        
        try {
            // Collect form data
            const formData = new FormData(calculatorForm);
            
            // Log the calculation request for debugging
            console.log('Calculation request:');
            for (const [key, value] of formData.entries()) {
                console.log(`${key}: ${value}`);
            }
            
            // Send request to calculate endpoint
            const response = await fetch('/calculate', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Display results
                displayResults(data);
                
                // Generate and display chart
                if (minerModelSelect.value) {
                    const clientElectricityCost = parseFloat(clientElectricityCostInput.value) || 0;
                    generateProfitChart(minerModelSelect.value, parseInt(minerCountInput.value) || 1, clientElectricityCost);
                }
            } else {
                showError(data.error || 'An error occurred during calculation.');
                console.error('Server returned error:', data.error);
            }
        } catch (error) {
            console.error('Calculation error:', error);
            showError('Failed to calculate mining profitability. Please try again.' + 
                     (error.message ? ` (${error.message})` : ''));
        } finally {
            // Hide loading state
            setLoadingState(false);
        }
    }
    
    // Fetch current Bitcoin network statistics
    async function fetchNetworkStats() {
        // Create loading indicators for network stats
        const networkStatsElements = [btcPriceEl, networkDifficultyEl, networkHashrateEl, blockRewardEl];
        networkStatsElements.forEach(el => {
            el.innerHTML = '<small class="text-muted">Loading...</small>';
        });
        
        try {
            const response = await fetch('/network_stats', { timeout: 10000 });
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Update the UI with network stats
                btcPriceEl.textContent = formatCurrency(data.price);
                networkDifficultyEl.textContent = formatNumber(data.difficulty) + 'T';
                networkHashrateEl.textContent = formatNumber(data.hashrate) + ' EH/s';
                blockRewardEl.textContent = formatNumber(data.block_reward) + ' BTC';
                
                // Update the BTC price input as well if real-time is checked
                if (useRealTimeCheckbox.checked) {
                    btcPriceInput.value = data.price.toFixed(2);
                    btcPriceInput.disabled = true;
                }
                
                // Store successful values in localStorage as fallback for future failures
                localStorage.setItem('last_btc_price', data.price);
                localStorage.setItem('last_network_difficulty', data.difficulty);
                localStorage.setItem('last_network_hashrate', data.hashrate);
                localStorage.setItem('last_block_reward', data.block_reward);
            } else {
                // Use fallback values from localStorage if available, otherwise show error
                useFallbackNetworkStats();
                console.error('Server returned error when fetching network stats:', data.error);
            }
        } catch (error) {
            console.error('Failed to fetch network stats:', error);
            // Use fallback values from localStorage if available
            useFallbackNetworkStats();
            
            // Retry after 30 seconds
            setTimeout(fetchNetworkStats, 30000);
        }
    }
    
    // Helper function to use fallback network stats
    function useFallbackNetworkStats() {
        // Check if we have values in localStorage
        const lastBtcPrice = localStorage.getItem('last_btc_price');
        const lastDifficulty = localStorage.getItem('last_network_difficulty');
        const lastHashrate = localStorage.getItem('last_network_hashrate');
        const lastBlockReward = localStorage.getItem('last_block_reward');
        
        // Use last known values if available
        if (lastBtcPrice) {
            btcPriceEl.textContent = formatCurrency(parseFloat(lastBtcPrice));
            if (useRealTimeCheckbox.checked) {
                btcPriceInput.value = parseFloat(lastBtcPrice).toFixed(2);
                btcPriceInput.disabled = true;
            }
        } else {
            btcPriceEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
        }
        
        if (lastDifficulty) {
            networkDifficultyEl.textContent = formatNumber(parseFloat(lastDifficulty)) + 'T';
        } else {
            networkDifficultyEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
        }
        
        if (lastHashrate) {
            networkHashrateEl.textContent = formatNumber(parseFloat(lastHashrate)) + ' EH/s';
        } else {
            networkHashrateEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
        }
        
        if (lastBlockReward) {
            blockRewardEl.textContent = formatNumber(parseFloat(lastBlockReward), 3) + ' BTC';
        } else {
            blockRewardEl.innerHTML = '<small class="text-danger">数据获取失败 / Data fetch failed</small>';
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
        // 添加安全检查，确保所有需要的数据都存在
        if (!data || !data.btc_mined || !data.profit) {
            showError('Invalid data received from server. Missing required fields.');
            console.error('Invalid data structure:', data);
            return;
        }
        
        try {
            // Show results card
            if (resultsCard) resultsCard.style.display = 'block';
            
            // Format and display the timestamp
            const timestamp = new Date(data.timestamp);
            if (resultsTimestamp) resultsTimestamp.textContent = `Calculated at ${timestamp.toLocaleString()}`;
            
            // ===== 更新主要显示数据 (Update main display data) =====
            if (btcMinedDailyEl) btcMinedDailyEl.textContent = formatNumber(data.btc_mined.daily, 8);
            if (dailyProfitEl) dailyProfitEl.textContent = formatCurrency(data.profit.daily);
            if (monthlyProfitEl) monthlyProfitEl.textContent = formatCurrency(data.profit.monthly);
        
        // ===== 更新矿场主相关信息 (Update mining site/host information) =====
        
        // 设置年度/月度/日度收益和产出 (Set yearly/monthly/daily profit and output)
        const hostYearlyProfitEl = document.getElementById('host-yearly-profit');
        const hostMonthlyProfitDisplayEl = document.getElementById('host-monthly-profit-display');
        
        if (hostYearlyProfitEl) hostYearlyProfitEl.textContent = formatCurrency(data.profit.yearly);
        if (hostMonthlyProfitDisplayEl) hostMonthlyProfitDisplayEl.textContent = formatCurrency(data.profit.monthly);
        if (monthlyBtcEl) monthlyBtcEl.textContent = formatNumber(data.btc_mined.monthly, 8);
        if (monthlyRevenueEl) monthlyRevenueEl.textContent = formatCurrency(data.revenue.monthly);
        if (monthlyElectricityEl) monthlyElectricityEl.textContent = formatCurrency(data.electricity_cost.monthly);
        
        // 设置盈亏平衡和其他信息 (Set break-even and other info)
        if (breakEvenElectricityEl && data.break_even) 
            breakEvenElectricityEl.textContent = formatCurrency(data.break_even.electricity_cost) + '/kWh';
        if (optimalCurtailmentEl && data.optimization) 
            optimalCurtailmentEl.textContent = formatNumber(data.optimization.optimal_curtailment, 2) + '%';
        
        // Break-even BTC price for host (at what BTC price mining becomes profitable)
        if (breakEvenBtcEl && data.break_even && data.btc_mined.monthly > 0) {
            breakEvenBtcEl.textContent = formatCurrency(data.break_even.btc_price);
        }
        
        // ===== 更新客户相关信息 (Update customer information) =====
        if (data.client_profit) {
            // 客户收益 (Customer profit metrics)
            if (clientMonthlyProfitEl) clientMonthlyProfitEl.textContent = formatCurrency(data.client_profit.monthly);
            if (clientYearlyProfitEl) clientYearlyProfitEl.textContent = formatCurrency(data.client_profit.yearly);
            
            // 添加客户日度收益 (Add customer daily profit)
            const clientDailyProfitEl = document.getElementById('client-daily-profit');
            if (clientDailyProfitEl) clientDailyProfitEl.textContent = formatCurrency(data.client_profit.daily);
            
            // 客户电费 (Customer electricity cost)
            if (data.client_electricity_cost) {
                if (clientMonthlyElectricityEl) 
                    clientMonthlyElectricityEl.textContent = formatCurrency(data.client_electricity_cost.monthly);
                
                // 矿场主收益 = 客户电费 - 实际电费 (Host profit = customer electricity cost - actual electricity cost)
                const hostProfit = data.client_electricity_cost.monthly - data.electricity_cost.monthly;
                if (hostMonthlyProfitEl) hostMonthlyProfitEl.textContent = formatCurrency(hostProfit);
                
                // 如果需要显示矿场挖矿自身的收益，可以计算
                const miningSelfProfit = data.revenue.monthly - data.electricity_cost.monthly;
                const hostSelfProfitEl = document.getElementById('host-self-profit');
                if (hostSelfProfitEl) hostSelfProfitEl.textContent = formatCurrency(miningSelfProfit);
                
                // 客户的盈亏平衡电价和BTC价格 (Customer break-even electricity cost and BTC price)
                if (data.btc_mined.monthly > 0) {
                    // 客户盈亏平衡BTC价格是基于客户电费计算的 (Customer break-even BTC price is based on customer electricity cost)
                    const clientBreakEvenBtc = (data.client_electricity_cost.monthly / data.btc_mined.monthly);
                    if (clientBreakEvenBtcEl) clientBreakEvenBtcEl.textContent = formatCurrency(clientBreakEvenBtc);
                    
                    // 客户盈亏平衡电价与矿场主相同 (Customer break-even electricity cost is the same as host's)
                    if (clientBreakEvenElectricityEl && data.break_even) 
                        clientBreakEvenElectricityEl.textContent = formatCurrency(data.break_even.electricity_cost) + '/kWh';
                }
            }
        }
        
        // Network and mining details
        if (data.network_data) {
            if (networkDifficultyValueEl) 
                networkDifficultyValueEl.textContent = formatNumber(data.network_data.network_difficulty) + ' T';
            // Use network hashrate from the API if available, otherwise estimate it
            const networkHashrateEH = data.network_data.network_hashrate || 
                                    ((data.network_data.network_difficulty * 2**32 / 600) / 10**18);
            if (networkHashrateValueEl) 
                networkHashrateValueEl.textContent = formatNumber(networkHashrateEH, 2) + ' EH/s';
            if (currentBtcPriceValueEl) 
                currentBtcPriceValueEl.textContent = formatCurrency(data.network_data.btc_price);
            if (blockRewardValueEl) 
                blockRewardValueEl.textContent = formatNumber(data.network_data.block_reward, 3) + ' BTC';
        }
        
        // Mining details
        if (dailyBtcValueEl) 
            dailyBtcValueEl.textContent = formatNumber(data.btc_mined.daily, 8);
            
        // 显示两种算法的BTC产出
        const btcMethod1El = document.getElementById('btc-method1-daily');
        const btcMethod2El = document.getElementById('btc-method2-daily');
        
        if (btcMethod1El && data.btc_mined.method1) {
            btcMethod1El.textContent = formatNumber(data.btc_mined.method1.daily, 8);
        }
        
        if (btcMethod2El && data.btc_mined.method2) {
            btcMethod2El.textContent = formatNumber(data.btc_mined.method2.daily, 8);
        }
        if (optimalElectricityRateEl && data.break_even) 
            optimalElectricityRateEl.textContent = formatCurrency(data.break_even.electricity_cost) + '/kWh';
        
        // Calculate or use provided BTC per TH per day
        if (btcPerThDailyEl) {
            if (data.btc_mined.per_th_daily) {
                btcPerThDailyEl.textContent = formatNumber(data.btc_mined.per_th_daily, 8);
            } else if (data.inputs.hashrate && data.btc_mined.daily) {
                const btcPerTh = data.btc_mined.daily / data.inputs.hashrate;
                btcPerThDailyEl.textContent = formatNumber(btcPerTh, 8);
            }
        }
        
        // Miner count and hashrate
        if (data.inputs.miner_count && minerCountResultEl) {
            minerCountResultEl.textContent = data.inputs.miner_count.toLocaleString();
            
            // Display total hashrate
            if (data.inputs.hashrate && totalHashrateResultEl) {
                // Convert hashrate to appropriate unit
                let displayHashrate = data.inputs.hashrate;
                let displayUnit = 'TH/s';
                
                if (displayHashrate >= 1000000) {
                    displayHashrate = displayHashrate / 1000000;
                    displayUnit = 'EH/s';
                } else if (displayHashrate >= 1000) {
                    displayHashrate = displayHashrate / 1000;
                    displayUnit = 'PH/s';
                }
                
                totalHashrateResultEl.textContent = formatNumber(displayHashrate, 2) + ' ' + displayUnit;
            }
        }
        
        // Color the profit values based on whether they're positive or negative
        [dailyProfitEl, monthlyProfitEl, yearlyProfitEl].forEach(el => {
            if (el && el.textContent) {
                try {
                    if (parseFloat(el.textContent.replace(/[^0-9.-]+/g, '')) >= 0) {
                        el.classList.add('profit-positive');
                        el.classList.remove('profit-negative');
                    } else {
                        el.classList.add('profit-negative');
                        el.classList.remove('profit-positive');
                    }
                } catch (error) {
                    console.error('Error formatting profit element:', error);
                }
            }
        });
        
        } catch (error) {
            console.error('Error displaying results:', error);
            showError('Failed to display calculation results. Please try again.');
        }
    }
    
    // Generate profit heatmap chart
    async function generateProfitChart(minerModel, minerCount, clientElectricityCost = 0) {
        try {
            console.log(`Generating profit chart for ${minerModel} with ${minerCount} miners and client electricity cost ${clientElectricityCost}`);
            
            // Create form data with miner model and count
            const formData = new FormData();
            formData.append('miner_model', minerModel);
            formData.append('miner_count', minerCount);
            formData.append('client_electricity_cost', clientElectricityCost);
            
            // Fetch chart data
            const response = await fetch('/profit_chart_data', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const chartData = await response.json();
            
            if (!chartData.success) {
                console.error("Chart data API returned error:", chartData.error || "Unknown error");
                return;
            }
            
            // Show chart card
            chartCard.style.display = 'block';
            
            // Process data for heatmap
            const profitData = chartData.profit_data;
            
            if (!profitData || !Array.isArray(profitData) || profitData.length === 0) {
                console.error("Invalid profit data returned from server");
                return;
            }
            
            // Get unique BTC prices and electricity costs
            const btcPrices = [...new Set(profitData.map(item => item.btc_price))].sort((a, b) => a - b);
            const electricityCosts = [...new Set(profitData.map(item => item.electricity_cost))].sort((a, b) => a - b);
            
            // Create simple scatter data for a heatmap-like visualization
            const scatterData = profitData.map(item => ({
                x: item.electricity_cost,
                y: item.btc_price,
                profit: item.monthly_profit
            }));
            
            // Destroy previous chart if it exists
            if (profitHeatmapChart) {
                profitHeatmapChart.destroy();
            }
            
            // Create the chart
            profitHeatmapChart = new Chart(profitHeatmapCanvas, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Monthly Profit ($)',
                        data: scatterData,
                        pointBackgroundColor: (context) => {
                            const profit = context.raw?.profit || 0;
                            if (profit < 0) return 'rgba(220, 53, 69, 0.7)'; // Negative: red
                            const intensity = Math.min(0.9, Math.max(0.2, profit / 20000)); // Normalize between 0.2 and 0.9
                            return `rgba(25, 135, 84, ${intensity})`;  // Positive: green with intensity
                        },
                        pointRadius: 15,
                        pointHoverRadius: 18,
                        borderWidth: 1,
                        borderColor: 'rgba(255, 255, 255, 0.2)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: '电价 ($/kWh) / Electricity Cost',
                                color: '#ffffff'
                            },
                            ticks: {
                                color: '#dddddd'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: '比特币价格 ($) / Bitcoin Price',
                                color: '#ffffff'
                            },
                            ticks: {
                                color: '#dddddd'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                title: (items) => {
                                    const item = items[0];
                                    return `BTC: $${item.raw.y.toLocaleString()}, Electricity: $${item.raw.x.toFixed(3)}/kWh`;
                                },
                                label: (context) => {
                                    return `Monthly Profit: ${formatCurrency(context.raw.profit)}`;
                                }
                            }
                        },
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            color: '#ffffff',
                            font: {
                                size: 16
                            },
                            text: [
                                clientElectricityCost > 0 ? '客户收益图表 / Customer Profit Chart' : '矿场主收益图表 / Host Profit Chart',
                                `BTC价格: ${formatCurrency(chartData.current_network_data.btc_price)}, 最优电价: ${formatCurrency(chartData.optimal_electricity_rate)}/kWh`
                            ]
                        }
                    },
                    animation: {
                        duration: 800
                    }
                }
            });
            
            console.log("Chart generated successfully");
            
        } catch (error) {
            console.error('Failed to generate profit chart:', error);
            chartCard.style.display = 'none';
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
        // Create or get error message container
        let errorContainer = document.getElementById('error-container');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.id = 'error-container';
            errorContainer.className = 'alert alert-danger alert-dismissible fade show my-3';
            errorContainer.setAttribute('role', 'alert');
            
            // Add dismiss button
            const dismissButton = document.createElement('button');
            dismissButton.type = 'button';
            dismissButton.className = 'btn-close';
            dismissButton.setAttribute('data-bs-dismiss', 'alert');
            dismissButton.setAttribute('aria-label', 'Close');
            
            errorContainer.appendChild(dismissButton);
            
            // Insert at top of form
            calculatorForm.insertBefore(errorContainer, calculatorForm.firstChild);
        }
        
        // Set error message
        errorContainer.innerHTML = `<strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        
        // Scroll to error
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (errorContainer && errorContainer.parentNode) {
                errorContainer.parentNode.removeChild(errorContainer);
            }
        }, 10000);
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