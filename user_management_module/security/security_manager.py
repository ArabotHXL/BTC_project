"""
安全管理器模块
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
            if min_val is not None and num < min_val:
                return False, f"数值不能小于 {min_val}"
            if max_val is not None and num > max_val:
                return False, f"数值不能大于 {max_val}"
            return True, "数值验证通过"
        except (ValueError, TypeError):
            return False, "请输入有效的数字"
    
    @staticmethod
    def rate_limit(key, limit=100, period=3600):
        """简单的速率限制"""
        current_time = datetime.utcnow()
        
        # 清理过期记录
        if hasattr(g, 'rate_limits'):
            expired_keys = [k for k, v in g.rate_limits.items() 
                          if current_time - v['start_time'] > timedelta(seconds=period)]
            for k in expired_keys:
                del g.rate_limits[k]
        else:
            g.rate_limits = {}
        
        # 检查当前限制
        if key in g.rate_limits:
            if g.rate_limits[key]['count'] >= limit:
                return False
            g.rate_limits[key]['count'] += 1
        else:
            g.rate_limits[key] = {
                'count': 1,
                'start_time': current_time
            }
        
        return True
    
    @staticmethod
    def generate_secure_token(length=32):
        """生成安全令牌"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password):
        """哈希密码"""
        return generate_password_hash(password)
    
    @staticmethod
    def verify_password(password, password_hash):
        """验证密码"""
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def create_verification_code():
        """创建验证码"""
        return secrets.randbelow(1000000)  # 6位数字验证码
    
    @staticmethod
    def generate_api_key():
        """生成API密钥"""
        return f"umm_{secrets.token_urlsafe(32)}"  # umm = user management module
    
    @staticmethod
    def validate_ip_address(ip):
        """验证IP地址格式"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def secure_filename(filename):
        """生成安全的文件名"""
        # 移除危险字符
        filename = re.sub(r'[^\w\s-.]', '', filename)
        # 限制文件名长度
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext
        return filename
    
    @staticmethod
    def encrypt_sensitive_data(data, key=None):
        """加密敏感数据（简单实现）"""
        if key is None:
            key = os.environ.get('ENCRYPTION_KEY', 'default-key-change-in-prod')
        
        # 简单的XOR加密（生产环境应使用更强的加密）
        result = []
        for i, char in enumerate(str(data)):
            result.append(chr(ord(char) ^ ord(key[i % len(key)])))
        return ''.join(result)
    
    @staticmethod
    def decrypt_sensitive_data(encrypted_data, key=None):
        """解密敏感数据"""
        if key is None:
            key = os.environ.get('ENCRYPTION_KEY', 'default-key-change-in-prod')
        
        # XOR解密
        result = []
        for i, char in enumerate(encrypted_data):
            result.append(chr(ord(char) ^ ord(key[i % len(key)])))
        return ''.join(result)