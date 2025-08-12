"""
简化的翻译模块
提供基本的中英文翻译功能
"""

import logging

# 翻译字典
TRANSLATIONS = {
    'en': {
        'btc_mining_calculator': 'BTC Mining Calculator',
        'language': 'Language',
        'owner': 'Owner',
        'admin': 'Admin',
        'manager': 'Manager',
        'mining_site': 'Mining Site',
        'guest': 'Guest',
        'logout': 'Logout',
        'login': 'Login',
        'dashboard': 'Dashboard',
        'user_management': 'User Management',
        'miner_settings': 'Miner Settings',
        'miner_model': 'Miner Model',
        'select_miner': 'Select Miner',
        'site_power_mw': 'Site Power (MW)',
        'miner_count': 'Miner Count',
        'electricity_cost': 'Electricity Cost',
        'btc_price': 'BTC Price',
        'use_real_time_data': 'Use Real Time Data',
        'calculate': 'Calculate',
        'results': 'Results',
        'btc_mined': 'BTC Mined',
        'daily': 'Daily',
        'profitability_heatmap': 'Profitability Heatmap',
        'difficulty': 'Difficulty',
        'network_hashrate': 'Network Hashrate',
        'block_reward': 'Block Reward',
        'subscription_plan': 'Subscription Plan',
        'free': 'Free',
        'basic': 'Basic',
        'pro': 'Pro',
        'role': 'Role',
        'has_access': 'Has Access',
        'yes': 'Yes',
        'no': 'No',
        'edit': 'Edit',
        'save': 'Save',
        'cancel': 'Cancel',
        'actions': 'Actions',
        'name': 'Name',
        'email': 'Email',
        'created_at': 'Created At',
        'last_login': 'Last Login',
        'status': 'Status',
        'active': 'Active',
        'inactive': 'Inactive',
    },
    'zh': {
        'btc_mining_calculator': 'BTC挖矿计算器',
        'language': '语言',
        'owner': '所有者',
        'admin': '管理员',
        'manager': '经理',
        'mining_site': '挖矿站点',
        'guest': '访客',
        'logout': '退出登录',
        'login': '登录',
        'dashboard': '仪表盘',
        'user_management': '用户管理',
        'miner_settings': '矿机设置',
        'miner_model': '矿机型号',
        'select_miner': '选择矿机',
        'site_power_mw': '站点功率(MW)',
        'miner_count': '矿机数量',
        'electricity_cost': '电力成本',
        'btc_price': 'BTC价格',
        'use_real_time_data': '使用实时数据',
        'calculate': '计算',
        'results': '结果',
        'btc_mined': 'BTC产出',
        'daily': '每日',
        'profitability_heatmap': '盈利能力热图',
        'difficulty': '挖矿难度',
        'network_hashrate': '网络算力',
        'block_reward': '区块奖励',
        'subscription_plan': '订阅计划',
        'free': '免费',
        'basic': '基础',
        'pro': '专业',
        'role': '角色',
        'has_access': '有访问权限',
        'yes': '是',
        'no': '否',
        'edit': '编辑',
        'save': '保存',
        'cancel': '取消',
        'actions': '操作',
        'name': '姓名',
        'email': '邮箱',
        'created_at': '创建时间',
        'last_login': '最后登录',
        'status': '状态',
        'active': '活跃',
        'inactive': '非活跃',
    }
}

def get_translation(text, to_lang='zh'):
    """
    获取文本翻译
    
    Args:
        text (str): 要翻译的文本键
        to_lang (str): 目标语言 'en' 或 'zh'
    
    Returns:
        str: 翻译后的文本
    """
    try:
        if to_lang not in ['en', 'zh']:
            to_lang = 'zh'
            
        # 获取翻译
        translation = TRANSLATIONS.get(to_lang, {}).get(text)
        
        if translation:
            logging.debug(f"Translating '{text}' to '{to_lang}'")
            # 简单的格式化：首字母大写，下划线替换为空格
            formatted = translation.title() if to_lang == 'en' else translation
            logging.debug(f"Formatted '{text}' to '{formatted}'")
            return formatted
        else:
            # 如果没有找到翻译，返回格式化的原文本
            if to_lang == 'en':
                # 英文：首字母大写，下划线替换为空格
                formatted = text.replace('_', ' ').title()
            else:
                # 中文：直接返回原文本
                formatted = text
            
            logging.warning(f"Translation not found for '{text}' in '{to_lang}', using formatted version: '{formatted}'")
            return formatted
            
    except Exception as e:
        logging.error(f"Translation error for '{text}': {e}")
        return text.replace('_', ' ').title() if to_lang == 'en' else text