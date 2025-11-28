"""
RBAC权限矩阵系统 v2.0
Role-Based Access Control (RBAC) Permission Matrix

基于推荐的权限重新分配方案:
- 6个用户角色: Owner, Admin, Mining_Site_Owner, Client, Customer, Guest
- 11个功能模块: 基础功能、托管服务、智能限电、CRM系统、分析工具、智能层、用户管理、系统监控、Web3功能、财务管理、报表系统
- 3种访问级别: FULL(完全访问), READ(只读), NONE(无权限)
"""

import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
from flask import g, jsonify, session

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """访问级别"""
    FULL = "full"      # 完全访问 (✓ 绿色勾)
    READ = "read"      # 只读访问 (● 蓝色点)
    NONE = "none"      # 无权限 (✗ 红色叉)


class Role(Enum):
    """用户角色枚举 - 按权限从高到低排列"""
    OWNER = "owner"                         # 所有者 - 最高权限
    ADMIN = "admin"                         # 管理员
    MINING_SITE_OWNER = "mining_site_owner" # 矿场站点负责人
    CLIENT = "client"                       # 矿场客户端 (mining site client)
    CUSTOMER = "customer"                   # 应用客户 (App customer)
    GUEST = "guest"                         # 未登录访客
    
    # 保留旧角色映射兼容性
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_OWNER = "tenant_owner"
    MINING_SITE = "mining_site"
    USER = "user"


# 旧角色到新角色的映射
ROLE_MIGRATION_MAP = {
    'super_admin': Role.OWNER,
    'tenant_owner': Role.OWNER,
    'tenant_admin': Role.ADMIN,
    'mining_site': Role.MINING_SITE_OWNER,
    'user': Role.CUSTOMER,
    'guest': Role.GUEST,
    'owner': Role.OWNER,
    'admin': Role.ADMIN,
    'mining_site_owner': Role.MINING_SITE_OWNER,
    'client': Role.CLIENT,
    'customer': Role.CUSTOMER,
}


def normalize_role(role_str: str) -> Role:
    """将任意角色字符串规范化为新角色枚举"""
    if not role_str:
        return Role.GUEST
    
    role_lower = role_str.lower().strip()
    
    # 直接映射
    if role_lower in ROLE_MIGRATION_MAP:
        return ROLE_MIGRATION_MAP[role_lower]
    
    # 尝试枚举匹配
    try:
        return Role(role_lower)
    except ValueError:
        pass
    
    # 默认返回Guest
    logger.warning(f"未知角色 '{role_str}'，默认为Guest")
    return Role.GUEST


