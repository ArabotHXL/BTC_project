/**
 * HashInsight Enterprise - ROI Heatmap Visualization
 * ROI热力图可视化（D3.js）
 */

class ROIHeatmap {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        this.margin = {top: 40, right: 100, bottom: 60, left: 80};
        this.width = 900 - this.margin.left - this.margin.right;
        this.height = 600 - this.margin.top - this.margin.bottom;
        
        // 颜色比例尺（红色亏损→绿色盈利）
        this.colorScale = d3.scaleLinear()
            .range(['#dc3545', '#ffc107', '#28a745']);
    }
    
    /**
     * 渲染热力图
     */
    render(heatmapData) {
        // 清空容器
        this.container.html('');
        
        // 创建SVG
        const svg = this.container.append('svg')
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        
        // 提取数据
        const xData = heatmapData.x_axis;
        const yData = heatmapData.y_axis;
        const matrix = heatmapData.heatmap;
        
        // 创建比例尺
        const xScale = d3.scaleBand()
            .domain(xData)
            .range([0, this.width])
            .padding(0.05);
        
        const yScale = d3.scaleBand()
            .domain(yData)
            .range([this.height, 0])
            .padding(0.05);
        
        // 设置颜色域
        const allProfits = matrix.flat().map(d => d.profit);
        const minProfit = d3.min(allProfits);
        const maxProfit = d3.max(allProfits);
        
        this.colorScale.domain([minProfit, 0, maxProfit]);
        
        // 绘制热力图单元格
        yData.forEach((yValue, yIndex) => {
            xData.forEach((xValue, xIndex) => {
                const cellData = matrix[yIndex][xIndex];
                
                svg.append('rect')
                    .attr('x', xScale(xValue))
                    .attr('y', yScale(yValue))
                    .attr('width', xScale.bandwidth())
                    .attr('height', yScale.bandwidth())
                    .attr('fill', this.colorScale(cellData.profit))
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 1)
                    .on('mouseover', (event) => {
                        this.showTooltip(event, xValue, yValue, cellData);
                    })
                    .on('mouseout', () => {
                        this.hideTooltip();
                    });
            });
        });
        
        // 绘制当前状态标记
        if (heatmapData.current_state) {
            const currentX = xScale(heatmapData.current_state.btc_price);
            const currentY = yScale(heatmapData.current_state.difficulty_mult);
            
            svg.append('circle')
                .attr('cx', currentX + xScale.bandwidth() / 2)
                .attr('cy', currentY + yScale.bandwidth() / 2)
                .attr('r', 8)
                .attr('fill', 'none')
                .attr('stroke', '#fff')
                .attr('stroke-width', 3);
        }
        
        // 绘制X轴
        const xAxis = d3.axisBottom(xScale)
            .tickValues(xData.filter((d, i) => i % 2 === 0));
        
        svg.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${this.height})`)
            .call(xAxis)
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-45)');
        
        // X轴标签
        svg.append('text')
            .attr('x', this.width / 2)
            .attr('y', this.height + 50)
            .attr('text-anchor', 'middle')
            .text(heatmapData.x_label);
        
        // 绘制Y轴
        const yAxis = d3.axisLeft(yScale);
        
        svg.append('g')
            .attr('class', 'y-axis')
            .call(yAxis);
        
        // Y轴标签
        svg.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -this.height / 2)
            .attr('y', -50)
            .attr('text-anchor', 'middle')
            .text(heatmapData.y_label);
        
        // 添加图例
        this.addLegend(svg, minProfit, maxProfit);
        
        // 添加标题
        svg.append('text')
            .attr('x', this.width / 2)
            .attr('y', -20)
            .attr('text-anchor', 'middle')
            .attr('font-size', '16px')
            .attr('font-weight', 'bold')
            .text(`ROI Heatmap - ${heatmapData.curtailment.name}`);
    }
    
    /**
     * 添加图例
     */
    addLegend(svg, minProfit, maxProfit) {
        const legendHeight = 200;
        const legendWidth = 20;
        
        // 创建渐变
        const defs = svg.append('defs');
        const gradient = defs.append('linearGradient')
            .attr('id', 'profit-gradient')
            .attr('x1', '0%')
            .attr('x2', '0%')
            .attr('y1', '100%')
            .attr('y2', '0%');
        
        gradient.append('stop')
            .attr('offset', '0%')
            .attr('stop-color', '#dc3545');
        
        gradient.append('stop')
            .attr('offset', '50%')
            .attr('stop-color', '#ffc107');
        
        gradient.append('stop')
            .attr('offset', '100%')
            .attr('stop-color', '#28a745');
        
        // 绘制图例矩形
        const legend = svg.append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${this.width + 20}, ${this.height - legendHeight})`);
        
        legend.append('rect')
            .attr('width', legendWidth)
            .attr('height', legendHeight)
            .style('fill', 'url(#profit-gradient)');
        
        // 图例刻度
        const legendScale = d3.scaleLinear()
            .domain([minProfit, maxProfit])
            .range([legendHeight, 0]);
        
        const legendAxis = d3.axisRight(legendScale)
            .ticks(5)
            .tickFormat(d => `$${d.toFixed(0)}`);
        
        legend.append('g')
            .attr('transform', `translate(${legendWidth}, 0)`)
            .call(legendAxis);
    }
    
    /**
     * 显示工具提示
     */
    showTooltip(event, btcPrice, diffMult, cellData) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'heatmap-tooltip')
            .style('position', 'absolute')
            .style('background', '#000')
            .style('color', '#fff')
            .style('padding', '10px')
            .style('border-radius', '5px')
            .style('pointer-events', 'none')
            .style('opacity', 0);
        
        tooltip.html(`
            <strong>BTC Price:</strong> $${btcPrice.toLocaleString()}<br>
            <strong>Difficulty:</strong> ${(diffMult * 100).toFixed(0)}%<br>
            <strong>Daily Profit:</strong> <span style="color: ${cellData.is_profitable ? '#28a745' : '#dc3545'}">
                $${cellData.profit.toFixed(2)}
            </span><br>
            <strong>Margin:</strong> ${cellData.margin.toFixed(1)}%
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px')
        .transition()
        .duration(200)
        .style('opacity', 0.9);
    }
    
    /**
     * 隐藏工具提示
     */
    hideTooltip() {
        d3.selectAll('.heatmap-tooltip').remove();
    }
}
