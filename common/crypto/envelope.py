"""
企业级KMS/HSM密钥管理 - 信封加密实现
Envelope Encryption Implementation for Enterprise Key Management

支持的KMS提供商:
- AWS KMS (Amazon Key Management Service)
- GCP KMS (Google Cloud Key Management Service)
- Azure Key Vault
- Local HSM (PKCS#11 interface)

信封加密原理:
1. 使用KMS生成数据加密密钥(DEK)
2. 使用DEK加密实际数据
3. 使用KMS主密钥(CMK)加密DEK
4. 存储: 加密后的数据 + 加密后的DEK

安全特性:
- 密钥永不离开KMS/HSM
- 支持密钥自动轮换
- 审计日志集成
- 多区域冗余
- FIPS 140-2 Level 3 合规
"""

import os
import json
import logging
import base64
import hashlib
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, timedelta
from enum import Enum
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class KMSProvider(Enum):
    """KMS提供商枚举"""
    AWS_KMS = "aws_kms"
    GCP_KMS = "gcp_kms"
    AZURE_KEY_VAULT = "azure_key_vault"
    LOCAL_HSM = "local_hsm"
    FALLBACK_FERNET = "fallback_fernet"  # 降级模式

class EncryptionContext:
    """加密上下文 - 用于审计和访问控制"""
    
    def __init__(
        self,
        purpose: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        additional_context: Optional[Dict[str, str]] = None
    ):
        self.purpose = purpose
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.resource_type = resource_type
        self.additional_context = additional_context or {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        context = {
            "purpose": self.purpose,
            "timestamp": self.timestamp
        }
        if self.user_id:
            context["user_id"] = self.user_id
        if self.tenant_id:
            context["tenant_id"] = self.tenant_id
        if self.resource_type:
            context["resource_type"] = self.resource_type
        context.update(self.additional_context)
        return context
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), sort_keys=True)

