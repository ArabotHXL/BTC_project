"""
HashInsight CDC Platform - Audit Logger
审计日志服务，记录所有关键操作
"""
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    审计日志服务
    
    功能：
    1. 记录用户操作日志
    2. 支持多租户
    3. 记录IP、User-Agent等元数据
    4. 支持合规审计（SOC2、GDPR）
    """
    
    def __init__(self, db):
        """
        初始化审计日志服务
        
        参数:
            db: SQLAlchemy数据库实例
        """
        self.db = db
        self._ensure_table_exists()
        logger.info("✅ AuditLogger initialized")
    
    def _ensure_table_exists(self):
        """确保审计日志表存在"""
        try:
            sql = text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    user_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    details JSONB,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL DEFAULT true,
                    error_message TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            
            self.db.session.execute(sql)
            self.db.session.commit()
            
            # 创建索引
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_logs (user_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_audit_tenant_time ON audit_logs (tenant_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs (action)",
                "CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs (resource_type, resource_id)"
            ]
            
            for index_sql in index_sqls:
                self.db.session.execute(text(index_sql))
            
            self.db.session.commit()
            
        except SQLAlchemyError as e:
            logger.warning(f"⚠️ Audit table creation warning: {e}")
            self.db.session.rollback()
    
    def log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        tenant_id: str = 'default',
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[str]:
        """
        记录审计日志
        
        参数:
            user_id: 用户ID
            action: 操作类型（如 'create', 'update', 'delete', 'view'）
            resource_type: 资源类型（如 'miner', 'trade', 'user'）
            resource_id: 资源ID（可选）
            details: 操作详情（JSON）
            tenant_id: 租户ID
            ip_address: IP地址
            user_agent: User-Agent
            success: 操作是否成功
            error_message: 错误信息（如果失败）
        
        返回:
            日志ID或None
        
        示例:
            >>> audit.log(
            ...     user_id='user123',
            ...     action='create',
            ...     resource_type='miner',
            ...     resource_id='miner456',
            ...     details={'hashrate': 100, 'model': 'S19'},
            ...     ip_address='192.168.1.1'
            ... )
        """
        try:
            log_id = str(uuid.uuid4())
            
            sql = text("""
                INSERT INTO audit_logs (
                    id, user_id, tenant_id, action, resource_type, resource_id,
                    details, ip_address, user_agent, success, error_message, created_at
                )
                VALUES (
                    :id, :user_id, :tenant_id, :action, :resource_type, :resource_id,
                    :details::jsonb, :ip_address, :user_agent, :success, :error_message, :created_at
                )
                RETURNING id
            """)
            
            result = self.db.session.execute(sql, {
                'id': log_id,
                'user_id': user_id,
                'tenant_id': tenant_id,
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'details': details or {},
                'ip_address': ip_address,
                'user_agent': user_agent,
                'success': success,
                'error_message': error_message,
                'created_at': datetime.utcnow()
            })
            
            # 注意：不在这里commit，让调用方控制事务
            # self.db.session.commit()
            
            logger.debug(
                f"📝 Audit log: user={user_id}, action={action}, "
                f"resource={resource_type}/{resource_id}, success={success}"
            )
            
            return log_id
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to write audit log: {e}")
            return None
    
    def log_from_request(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        tenant_id: str = 'default',
        request=None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[str]:
        """
        从Flask request对象自动提取元数据并记录日志
        
        参数:
            request: Flask request对象
            其他参数同 log()
        
        返回:
            日志ID或None
        """
        ip_address = None
        user_agent = None
        
        if request:
            # 获取真实IP（考虑代理）
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address and ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()
            
            # 获取User-Agent
            user_agent = request.headers.get('User-Agent', '')[:500]  # 限制长度
        
        return self.log(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
    
    def get_user_logs(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        获取用户的审计日志
        
        参数:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
        
        返回:
            日志列表
        """
        try:
            sql = text("""
                SELECT id, action, resource_type, resource_id, details,
                       ip_address, success, error_message, created_at
                FROM audit_logs
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            
            result = self.db.session.execute(sql, {
                'user_id': user_id,
                'limit': limit,
                'offset': offset
            })
            
            logs = []
            for row in result:
                logs.append({
                    'id': row.id,
                    'action': row.action,
                    'resource_type': row.resource_type,
                    'resource_id': row.resource_id,
                    'details': row.details,
                    'ip_address': row.ip_address,
                    'success': row.success,
                    'error_message': row.error_message,
                    'created_at': row.created_at.isoformat()
                })
            
            return logs
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to get user logs: {e}")
            return []
    
    def get_resource_logs(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50
    ) -> list:
        """
        获取资源的操作历史
        
        参数:
            resource_type: 资源类型
            resource_id: 资源ID
            limit: 返回数量限制
        
        返回:
            日志列表
        """
        try:
            sql = text("""
                SELECT id, user_id, action, details, ip_address,
                       success, error_message, created_at
                FROM audit_logs
                WHERE resource_type = :resource_type
                AND resource_id = :resource_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = self.db.session.execute(sql, {
                'resource_type': resource_type,
                'resource_id': resource_id,
                'limit': limit
            })
            
            logs = []
            for row in result:
                logs.append({
                    'id': row.id,
                    'user_id': row.user_id,
                    'action': row.action,
                    'details': row.details,
                    'ip_address': row.ip_address,
                    'success': row.success,
                    'error_message': row.error_message,
                    'created_at': row.created_at.isoformat()
                })
            
            return logs
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to get resource logs: {e}")
            return []
    
    def get_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取审计统计信息
        
        参数:
            tenant_id: 租户ID（可选，为None时返回所有租户）
        
        返回:
            统计字典
        """
        try:
            if tenant_id:
                sql = text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE success = true) as success_count,
                        COUNT(*) FILTER (WHERE success = false) as failure_count,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT action) as unique_actions
                    FROM audit_logs
                    WHERE tenant_id = :tenant_id
                """)
                result = self.db.session.execute(sql, {'tenant_id': tenant_id}).first()
            else:
                sql = text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE success = true) as success_count,
                        COUNT(*) FILTER (WHERE success = false) as failure_count,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT action) as unique_actions
                    FROM audit_logs
                """)
                result = self.db.session.execute(sql).first()
            
            return {
                'total': result.total or 0,
                'success_count': result.success_count or 0,
                'failure_count': result.failure_count or 0,
                'unique_users': result.unique_users or 0,
                'unique_actions': result.unique_actions or 0
            }
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to get audit stats: {e}")
            return {'error': str(e)}
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """
        清理旧的审计日志（合规要求：保留至少90天）
        
        参数:
            days: 保留天数（默认90天）
        
        返回:
            删除的日志数量
        """
        if days < 90:
            logger.warning("⚠️ Audit logs must be retained for at least 90 days (compliance)")
            days = 90
        
        try:
            sql = text("""
                DELETE FROM audit_logs
                WHERE created_at < NOW() - INTERVAL ':days days'
            """)
            
            result = self.db.session.execute(sql, {'days': days})
            count = result.rowcount
            self.db.session.commit()
            
            logger.info(f"🧹 Cleaned up {count} old audit logs (>{days} days)")
            return count
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Cleanup failed: {e}")
            self.db.session.rollback()
            return 0
