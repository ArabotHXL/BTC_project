#!/usr/bin/env python3
"""
Edge Collector E2EE (End-to-End Encryption) Module

Provides Python-side decryption for miner connection credentials
encrypted by the site owner using the Owner-Level Encryption feature.

=== Owner-Level Encryption (矿场主级加密) ===

Architecture:
    - Site owner sets ONE master passphrase for the entire site
    - All miners at the site are encrypted with this passphrase
    - Customers CANNOT see or modify encryption settings
    - Edge Collector uses the master passphrase to decrypt all miners

Algorithm: AES-256-GCM with PBKDF2 key derivation (100,000 iterations)
Compatible with: static/js/crypto_miner_e2ee.js

Usage:
    from crypto_e2ee import decrypt_credentials, decrypt_connection_full
    
    # Decrypt miner credentials using site master passphrase
    passphrase = os.environ.get('SITE_MASTER_PASSPHRASE')
    creds = decrypt_credentials(encrypted_block, passphrase)
    print(creds['username'], creds['password'])
    
    # Decrypt full connection info
    conn = decrypt_connection_full(encrypted_block, passphrase)
    print(conn['ip_address'], conn['port'], conn['username'])

Environment Variables:
    SITE_MASTER_PASSPHRASE - The site owner's master passphrase (required)
    
Security:
    - Passphrase should be provided at Edge Collector startup
    - Use environment variable SITE_MASTER_PASSPHRASE
    - Never log or store the passphrase in plain text
    - Only site owners (not customers) can set up encryption
"""

import base64
import json
import os
import logging
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

ALGO = 'AES-256-GCM'
VERSION = 1
PBKDF2_ITERATIONS = 100000


class E2EEDecryptionError(Exception):
    """Raised when decryption fails"""
    pass


class E2EEValidationError(Exception):
    """Raised when encrypted block validation fails"""
    pass


def validate_encrypted_block(block: Dict[str, Any]) -> None:
    """
    Validate encrypted block structure
    
    Args:
        block: Encrypted block dictionary
        
    Raises:
        E2EEValidationError: If block is invalid
    """
    if not block:
        raise E2EEValidationError("Encrypted block is None or empty")
    
    required_fields = ['ciphertext', 'iv', 'salt', 'algo', 'version']
    for field in required_fields:
        if field not in block:
            raise E2EEValidationError(f"Missing required field: {field}")
    
    if block.get('algo') != ALGO:
        raise E2EEValidationError(f"Unsupported algorithm: {block.get('algo')}. Expected: {ALGO}")
    
    if block.get('version') != VERSION:
        raise E2EEValidationError(f"Unsupported version: {block.get('version')}. Expected: {VERSION}")


def derive_key_from_passphrase(passphrase: str, salt_base64: str) -> bytes:
    """
    Derive AES-256 key from passphrase using PBKDF2
    
    Args:
        passphrase: User's encryption passphrase
        salt_base64: Base64 encoded salt
        
    Returns:
        32-byte derived key
    """
    salt = base64.b64decode(salt_base64)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    
    return kdf.derive(passphrase.encode('utf-8'))


def decrypt_object(block: Dict[str, Any], passphrase: str) -> Dict[str, Any]:
    """
    Decrypt an encrypted block back to object
    
    Args:
        block: Encrypted block {ciphertext, iv, salt, algo, version}
        passphrase: Decryption passphrase
        
    Returns:
        Decrypted object dictionary
        
    Raises:
        E2EEValidationError: If block format is invalid
        E2EEDecryptionError: If decryption fails (wrong passphrase or corrupted data)
    """
    validate_encrypted_block(block)
    
    try:
        key = derive_key_from_passphrase(passphrase, block['salt'])
        aesgcm = AESGCM(key)
        
        iv = base64.b64decode(block['iv'])
        ciphertext = base64.b64decode(block['ciphertext'])
        
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        return json.loads(plaintext.decode('utf-8'))
        
    except Exception as e:
        if isinstance(e, (E2EEValidationError, E2EEDecryptionError)):
            raise
        raise E2EEDecryptionError(f"Decryption failed: {str(e)}")


def decrypt_credentials(block: Dict[str, Any], passphrase: str) -> Dict[str, str]:
    """
    Decrypt miner credentials
    
    Args:
        block: Encrypted credentials block
        passphrase: Site master passphrase
        
    Returns:
        Dictionary with username, password, pool_password
    """
    return decrypt_object(block, passphrase)


def decrypt_connection_full(block: Dict[str, Any], passphrase: str) -> Dict[str, Any]:
    """
    Decrypt full miner connection info
    
    Args:
        block: Encrypted connection block
        passphrase: Site master passphrase
        
    Returns:
        Dictionary with ip_address, port, username, password, pool_url, pool_user, pool_password
    """
    return decrypt_object(block, passphrase)


