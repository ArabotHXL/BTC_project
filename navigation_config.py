"""
统一导航系统配置文件
实现基于角色的权限分级菜单系统

权限层级（从高到低）:
- owner: 系统拥有者，拥有所有权限
- admin: 管理员，拥有CRM、用户管理等权限
- mining_site: 矿场用户，拥有批量计算、网络分析、矿机管理权限
- user: 普通登录用户，拥有基础计算器、投资组合权限
- guest: 访客，仅可访问公开页面
"""

# 权限层级定义
ROLE_HIERARCHY = {
    'owner': 5,
    'admin': 4,
    'mining_site': 3,
    'user': 2,
    'guest': 1
}

# 导航菜单结构定义
NAVIGATION_MENU = [
    {
        'id': 'home',
        'name': {
            'zh': '首页',
            'en': 'Home'
        },
        'url': '/',
        'icon': 'bi-house-door',
        'min_role': 'guest',
        'order': 1
    },
    {
        'id': 'dashboard',
        'name': {
            'zh': '仪表盘',
            'en': 'Dashboard'
        },
        'url': '/dashboard',
        'icon': 'bi-speedometer2',
        'min_role': 'user',
        'order': 2
    },
    
    # ========== 挖矿运营中心 ==========
    {
        'id': 'mining_operations',
        'name': {
            'zh': '挖矿运营中心',
            'en': 'Mining Operations'
        },
        'url': '/operations/mining',
        'icon': 'bi-minecart',
        'min_role': 'mining_site',
        'order': 3,
        'children': [
            {
                'id': 'basic_calculator',
                'name': {
                    'zh': '基础计算器',
                    'en': 'Basic Calculator'
                },
                'url': '/operations/mining#calculator',
                'icon': 'bi-calculator',
                'min_role': 'mining_site'
            },
            {
                'id': 'batch_calculator',
                'name': {
                    'zh': '批量计算器',
                    'en': 'Batch Calculator'
                },
                'url': '/operations/mining#batch',
                'icon': 'bi-grid-3x3',
                'min_role': 'mining_site'
            },
            {
                'id': 'miner_list',
                'name': {
                    'zh': '矿机列表',
                    'en': 'Miner List'
                },
                'url': '/operations/mining#miners',
                'icon': 'bi-cpu',
                'min_role': 'mining_site'
            },
            {
                'id': 'batch_import',
                'name': {
                    'zh': '批量导入',
                    'en': 'Batch Import'
                },
                'url': '/operations/mining#import',
                'icon': 'bi-cloud-upload',
                'min_role': 'mining_site'
            },
            {
                'id': 'curtailment_calculator',
                'name': {
                    'zh': '限电策略计算器',
                    'en': 'Curtailment Calculator'
                },
                'url': '/curtailment-calculator',
                'icon': 'bi-lightning',
                'min_role': 'mining_site'
            },
            {
                'id': 'network_history',
                'name': {
                    'zh': '网络历史分析',
                    'en': 'Network History'
                },
                'url': '/network-history',
                'icon': 'bi-graph-up',
                'min_role': 'mining_site'
            }
        ]
    },
    
    # ========== 数据分析中心 ==========
    {
        'id': 'analytics_center',
        'name': {
            'zh': '数据分析中心',
            'en': 'Analytics Center'
        },
        'url': '/operations/analytics',
        'icon': 'bi-bar-chart-line',
        'min_role': 'mining_site',
        'order': 4,
        'children': [
            {
                'id': 'technical_analysis',
                'name': {
                    'zh': '技术指标分析',
                    'en': 'Technical Analysis'
                },
                'url': '/operations/analytics#technical',
                'icon': 'bi-graph-up-arrow',
                'min_role': 'mining_site'
            },
            {
                'id': 'market_analysis',
                'name': {
                    'zh': '市场数据分析',
                    'en': 'Market Data'
                },
                'url': '/operations/analytics#market',
                'icon': 'bi-currency-bitcoin',
                'min_role': 'mining_site'
            },
            {
                'id': 'network_history',
                'name': {
                    'zh': '网络历史数据',
                    'en': 'Network History'
                },
                'url': '/operations/analytics#network',
                'icon': 'bi-graph-up',
                'min_role': 'mining_site'
            },
            {
                'id': 'roi_heatmap',
                'name': {
                    'zh': 'ROI热力图',
                    'en': 'ROI Heatmap'
                },
                'url': '/operations/analytics#roi',
                'icon': 'bi-grid-fill',
                'min_role': 'mining_site'
            },
            {
                'id': 'algorithm_engine',
                'name': {
                    'zh': '高级算法引擎',
                    'en': 'Advanced Algorithm'
                },
                'url': '/algorithm-test',
                'icon': 'bi-cpu-fill',
                'min_role': 'mining_site'
            }
        ]
    },
    
    # ========== Treasury智能决策 ==========
    {
        'id': 'treasury_management',
        'name': {
            'zh': 'Treasury智能决策',
            'en': 'Treasury Management'
        },
        'icon': 'bi-bank',
        'min_role': 'user',
        'order': 5,
        'children': [
            {
                'id': 'treasury_overview',
                'name': {
                    'zh': 'Treasury概览',
                    'en': 'Treasury Overview'
                },
                'url': '/analytics#treasury',
                'icon': 'bi-wallet2',
                'min_role': 'user'
            },
            {
                'id': 'portfolio_management',
                'name': {
                    'zh': '投资组合管理',
                    'en': 'Portfolio Management'
                },
                'url': '/analytics#portfolio',
                'icon': 'bi-pie-chart',
                'min_role': 'user'
            },
            {
                'id': 'strategy_templates',
                'name': {
                    'zh': '策略模板',
                    'en': 'Strategy Templates'
                },
                'url': '/analytics#strategies',
                'icon': 'bi-clipboard-data',
                'min_role': 'user'
            },
            {
                'id': 'signal_aggregation',
                'name': {
                    'zh': '信号聚合',
                    'en': 'Signal Aggregation'
                },
                'url': '/analytics#signals',
                'icon': 'bi-broadcast',
                'min_role': 'mining_site'
            }
        ]
    },
    
    # ========== Web3中心 ==========
    {
        'id': 'web3_dashboard',
        'name': {
            'zh': 'Web3中心',
            'en': 'Web3 Center'
        },
        'url': '/operations/web3',
        'icon': 'bi-diagram-3',
        'min_role': 'mining_site',
        'order': 6,
        'children': [
            {
                'id': 'web3_overview',
                'name': {
                    'zh': 'Web3概览',
                    'en': 'Web3 Overview'
                },
                'url': '/operations/web3#overview',
                'icon': 'bi-grid-3x2',
                'min_role': 'mining_site'
            },
            {
                'id': 'blockchain_verification',
                'name': {
                    'zh': '区块链验证',
                    'en': 'Blockchain Verification'
                },
                'url': '/operations/web3#verification',
                'icon': 'bi-shield-check',
                'min_role': 'mining_site'
            },
            {
                'id': 'sla_nft_manager',
                'name': {
                    'zh': 'SLA NFT管理',
                    'en': 'SLA NFT Manager'
                },
                'url': '/operations/web3#sla',
                'icon': 'bi-award',
                'min_role': 'mining_site'
            },
            {
                'id': 'transparency_center',
                'name': {
                    'zh': '透明度验证中心',
                    'en': 'Transparency Center'
                },
                'url': '/operations/web3#transparency',
                'icon': 'bi-eye',
                'min_role': 'mining_site'
            },
            {
                'id': 'crypto_payment',
                'name': {
                    'zh': '加密支付管理',
                    'en': 'Crypto Payment'
                },
                'url': '/operations/web3#payment',
                'icon': 'bi-wallet',
                'min_role': 'admin'
            }
        ]
    },
    
    # ========== 客户管理中心 ==========
    {
        'id': 'crm_center',
        'name': {
            'zh': '客户管理中心',
            'en': 'CRM Center'
        },
        'icon': 'bi-people',
        'min_role': 'admin',
        'order': 7,
        'children': [
            {
                'id': 'crm_dashboard',
                'name': {
                    'zh': 'CRM仪表盘',
                    'en': 'CRM Dashboard'
                },
                'url': '/crm',
                'icon': 'bi-speedometer',
                'min_role': 'admin'
            },
            {
                'id': 'customer_management',
                'name': {
                    'zh': '客户管理',
                    'en': 'Customer Management'
                },
                'url': '/crm/customers',
                'icon': 'bi-person-lines-fill',
                'min_role': 'admin'
            },
            {
                'id': 'mine_customers',
                'name': {
                    'zh': '矿场客户',
                    'en': 'Mining Customers'
                },
                'url': '/mine/customers',
                'icon': 'bi-building',
                'min_role': 'admin'
            },
            {
                'id': 'user_access',
                'name': {
                    'zh': '用户权限管理',
                    'en': 'User Access'
                },
                'url': '/user-access',
                'icon': 'bi-key',
                'min_role': 'admin'
            },
            {
                'id': 'login_records',
                'name': {
                    'zh': '登录记录',
                    'en': 'Login Records'
                },
                'url': '/login-records',
                'icon': 'bi-clock-history',
                'min_role': 'admin'
            }
        ]
    },
    
    # ========== 系统管理（仅Owner） ==========
    {
        'id': 'system_management',
        'name': {
            'zh': '系统管理',
            'en': 'System Management'
        },
        'icon': 'bi-gear',
        'min_role': 'owner',
        'order': 8,
        'children': [
            {
                'id': 'system_config',
                'name': {
                    'zh': '系统配置',
                    'en': 'System Config'
                },
                'url': '/system-config',
                'icon': 'bi-sliders',
                'min_role': 'owner'
            },
            {
                'id': 'database_admin',
                'name': {
                    'zh': '数据库管理',
                    'en': 'Database Admin'
                },
                'url': '/database-admin',
                'icon': 'bi-database',
                'min_role': 'owner'
            },
            {
                'id': 'api_management',
                'name': {
                    'zh': 'API管理',
                    'en': 'API Management'
                },
                'url': '/api-management',
                'icon': 'bi-code-square',
                'min_role': 'owner'
            },
            {
                'id': 'security_center',
                'name': {
                    'zh': '安全中心',
                    'en': 'Security Center'
                },
                'url': '/security-center',
                'icon': 'bi-shield-lock',
                'min_role': 'owner'
            },
            {
                'id': 'backup_recovery',
                'name': {
                    'zh': '备份与恢复',
                    'en': 'Backup & Recovery'
                },
                'url': '/backup-recovery',
                'icon': 'bi-arrow-clockwise',
                'min_role': 'owner'
            },
            {
                'id': 'debug_info',
                'name': {
                    'zh': '调试信息',
                    'en': 'Debug Info'
                },
                'url': '/debug-info',
                'icon': 'bi-bug',
                'min_role': 'owner'
            }
        ]
    }
]

