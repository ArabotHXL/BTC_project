"""
模块配置和注册
统一管理所有模块的配置和注册
"""
import logging
from flask import Flask
from importlib import import_module

logger = logging.getLogger(__name__)

# 定义所有可用的模块
AVAILABLE_MODULES = {
    'calculator': {
        'name': '挖矿计算器',
        'blueprint': 'modules.calculator',
        'url_prefix': '/calculator',
        'requires_auth': False,
        'enabled': False  # 已在app.py通过routes/calculator_routes.py注册，避免重复注册
    },
    'crm': {
        'name': 'CRM系统',
        'blueprint': 'modules.crm',
        'url_prefix': '/crm',
        'requires_auth': True,
        'enabled': False  # 已在app.py通过crm_routes.py注册
    },
    'batch': {
        'name': '批量计算器',
        'blueprint': 'modules.batch',
        'url_prefix': '/batch',
        'requires_auth': True,
        'enabled': False  # 模块不存在，功能已在app.py的batch_calculator_bp中实现
    },
    'analytics': {
        'name': '数据分析',
        'blueprint': 'modules.analytics',
        'url_prefix': '/analytics',
        'requires_auth': True,
        'enabled': False  # 模块缺少蓝图定义，功能已在app.py的analytics_bp中实现
    },
    'broker': {
        'name': '经纪人系统',
        'blueprint': 'modules.broker',
        'url_prefix': '/broker',
        'requires_auth': True,
        'enabled': False  # 模块不存在（已禁用mining broker功能）
    },
    'hosting': {
        'name': '托管服务',
        'blueprint': 'modules.hosting',
        'url_prefix': '/hosting',
        'requires_auth': True,
        'enabled': False  # 已在app.py中直接注册
    },
    'client': {
        'name': '客户服务',
        'blueprint': 'modules.client',
        'url_prefix': '/client',
        'requires_auth': True,
        'enabled': False  # 已在app.py中直接注册
    }
}

def register_modules(app: Flask):
    """
    注册所有启用的模块
    
    Args:
        app: Flask应用实例
    """
    registered_modules = []
    
    for module_key, module_config in AVAILABLE_MODULES.items():
        if not module_config['enabled']:
            logger.info(f"模块 {module_config['name']} 已禁用")
            continue
            
        try:
            # 动态导入模块
            module = import_module(module_config['blueprint'])
            
            # 获取蓝图对象
            # 约定：每个模块都有一个 {module_name}_bp 的蓝图对象
            blueprint_name = f"{module_key}_bp"
            if hasattr(module, blueprint_name):
                blueprint = getattr(module, blueprint_name)
                
                # 注册蓝图到Flask应用
                app.register_blueprint(
                    blueprint,
                    url_prefix=module_config['url_prefix']
                )
                
                registered_modules.append(module_config['name'])
                logger.info(f"✅ 模块 {module_config['name']} 注册成功 (前缀: {module_config['url_prefix']})")
            else:
                logger.warning(f"模块 {module_config['name']} 缺少蓝图对象: {blueprint_name}")
                
        except ImportError as e:
            logger.error(f"❌ 无法导入模块 {module_config['name']}: {e}")
        except Exception as e:
            logger.error(f"❌ 注册模块 {module_config['name']} 失败: {e}")
    
    logger.info(f"共注册 {len(registered_modules)} 个模块: {', '.join(registered_modules)}")
    return registered_modules

def get_module_info(module_key: str):
    """
    获取模块信息
    
    Args:
        module_key: 模块键名
        
    Returns:
        模块配置字典或None
    """
    return AVAILABLE_MODULES.get(module_key)

def is_module_enabled(module_key: str):
    """
    检查模块是否启用
    
    Args:
        module_key: 模块键名
        
    Returns:
        布尔值，表示模块是否启用
    """
    module = AVAILABLE_MODULES.get(module_key)
    return module and module.get('enabled', False)

def get_enabled_modules():
    """
    获取所有启用的模块列表
    
    Returns:
        启用的模块配置列表
    """
    return [
        (key, config) 
        for key, config in AVAILABLE_MODULES.items() 
        if config.get('enabled', False)
    ]

def toggle_module(module_key: str, enabled: bool):
    """
    动态启用或禁用模块
    
    Args:
        module_key: 模块键名
        enabled: 是否启用
    """
    if module_key in AVAILABLE_MODULES:
        AVAILABLE_MODULES[module_key]['enabled'] = enabled
        logger.info(f"模块 {AVAILABLE_MODULES[module_key]['name']} 已{'启用' if enabled else '禁用'}")
        return True
    return False