class Module(Enum):
    """功能模块枚举"""
    # 基础功能
    BASIC_CALCULATOR = "basic:calculator"           # 挖矿计算器(单个)
    BASIC_SETTINGS = "basic:settings"               # 用户个人设置
    BASIC_DASHBOARD = "basic:dashboard"             # 仪表盘首页
    
    # 托管服务 (Hosting)
    HOSTING_SITE_MGMT = "hosting:site_management"   # 矿场站点管理
    HOSTING_BATCH_CREATE = "hosting:batch_create"   # 矿机批量创建
    HOSTING_STATUS_MONITOR = "hosting:status_monitor" # 矿机状态监控
    HOSTING_TICKET = "hosting:ticket"               # 工单系统
    HOSTING_USAGE_TRACKING = "hosting:usage"        # 使用记录管理
    HOSTING_RECONCILIATION = "hosting:reconciliation" # 对账功能
    
    # 智能限电 (Curtailment)
    CURTAILMENT_STRATEGY = "curtailment:strategy"   # 限电策略计算
    CURTAILMENT_AI_PREDICT = "curtailment:ai_predict" # AI 24小时预测
    CURTAILMENT_EXECUTE = "curtailment:execute"     # 限电执行控制
    CURTAILMENT_EMERGENCY = "curtailment:emergency" # 紧急恢复
    CURTAILMENT_HISTORY = "curtailment:history"     # 限电历史查询
    
    # CRM系统
    CRM_CUSTOMER_MGMT = "crm:customer_management"   # 客户管理(创建/编辑/删除)
    CRM_CUSTOMER_VIEW = "crm:customer_view"         # 客户信息查看
    CRM_TRANSACTION = "crm:transaction"             # 交易/结算管理
    CRM_INVOICE = "crm:invoice"                     # 发票开具
    CRM_BROKER_COMMISSION = "crm:broker_commission" # 经纪人佣金
    CRM_ACTIVITY_LOG = "crm:activity_log"           # 活动记录
    
    # 分析工具 (Analytics)
    ANALYTICS_BATCH_CALC = "analytics:batch_calculator" # 批量计算器(6000+)
    ANALYTICS_NETWORK = "analytics:network"         # 网络分析
    ANALYTICS_TECHNICAL = "analytics:technical"     # 技术指标分析
    ANALYTICS_DERIBIT = "analytics:deribit"         # Deribit高级分析
    
    # 智能层 (AI Layer)
    AI_BTC_PREDICT = "ai:btc_predict"               # AI预测(BTC价格/难度)
    AI_ROI_EXPLAIN = "ai:roi_explain"               # ROI智能解释
    AI_ANOMALY_DETECT = "ai:anomaly_detect"         # 异常检测
    AI_POWER_OPTIMIZE = "ai:power_optimize"         # 功耗优化建议
    
    # 用户管理
    USER_CREATE = "user:create"                     # 创建用户
    USER_EDIT = "user:edit"                         # 编辑用户
    USER_DELETE = "user:delete"                     # 删除用户
    USER_ROLE_ASSIGN = "user:role_assign"           # 角色分配
    USER_LIST_VIEW = "user:list_view"               # 用户列表查看
    
    # 系统监控
    SYSTEM_HEALTH = "system:health"                 # 系统健康监控
    SYSTEM_PERFORMANCE = "system:performance"       # 性能监控
    SYSTEM_EVENT = "system:event"                   # 事件监控
    
    # Web3功能
    WEB3_BLOCKCHAIN_VERIFY = "web3:blockchain_verify"   # 区块链验证管理
    WEB3_TRANSPARENCY = "web3:transparency"         # 透明版本验证
    WEB3_SLA_NFT = "web3:sla_nft"                   # SLA NFT管理
    
    # 财务管理
    FINANCE_BILLING = "finance:billing"             # 账单管理
    FINANCE_BTC_SETTLE = "finance:btc_settlement"   # BTC结算/提现
    FINANCE_CRYPTO_PAY = "finance:crypto_payment"   # 加密支付
    
    # 报表系统
    REPORT_PDF = "report:pdf"                       # PDF报表生成
    REPORT_EXCEL = "report:excel"                   # Excel导出
    REPORT_PPT = "report:ppt"                       # PowerPoint报表


# ==================== 权限矩阵定义 ====================
# 基于用户提供的权限重新分配方案图片
# FULL = 完全访问, READ = 只读, NONE = 无权限

