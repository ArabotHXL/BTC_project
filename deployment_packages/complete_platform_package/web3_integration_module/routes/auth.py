"""
Web3认证路由
钱包连接、签名验证、会话管理
"""

import os
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from eth_account.messages import encode_defunct
from eth_account import Account

try:
    from ..models import User, WalletSession
    from ..services.compliance import compliance_service
except ImportError:
    # Fallback for standalone execution
    from models import User, WalletSession
    from services.compliance import compliance_service

logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/wallet/connect', methods=['POST'])
def connect_wallet():
    """钱包连接请求"""
    try:
        data = request.get_json()
        wallet_address = data.get('wallet_address', '').lower()
        wallet_provider = data.get('wallet_provider', 'metamask')
        
        if not wallet_address:
            return jsonify({'error': 'Missing wallet address'}), 400
        
        # 验证地址格式
        if not _is_valid_eth_address(wallet_address):
            return jsonify({'error': 'Invalid wallet address format'}), 400
        
        # 生成随机数用于签名验证
        nonce = secrets.token_hex(16)
        message = f"Sign this message to authenticate with Web3 Integration Module.\n\nNonce: {nonce}\nTimestamp: {int(time.time())}"
        
        # 临时存储待验证信息
        session_data = {
            'wallet_address': wallet_address,
            'wallet_provider': wallet_provider,
            'nonce': nonce,
            'message': message,
            'expires_at': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
        
        session['pending_auth'] = session_data
        
        return jsonify({
            'success': True,
            'message': message,
            'nonce': nonce,
            'expires_in': 300  # 5分钟
        })
        
    except Exception as e:
        logger.error(f"钱包连接失败: {e}")
        return jsonify({'error': 'Connection failed'}), 500

@auth_bp.route('/wallet/verify', methods=['POST'])
def verify_wallet_signature():
    """验证钱包签名并完成认证"""
    try:
        data = request.get_json()
        signature = data.get('signature')
        
        if not signature:
            return jsonify({'error': 'Missing signature'}), 400
        
        # 获取待验证信息
        pending_auth = session.get('pending_auth')
        if not pending_auth:
            return jsonify({'error': 'No pending authentication'}), 400
        
        # 检查是否过期
        expires_at = datetime.fromisoformat(pending_auth['expires_at'])
        if datetime.utcnow() > expires_at:
            session.pop('pending_auth', None)
            return jsonify({'error': 'Authentication expired'}), 400
        
        wallet_address = pending_auth['wallet_address']
        message = pending_auth['message']
        
        # 验证签名
        if not _verify_signature(message, signature, wallet_address):
            return jsonify({'error': 'Invalid signature'}), 401
        
        # 合规检查
        compliance_result = compliance_service.check_user_kyc_status(0)  # 使用钱包地址作为用户标识
        
        # 查找或创建用户
        user = _find_or_create_user(wallet_address, pending_auth['wallet_provider'])
        
        # 创建钱包会话
        wallet_session = _create_wallet_session(
            user.id, wallet_address, pending_auth['wallet_provider'], 
            signature, message, pending_auth['nonce']
        )
        
        # 清除待验证信息
        session.pop('pending_auth', None)
        
        # 设置会话
        session['user_id'] = user.id
        session['wallet_address'] = wallet_address
        session['session_token'] = wallet_session.session_token
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'wallet_address': user.wallet_address,
                'wallet_verified': user.wallet_verified
            },
            'session_token': wallet_session.session_token,
            'expires_at': wallet_session.expires_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"签名验证失败: {e}")
        return jsonify({'error': 'Verification failed'}), 500

@auth_bp.route('/wallet/disconnect', methods=['POST'])
def disconnect_wallet():
    """断开钱包连接"""
    try:
        session_token = session.get('session_token')
        
        if session_token:
            # 标记会话为非活跃
            _deactivate_wallet_session(session_token)
        
        # 清除会话
        session.clear()
        
        return jsonify({'success': True, 'message': 'Disconnected successfully'})
        
    except Exception as e:
        logger.error(f"断开连接失败: {e}")
        return jsonify({'error': 'Disconnect failed'}), 500

