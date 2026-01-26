"""
SOC2安全合规模块
SOC2 Security Compliance Module for HashInsight Enterprise

功能:
- 审计日志保留策略 (Log Retention Policy)
- 登录安全增强 (Login Security Enhancement)
- 密码策略管理 (Password Policy Management)
- 安全告警通知 (Security Alerts)
- 敏感数据访问日志 (Data Access Logging)

合规标准:
- SOC 2 Type II CC6.1, CC6.6, CC6.7
- NIST 800-53 AU-4, AU-11
"""

import os
import re
import json
import logging
import hashlib
import glob
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass

from audit.audit_logger import (
    audit_logger, 
    AuditLevel, 
    AuditCategory, 
    AuditAction
)

logger = logging.getLogger(__name__)


class SecurityAlertType(Enum):
    """安全告警类型"""
    BRUTE_FORCE = "brute_force"
    SUSPICIOUS_LOGIN = "suspicious_login"
    PASSWORD_EXPIRED_BATCH = "password_expired_batch"
    DATA_EXPORT = "data_export"


class SensitiveResourceType(Enum):
    """敏感资源类型"""
    CREDENTIALS = "credentials"
    CUSTOMER_DATA = "customer_data"
    FINANCIAL_DATA = "financial_data"
    AUDIT_LOGS = "audit_logs"


@dataclass
class PasswordValidationResult:
    """密码验证结果"""
    is_valid: bool
    errors_en: List[str]
    errors_zh: List[str]
    score: int
    
    def get_errors(self, language: str = 'zh') -> List[str]:
        """获取指定语言的错误消息"""
        return self.errors_zh if language == 'zh' else self.errors_en


def cleanup_old_audit_logs(retention_days: int = None) -> Dict[str, Any]:
    """
    清理过期的审计日志文件
    
    根据保留天数删除旧的审计日志，符合SOC2数据保留策略要求。
    
    Args:
        retention_days: 日志保留天数，默认从环境变量AUDIT_LOG_RETENTION_DAYS读取(默认365天)
    
    Returns:
        Dict包含清理结果信息:
        - deleted_count: 删除的文件数量
        - deleted_files: 删除的文件列表
        - errors: 错误信息列表
        - execution_time: 执行时间(秒)
    """
    start_time = datetime.utcnow()
    
    if retention_days is None:
        retention_days = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', '365'))
    
    log_dir = os.environ.get('AUDIT_LOG_DIR', 'logs')
    log_file_pattern = os.environ.get('AUDIT_LOG_FILE', 'logs/audit.jsonl')
    
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    result = {
        'deleted_count': 0,
        'deleted_files': [],
        'errors': [],
        'retention_days': retention_days,
        'cutoff_date': cutoff_date.isoformat(),
        'execution_time': 0
    }
    
    try:
        base_log_file = os.path.basename(log_file_pattern)
        rotated_pattern = os.path.join(log_dir, f"{base_log_file}.*")
        log_files = glob.glob(rotated_pattern)
        
        for log_file in log_files:
            try:
                file_stat = os.stat(log_file)
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                
                if file_mtime < cutoff_date:
                    os.remove(log_file)
                    result['deleted_files'].append(log_file)
                    result['deleted_count'] += 1
                    logger.info(f"已删除过期审计日志: {log_file} (修改时间: {file_mtime.isoformat()})")
            
            except Exception as e:
                error_msg = f"删除日志文件失败 {log_file}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        audit_logger.log(
            level=AuditLevel.INFO,
            category=AuditCategory.SYSTEM,
            action=AuditAction.DELETE,
            status="success",
            resource_type="audit_logs",
            details={
                'operation': 'cleanup_old_audit_logs',
                'deleted_count': result['deleted_count'],
                'retention_days': retention_days,
                'cutoff_date': cutoff_date.isoformat()
            }
        )
        
    except Exception as e:
        error_msg = f"审计日志清理失败: {str(e)}"
        result['errors'].append(error_msg)
        logger.error(error_msg)
    
    end_time = datetime.utcnow()
    result['execution_time'] = (end_time - start_time).total_seconds()
    
    return result