# 快捷操作菜单（右上角用户菜单）
USER_MENU_ITEMS = [
    {
        'id': 'dashboard',
        'name': {
            'zh': '我的仪表盘',
            'en': 'My Dashboard'
        },
        'url': '/dashboard',
        'icon': 'bi-speedometer2',
        'min_role': 'user'
    },
    {
        'id': 'profile',
        'name': {
            'zh': '个人设置',
            'en': 'Profile'
        },
        'url': '/profile',
        'icon': 'bi-person-circle',
        'min_role': 'user'
    },
    {
        'id': 'logout',
        'name': {
            'zh': '退出登录',
            'en': 'Logout'
        },
        'url': '/logout',
        'icon': 'bi-box-arrow-right',
        'min_role': 'user'
    }
]

# 公开页面（无需登录）
PUBLIC_PAGES = [
    {
        'id': 'login',
        'name': {
            'zh': '登录',
            'en': 'Login'
        },
        'url': '/login',
        'icon': 'bi-box-arrow-in-right'
    },
    {
        'id': 'home',
        'name': {
            'zh': '首页',
            'en': 'Home'
        },
        'url': '/',
        'icon': 'bi-house-door'
    }
]


def has_permission(user_role, required_role):
    """
    检查用户是否有访问权限
    
    Args:
        user_role: 用户当前角色
        required_role: 所需最低角色
    
    Returns:
        bool: True表示有权限，False表示无权限
    """
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 999)
    
    return user_level >= required_level


