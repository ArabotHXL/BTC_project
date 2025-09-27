"""
计算器路由模块
Calculator Routes Module

提供挖矿收益计算API和页面路由
"""
import logging
from flask import Blueprint, request, jsonify, render_template, current_app
from models import MinerModel, NetworkSnapshot, db
from mining_calculator import calculate_mining_profitability
from api.coinwarz import get_bitcoin_data_from_coinwarz
from api.bitcoin_rpc import BitcoinRPCClient

# 创建蓝图
calculator_bp = Blueprint('calculator', __name__)

logger = logging.getLogger(__name__)

@calculator_bp.route('/')
def index():
    """计算器主页面"""
    try:
        # 获取可用的矿机列表
        miners = MinerModel.get_active_miners()
        
        # 获取最新网络数据
        latest_network = NetworkSnapshot.query.order_by(
            NetworkSnapshot.recorded_at.desc()
        ).first()
        
        return render_template('calculator/index.html', 
                             miners=miners, 
                             network_data=latest_network)
    except Exception as e:
        logger.error(f"加载计算器页面失败: {e}")
        return render_template('errors/500.html'), 500

@calculator_bp.route('/api/miners')
def get_miners():
    """获取矿机列表API"""
    try:
        miners = MinerModel.get_active_miners()
        miners_data = []
        
        for miner in miners:
            miners_data.append({
                'id': miner.id,
                'name': miner.model_name,
                'manufacturer': miner.manufacturer,
                'hashrate': miner.reference_hashrate,
                'power_consumption': miner.reference_power,
                'efficiency': miner.reference_efficiency,
                'price': miner.reference_price or 0
            })
        
        return jsonify({
            'success': True,
            'miners': miners_data,
            'count': len(miners_data)
        })
        
    except Exception as e:
        logger.error(f"获取矿机列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取矿机列表失败'
        }), 500

@calculator_bp.route('/api/network-data')
def get_network_data():
    """获取网络数据API"""
    try:
        # 从数据库获取最新数据
        latest_data = NetworkSnapshot.query.order_by(
            NetworkSnapshot.recorded_at.desc()
        ).first()
        
        if latest_data:
            return jsonify({
                'success': True,
                'data': latest_data.to_dict()
            })
        else:
            # 如果没有数据，返回默认值
            return jsonify({
                'success': True,
                'data': {
                    'btc_price': 43000.0,
                    'network_difficulty': 83148355189239.0,
                    'network_hashrate': 650.0,
                    'block_reward': 3.125,
                    'source': 'default'
                }
            })
            
    except Exception as e:
        logger.error(f"获取网络数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '获取网络数据失败'
        }), 500

