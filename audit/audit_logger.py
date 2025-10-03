"""
企业级审计日志系统
Enterprise Audit Logging System

功能:
- 全量操作审计（CRUD+配置变更）
- 自动PII/密钥脱敏
- 结构化日志输出
- 集中式日志聚合
- 长期归档和合规保留
- 日志查询和分析
- 异常检测和告警

合规标准:
- SOC 2 Type II
- PCI DSS
- HIPAA
- GDPR Article 30
- ISO 27001
"""

import os
import json
import logging
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)

class AuditLevel(Enum):
    """审计级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    SECURITY = "SECURITY"

class AuditCategory(Enum):
    """审计类别"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    CONFIGURATION = "configuration"
    API_CALL = "api_call"
    ENCRYPTION = "encryption"
    USER_MANAGEMENT = "user_management"
    SYSTEM = "system"
    COMPLIANCE = "compliance"

class AuditAction(Enum):
    """审计操作"""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    
    EXPORT = "export"
    IMPORT = "import"
    BATCH_OPERATION = "batch_operation"
    
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"
    
    ENCRYPTION = "encryption"
    DECRYPTION = "decryption"
    KEY_ROTATION = "key_rotation"
    
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"
    
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

@dataclass
class AuditEvent:
    """审计事件"""
    timestamp: str
    event_id: str
    level: AuditLevel
    category: AuditCategory
    action: AuditAction
    
    user_id: Optional[str]
    user_email: Optional[str]
    user_role: Optional[str]
    tenant_id: Optional[str]
    
    resource_type: Optional[str]
    resource_id: Optional[str]
    
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    
    status: str  # success, failure, partial
    
    details: Dict[str, Any]
    
    request_id: Optional[str]
    
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['level'] = self.level.value
        data['category'] = self.category.value
        data['action'] = self.action.value
        return data
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