def filter_menu_items(menu_items, user_role):
    """
    根据用户角色过滤菜单项
    
    Args:
        menu_items: 菜单项列表
        user_role: 用户角色
    
    Returns:
        list: 过滤后的菜单项列表
    """
    filtered_items = []
    
    for item in menu_items:
        # 检查是否有访问权限
        if has_permission(user_role, item.get('min_role', 'owner')):
            # 复制菜单项
            filtered_item = item.copy()
            
            # 如果有子菜单，递归过滤
            if 'children' in item:
                filtered_children = filter_menu_items(item['children'], user_role)
                if filtered_children:  # 只有当有可见子菜单时才添加
                    filtered_item['children'] = filtered_children
                    filtered_items.append(filtered_item)
            else:
                filtered_items.append(filtered_item)
    
    return filtered_items


def get_user_navigation(role='guest', lang='zh'):
    """
    获取用户可见的导航菜单
    
    Args:
        role: 用户角色 (owner/admin/mining_site/user/guest)
        lang: 语言 (zh/en)
    
    Returns:
        list: 过滤后的导航菜单列表，包含翻译后的名称
    """
    # 过滤菜单项
    filtered_menu = filter_menu_items(NAVIGATION_MENU, role)
    
    # 应用语言翻译
    def translate_menu(menu_items):
        translated = []
        for item in menu_items:
            translated_item = item.copy()
            
            # 翻译名称
            if 'name' in item and isinstance(item['name'], dict):
                translated_item['name'] = item['name'].get(lang, item['name'].get('zh', ''))
            
            # 递归翻译子菜单
            if 'children' in item:
                translated_item['children'] = translate_menu(item['children'])
            
            translated.append(translated_item)
        
        return translated
    
    return translate_menu(filtered_menu)


