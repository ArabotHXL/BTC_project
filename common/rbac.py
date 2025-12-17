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
    # 新版6角色体系
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
    
    # 旧版功能角色（向后兼容）
    DEVELOPER = "developer"                 # 开发者
    API_CLIENT = "api_client"               # API客户端
    INVESTOR = "investor"                   # 投资人
    OPERATOR = "operator"                   # 运维人员
    FINANCE = "finance"                     # 财务人员
    TRADER = "trader"                       # 交易员
    READONLY = "readonly"                   # 只读用户


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
    # 旧功能角色映射
    'developer': Role.ADMIN,      # 开发者 -> 管理员权限
    'api_client': Role.CLIENT,    # API客户端 -> 客户端权限
    'investor': Role.CLIENT,      # 投资人 -> 客户端权限
    'operator': Role.MINING_SITE_OWNER,  # 运维人员 -> 矿场站点负责人
    'finance': Role.ADMIN,        # 财务人员 -> 管理员权限
    'trader': Role.CLIENT,        # 交易员 -> 客户端权限
    'readonly': Role.CUSTOMER,    # 只读用户 -> 应用客户
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
    USER_DISABLE = "user:disable"                   # 禁用/停用用户
    USER_DELETE = "user:delete"                     # 永久删除用户
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
    
    # 远程控制 (Remote Control)
    REMOTE_CONTROL_REQUEST = "remote:request"       # 远程控制请求（提交/批准窗口）
    REMOTE_CONTROL_AUDIT = "remote:audit"           # 远控审计与执行结果查看
    REMOTE_CONTROL_EXECUTE = "remote:execute"       # 远控执行（重启/功率/矿池/频率/温控/LED）


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
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 矿场负责人可管理自己站点
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
        Role.CUSTOMER: AccessLevel.READ,  # Customer可查看自己矿机状态
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
        Role.CUSTOMER: AccessLevel.READ,  # Customer可查看自己使用记录
        Role.GUEST: AccessLevel.NONE,
    },
    Module.HOSTING_RECONCILIATION: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # 财务对账: 平台 vs 矿场 vs 客户
        Role.CUSTOMER: AccessLevel.READ,  # Customer可查看自己对账信息
        Role.GUEST: AccessLevel.NONE,
    },
    
    # ==================== 智能限电 ====================
    Module.CURTAILMENT_STRATEGY: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 矿场负责人可完全管理限电策略
        Role.CLIENT: AccessLevel.READ,  # Client只读
        Role.CUSTOMER: AccessLevel.READ,  # Customer可查看限电策略
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CURTAILMENT_AI_PREDICT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 矿场负责人可使用AI预测
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
        Role.CUSTOMER: AccessLevel.READ,  # Customer可查看限电历史
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
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 矿场负责人可管理佣金
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.CRM_ACTIVITY_LOG: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 矿场负责人可管理活动记录
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
        Role.CLIENT: AccessLevel.READ,  # Client看到市场级数据但不可改
        Role.CUSTOMER: AccessLevel.READ,  # Customer可查看网络分析
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
        Role.MINING_SITE_OWNER: AccessLevel.NONE,  # Owner/Admin全局创建用户
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_EDIT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.NONE,
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_DISABLE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,  # Owner/Admin可禁用/停用用户
        Role.MINING_SITE_OWNER: AccessLevel.NONE,
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_DELETE: {
        Role.OWNER: AccessLevel.FULL,  # 只有Owner可永久删除用户
        Role.ADMIN: AccessLevel.NONE,
        Role.MINING_SITE_OWNER: AccessLevel.NONE,
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_ROLE_ASSIGN: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.NONE,
        Role.CLIENT: AccessLevel.NONE,
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.USER_LIST_VIEW: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.READ,  # Client/App仅看到自己公司内部账号
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
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 矿场负责人可管理区块链验证
        Role.CLIENT: AccessLevel.READ,  # Client/App仅验证自己的记录
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.WEB3_TRANSPARENCY: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 矿场负责人可管理透明版本
        Role.CLIENT: AccessLevel.READ,
        Role.CUSTOMER: AccessLevel.READ,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.WEB3_SLA_NFT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 矿场负责人可管理SLA NFT
        Role.CLIENT: AccessLevel.READ,  # 客户领取/查看自己的SLA NFT
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
    
    # ==================== 远程控制 ====================
    Module.REMOTE_CONTROL_REQUEST: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.FULL,  # Client可提交远程控制请求
        Role.CUSTOMER: AccessLevel.NONE,
        Role.GUEST: AccessLevel.NONE,
    },
    Module.REMOTE_CONTROL_AUDIT: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,
        Role.CLIENT: AccessLevel.READ,  # Client可查看审计与执行结果
        Role.CUSTOMER: AccessLevel.READ,  # Customer可查看审计记录
        Role.GUEST: AccessLevel.NONE,
    },
    Module.REMOTE_CONTROL_EXECUTE: {
        Role.OWNER: AccessLevel.FULL,
        Role.ADMIN: AccessLevel.FULL,
        Role.MINING_SITE_OWNER: AccessLevel.FULL,  # 只有运维方可执行远程控制
        Role.CLIENT: AccessLevel.NONE,  # Client不能直接执行
        Role.CUSTOMER: AccessLevel.NONE,
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
    
    # ==================== 向后兼容方法 ====================
    
    def has_permission(
        self,
        user_role: Role,
        required_permission: 'Permission',
        tenant_id: Optional[str] = None
    ) -> bool:
        """检查用户是否有指定权限 - 向后兼容旧代码"""
        # 使用 normalize_role 确保兼容性
        if isinstance(user_role, str):
            user_role = normalize_role(user_role)
        
        # Owner总是有权限
        if user_role == Role.OWNER:
            return True
        
        # 将旧Permission转换为新Module检查
        from common.rbac import PERMISSION_TO_MODULE_MAP
        module = PERMISSION_TO_MODULE_MAP.get(required_permission)
        if module:
            need_full = 'write' in required_permission.value or 'delete' in required_permission.value
            return self.has_access(user_role, module, require_full=need_full)
        
        # 未映射的权限，允许Admin访问
        return user_role in [Role.OWNER, Role.ADMIN]
    
    def has_any_permission(
        self,
        user_role: Role,
        required_permissions: List['Permission']
    ) -> bool:
        """检查用户是否有任意一个权限 - 向后兼容旧代码"""
        return any(
            self.has_permission(user_role, perm)
            for perm in required_permissions
        )
    
    def has_all_permissions(
        self,
        user_role: Role,
        required_permissions: List['Permission']
    ) -> bool:
        """检查用户是否有所有权限 - 向后兼容旧代码"""
        return all(
            self.has_permission(user_role, perm)
            for perm in required_permissions
        )


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


# ==================== 向后兼容层 ====================
# 兼容旧代码使用的Permission枚举

class Permission(Enum):
    """权限枚举 - 向后兼容旧代码"""
    
    # 基础功能
    CALC_READ = "calculator:read"
    CALC_WRITE = "calculator:write"
    CALC_DELETE = "calculator:delete"
    CALC_EXPORT = "calculator:export"
    CALC_BATCH = "calculator:batch"
    
    # 分析
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_ADVANCED = "analytics:advanced"
    ANALYTICS_EXPORT = "analytics:export"
    
    # 用户管理
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    # 租户
    TENANT_READ = "tenant:read"
    TENANT_WRITE = "tenant:write"
    TENANT_ADMIN = "tenant:admin"
    
    # API密钥
    API_KEY_READ = "api_key:read"
    API_KEY_CREATE = "api_key:create"
    API_KEY_REVOKE = "api_key:revoke"
    
    # 区块链
    BLOCKCHAIN_READ = "blockchain:read"
    BLOCKCHAIN_WRITE = "blockchain:write"
    
    # 报表
    REPORT_READ = "report:read"
    REPORT_CREATE = "report:create"
    REPORT_EXPORT = "report:export"
    
    # 系统
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_AUDIT = "system:audit"
    
    # 计费
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    
    # Webhook
    WEBHOOK_READ = "webhook:read"
    WEBHOOK_WRITE = "webhook:write"
    
    # 矿机
    MINERS_READ = "miners:read"
    MINERS_WRITE = "miners:write"
    MINERS_DELETE = "miners:delete"
    
    # 智能层
    INTEL_READ = "intel:read"
    INTEL_FORECAST = "intel:forecast"
    INTEL_OPTIMIZE = "intel:optimize"
    INTEL_EXPLAIN = "intel:explain"
    
    # 运营
    OPS_PLAN = "ops:plan"
    OPS_APPLY = "ops:apply"
    OPS_READ = "ops:read"
    
    # 财资
    TREASURY_READ = "treasury:read"
    TREASURY_TRADE = "treasury:trade"
    TREASURY_EXECUTE = "treasury:execute"
    
    # Web3
    WEB3_MINT = "web3:mint"
    WEB3_VERIFY = "web3:verify"
    WEB3_READ = "web3:read"
    
    # CRM
    CRM_READ = "crm:read"
    CRM_SYNC = "crm:sync"
    CRM_WEBHOOK = "crm:webhook"
    CRM_ADMIN = "crm:admin"
    
    # 托管
    HOSTING_READ = "hosting:read"
    HOSTING_WRITE = "hosting:write"
    HOSTING_DELETE = "hosting:delete"
    HOSTING_ADMIN = "hosting:admin"
    
    # 限电
    CURTAILMENT_READ = "curtailment:read"
    CURTAILMENT_WRITE = "curtailment:write"
    CURTAILMENT_EXECUTE = "curtailment:execute"
    
    WILDCARD = "*"  # 所有权限


# 旧Permission到新Module的映射
PERMISSION_TO_MODULE_MAP = {
    Permission.CALC_READ: Module.BASIC_CALCULATOR,
    Permission.CALC_WRITE: Module.BASIC_CALCULATOR,
    Permission.CALC_BATCH: Module.ANALYTICS_BATCH_CALC,
    Permission.ANALYTICS_READ: Module.ANALYTICS_NETWORK,
    Permission.ANALYTICS_ADVANCED: Module.ANALYTICS_DERIBIT,
    Permission.USER_READ: Module.USER_LIST_VIEW,
    Permission.USER_WRITE: Module.USER_EDIT,
    Permission.USER_DELETE: Module.USER_DELETE,
    Permission.USER_ADMIN: Module.USER_ROLE_ASSIGN,
    Permission.SYSTEM_CONFIG: Module.SYSTEM_HEALTH,
    Permission.SYSTEM_ADMIN: Module.SYSTEM_HEALTH,
    Permission.SYSTEM_AUDIT: Module.SYSTEM_EVENT,
    Permission.BILLING_READ: Module.FINANCE_BILLING,
    Permission.BILLING_WRITE: Module.FINANCE_BILLING,
    Permission.MINERS_READ: Module.HOSTING_STATUS_MONITOR,
    Permission.MINERS_WRITE: Module.HOSTING_BATCH_CREATE,
    Permission.MINERS_DELETE: Module.HOSTING_BATCH_CREATE,
    Permission.INTEL_READ: Module.AI_BTC_PREDICT,
    Permission.INTEL_FORECAST: Module.AI_BTC_PREDICT,
    Permission.INTEL_OPTIMIZE: Module.AI_POWER_OPTIMIZE,
    Permission.INTEL_EXPLAIN: Module.AI_ROI_EXPLAIN,
    Permission.OPS_READ: Module.CURTAILMENT_HISTORY,
    Permission.OPS_PLAN: Module.CURTAILMENT_STRATEGY,
    Permission.OPS_APPLY: Module.CURTAILMENT_EXECUTE,
    Permission.TREASURY_READ: Module.FINANCE_BILLING,
    Permission.TREASURY_TRADE: Module.FINANCE_BTC_SETTLE,
    Permission.TREASURY_EXECUTE: Module.FINANCE_BTC_SETTLE,
    Permission.WEB3_READ: Module.WEB3_BLOCKCHAIN_VERIFY,
    Permission.WEB3_VERIFY: Module.WEB3_TRANSPARENCY,
    Permission.WEB3_MINT: Module.WEB3_SLA_NFT,
    Permission.CRM_READ: Module.CRM_CUSTOMER_VIEW,
    Permission.CRM_SYNC: Module.CRM_CUSTOMER_MGMT,
    Permission.CRM_WEBHOOK: Module.CRM_ACTIVITY_LOG,
    Permission.CRM_ADMIN: Module.CRM_CUSTOMER_MGMT,
    Permission.REPORT_READ: Module.REPORT_PDF,
    Permission.REPORT_CREATE: Module.REPORT_PDF,
    Permission.REPORT_EXPORT: Module.REPORT_EXCEL,
    Permission.BLOCKCHAIN_READ: Module.WEB3_BLOCKCHAIN_VERIFY,
    Permission.BLOCKCHAIN_WRITE: Module.WEB3_BLOCKCHAIN_VERIFY,
    Permission.HOSTING_READ: Module.HOSTING_STATUS_MONITOR,
    Permission.HOSTING_WRITE: Module.HOSTING_BATCH_CREATE,
    Permission.HOSTING_DELETE: Module.HOSTING_BATCH_CREATE,
    Permission.HOSTING_ADMIN: Module.HOSTING_SITE_MGMT,
    Permission.CURTAILMENT_READ: Module.CURTAILMENT_HISTORY,
    Permission.CURTAILMENT_WRITE: Module.CURTAILMENT_STRATEGY,
    Permission.CURTAILMENT_EXECUTE: Module.CURTAILMENT_EXECUTE,
}


def require_permission(
    required_permissions: List[Permission],
    require_all: bool = False,
    resource_tenant_field: Optional[str] = None
):
    """
    权限检查装饰器 - 向后兼容旧代码
    
    Args:
        required_permissions: 需要的权限列表
        require_all: True=需要所有权限, False=需要任意一个权限
        resource_tenant_field: 如果指定，会检查资源的租户ID
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role_str = session.get('role', 'guest')
            user_role = normalize_role(user_role_str)
            
            # Owner总是有权限
            if user_role == Role.OWNER:
                g.user_role = user_role
                return f(*args, **kwargs)
            
            # 将旧Permission转换为新Module检查
            has_access = False
            for perm in required_permissions:
                module = PERMISSION_TO_MODULE_MAP.get(perm)
                if module:
                    # 写操作需要FULL权限
                    need_full = 'write' in perm.value or 'delete' in perm.value or 'admin' in perm.value
                    if rbac_manager.has_access(user_role, module, require_full=need_full):
                        has_access = True
                        if not require_all:
                            break
                    elif require_all:
                        has_access = False
                        break
                else:
                    # 未映射的权限，允许Owner/Admin访问
                    if user_role in [Role.OWNER, Role.ADMIN]:
                        has_access = True
            
            if not has_access:
                logger.warning(
                    f"Permission denied for role={user_role.value}: "
                    f"required {[p.value for p in required_permissions]}"
                )
                return jsonify({
                    'success': False,
                    'error': 'Insufficient permissions',
                    'required_permissions': [p.value for p in required_permissions]
                }), 403
            
            g.user_role = user_role
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# 导出
__all__ = [
    'AccessLevel',
    'Role',
    'Module',
    'Permission',  # 向后兼容
    'PERMISSION_MATRIX',
    'ROLE_DEFINITIONS',
    'RoleDefinition',
    'RBACManager',
    'rbac_manager',
    'normalize_role',
    'requires_module_access',
    'requires_any_module_access',
    'requires_role',
    'require_permission',  # 向后兼容
    'get_user_permissions',
    'PERMISSION_TO_MODULE_MAP'
]