PERMISSION_MATRIX: Dict[Module, Dict[Role, AccessLevel]] = {
    # ==================== 基础功能 ====================
    Module.BASIC_CALCULATOR: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.FULL,  # 所有人可用，可做引流工具
    },
    Module.BASIC_SETTINGS: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.NONE,  # 需登录
    },
    Module.BASIC_DASHBOARD: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.READ,  # 登录后为个人站点视觉，未登录为公共看板
    },
    
    # ==================== 托管服务 ====================
    Module.HOSTING_SITE_MGMT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # 只读 - Client只需知道自己在哪个站点
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.HOSTING_BATCH_CREATE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 运营功能，只给平台/矿场
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.HOSTING_STATUS_MONITOR: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # Client只看自己矿机运行状态
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.HOSTING_TICKET: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,  # Client/App Customer可提自己工单
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.HOSTING_USAGE_TRACKING: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 包含机位使用、电费、服务记录等
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.HOSTING_RECONCILIATION: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 财务对账: 平台 vs 矿场 vs 客户
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== 智能限电 ====================
    Module.CURTAILMENT_STRATEGY: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # 策略由平台/矿场制定，Client只读
        Role.CLIENT: AccessLevel.READ,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CURTAILMENT_AI_PREDICT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # 高级功能，可做电价/功率预测
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CURTAILMENT_EXECUTE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 敏感操作，只能运维方执行
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CURTAILMENT_EMERGENCY: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 应急功能，通常运维触发
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CURTAILMENT_HISTORY: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # Client只看影响自己机队的限电记录
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== CRM系统 ====================
    Module.CRM_CUSTOMER_MGMT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.NONE,  # 销售运营后台功能
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CRM_CUSTOMER_VIEW: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.NONE,  # 新增：矿场查看关联客户；Client只看自己的档案
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CRM_TRANSACTION: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # Client/App只能查看自己交易与结算
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CRM_INVOICE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 平台开具，客户可下载自己发票
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CRM_BROKER_COMMISSION: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # 可选：矿场只读佣金信息
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CRM_ACTIVITY_LOG: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,
        Role.CLIENT: AccessLevel.NONE,  # 营销/客户经营相关记录
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== 分析工具 ====================
    Module.ANALYTICS_BATCH_CALC: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,  # 企业功能：Client/App导入自己列表批算
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.ANALYTICS_NETWORK: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 新增：Client看到市场级数据但不可改
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.ANALYTICS_TECHNICAL: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 可视化K线/指标，Guest看Demo
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.READ,
    },
    Module.ANALYTICS_DERIBIT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 需对衍生品分析，可做高级付费层
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== 智能层 (AI Layer) ====================
    Module.AI_BTC_PREDICT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # Client看自己的预测，Guest看公开预测
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.READ,
    },
    Module.AI_ROI_EXPLAIN: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 基于各自机器/投资组合做解释，Guest看Demo
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.READ,
    },
    Module.AI_ANOMALY_DETECT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # Client看到自己矿机异常
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.AI_POWER_OPTIMIZE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # Client获得针对自己机队的建议
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== 用户管理 ====================
    Module.USER_CREATE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.NONE,  # Owner/Admin全局；矿场仅建本场运维账号
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_EDIT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.NONE,  # 同上（可放宽严格：矿场只能停用）
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_DELETE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.READ,  # 同上
        Role.MINING_SITE_OWNER: AccessLevel.NONE,
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_ROLE_ASSIGN: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.NONE,  # 矿场仅能在限定角色集合内分配
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_LIST_VIEW: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # Client/App仅看到自己公司内部账号（如果支持多账号）
        Role.CLIENT: AccessLevel.READ,
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== 系统监控 ====================
    Module.SYSTEM_HEALTH: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.NONE,  # 运维功能，矿场仅做只读观察
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.SYSTEM_PERFORMANCE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.NONE,  # 同上
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.SYSTEM_EVENT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # 同上
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== Web3功能 ====================
    Module.WEB3_BLOCKCHAIN_VERIFY: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # 链上校验：Client/App仅验证自己的记录
        Role.CLIENT: AccessLevel.READ,
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.WEB3_TRANSPARENCY: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # 可做公开透明版本视图
        Role.CLIENT: AccessLevel.READ,
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.WEB3_SLA_NFT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # 客户领取/查看自己的SLA NFT
        Role.CLIENT: AccessLevel.READ,
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== 财务管理 ====================
    Module.FINANCE_BILLING: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 财务功能：客户只看自己的账单
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.FINANCE_BTC_SETTLE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 支付/提现入口，需KYC
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.FINANCE_CRYPTO_PAY: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,  # 支付功能，可支持多种加密货币
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== 报表系统 ====================
    Module.REPORT_PDF: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,  # Client可生成自己的报表，Guest下载Demo
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.READ,
    },
    Module.REPORT_EXCEL: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,  # 详细数据导出，仅登录用户
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.REPORT_PPT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,  # 给老板投资人用的展示型报表
        Role.CUSTOMER: AccessLevel.FULL,
        Role.GUEST: AccessLevel.NONE,
    },
}


@dataclass
class RoleDefinition:
    """角色定义"""
    name: Role
    display_name_en: str
    display_name_zh: str
    description_en: str
    description_zh: str
    priority: int  # 优先级，数字越小权限越高


ROLE_DEFINITIONS: Dict[Role, RoleDefinition] = {
    Role.OWNER: RoleDefinition(
        name=Role.OWNER,
        display_name_en="Owner",
        display_name_zh="所有者",
        description_en="Highest authority, manages all system configurations and users",
        description_zh="最高权限，管理所有系统配置和用户",
        priority=1
    ),
    Role.ADMIN: RoleDefinition(
        name=Role.ADMIN,
        display_name_en="Admin",
        display_name_zh="管理员",
        description_en="System administrator, manages users and configurations",
        description_zh="系统管理员，管理用户和配置",
        priority=2
    ),
    Role.MINING_SITE_OWNER: RoleDefinition(
        name=Role.MINING_SITE_OWNER,
        display_name_en="Mining Site Owner",
        display_name_zh="矿场站点负责人",
        description_en="Mining farm operator, manages site operations and miners",
        description_zh="矿场运营者，管理站点运营和矿机",
        priority=3
    ),
    Role.CLIENT: RoleDefinition(
        name=Role.CLIENT,
        display_name_en="Client",
        display_name_zh="矿场客户端",
        description_en="Mining site client, views own miners and operations",
        description_zh="矿场客户端，查看自己的矿机和运营",
        priority=4
    ),
    Role.CUSTOMER: RoleDefinition(
        name=Role.CUSTOMER,
        display_name_en="Customer",
        display_name_zh="应用客户",
        description_en="App customer, uses calculator and basic features",
        description_zh="应用客户，使用计算器和基础功能",
        priority=5
    ),
    Role.GUEST: RoleDefinition(
        name=Role.GUEST,
        display_name_en="Guest",
        display_name_zh="访客",
        description_en="Unauthenticated visitor, limited public access",
        description_zh="未登录访客，仅限公开访问",
        priority=6
    ),
}


