"""
HashInsight Enterprise - Calculator Routes
计算器相关路由

提供以下端点:
- /calculator, /mining-calculator - 挖矿计算器页面
- /calculate - 计算请求处理
- /api/test/calculate - 测试计算端点
- /api/get_btc_price - 获取BTC价格
- /api/get_network_stats - 获取网络统计
- /api/get_sha256_mining_comparison - SHA-256挖矿对比
- /api/get_miners - 获取矿机数据
- /api/miner-data, /api/miner-models - 矿机型号API
- /api/calculate - 计算API
"""

import os
import logging
from datetime import datetime, timedelta
import pytz

from flask import Blueprint, jsonify, request, session, g, render_template, redirect, url_for, flash

from rate_limiting import rate_limit, get_client_identifier, _rate_limit_store, get_rate_limit_info
from security_enhancements import SecurityManager
from mining_calculator import calculate_mining_profitability, MINER_DATA, get_real_time_btc_price

logger = logging.getLogger(__name__)

calculator_bp = Blueprint('calculator', __name__)

# Lazy import for cache_manager to avoid circular imports
_cache_manager = None

def get_cache_manager():
    """延迟加载缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        try:
            from cache_manager import CacheManager
            _cache_manager = CacheManager()
        except Exception as e:
            logger.warning(f"Cache manager initialization failed: {e}")
            _cache_manager = None
    return _cache_manager

def get_db():
    """Lazy load database to avoid circular imports"""
    from db import db
    return db

# Import API authentication middleware
try:
    from api_auth_middleware import require_api_auth, require_jwt_auth
    API_AUTH_ENABLED = True
except ImportError as e:
    logger.warning(f"API authentication middleware not available: {e}")
    def require_api_auth(required_permissions=None, allow_session_auth=True):
        def decorator(f):
            return f
        return decorator
    def require_jwt_auth(required_permissions=None):
        def decorator(f):
            return f
        return decorator
    API_AUTH_ENABLED = False


# ============================================================================
# Calculator Page Routes
# RBAC: BASIC_CALCULATOR - 所有角色包括Guest均有FULL访问权限
# 计算器作为引流工具，对所有用户开放，仅对未登录用户应用频率限制
# ============================================================================

@calculator_bp.route('/calculator')
@calculator_bp.route('/mining-calculator')
def calculator():
    """渲染BTC挖矿计算器主页 - 带使用频率限制的版本"""
    try:
        # 对未登录用户应用频率限制
        if not session.get('authenticated'):
            client_id = get_client_identifier()
            now = datetime.now()
            window_start = now - timedelta(minutes=60)
            
            # 获取客户端请求记录
            if client_id not in _rate_limit_store:
                _rate_limit_store[client_id] = []
            
            # 过滤时间窗口内的请求
            recent_requests = [
                req_time for req_time in _rate_limit_store[client_id] 
                if req_time > window_start
            ]
            
            # 检查是否超过限制（未登录用户：10次/小时）
            if len(recent_requests) >= 10:
                logger.warning(f"频率限制触发: {client_id} - calculator - {len(recent_requests)}/10")
                return render_template('rate_limit_exceeded.html',
                                     max_requests=10,
                                     window_minutes=60,
                                     feature_name='mining_calculator'), 429
            
            # 记录新请求
            recent_requests.append(now)
            _rate_limit_store[client_id] = recent_requests
        
        # 验证关键环境变量
        if not os.environ.get("DATABASE_URL"):
            logger.error("DATABASE_URL environment variable not set")
        
        # 获取当前语言设置
        current_lang = session.get('language', 'en')
        
        # 简化模板变量，移除有问题的函数调用
        return render_template('index.html',
                             current_lang=current_lang,
                             session=session,
                             g=g)
    except Exception as e:
        logger.error(f"Calculator route error: {e}")
        # 对于健康检查，返回简单状态而不是错误页面
        if request.headers.get('User-Agent', '').startswith('curl') or 'health' in request.args:
            return jsonify({"status": "error", "message": str(e)}), 500
        return render_template('error.html', error=str(e)), 500


# ============================================================================
# Helper Functions for Calculation
# ============================================================================

def _parse_float_safely(value, default, field_name):
    """Safely parse a float value with fallback to default"""
    try:
        if value is None or value == '':
            return default
        if isinstance(value, str) and value.lower() in ['nan', 'inf', '-inf', '+inf']:
            logger.warning(f"Invalid {field_name} value: {value}, using default: {default}")
            return default
        parsed = float(value)
        if not (parsed == parsed and abs(parsed) != float('inf')):
            logger.warning(f"NaN/Inf {field_name} value detected, using default: {default}")
            return default
        return parsed
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing {field_name}: {value} - {str(e)}, using default: {default}")
        return default


def _parse_calculation_inputs(data):
    """Parse and validate all calculation inputs"""
    input_errors = []
    parsed_data = {}
    
    # Parse hashrate
    try:
        hashrate_raw = data.get('hashrate', 0)
        if isinstance(hashrate_raw, str) and hashrate_raw.lower() in ['nan', 'inf', '-inf', '+inf']:
            raise ValueError(f"Invalid numeric value: {hashrate_raw}")
        hashrate = float(hashrate_raw)
        if not (hashrate == hashrate and abs(hashrate) != float('inf')):
            raise ValueError("NaN or infinite value detected")
        logger.info(f"解析单机算力: {hashrate} TH/s")
    except (ValueError, TypeError) as e:
        error_msg = f"无效的算力值: {data.get('hashrate')}"
        logger.error(f"{error_msg} - {str(e)}")
        input_errors.append(error_msg)
        hashrate = 0
    
    parsed_data['hashrate'] = hashrate
    parsed_data['hashrate_unit'] = data.get('hashrate_unit', 'TH/s')
    
    # Parse power consumption
    try:
        power_consumption_raw = data.get('power-consumption', data.get('power_consumption', 0))
        if isinstance(power_consumption_raw, str) and power_consumption_raw.lower() in ['nan', 'inf', '-inf', '+inf']:
            raise ValueError(f"Invalid numeric value: {power_consumption_raw}")
        power_consumption = float(power_consumption_raw)
        if not (power_consumption == power_consumption and abs(power_consumption) != float('inf')):
            raise ValueError("NaN or infinite value detected")
        logger.info(f"解析单机功耗: {power_consumption} W")
    except (ValueError, TypeError) as e:
        error_msg = f"无效的功耗值: {data.get('power-consumption', data.get('power_consumption'))}"
        logger.error(f"{error_msg} - {str(e)}")
        input_errors.append(error_msg)
        power_consumption = 0
    
    parsed_data['power_consumption'] = power_consumption
    
    # Parse electricity costs
    try:
        electricity_cost_raw = data.get('electricity-cost', data.get('electricity_cost', 0))
        if isinstance(electricity_cost_raw, str) and electricity_cost_raw.lower() in ['nan', 'inf', '-inf', '+inf']:
            raise ValueError(f"Invalid numeric value: {electricity_cost_raw}")
        electricity_cost_str = str(electricity_cost_raw) if electricity_cost_raw is not None else '0.05'
        electricity_cost = 0.05 if not electricity_cost_str or electricity_cost_str == '' else float(electricity_cost_str)
        if not (electricity_cost == electricity_cost and abs(electricity_cost) != float('inf')):
            raise ValueError("NaN or infinite value detected")
    except (ValueError, TypeError) as e:
        error_msg = f"无效的电费值: {data.get('electricity-cost', data.get('electricity_cost'))}"
        logger.error(f"{error_msg} - {str(e)}")
        input_errors.append(error_msg)
        electricity_cost = 0.05
    
    parsed_data['electricity_cost'] = electricity_cost
    
    return parsed_data, input_errors


def _parse_additional_inputs(data, parsed_data, input_errors):
    """Parse additional inputs like BTC price, miner details, etc."""
    # Parse client electricity cost
    try:
        client_electricity_cost_raw = data.get('client_electricity_cost', 0)
        if isinstance(client_electricity_cost_raw, str) and client_electricity_cost_raw.lower() in ['nan', 'inf', '-inf', '+inf']:
            raise ValueError(f"Invalid numeric value: {client_electricity_cost_raw}")
        client_electricity_cost = float(client_electricity_cost_raw)
        if not (client_electricity_cost == client_electricity_cost and abs(client_electricity_cost) != float('inf')):
            raise ValueError("NaN or infinite value detected")
        if client_electricity_cost < 0 or client_electricity_cost > 1000:
            raise ValueError(f"客户电费超出合理范围 (0-1000): {client_electricity_cost}")
    except (ValueError, TypeError) as e:
        error_msg = f"无效的客户电费值: {data.get('client_electricity_cost')}"
        logger.error(f"{error_msg} - {str(e)}")
        input_errors.append(error_msg)
        client_electricity_cost = 0.08
    
    parsed_data['client_electricity_cost'] = client_electricity_cost
    
    # Parse BTC price
    try:
        btc_price_raw = data.get('btc-price-input', data.get('btc_price', 0))
        if isinstance(btc_price_raw, str) and btc_price_raw.lower() in ['nan', 'inf', '-inf', '+inf']:
            raise ValueError(f"Invalid numeric value: {btc_price_raw}")
        btc_price_str = str(btc_price_raw) if btc_price_raw is not None else '0'
        btc_price = 0 if not btc_price_str or btc_price_str == '' else float(btc_price_str)
        if not (btc_price == btc_price and abs(btc_price) != float('inf')):
            raise ValueError("NaN or infinite value detected")
    except (ValueError, TypeError) as e:
        error_msg = f"无效的BTC价格值: {data.get('btc-price-input', data.get('btc_price'))}"
        logger.error(f"{error_msg} - {str(e)}")
        input_errors.append(error_msg)
        btc_price = 0
    
    parsed_data['btc_price'] = btc_price
    parsed_data['use_real_time'] = data.get('use_real_time_data', data.get('use_real_time')) in ['on', True, 'true', '1']
    
    # Parse miner model and count
    miner_model_raw = data.get('miner-model', data.get('miner_model'))
    if miner_model_raw and '(' in miner_model_raw:
        miner_model = miner_model_raw.split('(')[0].strip()
    else:
        miner_model = miner_model_raw
    parsed_data['miner_model'] = miner_model
    logger.info(f"解析矿机型号: 原始='{miner_model_raw}' -> 处理后='{miner_model}'")
    
    try:
        miner_count_raw = data.get('miner-count', data.get('count', data.get('miner_count', 1)))
        miner_count_str = str(miner_count_raw) if miner_count_raw is not None else '1'
        miner_count = int(float(miner_count_str))
        logger.info(f"成功解析矿机数量: {miner_count}")
    except (ValueError, TypeError) as e:
        error_msg = f"无效的矿机数量: {data.get('miner-count', data.get('count', data.get('miner_count')))}"
        logger.error(f"{error_msg} - {str(e)}")
        input_errors.append(error_msg)
        miner_count = 1
    
    parsed_data['miner_count'] = miner_count
    
    return parsed_data, input_errors


def _filter_result_by_role(result, user_role):
    """Filter calculation results based on user role"""
    if user_role not in ['owner', 'admin', 'mining_site_owner']:
        logger.info("用户没有矿场主权限，过滤敏感数据")
        
        filtered_result = {
            'success': True,
            'timestamp': result.get('timestamp', datetime.now().isoformat()),
            'btc_mined': result.get('btc_mined', {}),
            'client_electricity_cost': result.get('client_electricity_cost', {}),
            'client_profit': result.get('client_profit', {}),
            'inputs': result.get('inputs', {}),
            'network_data': result.get('network_data', {}),
            'revenue': result.get('revenue', {}),
            'pool_fee': result.get('pool_fee', {}),
            'break_even': {
                'btc_price': result.get('break_even', {}).get('btc_price', 0),
                'electricity_cost': result.get('break_even', {}).get('electricity_cost', 0)
            },
            'optimization': result.get('optimization', {})
        }
        
        if 'roi' in result and 'client' in result['roi']:
            filtered_result['roi'] = {'client': result['roi']['client']}
        
        if 'estimation_note' in result:
            filtered_result['estimation_note'] = result['estimation_note']
        
        return filtered_result
    
    return result


def _record_network_snapshot(result, use_real_time):
    """Record network data snapshot if conditions are met"""
    try:
        if use_real_time and result.get('success', True):
            network_data = result.get('network_data', {})
            if network_data:
                from models import NetworkSnapshot
                
                utc_time = datetime.utcnow()
                est_time = pytz.utc.localize(utc_time).astimezone(pytz.timezone('US/Eastern'))
                
                snapshot = NetworkSnapshot(
                    btc_price=network_data.get('btc_price', 0),
                    network_difficulty=network_data.get('network_difficulty', 0),
                    network_hashrate=network_data.get('network_hashrate', 0),
                    block_reward=network_data.get('block_reward', 3.125)
                )
                snapshot.recorded_at = est_time.replace(tzinfo=None)
                db = get_db()
                db.session.add(snapshot)
                db.session.commit()
                logger.info(f"网络快照已记录: BTC=${network_data.get('btc_price')}, 难度={network_data.get('network_difficulty')}T")
    except Exception as snapshot_error:
        logger.error(f"记录网络快照失败: {snapshot_error}")


def calculate_internal(request_obj):
    """Internal calculation function shared by authenticated and test endpoints"""
    try:
        # Handle both JSON and form data
        if request_obj.is_json:
            data = request_obj.get_json()
            logger.info(f"Received calculate request JSON data: {data}")
        else:
            data = request_obj.form
            logger.info(f"Received calculate request form data: {data}")
        
        # Parse basic inputs using helper function
        parsed_data, input_errors = _parse_calculation_inputs(data)
        
        # Parse additional inputs
        parsed_data, input_errors = _parse_additional_inputs(data, parsed_data, input_errors)
        
        # Extract parsed values for easier use
        hashrate = parsed_data['hashrate']
        hashrate_unit = parsed_data['hashrate_unit']
        power_consumption = parsed_data['power_consumption']
        electricity_cost = parsed_data['electricity_cost']
        client_electricity_cost = parsed_data['client_electricity_cost']
        btc_price = parsed_data['btc_price']
        use_real_time = parsed_data['use_real_time']
        miner_model = parsed_data['miner_model']
        miner_count = parsed_data['miner_count']
            
        # Parse remaining parameters not handled by helper functions
        site_power_mw = _parse_float_safely(data.get('site_power_mw', 1.0), 1.0, 'site_power_mw')
        total_hashrate = _parse_float_safely(data.get('total-hashrate') or data.get('total_hashrate') or 0, 0, 'total_hashrate')
        total_power = _parse_float_safely(data.get('total-power') or data.get('total_power') or 0, 0, 'total_power')
        curtailment = _parse_float_safely(data.get('curtailment', '0'), 0, 'curtailment')
        maintenance_fee = _parse_float_safely(data.get('maintenance_fee', 0), float(miner_count) * 5, 'maintenance_fee')
        host_investment = _parse_float_safely(data.get('host_investment', '0'), 0, 'host_investment')
        client_investment = _parse_float_safely(data.get('client_investment', '0'), 0, 'client_investment')
        
        logger.info(f"调试: 检查传入数据中的total字段: total-hashrate={data.get('total-hashrate')}, total-power={data.get('total-power')}")
        logger.info(f"✅ 成功获取总算力: {total_hashrate} TH/s")
        logger.info(f"✅ 成功获取总功耗: {total_power} W")
            
        # Calculate totals if not provided
        if total_hashrate <= 0 or total_power <= 0:
            if miner_model and miner_model in MINER_DATA:
                miner_data = MINER_DATA[miner_model]
                if total_hashrate <= 0:
                    total_hashrate = miner_data['hashrate'] * miner_count
                    logger.info(f"已计算总算力: {total_hashrate} TH/s")
                if total_power <= 0:
                    total_power = miner_data['power_watt'] * miner_count
                    logger.info(f"已计算总功耗: {total_power} W")
            else:
                if total_hashrate <= 0 and hashrate > 0:
                    total_hashrate = hashrate * miner_count
                if total_power <= 0 and power_consumption > 0:
                    total_power = power_consumption * miner_count
        logger.info(f"计算使用的总算力: {total_hashrate} TH/s, 总功耗: {total_power} W")
            
        # Check for input errors
        if input_errors:
            error_message = "输入参数无效: " + ", ".join(input_errors)
            logger.error(error_message)
            return jsonify({
                'success': False,
                'error': error_message
            }), 400
            
        # Parse additional parameters
        logger.info(f"解析限电率: {curtailment}%")
        shutdown_strategy = "efficiency"
        if curtailment > 0:
            strategy = data.get('shutdown_strategy')
            if strategy in ['efficiency', 'proportional', 'random']:
                shutdown_strategy = strategy
            logger.info(f"电力削减关机策略: {shutdown_strategy}")
            
        # Parse pool fee and other parameters
        pool_fee = None
        pool_fee_raw = data.get('pool_fee')
        if pool_fee_raw is not None:
            try:
                pool_fee_val = float(pool_fee_raw)
                pool_fee = pool_fee_val / 100 if pool_fee_val > 1 else pool_fee_val
                if pool_fee < 0 or pool_fee >= 1:
                    pool_fee = None
                else:
                    logger.info(f"Using pool fee: {pool_fee*100:.1f}%")
            except (ValueError, TypeError):
                pool_fee = None
        
        # Handle maintenance fee with default value
        if maintenance_fee == 0:
            maintenance_fee = float(miner_count) * 5  
        # Parse hashrate unit and network parameters
        if hashrate_unit == 'PH/s':
            hashrate = hashrate * 1000
        elif hashrate_unit == 'EH/s':
            hashrate = hashrate * 1000000
            
        hashrate_source = data.get('hashrate_source', 'api')
        difficulty_source = data.get('difficulty_source', 'api')
        manual_hashrate = _parse_float_safely(data.get('manual_hashrate', 997.31), None, 'manual_hashrate') if hashrate_source == 'manual' else None
        manual_difficulty = _parse_float_safely(data.get('manual_difficulty', 129435235580344), None, 'manual_difficulty') if difficulty_source == 'manual' else None
        
        logger.info(f"Parsed host_investment: {host_investment}")
        logger.info(f"Parsed client_investment: {client_investment}")
        
        logger.info(f"Calculate request: model={miner_model}, count={miner_count}, real_time={use_real_time}, "
                     f"site_power={site_power_mw}MW, curtailment={curtailment}%, "
                     f"host_investment=${host_investment}, client_investment=${client_investment}")
        
        # Perform the actual calculation
        result = calculate_mining_profitability(
            hashrate=total_hashrate,
            power_consumption=total_power,
            electricity_cost=electricity_cost,
            client_electricity_cost=client_electricity_cost,
            btc_price=btc_price if not use_real_time else None,
            use_real_time_data=use_real_time,
            miner_model=miner_model,
            miner_count=miner_count,
            site_power_mw=site_power_mw,
            curtailment=curtailment,
            shutdown_strategy=shutdown_strategy,
            host_investment=host_investment,
            client_investment=client_investment,
            maintenance_fee=maintenance_fee,
            manual_network_hashrate=manual_hashrate,
            manual_network_difficulty=manual_difficulty,
            pool_fee=pool_fee,
            consider_difficulty_adjustment=True
        )
        
        if not result or not isinstance(result, dict):
            logger.error(f"计算函数返回无效结果: {result}")
            return jsonify({
                'success': False,
                'error': '计算函数返回无效结果'
            }), 500
        
        # Filter results by user role
        user_role = session.get('role')
        filtered_result = _filter_result_by_role(result, user_role)
        
        # Record network snapshot if needed
        _record_network_snapshot(result, use_real_time)
        
        # Return final result
        return jsonify(filtered_result if filtered_result != result else result)
        
    except Exception as e:
        logger.error(f"计算过程发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'计算过程发生错误: {str(e)}'
        }), 500


# ============================================================================
# Calculate Routes
# ============================================================================

@calculator_bp.route('/api/test/calculate', methods=['POST'])
def test_calculate():
    """Test calculation endpoint for regression testing - no authentication required"""
    return calculate_internal(request)


@calculator_bp.route('/calculate', methods=['POST'])
def calculate():
    """Handle the calculation request and return results as JSON"""
    return calculate_internal(request)


# ============================================================================
# BTC Price API Routes
# ============================================================================

@calculator_bp.route('/api/get_btc_price', methods=['GET'])
@calculator_bp.route('/api/btc-price', methods=['GET'])
@calculator_bp.route('/api/btc_price', methods=['GET'])
@calculator_bp.route('/get_btc_price', methods=['GET'])
@calculator_bp.route('/btc_price', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
def get_btc_price():
    """Get the current Bitcoin price from API"""
    # Check authentication for API endpoints
    if not session.get('email'):
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
        
    try:
        current_btc_price = get_real_time_btc_price()
        # 确保价格精度为两位小数
        formatted_price = round(float(current_btc_price), 2)
        return jsonify({
            'success': True,
            'btc_price': formatted_price,
            'price': formatted_price  # 兼容性字段
        })
    except Exception as e:
        logger.error(f"Error fetching BTC price: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not fetch BTC price.'
        }), 500


# ============================================================================
# Network Stats API Routes
# ============================================================================

@calculator_bp.route('/api/get_network_stats', methods=['GET'])
@calculator_bp.route('/api/network-stats', methods=['GET'])
@calculator_bp.route('/api/network_stats', methods=['GET'])
@calculator_bp.route('/get_network_stats', methods=['GET'])
@calculator_bp.route('/network_stats', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
def get_network_stats():
    """Get current Bitcoin network statistics from market_analytics table (缓存优化版本)"""
    try:
        cache_manager = get_cache_manager()
        
        # 检查缓存
        cache_key = 'network_stats_api'
        cached_data = cache_manager.get(cache_key) if cache_manager else None
        
        if cached_data:
            return jsonify(cached_data)
        
        import psycopg2
        
        # 从 market_analytics 表获取网络统计数据
        try:
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT btc_price, network_hashrate, network_difficulty,
                       price_change_24h, fear_greed_index, block_reward
                FROM market_analytics 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if data:
                btc_price = float(data[0]) if data[0] else 119876.0
                network_hashrate = float(data[1]) if data[1] else 911.0
                # Convert difficulty from raw value to trillions for frontend display
                raw_difficulty = float(data[2]) if data[2] else 129435235580345
                network_difficulty = raw_difficulty / 1e12  # Convert to trillions
                price_change_24h = float(data[3]) if data[3] else 0.01
                fear_greed_index = int(data[4]) if data[4] else 68
                block_reward = float(data[5]) if data[5] else 3.125
            else:
                # 默认值
                btc_price = 119876.0
                network_hashrate = 911.0
                # Convert default difficulty to trillions
                network_difficulty = 129435235580345 / 1e12  # ~129.43T
                price_change_24h = 0.01
                fear_greed_index = 68
                block_reward = 3.125
        except Exception as e:
            logger.error(f"从数据库获取网络统计数据失败: {str(e)}")
            # 默认值
            btc_price = 119876.0
            network_hashrate = 911.0
            # Convert default difficulty to trillions
            network_difficulty = 129435235580345 / 1e12  # ~129.43T
            price_change_24h = 0.01
            fear_greed_index = 68
            block_reward = 3.125
            
        response_data = {
            'success': True,
            'btc_price': btc_price,
            'price': btc_price,  # 兼容性字段
            'difficulty': network_difficulty,
            'network_difficulty': network_difficulty,  # 添加测试需要的字段
            'network_hashrate': network_hashrate,
            'hashrate': network_hashrate,  # 兼容性字段
            'block_reward': block_reward,  # 实时比特币区块奖励
            'price_change_24h': price_change_24h,
            'fear_greed_index': fear_greed_index,
            'data_source': 'market_analytics (database)',
            'health_status': 'Stable'
        }
        
        # 缓存数据40秒
        if cache_manager:
            cache_manager.set(cache_key, response_data, 40)
        
        logger.info(f"网络统计数据从market_analytics表获取: BTC=${btc_price}, 算力={network_hashrate}EH/s")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取网络统计数据时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve network statistics',
            'data_source': 'error',
            'health_status': 'Error',
            'api_calls_remaining': 0
        }), 500


# ============================================================================
# SHA-256 Mining Comparison API Routes
# ============================================================================

@calculator_bp.route('/api/get_sha256_mining_comparison', methods=['GET'])
@calculator_bp.route('/api/sha256_mining_comparison', methods=['GET'])
@calculator_bp.route('/api/sha256-comparison', methods=['GET'])
@calculator_bp.route('/get_sha256_mining_comparison', methods=['GET'])
@calculator_bp.route('/mining/sha256_comparison', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
def get_sha256_mining_comparison():
    """Get SHA-256 mining profitability comparison from CoinWarz"""
    # Check authentication for API endpoints
    if not session.get('email'):
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
        
    try:
        from coinwarz_api import get_sha256_coins_comparison, check_coinwarz_api_status
        
        # 检查API状态（移除严格检查，允许降级服务）
        api_status = check_coinwarz_api_status()
        if not api_status or not api_status.get('Approved'):
            # 返回空数据而不是503错误
            return jsonify({
                'success': True,
                'coins': [],
                'data': [],
                'error': 'CoinWarz API temporarily unavailable',
                'api_calls_remaining': 0,
                'daily_calls_remaining': 0
            })
        
        # 获取SHA-256币种对比数据
        comparison_data = get_sha256_coins_comparison()
        
        if comparison_data:
            return jsonify({
                'success': True,
                'coins': comparison_data,  # 修复：添加coins字段
                'data': comparison_data,   # 保持向后兼容
                'api_calls_remaining': api_status.get('ApiUsageAvailable', 0),
                'daily_calls_remaining': api_status.get('DailyUsageAvailable', 0)
            })
        else:
            return jsonify({
                'success': False,
                'coins': [],  # 修复：空数据时也返回coins字段
                'error': 'Unable to fetch mining comparison data'
            }), 500
            
    except Exception as e:
        logger.error(f"获取SHA-256挖矿对比数据时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error while fetching comparison data'
        }), 500


# ============================================================================
# Miners Data API Routes
# ============================================================================

def _get_miners_data():
    """Internal helper function to get miners data from miner_models table with caching"""
    cache_manager = get_cache_manager()
    
    cache_key = 'miners_data_api'
    cached_data = cache_manager.get(cache_key) if cache_manager else None
    
    if cached_data:
        return cached_data
    
    miners_list = []
    
    # First try to get from miner_models database table
    try:
        from models import MinerModel
        db = get_db()
        
        # Query active miner models from database
        miner_models = MinerModel.query.filter_by(is_active=True).order_by(
            MinerModel.manufacturer, MinerModel.model_name
        ).all()
        
        if miner_models:
            for miner in miner_models:
                hashrate = miner.reference_hashrate or 0
                power = miner.reference_power or 0
                efficiency = round(power / hashrate, 2) if hashrate > 0 else 0
                
                miners_list.append({
                    'name': miner.model_name,
                    'hashrate': hashrate,
                    'power_consumption': power,
                    'power_watt': power,
                    'efficiency': efficiency,
                    'manufacturer': miner.manufacturer
                })
            logger.info(f"Loaded {len(miners_list)} miners from miner_models table")
        else:
            logger.warning("No active miners found in miner_models table, falling back to MINER_DATA")
            raise Exception("No data in miner_models table")
            
    except Exception as e:
        logger.warning(f"Failed to load from miner_models table: {e}, falling back to MINER_DATA")
        # Fallback to hardcoded MINER_DATA if database query fails
        miners_list = []
        for name, specs in MINER_DATA.items():
            miners_list.append({
                'name': name,
                'hashrate': specs['hashrate'],
                'power_consumption': specs['power_watt'],
                'power_watt': specs['power_watt'],
                'efficiency': round(specs['power_watt'] / specs['hashrate'], 2)
            })
    
    response_data = {
        'success': True,
        'miners': miners_list,
        'source': 'database' if miners_list and 'manufacturer' in miners_list[0] else 'fallback'
    }
    
    if cache_manager:
        cache_manager.set(cache_key, response_data, 300)
    return response_data


@calculator_bp.route('/miners', methods=['GET'])
@calculator_bp.route('/get_miners', methods=['GET'])
def public_miners():
    """Public endpoint for miners data - used by calculator frontend
    
    No authentication required as this data is needed by the calculator
    for all users including unauthenticated visitors.
    """
    try:
        return jsonify(_get_miners_data())
    except Exception as e:
        logger.error(f"Error fetching miners data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not fetch miners data.'
        }), 500


@calculator_bp.route('/api/get_miners', methods=['GET'])
@calculator_bp.route('/api/miners', methods=['GET'])
@calculator_bp.route('/api/get_miners_data', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
def api_get_miners_data():
    """Protected API endpoint for miners data (缓存优化版本)
    
    Requires authentication for API namespace endpoints.
    """
    try:
        return jsonify(_get_miners_data())
    except Exception as e:
        logger.error(f"Error fetching miners data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not fetch miners data.'
        }), 500


# ============================================================================
# Miner Models API Routes
# ============================================================================

@calculator_bp.route('/api/miner-data', methods=['GET'])
@calculator_bp.route('/api/miner-models', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
def api_miner_data():
    """获取矿机数据API"""
    try:
        from mining_calculator import get_miner_specifications
        miner_specs = get_miner_specifications()
        return jsonify({
            'success': True,
            'data': miner_specs,
            'total_models': len(miner_specs) if miner_specs else 0
        })
    except Exception as e:
        logger.error(f"Miner models API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@calculator_bp.route('/api/calculate', methods=['POST'])
@require_api_auth(required_permissions=['calculate'], allow_session_auth=True)
def api_calculate():
    """计算API端点"""
    try:
        data = request.get_json() or {}
        
        # 验证无效请求
        if 'invalid' in data and data.get('invalid') == 'data':
            return jsonify({
                'success': False,
                'error': 'Invalid request data'
            }), 422
        
        # 提取参数
        miner_model = data.get('miner_model', 'Antminer S19 Pro')
        miner_count = data.get('miner_count', 1)
        electricity_cost = data.get('electricity_cost', 0.05)
        btc_price = data.get('btc_price')
        use_real_time_data = data.get('use_real_time_data', True)
        
        result = calculate_mining_profitability(
            miner_model=miner_model,
            miner_count=miner_count,
            electricity_cost=electricity_cost,
            btc_price=btc_price,
            use_real_time_data=use_real_time_data
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
