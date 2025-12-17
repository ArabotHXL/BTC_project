#!/usr/bin/env python3
"""
Edge Collector Device Keypair Module

Handles X25519 key pair generation, encrypted storage, and Sealed Box operations
for the Device Envelope Encryption system.

Architecture:
    - Each Edge Collector generates a unique X25519 key pair
    - Private key is encrypted locally with a passphrase (PBKDF2 + AES-256-GCM)
    - Public key is registered with the cloud server
    - Browser uses Sealed Box to encrypt DEK (Data Encryption Key)
    - Edge Collector unwraps DEK using its private key

Usage:
    from device_keypair import DeviceKeypair, KeypairManager
    
    # First time setup
    manager = KeypairManager('/path/to/keystore')
    keypair = manager.generate_and_save('my-device', passphrase='secure-pass')
    print(f"Public key: {keypair.public_key_base64}")
    
    # Load existing keypair
    manager = KeypairManager('/path/to/keystore')
    keypair = manager.load('my-device', passphrase='secure-pass')
    
    # Unseal a sealed box from browser
    plaintext = keypair.unseal(sealed_box_base64)

Security:
    - Private key is NEVER stored in plaintext
    - Uses PBKDF2 with 100,000 iterations for key derivation
    - AES-256-GCM for authenticated encryption of private key
    - Salt and nonce are unique per key generation
"""

import base64
import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.encoding import Base64Encoder
from nacl.utils import random as nacl_random
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

KEYSTORE_VERSION = 1
PBKDF2_ITERATIONS = 100000
SALT_SIZE = 32
NONCE_SIZE = 12


class KeypairError(Exception):
    """Base exception for keypair operations"""
    pass


class KeypairNotFoundError(KeypairError):
    """Raised when keypair file doesn't exist"""
    pass


class KeypairDecryptionError(KeypairError):
    """Raised when passphrase is incorrect"""
    pass


class KeypairValidationError(KeypairError):
    """Raised when keypair data is invalid"""
    pass


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive AES-256 key from passphrase using PBKDF2"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(passphrase.encode('utf-8'))


def _encrypt_private_key(private_key_bytes: bytes, passphrase: str) -> Dict[str, str]:
    """
    Encrypt private key with passphrase
    
    Returns:
        Dict with salt, nonce, ciphertext (all base64)
    """
    salt = nacl_random(SALT_SIZE)
    nonce = nacl_random(NONCE_SIZE)
    
    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    
    ciphertext = aesgcm.encrypt(nonce, private_key_bytes, None)
    
    return {
        'salt': base64.b64encode(salt).decode('ascii'),
        'nonce': base64.b64encode(nonce).decode('ascii'),
        'ciphertext': base64.b64encode(ciphertext).decode('ascii'),
    }


def _decrypt_private_key(encrypted: Dict[str, str], passphrase: str) -> bytes:
    """
    Decrypt private key with passphrase
    
    Raises:
        KeypairDecryptionError: If passphrase is incorrect
    """
    try:
        salt = base64.b64decode(encrypted['salt'])
        nonce = base64.b64decode(encrypted['nonce'])
        ciphertext = base64.b64decode(encrypted['ciphertext'])
        
        key = _derive_key(passphrase, salt)
        aesgcm = AESGCM(key)
        
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise KeypairDecryptionError(f"Failed to decrypt private key: {e}")


