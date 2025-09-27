"""
Mining Core Module - Inter-Module Communication API Routes
挖矿核心模块 - 模块间通信API路由
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
api_comm_bp = Blueprint('api_communication', __name__)

@api_comm_bp.route('/health')
def health():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'module': 'mining_core',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'features': [
            'Mining Profitability Calculation',
            'Technical Analysis',
            'Market Analytics',
            'Batch Processing',
            'Historical Data'
        ]
    })

@api_comm_bp.route('/api/calculate/profitability', methods=['POST'])
def calculate_mining_profitability():
    """计算挖矿盈利能力 - 供其他模块调用"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid request data'
            }), 400
        
        # 获取计算参数
        miner_model = data.get('miner_model')
        hashrate = data.get('hashrate', 0)
        power_consumption = data.get('power_consumption', 0)
        electricity_cost = data.get('electricity_cost', 0.1)
        btc_price = data.get('btc_price', 43000)
        network_difficulty = data.get('network_difficulty', 83148355189239)
        
        if not all([miner_model, hashrate, power_consumption]):
            return jsonify({
                'success': False,
                'error': 'Missing required calculation parameters'
            }), 400
        
        # 简化的盈利能力计算
        daily_revenue = (hashrate * 86400 * 6.25) / (network_difficulty * 2**32 / 10**12) * btc_price
        daily_electricity_cost = (power_consumption / 1000) * 24 * electricity_cost
        daily_profit = daily_revenue - daily_electricity_cost
        
        result = {
            'miner_model': miner_model,
            'hashrate_ths': hashrate,
            'power_consumption_w': power_consumption,
            'electricity_cost_kwh': electricity_cost,
            'btc_price_usd': btc_price,
            'calculations': {
                'daily_revenue_usd': round(daily_revenue, 2),
                'daily_electricity_cost_usd': round(daily_electricity_cost, 2),
                'daily_profit_usd': round(daily_profit, 2),
                'monthly_profit_usd': round(daily_profit * 30, 2),
                'yearly_profit_usd': round(daily_profit * 365, 2),
                'roi_days': round(data.get('miner_price', 0) / max(daily_profit, 0.01), 0) if daily_profit > 0 else -1
            },
            'calculated_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Profitability calculation error: {e}")
        return jsonify({
            'success': False,
            'error': 'Calculation failed'
        }), 500

@api_comm_bp.route('/api/analytics/market', methods=['GET'])
def get_market_analytics():
    """获取市场分析数据 - 供其他模块调用"""
    try:
        timeframe = request.args.get('timeframe', '24h')
        indicators = request.args.get('indicators', '').split(',') if request.args.get('indicators') else []
        
        # 模拟市场分析数据
        market_data = {
            'timeframe': timeframe,
            'btc_price': {
                'current': 43000,
                'change_24h': 2.5,
                'change_7d': -1.2,
                'high_24h': 43500,
                'low_24h': 42200
            },
            'network_metrics': {
                'difficulty': 83148355189239,
                'hashrate_ehs': 650,
                'next_difficulty_adjustment': 1.2,
                'blocks_until_adjustment': 1456
            },
            'mining_profitability': {
                'average_daily_profit_s19_pro': 12.50,
                'electricity_break_even': 0.08,
                'profitability_index': 1.25
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 如果请求了特定指标，只返回这些指标
        if indicators:
            filtered_data = {'timeframe': timeframe, 'timestamp': market_data['timestamp']}
            for indicator in indicators:
                if indicator in market_data:
                    filtered_data[indicator] = market_data[indicator]
            market_data = filtered_data
        
        return jsonify({
            'success': True,
            'data': market_data
        })
        
    except Exception as e:
        logger.error(f"Market analytics error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get market analytics'
        }), 500

@api_comm_bp.route('/api/reports/generate', methods=['POST'])
def generate_mining_report():
    """生成挖矿报告 - 供其他模块调用"""
    try:
        data = request.get_json()
        report_type = data.get('report_type', 'standard')
        period = data.get('period', '30d')
        user_id = data.get('user_id')
        
        # 模拟报告生成
        report_id = f"report_{datetime.utcnow().timestamp()}"
        
        report_data = {
            'report_id': report_id,
            'report_type': report_type,
            'period': period,
            'user_id': user_id,
            'generated_at': datetime.utcnow().isoformat(),
            'status': 'completed',
            'summary': {
                'total_calculations': 145,
                'profitable_configs': 89,
                'average_daily_profit': 15.30,
                'best_miner_model': 'Antminer S21',
                'recommended_electricity_cost': 0.06
            },
            'file_url': f"/reports/{report_id}.pdf",
            'download_expires_at': (datetime.utcnow().replace(microsecond=0).isoformat() + 'Z')
        }
        
        return jsonify({
            'success': True,
            'data': report_data
        })
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate report'
        }), 500

