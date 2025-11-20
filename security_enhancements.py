"""
安全增强模块
实现CSRF保护、输入验证、速率限制等安全功能
"""

import os
import re
import secrets
import hashlib
import logging
from functools import wraps
from datetime import datetime, timedelta
from flask import request, session, abort, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import html

logger = logging.getLogger(__name__)

class SecurityManager:
    """安全管理器"""
    
    def __init__(self, app=None):
        self.app = app
        self.rate_limits = {}
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用安全设置"""
        self.app = app
    
    @staticmethod
    def generate_csrf_token():
        """生成CSRF令牌 - iframe兼容性配置"""
        # 强制建立permanent session以解决iframe环境问题
        session.permanent = True
        session['_csrf_init'] = True
        
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(16)
        
        session.modified = True
        return session['csrf_token']
    
    @staticmethod
    def validate_csrf_token(token):
        """验证CSRF令牌"""
        if 'csrf_token' not in session:
            return False
        session_token = session['csrf_token']
        return secrets.compare_digest(session_token, token)
    
    @staticmethod
    def csrf_protect(f):
        """CSRF保护装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                # Extract CSRF token from multiple sources - FIXED for iframe compatibility
                token = None
                try:
                    # Primary method: direct dict access (Flask form handling quirk fix)
                    if 'csrf_token' in request.form:
                        token = request.form['csrf_token']
                    # Fallback methods
                    elif request.headers.get('X-CSRF-Token'):
                        token = request.headers.get('X-CSRF-Token')
                    elif request.is_json and request.json and 'csrf_token' in request.json:
                        token = request.json['csrf_token']
                except Exception:
                    pass  # Continue with token validation
                
                if not token or not SecurityManager.validate_csrf_token(token):
                    abort(403, 'CSRF token validation failed')
            
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def sanitize_input(text, allow_html=False):
        """清理输入数据"""
        if not text:
            return text
        
        # 转换为字符串
        text = str(text)
        
        # 移除控制字符
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # HTML转义
        if not allow_html:
            text = html.escape(text)
        
        return text.strip()
    
    @staticmethod
    def validate_email(email):
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password_strength(password):
        """验证密码强度"""
        if len(password) < 8:
            return False, "密码长度至少8位"
        
        if not re.search(r'[A-Z]', password):
            return False, "密码必须包含大写字母"
        
        if not re.search(r'[a-z]', password):
            return False, "密码必须包含小写字母"
        
        if not re.search(r'\d', password):
            return False, "密码必须包含数字"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "密码必须包含特殊字符"
        
        return True, "密码强度符合要求"
    
    @staticmethod
    def validate_number(value, min_val=None, max_val=None):
        """验证数字输入"""
        try:
            num = float(value)
            
            # 检查NaN和无限值
            if num != num or num == float('inf') or num == float('-inf'):
                return None
            
            # 范围检查
            if min_val is not None and num < min_val:
                return None
            if max_val is not None and num > max_val:
                return None
            
            return num
        except (ValueError, TypeError):
            return None
    
    def rate_limit(self, key, max_requests=100, window=3600):
        """速率限制检查"""
        now = datetime.now()
        
        # 清理过期记录
        self._cleanup_rate_limits()
        
        if key not in self.rate_limits:
            self.rate_limits[key] = []
        
        # 获取时间窗口内的请求
        window_start = now - timedelta(seconds=window)
        requests = [req for req in self.rate_limits[key] if req > window_start]
        
        # 检查限制
        if len(requests) >= max_requests:
            return False
        
        # 记录新请求
        requests.append(now)
        self.rate_limits[key] = requests
        
        return True
    
    def _cleanup_rate_limits(self):
        """清理过期的速率限制记录"""
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        
        for key in list(self.rate_limits.keys()):
            self.rate_limits[key] = [req for req in self.rate_limits[key] if req > cutoff]
            if not self.rate_limits[key]:
                del self.rate_limits[key]

def rate_limit_decorator(max_requests=100, window=3600):
    """速率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端标识
            client_id = request.remote_addr
            if 'user_id' in session:
                client_id = f"user_{session['user_id']}"
            
            # 检查速率限制
            if not g.get('security_manager'):
                g.security_manager = SecurityManager()
            
            if not g.security_manager.rate_limit(client_id, max_requests, window):
                logger.warning(f"Rate limit exceeded for {client_id}")
                return jsonify({'error': '请求过于频繁，请稍后再试'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 输入验证函数
def validate_mining_input(data):
    """验证挖矿计算输入"""
    errors = []
    
    # 算力验证
    hashrate = SecurityManager.validate_number(
        data.get('hashrate'), 
        min_val=0, 
        max_val=10000000
    )
    if hashrate is None:
        errors.append("算力必须是0到10,000,000之间的数字")
    
    # 功耗验证
    power = SecurityManager.validate_number(
        data.get('power'),
        min_val=0,
        max_val=100000
    )
    if power is None:
        errors.append("功耗必须是0到100,000之间的数字")
    
    # 电费验证
    electricity_cost = SecurityManager.validate_number(
        data.get('electricity_cost'),
        min_val=0,
        max_val=10
    )
    if electricity_cost is None:
        errors.append("电费必须是0到10之间的数字")
    
    # 池费验证
    pool_fee = SecurityManager.validate_number(
        data.get('pool_fee', 2),
        min_val=0,
        max_val=100
    )
    if pool_fee is None:
        errors.append("池费必须是0到100之间的百分比")
    
    if errors:
        return False, errors
    
    return True, {
        'hashrate': hashrate,
        'power': power,
        'electricity_cost': electricity_cost,
        'pool_fee': pool_fee
    }

def log_security_event(event_type, details, severity='info'):
    """记录安全事件"""
    timestamp = datetime.now().isoformat()
    client_ip = request.remote_addr
    user_id = session.get('user_id', 'anonymous')
    
    log_entry = {
        'timestamp': timestamp,
        'event_type': event_type,
        'client_ip': client_ip,
        'user_id': user_id,
        'details': details
    }
    
    if severity == 'critical':
        logger.critical(f"SECURITY: {log_entry}")
    elif severity == 'error':
        logger.error(f"SECURITY: {log_entry}")
    elif severity == 'warning':
        logger.warning(f"SECURITY: {log_entry}")
    else:
        logger.info(f"SECURITY: {log_entry}")

# 导出
__all__ = [
    'SecurityManager',
    'rate_limit_decorator',
    'validate_mining_input',
    'log_security_event'
]