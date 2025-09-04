"""
安全中间件 - Sprint 1 安全加固要求
实现CSRF保护、限流、安全响应头等安全措施
"""
from flask import request, abort, g, session
from functools import wraps
import time
import hashlib
import os
from collections import defaultdict, deque
import logging

# 限流存储（内存中，生产环境应使用Redis）
rate_limit_storage = defaultdict(lambda: deque())

def init_security_middleware(app):
    """初始化安全中间件"""
    
    # 注册组织隔离中间件
    app.before_request(organization_isolation)
    
    # 添加安全响应头
    @app.after_request
    def add_security_headers(response):
        """添加安全响应头"""
        if os.environ.get('SECURE_HEADERS_ENABLED', 'false').lower() == 'true':
            # CSRF保护头部
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # 内容安全策略
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
                "font-src 'self' fonts.gstatic.com cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "connect-src 'self' api.coingecko.com blockchain.info api.coinwarz.com"
            )
        
        return response
    
    # 限流中间件
    @app.before_request
    def rate_limiting():
        """基础限流保护"""
        if os.environ.get('RATE_LIMITING_ENABLED', 'false').lower() != 'true':
            return
        
        # 获取客户端IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # 检查限流
        current_time = time.time()
        max_requests = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', '60'))
        window_size = 60  # 1分钟窗口
        
        # 清理过期请求
        cutoff_time = current_time - window_size
        while rate_limit_storage[client_ip] and rate_limit_storage[client_ip][0] < cutoff_time:
            rate_limit_storage[client_ip].popleft()
        
        # 检查是否超过限制
        if len(rate_limit_storage[client_ip]) >= max_requests:
            abort(429, description="Rate limit exceeded")
        
        # 记录本次请求
        rate_limit_storage[client_ip].append(current_time)

def csrf_token():
    """生成CSRF令牌"""
    if 'csrf_token' not in session:
        session['csrf_token'] = hashlib.md5(
            (str(time.time()) + os.urandom(16).hex()).encode()
        ).hexdigest()
    return session['csrf_token']

def validate_csrf():
    """验证CSRF令牌"""
    if os.environ.get('CSRF_ENABLED', 'false').lower() != 'true':
        return True
    
    # GET请求不需要CSRF验证
    if request.method in ['GET', 'HEAD', 'OPTIONS']:
        return True
    
    # 检查令牌
    token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    return token and token == session.get('csrf_token')

def require_csrf(f):
    """CSRF保护装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_csrf():
            abort(403, description="CSRF token validation failed")
        return f(*args, **kwargs)
    return decorated_function

# 组织隔离中间件将在init_security_middleware中注册
def organization_isolation():
    """组织隔离中间件 - Sprint 1 RBAC要求"""
    # 跳过公共页面和API
    public_paths = ['/healthz', '/readiness', '/liveness', '/login', '/register', '/hosting/status']
    if any(request.path.startswith(path) for path in public_paths):
        return
    
    # 从会话中获取用户组织信息
    user_id = session.get('user_id')
    user_role = session.get('role', 'viewer')
    
    if user_id:
        # 设置当前用户上下文
        g.current_user_id = user_id
        g.current_user_role = user_role
        g.is_owner = user_role in ['owner', 'admin']
        g.is_host_user = user_role in ['owner', 'admin', 'mining_site', 'host_manager']
        g.is_client_user = user_role in ['owner', 'admin', 'client', 'client_viewer']
        
        # 路径权限检查
        if request.path.startswith('/hosting/') and not g.is_host_user:
            abort(403, description="Access denied: Host privileges required")
        elif request.path.startswith('/client/') and not g.is_client_user:
            abort(403, description="Access denied: Client privileges required")

def requires_organization_role(required_roles):
    """组织角色权限装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('role', 'viewer')
            if user_role not in required_roles:
                abort(403, description=f"Access denied: Required roles: {', '.join(required_roles)}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 审计日志中间件
def log_user_action(action, resource=None, details=None):
    """记录用户操作到审计日志"""
    try:
        from datetime import datetime
        # 简化审计日志，记录到应用日志
        logging.info(f"AUDIT: User {session.get('user_id')} performed {action} on {resource}")
        
        # 如果需要数据库审计日志，可以取消下面的注释
        # from models import AuditLog, db
        
        audit_entry = AuditLog(
            user_id=session.get('user_id'),
            action=action,
            resource=resource,
            details=details,
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=request.headers.get('User-Agent'),
            timestamp=datetime.now()
        )
        
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        # 审计日志失败不应影响主要功能
        logging.error(f"审计日志记录失败: {e}")

def audit_log(action, resource=None):
    """审计日志装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            # 只记录成功的操作
            if hasattr(result, 'status_code') and result.status_code < 400:
                log_user_action(action, resource, str(kwargs))
            elif not hasattr(result, 'status_code'):
                log_user_action(action, resource, str(kwargs))
            return result
        return decorated_function
    return decorator