class RBACManager:
    """RBAC管理器 v2.0"""
    
    def __init__(self):
        self.permission_matrix = PERMISSION_MATRIX
        self.role_definitions = ROLE_DEFINITIONS
    
    def get_access_level(
        self,
        role: Role,
        module: Module
    ) -> AccessLevel:
        """获取角色对模块的访问级别"""
        if module not in self.permission_matrix:
            logger.warning(f"未知模块: {module}")
            return AccessLevel.NONE
        
        module_permissions = self.permission_matrix[module]
        return module_permissions.get(role, AccessLevel.NONE)
    
    def has_access(
        self,
        role: Role,
        module: Module,
        require_full: bool = False
    ) -> bool:
        """检查角色是否有访问权限
        
        Args:
            role: 用户角色
            module: 目标模块
            require_full: True=需要完全访问权限, False=只读也可以
        """
        access_level = self.get_access_level(role, module)
        
        if require_full:
            return access_level == AccessLevel.FULL
        
        return access_level in [AccessLevel.FULL, AccessLevel.READ]
    
    def has_full_access(self, role: Role, module: Module) -> bool:
        """检查是否有完全访问权限"""
        return self.get_access_level(role, module) == AccessLevel.FULL
    
    def has_read_access(self, role: Role, module: Module) -> bool:
        """检查是否有只读访问权限"""
        return self.get_access_level(role, module) in [AccessLevel.FULL, AccessLevel.READ]
    
    def get_role_permissions(self, role: Role) -> Dict[Module, AccessLevel]:
        """获取角色的所有权限"""
        permissions = {}
        for module in Module:
            permissions[module] = self.get_access_level(role, module)
        return permissions
    
    def get_module_access_matrix(self, module: Module) -> Dict[Role, AccessLevel]:
        """获取模块的角色访问矩阵"""
        return self.permission_matrix.get(module, {})
    
    def get_accessible_modules(
        self,
        role: Role,
        require_full: bool = False
    ) -> List[Module]:
        """获取角色可访问的所有模块"""
        accessible = []
        for module in Module:
            if self.has_access(role, module, require_full):
                accessible.append(module)
        return accessible
    
    def can_access_resource(
        self,
        user_role: Role,
        user_id: Optional[int],
        resource_owner_id: Optional[int],
        module: Module,
        require_full: bool = False
    ) -> Tuple[bool, str]:
        """检查用户是否可以访问特定资源（结合RLS）
        
        Returns:
            (是否有权限, 原因说明)
        """
        # 1. 检查模块权限
        access_level = self.get_access_level(user_role, module)
        
        if access_level == AccessLevel.NONE:
            return False, "no_module_access"
        
        if require_full and access_level != AccessLevel.FULL:
            return False, "read_only_access"
        
        # 2. Owner/Admin有全局访问权限
        if user_role in [Role.OWNER, Role.ADMIN]:
            return True, "admin_access"
        
        # 3. 其他角色需要检查资源所有权（RLS）
        if user_id and resource_owner_id:
            if user_id != resource_owner_id:
                # Mining Site Owner可以查看其站点的资源
                if user_role == Role.MINING_SITE_OWNER:
                    return True, "site_owner_access"
                return False, "not_resource_owner"
        
        return True, "access_granted"
    
    def export_matrix_json(self) -> Dict[str, Any]:
        """导出权限矩阵为JSON格式（用于前端）"""
        matrix = {}
        for module in Module:
            module_key = module.value
            matrix[module_key] = {}
            for role in [Role.OWNER, Role.ADMIN, Role.MINING_SITE_OWNER, 
                        Role.CLIENT, Role.CUSTOMER, Role.GUEST]:
                access = self.get_access_level(role, module)
                matrix[module_key][role.value] = access.value
        return matrix
    
    def export_role_summary(self, lang: str = 'zh') -> List[Dict[str, Any]]:
        """导出角色摘要（用于管理界面）"""
        summary = []
        for role in [Role.OWNER, Role.ADMIN, Role.MINING_SITE_OWNER, 
                    Role.CLIENT, Role.CUSTOMER, Role.GUEST]:
            definition = self.role_definitions.get(role)
            if definition:
                full_count = len([m for m in Module if self.has_full_access(role, m)])
                read_count = len([m for m in Module if 
                                 self.get_access_level(role, m) == AccessLevel.READ])
                
                summary.append({
                    'role': role.value,
                    'display_name': definition.display_name_zh if lang == 'zh' else definition.display_name_en,
                    'description': definition.description_zh if lang == 'zh' else definition.description_en,
                    'priority': definition.priority,
                    'full_access_count': full_count,
                    'read_access_count': read_count,
                    'total_access_count': full_count + read_count
                })
        return summary


