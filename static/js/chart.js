// 热力图功能独立脚本
document.addEventListener('DOMContentLoaded', () => {
    // 全局变量
    let profitHeatmapChart = null;

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
            
            // 创建热力图
            profitHeatmapChart = new Chart(canvas, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: '月度利润',
                        data: chartData,
                        backgroundColor: function(context) {
                            const value = context.raw ? context.raw.profit : 0;
                            return value >= 0 ? 'rgba(0, 255, 0, 0.5)' : 'rgba(255, 0, 0, 0.5)';
                        },
                        pointRadius: 10,
                        pointHoverRadius: 15
                    }]
                },
                options: {
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: '电费价格 ($/kWh)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: '比特币价格 ($)'
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const profit = context.raw.profit;
                                    return `月利润: $${profit.toFixed(2)}`;
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: clientElectricityCost > 0 ? 
                                '客户收益热力图' : '矿场主收益热力图'
                        }
                    }
                }
            });
            
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

        // Use the forecast data directly
        const months = [];
        const roiPercentage = [];
        
        // Find break-even point
        let breakEvenPoint = null;
        let breakEvenIndex = -1;
        
        if (clientRoi.forecast && Array.isArray(clientRoi.forecast)) {
            clientRoi.forecast.forEach((point, index) => {
                months.push(point.month + 'M');
                roiPercentage.push(point.roi_percent);
                
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

        // Create datasets
        const datasets = [{
            label: 'ROI %',
            data: roiPercentage,
            borderColor: 'rgb(40, 167, 69)',
            backgroundColor: 'rgba(40, 167, 69, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.1,
            pointBackgroundColor: roiPercentage.map((value, index) => 
                index === breakEvenIndex ? '#ffc107' : 'rgb(40, 167, 69)'
            ),
            pointBorderColor: roiPercentage.map((value, index) => 
                index === breakEvenIndex ? '#ffc107' : 'rgb(40, 167, 69)'
            ),
            pointRadius: roiPercentage.map((value, index) => 
                index === breakEvenIndex ? 8 : 4
            ),
            pointHoverRadius: roiPercentage.map((value, index) => 
                index === breakEvenIndex ? 10 : 6
            )
        }];

        // Add break-even line if break-even point exists
        if (breakEvenPoint && breakEvenIndex >= 0) {
            datasets.push({
                label: 'Break-even Point',
                data: roiPercentage.map((value, index) => 
                    index === breakEvenIndex ? value : null
                ),
                borderColor: '#ffc107',
                backgroundColor: '#ffc107',
                borderWidth: 0,
                fill: false,
                pointBackgroundColor: '#ffc107',
                pointBorderColor: '#ffc107',
                pointRadius: 10,
                pointHoverRadius: 12,
                showLine: false,
                pointStyle: 'star'
            });
        }

        try {
            clientRoiChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: months,
                datasets: datasets
            },
            options: {
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
                            color: 'rgba(255, 255, 255, 0.8)'
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.8)'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Months',
                            color: 'rgba(255, 255, 255, 0.8)'
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.8)'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Client ROI Progression',
                        color: 'rgb(40, 167, 69)',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        display: true,
                        labels: {
                            color: 'rgba(255, 255, 255, 0.8)',
                            filter: function(item, chart) {
                                // Only show ROI % in legend, hide Break-even Point
                                return item.text === 'ROI %';
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'rgba(255, 255, 255, 0.9)',
                        bodyColor: 'rgba(255, 255, 255, 0.9)',
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                        borderWidth: 1,
                        callbacks: {
                            afterBody: function(context) {
                                const dataIndex = context[0].dataIndex;
                                if (dataIndex === breakEvenIndex && breakEvenPoint) {
                                    return [
                                        '',
                                        '🎯 BREAK-EVEN ACHIEVED!',
                                        `✅ Investment Recovered: $${breakEvenPoint.cumulative_profit.toLocaleString()}`,
                                        `📅 Month: ${breakEvenPoint.month}`,
                                        `📈 ROI: ${breakEvenPoint.roi_percent.toFixed(2)}%`
                                    ];
                                }
                                return '';
                            }
                        }
                    }
                }
            }
        });
        console.log("Client ROI chart created successfully with break-even point at month:", breakEvenPoint ? breakEvenPoint.month : 'N/A');
        } catch (error) {
            console.error("Error creating client ROI chart:", error);
        }
    }
});