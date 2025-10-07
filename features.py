"""
功能开关配置管理
Feature Flags Configuration Management

用于控制Web3、CRM、Treasury等功能的启用状态
"""

import os
from typing import Dict


class FeatureFlags:
    """功能开关配置"""
    
    WEB3_ENABLED = os.environ.get('FEATURE_WEB3_ENABLED', 'false').lower() == 'true'
    CRM_ENABLED = os.environ.get('FEATURE_CRM_ENABLED', 'true').lower() == 'true'
    TREASURY_EXECUTION_ENABLED = os.environ.get('FEATURE_TREASURY_EXECUTION_ENABLED', 'false').lower() == 'true'
    
    @classmethod
    def get_status(cls) -> Dict[str, bool]:
        """获取所有功能开关状态"""
        return {
            'web3': cls.WEB3_ENABLED,
            'crm': cls.CRM_ENABLED,
            'treasury_execution': cls.TREASURY_EXECUTION_ENABLED
        }
    
    @classmethod
    def get_enabled_features(cls) -> list:
        """获取已启用的功能列表"""
        status = cls.get_status()
        return [feature for feature, enabled in status.items() if enabled]
    
    @classmethod
    def is_feature_enabled(cls, feature_name: str) -> bool:
        """检查特定功能是否启用"""
        status = cls.get_status()
        return status.get(feature_name, False)