def setup_audit_log_cleanup_scheduler():
    """
    设置审计日志清理定时任务
    
    使用APScheduler创建每日运行的日志清理任务，
    默认在每天凌晨2:00执行。
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BackgroundScheduler()
        
        cleanup_hour = int(os.environ.get('AUDIT_CLEANUP_HOUR', '2'))
        cleanup_minute = int(os.environ.get('AUDIT_CLEANUP_MINUTE', '0'))
        
        scheduler.add_job(
            cleanup_old_audit_logs,
            trigger=CronTrigger(hour=cleanup_hour, minute=cleanup_minute),
            id='audit_log_cleanup',
            name='每日审计日志清理',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info(f"审计日志清理调度器已启动 (每日 {cleanup_hour:02d}:{cleanup_minute:02d} 执行)")
        
        return scheduler
        
    except ImportError:
        logger.warning("APScheduler未安装，审计日志自动清理功能不可用")
        return None
    except Exception as e:
        logger.error(f"设置审计日志清理调度器失败: {e}")
        return None


class LoginSecurityManager:
    """
    登录安全管理器
    
    提供以下功能:
    - 记录失败登录尝试
    - 账户锁定检查 (5次失败在15分钟内 = 锁定30分钟)
    - 记录成功登录并重置失败计数
    - 检测可疑登录行为 (异常IP、设备)
    
    使用Redis进行分布式状态存储，当Redis不可用时回退到内存字典。
    """
    
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_WINDOW_MINUTES = 15
    LOCKOUT_DURATION_MINUTES = 30
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化登录安全管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._redis_client = None
        self._memory_store: Dict[str, Any] = {}
        self._memory_lock = threading.Lock()
        
        self._init_redis()
        
        self._known_user_patterns: Dict[str, Dict] = {}
    
    def _init_redis(self):
        """初始化Redis连接"""
        redis_url = os.environ.get('REDIS_URL')
        
        if redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                logger.info("LoginSecurityManager: Redis连接成功")
            except ImportError:
                logger.warning("redis-py未安装，使用内存存储")
                self._redis_client = None
            except Exception as e:
                logger.warning(f"Redis连接失败，使用内存存储: {e}")
                self._redis_client = None
        else:
            logger.info("未配置REDIS_URL，使用内存存储")
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        """生成存储键"""
        return f"login_security:{prefix}:{identifier}"
    
    def _get_value(self, key: str) -> Optional[str]:
        """获取存储值"""
        if self._redis_client:
            try:
                return self._redis_client.get(key)
            except Exception as e:
                logger.error(f"Redis读取失败: {e}")
        
        with self._memory_lock:
            item = self._memory_store.get(key)
            if item and item.get('expires_at', datetime.max) > datetime.utcnow():
                return item.get('value')
            elif item:
                del self._memory_store[key]
        return None
    
    def _set_value(self, key: str, value: str, ttl_seconds: int):
        """设置存储值"""
        if self._redis_client:
            try:
                self._redis_client.setex(key, ttl_seconds, value)
                return
            except Exception as e:
                logger.error(f"Redis写入失败: {e}")
        
        with self._memory_lock:
            self._memory_store[key] = {
                'value': value,
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl_seconds)
            }
    
    def _incr_value(self, key: str, ttl_seconds: int) -> int:
        """递增存储值"""
        if self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl_seconds)
                results = pipe.execute()
                return results[0]
            except Exception as e:
                logger.error(f"Redis递增失败: {e}")
        
        with self._memory_lock:
            item = self._memory_store.get(key, {'value': '0', 'expires_at': datetime.max})
            if item.get('expires_at', datetime.max) <= datetime.utcnow():
                item = {'value': '0'}
            
            new_value = int(item.get('value', 0)) + 1
            self._memory_store[key] = {
                'value': str(new_value),
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl_seconds)
            }
            return new_value
    
    def _delete_key(self, key: str):
        """删除存储键"""
        if self._redis_client:
            try:
                self._redis_client.delete(key)
                return
            except Exception as e:
                logger.error(f"Redis删除失败: {e}")
        
        with self._memory_lock:
            self._memory_store.pop(key, None)
    
    def record_failed_login(self, email: str, ip: str) -> Dict[str, Any]:
        """
        记录失败的登录尝试
        
        Args:
            email: 用户邮箱
            ip: 客户端IP地址
        
        Returns:
            Dict包含:
            - attempts: 当前失败次数
            - is_locked: 是否已锁定
            - lockout_remaining: 剩余锁定时间(秒)
        """
        email_lower = email.lower().strip()
        
        failed_key = self._get_key('failed', email_lower)
        lockout_key = self._get_key('lockout', email_lower)
        
        attempts = self._incr_value(failed_key, self.LOCKOUT_WINDOW_MINUTES * 60)
        
        result = {
            'email': email_lower,
            'ip': ip,
            'attempts': attempts,
            'is_locked': False,
            'lockout_remaining': 0
        }
        
        if attempts >= self.MAX_FAILED_ATTEMPTS:
            lockout_ttl = self.LOCKOUT_DURATION_MINUTES * 60
            self._set_value(lockout_key, datetime.utcnow().isoformat(), lockout_ttl)
            result['is_locked'] = True
            result['lockout_remaining'] = lockout_ttl
            
            audit_logger.log(
                level=AuditLevel.SECURITY,
                category=AuditCategory.AUTHENTICATION,
                action=AuditAction.LOGIN_FAILED,
                status="account_locked",
                user_email=email_lower,
                ip_address=ip,
                details={
                    'reason': 'brute_force_protection',
                    'failed_attempts': attempts,
                    'lockout_duration_minutes': self.LOCKOUT_DURATION_MINUTES
                }
            )
            
            SecurityAlertManager().send_admin_alert(
                SecurityAlertType.BRUTE_FORCE,
                {
                    'email': email_lower,
                    'ip': ip,
                    'attempts': attempts,
                    'lockout_duration': self.LOCKOUT_DURATION_MINUTES
                }
            )
        else:
            audit_logger.log(
                level=AuditLevel.WARNING,
                category=AuditCategory.AUTHENTICATION,
                action=AuditAction.LOGIN_FAILED,
                status="failure",
                user_email=email_lower,
                ip_address=ip,
                details={
                    'failed_attempts': attempts,
                    'max_attempts': self.MAX_FAILED_ATTEMPTS
                }
            )
        
        logger.warning(f"登录失败: {email_lower} 来自 {ip} (第{attempts}次)")
        
        return result
    
    def check_account_locked(self, email: str) -> Dict[str, Any]:
        """
        检查账户是否被锁定
        
        Args:
            email: 用户邮箱
        
        Returns:
            Dict包含:
            - is_locked: 是否被锁定
            - lockout_remaining: 剩余锁定时间(秒)
            - message_en: 英文消息
            - message_zh: 中文消息
        """
        email_lower = email.lower().strip()
        lockout_key = self._get_key('lockout', email_lower)
        
        lockout_time_str = self._get_value(lockout_key)
        
        result = {
            'is_locked': False,
            'lockout_remaining': 0,
            'message_en': '',
            'message_zh': ''
        }
        
        if lockout_time_str:
            try:
                lockout_time = datetime.fromisoformat(lockout_time_str)
                lockout_end = lockout_time + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                remaining = (lockout_end - datetime.utcnow()).total_seconds()
                
                if remaining > 0:
                    result['is_locked'] = True
                    result['lockout_remaining'] = int(remaining)
                    remaining_minutes = int(remaining / 60) + 1
                    result['message_en'] = f"Account is locked. Please try again in {remaining_minutes} minutes."
                    result['message_zh'] = f"账户已锁定，请在{remaining_minutes}分钟后重试。"
                else:
                    self._delete_key(lockout_key)
            except Exception as e:
                logger.error(f"解析锁定时间失败: {e}")
        
        return result
    
    def record_successful_login(self, email: str, ip: str) -> Dict[str, Any]:
        """
        记录成功登录并重置失败计数
        
        Args:
            email: 用户邮箱
            ip: 客户端IP地址
        
        Returns:
            Dict包含登录信息
        """
        email_lower = email.lower().strip()
        
        failed_key = self._get_key('failed', email_lower)
        lockout_key = self._get_key('lockout', email_lower)
        
        self._delete_key(failed_key)
        self._delete_key(lockout_key)
        
        pattern_key = self._get_key('pattern', email_lower)
        existing_pattern = self._get_value(pattern_key)
        
        current_pattern = {
            'last_ip': ip,
            'last_login': datetime.utcnow().isoformat(),
            'login_count': 1
        }
        
        if existing_pattern:
            try:
                pattern_data = json.loads(existing_pattern)
                current_pattern['login_count'] = pattern_data.get('login_count', 0) + 1
                current_pattern['known_ips'] = pattern_data.get('known_ips', [])
                if ip not in current_pattern['known_ips']:
                    current_pattern['known_ips'].append(ip)
                    current_pattern['known_ips'] = current_pattern['known_ips'][-10:]
            except json.JSONDecodeError:
                current_pattern['known_ips'] = [ip]
        else:
            current_pattern['known_ips'] = [ip]
        
        self._set_value(pattern_key, json.dumps(current_pattern), 90 * 24 * 3600)
        
        audit_logger.log(
            level=AuditLevel.INFO,
            category=AuditCategory.AUTHENTICATION,
            action=AuditAction.LOGIN,
            status="success",
            user_email=email_lower,
            ip_address=ip,
            details={
                'login_count': current_pattern['login_count']
            }
        )
        
        logger.info(f"登录成功: {email_lower} 来自 {ip}")
        
        return {
            'email': email_lower,
            'ip': ip,
            'login_count': current_pattern['login_count']
        }
    
    def detect_suspicious_login(
        self, 
        user_id: str, 
        ip: str, 
        user_agent: str,
        email: str = None
    ) -> Dict[str, Any]:
        """
        检测可疑登录行为
        
        分析登录请求是否存在异常，包括:
        - 新的IP地址
        - 不同的设备/浏览器
        - 地理位置异常
        
        Args:
            user_id: 用户ID
            ip: 客户端IP地址
            user_agent: 用户代理字符串
            email: 用户邮箱(可选)
        
        Returns:
            Dict包含:
            - is_suspicious: 是否可疑
            - risk_score: 风险评分 (0-100)
            - reasons: 可疑原因列表
        """
        result = {
            'is_suspicious': False,
            'risk_score': 0,
            'reasons': [],
            'reasons_zh': []
        }
        
        pattern_key = self._get_key('pattern', str(user_id))
        existing_pattern = self._get_value(pattern_key)
        
        if not existing_pattern:
            result['risk_score'] = 30
            result['reasons'].append("First login from this device/location")
            result['reasons_zh'].append("首次从此设备/位置登录")
            return result
        
        try:
            pattern_data = json.loads(existing_pattern)
        except json.JSONDecodeError:
            return result
        
        known_ips = pattern_data.get('known_ips', [])
        if ip not in known_ips:
            result['risk_score'] += 40
            result['reasons'].append(f"Login from new IP address: {ip}")
            result['reasons_zh'].append(f"从新IP地址登录: {ip}")
        
        ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
        known_ua_hashes = pattern_data.get('known_ua_hashes', [])
        if ua_hash not in known_ua_hashes:
            result['risk_score'] += 25
            result['reasons'].append("Login from new device/browser")
            result['reasons_zh'].append("从新设备/浏览器登录")
            
            known_ua_hashes.append(ua_hash)
            pattern_data['known_ua_hashes'] = known_ua_hashes[-5:]
            self._set_value(pattern_key, json.dumps(pattern_data), 90 * 24 * 3600)
        
        last_login_str = pattern_data.get('last_login')
        if last_login_str:
            try:
                last_login = datetime.fromisoformat(last_login_str)
                days_since_last = (datetime.utcnow() - last_login).days
                if days_since_last > 30:
                    result['risk_score'] += 15
                    result['reasons'].append(f"No login for {days_since_last} days")
                    result['reasons_zh'].append(f"超过{days_since_last}天未登录")
            except ValueError:
                pass
        
        result['is_suspicious'] = result['risk_score'] >= 50
        
        if result['is_suspicious']:
            audit_logger.log(
                level=AuditLevel.SECURITY,
                category=AuditCategory.AUTHENTICATION,
                action=AuditAction.SUSPICIOUS_ACTIVITY,
                status="detected",
                user_id=str(user_id),
                user_email=email,
                ip_address=ip,
                user_agent=user_agent,
                details={
                    'risk_score': result['risk_score'],
                    'reasons': result['reasons']
                }
            )
            
            SecurityAlertManager().send_admin_alert(
                SecurityAlertType.SUSPICIOUS_LOGIN,
                {
                    'user_id': user_id,
                    'email': email,
                    'ip': ip,
                    'risk_score': result['risk_score'],
                    'reasons': result['reasons']
                }
            )
            
            logger.warning(f"检测到可疑登录: user_id={user_id}, risk_score={result['risk_score']}")
        
        return result


class PasswordPolicyManager:
    """
    密码策略管理器
    
    实现SOC2合规的密码策略:
    - 最小长度8个字符
    - 至少1个大写字母
    - 至少1个小写字母
    - 至少1个数字
    - 至少1个特殊字符
    - 密码90天过期检查
    """
    
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    PASSWORD_EXPIRY_DAYS = 90
    
    SPECIAL_CHARS = r"!@#$%^&*()_+-=[]{}|;':\",./<>?"
    
    def validate_password_strength(self, password: str) -> PasswordValidationResult:
        """
        验证密码强度
        
        检查密码是否满足以下要求:
        - 最小8个字符
        - 至少1个大写字母
        - 至少1个小写字母
        - 至少1个数字
        - 至少1个特殊字符
        
        Args:
            password: 待验证的密码
        
        Returns:
            PasswordValidationResult包含验证结果和双语错误消息
        """
        errors_en = []
        errors_zh = []
        score = 0
        
        if len(password) < self.MIN_LENGTH:
            errors_en.append(f"Password must be at least {self.MIN_LENGTH} characters long")
            errors_zh.append(f"密码长度至少需要{self.MIN_LENGTH}个字符")
        else:
            score += 20
            if len(password) >= 12:
                score += 10
            if len(password) >= 16:
                score += 10
        
        if self.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors_en.append("Password must contain at least one uppercase letter")
            errors_zh.append("密码必须包含至少一个大写字母")
        else:
            score += 15
        
        if self.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors_en.append("Password must contain at least one lowercase letter")
            errors_zh.append("密码必须包含至少一个小写字母")
        else:
            score += 15
        
        if self.REQUIRE_DIGIT and not re.search(r'\d', password):
            errors_en.append("Password must contain at least one number")
            errors_zh.append("密码必须包含至少一个数字")
        else:
            score += 15
        
        if self.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;\':",./<>?]', password):
            errors_en.append("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;':\",./<>?)")
            errors_zh.append("密码必须包含至少一个特殊字符 (!@#$%^&*()_+-=[]{}|;':\",./<>?)")
        else:
            score += 15
        
        common_passwords = ['password', '123456', 'qwerty', 'admin', 'letmein', 'welcome']
        if password.lower() in common_passwords:
            errors_en.append("Password is too common, please choose a stronger password")
            errors_zh.append("密码过于常见，请选择更强的密码")
            score = max(0, score - 30)
        
        if re.search(r'(.)\1{2,}', password):
            errors_en.append("Password should not contain more than 2 consecutive identical characters")
            errors_zh.append("密码不应包含超过2个连续相同的字符")
            score = max(0, score - 10)
        
        is_valid = len(errors_en) == 0
        score = min(100, max(0, score))
        
        return PasswordValidationResult(
            is_valid=is_valid,
            errors_en=errors_en,
            errors_zh=errors_zh,
            score=score
        )
    
    def check_password_expiry(self, user_id: str, password_changed_at: datetime = None) -> Dict[str, Any]:
        """
        检查密码是否过期
        
        根据90天密码过期策略检查用户密码状态。
        
        Args:
            user_id: 用户ID
            password_changed_at: 密码最后修改时间，如为None则从数据库查询
        
        Returns:
            Dict包含:
            - is_expired: 是否过期
            - days_until_expiry: 距离过期天数
            - message_en: 英文消息
            - message_zh: 中文消息
        """
        expiry_days = int(os.environ.get('PASSWORD_EXPIRY_DAYS', str(self.PASSWORD_EXPIRY_DAYS)))
        
        if password_changed_at is None:
            try:
                from models import User
                from db import db
                user = User.query.get(user_id)
                if user:
                    if hasattr(user, 'password_changed_at') and user.password_changed_at:
                        password_changed_at = user.password_changed_at
                    elif hasattr(user, 'updated_at') and user.updated_at:
                        password_changed_at = user.updated_at
                    elif hasattr(user, 'created_at') and user.created_at:
                        password_changed_at = user.created_at
                    else:
                        password_changed_at = datetime.utcnow()
                else:
                    password_changed_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"查询用户密码修改时间失败: {e}")
                password_changed_at = datetime.utcnow()
        
        days_since_change = (datetime.utcnow() - password_changed_at).days
        days_until_expiry = expiry_days - days_since_change
        is_expired = days_until_expiry <= 0
        
        result = {
            'is_expired': is_expired,
            'days_until_expiry': max(0, days_until_expiry),
            'days_since_change': days_since_change,
            'message_en': '',
            'message_zh': ''
        }
        
        if is_expired:
            result['message_en'] = "Your password has expired. Please change your password to continue."
            result['message_zh'] = "您的密码已过期，请修改密码以继续使用。"
        elif days_until_expiry <= 7:
            result['message_en'] = f"Your password will expire in {days_until_expiry} days. Please change it soon."
            result['message_zh'] = f"您的密码将在{days_until_expiry}天后过期，请尽快修改。"
        elif days_until_expiry <= 14:
            result['message_en'] = f"Password expiry reminder: {days_until_expiry} days remaining."
            result['message_zh'] = f"密码过期提醒：还有{days_until_expiry}天。"
        
        return result


class SecurityAlertManager:
    """
    安全告警管理器
    
    负责向管理员发送安全事件告警，包括:
    - 暴力破解攻击 (BRUTE_FORCE)
    - 可疑登录 (SUSPICIOUS_LOGIN)
    - 批量密码过期 (PASSWORD_EXPIRED_BATCH)
    - 数据导出 (DATA_EXPORT)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化安全告警管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._admin_emails = self._get_admin_emails()
        self._alert_history: List[Dict] = []
        self._alert_lock = threading.Lock()
    
    def _get_admin_emails(self) -> List[str]:
        """获取管理员邮箱列表"""
        admin_emails_str = os.environ.get('SECURITY_ADMIN_EMAILS', '')
        if admin_emails_str:
            return [e.strip() for e in admin_emails_str.split(',') if e.strip()]
        
        try:
            from models import UserAccess
            admins = UserAccess.query.filter_by(role='admin', has_access=True).all()
            return [a.email for a in admins if a.email]
        except Exception as e:
            logger.warning(f"获取管理员邮箱失败: {e}")
            return []
    
    def send_admin_alert(
        self, 
        alert_type: SecurityAlertType, 
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        向管理员发送安全告警
        
        Args:
            alert_type: 告警类型
            details: 告警详情
        
        Returns:
            Dict包含发送结果
        """
        alert_id = hashlib.sha256(
            f"{datetime.utcnow().isoformat()}:{alert_type.value}:{json.dumps(details, sort_keys=True)}".encode()
        ).hexdigest()[:16]
        
        alert_record = {
            'alert_id': alert_id,
            'alert_type': alert_type.value,
            'details': details,
            'timestamp': datetime.utcnow().isoformat(),
            'sent_to': self._admin_emails,
            'status': 'pending'
        }
        
        alert_titles = {
            SecurityAlertType.BRUTE_FORCE: {
                'en': 'Security Alert: Brute Force Attack Detected',
                'zh': '安全告警：检测到暴力破解攻击'
            },
            SecurityAlertType.SUSPICIOUS_LOGIN: {
                'en': 'Security Alert: Suspicious Login Detected',
                'zh': '安全告警：检测到可疑登录'
            },
            SecurityAlertType.PASSWORD_EXPIRED_BATCH: {
                'en': 'Security Alert: Multiple Passwords Expired',
                'zh': '安全告警：多个用户密码已过期'
            },
            SecurityAlertType.DATA_EXPORT: {
                'en': 'Security Alert: Sensitive Data Export',
                'zh': '安全告警：敏感数据导出'
            }
        }
        
        title = alert_titles.get(alert_type, {'en': 'Security Alert', 'zh': '安全告警'})
        
        try:
            email_enabled = os.environ.get('SECURITY_ALERTS_EMAIL_ENABLED', 'false').lower() == 'true'
            
            if email_enabled and self._admin_emails:
                self._send_email_alert(title, alert_type, details)
            
            audit_logger.log(
                level=AuditLevel.SECURITY,
                category=AuditCategory.SYSTEM,
                action=AuditAction.SUSPICIOUS_ACTIVITY,
                status="alert_sent",
                details={
                    'alert_id': alert_id,
                    'alert_type': alert_type.value,
                    'alert_details': details,
                    'recipients': self._admin_emails
                }
            )
            
            alert_record['status'] = 'sent'
            
        except Exception as e:
            logger.error(f"发送安全告警失败: {e}")
            alert_record['status'] = 'failed'
            alert_record['error'] = str(e)
        
        with self._alert_lock:
            self._alert_history.append(alert_record)
            self._alert_history = self._alert_history[-100:]
        
        logger.warning(f"安全告警: [{alert_type.value}] {json.dumps(details, ensure_ascii=False)}")
        
        return alert_record
    
    def _send_email_alert(
        self, 
        title: Dict[str, str], 
        alert_type: SecurityAlertType, 
        details: Dict[str, Any]
    ):
        """发送邮件告警"""
        try:
            from gmail_oauth_service import send_email_smtp
        except ImportError:
            send_email_smtp = None
            logger.warning("gmail_oauth_service not available, email alerts disabled")
        
        if send_email_smtp is None:
            logger.warning(f"Email alert skipped (no email service): {alert_type.value}")
            return
            
        try:
            body = f"""
安全告警 / Security Alert
=========================

告警类型 / Alert Type: {alert_type.value}
时间 / Time: {datetime.utcnow().isoformat()}

详情 / Details:
{json.dumps(details, indent=2, ensure_ascii=False)}

---
HashInsight Enterprise Security System
"""
            
            for admin_email in self._admin_emails:
                send_email_smtp(admin_email, title['zh'], body)
                
        except Exception as e:
            logger.error(f"发送告警邮件失败: {e}")
            raise
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """获取最近的告警记录"""
        with self._alert_lock:
            return list(reversed(self._alert_history[-limit:]))


class DataAccessLogger:
    """
    敏感数据访问日志记录器
    
    记录对敏感数据的所有访问操作，包括:
    - 凭证 (credentials)
    - 客户数据 (customer_data)
    - 财务数据 (financial_data)
    - 审计日志 (audit_logs)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化数据访问日志记录器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._access_log: List[Dict] = []
        self._log_lock = threading.Lock()
    
    def log_sensitive_access(
        self,
        user_id: str,
        resource_type: SensitiveResourceType,
        resource_id: str,
        action: str,
        ip_address: str = None,
        user_agent: str = None,
        details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        记录敏感数据访问
        
        Args:
            user_id: 用户ID
            resource_type: 资源类型 (credentials, customer_data, financial_data, audit_logs)
            resource_id: 资源ID
            action: 操作类型 (read, create, update, delete, export)
            ip_address: 客户端IP地址
            user_agent: 用户代理字符串
            details: 额外详情
        
        Returns:
            Dict包含日志记录信息
        """
        access_id = hashlib.sha256(
            f"{datetime.utcnow().isoformat()}:{user_id}:{resource_type.value}:{resource_id}:{action}".encode()
        ).hexdigest()[:16]
        
        access_record = {
            'access_id': access_id,
            'user_id': str(user_id),
            'resource_type': resource_type.value,
            'resource_id': str(resource_id),
            'action': action,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details or {}
        }
        
        action_map = {
            'read': AuditAction.READ,
            'create': AuditAction.CREATE,
            'update': AuditAction.UPDATE,
            'delete': AuditAction.DELETE,
            'export': AuditAction.EXPORT
        }
        
        audit_action = action_map.get(action.lower(), AuditAction.READ)
        
        audit_logger.log(
            level=AuditLevel.INFO,
            category=AuditCategory.DATA_ACCESS,
            action=audit_action,
            status="success",
            user_id=str(user_id),
            resource_type=resource_type.value,
            resource_id=str(resource_id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                'access_id': access_id,
                'sensitive_resource': True,
                **(details or {})
            }
        )
        
        with self._log_lock:
            self._access_log.append(access_record)
            self._access_log = self._access_log[-1000:]
        
        if action.lower() == 'export':
            SecurityAlertManager().send_admin_alert(
                SecurityAlertType.DATA_EXPORT,
                {
                    'user_id': user_id,
                    'resource_type': resource_type.value,
                    'resource_id': resource_id,
                    'ip_address': ip_address
                }
            )
        
        logger.info(
            f"敏感数据访问: user={user_id}, type={resource_type.value}, "
            f"resource={resource_id}, action={action}"
        )
        
        return access_record
    
    def get_access_history(
        self,
        user_id: str = None,
        resource_type: SensitiveResourceType = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取访问历史记录
        
        Args:
            user_id: 过滤用户ID
            resource_type: 过滤资源类型
            limit: 返回记录数限制
        
        Returns:
            访问记录列表
        """
        with self._log_lock:
            records = self._access_log.copy()
        
        if user_id:
            records = [r for r in records if r['user_id'] == str(user_id)]
        
        if resource_type:
            records = [r for r in records if r['resource_type'] == resource_type.value]
        
        return list(reversed(records[-limit:]))


login_security_manager = LoginSecurityManager()
password_policy_manager = PasswordPolicyManager()
security_alert_manager = SecurityAlertManager()
data_access_logger = DataAccessLogger()


__all__ = [
    'SecurityAlertType',
    'SensitiveResourceType',
    'PasswordValidationResult',
    'cleanup_old_audit_logs',
    'setup_audit_log_cleanup_scheduler',
    'LoginSecurityManager',
    'PasswordPolicyManager',
    'SecurityAlertManager',
    'DataAccessLogger',
    'login_security_manager',
    'password_policy_manager',
    'security_alert_manager',
    'data_access_logger'
]
