/**
 * Enhanced Heatmap Visualization for Mining Profitability
 * Creates a beautiful grid-based heatmap instead of scatter plot
 */

function createEnhancedHeatmap(containerElement, profitData, options = {}) {
    try {
        console.log('开始创建增强热力图，数据点数量:', profitData.length);
        
        // Clear container
        containerElement.innerHTML = '';
        
        const {
            title = '挖矿收益热力图',
            width = 800,
            height = 500,
            language = 'zh'
        } = options;
        
        // Validate input data
        if (!profitData || !Array.isArray(profitData) || profitData.length === 0) {
            throw new Error('无效的利润数据');
        }
        
        // Prepare data structure first
        const btcPrices = [...new Set(profitData.map(item => item.btc_price))].sort((a, b) => b - a);
        const electricityCosts = [...new Set(profitData.map(item => item.electricity_cost))].sort((a, b) => a - b);
        
        console.log('BTC价格范围:', btcPrices);
        console.log('电费范围:', electricityCosts);
        
        // Find min/max profits for color scaling
        const profits = profitData.map(item => item.monthly_profit);
        const minProfit = Math.min(...profits);
        const maxProfit = Math.max(...profits);
        const maxAbsProfit = Math.max(Math.abs(minProfit), Math.abs(maxProfit));
    
    // Create main container with styling
    const heatmapContainer = document.createElement('div');
    heatmapContainer.className = 'enhanced-heatmap-container';
    heatmapContainer.style.cssText = `
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 20px 0;
    `;
    
    // Add title
    const titleElement = document.createElement('h3');
    titleElement.textContent = title;
    titleElement.style.cssText = `
        margin: 0 0 20px 0;
        text-align: center;
        font-size: 24px;
        font-weight: 600;
        color: #ffffff;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    `;
    heatmapContainer.appendChild(titleElement);
    
    // Create heatmap grid
    const heatmapGrid = document.createElement('div');
    heatmapGrid.className = 'heatmap-grid';
    heatmapGrid.style.cssText = `
        display: grid;
        grid-template-columns: 80px repeat(${electricityCosts.length}, 1fr);
        grid-gap: 2px;
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 15px;
        backdrop-filter: blur(10px);
        max-width: 100%;
        overflow-x: auto;
    `;
    
    // Prepare data structure
    const btcPrices = [...new Set(profitData.map(item => item.btc_price))].sort((a, b) => b - a);
    const electricityCosts = [...new Set(profitData.map(item => item.electricity_cost))].sort((a, b) => a - b);
    
    // Find min/max profits for color scaling
    const profits = profitData.map(item => item.monthly_profit);
    const minProfit = Math.min(...profits);
    const maxProfit = Math.max(...profits);
    const maxAbsProfit = Math.max(Math.abs(minProfit), Math.abs(maxProfit));
    
    // Helper function to get profit color
    function getProfitColor(profit) {
        if (profit === 0) return '#6c757d'; // Neutral gray
        
        const intensity = Math.abs(profit) / maxAbsProfit;
        const alpha = Math.max(0.3, Math.min(1, intensity * 0.8 + 0.2));
        
        if (profit > 0) {
            // Green gradient for profits
            const greenIntensity = Math.floor(intensity * 100);
            return `rgba(34, 197, 94, ${alpha})`;
        } else {
            // Red gradient for losses
            const redIntensity = Math.floor(intensity * 100);
            return `rgba(239, 68, 68, ${alpha})`;
        }
    }
    
    // Helper function to format currency
    function formatCurrency(amount) {
        if (Math.abs(amount) >= 1000000) {
            return (amount / 1000000).toFixed(1) + 'M';
        } else if (Math.abs(amount) >= 1000) {
            return (amount / 1000).toFixed(0) + 'k';
        } else if (Math.abs(amount) >= 100) {
            return amount.toFixed(0);
        } else {
            return amount.toFixed(1);
        }
    }
    
    // Create empty top-left cell
    const emptyCell = document.createElement('div');
    emptyCell.style.cssText = `
        background: transparent;
        border: none;
    `;
    heatmapGrid.appendChild(emptyCell);
    
    // Create electricity cost headers
    electricityCosts.forEach(cost => {
        const headerCell = document.createElement('div');
        headerCell.textContent = `$${cost.toFixed(3)}`;
        headerCell.style.cssText = `
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            padding: 8px 4px;
            text-align: center;
            font-weight: 600;
            font-size: 12px;
            color: #ffffff;
        `;
        heatmapGrid.appendChild(headerCell);
    });
    
    // Create rows with BTC price labels and data cells
    btcPrices.forEach(btcPrice => {
        // BTC price label
        const rowLabel = document.createElement('div');
        rowLabel.textContent = `$${formatCurrency(btcPrice)}`;
        rowLabel.style.cssText = `
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            padding: 8px 4px;
            text-align: center;
            font-weight: 600;
            font-size: 11px;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 50px;
        `;
        heatmapGrid.appendChild(rowLabel);
        
        // Data cells for this BTC price
        electricityCosts.forEach(electricityCost => {
            const dataPoint = profitData.find(item => 
                item.btc_price === btcPrice && item.electricity_cost === electricityCost
            );
            
            const profit = dataPoint ? dataPoint.monthly_profit : 0;
            const backgroundColor = getProfitColor(profit);
            
            const dataCell = document.createElement('div');
            dataCell.style.cssText = `
                background: ${backgroundColor};
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 6px;
                padding: 6px 3px;
                text-align: center;
                font-size: 10px;
                font-weight: 600;
                color: ${profit >= 0 ? '#ffffff' : '#ffffff'};
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                min-height: 55px;
                text-shadow: 0 1px 2px rgba(0,0,0,0.7);
                box-shadow: inset 0 1px 2px rgba(255,255,255,0.1);
            `;
            
            // Add profit text
            const profitText = document.createElement('div');
            if (profit >= 0) {
                profitText.textContent = `+$${formatCurrency(profit)}`;
            } else {
                profitText.textContent = `-$${formatCurrency(Math.abs(profit))}`;
            }
            profitText.style.cssText = `
                font-weight: 700;
                font-size: 9px;
                line-height: 1.1;
                letter-spacing: -0.2px;
            `;
            dataCell.appendChild(profitText);
            
            // Add hover effects
            dataCell.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.05)';
                this.style.boxShadow = '0 5px 15px rgba(0,0,0,0.3)';
                this.style.zIndex = '10';
            });
            
            dataCell.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
                this.style.boxShadow = 'none';
                this.style.zIndex = '1';
            });
            
            // Add tooltip
            dataCell.title = `BTC价格: $${btcPrice.toLocaleString()}\n电费: $${electricityCost}/kWh\n月利润: $${profit.toLocaleString()}`;
            
            heatmapGrid.appendChild(dataCell);
        });
    });
    
    heatmapContainer.appendChild(heatmapGrid);
    
    // Add legend
    const legend = document.createElement('div');
    legend.style.cssText = `
        margin-top: 20px;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        flex-wrap: wrap;
    `;
    
    // Create legend items
    const legendItems = [
        { color: 'rgba(239, 68, 68, 0.8)', label: language === 'zh' ? '高亏损' : 'High Loss' },
        { color: 'rgba(239, 68, 68, 0.4)', label: language === 'zh' ? '低亏损' : 'Low Loss' },
        { color: '#6c757d', label: language === 'zh' ? '盈亏平衡' : 'Break-even' },
        { color: 'rgba(34, 197, 94, 0.4)', label: language === 'zh' ? '低盈利' : 'Low Profit' },
        { color: 'rgba(34, 197, 94, 0.8)', label: language === 'zh' ? '高盈利' : 'High Profit' }
    ];
    
    legendItems.forEach(item => {
        const legendItem = document.createElement('div');
        legendItem.style.cssText = `
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #ffffff;
        `;
        
        const colorBox = document.createElement('div');
        colorBox.style.cssText = `
            width: 20px;
            height: 15px;
            background: ${item.color};
            border-radius: 3px;
            border: 1px solid rgba(255,255,255,0.3);
        `;
        
        const label = document.createElement('span');
        label.textContent = item.label;
        
        legendItem.appendChild(colorBox);
        legendItem.appendChild(label);
        legend.appendChild(legendItem);
    });
    
    heatmapContainer.appendChild(legend);
    
    // Add axis labels
    const axisLabels = document.createElement('div');
    axisLabels.style.cssText = `
        margin-top: 15px;
        text-align: center;
        font-size: 14px;
        color: rgba(255,255,255,0.8);
    `;
    axisLabels.innerHTML = `
        <div style="margin-bottom: 5px;">
            <strong>${language === 'zh' ? '横轴：电费价格 ($/kWh)' : 'X-Axis: Electricity Cost ($/kWh)'}</strong>
        </div>
        <div>
            <strong>${language === 'zh' ? '纵轴：比特币价格 ($)' : 'Y-Axis: Bitcoin Price ($)'}</strong>
        </div>
    `;
    heatmapContainer.appendChild(axisLabels);
    
    containerElement.appendChild(heatmapContainer);
    
        return heatmapContainer;
    } catch (error) {
        console.error('Enhanced heatmap generation error:', error);
        containerElement.innerHTML = '<div class="alert alert-danger text-center">热力图生成失败: ' + error.message + '</div>';
        throw error;
    }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.createEnhancedHeatmap = createEnhancedHeatmap;
}