def get_passphrase_from_env() -> Optional[str]:
    """
    Get E2EE passphrase from environment variable
    
    Returns:
        Passphrase string or None if not set
    """
    return os.environ.get('SITE_MASTER_PASSPHRASE')


def prompt_passphrase() -> str:
    """
    Prompt user for passphrase interactively
    
    Returns:
        Passphrase string
    """
    import getpass
    return getpass.getpass("Enter E2EE passphrase for miner connections: ")


class E2EEManager:
    """
    Manager class for E2EE operations in Edge Collector
    
    Usage:
        manager = E2EEManager()
        manager.initialize()  # Get passphrase from env or prompt
        
        # For each miner
        if miner.use_full_e2ee:
            conn = manager.decrypt_connection_full(miner.encrypted_connection_full)
            ip, port = conn['ip_address'], conn['port']
        else:
            creds = manager.decrypt_credentials(miner.encrypted_credentials)
            username, password = creds['username'], creds['password']
    """
    
    def __init__(self):
        self._passphrase: Optional[str] = None
        self._initialized: bool = False
    
    def initialize(self, passphrase: Optional[str] = None) -> bool:
        """
        Initialize with passphrase
        
        Args:
            passphrase: Optional passphrase. If None, tries env var then prompts.
            
        Returns:
            True if initialized successfully
        """
        if passphrase:
            self._passphrase = passphrase
        else:
            self._passphrase = get_passphrase_from_env()
            
            if not self._passphrase:
                try:
                    self._passphrase = prompt_passphrase()
                except (EOFError, KeyboardInterrupt):
                    logger.warning("E2EE passphrase input cancelled")
                    return False
        
        if self._passphrase:
            self._initialized = True
            logger.info("E2EE Manager initialized successfully")
            return True
        
        return False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    def decrypt_credentials(self, block: Dict[str, Any]) -> Dict[str, str]:
        """Decrypt credentials using stored passphrase"""
        if not self._initialized or self._passphrase is None:
            raise E2EEDecryptionError("E2EE Manager not initialized. Call initialize() first.")
        return decrypt_credentials(block, self._passphrase)
    
    def decrypt_connection_full(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt full connection using stored passphrase"""
        if not self._initialized or self._passphrase is None:
            raise E2EEDecryptionError("E2EE Manager not initialized. Call initialize() first.")
        return decrypt_connection_full(block, self._passphrase)
    
    def get_miner_connection(self, miner_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get decrypted connection info for a miner
        
        Handles both credentials-only and full connection encryption modes.
        
        Args:
            miner_data: Miner data dict with encryption fields
            
        Returns:
            Connection info dict with at least: ip_address, port
            May also include: username, password, pool_url, pool_user, pool_password
        """
        if not self._initialized:
            raise E2EEDecryptionError("E2EE Manager not initialized. Call initialize() first.")
        
        use_full_e2ee = miner_data.get('use_full_e2ee', False)
        
        if use_full_e2ee:
            encrypted = miner_data.get('encrypted_connection_full')
            if not encrypted:
                raise E2EEDecryptionError("Full E2EE enabled but no encrypted_connection_full found")
            return self.decrypt_connection_full(encrypted)
        else:
            result = {
                'ip_address': miner_data.get('ip_address', ''),
                'port': miner_data.get('api_port', 4028),
            }
            
            encrypted = miner_data.get('encrypted_credentials')
            if encrypted:
                creds = self.decrypt_credentials(encrypted)
                result.update(creds)
            
            return result


_manager: Optional[E2EEManager] = None


def get_e2ee_manager() -> E2EEManager:
    """Get singleton E2EE Manager instance"""
    global _manager
    if _manager is None:
        _manager = E2EEManager()
    return _manager


if __name__ == '__main__':
    import sys
    
    print("E2EE Module Test")
    print("=" * 50)
    
    test_block = {
        "ciphertext": "dGVzdA==",
        "iv": "dGVzdGl2MTIzNDU2",
        "salt": "dGVzdHNhbHQxMjM0NTY3OA==",
        "algo": "AES-256-GCM",
        "version": 1
    }
    
    print("Validating encrypted block format...")
    try:
        validate_encrypted_block(test_block)
        print("✓ Block format is valid")
    except E2EEValidationError as e:
        print(f"✗ Validation error: {e}")
    
    print("\nTo test actual decryption:")
    print("1. Encrypt data in browser using MinerE2EE.encryptCredentials()")
    print("2. Pass the encrypted block and passphrase to decrypt_credentials()")
    print("")
    print("Example:")
    print("  from crypto_e2ee import decrypt_credentials")
    print("  result = decrypt_credentials(encrypted_block, 'your-passphrase')")