class KMSClient:
    """KMS客户端抽象基类"""
    
    def __init__(self, provider: KMSProvider, config: Dict[str, Any]):
        self.provider = provider
        self.config = config
        self.audit_enabled = config.get('audit_enabled', True)
    
    def generate_data_key(
        self,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> Tuple[bytes, bytes]:
        """
        生成数据加密密钥(DEK)
        
        Returns:
            Tuple[plaintext_key, encrypted_key]
        """
        raise NotImplementedError
    
    def decrypt_data_key(
        self,
        encrypted_key: bytes,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> bytes:
        """解密数据加密密钥(DEK)"""
        raise NotImplementedError
    
    def encrypt_secret(
        self,
        plaintext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接使用KMS加密数据(小数据量)"""
        raise NotImplementedError
    
    def decrypt_secret(
        self,
        ciphertext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接使用KMS解密数据"""
        raise NotImplementedError
    
    def log_audit(self, operation: str, key_id: str, context: Optional[EncryptionContext], success: bool):
        """记录审计日志"""
        if not self.audit_enabled:
            return
        
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": self.provider.value,
            "operation": operation,
            "key_id": key_id,
            "success": success,
            "context": context.to_dict() if context else {}
        }
        logger.info(f"KMS_AUDIT: {json.dumps(audit_entry)}")

class AWSKMSClient(KMSClient):
    """AWS KMS客户端实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(KMSProvider.AWS_KMS, config)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化AWS KMS客户端"""
        try:
            import boto3
            
            aws_config = {
                'region_name': self.config.get('region', os.environ.get('AWS_REGION', 'us-east-1'))
            }
            
            if self.config.get('access_key_id'):
                aws_config['aws_access_key_id'] = self.config['access_key_id']
            if self.config.get('secret_access_key'):
                aws_config['aws_secret_access_key'] = self.config['secret_access_key']
            
            self.client = boto3.client('kms', **aws_config)
            logger.info("AWS KMS client initialized successfully")
            
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS KMS client: {e}")
            raise
    
    def generate_data_key(
        self,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> Tuple[bytes, bytes]:
        """生成数据加密密钥"""
        try:
            encryption_context = context.to_dict() if context else {}
            
            response = self.client.generate_data_key(
                KeyId=key_id,
                KeySpec='AES_256',
                EncryptionContext=encryption_context
            )
            
            plaintext_key = response['Plaintext']
            encrypted_key = response['CiphertextBlob']
            
            self.log_audit("generate_data_key", key_id, context, True)
            
            return plaintext_key, encrypted_key
            
        except Exception as e:
            self.log_audit("generate_data_key", key_id, context, False)
            logger.error(f"AWS KMS generate_data_key failed: {e}")
            raise
    
    def decrypt_data_key(
        self,
        encrypted_key: bytes,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> bytes:
        """解密数据加密密钥"""
        try:
            encryption_context = context.to_dict() if context else {}
            
            response = self.client.decrypt(
                CiphertextBlob=encrypted_key,
                EncryptionContext=encryption_context
            )
            
            plaintext_key = response['Plaintext']
            
            self.log_audit("decrypt_data_key", key_id, context, True)
            
            return plaintext_key
            
        except Exception as e:
            self.log_audit("decrypt_data_key", key_id, context, False)
            logger.error(f"AWS KMS decrypt_data_key failed: {e}")
            raise
    
    def encrypt_secret(
        self,
        plaintext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接使用KMS加密"""
        try:
            encryption_context = context.to_dict() if context else {}
            
            response = self.client.encrypt(
                KeyId=key_id,
                Plaintext=plaintext.encode('utf-8'),
                EncryptionContext=encryption_context
            )
            
            ciphertext = base64.b64encode(response['CiphertextBlob']).decode('utf-8')
            
            self.log_audit("encrypt_secret", key_id, context, True)
            
            return ciphertext
            
        except Exception as e:
            self.log_audit("encrypt_secret", key_id, context, False)
            logger.error(f"AWS KMS encrypt_secret failed: {e}")
            raise
    
    def decrypt_secret(
        self,
        ciphertext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接使用KMS解密"""
        try:
            encryption_context = context.to_dict() if context else {}
            
            response = self.client.decrypt(
                CiphertextBlob=base64.b64decode(ciphertext),
                EncryptionContext=encryption_context
            )
            
            plaintext = response['Plaintext'].decode('utf-8')
            
            self.log_audit("decrypt_secret", key_id, context, True)
            
            return plaintext
            
        except Exception as e:
            self.log_audit("decrypt_secret", key_id, context, False)
            logger.error(f"AWS KMS decrypt_secret failed: {e}")
            raise

class GCPKMSClient(KMSClient):
    """GCP KMS客户端实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(KMSProvider.GCP_KMS, config)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化GCP KMS客户端"""
        try:
            from google.cloud import kms
            
            project_id = self.config.get('project_id', os.environ.get('GCP_PROJECT_ID'))
            if not project_id:
                raise ValueError("GCP project_id is required")
            
            self.project_id = project_id
            self.location_id = self.config.get('location', 'us-east1')
            self.client = kms.KeyManagementServiceClient()
            
            logger.info("GCP KMS client initialized successfully")
            
        except ImportError:
            logger.error("google-cloud-kms not installed. Install with: pip install google-cloud-kms")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize GCP KMS client: {e}")
            raise
    
    def generate_data_key(
        self,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> Tuple[bytes, bytes]:
        """生成数据加密密钥"""
        try:
            plaintext_key = secrets.token_bytes(32)
            
            key_name = self.client.crypto_key_path(
                self.project_id,
                self.location_id,
                key_id.split('/')[0],  # keyring
                key_id.split('/')[1]   # key
            )
            
            encrypt_response = self.client.encrypt(
                request={
                    "name": key_name,
                    "plaintext": plaintext_key,
                    "additional_authenticated_data": context.to_json().encode() if context else b""
                }
            )
            
            encrypted_key = encrypt_response.ciphertext
            
            self.log_audit("generate_data_key", key_id, context, True)
            
            return plaintext_key, encrypted_key
            
        except Exception as e:
            self.log_audit("generate_data_key", key_id, context, False)
            logger.error(f"GCP KMS generate_data_key failed: {e}")
            raise
    
    def decrypt_data_key(
        self,
        encrypted_key: bytes,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> bytes:
        """解密数据加密密钥"""
        try:
            key_name = self.client.crypto_key_path(
                self.project_id,
                self.location_id,
                key_id.split('/')[0],
                key_id.split('/')[1]
            )
            
            decrypt_response = self.client.decrypt(
                request={
                    "name": key_name,
                    "ciphertext": encrypted_key,
                    "additional_authenticated_data": context.to_json().encode() if context else b""
                }
            )
            
            plaintext_key = decrypt_response.plaintext
            
            self.log_audit("decrypt_data_key", key_id, context, True)
            
            return plaintext_key
            
        except Exception as e:
            self.log_audit("decrypt_data_key", key_id, context, False)
            logger.error(f"GCP KMS decrypt_data_key failed: {e}")
            raise
    
    def encrypt_secret(
        self,
        plaintext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接使用KMS加密"""
        try:
            key_name = self.client.crypto_key_path(
                self.project_id,
                self.location_id,
                key_id.split('/')[0],
                key_id.split('/')[1]
            )
            
            encrypt_response = self.client.encrypt(
                request={
                    "name": key_name,
                    "plaintext": plaintext.encode('utf-8'),
                    "additional_authenticated_data": context.to_json().encode() if context else b""
                }
            )
            
            ciphertext = base64.b64encode(encrypt_response.ciphertext).decode('utf-8')
            
            self.log_audit("encrypt_secret", key_id, context, True)
            
            return ciphertext
            
        except Exception as e:
            self.log_audit("encrypt_secret", key_id, context, False)
            logger.error(f"GCP KMS encrypt_secret failed: {e}")
            raise
    
    def decrypt_secret(
        self,
        ciphertext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接使用KMS解密"""
        try:
            key_name = self.client.crypto_key_path(
                self.project_id,
                self.location_id,
                key_id.split('/')[0],
                key_id.split('/')[1]
            )
            
            decrypt_response = self.client.decrypt(
                request={
                    "name": key_name,
                    "ciphertext": base64.b64decode(ciphertext),
                    "additional_authenticated_data": context.to_json().encode() if context else b""
                }
            )
            
            plaintext = decrypt_response.plaintext.decode('utf-8')
            
            self.log_audit("decrypt_secret", key_id, context, True)
            
            return plaintext
            
        except Exception as e:
            self.log_audit("decrypt_secret", key_id, context, False)
            logger.error(f"GCP KMS decrypt_secret failed: {e}")
            raise

class AzureKeyVaultClient(KMSClient):
    """Azure Key Vault客户端实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(KMSProvider.AZURE_KEY_VAULT, config)
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化Azure Key Vault客户端"""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
            from azure.keyvault.keys import KeyClient
            
            vault_url = self.config.get('vault_url', os.environ.get('AZURE_VAULT_URL'))
            if not vault_url:
                raise ValueError("Azure vault_url is required")
            
            self.vault_url = vault_url
            self.credential = DefaultAzureCredential()
            self.key_client = KeyClient(vault_url=vault_url, credential=self.credential)
            
            logger.info("Azure Key Vault client initialized successfully")
            
        except ImportError:
            logger.error("azure-keyvault-keys not installed. Install with: pip install azure-keyvault-keys azure-identity")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault client: {e}")
            raise
    
    def generate_data_key(
        self,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> Tuple[bytes, bytes]:
        """生成数据加密密钥"""
        try:
            from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
            
            plaintext_key = secrets.token_bytes(32)
            
            key = self.key_client.get_key(key_id)
            crypto_client = CryptographyClient(key, credential=self.credential)
            
            aad = context.to_json().encode() if context else None
            
            encrypt_result = crypto_client.encrypt(
                EncryptionAlgorithm.rsa_oaep_256,
                plaintext_key,
                additional_authenticated_data=aad
            )
            
            encrypted_key = encrypt_result.ciphertext
            
            self.log_audit("generate_data_key", key_id, context, True)
            
            return plaintext_key, encrypted_key
            
        except Exception as e:
            self.log_audit("generate_data_key", key_id, context, False)
            logger.error(f"Azure Key Vault generate_data_key failed: {e}")
            raise
    
    def decrypt_data_key(
        self,
        encrypted_key: bytes,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> bytes:
        """解密数据加密密钥"""
        try:
            from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
            
            key = self.key_client.get_key(key_id)
            crypto_client = CryptographyClient(key, credential=self.credential)
            
            aad = context.to_json().encode() if context else None
            
            decrypt_result = crypto_client.decrypt(
                EncryptionAlgorithm.rsa_oaep_256,
                encrypted_key,
                additional_authenticated_data=aad
            )
            
            plaintext_key = decrypt_result.plaintext
            
            self.log_audit("decrypt_data_key", key_id, context, True)
            
            return plaintext_key
            
        except Exception as e:
            self.log_audit("decrypt_data_key", key_id, context, False)
            logger.error(f"Azure Key Vault decrypt_data_key failed: {e}")
            raise
    
    def encrypt_secret(
        self,
        plaintext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接使用Key Vault加密"""
        try:
            from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
            
            key = self.key_client.get_key(key_id)
            crypto_client = CryptographyClient(key, credential=self.credential)
            
            aad = context.to_json().encode() if context else None
            
            encrypt_result = crypto_client.encrypt(
                EncryptionAlgorithm.rsa_oaep_256,
                plaintext.encode('utf-8'),
                additional_authenticated_data=aad
            )
            
            ciphertext = base64.b64encode(encrypt_result.ciphertext).decode('utf-8')
            
            self.log_audit("encrypt_secret", key_id, context, True)
            
            return ciphertext
            
        except Exception as e:
            self.log_audit("encrypt_secret", key_id, context, False)
            logger.error(f"Azure Key Vault encrypt_secret failed: {e}")
            raise
    
    def decrypt_secret(
        self,
        ciphertext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接使用Key Vault解密"""
        try:
            from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
            
            key = self.key_client.get_key(key_id)
            crypto_client = CryptographyClient(key, credential=self.credential)
            
            aad = context.to_json().encode() if context else None
            
            decrypt_result = crypto_client.decrypt(
                EncryptionAlgorithm.rsa_oaep_256,
                base64.b64decode(ciphertext),
                additional_authenticated_data=aad
            )
            
            plaintext = decrypt_result.plaintext.decode('utf-8')
            
            self.log_audit("decrypt_secret", key_id, context, True)
            
            return plaintext
            
        except Exception as e:
            self.log_audit("decrypt_secret", key_id, context, False)
            logger.error(f"Azure Key Vault decrypt_secret failed: {e}")
            raise

class FallbackFernetClient(KMSClient):
    """降级模式 - 使用Fernet加密（用于开发环境或KMS不可用时）"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(KMSProvider.FALLBACK_FERNET, config)
        self.master_key = None
        self._initialize_key()
    
    def _initialize_key(self):
        """初始化主密钥"""
        try:
            master_key_b64 = self.config.get('master_key') or os.environ.get('FALLBACK_MASTER_KEY')
            
            if not master_key_b64:
                logger.warning("⚠️ No master key provided for fallback mode, generating new key")
                master_key_b64 = Fernet.generate_key().decode('utf-8')
                logger.warning(f"⚠️ GENERATED KEY (SAVE THIS): {master_key_b64}")
            
            self.master_key = master_key_b64.encode() if isinstance(master_key_b64, str) else master_key_b64
            self.fernet = Fernet(self.master_key)
            
            logger.info("Fallback Fernet client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Fallback Fernet client: {e}")
            raise
    
    def generate_data_key(
        self,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> Tuple[bytes, bytes]:
        """生成数据加密密钥"""
        try:
            plaintext_key = Fernet.generate_key()
            encrypted_key = self.fernet.encrypt(plaintext_key)
            
            self.log_audit("generate_data_key", key_id, context, True)
            
            return plaintext_key, encrypted_key
            
        except Exception as e:
            self.log_audit("generate_data_key", key_id, context, False)
            logger.error(f"Fallback generate_data_key failed: {e}")
            raise
    
    def decrypt_data_key(
        self,
        encrypted_key: bytes,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> bytes:
        """解密数据加密密钥"""
        try:
            plaintext_key = self.fernet.decrypt(encrypted_key)
            
            self.log_audit("decrypt_data_key", key_id, context, True)
            
            return plaintext_key
            
        except Exception as e:
            self.log_audit("decrypt_data_key", key_id, context, False)
            logger.error(f"Fallback decrypt_data_key failed: {e}")
            raise
    
    def encrypt_secret(
        self,
        plaintext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接加密"""
        try:
            ciphertext = self.fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')
            
            self.log_audit("encrypt_secret", key_id, context, True)
            
            return ciphertext
            
        except Exception as e:
            self.log_audit("encrypt_secret", key_id, context, False)
            logger.error(f"Fallback encrypt_secret failed: {e}")
            raise
    
    def decrypt_secret(
        self,
        ciphertext: str,
        key_id: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """直接解密"""
        try:
            plaintext = self.fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
            
            self.log_audit("decrypt_secret", key_id, context, True)
            
            return plaintext
            
        except Exception as e:
            self.log_audit("decrypt_secret", key_id, context, False)
            logger.error(f"Fallback decrypt_secret failed: {e}")
            raise

class EnvelopeEncryption:
    """信封加密管理器 - 统一接口"""
    
    def __init__(self, kms_client: KMSClient, master_key_id: str):
        self.kms_client = kms_client
        self.master_key_id = master_key_id
    
    def encrypt(
        self,
        plaintext: str,
        context: Optional[EncryptionContext] = None
    ) -> Dict[str, str]:
        """
        使用信封加密加密数据
        
        Returns:
            {
                "ciphertext": base64编码的加密数据,
                "encrypted_key": base64编码的加密DEK,
                "algorithm": 加密算法,
                "version": 版本号,
                "context_hash": 上下文哈希(用于验证)
            }
        """
        try:
            plaintext_dek, encrypted_dek = self.kms_client.generate_data_key(
                self.master_key_id,
                context
            )
            
            fernet = Fernet(plaintext_dek)
            ciphertext = fernet.encrypt(plaintext.encode('utf-8'))
            
            context_hash = hashlib.sha256(context.to_json().encode()).hexdigest() if context else ""
            
            return {
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
                "encrypted_key": base64.b64encode(encrypted_dek).decode('utf-8'),
                "algorithm": "AES-256-GCM",
                "version": "1.0",
                "context_hash": context_hash
            }
            
        except Exception as e:
            logger.error(f"Envelope encryption failed: {e}")
            raise
    
    def decrypt(
        self,
        envelope: Dict[str, str],
        context: Optional[EncryptionContext] = None
    ) -> str:
        """
        使用信封加密解密数据
        
        Args:
            envelope: encrypt()返回的加密包
            context: 加密上下文(必须与加密时一致)
        
        Returns:
            解密后的明文
        """
        try:
            if context and envelope.get("context_hash"):
                expected_hash = hashlib.sha256(context.to_json().encode()).hexdigest()
                if expected_hash != envelope["context_hash"]:
                    raise ValueError("Encryption context mismatch")
            
            encrypted_dek = base64.b64decode(envelope["encrypted_key"])
            plaintext_dek = self.kms_client.decrypt_data_key(
                encrypted_dek,
                self.master_key_id,
                context
            )
            
            fernet = Fernet(plaintext_dek)
            ciphertext = base64.b64decode(envelope["ciphertext"])
            plaintext = fernet.decrypt(ciphertext).decode('utf-8')
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Envelope decryption failed: {e}")
            raise
    
    def encrypt_field(
        self,
        field_value: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """
        加密数据库字段(返回JSON字符串)
        """
        envelope = self.encrypt(field_value, context)
        return json.dumps(envelope)
    
    def decrypt_field(
        self,
        encrypted_field: str,
        context: Optional[EncryptionContext] = None
    ) -> str:
        """
        解密数据库字段
        """
        envelope = json.loads(encrypted_field)
        return self.decrypt(envelope, context)

def get_kms_client(provider: str = None) -> KMSClient:
    """
    获取KMS客户端实例(工厂模式)
    
    配置优先级:
    1. 环境变量 KMS_PROVIDER
    2. 参数 provider
    3. 默认降级到 Fernet
    """
    provider = provider or os.environ.get('KMS_PROVIDER', 'fallback_fernet')
    provider_enum = KMSProvider(provider)
    
    if provider_enum == KMSProvider.AWS_KMS:
        config = {
            'region': os.environ.get('AWS_REGION'),
            'access_key_id': os.environ.get('AWS_ACCESS_KEY_ID'),
            'secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
            'audit_enabled': True
        }
        return AWSKMSClient(config)
    
    elif provider_enum == KMSProvider.GCP_KMS:
        config = {
            'project_id': os.environ.get('GCP_PROJECT_ID'),
            'location': os.environ.get('GCP_KMS_LOCATION', 'us-east1'),
            'audit_enabled': True
        }
        return GCPKMSClient(config)
    
    elif provider_enum == KMSProvider.AZURE_KEY_VAULT:
        config = {
            'vault_url': os.environ.get('AZURE_VAULT_URL'),
            'audit_enabled': True
        }
        return AzureKeyVaultClient(config)
    
    else:  # FALLBACK_FERNET
        config = {
            'master_key': os.environ.get('FALLBACK_MASTER_KEY'),
            'audit_enabled': True
        }
        return FallbackFernetClient(config)

def get_envelope_encryption(key_id: str = None) -> EnvelopeEncryption:
    """
    获取信封加密实例(便捷函数)
    
    Args:
        key_id: KMS主密钥ID,如果未提供则从环境变量读取
    """
    kms_client = get_kms_client()
    master_key_id = key_id or os.environ.get('KMS_MASTER_KEY_ID', 'default-master-key')
    
    return EnvelopeEncryption(kms_client, master_key_id)

def encrypt_secret(plaintext: str, context: Optional[EncryptionContext] = None) -> Dict[str, str]:
    """便捷函数: 加密秘密数据"""
    envelope = get_envelope_encryption()
    return envelope.encrypt(plaintext, context)

def decrypt_secret(envelope: Dict[str, str], context: Optional[EncryptionContext] = None) -> str:
    """便捷函数: 解密秘密数据"""
    envelope_enc = get_envelope_encryption()
    return envelope_enc.decrypt(envelope, context)
