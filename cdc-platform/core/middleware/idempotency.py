"""
HashInsight CDC Platform - API Idempotency Middleware
API层幂等性验证中间件

功能：
1. 验证POST/PATCH/PUT/DELETE请求必须包含Idempotency-Key头
2. 检查Idempotency-Key是否已被使用（防止重复请求）
3. 缓存请求结果，相同Key返回缓存响应
4. 支持TTL过期清理

Author: HashInsight Team
Version: 1.0.0
"""
import os
import json
import hashlib
import logging
from functools import wraps
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from flask import request, jsonify, Response, g
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core.infra.database import db
from core.infra.redis_client import redis_client

logger = logging.getLogger(__name__)

# 配置
IDEMPOTENCY_KEY_HEADER = 'Idempotency-Key'
IDEMPOTENCY_TTL = int(os.getenv('IDEMPOTENCY_TTL', 86400))  # 24小时
IDEMPOTENCY_ENABLED = os.getenv('IDEMPOTENCY_ENABLED', 'true').lower() == 'true'

class IdempotencyManager:
    """
    幂等性管理器
    
    使用Redis缓存和PostgreSQL持久化双重机制：
    1. Redis：快速查询（缓存层）
    2. PostgreSQL：持久化存储（防止Redis数据丢失）
    """
    
    def __init__(self):
        self.redis = redis_client
        self.ttl = IDEMPOTENCY_TTL
        logger.info(f"✅ IdempotencyManager initialized (TTL={self.ttl}s)")
    
    def _generate_key(self, idempotency_key: str, method: str, path: str) -> str:
        """
        生成内部存储键
        
        格式：idempotency:{hash}
        hash = md5(idempotency_key + method + path)
        """
        composite = f"{idempotency_key}:{method}:{path}"
        hash_key = hashlib.md5(composite.encode()).hexdigest()
        return f"idempotency:{hash_key}"
    
    def check_and_store(
        self,
        idempotency_key: str,
        method: str,
        path: str,
        request_body: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        检查幂等键是否已使用，如果未使用则标记为处理中
        
        参数:
            idempotency_key: 客户端提供的幂等键
            method: HTTP方法
            path: 请求路径
            request_body: 请求体（可选）
        
        返回:
            None: 未使用（可以处理）
            Dict: 已使用，返回缓存的响应
        """
        storage_key = self._generate_key(idempotency_key, method, path)
        
        # 1. 先查Redis缓存
        try:
            cached_response = self.redis.get(storage_key)
            if cached_response:
                logger.info(f"🔄 Idempotent request detected (Redis): {idempotency_key}")
                return json.loads(cached_response)
        except Exception as e:
            logger.warning(f"⚠️ Redis check failed: {e}")
        
        # 2. 查PostgreSQL持久化存储
        try:
            sql = text("""
                SELECT response_status, response_body, created_at
                FROM idempotency_records
                WHERE idempotency_key = :key
                AND method = :method
                AND path = :path
                AND created_at > NOW() - INTERVAL ':ttl seconds'
                LIMIT 1
            """)
            
            result = db.session.execute(sql, {
                'key': idempotency_key,
                'method': method,
                'path': path,
                'ttl': self.ttl
            }).first()
            
            if result:
                logger.info(f"🔄 Idempotent request detected (PostgreSQL): {idempotency_key}")
                response_data = {
                    'status': result.response_status,
                    'body': result.response_body,
                    'cached_at': result.created_at.isoformat()
                }
                
                # 回填Redis缓存
                try:
                    remaining_ttl = int((result.created_at + timedelta(seconds=self.ttl) - datetime.utcnow()).total_seconds())
                    if remaining_ttl > 0:
                        self.redis.setex(storage_key, remaining_ttl, json.dumps(response_data))
                except Exception as e:
                    logger.warning(f"⚠️ Redis backfill failed: {e}")
                
                return response_data
        
        except SQLAlchemyError as e:
            logger.error(f"❌ PostgreSQL check failed: {e}")
        
        # 3. 未使用，标记为处理中（Redis中设置占位符）
        try:
            placeholder = json.dumps({
                'status': 'processing',
                'started_at': datetime.utcnow().isoformat()
            })
            self.redis.setex(storage_key, 300, placeholder)  # 5分钟处理超时
        except Exception as e:
            logger.warning(f"⚠️ Redis placeholder failed: {e}")
        
        return None
    
    def save_response(
        self,
        idempotency_key: str,
        method: str,
        path: str,
        status_code: int,
        response_body: Dict[str, Any]
    ):
        """
        保存请求响应（Redis + PostgreSQL）
        
        参数:
            idempotency_key: 幂等键
            method: HTTP方法
            path: 请求路径
            status_code: HTTP状态码
            response_body: 响应体
        """
        storage_key = self._generate_key(idempotency_key, method, path)
        
        response_data = {
            'status': status_code,
            'body': response_body,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        # 1. 保存到Redis（快速访问）
        try:
            self.redis.setex(
                storage_key,
                self.ttl,
                json.dumps(response_data)
            )
            logger.debug(f"💾 Saved to Redis: {idempotency_key}")
        except Exception as e:
            logger.error(f"❌ Redis save failed: {e}")
        
        # 2. 保存到PostgreSQL（持久化）
        try:
            sql = text("""
                INSERT INTO idempotency_records (
                    idempotency_key,
                    method,
                    path,
                    response_status,
                    response_body,
                    created_at
                )
                VALUES (
                    :key, :method, :path, :status, :body::jsonb, NOW()
                )
                ON CONFLICT (idempotency_key, method, path) 
                DO UPDATE SET
                    response_status = EXCLUDED.response_status,
                    response_body = EXCLUDED.response_body,
                    created_at = EXCLUDED.created_at
            """)
            
            db.session.execute(sql, {
                'key': idempotency_key,
                'method': method,
                'path': path,
                'status': status_code,
                'body': json.dumps(response_body)
            })
            db.session.commit()
            logger.debug(f"💾 Saved to PostgreSQL: {idempotency_key}")
        
        except SQLAlchemyError as e:
            logger.error(f"❌ PostgreSQL save failed: {e}")
            db.session.rollback()
    
    def cleanup_expired(self) -> int:
        """
        清理过期的幂等性记录
        
        返回:
            清理的记录数
        """
        try:
            sql = text("""
                DELETE FROM idempotency_records
                WHERE created_at < NOW() - INTERVAL ':ttl seconds'
            """)
            
            result = db.session.execute(sql, {'ttl': self.ttl})
            count = result.rowcount
            db.session.commit()
            
            logger.info(f"🧹 Cleaned up {count} expired idempotency records")
            return count
        
        except SQLAlchemyError as e:
            logger.error(f"❌ Cleanup failed: {e}")
            db.session.rollback()
            return 0

# 全局实例
idempotency_manager = IdempotencyManager()

def require_idempotency_key(f):
    """
    装饰器：要求POST/PATCH/PUT/DELETE请求包含Idempotency-Key
    
    使用示例:
    ```python
    @app.route('/api/miners', methods=['POST'])
    @require_idempotency_key
    def add_miner():
        # 业务逻辑
        return jsonify({'success': True})
    ```
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 仅对修改类请求强制要求
        if request.method in ['POST', 'PATCH', 'PUT', 'DELETE']:
            if not IDEMPOTENCY_ENABLED:
                logger.debug("⏭️ Idempotency check disabled")
                return f(*args, **kwargs)
            
            idempotency_key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
            
            if not idempotency_key:
                return jsonify({
                    'error': 'Idempotency-Key header is required',
                    'message': f'Please provide {IDEMPOTENCY_KEY_HEADER} header for {request.method} requests',
                    'code': 'IDEMPOTENCY_KEY_REQUIRED'
                }), 400
            
            # 检查幂等性
            cached_response = idempotency_manager.check_and_store(
                idempotency_key=idempotency_key,
                method=request.method,
                path=request.path,
                request_body=request.get_json(silent=True)
            )
            
            if cached_response:
                # 返回缓存响应
                return jsonify({
                    'cached': True,
                    'cached_at': cached_response.get('cached_at'),
                    'data': cached_response.get('body')
                }), cached_response.get('status', 200)
            
            # 存储幂等键到g对象（供after_request使用）
            g.idempotency_key = idempotency_key
        
        return f(*args, **kwargs)
    
    return decorated_function

def after_request_idempotency(response: Response) -> Response:
    """
    请求后处理：保存响应到幂等性存储
    
    需要在Flask app中注册：
    ```python
    app.after_request(after_request_idempotency)
    ```
    """
    # 仅处理修改类请求
    if request.method in ['POST', 'PATCH', 'PUT', 'DELETE']:
        if not IDEMPOTENCY_ENABLED:
            return response
        
        idempotency_key = getattr(g, 'idempotency_key', None)
        
        if idempotency_key and 200 <= response.status_code < 300:
            try:
                response_body = response.get_json(silent=True) or {}
                
                idempotency_manager.save_response(
                    idempotency_key=idempotency_key,
                    method=request.method,
                    path=request.path,
                    status_code=response.status_code,
                    response_body=response_body
                )
            except Exception as e:
                logger.error(f"❌ Failed to save idempotent response: {e}")
    
    return response
