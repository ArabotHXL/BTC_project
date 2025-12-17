"""
IP Encryption Service (IP 隐藏服务)

Supports three IP hiding strategies:
- Strategy 1 (MASK): UI masking only (192.168.1.xxx) + RBAC + Audit
- Strategy 2 (SERVER_ENCRYPT): Server-side encryption using Fernet
- Strategy 3 (E2EE): End-to-end encryption (IP included in device envelope)

Usage:
    from services.ip_encryption_service import ip_encryption_service
    
    # Encrypt IP (Strategy 2)
    encrypted = ip_encryption_service.encrypt_ip("192.168.1.100")
    
    # Decrypt IP (Strategy 2)
    plaintext = ip_encryption_service.decrypt_ip(encrypted)
    
    # Mask IP for display (Strategy 1)
    masked = ip_encryption_service.mask_ip("192.168.1.100")
"""

import os
import logging
import base64
import hashlib
from enum import IntEnum
from typing import Optional, Tuple
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)


class IPEncryptionMode(IntEnum):
    """IP encryption modes"""
    MASK = 1           # UI masking only (default)
    SERVER_ENCRYPT = 2 # Server-side Fernet encryption
    E2EE = 3           # End-to-end encryption (in device envelope)


class IPEncryptionService:
    """
    IP Encryption Service
    
    Manages IP address encryption/decryption for mining equipment.
    Supports multiple security levels based on user requirements.
    """
    
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialized = False
        
    def _get_encryption_key(self) -> bytes:
        """
        Derive encryption key from environment secret
        
        Uses PBKDF2 with SESSION_SECRET to derive a Fernet-compatible key.
        """
        secret = os.environ.get('SESSION_SECRET', 'default-dev-secret-change-me')
        salt = os.environ.get('IP_ENCRYPTION_SALT', 'hashinsight-ip-salt-2025').encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        return key
    
    def _get_fernet(self) -> Fernet:
        """Get or create Fernet instance"""
        if self._fernet is None:
            key = self._get_encryption_key()
            self._fernet = Fernet(key)
            self._initialized = True
        return self._fernet
    
    def encrypt_ip(self, ip_address: str) -> str:
        """
        Encrypt IP address using server-side Fernet encryption (Strategy 2)
        
        Args:
            ip_address: Plain text IP address
            
        Returns:
            Base64-encoded encrypted IP with 'ENC:' prefix
        """
        if not ip_address:
            return ''
        
        try:
            fernet = self._get_fernet()
            encrypted = fernet.encrypt(ip_address.encode())
            return f"ENC:{encrypted.decode()}"
        except Exception as e:
            logger.error(f"Failed to encrypt IP: {e}")
            raise ValueError(f"IP encryption failed: {e}")
    
    def decrypt_ip(self, encrypted_ip: str) -> str:
        """
        Decrypt IP address (Strategy 2)
        
        Args:
            encrypted_ip: Encrypted IP with 'ENC:' prefix
            
        Returns:
            Plain text IP address
        """
        if not encrypted_ip:
            return ''
        
        if not encrypted_ip.startswith('ENC:'):
            return encrypted_ip
        
        try:
            fernet = self._get_fernet()
            ciphertext = encrypted_ip[4:].encode()
            decrypted = fernet.decrypt(ciphertext)
            return decrypted.decode()
        except InvalidToken:
            logger.error("Invalid encryption token - key may have changed")
            raise ValueError("IP decryption failed - invalid token")
        except Exception as e:
            logger.error(f"Failed to decrypt IP: {e}")
            raise ValueError(f"IP decryption failed: {e}")
    
    def mask_ip(self, ip_address: str, mask_last_octet: bool = True) -> str:
        """
        Mask IP address for display (Strategy 1)
        
        Args:
            ip_address: Plain text IP address
            mask_last_octet: If True, mask last octet only (192.168.1.xxx)
                           If False, mask last two octets (192.168.xxx.xxx)
            
        Returns:
            Masked IP address
        """
        if not ip_address:
            return ''
        
        if ip_address.startswith('ENC:'):
            return '[Encrypted]'
        
        if ip_address.startswith('E2EE:'):
            return '[E2EE Protected]'
        
        try:
            parts = ip_address.split('.')
            if len(parts) != 4:
                return ip_address
            
            if mask_last_octet:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
            else:
                return f"{parts[0]}.{parts[1]}.xxx.xxx"
        except Exception:
            return ip_address
    
    def is_encrypted(self, ip_value: str) -> bool:
        """Check if IP value is server-encrypted"""
        return bool(ip_value and ip_value.startswith('ENC:'))
    
    def is_e2ee(self, ip_value: str) -> bool:
        """Check if IP is E2EE protected (stored in device envelope)"""
        return bool(ip_value and ip_value.startswith('E2EE:'))
    
    def get_display_ip(
        self, 
        ip_address: str,
        encryption_mode: int,
        can_reveal: bool = False
    ) -> Tuple[str, str]:
        """
        Get IP address for display based on encryption mode and permissions
        
        Args:
            ip_address: Stored IP value (may be encrypted)
            encryption_mode: IPEncryptionMode value
            can_reveal: Whether user has permission to see full IP
            
        Returns:
            Tuple of (display_value, status)
            status: 'plain', 'masked', 'encrypted', 'e2ee'
        """
        if not ip_address:
            return ('', 'empty')
        
        mode = IPEncryptionMode(encryption_mode) if encryption_mode else IPEncryptionMode.MASK
        
        if mode == IPEncryptionMode.MASK:
            if can_reveal:
                return (ip_address, 'plain')
            else:
                return (self.mask_ip(ip_address), 'masked')
        
        elif mode == IPEncryptionMode.SERVER_ENCRYPT:
            if self.is_encrypted(ip_address):
                if can_reveal:
                    try:
                        decrypted = self.decrypt_ip(ip_address)
                        return (decrypted, 'decrypted')
                    except Exception as e:
                        logger.error(f"Failed to decrypt for reveal: {e}")
                        return ('[Decryption Error]', 'error')
                else:
                    return ('[Server Encrypted]', 'encrypted')
            else:
                if can_reveal:
                    return (ip_address, 'plain')
                else:
                    return (self.mask_ip(ip_address), 'masked')
        
        elif mode == IPEncryptionMode.E2EE:
            return ('[E2EE Protected]', 'e2ee')
        
        return (ip_address, 'unknown')
    
    def prepare_ip_for_storage(
        self,
        ip_address: str,
        encryption_mode: int
    ) -> str:
        """
        Prepare IP address for database storage based on encryption mode
        
        Args:
            ip_address: Plain text IP address
            encryption_mode: IPEncryptionMode value
            
        Returns:
            Value to store in database
        """
        if not ip_address:
            return ''
        
        mode = IPEncryptionMode(encryption_mode) if encryption_mode else IPEncryptionMode.MASK
        
        if mode == IPEncryptionMode.MASK:
            return ip_address
        
        elif mode == IPEncryptionMode.SERVER_ENCRYPT:
            return self.encrypt_ip(ip_address)
        
        elif mode == IPEncryptionMode.E2EE:
            return 'E2EE:encrypted-in-envelope'
        
        return ip_address
    
    def generate_ip_fingerprint(self, ip_address: str) -> str:
        """
        Generate a fingerprint/hash of IP for correlation without revealing it
        
        Useful for grouping miners by subnet without exposing full IP.
        
        Args:
            ip_address: Plain text IP address
            
        Returns:
            Short hash string (first 8 chars of SHA256)
        """
        if not ip_address:
            return ''
        
        actual_ip = ip_address
        if ip_address.startswith('ENC:'):
            try:
                actual_ip = self.decrypt_ip(ip_address)
            except Exception:
                return 'unknown'
        
        salt = os.environ.get('IP_FINGERPRINT_SALT', 'hashinsight-fp-2025')
        data = f"{salt}:{actual_ip}".encode()
        hash_bytes = hashlib.sha256(data).digest()
        return base64.b64encode(hash_bytes)[:8].decode()
    
    def get_mode_name(self, mode: int, lang: str = 'zh') -> str:
        """Get human-readable name for encryption mode"""
        names = {
            1: {'zh': 'UI脱敏', 'en': 'UI Masking'},
            2: {'zh': '服务器加密', 'en': 'Server Encrypted'},
            3: {'zh': 'E2EE加密', 'en': 'E2EE Protected'},
        }
        mode_names = names.get(mode, {'zh': '未知', 'en': 'Unknown'})
        return mode_names.get(lang, mode_names['en'])


ip_encryption_service = IPEncryptionService()
