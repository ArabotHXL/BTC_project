// 简化版热力图生成脚本
document.addEventListener('DOMContentLoaded', function() {
    // 查找热力图生成按钮
    const chartBtn = document.getElementById('generate-chart-btn');
    if (chartBtn) {
        // 给按钮添加点击事件
        chartBtn.addEventListener('click', function() {
            // 获取需要的数据
            const minerModel = document.getElementById('miner-model').value;
            const minerCount = document.getElementById('miner-count').value || 1;
            const clientElectricityCost = document.getElementById('client-electricity-cost').value || 0;
            
            // 生成热力图
            generateSimpleChart(minerModel, minerCount, clientElectricityCost);
        });
    }
    
    // 生成热力图的函数
    function generateSimpleChart(minerModel, minerCount, clientElectricityCost) {
        console.log(`Generating chart: model=${minerModel}, count=${minerCount}, client_cost=${clientElectricityCost}`);
        
        // 获取图表容器
        const chartContainer = document.getElementById('chart-container');
        if (!chartContainer) {
            console.error("找不到图表容器");
            return;
        }
        
        // 显示加载中
        chartContainer.innerHTML = '';  // Clear container first
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'd-flex justify-content-center align-items-center';
        loadingDiv.style.height = '300px';
        
        const spinnerDiv = document.createElement('div');
        spinnerDiv.className = 'spinner-border text-primary';
        
        const loadingText = document.createElement('span');
        loadingText.className = 'ms-3';
        loadingText.textContent = '正在生成热力图...';
        
        loadingDiv.appendChild(spinnerDiv);
        loadingDiv.appendChild(loadingText);
        chartContainer.appendChild(loadingDiv);
        
        // 创建请求参数
        const params = new URLSearchParams();
        params.append('miner_model', minerModel);
        params.append('miner_count', minerCount);
        params.append('client_electricity_cost', clientElectricityCost);
        
        // 发送请求获取数据
        fetch('/profit_chart_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: params
        })
        .then(function(response) {
            // 检查响应
            if (!response.ok) {
                throw new Error(`服务器返回 ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(function(data) {
            // 检查数据
            if (!data.success || !data.profit_data || !Array.isArray(data.profit_data)) {
                throw new Error("服务器返回的数据格式不正确");
            }
            
            // 创建图表数据
            const chartData = data.profit_data.map(function(item) {
                return {
                    x: item.electricity_cost,
                    y: item.btc_price,
                    profit: item.monthly_profit
                };
            });
            
            // 准备Canvas
            chartContainer.innerHTML = '';  // Clear container first
            const canvas = document.createElement('canvas');
            canvas.id = 'heatmap-canvas';
            canvas.width = '100%';
            canvas.height = '400';
            chartContainer.appendChild(canvas);
            
            // 创建图表
            new Chart(canvas, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: '月度利润',
                        data: chartData,
                        backgroundColor: function(context) {
                            if (!context.raw) return 'rgba(128, 128, 128, 0.7)';
                            
                            const profit = context.raw.profit;
                            return profit >= 0 
                                ? 'rgba(40, 167, 69, 0.7)'  // 绿色 (正利润)
                                : 'rgba(220, 53, 69, 0.7)'; // 红色 (负利润)
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
                                text: '电价 ($/kWh)'
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
                                '客户收益热力图 / Customer Profit Chart' : 
                                '矿场主收益热力图 / Host Profit Chart'
                        }
                    }
                }
            });
            
            console.log("热力图生成成功");
        })
        .catch(function(error) {
            console.error("热力图生成失败:", error);
            // Create elements safely to prevent XSS
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger text-center';
            
            const strongElement = document.createElement('strong');
            strongElement.textContent = '热力图生成失败:';
            
            const brElement = document.createElement('br');
            
            const errorText = document.createTextNode(error.message || '未知错误');
            
            errorDiv.appendChild(strongElement);
            errorDiv.appendChild(brElement);
            errorDiv.appendChild(errorText);
            
            chartContainer.innerHTML = '';
            chartContainer.appendChild(errorDiv);
        });
    }
});