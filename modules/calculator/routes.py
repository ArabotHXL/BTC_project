"""
计算器模块路由
完全独立的路由处理，不依赖其他模块
"""
from flask import render_template, request, jsonify, session, current_app
from flask_caching import Cache
from datetime import datetime, timedelta
from . import calculator_bp
from models import MinerModel, NetworkSnapshot, db
from mining_calculator import MiningCalculator
import logging

logger = logging.getLogger(__name__)

# Simple in-memory cache for miner models (5 minutes TTL)
_miner_cache = {'data': None, 'timestamp': None}
MINER_CACHE_TTL = 300  # 5 minutes

# Simple in-memory cache for network snapshot (1 minute TTL)
_network_cache = {'data': None, 'timestamp': None}
NETWORK_CACHE_TTL = 60  # 1 minute


def get_cached_miners():
    """Get miners from cache or refresh from database"""
    now = datetime.now()
    if _miner_cache['data'] and _miner_cache['timestamp']:
        if (now - _miner_cache['timestamp']).total_seconds() < MINER_CACHE_TTL:
            return _miner_cache['data']
    
    # Refresh cache
    miners = MinerModel.query.filter_by(is_active=True).all()
    miners_data = []
    for miner in miners:
        miners_data.append({
            'id': miner.id,
            'name': miner.model_name,
            'hashrate': miner.reference_hashrate,
            'power_consumption': miner.reference_power,
            'price': miner.reference_price or 0,
            'manufacturer': miner.manufacturer
        })
    _miner_cache['data'] = miners_data
    _miner_cache['timestamp'] = now
    return _miner_cache['data']


def get_cached_network_snapshot():
    """Get network snapshot from cache or refresh from database"""
    now = datetime.now()
    if _network_cache['data'] and _network_cache['timestamp']:
        if (now - _network_cache['timestamp']).total_seconds() < NETWORK_CACHE_TTL:
            return _network_cache['data']
    
    # Refresh cache
    network_data = NetworkSnapshot.query.order_by(NetworkSnapshot.recorded_at.desc()).first()
    if network_data:
        _network_cache['data'] = {
            'btc_price': network_data.btc_price,
            'network_hashrate': network_data.network_hashrate,
            'network_difficulty': network_data.network_difficulty,
            'block_reward': network_data.block_reward,
            'recorded_at': network_data.recorded_at
        }
    else:
        _network_cache['data'] = None
    _network_cache['timestamp'] = now
    return _network_cache['data']


@calculator_bp.route('/')
def index():
    """计算器主页面"""
    return render_template('calculator/index.html')

@calculator_bp.route('/api/miners')
def get_miners():
    """获取矿机列表API - 从数据库读取（带缓存）"""
    try:
        miners_data = get_cached_miners()
        return jsonify({'success': True, 'miners': miners_data})
    except Exception as e:
        logger.error(f"获取矿机列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@calculator_bp.route('/api/calculate', methods=['POST'])
def calculate():
    """计算挖矿收益API"""
    try:
        data = request.get_json()
        
        # 从数据库获取矿机信息
        miner_model = data.get('miner_model')
        miner = MinerModel.query.filter_by(model_name=miner_model).first()
        
        if not miner:
            return jsonify({'success': False, 'error': '未找到矿机型号'})
        
        # 从缓存获取网络数据
        network_data = get_cached_network_snapshot()
        
        if not network_data:
            return jsonify({'success': False, 'error': '无法获取网络数据'})
        
        # 执行计算
        calc = MiningCalculator()
        result = calc.calculate_profitability(
            hashrate=miner.reference_hashrate,
            power_consumption=miner.reference_power,
            electricity_cost=float(data.get('electricity_cost', current_app.config.get('DEFAULT_ELECTRICITY_COST', 0.06))),
            btc_price=network_data['btc_price'],
            network_hashrate=network_data['network_hashrate'],
            network_difficulty=network_data['network_difficulty']
        )
        
        return jsonify({'success': True, 'result': result})
        
    except Exception as e:
        logger.error(f"计算失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@calculator_bp.route('/api/network-stats')
def get_network_stats():
    """获取网络统计数据 - 从数据库读取（带缓存）"""
    try:
        # 从缓存获取最新的网络数据
        network_data = get_cached_network_snapshot()
        
        if network_data:
            return jsonify({
                'success': True,
                'btc_price': network_data['btc_price'],
                'network_hashrate': network_data['network_hashrate'],
                'network_difficulty': network_data['network_difficulty'],
                'block_reward': network_data['block_reward'],
                'timestamp': network_data['recorded_at'].isoformat()
            })
        else:
            return jsonify({'success': False, 'error': '无网络数据'})
            
    except Exception as e:
        logger.error(f"获取网络数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
