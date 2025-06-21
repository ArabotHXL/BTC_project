#!/usr/bin/env python3
"""
算法差异演示工具
让用户直观看到两个挖矿算法在不同网络条件下的表现差异
"""

from flask import Blueprint, render_template, request, jsonify, session
from auth import login_required, get_user_role
from mining_calculator import calculate_mining_profitability, get_real_time_btc_price, get_real_time_difficulty, get_real_time_btc_hashrate
import logging

algorithm_demo_bp = Blueprint('algorithm_demo', __name__)

@algorithm_demo_bp.route('/algorithm_demo')
@login_required
def algorithm_demo():
    """算法差异演示页面"""
    user_role = get_user_role(session.get('email'))
    return render_template('algorithm_demo.html', user_role=user_role)

@algorithm_demo_bp.route('/test_algorithm_difference', methods=['POST'])
@login_required
def test_algorithm_difference():
    """测试算法差异的API端点"""
    try:
        # 获取请求参数
        data = request.get_json()
        hashrate_multiplier = float(data.get('hashrate_multiplier', 1.0))
        
        # 获取当前真实数据
        current_btc_price = get_real_time_btc_price()
        current_difficulty = get_real_time_difficulty()
        current_api_hashrate = get_real_time_btc_hashrate()
        
        # 计算修改后的网络算力
        modified_hashrate = current_api_hashrate * hashrate_multiplier
        
        # 测试参数
        test_params = {
            'miner_model': 'Antminer S21 XP',
            'miner_count': 100,
            'electricity_cost': 0.05,
            'use_real_time_data': True,
            'manual_network_hashrate': modified_hashrate
        }
        
        # 计算结果
        result = calculate_mining_profitability(**test_params)
        
        if not result['success']:
            return jsonify({'success': False, 'error': 'Calculation failed'})
        
        # 提取算法结果
        method1_daily = result['btc_mined']['method1']['daily']
        method2_daily = result['btc_mined']['method2']['daily']
        final_daily = result['btc_mined']['daily']
        
        # 计算差异
        difference = abs(method1_daily - method2_daily)
        percentage_diff = (difference / method2_daily * 100) if method2_daily > 0 else 0
        
        # 基于难度计算的参考算力
        difficulty_factor = 2 ** 32
        calculated_hashrate = (current_difficulty * difficulty_factor) / 600 / 1e18  # EH/s
        
        return jsonify({
            'success': True,
            'network_data': {
                'current_btc_price': current_btc_price,
                'current_difficulty': current_difficulty / 1e12,  # T
                'original_api_hashrate': current_api_hashrate,
                'calculated_hashrate': calculated_hashrate,
                'modified_hashrate': modified_hashrate,
                'hashrate_multiplier': hashrate_multiplier
            },
            'algorithm_results': {
                'method1_daily': method1_daily,
                'method2_daily': method2_daily,
                'final_daily': final_daily,
                'difference': difference,
                'percentage_diff': percentage_diff
            },
            'analysis': {
                'status': 'identical' if percentage_diff < 0.01 else 'different',
                'description': get_difference_description(percentage_diff)
            }
        })
        
    except Exception as e:
        logging.error(f"算法差异测试失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

def get_difference_description(percentage_diff):
    """根据差异百分比返回描述"""
    if percentage_diff < 0.01:
        return "算法结果一致 (<0.01%差异)"
    elif percentage_diff < 1:
        return f"微小差异 ({percentage_diff:.3f}%)"
    elif percentage_diff < 5:
        return f"小幅差异 ({percentage_diff:.2f}%)"
    elif percentage_diff < 20:
        return f"中等差异 ({percentage_diff:.2f}%)"
    else:
        return f"显著差异 ({percentage_diff:.2f}%)"

def init_algorithm_demo_routes(app):
    """初始化算法演示路由"""
    app.register_blueprint(algorithm_demo_bp)