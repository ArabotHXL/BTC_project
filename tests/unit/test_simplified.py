"""测试简化版本的基本功能"""
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash

# 导入简化的模块
from config import Config
from utils.helpers import get_user_role, has_role
from utils.api_client import APIClient
from mining_calculator_simplified import MINER_DATA, MiningCalculator

# 创建测试应用
app = Flask(__name__)
app.config.from_object(Config)

# 设置日志
logging.basicConfig(level=logging.INFO)

# 初始化组件
api_client = APIClient()
calculator = MiningCalculator()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html', miners=MINER_DATA)

@app.route('/test-api')
def test_api():
    """测试API功能"""
    try:
        stats = api_client.get_all_network_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/test-calculator')
def test_calculator():
    """测试计算器功能"""
    try:
        result = calculator.calculate_profitability(
            miner_model="Antminer S19 Pro",
            miner_count=1,
            electricity_cost=0.05,
            use_real_time_data=False,
            btc_price=80000,
            difficulty=119.12
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/test-helpers')
def test_helpers():
    """测试工具函数"""
    test_email = "test@example.com"
    role = get_user_role(test_email)
    
    return jsonify({
        'email': test_email,
        'role': role,
        'has_admin_role': has_role(['admin', 'owner']),
        'miners_count': len(MINER_DATA)
    })

@app.route('/status')
def status():
    """系统状态检查"""
    return jsonify({
        'status': 'running',
        'simplified_version': True,
        'modules_loaded': {
            'config': 'Config' in globals(),
            'api_client': 'APIClient' in globals(),
            'calculator': 'MiningCalculator' in globals(),
            'helpers': True
        },
        'miners_available': len(MINER_DATA)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)