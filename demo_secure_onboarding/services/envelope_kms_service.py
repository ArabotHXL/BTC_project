"""
Envelope KMS Service - Key Management for Mode 2 Server Encryption
Implements MASTER_KEY + Site DEK two-layer encryption
"""
import os
import base64
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

SESSION_SECRET = os.getenv("SESSION_SECRET", "demo-secret-key-change-in-production")
MASTER_SALT = os.getenv("MASTER_SALT", "hashinsight-demo-salt")


def derive_master_key() -> bytes:
    """
    Derive MASTER_KEY from SESSION_SECRET using PBKDF2HMAC.
    This key is used to wrap/unwrap Site DEKs.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=MASTER_SALT.encode('utf-8'),
        iterations=100000,
    )
    return kdf.derive(SESSION_SECRET.encode('utf-8'))


def get_master_fernet() -> Fernet:
    """Get Fernet instance using MASTER_KEY"""
    master_key = derive_master_key()
    master_key_b64 = base64.urlsafe_b64encode(master_key)
    return Fernet(master_key_b64)


def generate_site_dek() -> bytes:
    """Generate a random 32-byte DEK for a site"""
    return os.urandom(32)


def wrap_dek(dek: bytes) -> str:
    """Wrap (encrypt) a DEK using MASTER_KEY"""
    fernet = get_master_fernet()
    wrapped = fernet.encrypt(dek)
    return base64.b64encode(wrapped).decode('utf-8')


def unwrap_dek(wrapped_dek_b64: str) -> bytes:
    """Unwrap (decrypt) a DEK using MASTER_KEY"""
    fernet = get_master_fernet()
    wrapped = base64.b64decode(wrapped_dek_b64)
    return fernet.decrypt(wrapped)


def get_site_fernet(wrapped_dek_b64: str) -> Fernet:
    """Get Fernet instance for a site using its wrapped DEK"""
    dek = unwrap_dek(wrapped_dek_b64)
    dek_b64 = base64.urlsafe_b64encode(dek)
    return Fernet(dek_b64)


def encrypt_credential(wrapped_dek_b64: str, plaintext: str) -> str:
    """Encrypt credential using site's DEK, returns ENC: prefixed string"""
    fernet = get_site_fernet(wrapped_dek_b64)
    encrypted = fernet.encrypt(plaintext.encode('utf-8'))
    return "ENC:" + base64.b64encode(encrypted).decode('utf-8')


def decrypt_credential(wrapped_dek_b64: str, ciphertext: str) -> str:
    """Decrypt credential using site's DEK"""
    if not ciphertext.startswith("ENC:"):
        raise ValueError("Invalid ciphertext format - expected ENC: prefix")
    
    encrypted_b64 = ciphertext[4:]  # Remove "ENC:" prefix
    encrypted = base64.b64decode(encrypted_b64)
    fernet = get_site_fernet(wrapped_dek_b64)
    return fernet.decrypt(encrypted).decode('utf-8')


def compute_fingerprint(data: str) -> str:
    """Compute SHA-256 fingerprint of credential data (truncated to 16 chars)"""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()[:16]
