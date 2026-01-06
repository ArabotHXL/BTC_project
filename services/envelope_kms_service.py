"""
Envelope KMS Service - 两层密钥管理 (Mode 2)
MASTER_KEY (从环境变量派生) + Site DEK (每站点独立)
"""
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class EnvelopeKMSService:
    """双层信封加密密钥管理服务"""
    
    MASTER_SALT = b'HashInsight_KMS_2025'
    
    def __init__(self):
        self._master_key = None
    
    def _derive_master_key(self) -> bytes:
        """从 SESSION_SECRET 派生 MASTER_KEY"""
        if self._master_key:
            return self._master_key
            
        session_secret = os.environ.get('SESSION_SECRET', 'dev-secret-key')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.MASTER_SALT,
            iterations=100000,
            backend=default_backend()
        )
        self._master_key = kdf.derive(session_secret.encode())
        return self._master_key
    
    def _get_master_fernet(self) -> Fernet:
        """获取 MASTER_KEY Fernet 实例"""
        key = base64.urlsafe_b64encode(self._derive_master_key())
        return Fernet(key)
    
    def generate_site_dek(self) -> bytes:
        """生成新的 Site DEK (32 bytes)"""
        return os.urandom(32)
    
    def wrap_dek(self, dek: bytes) -> str:
        """用 MASTER_KEY 加密 DEK"""
        fernet = self._get_master_fernet()
        wrapped = fernet.encrypt(dek)
        return base64.b64encode(wrapped).decode()
    
    def unwrap_dek(self, wrapped_dek: str) -> bytes:
        """用 MASTER_KEY 解密 DEK"""
        fernet = self._get_master_fernet()
        wrapped = base64.b64decode(wrapped_dek)
        return fernet.decrypt(wrapped)
    
    def get_site_fernet(self, wrapped_dek: str) -> Fernet:
        """获取 Site 级别的 Fernet 实例"""
        dek = self.unwrap_dek(wrapped_dek)
        key = base64.urlsafe_b64encode(dek)
        return Fernet(key)
    
    def encrypt_with_site_dek(self, plaintext: str, wrapped_dek: str) -> str:
        """使用 Site DEK 加密数据，返回 ENC: 前缀的密文"""
        fernet = self.get_site_fernet(wrapped_dek)
        encrypted = fernet.encrypt(plaintext.encode())
        return f"ENC:{base64.b64encode(encrypted).decode()}"
    
    def decrypt_with_site_dek(self, ciphertext: str, wrapped_dek: str) -> str:
        """解密 ENC: 前缀的数据"""
        if not ciphertext.startswith('ENC:'):
            raise ValueError("Invalid ciphertext format, expected ENC: prefix")
        encrypted = base64.b64decode(ciphertext[4:])
        fernet = self.get_site_fernet(wrapped_dek)
        return fernet.decrypt(encrypted).decode()
    
    def compute_fingerprint(self, credential_json: str) -> str:
        """计算凭证指纹 (SHA-256)"""
        return hashlib.sha256(credential_json.encode()).hexdigest()[:16]


kms_service = EnvelopeKMSService()