class DeviceKeypair:
    """
    X25519 keypair for Edge Collector device
    
    Provides methods for:
    - Getting public key (for registration)
    - Unsealing sealed boxes from browser
    - Unwrapping DEK encrypted with sealed box
    """
    
    def __init__(self, private_key: PrivateKey, device_name: str, key_version: int = 1):
        self._private_key = private_key
        self._public_key = private_key.public_key
        self._sealed_box = SealedBox(self._private_key)
        self.device_name = device_name
        self.key_version = key_version
    
    @property
    def public_key_bytes(self) -> bytes:
        """Get raw public key bytes (32 bytes)"""
        return bytes(self._public_key)
    
    @property
    def public_key_base64(self) -> str:
        """Get public key as base64 string for API registration"""
        return base64.b64encode(self.public_key_bytes).decode('ascii')
    
    @property
    def private_key_bytes(self) -> bytes:
        """Get raw private key bytes (32 bytes)"""
        return bytes(self._private_key)
    
    def unseal(self, sealed_box_base64: str) -> bytes:
        """
        Unseal a sealed box encrypted by browser
        
        Args:
            sealed_box_base64: Base64 encoded sealed box ciphertext
            
        Returns:
            Decrypted plaintext bytes
        """
        sealed_bytes = base64.b64decode(sealed_box_base64)
        return self._sealed_box.decrypt(sealed_bytes)
    
    def unseal_to_string(self, sealed_box_base64: str) -> str:
        """Unseal and decode as UTF-8 string"""
        return self.unseal(sealed_box_base64).decode('utf-8')
    
    def unwrap_dek(self, wrapped_dek_base64: str) -> bytes:
        """
        Unwrap a DEK (Data Encryption Key) that was sealed by browser
        
        The DEK is typically a 32-byte AES-256 key used for encrypting
        miner credentials.
        
        Args:
            wrapped_dek_base64: Base64 sealed box containing the DEK
            
        Returns:
            32-byte DEK
        """
        dek = self.unseal(wrapped_dek_base64)
        if len(dek) != 32:
            logger.warning(f"DEK length is {len(dek)}, expected 32 bytes")
        return dek
    
    def decrypt_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt a full envelope from the cloud API
        
        The envelope contains:
        - wrapped_dek: Sealed box containing AES-256 DEK
        - encrypted_payload: AES-256-GCM ciphertext
        - nonce: Base64 12-byte nonce for AES-GCM
        - aad: Additional authenticated data (not encrypted)
        
        Args:
            envelope: Dict with wrapped_dek, encrypted_payload, nonce, aad
            
        Returns:
            Decrypted JSON payload (typically miner credentials)
        """
        wrapped_dek = envelope.get('wrapped_dek')
        encrypted_payload = envelope.get('encrypted_payload')
        nonce_b64 = envelope.get('nonce')
        
        if not all([wrapped_dek, encrypted_payload, nonce_b64]):
            raise ValueError("Envelope missing required fields: wrapped_dek, encrypted_payload, nonce")
        
        dek = self.unwrap_dek(wrapped_dek)
        
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(encrypted_payload)
        
        aesgcm = AESGCM(dek)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return json.loads(plaintext.decode('utf-8'))
    
    def decrypt_miner_secret(self, secret_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt miner secret from API response
        
        This is a convenience wrapper around decrypt_envelope that also
        extracts metadata from the response.
        
        Args:
            secret_data: API response from GET /api/edge/secrets or similar
            
        Returns:
            Dict with decrypted credentials and metadata:
            {
                'miner_id': 100,
                'ip_address': '192.168.1.10',
                'counter': 3,
                'credentials': {
                    'username': 'root',
                    'password': '...'
                }
            }
        """
        credentials = self.decrypt_envelope(secret_data)
        
        return {
            'miner_id': secret_data.get('miner_id'),
            'ip_address': secret_data.get('ip_address'),
            'miner_name': secret_data.get('miner_name'),
            'site_id': secret_data.get('site_id'),
            'counter': secret_data.get('counter'),
            'key_version': secret_data.get('key_version'),
            'credentials': credentials
        }
    
    @classmethod
    def generate(cls, device_name: str, key_version: int = 1) -> 'DeviceKeypair':
        """Generate a new random X25519 keypair"""
        private_key = PrivateKey.generate()
        logger.info(f"Generated new X25519 keypair for device: {device_name}")
        return cls(private_key, device_name, key_version)
    
    @classmethod
    def from_private_key_bytes(cls, private_key_bytes: bytes, 
                                device_name: str, key_version: int = 1) -> 'DeviceKeypair':
        """Reconstruct keypair from private key bytes"""
        private_key = PrivateKey(private_key_bytes)
        return cls(private_key, device_name, key_version)
    
    def __repr__(self):
        return f"<DeviceKeypair {self.device_name} v{self.key_version}>"


