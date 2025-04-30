document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const miningForm = document.getElementById('mining-form');
    const fetchPriceBtn = document.getElementById('fetch-price');
    const btcPriceInput = document.getElementById('btc_price');
    const resultsContainer = document.getElementById('results-container');
    const loadingIndicator = document.getElementById('loading');
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    
    // Set default BTC price on page load
    fetchBtcPrice();
    
    // Event listener for fetch price button
    fetchPriceBtn.addEventListener('click', fetchBtcPrice);
    
    // Event listener for form submission
    miningForm.addEventListener('submit', function(e) {
        e.preventDefault();
        calculateProfitability();
    });
    
    /**
     * Fetch BTC price from the server
     */
    function fetchBtcPrice() {
        // Show loading spinner on the button
        fetchPriceBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        fetchPriceBtn.disabled = true;
        
        fetch('/btc_price')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    btcPriceInput.value = data.price.toFixed(2);
                } else {
                    showError(data.error || 'Failed to fetch Bitcoin price');
                }
            })
            .catch(error => {
                console.error('Error fetching BTC price:', error);
                showError('Network error when fetching Bitcoin price');
            })
            .finally(() => {
                // Restore button state
                fetchPriceBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
                fetchPriceBtn.disabled = false;
            });
    }
    
    /**
     * Calculate mining profitability
     */
    function calculateProfitability() {
        // Hide previous results and error messages
        resultsContainer.classList.add('d-none');
        errorMessage.classList.add('d-none');
        
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        
        // Collect form data
        const formData = new FormData(miningForm);
        
        // Send calculation request to server
        fetch('/calculate', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayResults(data);
            } else {
                showError(data.error || 'Calculation failed');
            }
        })
        .catch(error => {
            console.error('Error calculating profitability:', error);
            showError('An error occurred during calculation');
        })
        .finally(() => {
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
        });
    }
    
    /**
     * Display calculation results
     */
    function displayResults(data) {
        // Show results container
        resultsContainer.classList.remove('d-none');
        
        // Update profit displays
        document.getElementById('daily-profit').textContent = formatCurrency(data.profit.daily);
        document.getElementById('monthly-profit').textContent = formatCurrency(data.profit.monthly);
        
        // Update BTC amounts
        document.getElementById('daily-btc').textContent = formatBtc(data.btc_mined.daily) + ' BTC';
        document.getElementById('monthly-btc').textContent = formatBtc(data.btc_mined.monthly) + ' BTC';
        
        // Update profit table
        const profitTable = document.getElementById('profit-table');
        profitTable.innerHTML = `
            <tr>
                <td>Daily</td>
                <td>${formatCurrency(data.revenue.daily)}</td>
                <td>${formatCurrency(data.electricity_cost.daily)}</td>
                <td class="${data.profit.daily >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(data.profit.daily)}</td>
            </tr>
            <tr>
                <td>Monthly</td>
                <td>${formatCurrency(data.revenue.monthly)}</td>
                <td>${formatCurrency(data.electricity_cost.monthly)}</td>
                <td class="${data.profit.monthly >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(data.profit.monthly)}</td>
            </tr>
            <tr>
                <td>Yearly</td>
                <td>${formatCurrency(data.revenue.yearly)}</td>
                <td>${formatCurrency(data.electricity_cost.yearly)}</td>
                <td class="${data.profit.yearly >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(data.profit.yearly)}</td>
            </tr>
        `;
        
        // Update break-even cost
        document.getElementById('break-even-cost').textContent = formatCurrency(data.break_even.electricity_cost);
        
        // Update chart
        updateProfitChart(data);
        
        // Scroll to results if on mobile
        if (window.innerWidth < 768) {
            resultsContainer.scrollIntoView({ behavior: 'smooth' });
        }
    }
    
    /**
     * Update the profit distribution chart
     */
    function updateProfitChart(data) {
        const ctx = document.getElementById('profit-chart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (window.profitChart) {
            window.profitChart.destroy();
        }
        
        // Calculate monthly data for the chart
        const revenue = data.revenue.monthly;
        const electricityCost = data.electricity_cost.monthly;
        const profit = data.profit.monthly;
        
        // Determine colors based on profit or loss
        const profitColor = 'rgba(40, 167, 69, 0.8)';
        const costColor = 'rgba(220, 53, 69, 0.8)';
        const revenueColor = 'rgba(13, 110, 253, 0.8)';
        
        if (profit >= 0) {
            // Profit scenario - show breakdown of revenue
            window.profitChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Profit', 'Electricity Cost'],
                    datasets: [{
                        data: [profit, electricityCost],
                        backgroundColor: [profitColor, costColor],
                        borderColor: ['rgba(40, 167, 69, 1)', 'rgba(220, 53, 69, 1)'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: 'rgba(255, 255, 255, 0.7)'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw;
                                    const percentage = ((value / revenue) * 100).toFixed(1);
                                    return `${context.label}: ${formatCurrency(value)} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        } else {
            // Loss scenario - show negative profit
            window.profitChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Revenue', 'Electricity Cost', 'Net Profit'],
                    datasets: [{
                        data: [revenue, electricityCost, Math.abs(profit)],
                        backgroundColor: [revenueColor, costColor, costColor],
                        borderColor: ['rgba(13, 110, 253, 1)', 'rgba(220, 53, 69, 1)', 'rgba(220, 53, 69, 1)'],
                        borderWidth: 1
                    }]
                },
                options: {
                    indexAxis: 'y',
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return formatCurrency(context.raw);
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: 'rgba(255, 255, 255, 0.7)',
                                callback: function(value) {
                                    return formatCurrency(value);
                                }
                            }
                        },
                        y: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: 'rgba(255, 255, 255, 0.7)'
                            }
                        }
                    }
                }
            });
        }
    }
    
    /**
     * Show error message
     */
    function showError(message) {
        errorText.textContent = message;
        errorMessage.classList.remove('d-none');
    }
    
    /**
     * Format currency value
     */
    function formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }
    
    /**
     * Format BTC value with 8 decimal places
     */
    function formatBtc(value) {
        return value.toFixed(8);
    }
});
