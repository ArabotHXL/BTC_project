"""
基于数据库的智能电力削减管理系统 - Web应用
"""
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from datetime import datetime, timedelta

from power_management_models import db
from power_management_db import PowerManagementDB
from db_power_manager import DBPowerManager

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 初始化数据库
PowerManagementDB.init_app(app)

# 创建电力管理系统实例
power_manager = DBPowerManager()

# ---------------- Web路由 ----------------

@app.route('/')
def index():
    """主页 - 系统仪表盘"""
    return render_template('db_power_dashboard.html')

# ---------------- API路由 ----------------

@app.route('/api/system-status')
def api_system_status():
    """获取系统状态API"""
    status = power_manager.get_system_status()
    return jsonify(status)

@app.route('/api/miners-health')
def api_miners_health():
    """获取矿机健康状况API"""
    health_summary = power_manager.analyze_miners_health()
    return jsonify(health_summary)

@app.route('/api/miners-list')
def api_miners_list():
    """获取矿机列表API"""
    category = request.args.get('category', None)
    status = request.args.get('status', None)
    
    miners = PowerManagementDB.get_all_miners(status=status, category=category)
    
    # 转换为字典列表
    miners_data = [miner.to_dict() for miner in miners]
    
    return jsonify(miners_data)

@app.route('/api/apply-reduction', methods=['POST'])
def api_apply_reduction():
    """应用电力削减策略API"""
    data = request.json
    percentage = float(data.get('percentage', 20.0))
    
    # 应用削减策略
    results = power_manager.apply_power_reduction(percentage)
    
    return jsonify({
        'success': True,
        'message': f'成功应用{percentage}%电力削减策略',
        'results': results
    })

@app.route('/api/generate-rotation')
def api_generate_rotation():
    """生成轮换计划API"""
    rotation_plan = power_manager.generate_rotation_plan()
    return jsonify(rotation_plan)

@app.route('/api/execute-rotation', methods=['POST'])
def api_execute_rotation():
    """执行轮换计划API"""
    data = request.json
    plan_id = data.get('plan_id')
    
    if not plan_id:
        return jsonify({
            'success': False,
            'message': '缺少计划ID参数'
        })
    
    results = power_manager.execute_rotation_plan(plan_id)
    
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
    
    success_count = power_manager.initialize_test_data(count)
    
    return jsonify({
        'success': True,
        'message': f'成功初始化{success_count}台矿机数据'
    })

@app.route('/api/performance-history')
def api_performance_history():
    """获取性能历史数据API"""
    days = int(request.args.get('days', 30))
    
    history = PowerManagementDB.get_performance_history(days)
    
    return jsonify(history)

@app.route('/api/operations-history')
def api_operations_history():
    """获取操作历史记录API"""
    limit = int(request.args.get('limit', 100))
    
    operations = PowerManagementDB.get_recent_operations(limit)
    operations_data = [op.to_dict() for op in operations]
    
    return jsonify(operations_data)

@app.route('/api/miner-operations/<miner_id>')
def api_miner_operations(miner_id):
    """获取特定矿机的操作记录API"""
    operations = PowerManagementDB.get_miner_operations(miner_id)
    operations_data = [op.to_dict() for op in operations]
    
    return jsonify(operations_data)

@app.route('/api/miner-details/<miner_id>')
def api_miner_details(miner_id):
    """获取特定矿机详情API"""
    miner = PowerManagementDB.get_miner(miner_id)
    
    if not miner:
        return jsonify({
            'success': False,
            'message': f'矿机 {miner_id} 不存在'
        })
    
    return jsonify({
        'success': True,
        'miner': miner.to_dict()
    })

@app.route('/api/change-miner-status', methods=['POST'])
def api_change_miner_status():
    """改变矿机状态API"""
    data = request.json
    miner_id = data.get('miner_id')
    status = data.get('status')
    operator = data.get('operator', 'admin')
    reason = data.get('reason', '手动操作')
    
    if not miner_id or not status:
        return jsonify({
            'success': False,
            'message': '缺少必要参数'
        })
    
    if status not in ['running', 'shutdown']:
        return jsonify({
            'success': False,
            'message': f'无效的状态: {status}'
        })
    
    success, message = PowerManagementDB.change_miner_status(
        miner_id=miner_id,
        status=status,
        operator=operator,
        reason=reason
    )
    
    return jsonify({
        'success': success,
        'message': message
    })

# ---------- 计划管理API ----------

@app.route('/api/reduction-plans')
def api_reduction_plans():
    """获取所有电力削减计划API"""
    plans = PowerManagementDB.get_all_reduction_plans()
    plans_data = [plan.to_dict() for plan in plans]
    
    return jsonify(plans_data)

@app.route('/api/create-reduction-plan', methods=['POST'])
def api_create_reduction_plan():
    """创建电力削减计划API"""
    data = request.json
    
    try:
        plan = PowerManagementDB.create_power_reduction_plan(data)
        return jsonify({
            'success': True,
            'message': '成功创建电力削减计划',
            'plan': plan.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'创建计划失败: {str(e)}'
        })

@app.route('/api/activate-reduction-plan', methods=['POST'])
def api_activate_reduction_plan():
    """激活电力削减计划API"""
    data = request.json
    plan_id = data.get('plan_id')
    
    if not plan_id:
        return jsonify({
            'success': False,
            'message': '缺少计划ID参数'
        })
    
    success = PowerManagementDB.activate_reduction_plan(plan_id)
    
    return jsonify({
        'success': success,
        'message': '成功激活电力削减计划' if success else '激活计划失败'
    })

@app.route('/api/rotation-schedules')
def api_rotation_schedules():
    """获取轮换计划列表API"""
    from power_management_models import RotationSchedule
    
    schedules = RotationSchedule.query.order_by(
        RotationSchedule.is_active.desc(),
        RotationSchedule.created_at.desc()
    ).all()
    
    schedules_data = [schedule.to_dict() for schedule in schedules]
    
    return jsonify(schedules_data)

# ---------- 性能快照API ----------

@app.route('/api/create-snapshot', methods=['POST'])
def api_create_snapshot():
    """创建性能快照API"""
    try:
        snapshot = PowerManagementDB.create_performance_snapshot()
        return jsonify({
            'success': True,
            'message': '成功创建性能快照',
            'snapshot': snapshot.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'创建快照失败: {str(e)}'
        })

if __name__ == '__main__':
    # 确保有矿机数据
    with app.app_context():
        from power_management_models import MinerStatus
        
        if MinerStatus.query.count() == 0:
            print("初始化矿机数据...")
            power_manager.initialize_test_data(1000)
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)