@calculator_bp.route('/api/calculate', methods=['POST'])
def calculate():
    """执行挖矿收益计算API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求数据'
            }), 400
        
        # 验证必需参数
        required_fields = ['miner_model', 'miner_count', 'electricity_cost']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'缺少必需参数: {", ".join(missing_fields)}'
            }), 400
        
        # 获取矿机信息
        miner_model_name = data.get('miner_model')
        miner = MinerModel.get_by_name(miner_model_name)
        
        if not miner:
            return jsonify({
                'success': False,
                'error': f'未找到矿机型号: {miner_model_name}'
            }), 400
        
        # 获取计算参数
        miner_count = int(data.get('miner_count', 1))
        electricity_cost = float(data.get('electricity_cost'))
        pool_fee = float(data.get('pool_fee', current_app.config.get('DEFAULT_POOL_FEE', 0.025)))
        use_real_time_data = data.get('use_real_time_data', True)
        
        # 自定义参数
        custom_hashrate = data.get('custom_hashrate')
        custom_power = data.get('custom_power')
        custom_btc_price = data.get('custom_btc_price')
        custom_difficulty = data.get('custom_difficulty')
        
        # 执行计算
        result = calculate_mining_profitability(
            miner_model=miner_model_name,
            miner_count=miner_count,
            electricity_cost=electricity_cost,
            pool_fee=pool_fee,
            use_real_time_data=use_real_time_data,
            custom_hashrate=custom_hashrate,
            custom_power=custom_power,
            custom_btc_price=custom_btc_price,
            custom_difficulty=custom_difficulty
        )
        
        return jsonify({
            'success': True,
            'result': result,
            'input_parameters': {
                'miner_model': miner_model_name,
                'miner_count': miner_count,
                'electricity_cost': electricity_cost,
                'pool_fee': pool_fee,
                'hashrate_th': custom_hashrate or miner.reference_hashrate,
                'power_w': custom_power or miner.reference_power
            }
        })
        
    except ValueError as e:
        logger.error(f"计算参数错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '计算参数错误'
        }), 400
        
    except Exception as e:
        logger.error(f"计算失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '计算失败，请检查参数'
        }), 500

@calculator_bp.route('/api/refresh-data', methods=['POST'])
def refresh_data():
    """刷新网络数据API"""
    try:
        # 尝试从CoinWarz获取数据
        btc_data = get_bitcoin_data_from_coinwarz()
        
        if btc_data:
            # 创建新的网络快照
            snapshot = NetworkSnapshot(
                btc_price=btc_data['btc_price'],
                network_difficulty=btc_data['difficulty'],
                network_hashrate=btc_data.get('network_hashrate', 650.0),
                block_reward=btc_data['block_reward'],
                price_source='coinwarz',
                data_source='coinwarz'
            )
            
            db.session.add(snapshot)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'data': snapshot.to_dict(),
                'message': '数据刷新成功'
            })
        else:
            # 尝试使用Bitcoin RPC客户端
            rpc_client = BitcoinRPCClient()
            blockchain_info = rpc_client.get_blockchain_info()
            
            if blockchain_info:
                return jsonify({
                    'success': True,
                    'data': blockchain_info,
                    'message': '从RPC获取数据成功',
                    'source': 'bitcoin_rpc'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '无法获取最新数据',
                    'message': '所有数据源均不可用'
                }), 503
                
    except Exception as e:
        logger.error(f"刷新数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '刷新数据失败'
        }), 500

@calculator_bp.route('/api/miner/<int:miner_id>')
def get_miner_details(miner_id):
    """获取矿机详细信息API"""
    try:
        miner = MinerModel.query.get(miner_id)
        
        if not miner:
            return jsonify({
                'success': False,
                'error': '矿机不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取矿机详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@calculator_bp.route('/api/compare', methods=['POST'])
def compare_miners():
    """矿机对比计算API"""
    try:
        data = request.get_json()
        
        if not data or 'miners' not in data:
            return jsonify({
                'success': False,
                'error': '缺少矿机对比数据'
            }), 400
        
        miners_to_compare = data.get('miners', [])
        electricity_cost = float(data.get('electricity_cost', 0.06))
        pool_fee = float(data.get('pool_fee', 0.025))
        
        if len(miners_to_compare) < 2:
            return jsonify({
                'success': False,
                'error': '至少需要选择2台矿机进行对比'
            }), 400
        
        comparison_results = []
        
        for miner_data in miners_to_compare:
            miner_model = miner_data.get('model')
            miner_count = int(miner_data.get('count', 1))
            
            result = calculate_mining_profitability(
                miner_model=miner_model,
                miner_count=miner_count,
                electricity_cost=electricity_cost,
                pool_fee=pool_fee,
                use_real_time_data=True
            )
            
            comparison_results.append({
                'miner_model': miner_model,
                'miner_count': miner_count,
                'result': result
            })
        
        return jsonify({
            'success': True,
            'comparison': comparison_results,
            'parameters': {
                'electricity_cost': electricity_cost,
                'pool_fee': pool_fee
            }
        })
        
    except Exception as e:
        logger.error(f"矿机对比失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '矿机对比计算失败'
        }), 500