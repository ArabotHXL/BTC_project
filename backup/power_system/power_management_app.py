"""
智能电力削减管理系统 - Web应用界面
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for
import json
import os
from datetime import datetime

from smart_power_manager import PowerManagementSystem

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development_secret_key")

# 创建电力管理系统实例
power_system = PowerManagementSystem()

@app.route('/')
def index():
    """主页 - 系统仪表盘"""
    return render_template('power_dashboard.html')

@app.route('/api/system-status')
def api_system_status():
    """获取系统状态API"""
    status = power_system.get_system_status()
    return jsonify(status)

@app.route('/api/miners-health')
def api_miners_health():
    """获取矿机健康状况API"""
    # 确保有矿机数据
    if not power_system.all_miners:
        power_system.initialize_miners(1000)
    
    health_summary = power_system.analyze_miners_health()
    
    # 构建更详细的矿机状态数据
    categories_data = {}
    for category in ['A', 'B', 'C', 'D']:
        miners_in_category = power_system.categorized_miners.get(category, [])
        running = sum(1 for m in miners_in_category if m.status == "running")
        shutdown = sum(1 for m in miners_in_category if m.status == "shutdown")
        
        categories_data[category] = {
            'total': len(miners_in_category),
            'running': running,
            'shutdown': shutdown,
            'avg_health': sum(m.health_score for m in miners_in_category) / max(1, len(miners_in_category)),
            'avg_efficiency': sum(m.efficiency for m in miners_in_category) / max(1, len(miners_in_category))
        }
    
    return jsonify({
        'summary': health_summary,
        'categories': categories_data
    })

@app.route('/api/miners-list')
def api_miners_list():
    """获取矿机列表API"""
    category = request.args.get('category', None)
    status = request.args.get('status', None)
    
    miners = power_system.all_miners
    
    # 根据类别筛选
    if category in ['A', 'B', 'C', 'D']:
        miners = [m for m in miners if m.category == category]
    
    # 根据状态筛选
    if status in ['running', 'shutdown']:
        miners = [m for m in miners if m.status == status]
    
    # 转换为字典列表
    miners_data = [
        {
            'id': m.miner_id,
            'ip': m.ip,
            'model': m.model,
            'hashrate': round(m.hashrate, 2),
            'power': round(m.power, 2),
            'temperature': round(m.temperature, 1),
            'error_rate': round(m.error_rate, 2),
            'health_score': m.health_score,
            'efficiency': round(m.efficiency, 6),
            'category': m.category,
            'status': m.status
        }
        for m in miners
    ]
    
    return jsonify(miners_data)

@app.route('/api/apply-reduction', methods=['POST'])
def api_apply_reduction():
    """应用电力削减策略API"""
    data = request.json
    percentage = data.get('percentage', 20.0)
    
    # 应用削减策略
    results = power_system.apply_power_reduction(float(percentage))
    
    return jsonify({
        'success': True,
        'message': f'成功应用{percentage}%电力削减策略',
        'results': results
    })

@app.route('/api/generate-rotation')
def api_generate_rotation():
    """生成轮换计划API"""
    rotation_plan = power_system.generate_rotation_plan()
    return jsonify(rotation_plan)

@app.route('/api/execute-rotation', methods=['POST'])
def api_execute_rotation():
    """执行轮换计划API"""
    results = power_system.execute_rotation()
    return jsonify({
        'success': True,
        'message': '成功执行轮换计划',
        'results': results
    })

@app.route('/api/initialize-miners', methods=['POST'])
def api_initialize_miners():
    """初始化矿机数据API"""
    data = request.json
    count = int(data.get('count', 1000))
    
    power_system.initialize_miners(count)
    
    return jsonify({
        'success': True,
        'message': f'成功初始化{count}台矿机数据'
    })

if __name__ == '__main__':
    # 确保有矿机数据
    if not power_system.all_miners:
        power_system.initialize_miners(1000)
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=5000, debug=True)