class KeypairManager:
    """
    Manages encrypted keypair storage on disk
    
    Each device has a JSON keystore file containing:
    - device_name: Unique device identifier
    - key_version: Incremented on key rotation
    - public_key: Base64 public key (for reference)
    - encrypted_private_key: PBKDF2+AES-GCM encrypted private key
    - created_at: Timestamp of creation
    - keystore_version: Schema version
    """
    
    def __init__(self, keystore_dir: Optional[str] = None):
        """
        Initialize manager with keystore directory
        
        Args:
            keystore_dir: Directory to store keystore files.
                         Defaults to ~/.edge_collector/keys
        """
        if keystore_dir is None:
            keystore_dir = os.path.expanduser('~/.edge_collector/keys')
        
        self.keystore_dir = Path(keystore_dir)
        self.keystore_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"KeypairManager initialized with keystore: {self.keystore_dir}")
    
    def _keystore_path(self, device_name: str) -> Path:
        """Get keystore file path for device"""
        safe_name = device_name.replace('/', '_').replace('\\', '_')
        return self.keystore_dir / f"{safe_name}.keystore.json"
    
    def exists(self, device_name: str) -> bool:
        """Check if keystore exists for device"""
        return self._keystore_path(device_name).exists()
    
    def generate_and_save(self, device_name: str, passphrase: str, 
                          key_version: int = 1) -> DeviceKeypair:
        """
        Generate new keypair and save to encrypted keystore
        
        Args:
            device_name: Unique device identifier
            passphrase: Passphrase to encrypt private key
            key_version: Key version number
            
        Returns:
            DeviceKeypair instance
        """
        keypair = DeviceKeypair.generate(device_name, key_version)
        self.save(keypair, passphrase)
        return keypair
    
    def save(self, keypair: DeviceKeypair, passphrase: str) -> None:
        """
        Save keypair to encrypted keystore file
        
        Args:
            keypair: DeviceKeypair to save
            passphrase: Passphrase to encrypt private key
        """
        encrypted = _encrypt_private_key(keypair.private_key_bytes, passphrase)
        
        keystore_data = {
            'keystore_version': KEYSTORE_VERSION,
            'device_name': keypair.device_name,
            'key_version': keypair.key_version,
            'public_key': keypair.public_key_base64,
            'encrypted_private_key': encrypted,
            'created_at': datetime.utcnow().isoformat(),
        }
        
        path = self._keystore_path(keypair.device_name)
        
        # Write atomically
        temp_path = path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(keystore_data, f, indent=2)
        temp_path.rename(path)
        
        # Set restrictive permissions (owner read/write only)
        os.chmod(path, 0o600)
        
        logger.info(f"Saved encrypted keystore: {path}")
    
    def load(self, device_name: str, passphrase: str) -> DeviceKeypair:
        """
        Load keypair from encrypted keystore
        
        Args:
            device_name: Device identifier
            passphrase: Passphrase to decrypt private key
            
        Returns:
            DeviceKeypair instance
            
        Raises:
            KeypairNotFoundError: If keystore doesn't exist
            KeypairDecryptionError: If passphrase is wrong
            KeypairValidationError: If keystore is corrupted
        """
        path = self._keystore_path(device_name)
        
        if not path.exists():
            raise KeypairNotFoundError(f"Keystore not found: {path}")
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise KeypairValidationError(f"Invalid keystore JSON: {e}")
        
        if data.get('keystore_version') != KEYSTORE_VERSION:
            raise KeypairValidationError(
                f"Unsupported keystore version: {data.get('keystore_version')}")
        
        try:
            private_key_bytes = _decrypt_private_key(
                data['encrypted_private_key'], passphrase)
        except KeypairDecryptionError:
            raise
        except KeyError as e:
            raise KeypairValidationError(f"Missing field in keystore: {e}")
        
        keypair = DeviceKeypair.from_private_key_bytes(
            private_key_bytes,
            data['device_name'],
            data.get('key_version', 1)
        )
        
        # Verify public key matches
        if keypair.public_key_base64 != data.get('public_key'):
            raise KeypairValidationError("Public key mismatch - keystore may be corrupted")
        
        logger.info(f"Loaded keypair for device: {device_name}")
        return keypair
    
    def load_or_generate(self, device_name: str, passphrase: str,
                         key_version: int = 1) -> Tuple[DeviceKeypair, bool]:
        """
        Load existing keypair or generate new one
        
        Args:
            device_name: Device identifier
            passphrase: Passphrase for encryption/decryption
            key_version: Version for new key if generating
            
        Returns:
            Tuple of (DeviceKeypair, was_generated)
        """
        if self.exists(device_name):
            keypair = self.load(device_name, passphrase)
            return keypair, False
        else:
            keypair = self.generate_and_save(device_name, passphrase, key_version)
            return keypair, True
    
    def delete(self, device_name: str) -> bool:
        """
        Delete keystore file
        
        Args:
            device_name: Device identifier
            
        Returns:
            True if deleted, False if didn't exist
        """
        path = self._keystore_path(device_name)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted keystore: {path}")
            return True
        return False
    
    def list_devices(self) -> list:
        """List all device names with keystores"""
        devices = []
        for path in self.keystore_dir.glob('*.keystore.json'):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    devices.append({
                        'device_name': data.get('device_name'),
                        'key_version': data.get('key_version'),
                        'public_key': data.get('public_key'),
                        'created_at': data.get('created_at'),
                    })
            except Exception as e:
                logger.warning(f"Could not read keystore {path}: {e}")
        return devices
    
    def rotate_key(self, device_name: str, old_passphrase: str, 
                   new_passphrase: Optional[str] = None) -> DeviceKeypair:
        """
        Rotate keypair (generate new key with incremented version)
        
        Args:
            device_name: Device identifier
            old_passphrase: Current passphrase
            new_passphrase: New passphrase (defaults to same as old)
            
        Returns:
            New DeviceKeypair
        """
        old_keypair = self.load(device_name, old_passphrase)
        new_version = old_keypair.key_version + 1
        
        if new_passphrase is None:
            new_passphrase = old_passphrase
        
        new_keypair = self.generate_and_save(device_name, new_passphrase, new_version)
        
        logger.info(f"Rotated key for {device_name}: v{old_keypair.key_version} -> v{new_version}")
        return new_keypair
    
    def get_public_key(self, device_name: str) -> Optional[str]:
        """
        Get public key without needing passphrase
        
        Args:
            device_name: Device identifier
            
        Returns:
            Base64 public key or None if not found
        """
        path = self._keystore_path(device_name)
        if not path.exists():
            return None
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data.get('public_key')
        except Exception:
            return None


