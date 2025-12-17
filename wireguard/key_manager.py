"""
HashInsight Enterprise - WireGuard Key Manager
WireGuard密钥管理器
"""

import subprocess
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class WireGuardKeyManager:
    """WireGuard密钥管理器"""
    
    KEY_STORAGE_PATH = "/etc/wireguard/keys"
    
    def __init__(self):
        """初始化密钥管理器"""
        os.makedirs(self.KEY_STORAGE_PATH, exist_ok=True)
    
    def generate_keypair(self, site_name: str) -> Tuple[str, str]:
        """
        生成密钥对
        
        Returns:
            (private_key, public_key)
        """
        try:
            # 生成私钥
            private_key_result = subprocess.run(
                ['wg', 'genkey'],
                capture_output=True,
                text=True,
                check=True
            )
            private_key = private_key_result.stdout.strip()
            
            # 生成公钥
            public_key_result = subprocess.run(
                ['wg', 'pubkey'],
                input=private_key,
                capture_output=True,
                text=True,
                check=True
            )
            public_key = public_key_result.stdout.strip()
            
            # 保存密钥对
            self._save_keypair(site_name, private_key, public_key)
            
            logger.info(f"Generated keypair for site: {site_name}")
            return private_key, public_key
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate keypair: {e}")
            raise
    
    def _save_keypair(self, site_name: str, private_key: str, public_key: str):
        """保存密钥对到文件"""
        site_dir = os.path.join(self.KEY_STORAGE_PATH, site_name)
        os.makedirs(site_dir, exist_ok=True)
        
        # 保存私钥
        with open(os.path.join(site_dir, 'private.key'), 'w') as f:
            f.write(private_key)
        
        # 保存公钥
        with open(os.path.join(site_dir, 'public.key'), 'w') as f:
            f.write(public_key)
        
        # 保存元数据
        metadata = {
            'site_name': site_name,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=365)).isoformat(),
            'status': 'active'
        }
        
        with open(os.path.join(site_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # 设置权限
        os.chmod(os.path.join(site_dir, 'private.key'), 0o600)
    
    def get_keypair(self, site_name: str) -> Tuple[str, str]:
        """获取站点密钥对"""
        site_dir = os.path.join(self.KEY_STORAGE_PATH, site_name)
        
        if not os.path.exists(site_dir):
            raise FileNotFoundError(f"No keys found for site: {site_name}")
        
        with open(os.path.join(site_dir, 'private.key')) as f:
            private_key = f.read().strip()
        
        with open(os.path.join(site_dir, 'public.key')) as f:
            public_key = f.read().strip()
        
        return private_key, public_key
    
    def rotate_keys(self, site_name: str) -> Tuple[str, str]:
        """轮换密钥"""
        # 备份旧密钥
        old_private, old_public = self.get_keypair(site_name)
        backup_dir = os.path.join(self.KEY_STORAGE_PATH, f"{site_name}_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        os.makedirs(backup_dir, exist_ok=True)
        
        with open(os.path.join(backup_dir, 'private.key'), 'w') as f:
            f.write(old_private)
        with open(os.path.join(backup_dir, 'public.key'), 'w') as f:
            f.write(old_public)
        
        # 生成新密钥
        new_private, new_public = self.generate_keypair(site_name)
        
        logger.info(f"Rotated keys for site: {site_name}")
        return new_private, new_public