@api_comm_bp.route('/api/data/store', methods=['POST'])
def store_calculation_result():
    """存储计算结果 - 供Web3模块调用"""
    try:
        data = request.get_json()
        calculation_id = data.get('calculation_id')
        result_data = data.get('result_data')
        user_id = data.get('user_id')
        store_on_blockchain = data.get('store_on_blockchain', False)
        
        if not all([calculation_id, result_data]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # 模拟存储逻辑
        storage_result = {
            'calculation_id': calculation_id,
            'user_id': user_id,
            'stored_at': datetime.utcnow().isoformat(),
            'storage_type': 'database',
            'data_hash': f"hash_{calculation_id}",
            'status': 'stored'
        }
        
        if store_on_blockchain:
            # 这里会调用Web3模块进行区块链存储
            storage_result['blockchain_tx'] = f"0x{calculation_id}abcd1234"
            storage_result['storage_type'] = 'blockchain'
        
        return jsonify({
            'success': True,
            'data': storage_result
        })
        
    except Exception as e:
        logger.error(f"Data storage error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to store calculation result'
        }), 500

@api_comm_bp.route('/api/miners/models', methods=['GET'])
def get_miner_models():
    """获取矿机型号列表 - 供其他模块调用"""
    try:
        manufacturer = request.args.get('manufacturer')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        # 模拟矿机型号数据
        miners = [
            {
                'id': 1,
                'model_name': 'Antminer S19 Pro',
                'manufacturer': 'Bitmain',
                'hashrate_ths': 110,
                'power_consumption_w': 3250,
                'efficiency_jth': 29.5,
                'release_date': '2020-05-01',
                'is_active': True
            },
            {
                'id': 2,
                'model_name': 'WhatsMiner M30S++',
                'manufacturer': 'MicroBT',
                'hashrate_ths': 112,
                'power_consumption_w': 3472,
                'efficiency_jth': 31,
                'release_date': '2020-08-01',
                'is_active': True
            },
            {
                'id': 3,
                'model_name': 'Antminer S21',
                'manufacturer': 'Bitmain',
                'hashrate_ths': 200,
                'power_consumption_w': 3550,
                'efficiency_jth': 17.8,
                'release_date': '2024-01-01',
                'is_active': True
            }
        ]
        
        # 应用筛选条件
        if manufacturer:
            miners = [m for m in miners if m['manufacturer'].lower() == manufacturer.lower()]
        
        if active_only:
            miners = [m for m in miners if m['is_active']]
        
        return jsonify({
            'success': True,
            'data': miners,
            'count': len(miners)
        })
        
    except Exception as e:
        logger.error(f"Get miner models error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get miner models'
        }), 500

@api_comm_bp.route('/api/network/metrics', methods=['GET'])
def get_network_metrics():
    """获取网络指标 - 供其他模块调用"""
    try:
        # 模拟网络指标数据
        metrics = {
            'btc_price_usd': 43000,
            'network_difficulty': 83148355189239,
            'network_hashrate_ehs': 650,
            'block_height': 850000,
            'next_difficulty_adjustment': {
                'blocks_remaining': 1456,
                'estimated_change_percent': 1.2,
                'estimated_time_hours': 243
            },
            'mempool_stats': {
                'unconfirmed_transactions': 15420,
                'avg_fee_sat_vb': 25,
                'recommended_fee_sat_vb': 30
            },
            'mining_stats': {
                'avg_block_time_minutes': 9.8,
                'blocks_mined_24h': 147,
                'estimated_difficulty_next': 84148355189239
            },
            'updated_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': metrics
        })
        
    except Exception as e:
        logger.error(f"Network metrics error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get network metrics'
        }), 500