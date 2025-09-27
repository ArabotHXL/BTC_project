"""
加密货币支付路由
支付创建、状态查询、回调处理
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session, render_template

try:
    from ..services.crypto_payment import crypto_payment_service
    from ..services.compliance import compliance_service
    from .auth import require_wallet_auth
except ImportError:
    # Fallback for standalone execution
    from services.crypto_payment import crypto_payment_service
    from services.compliance import compliance_service
    from routes.auth import require_wallet_auth

logger = logging.getLogger(__name__)

# 创建蓝图
payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/supported-currencies', methods=['GET'])
def get_supported_currencies():
    """获取支持的加密货币列表"""
    try:
        currencies = crypto_payment_service.get_supported_currencies()
        prices = crypto_payment_service.get_current_prices()
        
        return jsonify({
            'success': True,
            'currencies': currencies,
            'current_prices': prices
        })
        
    except Exception as e:
        logger.error(f"获取支持的货币失败: {e}")
        return jsonify({'error': 'Failed to get currencies'}), 500

@payments_bp.route('/create', methods=['POST'])
@require_wallet_auth
def create_payment():
    """创建支付请求"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['amount_usd', 'crypto_currency']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # 添加用户信息
        data['user_id'] = session.get('user_id')
        
        # 验证金额
        amount_usd = float(data['amount_usd'])
        if amount_usd <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        # 验证货币类型
        crypto_currency = data['crypto_currency'].upper()
        if crypto_currency not in crypto_payment_service.get_supported_currencies():
            return jsonify({'error': 'Unsupported cryptocurrency'}), 400
        
        # 创建支付请求
        payment_request = crypto_payment_service.create_payment_request(data)
        
        return jsonify({
            'success': True,
            'payment': payment_request
        })
        
    except ValueError as e:
        logger.error(f"创建支付请求失败: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"创建支付请求失败: {e}")
        return jsonify({'error': 'Failed to create payment'}), 500

@payments_bp.route('/status/<payment_id>', methods=['GET'])
@require_wallet_auth
def get_payment_status(payment_id):
    """获取支付状态"""
    try:
        # 在实际实现中，这里应该从数据库查询支付信息
        # 暂时返回模拟状态
        
        # 验证支付是否属于当前用户
        user_id = session.get('user_id')
        
        # 模拟支付数据
        payment_data = {
            'payment_id': payment_id,
            'status': 'pending',
            'amount_usd': 100.0,
            'crypto_currency': 'BTC',
            'crypto_amount': 0.002,
            'payment_address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'transaction_hash': None,
            'confirmations': 0,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow()).isoformat()
        }
        
        # 检查实际支付状态
        status_result = crypto_payment_service.check_payment_status(
            payment_id,
            payment_data['payment_address'],
            payment_data['crypto_currency'],
            payment_data['crypto_amount']
        )
        
        # 更新状态
        payment_data.update(status_result)
        
        return jsonify({
            'success': True,
            'payment': payment_data
        })
        
    except Exception as e:
        logger.error(f"获取支付状态失败: {e}")
        return jsonify({'error': 'Failed to get payment status'}), 500