def get_user_menu(role='guest', lang='zh'):
    """
    获取用户菜单（右上角下拉菜单）
    
    Args:
        role: 用户角色
        lang: 语言
    
    Returns:
        list: 用户菜单项
    """
    filtered_menu = filter_menu_items(USER_MENU_ITEMS, role)
    
    # 翻译菜单项
    translated_menu = []
    for item in filtered_menu:
        translated_item = item.copy()
        if 'name' in item and isinstance(item['name'], dict):
            translated_item['name'] = item['name'].get(lang, item['name'].get('zh', ''))
        translated_menu.append(translated_item)
    
    return translated_menu


def get_breadcrumb(current_url, role='guest', lang='zh'):
    """
    根据当前URL生成面包屑导航
    
    Args:
        current_url: 当前页面URL
        role: 用户角色
        lang: 语言
    
    Returns:
        list: 面包屑导航列表
    """
    breadcrumb = []
    
    def find_menu_item(menu_items, url, parent_chain=None):
        if parent_chain is None:
            parent_chain = []
        
        for item in menu_items:
            if item.get('url') == url:
                return parent_chain + [item]
            
            if 'children' in item:
                result = find_menu_item(item['children'], url, parent_chain + [item])
                if result:
                    return result
        
        return None
    
    # 查找菜单项
    menu_chain = find_menu_item(NAVIGATION_MENU, current_url)
    
    if menu_chain:
        for item in menu_chain:
            breadcrumb.append({
                'name': item['name'].get(lang, item['name'].get('zh', '')) if isinstance(item['name'], dict) else item['name'],
                'url': item.get('url', '#'),
                'icon': item.get('icon', '')
            })
    
    return breadcrumb


def get_role_permissions(role):
    """
    获取角色的权限描述
    
    Args:
        role: 用户角色
    
    Returns:
        dict: 权限描述
    """
    permissions = {
        'owner': {
            'zh': '系统拥有者 - 拥有所有权限',
            'en': 'Owner - Full Access',
            'features': [
                'all_features',
                'system_config',
                'database_admin',
                'api_management',
                'security_center',
                'backup_recovery'
            ]
        },
        'admin': {
            'zh': '管理员 - CRM、用户管理权限',
            'en': 'Admin - CRM & User Management',
            'features': [
                'crm',
                'user_management',
                'customer_management',
                'mining_operations',
                'analytics',
                'web3'
            ]
        },
        'mining_site': {
            'zh': '矿场用户 - 批量计算、网络分析、矿机管理',
            'en': 'Mining Site - Batch Calculator, Network Analysis, Miner Management',
            'features': [
                'batch_calculator',
                'network_analysis',
                'miner_management',
                'analytics',
                'web3',
                'basic_features'
            ]
        },
        'user': {
            'zh': '普通用户 - 基础计算器、投资组合',
            'en': 'User - Basic Calculator, Portfolio',
            'features': [
                'basic_calculator',
                'treasury_management',
                'portfolio',
                'dashboard'
            ]
        },
        'guest': {
            'zh': '访客 - 仅公开页面',
            'en': 'Guest - Public Pages Only',
            'features': [
                'home',
                'login'
            ]
        }
    }
    
    return permissions.get(role, permissions['guest'])


# 导出所有需要的函数和变量
__all__ = [
    'NAVIGATION_MENU',
    'USER_MENU_ITEMS',
    'PUBLIC_PAGES',
    'ROLE_HIERARCHY',
    'get_user_navigation',
    'get_user_menu',
    'get_breadcrumb',
    'has_permission',
    'filter_menu_items',
    'get_role_permissions'
]
