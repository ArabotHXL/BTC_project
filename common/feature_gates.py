"""
Feature Gates - Coming Soon 功能产品化

Provides unified responses for disabled/placeholder features.
Prevents mock data from being returned, gives clear next steps to users.

Usage:
    from common.feature_gates import feature_disabled, require_feature

    @app.route('/api/v1/web3/nft')
    @require_feature('web3_nft')
    def get_nft():
        ...

    # Or manual check:
    if not is_feature_enabled('web3_nft'):
        return feature_disabled('web3_nft')
"""

import os
import logging
from functools import wraps
from flask import jsonify, request, g
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


FEATURE_CONFIG = {
    'web3_nft': {
        'name': 'Web3 NFT Integration',
        'name_zh': 'Web3 NFT 集成',
        'status': 'coming_soon',
        'env_key': 'FEATURE_WEB3_NFT_ENABLED',
        'requirements': ['Enterprise plan', 'Blockchain wallet setup'],
        'requirements_zh': ['企业版订阅', '区块链钱包设置'],
        'eta': '2026-Q2',
        'contact': 'sales@hashinsight.io',
        'waitlist_url': '/contact?feature=web3_nft',
    },
    'web3_sla': {
        'name': 'Web3 SLA Certificates',
        'name_zh': 'Web3 SLA 证书',
        'status': 'coming_soon',
        'env_key': 'FEATURE_WEB3_SLA_ENABLED',
        'requirements': ['Enterprise plan', 'Blockchain wallet setup'],
        'requirements_zh': ['企业版订阅', '区块链钱包设置'],
        'eta': '2026-Q2',
        'contact': 'sales@hashinsight.io',
        'waitlist_url': '/contact?feature=web3_sla',
    },
    'ai_autonomous': {
        'name': 'AI Autonomous Operations',
        'name_zh': 'AI 自主运维',
        'status': 'beta',
        'env_key': 'FEATURE_AI_AUTONOMOUS_ENABLED',
        'requirements': ['Pro plan or higher', 'AI integration setup'],
        'requirements_zh': ['专业版或更高', 'AI 集成设置'],
        'eta': '2026-Q1',
        'contact': 'support@hashinsight.io',
        'waitlist_url': '/contact?feature=ai_autonomous',
    },
    'defi_yield': {
        'name': 'DeFi Yield Strategies',
        'name_zh': 'DeFi 收益策略',
        'status': 'coming_soon',
        'env_key': 'FEATURE_DEFI_YIELD_ENABLED',
        'requirements': ['Enterprise plan', 'DeFi wallet connection'],
        'requirements_zh': ['企业版订阅', 'DeFi 钱包连接'],
        'eta': '2026-Q3',
        'contact': 'sales@hashinsight.io',
        'waitlist_url': '/contact?feature=defi_yield',
    },
    'exchange_trading': {
        'name': 'Exchange Auto-Trading',
        'name_zh': '交易所自动交易',
        'status': 'coming_soon',
        'env_key': 'FEATURE_EXCHANGE_TRADING_ENABLED',
        'requirements': ['Enterprise plan', 'Exchange API keys'],
        'requirements_zh': ['企业版订阅', '交易所 API 密钥'],
        'eta': '2026-Q2',
        'contact': 'sales@hashinsight.io',
        'waitlist_url': '/contact?feature=exchange_trading',
    },
    'multi_site': {
        'name': 'Multi-Site Management',
        'name_zh': '多站点管理',
        'status': 'available',
        'env_key': 'FEATURE_MULTI_SITE_ENABLED',
        'requirements': ['Pro plan or higher'],
        'requirements_zh': ['专业版或更高'],
        'eta': None,
        'contact': 'support@hashinsight.io',
        'waitlist_url': None,
    },
}

FEATURE_STATUS = {
    'available': {'code': 200, 'message': 'Feature is available'},
    'beta': {'code': 200, 'message': 'Feature is in beta testing'},
    'coming_soon': {'code': 503, 'message': 'Feature is coming soon'},
    'disabled': {'code': 503, 'message': 'Feature is disabled'},
    'deprecated': {'code': 410, 'message': 'Feature is deprecated'},
}


def is_feature_enabled(feature_key: str) -> bool:
    """Check if a feature is enabled via environment variable"""
    config = FEATURE_CONFIG.get(feature_key, {})
    env_key = config.get('env_key', f'FEATURE_{feature_key.upper()}_ENABLED')
    
    if config.get('status') == 'available':
        return os.environ.get(env_key, 'true').lower() == 'true'
    
    return os.environ.get(env_key, 'false').lower() == 'true'


def feature_disabled(feature_key: str, lang: str = 'en') -> tuple:
    """Return standardized feature_disabled response
    
    Args:
        feature_key: The feature identifier
        lang: Language code ('en' or 'zh')
    
    Returns:
        (response, status_code) tuple
    """
    config = FEATURE_CONFIG.get(feature_key, {})
    status_info = FEATURE_STATUS.get(config.get('status', 'disabled'), FEATURE_STATUS['disabled'])
    
    is_zh = lang == 'zh' or (hasattr(g, 'lang') and g.lang == 'zh')
    
    name = config.get('name_zh' if is_zh else 'name', feature_key)
    requirements = config.get('requirements_zh' if is_zh else 'requirements', [])
    
    response = {
        'error': 'feature_disabled',
        'feature': feature_key,
        'feature_name': name,
        'status': config.get('status', 'disabled'),
        'message': '该功能即将上线' if is_zh else 'This feature is coming soon',
        'requirements': requirements,
        'next_steps': {
            'contact': config.get('contact'),
            'waitlist': config.get('waitlist_url'),
            'eta': config.get('eta'),
        },
        '_coming_soon': {
            'show_ui': True,
            'allow_waitlist': True,
            'show_requirements': True,
        }
    }
    
    return jsonify(response), status_info['code']


def require_feature(feature_key: str):
    """Decorator to require a feature to be enabled
    
    Usage:
        @app.route('/api/v1/web3/nft')
        @require_feature('web3_nft')
        def get_nft():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not is_feature_enabled(feature_key):
                lang = request.args.get('lang', 'en')
                return feature_disabled(feature_key, lang)
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_feature_status(feature_key: str) -> Dict[str, Any]:
    """Get feature status for UI display"""
    config = FEATURE_CONFIG.get(feature_key, {})
    enabled = is_feature_enabled(feature_key)
    
    return {
        'feature': feature_key,
        'name': config.get('name', feature_key),
        'name_zh': config.get('name_zh', feature_key),
        'enabled': enabled,
        'status': config.get('status', 'unknown'),
        'eta': config.get('eta'),
        'requirements': config.get('requirements', []),
        'requirements_zh': config.get('requirements_zh', []),
    }


def get_all_features() -> Dict[str, Dict]:
    """Get all features with their status"""
    return {
        key: get_feature_status(key)
        for key in FEATURE_CONFIG.keys()
    }
