"""
Credential Protection Service - 三种 IP/凭证保护模式
Mode 1: UI Masking (明文存储 + UI脱敏 + RBAC)
Mode 2: Server Envelope (服务器端加密)
Mode 3: Device E2EE (设备端封存，服务器只存密文)
"""
import json
from typing import Dict, Any, Optional, Tuple
from services.envelope_kms_service import kms_service


class CredentialProtectionService:
    """凭证保护服务 - 支持三种保护模式"""
    
    MODE_UI_MASKING = 1
    MODE_SERVER_ENVELOPE = 2
    MODE_DEVICE_E2EE = 3
    
    MODE_NAMES = {
        1: 'UI Masking',
        2: 'Server Envelope',
        3: 'Device E2EE'
    }
    
    def mask_ip(self, ip: str) -> str:
        """IP地址脱敏: 192.168.1.100 -> 192.168.xxx.xxx"""
        if not ip:
            return ""
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.xxx.xxx"
        return ip[:len(ip)//2] + "***"
    
    SENSITIVE_KEYS = ('api_password', 'password', 'secret', 'pass', 'key', 'token', 'credential')
    
    def mask_credential(self, cred_json: str, role: str = 'viewer') -> Dict[str, Any]:
        """根据角色脱敏凭证（viewer角色会遮盖敏感字段）"""
        try:
            cred = json.loads(cred_json)
        except:
            return {"display": "[Invalid JSON]"}
        
        result = {}
        for key, val in cred.items():
            if key == 'ip':
                result[key] = self.mask_ip(str(val)) if role != 'admin' else val
            elif key.lower() in self.SENSITIVE_KEYS or any(s in key.lower() for s in self.SENSITIVE_KEYS):
                result[key] = '******' if role != 'admin' else val
            else:
                result[key] = val
        return result
    
    def compute_fingerprint(self, data: str) -> str:
        """计算凭证指纹（代理到 KMS 服务）"""
        return kms_service.compute_fingerprint(data)
    
    def store_credential(self, site, credential_json: str, device_id: Optional[int] = None, 
                         e2ee_ciphertext: Optional[str] = None, counter: int = 1) -> Tuple[str, int, str]:
        """
        存储凭证，根据站点 ip_mode 决定保护方式
        返回: (credential_value, credential_mode, fingerprint)
        """
        mode = getattr(site, 'ip_mode', 1)
        
        if mode == self.MODE_UI_MASKING:
            fingerprint = kms_service.compute_fingerprint(credential_json)
            return credential_json, 1, fingerprint
        
        elif mode == self.MODE_SERVER_ENVELOPE:
            from db import db
            if not site.site_dek_wrapped:
                dek = kms_service.generate_site_dek()
                site.site_dek_wrapped = kms_service.wrap_dek(dek)
                db.session.add(site)
            encrypted = kms_service.encrypt_with_site_dek(credential_json, site.site_dek_wrapped)
            fingerprint = kms_service.compute_fingerprint(credential_json)
            return encrypted, 2, fingerprint
        
        elif mode == self.MODE_DEVICE_E2EE:
            if not e2ee_ciphertext:
                raise ValueError("Mode 3 requires e2ee_ciphertext from client")
            return f"E2EE:{e2ee_ciphertext}", 3, f"e2ee_{counter}"
        
        raise ValueError(f"Unknown mode: {mode}")
    
    def reveal_credential(self, miner, site, reason: str, actor: str) -> Dict[str, Any]:
        """
        揭示凭证 (admin only)
        Mode 1: 直接返回
        Mode 2: 服务器解密返回
        Mode 3: 返回错误 (需要 Edge 解密)
        """
        mode = getattr(miner, 'credential_mode', 1)
        cred_value = getattr(miner, 'credential_value', None)
        
        if not cred_value:
            return {'success': False, 'error': 'No credential stored'}
        
        if mode == self.MODE_UI_MASKING:
            try:
                return {
                    'success': True,
                    'credential': json.loads(cred_value),
                    'mode': 'plaintext'
                }
            except:
                return {'success': False, 'error': 'Invalid credential JSON'}
        
        elif mode == self.MODE_SERVER_ENVELOPE:
            if not site.site_dek_wrapped:
                return {'success': False, 'error': 'Site DEK not found'}
            try:
                plaintext = kms_service.decrypt_with_site_dek(cred_value, site.site_dek_wrapped)
                return {
                    'success': True,
                    'credential': json.loads(plaintext),
                    'mode': 'server_decrypted'
                }
            except Exception as e:
                return {'success': False, 'error': f'Decryption failed: {str(e)}'}
        
        elif mode == self.MODE_DEVICE_E2EE:
            return {
                'success': False,
                'error': 'E2EE credentials can only be decrypted by Edge device',
                'mode': 'e2ee',
                'ciphertext': cred_value[5:] if cred_value.startswith('E2EE:') else None
            }
        
        return {'success': False, 'error': f'Unknown mode: {mode}'}
    
    def get_display_value(self, miner, site, role: str = 'viewer') -> Dict[str, Any]:
        """获取用于显示的凭证信息"""
        mode = getattr(miner, 'credential_mode', 1)
        cred_value = getattr(miner, 'credential_value', None)
        
        result = {
            'mode': mode,
            'mode_name': self.MODE_NAMES.get(mode, 'Unknown'),
            'protected': mode > 1
        }
        
        if mode == self.MODE_UI_MASKING:
            if cred_value:
                result['display'] = self.mask_credential(cred_value, role)
            else:
                result['display'] = {}
        
        elif mode == self.MODE_SERVER_ENVELOPE:
            result['display'] = {'status': '[Server Encrypted]'}
            result['can_reveal'] = role == 'admin'
        
        elif mode == self.MODE_DEVICE_E2EE:
            result['display'] = {'status': '[E2EE Protected]'}
            result['can_reveal'] = False
            result['edge_decrypt_required'] = True
        
        return result
    
    def migrate_credential(self, miner, old_site, new_site, admin_plaintext: str = None) -> Tuple[bool, str]:
        """
        迁移凭证到新模式
        返回: (success, message)
        """
        old_mode = getattr(miner, 'credential_mode', 1)
        new_mode = getattr(new_site, 'ip_mode', 1)
        
        if old_mode == new_mode:
            return True, "No migration needed, same mode"
        
        if old_mode == self.MODE_DEVICE_E2EE and new_mode != self.MODE_DEVICE_E2EE:
            return False, "Cannot migrate from E2EE without Edge device decryption"
        
        if old_mode == self.MODE_UI_MASKING:
            plaintext = miner.credential_value
        elif old_mode == self.MODE_SERVER_ENVELOPE:
            try:
                plaintext = kms_service.decrypt_with_site_dek(miner.credential_value, old_site.site_dek_wrapped)
            except Exception as e:
                return False, f"Failed to decrypt: {str(e)}"
        else:
            return False, "Cannot get plaintext from E2EE mode"
        
        try:
            cred_value, cred_mode, fingerprint = self.store_credential(new_site, plaintext)
            miner.credential_value = cred_value
            miner.credential_mode = cred_mode
            miner.fingerprint = fingerprint
            return True, f"Migrated from mode {old_mode} to mode {new_mode}"
        except Exception as e:
            return False, f"Migration failed: {str(e)}"
    
    def validate_anti_rollback(self, miner, counter: int) -> Tuple[bool, str]:
        """
        验证反回滚计数器
        返回: (valid, message)
        """
        last_counter = getattr(miner, 'last_accepted_counter', 0)
        
        if counter <= last_counter:
            return False, f"Anti-rollback violation: counter {counter} <= last accepted {last_counter}"
        
        return True, f"Counter valid: {counter} > {last_counter}"


credential_service = CredentialProtectionService()