# Singleton manager for convenience
_default_manager: Optional[KeypairManager] = None


def get_keypair_manager(keystore_dir: Optional[str] = None) -> KeypairManager:
    """Get default KeypairManager singleton"""
    global _default_manager
    if _default_manager is None or keystore_dir is not None:
        _default_manager = KeypairManager(keystore_dir)
    return _default_manager


if __name__ == '__main__':
    import sys
    import tempfile
    
    print("Edge Collector Device Keypair Test")
    print("=" * 50)
    
    # Use temp directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = KeypairManager(tmpdir)
        
        # Test generation
        print("\n1. Generating new keypair...")
        keypair = manager.generate_and_save('test-device', 'test-passphrase')
        print(f"   Device: {keypair.device_name}")
        print(f"   Version: {keypair.key_version}")
        print(f"   Public key: {keypair.public_key_base64[:32]}...")
        
        # Test loading
        print("\n2. Loading keypair...")
        loaded = manager.load('test-device', 'test-passphrase')
        assert loaded.public_key_base64 == keypair.public_key_base64
        print("   ✓ Loaded successfully, public key matches")
        
        # Test wrong passphrase
        print("\n3. Testing wrong passphrase...")
        try:
            manager.load('test-device', 'wrong-passphrase')
            print("   ✗ Should have failed!")
        except KeypairDecryptionError:
            print("   ✓ Correctly rejected wrong passphrase")
        
        # Test sealed box (self-test)
        print("\n4. Testing sealed box encryption/decryption...")
        from nacl.public import SealedBox as SenderBox
        
        # Simulate browser encrypting
        recipient_pubkey = PublicKey(base64.b64decode(keypair.public_key_base64))
        sender_box = SenderBox(recipient_pubkey)
        test_message = b"This is a test DEK: 32 bytes!!"
        sealed = sender_box.encrypt(test_message)
        sealed_b64 = base64.b64encode(sealed).decode('ascii')
        
        # Edge collector decrypting
        decrypted = keypair.unseal(sealed_b64)
        assert decrypted == test_message
        print(f"   ✓ Sealed box round-trip successful")
        print(f"   Original: {test_message}")
        print(f"   Decrypted: {decrypted}")
        
        # Test key rotation
        print("\n5. Testing key rotation...")
        new_keypair = manager.rotate_key('test-device', 'test-passphrase')
        assert new_keypair.key_version == 2
        assert new_keypair.public_key_base64 != keypair.public_key_base64
        print(f"   ✓ Key rotated to version {new_keypair.key_version}")
        print(f"   New public key: {new_keypair.public_key_base64[:32]}...")
        
        # List devices
        print("\n6. Listing devices...")
        devices = manager.list_devices()
        for d in devices:
            print(f"   - {d['device_name']} v{d['key_version']}")
        
        print("\n" + "=" * 50)
        print("All tests passed!")
