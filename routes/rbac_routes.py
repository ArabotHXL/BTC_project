"""
RBAC权限管理API路由
Permission Management API Routes

提供权限矩阵查询、角色管理和权限检查功能。
"""

import logging
from flask import Blueprint, jsonify, session, request, g
from auth import login_required
from common.rbac import (
    Role, Module, AccessLevel, PERMISSION_MATRIX, ROLE_DEFINITIONS,
    rbac_manager, normalize_role, get_user_permissions,
    requires_module_access, requires_role
)

logger = logging.getLogger(__name__)

rbac_bp = Blueprint('rbac', __name__, url_prefix='/api/rbac')


@rbac_bp.route('/my-permissions', methods=['GET'])
@login_required
def get_my_permissions():
    """获取当前用户的权限信息
    
    Returns:
        当前用户的角色和所有模块权限
    """
    try:
        permissions = get_user_permissions()
        return jsonify({
            'success': True,
            'data': permissions
        })
    except Exception as e:
        logger.error(f"获取用户权限失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rbac_bp.route('/matrix', methods=['GET'])
@login_required
def get_permission_matrix():
    """获取完整权限矩阵
    
    只有Owner和Admin可以查看完整矩阵
    """
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        
        # 只有管理员可以查看完整矩阵
        if user_role not in [Role.OWNER, Role.ADMIN]:
            return jsonify({
                'success': False,
                'error': '您没有权限查看权限矩阵',
                'error_code': 'ACCESS_DENIED'
            }), 403
        
        matrix = rbac_manager.export_matrix_json()
        
        return jsonify({
            'success': True,
            'data': {
                'matrix': matrix,
                'roles': [
                    {'value': r.value, 'label_zh': ROLE_DEFINITIONS[r].display_name_zh if r in ROLE_DEFINITIONS else r.value,
                     'label_en': ROLE_DEFINITIONS[r].display_name_en if r in ROLE_DEFINITIONS else r.value}
                    for r in [Role.OWNER, Role.ADMIN, Role.MINING_SITE_OWNER, Role.OPERATOR, Role.CLIENT, Role.GUEST]
                ],
                'access_levels': [
                    {'value': 'full', 'label_zh': '完全访问', 'label_en': 'Full Access', 'icon': '✓', 'color': 'success'},
                    {'value': 'read', 'label_zh': '只读', 'label_en': 'Read Only', 'icon': '●', 'color': 'info'},
                    {'value': 'none', 'label_zh': '无权限', 'label_en': 'No Access', 'icon': '✗', 'color': 'danger'}
                ]
            }
        })
    except Exception as e:
        logger.error(f"获取权限矩阵失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rbac_bp.route('/roles', methods=['GET'])
@login_required
def get_roles():
    """获取所有角色定义
    
    Returns:
        角色列表和权限统计
    """
    try:
        lang = request.args.get('lang', 'zh')
        summary = rbac_manager.export_role_summary(lang)
        
        return jsonify({
            'success': True,
            'data': {
                'roles': summary,
                'total': len(summary)
            }
        })
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rbac_bp.route('/modules', methods=['GET'])
@login_required
def get_modules():
    """获取所有模块定义
    
    Returns:
        模块列表按分类分组
    """
    try:
        lang = request.args.get('lang', 'zh')
        
        # 模块分组
        module_groups = {
            'basic': {'zh': '基础功能', 'en': 'Basic Functions', 'modules': []},
            'hosting': {'zh': '托管服务', 'en': 'Hosting Services', 'modules': []},
            'curtailment': {'zh': '智能限电', 'en': 'Smart Curtailment', 'modules': []},
            'crm': {'zh': 'CRM系统', 'en': 'CRM System', 'modules': []},
            'analytics': {'zh': '分析工具', 'en': 'Analytics', 'modules': []},
            'ai': {'zh': '智能层', 'en': 'AI Layer', 'modules': []},
            'user': {'zh': '用户管理', 'en': 'User Management', 'modules': []},
            'system': {'zh': '系统监控', 'en': 'System Monitoring', 'modules': []},
            'web3': {'zh': 'Web3功能', 'en': 'Web3 Features', 'modules': []},
            'finance': {'zh': '财务管理', 'en': 'Financial Management', 'modules': []},
            'report': {'zh': '报表系统', 'en': 'Reporting', 'modules': []}
        }
        
        # 模块名称映射
        module_labels = {
            # 基础功能
            Module.BASIC_CALCULATOR: {'zh': '挖矿计算器', 'en': 'Mining Calculator'},
            Module.BASIC_SETTINGS: {'zh': '个人设置', 'en': 'Personal Settings'},
            Module.BASIC_DASHBOARD: {'zh': '仪表盘首页', 'en': 'Dashboard'},
            # 托管服务
            Module.HOSTING_SITE_MGMT: {'zh': '矿场站点管理', 'en': 'Site Management'},
            Module.HOSTING_BATCH_CREATE: {'zh': '矿机批量创建', 'en': 'Batch Creation'},
            Module.HOSTING_STATUS_MONITOR: {'zh': '矿机状态监控', 'en': 'Status Monitoring'},
            Module.HOSTING_TICKET: {'zh': '工单系统', 'en': 'Ticket System'},
            Module.HOSTING_USAGE_TRACKING: {'zh': '使用记录管理', 'en': 'Usage Tracking'},
            Module.HOSTING_RECONCILIATION: {'zh': '对账功能', 'en': 'Reconciliation'},
            # 智能限电
            Module.CURTAILMENT_STRATEGY: {'zh': '限电策略计算', 'en': 'Curtailment Strategy'},
            Module.CURTAILMENT_AI_PREDICT: {'zh': 'AI 24小时预测', 'en': 'AI 24h Prediction'},
            Module.CURTAILMENT_EXECUTE: {'zh': '限电执行控制', 'en': 'Execution Control'},
            Module.CURTAILMENT_EMERGENCY: {'zh': '紧急恢复', 'en': 'Emergency Recovery'},
            Module.CURTAILMENT_HISTORY: {'zh': '限电历史查询', 'en': 'History Query'},
            # CRM
            Module.CRM_CUSTOMER_MGMT: {'zh': '客户管理', 'en': 'Customer Management'},
            Module.CRM_CUSTOMER_VIEW: {'zh': '客户信息查看', 'en': 'Customer View'},
            Module.CRM_TRANSACTION: {'zh': '交易/结算管理', 'en': 'Transaction Management'},
            Module.CRM_INVOICE: {'zh': '发票开具', 'en': 'Invoice'},
            Module.CRM_BROKER_COMMISSION: {'zh': '经纪人佣金', 'en': 'Broker Commission'},
            Module.CRM_ACTIVITY_LOG: {'zh': '活动记录', 'en': 'Activity Log'},
            # 分析工具
            Module.ANALYTICS_BATCH_CALC: {'zh': '批量计算器', 'en': 'Batch Calculator'},
            Module.ANALYTICS_NETWORK: {'zh': '网络分析', 'en': 'Network Analysis'},
            Module.ANALYTICS_TECHNICAL: {'zh': '技术指标分析', 'en': 'Technical Analysis'},
            Module.ANALYTICS_DERIBIT: {'zh': 'Deribit高级分析', 'en': 'Deribit Analysis'},
            # 智能层
            Module.AI_BTC_PREDICT: {'zh': 'AI价格/难度预测', 'en': 'AI BTC Prediction'},
            Module.AI_ROI_EXPLAIN: {'zh': 'ROI智能解释', 'en': 'ROI Explanation'},
            Module.AI_ANOMALY_DETECT: {'zh': '异常检测', 'en': 'Anomaly Detection'},
            Module.AI_POWER_OPTIMIZE: {'zh': '功耗优化建议', 'en': 'Power Optimization'},
            # 用户管理
            Module.USER_CREATE: {'zh': '创建用户', 'en': 'Create User'},
            Module.USER_EDIT: {'zh': '编辑用户', 'en': 'Edit User'},
            Module.USER_DELETE: {'zh': '删除用户', 'en': 'Delete User'},
            Module.USER_ROLE_ASSIGN: {'zh': '角色分配', 'en': 'Role Assignment'},
            Module.USER_LIST_VIEW: {'zh': '用户列表查看', 'en': 'User List View'},
            # 系统监控
            Module.SYSTEM_HEALTH: {'zh': '系统健康监控', 'en': 'Health Monitoring'},
            Module.SYSTEM_PERFORMANCE: {'zh': '性能监控', 'en': 'Performance Monitoring'},
            Module.SYSTEM_EVENT: {'zh': '事件监控', 'en': 'Event Monitoring'},
            # Web3
            Module.WEB3_BLOCKCHAIN_VERIFY: {'zh': '区块链验证', 'en': 'Blockchain Verification'},
            Module.WEB3_TRANSPARENCY: {'zh': '透明版本验证', 'en': 'Transparency Verification'},
            Module.WEB3_SLA_NFT: {'zh': 'SLA NFT管理', 'en': 'SLA NFT Management'},
            # 财务
            Module.FINANCE_BILLING: {'zh': '账单管理', 'en': 'Billing Management'},
            Module.FINANCE_BTC_SETTLE: {'zh': 'BTC结算/提现', 'en': 'BTC Settlement'},
            Module.FINANCE_CRYPTO_PAY: {'zh': '加密支付', 'en': 'Crypto Payment'},
            # 报表
            Module.REPORT_PDF: {'zh': 'PDF报表生成', 'en': 'PDF Reports'},
            Module.REPORT_EXCEL: {'zh': 'Excel导出', 'en': 'Excel Export'},
            Module.REPORT_PPT: {'zh': 'PowerPoint报表', 'en': 'PowerPoint Reports'}
        }
        
        for module in Module:
            prefix = module.value.split(':')[0]
            if prefix in module_groups:
                label = module_labels.get(module, {'zh': module.value, 'en': module.value})
                module_groups[prefix]['modules'].append({
                    'value': module.value,
                    'label': label[lang] if lang in label else label['en']
                })
        
        # 转换为列表格式
        groups = []
        for key, group in module_groups.items():
            if group['modules']:
                groups.append({
                    'key': key,
                    'label': group[lang] if lang in group else group['en'],
                    'modules': group['modules']
                })
        
        return jsonify({
            'success': True,
            'data': {
                'groups': groups,
                'total_modules': len(Module)
            }
        })
    except Exception as e:
        logger.error(f"获取模块列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rbac_bp.route('/check', methods=['POST'])
@login_required
def check_permission():
    """检查当前用户对指定模块的权限
    
    Request Body:
        module: 模块名称
        require_full: 是否需要完全访问权限
    
    Returns:
        权限检查结果
    """
    try:
        data = request.get_json() or {}
        module_str = data.get('module')
        require_full = data.get('require_full', False)
        
        if not module_str:
            return jsonify({
                'success': False,
                'error': '缺少module参数'
            }), 400
        
        # 查找模块
        target_module = None
        for m in Module:
            if m.value == module_str:
                target_module = m
                break
        
        if not target_module:
            return jsonify({
                'success': False,
                'error': f'未知模块: {module_str}'
            }), 400
        
        user_role = normalize_role(session.get('role', 'guest'))
        access_level = rbac_manager.get_access_level(user_role, target_module)
        has_access = rbac_manager.has_access(user_role, target_module, require_full)
        
        return jsonify({
            'success': True,
            'data': {
                'module': module_str,
                'role': user_role.value,
                'access_level': access_level.value,
                'has_access': has_access,
                'can_read': access_level in [AccessLevel.FULL, AccessLevel.READ],
                'can_write': access_level == AccessLevel.FULL
            }
        })
    except Exception as e:
        logger.error(f"权限检查失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rbac_bp.route('/role/<role_name>/permissions', methods=['GET'])
@login_required
@requires_role([Role.OWNER, Role.ADMIN])
def get_role_permissions(role_name):
    """获取指定角色的所有权限
    
    只有Owner和Admin可以查看其他角色的权限
    """
    try:
        target_role = normalize_role(role_name)
        lang = request.args.get('lang', 'zh')
        
        permissions = []
        for module in Module:
            access = rbac_manager.get_access_level(target_role, module)
            permissions.append({
                'module': module.value,
                'access_level': access.value,
                'can_read': access in [AccessLevel.FULL, AccessLevel.READ],
                'can_write': access == AccessLevel.FULL
            })
        
        role_def = ROLE_DEFINITIONS.get(target_role)
        
        return jsonify({
            'success': True,
            'data': {
                'role': target_role.value,
                'display_name': role_def.display_name_zh if role_def and lang == 'zh' else (role_def.display_name_en if role_def else target_role.value),
                'description': role_def.description_zh if role_def and lang == 'zh' else (role_def.description_en if role_def else ''),
                'permissions': permissions,
                'stats': {
                    'full_access': len([p for p in permissions if p['access_level'] == 'full']),
                    'read_only': len([p for p in permissions if p['access_level'] == 'read']),
                    'no_access': len([p for p in permissions if p['access_level'] == 'none'])
                }
            }
        })
    except Exception as e:
        logger.error(f"获取角色权限失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rbac_bp.route('/module/<path:module_name>/access', methods=['GET'])
@login_required
@requires_role([Role.OWNER, Role.ADMIN])
def get_module_access(module_name):
    """获取指定模块的所有角色访问权限
    
    只有Owner和Admin可以查看模块权限矩阵
    """
    try:
        # 查找模块
        target_module = None
        for m in Module:
            if m.value == module_name:
                target_module = m
                break
        
        if not target_module:
            return jsonify({
                'success': False,
                'error': f'未知模块: {module_name}'
            }), 404
        
        lang = request.args.get('lang', 'zh')
        
        access_list = []
        for role in [Role.OWNER, Role.ADMIN, Role.MINING_SITE_OWNER, Role.OPERATOR, Role.CLIENT, Role.GUEST]:
            access = rbac_manager.get_access_level(role, target_module)
            role_def = ROLE_DEFINITIONS.get(role)
            
            access_list.append({
                'role': role.value,
                'role_display': role_def.display_name_zh if role_def and lang == 'zh' else (role_def.display_name_en if role_def else role.value),
                'access_level': access.value,
                'can_read': access in [AccessLevel.FULL, AccessLevel.READ],
                'can_write': access == AccessLevel.FULL
            })
        
        return jsonify({
            'success': True,
            'data': {
                'module': module_name,
                'access_matrix': access_list
            }
        })
    except Exception as e:
        logger.error(f"获取模块访问权限失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# 注册蓝图的函数
def register_rbac_routes(app):
    """注册RBAC路由到应用"""
    app.register_blueprint(rbac_bp)
    logger.info("RBAC routes registered successfully")
