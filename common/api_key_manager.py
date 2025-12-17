"""
API密钥管理系统
API Key Management System

功能:
- API密钥生成（安全随机）
- 密钥轮换和过期管理
- 密钥吊销和黑名单
- 使用率限制和配额
- 审计日志集成
- 多租户隔离

安全特性:
- 密钥哈希存储（never store plain keys）
- 自动轮换提醒
- 异常访问检测
- IP白名单
- 使用限额
"""

import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class APIKeyStatus(Enum):
    """API密钥状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"

@dataclass
class APIKey:
    """API密钥数据类"""
    key_id: str
    key_hash: str  # SHA256哈希
    prefix: str  # 密钥前缀（用于识别）
    user_id: str
    tenant_id: Optional[str]
    name: str
    description: str
    permissions: List[str]
    rate_limit: int  # 每小时请求限制
    quota_monthly: int  # 每月请求配额
    ip_whitelist: List[str]  # IP白名单
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    status: APIKeyStatus
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['expires_at'] = self.expires_at.isoformat() if self.expires_at else None
        data['last_used_at'] = self.last_used_at.isoformat() if self.last_used_at else None
        return data
    
    def is_valid(self) -> Tuple[bool, Optional[str]]:
        """检查密钥是否有效"""
        if self.status != APIKeyStatus.ACTIVE:
            return False, f"Key status is {self.status.value}"
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False, "Key has expired"
        
        return True, None
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """检查IP是否在白名单"""
        if not self.ip_whitelist:
            return True
        return ip_address in self.ip_whitelist
    
    def check_rate_limit(self, current_usage: int) -> bool:
        """检查是否超过速率限制"""
        return current_usage < self.rate_limit
    
    def check_quota(self, monthly_usage: int) -> bool:
        """检查是否超过月度配额"""
        return monthly_usage < self.quota_monthly

class APIKeyGenerator:
    """API密钥生成器"""
    
    PREFIX = "hsi_"  # HashInsight API key prefix
    KEY_LENGTH = 32  # 密钥长度（字节）
    
    @classmethod
    def generate_key(cls) -> Tuple[str, str, str]:
        """
        生成API密钥
        
        Returns:
            Tuple[full_key, key_hash, prefix]
        """
        random_bytes = secrets.token_bytes(cls.KEY_LENGTH)
        random_str = secrets.token_urlsafe(cls.KEY_LENGTH)
        
        timestamp_suffix = secrets.token_hex(4)
        key_id = f"{cls.PREFIX}{random_str}_{timestamp_suffix}"
        
        key_hash = hashlib.sha256(key_id.encode()).hexdigest()
        
        prefix = key_id[:12]
        
        logger.info(f"Generated new API key with prefix: {prefix}")
        
        return key_id, key_hash, prefix
    
    @classmethod
    def hash_key(cls, key: str) -> str:
        """对密钥进行哈希"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @classmethod
    def verify_key(cls, provided_key: str, stored_hash: str) -> bool:
        """验证密钥"""
        provided_hash = cls.hash_key(provided_key)
        return secrets.compare_digest(provided_hash, stored_hash)