@payments_bp.route('/history', methods=['GET'])
@require_wallet_auth
def get_payment_history():
    """获取用户支付历史"""
    try:
        user_id = session.get('user_id')
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        
        # 在实际实现中，这里应该从数据库查询
        # 暂时返回空列表
        payments = []
        total_count = 0
        
        return jsonify({
            'success': True,
            'payments': payments,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"获取支付历史失败: {e}")
        return jsonify({'error': 'Failed to get payment history'}), 500

@payments_bp.route('/cancel/<payment_id>', methods=['POST'])
@require_wallet_auth
def cancel_payment(payment_id):
    """取消支付"""
    try:
        user_id = session.get('user_id')
        
        # 在实际实现中，这里应该验证支付归属并更新状态
        # 暂时返回成功
        
        return jsonify({
            'success': True,
            'message': 'Payment cancelled successfully'
        })
        
    except Exception as e:
        logger.error(f"取消支付失败: {e}")
        return jsonify({'error': 'Failed to cancel payment'}), 500

@payments_bp.route('/webhook/confirmation', methods=['POST'])
def payment_confirmation_webhook():
    """支付确认回调"""
    try:
        data = request.get_json()
        
        # 验证回调签名
        # 在实际实现中，这里应该验证来自区块链监控服务的签名
        
        payment_id = data.get('payment_id')
        transaction_hash = data.get('transaction_hash')
        confirmations = data.get('confirmations', 0)
        status = data.get('status')
        
        if not payment_id:
            return jsonify({'error': 'Missing payment_id'}), 400
        
        # 处理支付确认
        # 在实际实现中，这里应该更新数据库并触发相应的业务逻辑
        
        logger.info(f"支付确认回调: {payment_id}, 状态: {status}, 确认数: {confirmations}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"处理支付确认回调失败: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500

@payments_bp.route('/estimate-fee', methods=['POST'])
def estimate_transaction_fee():
    """估算交易费用"""
    try:
        data = request.get_json()
        crypto_currency = data.get('crypto_currency', '').upper()
        
        if crypto_currency not in crypto_payment_service.get_supported_currencies():
            return jsonify({'error': 'Unsupported cryptocurrency'}), 400
        
        # 获取当前网络费用估算
        # 在实际实现中，这里应该调用相应的区块链网络API
        
        fee_estimates = {
            'BTC': {
                'slow': {'fee': 0.0001, 'time_minutes': 60},
                'normal': {'fee': 0.0003, 'time_minutes': 20},
                'fast': {'fee': 0.0005, 'time_minutes': 10}
            },
            'ETH': {
                'slow': {'fee': 0.001, 'time_minutes': 15},
                'normal': {'fee': 0.003, 'time_minutes': 5},
                'fast': {'fee': 0.005, 'time_minutes': 2}
            },
            'USDC': {
                'slow': {'fee': 1.0, 'time_minutes': 15},
                'normal': {'fee': 3.0, 'time_minutes': 5},
                'fast': {'fee': 5.0, 'time_minutes': 2}
            }
        }
        
        return jsonify({
            'success': True,
            'currency': crypto_currency,
            'fee_estimates': fee_estimates.get(crypto_currency, {})
        })
        
    except Exception as e:
        logger.error(f"估算交易费用失败: {e}")
        return jsonify({'error': 'Failed to estimate fees'}), 500

@payments_bp.route('/statistics', methods=['GET'])
@require_wallet_auth
def get_payment_statistics():
    """获取支付统计信息"""
    try:
        user_id = session.get('user_id')
        
        # 获取统计信息
        stats = crypto_payment_service.get_payment_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"获取支付统计失败: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@payments_bp.route('/qr-code/<payment_id>', methods=['GET'])
@require_wallet_auth
def get_payment_qr_code(payment_id):
    """获取支付二维码"""
    try:
        user_id = session.get('user_id')
        
        # 在实际实现中，这里应该从数据库查询支付信息
        # 暂时返回模拟二维码
        
        qr_code_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'qr_code': qr_code_data
        })
        
    except Exception as e:
        logger.error(f"获取支付二维码失败: {e}")
        return jsonify({'error': 'Failed to get QR code'}), 500

# 前端页面路由
@payments_bp.route('/page/create')
@require_wallet_auth
def payment_create_page():
    """支付创建页面"""
    return render_template('payments/create.html')

@payments_bp.route('/page/status/<payment_id>')
@require_wallet_auth
def payment_status_page(payment_id):
    """支付状态页面"""
    return render_template('payments/status.html', payment_id=payment_id)

@payments_bp.route('/page/history')
@require_wallet_auth
def payment_history_page():
    """支付历史页面"""
    return render_template('payments/history.html')