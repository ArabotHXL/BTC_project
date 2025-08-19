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
        if (!data || !data.roi) {
            console.log("No ROI data available for charts");
            return;
        }

        const roi = data.roi;
        
        // Generate Host ROI Chart
        if (roi.host && document.getElementById('host-roi-chart')) {
            generateHostRoiChart(roi.host, data.inputs);
        }
        
        // Generate Client ROI Chart
        if (roi.client && document.getElementById('client-roi-chart')) {
            generateClientRoiChart(roi.client, data.inputs);
        }
    };

    function generateHostRoiChart(hostRoi, inputs) {
        const container = document.getElementById('host-roi-chart');
        if (!container || !hostRoi) return;

        // Clear previous chart
        if (hostRoiChart) {
            hostRoiChart.destroy();
        }

        container.innerHTML = '<canvas id="host-roi-canvas"></canvas>';
        const canvas = document.getElementById('host-roi-canvas');

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
    }

    function generateClientRoiChart(clientRoi, inputs) {
        const container = document.getElementById('client-roi-chart');
        if (!container || !clientRoi) return;

        // Clear previous chart
        if (clientRoiChart) {
            clientRoiChart.destroy();
        }

        container.innerHTML = '<canvas id="client-roi-canvas"></canvas>';
        const canvas = document.getElementById('client-roi-canvas');

        // Generate data points for ROI progression
        const months = [];
        const cumulativeProfit = [];
        const roiPercentage = [];
        
        const monthlyProfit = clientRoi.annual_profit / 12;
        const investment = inputs.client_investment;
        
        for (let i = 1; i <= Math.min(60, Math.ceil(clientRoi.payback_period_months * 1.5)); i++) { // Project beyond payback
            months.push(i);
            const totalProfit = monthlyProfit * i;
            cumulativeProfit.push(totalProfit);
            roiPercentage.push((totalProfit / investment) * 100);
        }

        clientRoiChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: months.map(m => m + 'M'),
                datasets: [{
                    label: 'ROI %',
                    data: roiPercentage,
                    borderColor: 'rgb(40, 167, 69)',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
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
                        text: 'Client ROI Progression',
                        color: 'rgb(40, 167, 69)'
                    },
                    legend: {
                        labels: {
                            color: 'rgba(255, 255, 255, 0.8)'
                        }
                    }
                }
            }
        });
    }
});