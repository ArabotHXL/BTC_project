"""
Credential Protection Service - Mode 1/2/3 Implementation
Handles storage, retrieval, display, and migration of credentials
"""
import json
import base64
import hashlib
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from .envelope_kms_service import (
    generate_site_dek, wrap_dek, encrypt_credential, 
    decrypt_credential, compute_fingerprint
)

SENSITIVE_KEYS = ['password', 'secret', 'api_password', 'api_key', 'token', 'credential']


def mask_ip(ip: str) -> str:
    """Mask IP address for display: 192.168.1.100 -> 192.168.xxx.xxx"""
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.xxx.xxx"
    return "xxx.xxx.xxx.xxx"


def mask_sensitive_value(value: str) -> str:
    """Mask sensitive value with asterisks"""
    if len(value) <= 2:
        return "***"
    return value[0] + "*" * (len(value) - 2) + value[-1]


def mask_credential_for_display(credential_json: str, is_admin: bool = False) -> Dict:
    """
    Mode 1 display masking - mask sensitive fields for viewers
    Admins still see masked in list view, but can reveal
    """
    try:
        cred = json.loads(credential_json)
    except:
        return {"error": "Invalid credential format"}
    
    masked = {}
    for key, value in cred.items():
        if key == 'ip':
            masked[key] = mask_ip(str(value))
        elif any(s in key.lower() for s in SENSITIVE_KEYS):
            masked[key] = "***"
        else:
            masked[key] = value
    
    return masked


def get_display_credential(
    credential_value: str,
    credential_mode: int,
    is_admin: bool = False
) -> Dict:
    """
    Get display-safe credential based on mode
    """
    if not credential_value:
        return {"status": "No credential"}
    
    if credential_mode == 1:
        return mask_credential_for_display(credential_value, is_admin)
    elif credential_mode == 2:
        return {"status": "[Server Encrypted]", "mode": 2}
    elif credential_mode == 3:
        return {"status": "[E2EE Protected]", "mode": 3}
    else:
        return {"status": "Unknown mode"}


def store_credential_mode1(credential_json: str) -> Tuple[str, int, str]:
    """Store credential in Mode 1 (plaintext with UI masking)"""
    fingerprint = compute_fingerprint(credential_json)
    return credential_json, 1, fingerprint


def store_credential_mode2(credential_json: str, site_dek_wrapped: str) -> Tuple[str, int, str]:
    """Store credential in Mode 2 (Server Envelope Encryption)"""
    fingerprint = compute_fingerprint(credential_json)
    encrypted = encrypt_credential(site_dek_wrapped, credential_json)
    return encrypted, 2, fingerprint


def store_credential_mode3(e2ee_ciphertext: str, counter: int) -> Tuple[str, int, str]:
    """
    Store credential in Mode 3 (Device E2EE)
    Server never sees plaintext - only stores the sealed box from client
    """
    if not e2ee_ciphertext.startswith("E2EE:"):
        e2ee_ciphertext = "E2EE:" + e2ee_ciphertext
    
    fingerprint = hashlib.sha256(e2ee_ciphertext.encode()).hexdigest()[:16]
    return e2ee_ciphertext, 3, fingerprint


def reveal_credential_mode1(credential_value: str) -> Dict:
    """Reveal Mode 1 credential (already plaintext)"""
    try:
        return json.loads(credential_value)
    except:
        return {"error": "Invalid credential format", "raw": credential_value}


def reveal_credential_mode2(credential_value: str, site_dek_wrapped: str) -> Dict:
    """Reveal Mode 2 credential (decrypt using site DEK)"""
    try:
        plaintext = decrypt_credential(site_dek_wrapped, credential_value)
        return json.loads(plaintext)
    except Exception as e:
        return {"error": f"Decryption failed: {str(e)}"}


def reveal_credential_mode3() -> Dict:
    """Mode 3 credentials cannot be revealed by server"""
    return {
        "error": "Server cannot reveal E2EE credentials",
        "hint": "Use Edge device decrypt endpoint with device_token"
    }


def validate_anti_rollback(last_accepted_counter: int, new_counter: int) -> Tuple[bool, str]:
    """Validate anti-rollback counter"""
    if new_counter <= last_accepted_counter:
        return False, f"Anti-rollback reject: counter {new_counter} <= last_accepted {last_accepted_counter}"
    return True, "OK"


def migrate_credential(
    credential_value: str,
    from_mode: int,
    to_mode: int,
    site_dek_wrapped: Optional[str] = None,
    e2ee_ciphertext: Optional[str] = None,
    counter: int = 1
) -> Tuple[Optional[str], int, Optional[str], str]:
    """
    Migrate credential between modes.
    
    Returns: (new_value, new_mode, new_fingerprint, message)
    """
    if from_mode == 3:
        return None, from_mode, None, "Cannot migrate from E2EE without Edge device - requires Edge export flow"
    
    if from_mode == to_mode:
        return None, from_mode, None, "Already in target mode"
    
    if from_mode == 1:
        plaintext = credential_value
    elif from_mode == 2:
        if not site_dek_wrapped:
            return None, from_mode, None, "Missing site DEK for Mode 2 decryption"
        plaintext = decrypt_credential(site_dek_wrapped, credential_value)
    else:
        return None, from_mode, None, f"Unknown source mode: {from_mode}"
    
    if to_mode == 1:
        new_value, new_mode, fingerprint = store_credential_mode1(plaintext)
    elif to_mode == 2:
        if not site_dek_wrapped:
            return None, from_mode, None, "Missing site DEK for Mode 2 encryption"
        new_value, new_mode, fingerprint = store_credential_mode2(plaintext, site_dek_wrapped)
    elif to_mode == 3:
        if not e2ee_ciphertext:
            return None, from_mode, None, "Mode 3 requires client-side E2EE encryption"
        new_value, new_mode, fingerprint = store_credential_mode3(e2ee_ciphertext, counter)
    else:
        return None, from_mode, None, f"Unknown target mode: {to_mode}"
    
    return new_value, new_mode, fingerprint, "Migration successful"
