# Safari iframe Session Assertion Service
# 用于在Safari iframe环境中安全地传递用户会话信息
# 使用签名token防止篡改，仅用于UI显示，所有授权仍在服务器端进行

import os
import logging
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

class SessionAssertionService:
    """
    会话断言服务 - 为Safari iframe环境签发短期token
    
    安全特性：
    1. 使用SECRET_KEY签名，防止篡改
    2. 5分钟过期时间，减少风险
    3. 仅包含必要的显示信息（email、role）
    4. 服务器端验证，客户端无法伪造
    """
    
    def __init__(self, secret_key=None):
        """
        初始化服务
        
        Args:
            secret_key: 用于签名的密钥，默认使用SESSION_SECRET环境变量
        """
        self.secret_key = secret_key or os.environ.get('SESSION_SECRET')
        if not self.secret_key:
            raise ValueError("SESSION_SECRET environment variable must be set")
        
        # 创建签名序列化器
        self.serializer = URLSafeTimedSerializer(
            self.secret_key,
            salt='session-assertion'  # 添加salt增加安全性
        )
        
        # Token过期时间（秒）
        self.token_max_age = 5 * 60  # 5分钟
        
        logging.info("SessionAssertionService initialized")
    
    def create_assertion(self, email, role, user_id=None):
        """
        创建签名的会话断言token
        
        Args:
            email: 用户邮箱
            role: 用户角色
            user_id: 用户ID（可选）
        
        Returns:
            str: 签名的token字符串
        """
        try:
            payload = {
                'email': email,
                'role': role,
                'user_id': user_id,
                'issued_at': datetime.utcnow().isoformat()
            }
            
            # 序列化并签名
            token = self.serializer.dumps(payload)
            
            logging.info(f"Created session assertion for {email} (role: {role})")
            return token
            
        except Exception as e:
            logging.error(f"Failed to create session assertion: {e}")
            return None
    
    def verify_assertion(self, token):
        """
        验证并解析会话断言token
        
        Args:
            token: 待验证的token字符串
        
        Returns:
            dict: 包含用户信息的字典，如果验证失败返回None
            {
                'valid': True/False,
                'email': str,
                'role': str,
                'user_id': int,
                'error': str (if invalid)
            }
        """
        try:
            # 反序列化并验证签名和过期时间
            payload = self.serializer.loads(
                token,
                max_age=self.token_max_age
            )
            
            logging.info(f"Verified session assertion for {payload.get('email')}")
            
            return {
                'valid': True,
                'email': payload.get('email'),
                'role': payload.get('role'),
                'user_id': payload.get('user_id')
            }
            
        except SignatureExpired:
            logging.warning("Session assertion token expired")
            return {
                'valid': False,
                'error': 'Token expired (5 minutes)'
            }
            
        except BadSignature:
            logging.warning("Invalid session assertion signature")
            return {
                'valid': False,
                'error': 'Invalid token signature'
            }
            
        except Exception as e:
            logging.error(f"Failed to verify session assertion: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def is_token_valid(self, token):
        """
        快速检查token是否有效
        
        Args:
            token: 待检查的token字符串
        
        Returns:
            bool: True如果token有效，否则False
        """
        result = self.verify_assertion(token)
        return result.get('valid', False)


# 全局实例（延迟初始化）
_assertion_service = None

def get_assertion_service():
    """
    获取全局SessionAssertionService实例
    
    Returns:
        SessionAssertionService: 服务实例
    """
    global _assertion_service
    if _assertion_service is None:
        _assertion_service = SessionAssertionService()
    return _assertion_service
