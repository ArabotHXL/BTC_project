/**
 * Enhanced Grid-based Heatmap Visualization for Mining Profitability
 * Creates beautiful square-based heatmap with proper grid layout
 */

function createEnhancedHeatmap(containerElement, profitData, options = {}) {
    try {
        console.log('开始创建方块热力图，数据点数量:', profitData.length);
        
        // Clear container
        containerElement.innerHTML = '';
        
        // Get current language from page
        const currentLang = document.documentElement.lang === 'en' || document.querySelector('meta[name="language"]')?.content === 'en' ? 'en' : 'zh';
        
        const {
            title = currentLang === 'en' ? 'Customer Profitability Heatmap' : '客户收益热力图',
            width = 900,
            height = 550,
            language = currentLang
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
        heatmapContainer.className = 'square-heatmap-container';
        heatmapContainer.style.cssText = `
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.4);
            color: white;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px 0;
            overflow: hidden;
        `;
        
        // Add title
        const titleElement = document.createElement('h3');
        titleElement.textContent = title;
        titleElement.style.cssText = `
            margin: 0 0 25px 0;
            text-align: center;
            font-size: 26px;
            font-weight: 700;
            color: #ffffff;
            text-shadow: 0 3px 6px rgba(0,0,0,0.5);
            letter-spacing: 1px;
        `;
        heatmapContainer.appendChild(titleElement);
        
        // Helper function to get profit color for squares
        function getSquareColor(profit) {
            if (profit === 0) return '#4a5568'; // Neutral gray
            
            const intensity = Math.min(1, Math.abs(profit) / maxAbsProfit);
            
            if (profit > 0) {
                // Green gradient for profit
                const greenBase = [34, 197, 94]; // rgb(34, 197, 94)
                const alpha = 0.3 + (intensity * 0.7); // 0.3 to 1.0
                return `rgba(${greenBase[0]}, ${greenBase[1]}, ${greenBase[2]}, ${alpha})`;
            } else {
                // Red gradient for loss
                const redBase = [239, 68, 68]; // rgb(239, 68, 68)
                const alpha = 0.3 + (intensity * 0.7); // 0.3 to 1.0
                return `rgba(${redBase[0]}, ${redBase[1]}, ${redBase[2]}, ${alpha})`;
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
        
        // Create grid wrapper
        const gridWrapper = document.createElement('div');
        gridWrapper.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        `;
        
        // Create column headers for electricity costs
        const headerRow = document.createElement('div');
        headerRow.style.cssText = `
            display: flex;
            gap: 6px;
            margin-left: 120px;
            align-items: center;
        `;
        
        const headerLabel = document.createElement('div');
        headerLabel.textContent = language === 'en' ? 'Electricity Cost ($/kWh)' : '电费价格 ($/kWh)';
        headerLabel.style.cssText = `
            position: absolute;
            left: 30px;
            top: -25px;
            font-size: 12px;
            color: #a0a0a0;
            font-weight: 600;
        `;
        headerRow.style.position = 'relative';
        headerRow.appendChild(headerLabel);
        
        electricityCosts.forEach(cost => {
            const header = document.createElement('div');
            header.textContent = cost.toFixed(2);
            header.style.cssText = `
                width: 99px;
                text-align: center;
                font-size: 12px;
                font-weight: 600;
                color: #e0e0e0;
                padding: 6px;
            `;
            headerRow.appendChild(header);
        });
        gridWrapper.appendChild(headerRow);
        
        // Create heatmap grid
        const heatmapGrid = document.createElement('div');
        heatmapGrid.className = 'square-heatmap-grid';
        heatmapGrid.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 6px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 25px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.1);
        `;

        // Create data lookup for quick access
        const dataLookup = {};
        profitData.forEach(item => {
            const key = `${item.btc_price}_${item.electricity_cost}`;
            dataLookup[key] = item;
        });

        // Create rows with BTC price labels and data squares
        btcPrices.forEach(btcPrice => {
            const row = document.createElement('div');
            row.style.cssText = `
                display: flex;
                align-items: center;
                gap: 6px;
            `;

            // BTC price label (Y-axis)
            const rowLabel = document.createElement('div');
            rowLabel.textContent = `$${formatCurrency(btcPrice)}`;
            rowLabel.style.cssText = `
                width: 100px;
                text-align: right;
                font-size: 13px;
                font-weight: 600;
                color: #e0e0e0;
                padding: 10px 15px 10px 5px;
                display: flex;
                align-items: center;
                justify-content: flex-end;
            `;
            row.appendChild(rowLabel);

            // Create squares for each electricity cost
            electricityCosts.forEach(electricityCost => {
                const key = `${btcPrice}_${electricityCost}`;
                const dataPoint = dataLookup[key];
                const profit = dataPoint ? dataPoint.monthly_profit : 0;
                const backgroundColor = getSquareColor(profit);

                const square = document.createElement('div');
                square.style.cssText = `
                    width: 75px;
                    height: 75px;
                    background: ${backgroundColor};
                    border: 2px solid rgba(255,255,255,0.2);
                    border-radius: 10px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    position: relative;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
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
                    font-size: 11px;
                    line-height: 1.1;
                    letter-spacing: -0.2px;
                    color: #ffffff;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.8);
                    text-align: center;
                `;
                square.appendChild(profitText);

                // Add hover effects
                square.addEventListener('mouseenter', function() {
                    this.style.transform = 'scale(1.1)';
                    this.style.zIndex = '10';
                    this.style.boxShadow = '0 8px 25px rgba(0,0,0,0.4)';
                    
                    // Show detailed tooltip
                    const tooltip = document.createElement('div');
                    tooltip.className = 'heatmap-tooltip';
                    tooltip.innerHTML = language === 'en' ? `
                        <strong>BTC Price:</strong> $${btcPrice.toLocaleString()}<br>
                        <strong>Electricity:</strong> $${electricityCost}/kWh<br>
                        <strong>Monthly Profit:</strong> $${profit.toLocaleString()}
                    ` : `
                        <strong>BTC价格:</strong> $${btcPrice.toLocaleString()}<br>
                        <strong>电费:</strong> $${electricityCost}/kWh<br>
                        <strong>月利润:</strong> $${profit.toLocaleString()}
                    `;
                    tooltip.style.cssText = `
                        position: absolute;
                        bottom: 110%;
                        left: 50%;
                        transform: translateX(-50%);
                        background: rgba(0,0,0,0.9);
                        color: white;
                        padding: 8px 12px;
                        border-radius: 6px;
                        font-size: 11px;
                        white-space: nowrap;
                        z-index: 20;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        border: 1px solid rgba(255,255,255,0.2);
                    `;
                    this.appendChild(tooltip);
                });

                square.addEventListener('mouseleave', function() {
                    this.style.transform = 'scale(1)';
                    this.style.zIndex = '1';
                    this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
                    
                    // Remove tooltip
                    const tooltip = this.querySelector('.heatmap-tooltip');
                    if (tooltip) {
                        tooltip.remove();
                    }
                });

                row.appendChild(square);
            });

            heatmapGrid.appendChild(row);
        });

        gridWrapper.appendChild(heatmapGrid);

        // Add Y-axis label
        const yAxisLabel = document.createElement('div');
        yAxisLabel.textContent = language === 'en' ? 'BTC Price ($)' : '比特币价格 ($)';
        yAxisLabel.style.cssText = `
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%) rotate(-90deg);
            font-size: 12px;
            color: #a0a0a0;
            font-weight: 600;
            white-space: nowrap;
        `;
        
        const gridContainer = document.createElement('div');
        gridContainer.style.position = 'relative';
        gridContainer.appendChild(yAxisLabel);
        gridContainer.appendChild(gridWrapper);

        // Add color legend
        const legend = document.createElement('div');
        legend.style.cssText = `
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-top: 20px;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            font-size: 11px;
        `;
        
        const legendItems = language === 'en' ? [
            { color: 'rgba(239, 68, 68, 0.8)', label: 'High Loss' },
            { color: 'rgba(239, 68, 68, 0.4)', label: 'Low Loss' },
            { color: '#4a5568', label: 'Break-even' },
            { color: 'rgba(34, 197, 94, 0.4)', label: 'Low Profit' },
            { color: 'rgba(34, 197, 94, 0.8)', label: 'High Profit' }
        ] : [
            { color: 'rgba(239, 68, 68, 0.8)', label: '高亏损' },
            { color: 'rgba(239, 68, 68, 0.4)', label: '低亏损' },
            { color: '#4a5568', label: '盈亏平衡' },
            { color: 'rgba(34, 197, 94, 0.4)', label: '低盈利' },
            { color: 'rgba(34, 197, 94, 0.8)', label: '高盈利' }
        ];
        
        legendItems.forEach(item => {
            const legendItem = document.createElement('div');
            legendItem.style.cssText = `
                display: flex;
                align-items: center;
                gap: 6px;
            `;
            
            const colorBox = document.createElement('div');
            colorBox.style.cssText = `
                width: 16px;
                height: 16px;
                background: ${item.color};
                border-radius: 3px;
                border: 1px solid rgba(255,255,255,0.3);
            `;
            
            const label = document.createElement('span');
            label.textContent = item.label;
            label.style.color = '#e0e0e0';
            
            legendItem.appendChild(colorBox);
            legendItem.appendChild(label);
            legend.appendChild(legendItem);
        });

        heatmapContainer.appendChild(gridContainer);
        heatmapContainer.appendChild(legend);
        containerElement.appendChild(heatmapContainer);

        console.log('方块热力图创建成功');
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