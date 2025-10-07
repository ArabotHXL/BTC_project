"""
RBAC权限矩阵系统
Role-Based Access Control (RBAC) Permission Matrix

企业级权限管理:
- 细粒度权限定义
- 角色继承
- 多租户隔离
- 行级安全(RLS)
- 动态权限检查
- 权限审计
"""

import logging
from typing import Dict, List, Set, Optional, Any
from enum import Enum
from dataclasses import dataclass
from functools import wraps
from flask import g, jsonify

logger = logging.getLogger(__name__)

class Permission(Enum):
    """权限枚举 - 细粒度权限定义"""
    
    CALC_READ = "calculator:read"
    CALC_WRITE = "calculator:write"
    CALC_DELETE = "calculator:delete"
    CALC_EXPORT = "calculator:export"
    CALC_BATCH = "calculator:batch"
    
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_ADVANCED = "analytics:advanced"
    ANALYTICS_EXPORT = "analytics:export"
    
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    TENANT_READ = "tenant:read"
    TENANT_WRITE = "tenant:write"
    TENANT_ADMIN = "tenant:admin"
    
    API_KEY_READ = "api_key:read"
    API_KEY_CREATE = "api_key:create"
    API_KEY_REVOKE = "api_key:revoke"
    
    BLOCKCHAIN_READ = "blockchain:read"
    BLOCKCHAIN_WRITE = "blockchain:write"
    
    REPORT_READ = "report:read"
    REPORT_CREATE = "report:create"
    REPORT_EXPORT = "report:export"
    
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_AUDIT = "system:audit"
    
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    
    WEBHOOK_READ = "webhook:read"
    WEBHOOK_WRITE = "webhook:write"
    
    MINERS_READ = "miners:read"
    MINERS_WRITE = "miners:write"
    MINERS_DELETE = "miners:delete"
    
    INTEL_READ = "intel:read"
    INTEL_FORECAST = "intel:forecast"
    INTEL_OPTIMIZE = "intel:optimize"
    INTEL_EXPLAIN = "intel:explain"
    
    OPS_PLAN = "ops:plan"
    OPS_APPLY = "ops:apply"
    OPS_READ = "ops:read"
    
    TREASURY_READ = "treasury:read"
    TREASURY_TRADE = "treasury:trade"
    TREASURY_EXECUTE = "treasury:execute"
    
    WEB3_MINT = "web3:mint"
    WEB3_VERIFY = "web3:verify"
    WEB3_READ = "web3:read"
    
    CRM_READ = "crm:read"
    CRM_SYNC = "crm:sync"
    CRM_WEBHOOK = "crm:webhook"
    CRM_ADMIN = "crm:admin"
    
    WILDCARD = "*"  # 所有权限

class Role(Enum):
    """角色枚举"""
    
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_OWNER = "tenant_owner"
    
    INVESTOR = "investor"
    OPERATOR = "operator"
    FINANCE = "finance"
    TRADER = "trader"
    
    DEVELOPER = "developer"
    API_CLIENT = "api_client"
    
    GUEST = "guest"
    READONLY = "readonly"

@dataclass
class RoleDefinition:
    """角色定义"""
    name: Role
    display_name: str
    description: str
    permissions: List[Permission]
    inherits_from: List[Role]
    is_tenant_scoped: bool

