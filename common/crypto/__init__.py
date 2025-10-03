"""
Enterprise Cryptography Module
企业级加密模块

提供统一的加密服务接口:
- KMS/HSM密钥管理
- 信封加密
- 字段级加密
- 密钥轮换
- 审计日志
"""

from .envelope import (
    KMSProvider,
    EncryptionContext,
    KMSClient,
    AWSKMSClient,
    GCPKMSClient,
    AzureKeyVaultClient,
    FallbackFernetClient,
    EnvelopeEncryption,
    get_kms_client,
    get_envelope_encryption,
    encrypt_secret,
    decrypt_secret
)

__all__ = [
    'KMSProvider',
    'EncryptionContext',
    'KMSClient',
    'AWSKMSClient',
    'GCPKMSClient',
    'AzureKeyVaultClient',
    'FallbackFernetClient',
    'EnvelopeEncryption',
    'get_kms_client',
    'get_envelope_encryption',
    'encrypt_secret',
    'decrypt_secret',
]

__version__ = '1.0.0'
