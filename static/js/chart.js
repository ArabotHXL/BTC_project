// 热力图功能独立脚本
document.addEventListener('DOMContentLoaded', () => {
    // 全局变量
    let profitHeatmapChart = null;
    
    // 语言系统
    const translations = {
        'en': {
            'month': 'Month',
            'dynamic_roi': 'Dynamic ROI (considers difficulty adjustment)',
            'static_roi': 'Static ROI (static assumptions)',
            'algorithm_comparison': 'Algorithm Comparison',
            'dynamic_method': 'Dynamic Method',
            'static_method': 'Static Method',
            'algorithm_difference': 'Algorithm Difference',
            'break_even_achieved': 'Break-even Achieved!',
            'break_even_month': 'Break-even Month',
            'monthly_profit': 'Monthly Profit',
            'cumulative_profit': 'Cumulative Profit',
            'remaining_investment': 'Remaining Investment'
        },
        'zh': {
            'month': '月份',
            'dynamic_roi': 'Dynamic ROI (考虑难度调整)',
            'static_roi': 'Static ROI (静态假设)',
            'algorithm_comparison': '双算法对比',
            'dynamic_method': 'Dynamic Method',
            'static_method': 'Static Method',
            'algorithm_difference': '算法差异',
            'break_even_achieved': '达成回本点!',
            'break_even_month': '回本月份',
            'monthly_profit': '当月利润',
            'cumulative_profit': '累计收益',
            'remaining_investment': '剩余投资'
        }
    };
    
    // 获取当前语言
    function getCurrentLanguage() {
        // 从全局变量获取语言
        if (typeof currentLang !== 'undefined') {
            return currentLang;
        }
        // 从meta标签获取语言
        const langMeta = document.querySelector('meta[name="language"]');
        if (langMeta) {
            return langMeta.getAttribute('content');
        }
        // 从URL参数获取语言
        const urlParams = new URLSearchParams(window.location.search);
        const langParam = urlParams.get('lang');
        if (langParam) {
            return langParam;
        }
        // 默认中文
        return 'zh';
    }
    
    // 翻译函数
    function t(key) {
        const lang = getCurrentLanguage();
        return translations[lang] && translations[lang][key] ? translations[lang][key] : key;
    }

    // 绑定生成热力图按钮
    const calculatorForm = document.getElementById('mining-calculator-form');
    if (calculatorForm) {
        calculatorForm.addEventListener('submit', async function(event) {
            // 表单处理部分在main.js中完成
            // 在这里可以获取到结果数据后，添加生成热力图的功能
            
            // 获取图表按钮并绑定事件
            const chartBtn = document.getElementById('generate-chart-btn');
            if (chartBtn) {
                chartBtn.onclick = function() {
                    const minerModel = document.getElementById('miner-model').value;
                    const minerCount = document.getElementById('miner-count').value || 1;
                    const clientElectricityCost = document.getElementById('client-electricity-cost').value || 0;
                    
                    generateChart(minerModel, minerCount, clientElectricityCost);
                    return false; // 防止表单重复提交
                };
            }
        });
    }

    // 简单版热力图生成函数
    async function generateChart(minerModel, minerCount, clientElectricityCost) {
        console.log("开始生成热力图...");
        const chartContainer = document.getElementById('chart-container');
        
        // 验证输入
        if (!minerModel || !chartContainer) {
            console.error("缺少必要参数或容器");
            return;
        }
        
        // 显示加载状态
        chartContainer.innerHTML = '';  // Clear container first
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'd-flex justify-content-center my-5';
        
        const spinnerDiv = document.createElement('div');
        spinnerDiv.className = 'spinner-border text-primary';
        spinnerDiv.setAttribute('role', 'status');
        
        const loadingText = document.createElement('span');
        loadingText.className = 'ms-3';
        loadingText.textContent = '正在生成热力图...';
        
        loadingDiv.appendChild(spinnerDiv);
        loadingDiv.appendChild(loadingText);
        chartContainer.appendChild(loadingDiv);
        
        try {
            // 清理之前的图表
            if (profitHeatmapChart) {
                profitHeatmapChart.destroy();
                profitHeatmapChart = null;
            }
            
            // 获取图表数据
            const params = new URLSearchParams({
                miner_model: minerModel,
                miner_count: minerCount,
                client_electricity_cost: clientElectricityCost
            });
            
            const response = await fetch('/profit_chart_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: params
            });
            
            if (!response.ok) {
                throw new Error(`服务器返回错误: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 验证返回数据
            if (!data.success || !data.profit_data || !Array.isArray(data.profit_data) || data.profit_data.length === 0) {
                throw new Error("服务器返回的数据格式不正确");
            }
            
            console.log("热力图数据获取成功:", data);
            
            // 准备图表容器
            chartContainer.innerHTML = '';  // Clear container first
            const canvas = document.createElement('canvas');
            canvas.id = 'profit-chart';
            canvas.width = '800';
            canvas.height = '400';
            chartContainer.appendChild(canvas);
            
            // 准备散点图数据
            const chartData = [];
            data.profit_data.forEach(item => {
                if (item && typeof item.btc_price === 'number' && 
                    typeof item.electricity_cost === 'number' && 
                    typeof item.monthly_profit === 'number') {
                    
                    chartData.push({
                        x: item.electricity_cost,
                        y: item.btc_price,
                        profit: item.monthly_profit
                    });
                }
            });
            
            // 使用增强热力图或备用散点图
            if (window.createEnhancedHeatmap && typeof window.createEnhancedHeatmap === 'function') {
                try {
                    // 使用新的网格式热力图
                    chartContainer.innerHTML = '';  // 清空容器
                    var title = clientElectricityCost > 0 ? '客户收益热力图' : '矿场主收益热力图';
                    window.createEnhancedHeatmap(chartContainer, data.profit_data, {
                        title: title,
                        language: 'zh'
                    });
                    console.log('增强热力图生成成功');
                } catch (error) {
                    console.error('增强热力图生成失败，使用备用散点图:', error);
                    // 使用备用散点图
                    chartContainer.innerHTML = '';
                    const canvas = document.createElement('canvas');
                    canvas.id = 'heatmap-canvas';
                    canvas.width = 800;
                    canvas.height = 400;
                    chartContainer.appendChild(canvas);
                    
                    const chartData = data.profit_data.map(item => ({
                        x: item.electricity_cost,
                        y: item.btc_price,
                        profit: item.monthly_profit
                    }));
                    
                    profitHeatmapChart = new Chart(canvas, {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: '月度利润',
                                data: chartData,
                                backgroundColor: function(context) {
                                    const value = context.raw ? context.raw.profit : 0;
                                    return value >= 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)';
                                },
                                pointRadius: 12,
                                pointHoverRadius: 18
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                title: {
                                    display: true,
                                    text: clientElectricityCost > 0 ? 
                                        '客户收益热力图' : '矿场主收益热力图',
                                    color: '#fff'
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            return `月利润: $${context.raw.profit.toLocaleString()}`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    title: { display: true, text: '电费价格 ($/kWh)', color: '#fff' },
                                    ticks: { color: '#fff' }
                                },
                                y: {
                                    title: { display: true, text: '比特币价格 ($)', color: '#fff' },
                                    ticks: { color: '#fff' }
                                }
                            }
                        }
                    });
                }
            } else {
                // 备用：改进的散点图
                profitHeatmapChart = new Chart(canvas, {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: '月度利润',
                            data: chartData,
                            backgroundColor: function(context) {
                                const value = context.raw ? context.raw.profit : 0;
                                return value >= 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)';
                            },
                            borderColor: function(context) {
                                const value = context.raw ? context.raw.profit : 0;
                                return value >= 0 ? 'rgba(34, 197, 94, 1)' : 'rgba(239, 68, 68, 1)';
                            },
                            pointRadius: 12,
                            pointHoverRadius: 18,
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                labels: { color: '#fff' }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(0,0,0,0.9)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                borderColor: '#fff',
                                borderWidth: 1,
                                callbacks: {
                                    label: function(context) {
                                        const profit = context.raw.profit;
                                        return `月利润: $${profit.toLocaleString()}`;
                                    }
                                }
                            },
                            title: {
                                display: true,
                                text: clientElectricityCost > 0 ? 
                                    '客户收益热力图' : '矿场主收益热力图',
                                color: '#fff',
                                font: { size: 16, weight: 'bold' }
                            }
                        },
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: '电费价格 ($/kWh)',
                                    color: '#fff',
                                    font: { size: 14, weight: 'bold' }
                                },
                                ticks: { 
                                    color: '#fff',
                                    font: { size: 12 }
                                },
                                grid: { 
                                    color: 'rgba(255,255,255,0.1)',
                                    lineWidth: 1
                                }
                            },
                            y: {
                                title: {
                                    display: true,
                                    text: '比特币价格 ($)',
                                    color: '#fff',
                                    font: { size: 14, weight: 'bold' }
                                },
                                ticks: { 
                                    color: '#fff',
                                    font: { size: 12 },
                                    callback: function(value) {
                                        return '$' + value.toLocaleString();
                                    }
                                },
                                grid: { 
                                    color: 'rgba(255,255,255,0.1)',
                                    lineWidth: 1
                                }
                            }
                        }
                    }
                });
            }
            
            console.log("热力图生成完成");
            
        } catch (error) {
            console.error("热力图生成错误:", error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger';
            errorDiv.textContent = '热力图生成失败: ' + error.message;
            chartContainer.innerHTML = '';
            chartContainer.appendChild(errorDiv);
        }
    }

    // ROI Chart Generation Functions
    let hostRoiChart = null;
    let clientRoiChart = null;

    // Function to generate ROI charts from calculation results
    window.generateRoiCharts = function(data) {
        console.log("generateRoiCharts called");
        
        // Add small delay to ensure DOM is fully rendered
        setTimeout(function() {
            console.log("Chart generation starting after DOM delay...");
            
            // Check if Chart.js is loaded
            if (typeof Chart === 'undefined') {
                console.error("Chart.js is not loaded!");
                return;
            }
            
            if (!data || !data.roi) {
                console.log("No ROI data available for charts");
                return;
            }

            const roi = data.roi;
            console.log("Chart generation - ROI data:", roi);
        
        // Host ROI Chart removed per user request
        
        // Generate Client ROI Chart
        if (roi.client && document.getElementById('client-roi-chart')) {
            console.log("Generating Client ROI chart...");
            generateClientRoiChart(roi.client, data.inputs);
        } else {
            console.log("Client ROI chart not generated - roi.client:", !!roi.client, "container:", !!document.getElementById('client-roi-chart'));
        }
        }, 100); // 100ms delay to ensure DOM is ready
    };

    function generateHostRoiChart(hostRoi, inputs) {
        console.log("generateHostRoiChart called with:", hostRoi, inputs);
        const container = document.getElementById('host-roi-chart');
        console.log("Host chart container found:", !!container);
        if (!container) {
            console.error("Host ROI chart container not found in DOM");
            return;
        }
        if (!hostRoi) {
            console.error("Host ROI data is missing");
            return;
        }

        // Clear previous chart
        if (hostRoiChart) {
            console.log("Destroying previous host chart");
            hostRoiChart.destroy();
        }

        container.innerHTML = '<canvas id="host-roi-canvas"></canvas>';
        const canvas = document.getElementById('host-roi-canvas');
        console.log("Host canvas created:", !!canvas);

        // Generate data points for ROI progression
        const months = [];
        const cumulativeProfit = [];
        const roiPercentage = [];
        
        const monthlyProfit = hostRoi.annual_profit / 12;
        const investment = inputs.host_investment;
        
        for (let i = 1; i <= 24; i++) { // 2 years projection
            months.push(i);
            const totalProfit = monthlyProfit * i;
            cumulativeProfit.push(totalProfit);
            roiPercentage.push((totalProfit / investment) * 100);
        }

        try {
            hostRoiChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: months.map(m => m + 'M'),
                datasets: [{
                    label: 'ROI %',
                    data: roiPercentage,
                    borderColor: 'rgb(255, 193, 7)',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: 'ROI (%)'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Months'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Host ROI Progression',
                        color: 'rgb(255, 193, 7)'
                    },
                    legend: {
                        labels: {
                            color: 'rgba(255, 255, 255, 0.8)'
                        }
                    }
                }
            }
        });
        console.log("Host ROI chart created successfully");
        } catch (error) {
            console.error("Error creating host ROI chart:", error);
        }
    }

    function generateClientRoiChart(clientRoi, inputs) {
        console.log("generateClientRoiChart called with:", clientRoi, inputs);
        const container = document.getElementById('client-roi-chart');
        console.log("Client chart container found:", !!container);
        if (!container) {
            console.error("Client ROI chart container not found in DOM");
            return;
        }
        if (!clientRoi) {
            console.error("Client ROI data is missing");
            return;
        }

        // Clear previous chart
        if (clientRoiChart) {
            console.log("Destroying previous client chart");
            clientRoiChart.destroy();
        }

        container.innerHTML = '<canvas id="client-roi-canvas"></canvas>';
        const canvas = document.getElementById('client-roi-canvas');
        console.log("Client canvas created:", !!canvas);

        // Use the forecast data directly for dynamic calculation
        const months = [];
        const dynamicRoiPercentage = [];
        const staticRoiPercentage = [];
        
        // Find break-even point
        let breakEvenPoint = null;
        let breakEvenIndex = -1;
        
        // Calculate static ROI (simple method) 
        const investment = inputs ? inputs.client_investment : 0;
        const monthlyProfit = clientRoi.forecast && clientRoi.forecast.length > 0 ? 
            clientRoi.forecast[0].monthly_profit : 0;
        
        if (clientRoi.forecast && Array.isArray(clientRoi.forecast)) {
            clientRoi.forecast.forEach((point, index) => {
                months.push(point.month + 'M');
                dynamicRoiPercentage.push(point.roi_percent);
                
                // Calculate static ROI (assumes constant monthly profit)
                const staticCumulativeProfit = monthlyProfit * point.month;
                const staticRoi = investment > 0 ? (staticCumulativeProfit / investment) * 100 : 0;
                staticRoiPercentage.push(staticRoi);
                
                // Find the break-even point (when cumulative profit >= investment)
                if (point.break_even === true && !breakEvenPoint) {
                    breakEvenPoint = point;
                    breakEvenIndex = index;
                    console.log("Break-even point found:", point);
                }
            });
        } else {
            console.error("Client ROI forecast data is not available");
            return;
        }

        // Create datasets with enhanced styling - both dynamic and static lines
        const datasets = [
            {
                label: t('dynamic_roi'),
                data: dynamicRoiPercentage,
                borderColor: 'rgb(139, 69, 255)', // Purple for dynamic method to match table
                backgroundColor: 'rgba(139, 69, 255, 0.15)',
                borderWidth: 3,
                fill: false,
                tension: 0.4,
                pointBackgroundColor: 'rgb(139, 69, 255)',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 8,
                pointHoverBackgroundColor: 'rgb(139, 69, 255)',
                pointHoverBorderColor: '#ffffff',
                pointHoverBorderWidth: 3,
                borderDash: [] // Solid line for dynamic
            },
            {
                label: t('static_roi'),
                data: staticRoiPercentage,
                borderColor: 'rgb(255, 193, 7)', // Yellow for static method to match table
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                pointBackgroundColor: 'rgb(255, 193, 7)',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 1,
                pointRadius: 3,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: 'rgb(255, 193, 7)',
                pointHoverBorderColor: '#ffffff',
                pointHoverBorderWidth: 2,
                borderDash: [5, 5] // Dashed line for static
            }
        ];

        // Create chart options with vertical line plugin
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'ROI (%)',
                        color: 'rgba(255, 255, 255, 0.9)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.8)',
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.15)',
                        lineWidth: 1
                    },
                    beginAtZero: true
                },
                x: {
                    title: {
                        display: true,
                        text: t('month') + 's',
                        color: 'rgba(255, 255, 255, 0.9)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.8)',
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.15)',
                        lineWidth: 1
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: getCurrentLanguage() === 'zh' ? '客户ROI进展: Static vs Dynamic' : 'Client ROI Progression: Static vs Dynamic',
                    color: 'rgb(139, 69, 255)',
                    font: {
                        size: 18,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 30
                    }
                },
                legend: {
                    display: true,
                    position: 'bottom',
                    align: 'center',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.9)',
                        font: {
                            size: 14
                        },
                        usePointStyle: true,
                        padding: 15,
                        boxWidth: 15,
                        boxHeight: 3
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(139, 69, 255, 0.8)',
                    borderWidth: 2,
                    cornerRadius: 12,
                    displayColors: false,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        title: function(context) {
                            if (!context || context.length === 0) return '';
                            return `${t('month')} ${context[0].label.replace('M', '')}`;
                        },
                        label: function(context) {
                            // 只在第一个数据集（Dynamic）时显示完整信息，避免重复
                            if (context.datasetIndex !== 0) {
                                const algorithmType = t('static_roi');
                                return `${algorithmType}: ${context.parsed.y.toFixed(1)}%`;
                            }
                            
                            const dataIndex = context.dataIndex;
                            
                            // Get monthly profit for this month
                            let monthlyProfit = 0;
                            let cumulativeProfit = 0;
                            if (clientRoi.forecast && clientRoi.forecast[dataIndex]) {
                                monthlyProfit = clientRoi.forecast[dataIndex].monthly_profit || 0;
                                cumulativeProfit = clientRoi.forecast[dataIndex].cumulative_profit || 0;
                            }
                            
                            // Calculate static algorithm income based on ROI percentage
                            let staticCumulativeProfit = 0;
                            let staticMonthlyProfit = 0;
                            if (clientRoi.forecast && clientRoi.forecast[dataIndex]) {
                                const investmentAmount = 5000; // Default client investment
                                const staticRoiDecimal = staticRoiPercentage[dataIndex] / 100;
                                staticCumulativeProfit = investmentAmount * staticRoiDecimal;
                                
                                // Calculate static monthly profit (approximation)
                                if (dataIndex === 0) {
                                    staticMonthlyProfit = staticCumulativeProfit;
                                } else if (dataIndex > 0 && staticRoiPercentage[dataIndex - 1]) {
                                    const prevStaticCumulative = investmentAmount * (staticRoiPercentage[dataIndex - 1] / 100);
                                    staticMonthlyProfit = staticCumulativeProfit - prevStaticCumulative;
                                }
                            }
                            
                            // Show both algorithm values for comparison
                            const dynamicRoi = dynamicRoiPercentage[dataIndex];
                            const staticRoi = staticRoiPercentage[dataIndex];
                            const roiDifference = dynamicRoi - staticRoi;
                            
                            let comparisonInfo = [
                                `${t('dynamic_roi')}: ${dynamicRoi.toFixed(1)}%`,
                                `${t('static_roi')}: ${staticRoi.toFixed(1)}%`,
                                '',
                                `📊 ${t('algorithm_comparison')}:`,
                                `${t('dynamic_method')}: $${monthlyProfit.toLocaleString()}`,
                                `${t('static_method')}: $${staticMonthlyProfit.toLocaleString()}`,
                                `${t('algorithm_difference')}: ${roiDifference >= 0 ? '+' : ''}${roiDifference.toFixed(1)}%`
                            ];
                            
                            // Add break-even information if applicable
                            if (dataIndex === breakEvenIndex && breakEvenPoint) {
                                comparisonInfo = comparisonInfo.concat([
                                    '',
                                    `🎯 ${t('break_even_achieved')}`,
                                    `${t('break_even_month')}: ${getCurrentLanguage() === 'zh' ? '第' + breakEvenPoint.month + '个月' : 'Month ' + breakEvenPoint.month}`
                                ]);
                            }
                            
                            return comparisonInfo;
                        }
                    }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeInOutQuart'
            }
        };

        try {
            clientRoiChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: months,
                datasets: datasets
            },
            options: chartOptions,
            plugins: [{
                id: 'breakEvenLines',
                afterDraw: function(chart) {
                    const ctx = chart.ctx;
                    const xScale = chart.scales.x;
                    const yScale = chart.scales.y;
                    
                    // Save context
                    ctx.save();
                    
                    // 红线已移除 - 用户要求移除100% ROI水平参考线
                    
                    // Draw vertical line and marker if break-even point exists
                    if (breakEvenPoint && breakEvenIndex >= 0) {
                        // Calculate x position for break-even line
                        const xPos = xScale.getPixelForValue(breakEvenIndex);
                        
                        // Draw vertical line
                        ctx.beginPath();
                        ctx.strokeStyle = '#ffc107';
                        ctx.lineWidth = 3;
                        ctx.setLineDash([10, 5]);
                        ctx.moveTo(xPos, yScale.top);
                        ctx.lineTo(xPos, yScale.bottom);
                        ctx.stroke();
                        ctx.setLineDash([]);
                        
                        // Draw break-even label
                        ctx.fillStyle = '#ffc107';
                        ctx.font = 'bold 12px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText(`Break-even Month ${breakEvenPoint.month}`, xPos, yScale.top - 10);
                        
                        // Draw break-even marker circle
                        const yPos = yScale.getPixelForValue(breakEvenPoint.roi_percent);
                        ctx.beginPath();
                        ctx.fillStyle = '#ffc107';
                        ctx.strokeStyle = '#ffffff';
                        ctx.lineWidth = 3;
                        ctx.arc(xPos, yPos, 8, 0, 2 * Math.PI);
                        ctx.fill();
                        ctx.stroke();
                    }
                    
                    // Restore context
                    ctx.restore();
                }
            }]
        });
        console.log("Client ROI chart created successfully with break-even point at month:", breakEvenPoint ? breakEvenPoint.month : 'N/A');
        } catch (error) {
            console.error("Error creating client ROI chart:", error);
        }
    }
});