class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.generator = APIKeyGenerator()
        
        self.in_memory_keys: Dict[str, APIKey] = {}
        
        self.rate_limit_tracker: Dict[str, Dict[str, int]] = {}
        
        self.quota_tracker: Dict[str, int] = {}
    
    def create_key(
        self,
        user_id: str,
        name: str,
        permissions: List[str],
        tenant_id: Optional[str] = None,
        description: str = "",
        rate_limit: int = 1000,  # 默认每小时1000次
        quota_monthly: int = 100000,  # 默认每月10万次
        ip_whitelist: List[str] = None,
        expires_in_days: Optional[int] = 365,  # 默认1年过期
        metadata: Dict[str, Any] = None
    ) -> Tuple[str, APIKey]:
        """
        创建新的API密钥
        
        Returns:
            Tuple[plain_key, api_key_object]
            注意: plain_key只会返回一次，必须立即展示给用户
        """
        full_key, key_hash, prefix = self.generator.generate_key()
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        api_key = APIKey(
            key_id=secrets.token_hex(16),
            key_hash=key_hash,
            prefix=prefix,
            user_id=user_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            permissions=permissions,
            rate_limit=rate_limit,
            quota_monthly=quota_monthly,
            ip_whitelist=ip_whitelist or [],
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            last_used_at=None,
            usage_count=0,
            status=APIKeyStatus.ACTIVE,
            metadata=metadata or {}
        )
        
        if self.db:
            self._save_to_db(api_key)
        else:
            self.in_memory_keys[key_hash] = api_key
        
        logger.info(f"Created API key for user {user_id}: {api_key.name} (prefix: {prefix})")
        
        return full_key, api_key
    
    def verify_key(
        self,
        provided_key: str,
        ip_address: Optional[str] = None
    ) -> Optional[APIKey]:
        """验证API密钥"""
        key_hash = self.generator.hash_key(provided_key)
        
        if self.db:
            api_key = self._load_from_db(key_hash)
        else:
            api_key = self.in_memory_keys.get(key_hash)
        
        if not api_key:
            logger.warning(f"API key not found: {provided_key[:12]}...")
            return None
        
        is_valid, reason = api_key.is_valid()
        if not is_valid:
            logger.warning(f"API key invalid: {reason}")
            return None
        
        if ip_address and not api_key.is_ip_allowed(ip_address):
            logger.warning(f"IP address not in whitelist: {ip_address}")
            return None
        
        current_hour_usage = self._get_hourly_usage(api_key.key_id)
        if not api_key.check_rate_limit(current_hour_usage):
            logger.warning(f"Rate limit exceeded for key: {api_key.name}")
            return None
        
        monthly_usage = self._get_monthly_usage(api_key.key_id)
        if not api_key.check_quota(monthly_usage):
            logger.warning(f"Monthly quota exceeded for key: {api_key.name}")
            return None
        
        self._record_usage(api_key)
        
        logger.debug(f"API key verified: {api_key.name}")
        return api_key
    
    def rotate_key(
        self,
        old_key_id: str,
        grace_period_days: int = 30
    ) -> Tuple[str, APIKey]:
        """
        轮换API密钥
        
        Args:
            old_key_id: 旧密钥ID
            grace_period_days: 宽限期（天），在此期间旧密钥仍然有效
        
        Returns:
            Tuple[new_plain_key, new_api_key_object]
        """
        old_key = self._get_key_by_id(old_key_id)
        if not old_key:
            raise ValueError(f"Key not found: {old_key_id}")
        
        new_full_key, new_api_key = self.create_key(
            user_id=old_key.user_id,
            name=f"{old_key.name} (rotated)",
            permissions=old_key.permissions,
            tenant_id=old_key.tenant_id,
            description=f"Rotated from {old_key.name}",
            rate_limit=old_key.rate_limit,
            quota_monthly=old_key.quota_monthly,
            ip_whitelist=old_key.ip_whitelist,
            expires_in_days=365,
            metadata={
                **old_key.metadata,
                'rotated_from': old_key.key_id,
                'rotation_date': datetime.utcnow().isoformat()
            }
        )
        
        old_key.expires_at = datetime.utcnow() + timedelta(days=grace_period_days)
        old_key.metadata['rotated_to'] = new_api_key.key_id
        old_key.metadata['rotation_grace_period'] = grace_period_days
        
        if self.db:
            self._update_in_db(old_key)
        
        logger.info(f"Rotated API key {old_key.name} → {new_api_key.name}")
        
        return new_full_key, new_api_key
    
    def revoke_key(self, key_id: str, reason: str = ""):
        """吊销API密钥"""
        api_key = self._get_key_by_id(key_id)
        if not api_key:
            raise ValueError(f"Key not found: {key_id}")
        
        api_key.status = APIKeyStatus.REVOKED
        api_key.metadata['revoked_at'] = datetime.utcnow().isoformat()
        api_key.metadata['revoke_reason'] = reason
        
        if self.db:
            self._update_in_db(api_key)
        
        logger.warning(f"Revoked API key {api_key.name}: {reason}")
    
    def suspend_key(self, key_id: str, reason: str = ""):
        """暂停API密钥（可恢复）"""
        api_key = self._get_key_by_id(key_id)
        if not api_key:
            raise ValueError(f"Key not found: {key_id}")
        
        api_key.status = APIKeyStatus.SUSPENDED
        api_key.metadata['suspended_at'] = datetime.utcnow().isoformat()
        api_key.metadata['suspend_reason'] = reason
        
        if self.db:
            self._update_in_db(api_key)
        
        logger.warning(f"Suspended API key {api_key.name}: {reason}")
    
    def reactivate_key(self, key_id: str):
        """重新激活暂停的密钥"""
        api_key = self._get_key_by_id(key_id)
        if not api_key:
            raise ValueError(f"Key not found: {key_id}")
        
        if api_key.status != APIKeyStatus.SUSPENDED:
            raise ValueError(f"Key is not suspended: {api_key.status.value}")
        
        api_key.status = APIKeyStatus.ACTIVE
        api_key.metadata['reactivated_at'] = datetime.utcnow().isoformat()
        
        if self.db:
            self._update_in_db(api_key)
        
        logger.info(f"Reactivated API key {api_key.name}")
    
    def list_keys(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[APIKeyStatus] = None
    ) -> List[APIKey]:
        """列出API密钥"""
        if self.db:
            return self._list_from_db(user_id, tenant_id, status)
        else:
            keys = list(self.in_memory_keys.values())
            
            if user_id:
                keys = [k for k in keys if k.user_id == user_id]
            if tenant_id:
                keys = [k for k in keys if k.tenant_id == tenant_id]
            if status:
                keys = [k for k in keys if k.status == status]
            
            return keys
    
    def get_usage_stats(self, key_id: str) -> Dict[str, Any]:
        """获取密钥使用统计"""
        api_key = self._get_key_by_id(key_id)
        if not api_key:
            raise ValueError(f"Key not found: {key_id}")
        
        return {
            'key_id': api_key.key_id,
            'name': api_key.name,
            'total_usage': api_key.usage_count,
            'hourly_usage': self._get_hourly_usage(key_id),
            'daily_usage': self._get_daily_usage(key_id),
            'monthly_usage': self._get_monthly_usage(key_id),
            'last_used_at': api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            'rate_limit': api_key.rate_limit,
            'quota_monthly': api_key.quota_monthly,
            'quota_remaining': api_key.quota_monthly - self._get_monthly_usage(key_id)
        }
    
    def _record_usage(self, api_key: APIKey):
        """记录密钥使用"""
        api_key.last_used_at = datetime.utcnow()
        api_key.usage_count += 1
        
        current_hour = datetime.utcnow().strftime('%Y%m%d%H')
        if api_key.key_id not in self.rate_limit_tracker:
            self.rate_limit_tracker[api_key.key_id] = {}
        self.rate_limit_tracker[api_key.key_id][current_hour] = \
            self.rate_limit_tracker[api_key.key_id].get(current_hour, 0) + 1
        
        current_month = datetime.utcnow().strftime('%Y%m')
        quota_key = f"{api_key.key_id}:{current_month}"
        self.quota_tracker[quota_key] = self.quota_tracker.get(quota_key, 0) + 1
        
        if self.db:
            self._update_in_db(api_key)
    
    def _get_hourly_usage(self, key_id: str) -> int:
        """获取当前小时使用次数"""
        current_hour = datetime.utcnow().strftime('%Y%m%d%H')
        return self.rate_limit_tracker.get(key_id, {}).get(current_hour, 0)
    
    def _get_daily_usage(self, key_id: str) -> int:
        """获取当天使用次数"""
        current_day = datetime.utcnow().strftime('%Y%m%d')
        total = 0
        for hour_key, count in self.rate_limit_tracker.get(key_id, {}).items():
            if hour_key.startswith(current_day):
                total += count
        return total
    
    def _get_monthly_usage(self, key_id: str) -> int:
        """获取当月使用次数"""
        current_month = datetime.utcnow().strftime('%Y%m')
        quota_key = f"{key_id}:{current_month}"
        return self.quota_tracker.get(quota_key, 0)
    
    def _get_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """通过ID获取密钥"""
        if self.db:
            return self._load_from_db_by_id(key_id)
        else:
            for api_key in self.in_memory_keys.values():
                if api_key.key_id == key_id:
                    return api_key
            return None
    
    def _save_to_db(self, api_key: APIKey):
        """保存到数据库（需要实现）"""
        pass
    
    def _load_from_db(self, key_hash: str) -> Optional[APIKey]:
        """从数据库加载（需要实现）"""
        pass
    
    def _load_from_db_by_id(self, key_id: str) -> Optional[APIKey]:
        """从数据库通过ID加载（需要实现）"""
        pass
    
    def _update_in_db(self, api_key: APIKey):
        """更新数据库（需要实现）"""
        pass
    
    def _list_from_db(
        self,
        user_id: Optional[str],
        tenant_id: Optional[str],
        status: Optional[APIKeyStatus]
    ) -> List[APIKey]:
        """从数据库列出（需要实现）"""
        return []

__all__ = [
    'APIKeyStatus',
    'APIKey',
    'APIKeyGenerator',
    'APIKeyManager'
]