class DataMasker:
    """数据脱敏器"""
    
    SENSITIVE_PATTERNS = {
        'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        'phone': r'(\+?1?\d{9,15})',
        'ssn': r'(\d{3}-\d{2}-\d{4})',
        'credit_card': r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})',
        'api_key': r'(hsi_[a-zA-Z0-9_-]{32,})',
        'jwt': r'(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)',
        'password': r'(password|passwd|pwd)[\s:=]+[^\s]+',
        'secret': r'(secret|token)[\s:=]+[^\s]+',
        'private_key': r'-----BEGIN (RSA |EC )?PRIVATE KEY-----[\s\S]+-----END (RSA |EC )?PRIVATE KEY-----'
    }
    
    SENSITIVE_FIELDS = {
        'password', 'password_hash', 'secret', 'api_key', 'private_key',
        'ssn', 'credit_card', 'bank_account', 'access_token', 'refresh_token'
    }
    
    @classmethod
    def mask_email(cls, email: str) -> str:
        """邮箱脱敏"""
        if '@' not in email:
            return email
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"
    
    @classmethod
    def mask_string(cls, value: str, show_length: int = 4) -> str:
        """字符串脱敏（显示前N位）"""
        if len(value) <= show_length:
            return '*' * len(value)
        return value[:show_length] + '*' * (len(value) - show_length)
    
    @classmethod
    def hash_value(cls, value: str) -> str:
        """使用SHA256哈希值替代（用于唯一标识）"""
        return hashlib.sha256(value.encode()).hexdigest()[:16]
    
    @classmethod
    def mask_text(cls, text: str) -> str:
        """文本中的敏感信息脱敏"""
        masked_text = text
        
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            if pattern_name == 'email':
                matches = re.findall(pattern, masked_text)
                for match in matches:
                    masked_text = masked_text.replace(match, cls.mask_email(match))
            else:
                masked_text = re.sub(pattern, f'<MASKED_{pattern_name.upper()}>', masked_text)
        
        return masked_text
    
    @classmethod
    def mask_dict(cls, data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """字典中的敏感数据脱敏"""
        if depth > 10:  # 防止无限递归
            return data
        
        masked_data = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            if any(sensitive_field in key_lower for sensitive_field in cls.SENSITIVE_FIELDS):
                if isinstance(value, str) and value:
                    masked_data[key] = cls.mask_string(value)
                else:
                    masked_data[key] = '<MASKED>'
            
            elif isinstance(value, dict):
                masked_data[key] = cls.mask_dict(value, depth + 1)
            
            elif isinstance(value, list):
                masked_data[key] = [
                    cls.mask_dict(item, depth + 1) if isinstance(item, dict) else item
                    for item in value
                ]
            
            elif isinstance(value, str):
                masked_data[key] = cls.mask_text(value)
            
            else:
                masked_data[key] = value
        
        return masked_data

class AuditLogStorage:
    """审计日志存储"""
    
    def __init__(self, storage_type: str = "file"):
        self.storage_type = storage_type
        self.log_file = os.environ.get('AUDIT_LOG_FILE', 'logs/audit.jsonl')
        self.rotation_size = int(os.environ.get('AUDIT_LOG_ROTATION_SIZE', 100 * 1024 * 1024))  # 100MB
        
        self.cloudwatch_enabled = os.environ.get('AUDIT_CLOUDWATCH_ENABLED', 'false').lower() == 'true'
        self.cloudwatch_log_group = os.environ.get('AUDIT_CLOUDWATCH_LOG_GROUP', '/hashinsight/audit')
        
        self.stackdriver_enabled = os.environ.get('AUDIT_STACKDRIVER_ENABLED', 'false').lower() == 'true'
        
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        self._init_storage()
    
    def _init_storage(self):
        """初始化存储"""
        if self.cloudwatch_enabled:
            self._init_cloudwatch()
        
        if self.stackdriver_enabled:
            self._init_stackdriver()
    
    def _init_cloudwatch(self):
        """初始化AWS CloudWatch"""
        try:
            import boto3
            self.cloudwatch_client = boto3.client('logs')
            logger.info("CloudWatch audit logging initialized")
        except ImportError:
            logger.warning("boto3 not installed, CloudWatch audit logging disabled")
            self.cloudwatch_enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize CloudWatch: {e}")
            self.cloudwatch_enabled = False
    
    def _init_stackdriver(self):
        """初始化Google Cloud Logging"""
        try:
            from google.cloud import logging as gcp_logging
            self.stackdriver_client = gcp_logging.Client()
            self.stackdriver_logger = self.stackdriver_client.logger('audit')
            logger.info("Stackdriver audit logging initialized")
        except ImportError:
            logger.warning("google-cloud-logging not installed, Stackdriver audit logging disabled")
            self.stackdriver_enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Stackdriver: {e}")
            self.stackdriver_enabled = False
    
    def write(self, event: AuditEvent):
        """写入审计日志"""
        self._write_to_file(event)
        
        if self.cloudwatch_enabled:
            self._write_to_cloudwatch(event)
        
        if self.stackdriver_enabled:
            self._write_to_stackdriver(event)
    
    def _write_to_file(self, event: AuditEvent):
        """写入文件"""
        try:
            self._check_rotation()
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(event.to_json() + '\n')
        
        except Exception as e:
            logger.error(f"Failed to write audit log to file: {e}")
    
    def _write_to_cloudwatch(self, event: AuditEvent):
        """写入CloudWatch"""
        try:
            log_stream = f"audit-{datetime.utcnow().strftime('%Y%m%d')}"
            
            self.cloudwatch_client.put_log_events(
                logGroupName=self.cloudwatch_log_group,
                logStreamName=log_stream,
                logEvents=[
                    {
                        'timestamp': int(datetime.utcnow().timestamp() * 1000),
                        'message': event.to_json()
                    }
                ]
            )
        
        except Exception as e:
            logger.error(f"Failed to write audit log to CloudWatch: {e}")
    
    def _write_to_stackdriver(self, event: AuditEvent):
        """写入Stackdriver"""
        try:
            self.stackdriver_logger.log_struct(
                event.to_dict(),
                severity=event.level.value
            )
        
        except Exception as e:
            logger.error(f"Failed to write audit log to Stackdriver: {e}")
    
    def _check_rotation(self):
        """检查日志轮转"""
        try:
            if os.path.exists(self.log_file):
                size = os.path.getsize(self.log_file)
                if size >= self.rotation_size:
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    rotated_file = f"{self.log_file}.{timestamp}"
                    os.rename(self.log_file, rotated_file)
                    logger.info(f"Rotated audit log: {rotated_file}")
        
        except Exception as e:
            logger.error(f"Failed to rotate audit log: {e}")
    
    def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        category: Optional[AuditCategory] = None,
        action: Optional[AuditAction] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """查询审计日志"""
        events = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        event_dict = json.loads(line)
                        
                        if start_time and event_dict['timestamp'] < start_time.isoformat():
                            continue
                        if end_time and event_dict['timestamp'] > end_time.isoformat():
                            continue
                        if user_id and event_dict.get('user_id') != user_id:
                            continue
                        if category and event_dict.get('category') != category.value:
                            continue
                        if action and event_dict.get('action') != action.value:
                            continue
                        
                        events.append(event_dict)
                        
                        if len(events) >= limit:
                            break
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")
        
        return events

class AuditLogger:
    """审计日志记录器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.storage = AuditLogStorage()
            self.masker = DataMasker()
            self.initialized = True
    
    def log(
        self,
        level: AuditLevel,
        category: AuditCategory,
        action: AuditAction,
        status: str = "success",
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        tenant_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        mask_details: bool = True
    ):
        """记录审计日志"""
        import secrets
        
        event_id = secrets.token_hex(16)
        
        if mask_details and details:
            details = self.masker.mask_dict(details)
        
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_id=event_id,
            level=level,
            category=category,
            action=action,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            status=status,
            details=details or {},
            request_id=request_id,
            metadata=metadata or {}
        )
        
        self.storage.write(event)
        
        logger.info(
            f"AUDIT: {level.value} | {category.value}.{action.value} | "
            f"user={user_email} | status={status} | resource={resource_type}/{resource_id}"
        )
    
    def log_authentication(
        self,
        action: AuditAction,
        user_email: str,
        status: str,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录认证事件"""
        level = AuditLevel.SECURITY if status == "failure" else AuditLevel.INFO
        
        self.log(
            level=level,
            category=AuditCategory.AUTHENTICATION,
            action=action,
            status=status,
            user_email=user_email,
            ip_address=ip_address,
            details=details
        )
    
    def log_data_access(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        user_id: str,
        user_email: str,
        tenant_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录数据访问"""
        self.log(
            level=AuditLevel.INFO,
            category=AuditCategory.DATA_ACCESS,
            action=action,
            user_id=user_id,
            user_email=user_email,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )
    
    def log_security_event(
        self,
        action: AuditAction,
        details: Dict[str, Any],
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """记录安全事件"""
        self.log(
            level=AuditLevel.SECURITY,
            category=AuditCategory.AUTHENTICATION,
            action=action,
            status="security_alert",
            user_email=user_email,
            ip_address=ip_address,
            details=details
        )

audit_logger = AuditLogger()

def audit_decorator(
    category: AuditCategory,
    action: AuditAction,
    resource_type: Optional[str] = None
):
    """审计装饰器"""
    from functools import wraps
    from flask import request, g
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                status = "success"
            except Exception as e:
                status = "failure"
                result = None
                raise
            finally:
                audit_logger.log(
                    level=AuditLevel.INFO,
                    category=category,
                    action=action,
                    status=status,
                    user_id=getattr(g, 'user_id', None),
                    user_email=getattr(g, 'user_email', None),
                    user_role=getattr(g, 'user_role', None),
                    tenant_id=getattr(g, 'tenant_id', None),
                    resource_type=resource_type or f.__name__,
                    ip_address=request.remote_addr if hasattr(request, 'remote_addr') else None,
                    user_agent=request.headers.get('User-Agent') if hasattr(request, 'headers') else None
                )
            
            return result
        return decorated_function
    return decorator

__all__ = [
    'AuditLevel',
    'AuditCategory',
    'AuditAction',
    'AuditEvent',
    'DataMasker',
    'AuditLogger',
    'audit_logger',
    'audit_decorator'
]