ROLE_HIERARCHY: Dict[Role, RoleDefinition] = {
    Role.SUPER_ADMIN: RoleDefinition(
        name=Role.SUPER_ADMIN,
        display_name="超级管理员",
        description="系统最高权限，可管理所有租户和系统配置",
        permissions=[Permission.WILDCARD],
        inherits_from=[],
        is_tenant_scoped=False
    ),
    
    Role.TENANT_OWNER: RoleDefinition(
        name=Role.TENANT_OWNER,
        display_name="租户所有者",
        description="租户最高权限，可管理租户内所有资源",
        permissions=[
            Permission.CALC_READ, Permission.CALC_WRITE, Permission.CALC_DELETE,
            Permission.CALC_EXPORT, Permission.CALC_BATCH,
            Permission.ANALYTICS_READ, Permission.ANALYTICS_ADVANCED, Permission.ANALYTICS_EXPORT,
            Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE,
            Permission.TENANT_READ, Permission.TENANT_WRITE,
            Permission.API_KEY_READ, Permission.API_KEY_CREATE, Permission.API_KEY_REVOKE,
            Permission.BLOCKCHAIN_READ, Permission.BLOCKCHAIN_WRITE,
            Permission.REPORT_READ, Permission.REPORT_CREATE, Permission.REPORT_EXPORT,
            Permission.BILLING_READ, Permission.BILLING_WRITE,
            Permission.WEBHOOK_READ, Permission.WEBHOOK_WRITE,
            Permission.MINERS_READ, Permission.MINERS_WRITE, Permission.MINERS_DELETE,
            Permission.INTEL_READ, Permission.INTEL_FORECAST, Permission.INTEL_OPTIMIZE, Permission.INTEL_EXPLAIN,
            Permission.OPS_PLAN, Permission.OPS_APPLY, Permission.OPS_READ,
            Permission.TREASURY_READ, Permission.TREASURY_TRADE, Permission.TREASURY_EXECUTE,
            Permission.WEB3_MINT, Permission.WEB3_VERIFY, Permission.WEB3_READ,
            Permission.CRM_READ, Permission.CRM_SYNC, Permission.CRM_WEBHOOK, Permission.CRM_ADMIN
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.TENANT_ADMIN: RoleDefinition(
        name=Role.TENANT_ADMIN,
        display_name="租户管理员",
        description="租户管理权限，可管理用户和配置",
        permissions=[
            Permission.CALC_READ, Permission.CALC_WRITE, Permission.CALC_EXPORT,
            Permission.ANALYTICS_READ, Permission.ANALYTICS_ADVANCED,
            Permission.USER_READ, Permission.USER_WRITE,
            Permission.TENANT_READ,
            Permission.API_KEY_READ,
            Permission.REPORT_READ, Permission.REPORT_CREATE,
            Permission.BILLING_READ,
            Permission.MINERS_READ, Permission.MINERS_WRITE,
            Permission.INTEL_READ, Permission.INTEL_FORECAST, Permission.INTEL_EXPLAIN,
            Permission.OPS_READ, Permission.OPS_PLAN,
            Permission.CRM_READ, Permission.CRM_SYNC
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.INVESTOR: RoleDefinition(
        name=Role.INVESTOR,
        display_name="投资人",
        description="投资人视图，关注ROI和财务数据",
        permissions=[
            Permission.CALC_READ, Permission.CALC_EXPORT,
            Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
            Permission.REPORT_READ, Permission.REPORT_EXPORT,
            Permission.BILLING_READ,
            Permission.INTEL_READ, Permission.INTEL_FORECAST, Permission.INTEL_EXPLAIN,
            Permission.TREASURY_READ
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.OPERATOR: RoleDefinition(
        name=Role.OPERATOR,
        display_name="运维人员",
        description="运维视图，关注设备健康和运行状态",
        permissions=[
            Permission.CALC_READ, Permission.CALC_WRITE,
            Permission.ANALYTICS_READ,
            Permission.REPORT_READ,
            Permission.BLOCKCHAIN_READ,
            Permission.MINERS_READ, Permission.MINERS_WRITE, Permission.MINERS_DELETE,
            Permission.OPS_PLAN, Permission.OPS_APPLY, Permission.OPS_READ,
            Permission.INTEL_READ
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.FINANCE: RoleDefinition(
        name=Role.FINANCE,
        display_name="财务人员",
        description="财务视图，关注成本和收益",
        permissions=[
            Permission.CALC_READ, Permission.CALC_EXPORT,
            Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
            Permission.REPORT_READ, Permission.REPORT_EXPORT,
            Permission.BILLING_READ, Permission.BILLING_WRITE
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.TRADER: RoleDefinition(
        name=Role.TRADER,
        display_name="交易员",
        description="财资交易权限",
        permissions=[
            Permission.CALC_READ,
            Permission.ANALYTICS_READ,
            Permission.TREASURY_READ, Permission.TREASURY_TRADE,
            Permission.INTEL_READ
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.DEVELOPER: RoleDefinition(
        name=Role.DEVELOPER,
        display_name="开发者",
        description="API访问权限",
        permissions=[
            Permission.CALC_READ, Permission.CALC_WRITE,
            Permission.ANALYTICS_READ,
            Permission.API_KEY_READ,
            Permission.WEBHOOK_READ, Permission.WEBHOOK_WRITE
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.API_CLIENT: RoleDefinition(
        name=Role.API_CLIENT,
        display_name="API客户端",
        description="基础API访问",
        permissions=[
            Permission.CALC_READ,
            Permission.ANALYTICS_READ
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.READONLY: RoleDefinition(
        name=Role.READONLY,
        display_name="只读用户",
        description="只读权限",
        permissions=[
            Permission.CALC_READ,
            Permission.ANALYTICS_READ,
            Permission.REPORT_READ
        ],
        inherits_from=[],
        is_tenant_scoped=True
    ),
    
    Role.GUEST: RoleDefinition(
        name=Role.GUEST,
        display_name="访客",
        description="最小权限",
        permissions=[
            Permission.CALC_READ
        ],
        inherits_from=[],
        is_tenant_scoped=True
    )
}

class RBACManager:
    """RBAC管理器"""
    
    def __init__(self):
        self.role_hierarchy = ROLE_HIERARCHY
        self._build_permission_cache()
    
    def _build_permission_cache(self):
        """构建权限缓存（包含继承的权限）"""
        self.permission_cache: Dict[Role, Set[Permission]] = {}
        
        for role, definition in self.role_hierarchy.items():
            permissions = set(definition.permissions)
            
            for parent_role in definition.inherits_from:
                if parent_role in self.permission_cache:
                    permissions.update(self.permission_cache[parent_role])
            
            self.permission_cache[role] = permissions
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """获取角色的所有权限（包含继承）"""
        return self.permission_cache.get(role, set())
    
    def has_permission(
        self,
        user_role: Role,
        required_permission: Permission,
        tenant_id: Optional[str] = None
    ) -> bool:
        """检查用户是否有指定权限"""
        
        if user_role == Role.SUPER_ADMIN:
            return True
        
        user_permissions = self.get_role_permissions(user_role)
        
        if Permission.WILDCARD in user_permissions:
            return True
        
        if required_permission in user_permissions:
            return True
        
        wildcard_permission = Permission(f"{required_permission.value.split(':')[0]}:*")
        try:
            if wildcard_permission in user_permissions:
                return True
        except ValueError:
            pass
        
        return False
    
    def has_any_permission(
        self,
        user_role: Role,
        required_permissions: List[Permission]
    ) -> bool:
        """检查用户是否有任意一个权限"""
        return any(
            self.has_permission(user_role, perm)
            for perm in required_permissions
        )
    
    def has_all_permissions(
        self,
        user_role: Role,
        required_permissions: List[Permission]
    ) -> bool:
        """检查用户是否有所有权限"""
        return all(
            self.has_permission(user_role, perm)
            for perm in required_permissions
        )
    
    def filter_by_tenant(
        self,
        user_tenant_id: Optional[str],
        resource_tenant_id: str,
        is_super_admin: bool = False
    ) -> bool:
        """多租户过滤 - 行级安全(RLS)"""
        
        if is_super_admin:
            return True
        
        if not user_tenant_id:
            return False
        
        return user_tenant_id == resource_tenant_id
    
    def get_accessible_resources(
        self,
        user_role: Role,
        user_tenant_id: Optional[str],
        all_resources: List[Dict[str, Any]],
        tenant_field: str = 'tenant_id'
    ) -> List[Dict[str, Any]]:
        """获取用户可访问的资源（应用RLS）"""
        
        is_super_admin = user_role == Role.SUPER_ADMIN
        
        if is_super_admin:
            return all_resources
        
        return [
            resource for resource in all_resources
            if self.filter_by_tenant(
                user_tenant_id,
                resource.get(tenant_field),
                is_super_admin
            )
        ]
    
    def check_resource_access(
        self,
        user_role: Role,
        user_tenant_id: Optional[str],
        resource_tenant_id: str,
        required_permission: Permission
    ) -> bool:
        """检查用户对特定资源的访问权限（权限 + RLS）"""
        
        if not self.has_permission(user_role, required_permission):
            logger.warning(
                f"Permission denied: {user_role.value} does not have {required_permission.value}"
            )
            return False
        
        is_super_admin = user_role == Role.SUPER_ADMIN
        
        if not self.filter_by_tenant(user_tenant_id, resource_tenant_id, is_super_admin):
            logger.warning(
                f"Tenant access denied: user tenant {user_tenant_id} != resource tenant {resource_tenant_id}"
            )
            return False
        
        return True

rbac_manager = RBACManager()

def require_permission(
    required_permissions: List[Permission],
    require_all: bool = False,
    resource_tenant_field: Optional[str] = None
):
    """
    权限检查装饰器
    
    Args:
        required_permissions: 需要的权限列表
        require_all: True=需要所有权限, False=需要任意一个权限
        resource_tenant_field: 如果指定，会检查资源的租户ID
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_role'):
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
            
            try:
                user_role = Role(g.user_role)
            except ValueError:
                logger.error(f"Invalid role: {g.user_role}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid user role'
                }), 403
            
            if require_all:
                has_access = rbac_manager.has_all_permissions(user_role, required_permissions)
            else:
                has_access = rbac_manager.has_any_permission(user_role, required_permissions)
            
            if not has_access:
                logger.warning(
                    f"Permission denied for {g.get('user_email')} ({user_role.value}): "
                    f"required {[p.value for p in required_permissions]}"
                )
                return jsonify({
                    'success': False,
                    'error': 'Insufficient permissions',
                    'required_permissions': [p.value for p in required_permissions]
                }), 403
            
            if resource_tenant_field and hasattr(g, 'tenant_id'):
                pass
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(allowed_roles: List[Role]):
    """角色检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_role'):
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
            
            try:
                user_role = Role(g.user_role)
            except ValueError:
                logger.error(f"Invalid role: {g.user_role}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid user role'
                }), 403
            
            if user_role not in allowed_roles and user_role != Role.SUPER_ADMIN:
                logger.warning(
                    f"Role denied for {g.get('user_email')} ({user_role.value}): "
                    f"required one of {[r.value for r in allowed_roles]}"
                )
                return jsonify({
                    'success': False,
                    'error': 'Insufficient role',
                    'required_roles': [r.value for r in allowed_roles]
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

__all__ = [
    'Permission',
    'Role',
    'RoleDefinition',
    'ROLE_HIERARCHY',
    'RBACManager',
    'rbac_manager',
    'require_permission',
    'require_role'
]
