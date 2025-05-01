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
    // Run initial UI setup
    handleRealTimeToggle();
});