@auth_bp.route('/status', methods=['GET'])
def get_auth_status():
    """获取认证状态"""
    try:
        user_id = session.get('user_id')
        session_token = session.get('session_token')
        
        if not user_id or not session_token:
            return jsonify({'authenticated': False})
        
        # 验证会话是否仍然有效
        wallet_session = _get_active_wallet_session(session_token)
        if not wallet_session:
            session.clear()
            return jsonify({'authenticated': False})
        
        # 获取用户信息
        user = _get_user_by_id(user_id)
        if not user:
            return jsonify({'authenticated': False})
        
        return jsonify({
            'authenticated': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'wallet_address': user.wallet_address,
                'wallet_verified': user.wallet_verified,
                'kyc_status': user.kyc_status.value if hasattr(user.kyc_status, 'value') else str(user.kyc_status)
            },
            'session': {
                'expires_at': wallet_session.expires_at.isoformat(),
                'last_activity': wallet_session.last_activity.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"获取认证状态失败: {e}")
        return jsonify({'error': 'Status check failed'}), 500

@auth_bp.route('/session/refresh', methods=['POST'])
def refresh_session():
    """刷新会话"""
    try:
        session_token = session.get('session_token')
        
        if not session_token:
            return jsonify({'error': 'No active session'}), 401
        
        # 更新会话活动时间
        wallet_session = _refresh_wallet_session(session_token)
        
        if not wallet_session:
            session.clear()
            return jsonify({'error': 'Session expired'}), 401
        
        return jsonify({
            'success': True,
            'expires_at': wallet_session.expires_at.isoformat(),
            'last_activity': wallet_session.last_activity.isoformat()
        })
        
    except Exception as e:
        logger.error(f"刷新会话失败: {e}")
        return jsonify({'error': 'Session refresh failed'}), 500

# 工具函数

def _is_valid_eth_address(address: str) -> bool:
    """验证以太坊地址格式"""
    try:
        return len(address) == 42 and address.startswith('0x') and all(c in '0123456789abcdefABCDEF' for c in address[2:])
    except:
        return False

def _verify_signature(message: str, signature: str, wallet_address: str) -> bool:
    """验证签名"""
    try:
        # 创建消息哈希
        message_hash = encode_defunct(text=message)
        
        # 恢复签名者地址
        recovered_address = Account.recover_message(message_hash, signature=signature)
        
        # 比较地址
        return recovered_address.lower() == wallet_address.lower()
        
    except Exception as e:
        logger.error(f"签名验证失败: {e}")
        return False

def _find_or_create_user(wallet_address: str, wallet_provider: str):
    """查找或创建用户"""
    try:
        # 在实际实现中，这里应该查询数据库
        # 暂时创建一个模拟用户对象
        class MockUser:
            def __init__(self):
                self.id = 1
                self.username = f"user_{wallet_address[:8]}"
                self.email = f"{wallet_address[:8]}@example.com"
                self.wallet_address = wallet_address
                self.wallet_provider = wallet_provider
                self.wallet_verified = True
                self.wallet_verified_at = datetime.utcnow()
                self.kyc_status = "pending"
                self.created_at = datetime.utcnow()
        
        return MockUser()
        
    except Exception as e:
        logger.error(f"查找或创建用户失败: {e}")
        raise

def _create_wallet_session(user_id: int, wallet_address: str, wallet_provider: str, 
                          signature: str, message: str, nonce: str):
    """创建钱包会话"""
    try:
        # 生成会话令牌
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # 在实际实现中，这里应该保存到数据库
        class MockWalletSession:
            def __init__(self):
                self.id = 1
                self.user_id = user_id
                self.wallet_address = wallet_address
                self.wallet_provider = wallet_provider
                self.session_token = session_token
                self.signature = signature
                self.message = message
                self.nonce = nonce
                self.is_active = True
                self.expires_at = expires_at
                self.ip_address = request.remote_addr
                self.user_agent = request.headers.get('User-Agent', '')
                self.created_at = datetime.utcnow()
                self.last_activity = datetime.utcnow()
        
        return MockWalletSession()
        
    except Exception as e:
        logger.error(f"创建钱包会话失败: {e}")
        raise

def _get_active_wallet_session(session_token: str):
    """获取活跃的钱包会话"""
    try:
        # 在实际实现中，这里应该查询数据库
        # 暂时返回模拟会话
        if session_token:
            return _create_wallet_session(1, "0x123", "metamask", "sig", "msg", "nonce")
        return None
        
    except Exception as e:
        logger.error(f"获取钱包会话失败: {e}")
        return None

def _get_user_by_id(user_id: int):
    """根据ID获取用户"""
    try:
        # 在实际实现中，这里应该查询数据库
        return _find_or_create_user("0x123", "metamask")
        
    except Exception as e:
        logger.error(f"获取用户失败: {e}")
        return None

def _deactivate_wallet_session(session_token: str):
    """停用钱包会话"""
    try:
        # 在实际实现中，这里应该更新数据库
        logger.info(f"会话已停用: {session_token}")
        
    except Exception as e:
        logger.error(f"停用会话失败: {e}")

def _refresh_wallet_session(session_token: str):
    """刷新钱包会话"""
    try:
        # 在实际实现中，这里应该更新数据库
        session = _get_active_wallet_session(session_token)
        if session:
            session.last_activity = datetime.utcnow()
            session.expires_at = datetime.utcnow() + timedelta(hours=24)
        return session
        
    except Exception as e:
        logger.error(f"刷新会话失败: {e}")
        return None

# 装饰器
def require_wallet_auth(f):
    """要求钱包认证的装饰器"""
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        session_token = session.get('session_token')
        
        if not user_id or not session_token:
            return jsonify({'error': 'Authentication required'}), 401
        
        # 验证会话
        wallet_session = _get_active_wallet_session(session_token)
        if not wallet_session:
            session.clear()
            return jsonify({'error': 'Session expired'}), 401
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function