# 全局RBAC管理器实例
rbac_manager = RBACManager()


# ==================== 装饰器 ====================

def requires_module_access(
    module: Module,
    require_full: bool = False,
    custom_error_message: Optional[str] = None
):
    """模块访问权限检查装饰器
    
    Args:
        module: 目标模块
        require_full: True=需要完全访问权限（写操作），False=只读也可以
        custom_error_message: 自定义错误消息
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取用户角色
            user_role_str = session.get('role', 'guest')
            user_role = normalize_role(user_role_str)
            
            # 检查权限
            if not rbac_manager.has_access(user_role, module, require_full):
                access_level = rbac_manager.get_access_level(user_role, module)
                
                error_msg = custom_error_message
                if not error_msg:
                    if access_level == AccessLevel.NONE:
                        error_msg = f"您没有访问 {module.value} 的权限"
                    else:
                        error_msg = f"您只有只读权限，无法执行此操作"
                
                logger.warning(
                    f"Permission denied: role={user_role.value}, module={module.value}, "
                    f"require_full={require_full}, actual_level={access_level.value}"
                )
                
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'error_code': 'PERMISSION_DENIED',
                    'required_access': 'full' if require_full else 'read',
                    'actual_access': access_level.value
                }), 403
            
            # 将访问级别传递给视图函数
            g.access_level = rbac_manager.get_access_level(user_role, module)
            g.user_role = user_role
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def requires_any_module_access(
    modules: List[Module],
    require_full: bool = False
):
    """检查是否有任意一个模块的访问权限"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role_str = session.get('role', 'guest')
            user_role = normalize_role(user_role_str)
            
            for module in modules:
                if rbac_manager.has_access(user_role, module, require_full):
                    g.access_level = rbac_manager.get_access_level(user_role, module)
                    g.user_role = user_role
                    g.accessed_module = module
                    return f(*args, **kwargs)
            
            logger.warning(
                f"Permission denied: role={user_role.value}, "
                f"modules={[m.value for m in modules]}, require_full={require_full}"
            )
            
            return jsonify({
                'success': False,
                'error': '您没有访问此功能的权限',
                'error_code': 'PERMISSION_DENIED'
            }), 403
        return decorated_function
    return decorator


def requires_role(allowed_roles: List[Role]):
    """角色检查装饰器（兼容旧版本）"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role_str = session.get('role', 'guest')
            user_role = normalize_role(user_role_str)
            
            # Owner总是有权限
            if user_role == Role.OWNER:
                g.user_role = user_role
                return f(*args, **kwargs)
            
            if user_role not in allowed_roles:
                logger.warning(
                    f"Role denied: {user_role.value} not in {[r.value for r in allowed_roles]}"
                )
                return jsonify({
                    'success': False,
                    'error': '您没有访问此功能的权限',
                    'error_code': 'ROLE_DENIED',
                    'required_roles': [r.value for r in allowed_roles]
                }), 403
            
            g.user_role = user_role
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_user_permissions() -> Dict[str, Any]:
    """获取当前用户的权限信息（用于前端）"""
    user_role_str = session.get('role', 'guest')
    user_role = normalize_role(user_role_str)
    
    permissions = {}
    for module in Module:
        access = rbac_manager.get_access_level(user_role, module)
        permissions[module.value] = {
            'level': access.value,
            'can_read': access in [AccessLevel.FULL, AccessLevel.READ],
            'can_write': access == AccessLevel.FULL
        }
    
    role_def = ROLE_DEFINITIONS.get(user_role)
    
    return {
        'role': user_role.value,
        'role_display_name': role_def.display_name_zh if role_def else user_role.value,
        'role_description': role_def.description_zh if role_def else '',
        'permissions': permissions
    }


# 导出
__all__ = [
    'AccessLevel',
    'Role',
    'Module',
    'PERMISSION_MATRIX',
    'ROLE_DEFINITIONS',
    'RoleDefinition',
    'RBACManager',
    'rbac_manager',
    'normalize_role',
    'requires_module_access',
    'requires_any_module_access',
    'requires_role',
    'get_user_permissions'
]
