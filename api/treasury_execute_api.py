"""
Treasury执行接口
Treasury Execution API

提供财资策略交易执行功能（占位实现）
"""

from flask import Blueprint, request, jsonify
from api_auth_middleware import require_api_auth
from common.rbac import require_permission, Permission
from features import FeatureFlags

treasury_execute_bp = Blueprint('treasury_execute_api', __name__, url_prefix='/api/treasury-exec')


def feature_check():
    """检查Treasury执行功能是否启用"""
    if not FeatureFlags.TREASURY_EXECUTION_ENABLED:
        return jsonify({
            'status': 'error',
            'message': 'Treasury execution is disabled. Set FEATURE_TREASURY_EXECUTION_ENABLED=true to enable.',
            'feature_enabled': False
        }), 503
    return None


@treasury_execute_bp.route('/execute', methods=['POST'])
@require_api_auth(required_permissions=[Permission.TREASURY_TRADE], allow_session_auth=True)
@require_permission([Permission.TREASURY_TRADE], require_all=True)
def execute_trade():
    """
    执行Treasury交易（占位实现）
    
    Request Body:
        - user_id: int (required)
        - strategy_name: str (required)
        - btc_amount: float (required)
        - exchange: str (default: "binance")
        - order_type: str (default: "market")
    
    Returns:
        JSON: 交易执行结果
    """
    check_result = feature_check()
    if check_result:
        return check_result
    
    data = request.get_json()
    
    if not data or 'user_id' not in data or 'strategy_name' not in data or 'btc_amount' not in data:
        return jsonify({
            'status': 'error',
            'message': 'user_id, strategy_name, and btc_amount are required'
        }), 400
    
    execution_result = {
        'trade_id': f"TRADE-{data['user_id']}-{hash(str(data))}",
        'user_id': data['user_id'],
        'strategy_name': data['strategy_name'],
        'btc_amount': data['btc_amount'],
        'exchange': data.get('exchange', 'binance'),
        'order_type': data.get('order_type', 'market'),
        'status': 'simulated',
        'execution_price': 50000.0,
        'total_usd': data['btc_amount'] * 50000.0,
        'fee_usd': data['btc_amount'] * 50000.0 * 0.001,
        'note': 'Placeholder: Real execution will connect to exchange API'
    }
    
    return jsonify({
        'status': 'success',
        'feature': 'treasury_execute',
        'enabled': True,
        'data': execution_result
    }), 200
