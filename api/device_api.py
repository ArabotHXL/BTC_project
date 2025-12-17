"""
Edge Device Management API
设备信封加密 - Device Envelope Encryption

Provides API endpoints for Edge Collector device registration,
public key management, and device lifecycle operations.

Endpoints:
    POST /api/devices/register - Register new edge device with public key
    GET /api/devices/<id>/pubkey - Get device public key for encryption
    GET /api/devices - List devices for tenant
    GET /api/devices/<id> - Get device details
    DELETE /api/devices/<id> - Delete device
    POST /api/devices/<id>/heartbeat - Device heartbeat (update last_seen)
"""

import logging
import secrets
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g, session
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, UserAccess, HostingSite, HostingMiner
from models_device_encryption import EdgeDevice, DeviceAuditEvent, MinerSecret, CapabilityLevel

logger = logging.getLogger(__name__)

device_bp = Blueprint('device', __name__, url_prefix='/api/devices')


def require_auth(f):
    """Decorator to require authentication via session or device token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import UserAccess
        
        # Check session-based authentication first
        user_id = session.get('user_id')
        if user_id and session.get('authenticated'):
            user = UserAccess.query.get(user_id)
            if user:
                g.auth_type = 'user'
                g.tenant_id = user.id
                g.actor_id = user.id
                return f(*args, **kwargs)
        
        # Check device token authentication
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            device = EdgeDevice.query.filter_by(device_token=token, status='ACTIVE').first()
            if device:
                g.auth_type = 'device'
                g.tenant_id = device.tenant_id
                g.device_id = device.id
                g.actor_id = None
                device.last_seen_at = datetime.utcnow()
                db.session.commit()
                return f(*args, **kwargs)
        
        return jsonify({'error': 'Authentication required'}), 401
    return decorated_function


def require_user_auth(f):
    """Decorator to require user authentication (not device token)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import UserAccess
        
        # Use session-based authentication (like auth.py login_required)
        user_id = session.get('user_id')
        if not user_id or not session.get('authenticated'):
            return jsonify({'error': 'User authentication required'}), 401
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        g.auth_type = 'user'
        g.tenant_id = user.id
        g.actor_id = user.id
        return f(*args, **kwargs)
    return decorated_function


def log_audit_event(event_type, device_id=None, miner_id=None, 
                    event_data=None, result='success', error_message=None):
    """Log an audit event for device operations"""
    try:
        DeviceAuditEvent.log(
            event_type=event_type,
            tenant_id=getattr(g, 'tenant_id', None),
            device_id=device_id,
            miner_id=miner_id,
            actor_id=getattr(g, 'actor_id', None),
            actor_type=getattr(g, 'auth_type', 'unknown'),
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:500] if request.user_agent else None,
            event_data=event_data,
            result=result,
            error_message=error_message
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")


@device_bp.route('/register', methods=['POST'])
@require_user_auth
def register_device():
    """
    Register a new edge device with its X25519 public key
    
    Request:
        {
            "device_name": "Site-A-Collector-1",
            "public_key": "base64-encoded-x25519-public-key",
            "site_id": 123  // optional
        }
    
    Response:
        {
            "success": true,
            "device": {
                "id": 1,
                "device_name": "Site-A-Collector-1",
                "device_token": "generated-bearer-token",
                "public_key": "...",
                "key_version": 1,
                "status": "ACTIVE"
            }
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        device_name = data.get('device_name', '').strip()
        public_key = data.get('public_key', '').strip()
        site_id = data.get('site_id')
        
        if not device_name:
            return jsonify({'error': 'device_name is required'}), 400
        
        if not public_key:
            return jsonify({'error': 'public_key is required'}), 400
        
        if len(device_name) > 200:
            return jsonify({'error': 'device_name too long (max 200 chars)'}), 400
        
        import base64
        try:
            pk_bytes = base64.b64decode(public_key)
            if len(pk_bytes) != 32:
                return jsonify({'error': 'public_key must be 32 bytes (X25519)'}), 400
        except Exception:
            return jsonify({'error': 'public_key must be valid base64'}), 400
        
        if site_id:
            # Verify site exists (access control is role-based, not ownership-based)
            site = HostingSite.query.get(site_id)
            if not site:
                return jsonify({'error': 'Invalid site_id'}), 400
        
        existing = EdgeDevice.query.filter_by(
            tenant_id=g.tenant_id,
            device_name=device_name,
            status='ACTIVE'
        ).first()
        if existing:
            return jsonify({'error': 'Device with this name already exists'}), 409
        
        device_token = secrets.token_urlsafe(48)
        
        device = EdgeDevice(
            tenant_id=g.tenant_id,
            site_id=site_id,
            device_name=device_name,
            device_token=device_token,
            public_key=public_key,
            key_version=1,
            status='ACTIVE',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(device)
        db.session.commit()
        
        log_audit_event(
            'DEVICE_REGISTERED',
            device_id=device.id,
            event_data={'device_name': device_name, 'site_id': site_id}
        )
        
        logger.info(f"Registered new device: {device_name} (id={device.id})")
        
        return jsonify({
            'success': True,
            'device': {
                'id': device.id,
                'device_name': device.device_name,
                'device_token': device_token,
                'public_key': device.public_key,
                'key_version': device.key_version,
                'status': device.status,
                'site_id': device.site_id,
                'created_at': device.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Device registration failed: {e}")
        log_audit_event('DEVICE_REGISTERED', result='error', error_message=str(e))
        return jsonify({'error': 'Registration failed'}), 500


@device_bp.route('/<int:device_id>/pubkey', methods=['GET'])
@require_auth
def get_device_pubkey(device_id):
    """
    Get device public key for encrypting secrets
    
    Returns:
        {
            "device_id": 1,
            "public_key": "base64-x25519-pubkey",
            "key_version": 1
        }
    """
    device = EdgeDevice.query.filter_by(
        id=device_id,
        tenant_id=g.tenant_id,
        status='ACTIVE'
    ).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    return jsonify({
        'device_id': device.id,
        'public_key': device.public_key,
        'key_version': device.key_version
    })


@device_bp.route('', methods=['GET'])
@require_user_auth
def list_devices():
    """
    List all devices for current tenant
    
    Query params:
        site_id: Filter by site
        status: Filter by status (ACTIVE, REVOKED, PENDING)
    
    Returns:
        {
            "devices": [...]
        }
    """
    query = EdgeDevice.query.filter_by(tenant_id=g.tenant_id)
    
    site_id = request.args.get('site_id', type=int)
    if site_id:
        query = query.filter_by(site_id=site_id)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status.upper())
    
    devices = query.order_by(EdgeDevice.created_at.desc()).all()
    
    return jsonify({
        'devices': [d.to_dict(include_pubkey=True) for d in devices]
    })


@device_bp.route('/<int:device_id>', methods=['GET'])
@require_auth
def get_device(device_id):
    """Get device details"""
    device = EdgeDevice.query.filter_by(
        id=device_id,
        tenant_id=g.tenant_id
    ).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    return jsonify({
        'device': device.to_dict(include_pubkey=True)
    })


@device_bp.route('/<int:device_id>', methods=['DELETE'])
@require_user_auth
def delete_device(device_id):
    """Delete a device (sets status to REVOKED)"""
    device = EdgeDevice.query.filter_by(
        id=device_id,
        tenant_id=g.tenant_id
    ).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    device.status = 'REVOKED'
    device.revoked_at = datetime.utcnow()
    device.revoked_by = g.actor_id
    device.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    log_audit_event('DEVICE_REVOKED', device_id=device.id)
    logger.info(f"Revoked device: {device.device_name} (id={device.id})")
    
    return jsonify({'success': True, 'message': 'Device revoked'})


@device_bp.route('/<int:device_id>/heartbeat', methods=['POST'])
@require_auth
def device_heartbeat(device_id):
    """
    Update device last_seen timestamp (called periodically by edge collector)
    """
    if getattr(g, 'auth_type', None) == 'device':
        if getattr(g, 'device_id', None) != device_id:
            return jsonify({'error': 'Token does not match device'}), 403
    
    device = EdgeDevice.query.filter_by(
        id=device_id,
        tenant_id=g.tenant_id,
        status='ACTIVE'
    ).first()
    
    if not device:
        return jsonify({'error': 'Device not found or not active'}), 404
    
    device.last_seen_at = datetime.utcnow()
    device.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'last_seen_at': device.last_seen_at.isoformat()
    })


@device_bp.route('/<int:device_id>/rotate-key', methods=['POST'])
@require_user_auth
def rotate_device_key(device_id):
    """
    Rotate device public key (for key compromise scenarios)
    
    Request:
        {
            "public_key": "new-base64-x25519-pubkey"
        }
    
    This increments key_version and invalidates all existing secrets
    encrypted with the old key.
    """
    device = EdgeDevice.query.filter_by(
        id=device_id,
        tenant_id=g.tenant_id,
        status='ACTIVE'
    ).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    data = request.get_json()
    if not data or not data.get('public_key'):
        return jsonify({'error': 'public_key is required'}), 400
    
    new_public_key = data['public_key'].strip()
    
    import base64
    try:
        pk_bytes = base64.b64decode(new_public_key)
        if len(pk_bytes) != 32:
            return jsonify({'error': 'public_key must be 32 bytes (X25519)'}), 400
    except Exception:
        return jsonify({'error': 'public_key must be valid base64'}), 400
    
    old_version = device.key_version
    device.public_key = new_public_key
    device.key_version = old_version + 1
    device.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    log_audit_event(
        'DEVICE_KEY_ROTATED',
        device_id=device.id,
        event_data={'old_version': old_version, 'new_version': device.key_version}
    )
    
    logger.info(f"Rotated key for device {device.device_name}: v{old_version} -> v{device.key_version}")
    
    return jsonify({
        'success': True,
        'device_id': device.id,
        'key_version': device.key_version,
        'message': f'Key rotated to version {device.key_version}. All secrets encrypted with v{old_version} need re-encryption.'
    })


@device_bp.route('/by-site/<int:site_id>', methods=['GET'])
@require_user_auth
def get_devices_by_site(site_id):
    """Get all active devices for a specific site"""
    site = HostingSite.query.filter_by(id=site_id).first()
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    devices = EdgeDevice.query.filter_by(
        site_id=site_id,
        status='ACTIVE'
    ).order_by(EdgeDevice.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'site_id': site_id,
        'devices': [d.to_dict(include_pubkey=True) for d in devices]
    })


miner_secrets_bp = Blueprint('miner_secrets', __name__, url_prefix='/api/miners')


@miner_secrets_bp.route('/<int:miner_id>/secrets', methods=['POST'])
@require_user_auth
def upload_miner_secret(miner_id):
    """
    Upload encrypted miner credentials (envelope encryption)
    
    Request:
        {
            "device_id": 1,
            "encrypted_payload": "base64-aes-gcm-ciphertext",
            "wrapped_dek": "base64-sealed-box",
            "nonce": "base64-nonce",
            "aad": {
                "schema_version": 1,
                "key_version": 1,
                "created_at": "2025-01-01T00:00:00Z"
            },
            "key_version": 1
        }
    
    Response:
        {
            "success": true,
            "secret": {
                "id": 1,
                "miner_id": 100,
                "device_id": 1,
                "counter": 1,
                "key_version": 1
            }
        }
    
    Security:
        - Counter must be strictly increasing (anti-rollback)
        - Miner must belong to the tenant
        - Device must be active and belong to the tenant
    """
    try:
        miner = HostingMiner.query.filter_by(id=miner_id).first()
        if not miner:
            return jsonify({'error': 'Miner not found'}), 404
        
        site = HostingSite.query.filter_by(id=miner.site_id, user_id=g.tenant_id).first()
        if not site:
            return jsonify({'error': 'Miner not owned by you'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        device_id = data.get('device_id')
        encrypted_payload = data.get('encrypted_payload', '').strip()
        wrapped_dek = data.get('wrapped_dek', '').strip()
        nonce = data.get('nonce', '').strip()
        aad = data.get('aad', {})
        key_version = data.get('key_version', 1)
        
        if not device_id:
            return jsonify({'error': 'device_id is required'}), 400
        if not encrypted_payload:
            return jsonify({'error': 'encrypted_payload is required'}), 400
        if not wrapped_dek:
            return jsonify({'error': 'wrapped_dek is required'}), 400
        if not nonce:
            return jsonify({'error': 'nonce is required'}), 400
        
        device = EdgeDevice.query.filter_by(
            id=device_id,
            tenant_id=g.tenant_id,
            status='ACTIVE'
        ).first()
        if not device:
            return jsonify({'error': 'Device not found or not active'}), 404
        
        if key_version != device.key_version:
            return jsonify({
                'error': 'Key version mismatch',
                'expected_key_version': device.key_version,
                'provided_key_version': key_version
            }), 400
        
        existing_secret = MinerSecret.query.filter_by(
            miner_id=miner_id,
            device_id=device_id
        ).first()
        
        if existing_secret:
            new_counter = existing_secret.counter + 1
            
            existing_secret.encrypted_payload = encrypted_payload
            existing_secret.wrapped_dek = wrapped_dek
            existing_secret.nonce = nonce
            existing_secret.aad = aad
            existing_secret.counter = new_counter
            existing_secret.key_version = key_version
            existing_secret.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            log_audit_event(
                'SECRET_UPDATED',
                device_id=device_id,
                miner_id=miner_id,
                event_data={'counter': new_counter, 'key_version': key_version}
            )
            
            logger.info(f"Updated secret for miner {miner_id} on device {device_id}, counter={new_counter}")
            
            return jsonify({
                'success': True,
                'secret': existing_secret.to_dict(include_encrypted=False)
            })
        
        new_secret = MinerSecret(
            tenant_id=g.tenant_id,
            device_id=device_id,
            miner_id=miner_id,
            encrypted_payload=encrypted_payload,
            wrapped_dek=wrapped_dek,
            nonce=nonce,
            aad=aad,
            counter=1,
            schema_version=aad.get('schema_version', 1),
            key_version=key_version,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(new_secret)
        db.session.commit()
        
        log_audit_event(
            'SECRET_CREATED',
            device_id=device_id,
            miner_id=miner_id,
            event_data={'counter': 1, 'key_version': key_version}
        )
        
        logger.info(f"Created secret for miner {miner_id} on device {device_id}")
        
        return jsonify({
            'success': True,
            'secret': new_secret.to_dict(include_encrypted=False)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Secret upload failed: {e}")
        log_audit_event(
            'SECRET_UPLOAD_FAILED',
            miner_id=miner_id,
            result='error',
            error_message=str(e)
        )
        return jsonify({'error': 'Secret upload failed'}), 500


@miner_secrets_bp.route('/<int:miner_id>/secrets', methods=['GET'])
@require_auth
def get_miner_secrets(miner_id):
    """
    Get encrypted secrets for a miner
    
    For user auth: Returns all secrets for the miner
    For device auth: Returns only secrets encrypted for that device
    """
    miner = HostingMiner.query.filter_by(id=miner_id).first()
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    site = HostingSite.query.filter_by(id=miner.site_id, user_id=g.tenant_id).first()
    if not site:
        return jsonify({'error': 'Miner not owned by you'}), 403
    
    if getattr(g, 'auth_type', None) == 'device':
        secrets = MinerSecret.query.filter_by(
            miner_id=miner_id,
            device_id=g.device_id
        ).all()
    else:
        secrets = MinerSecret.query.filter_by(miner_id=miner_id).all()
    
    return jsonify({
        'miner_id': miner_id,
        'secrets': [s.to_dict(include_encrypted=True) for s in secrets]
    })


@miner_secrets_bp.route('/<int:miner_id>/secrets/<int:device_id>', methods=['DELETE'])
@require_user_auth
def delete_miner_secret(miner_id, device_id):
    """Delete encrypted secret for a specific miner/device pair"""
    miner = HostingMiner.query.filter_by(id=miner_id).first()
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    site = HostingSite.query.filter_by(id=miner.site_id, user_id=g.tenant_id).first()
    if not site:
        return jsonify({'error': 'Miner not owned by you'}), 403
    
    secret = MinerSecret.query.filter_by(
        miner_id=miner_id,
        device_id=device_id,
        tenant_id=g.tenant_id
    ).first()
    
    if not secret:
        return jsonify({'error': 'Secret not found'}), 404
    
    db.session.delete(secret)
    db.session.commit()
    
    log_audit_event(
        'SECRET_DELETED',
        device_id=device_id,
        miner_id=miner_id
    )
    
    logger.info(f"Deleted secret for miner {miner_id} on device {device_id}")
    
    return jsonify({'success': True, 'message': 'Secret deleted'})


@miner_secrets_bp.route('/<int:miner_id>/capability', methods=['GET'])
@require_user_auth
def get_miner_capability(miner_id):
    """
    Get miner capability level and bound device
    
    Response:
        {
            "miner_id": 100,
            "capability_level": 3,
            "capability_name": "CONTROL",
            "bound_device_id": 1
        }
    """
    miner = HostingMiner.query.filter_by(id=miner_id).first()
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    site = HostingSite.query.filter_by(id=miner.site_id, user_id=g.tenant_id).first()
    if not site:
        return jsonify({'error': 'Miner not owned by you'}), 403
    
    level = miner.capability_level or 1
    level_names = {1: 'DISCOVERY', 2: 'TELEMETRY', 3: 'CONTROL'}
    
    return jsonify({
        'miner_id': miner_id,
        'capability_level': level,
        'capability_name': level_names.get(level, 'UNKNOWN'),
        'bound_device_id': miner.bound_device_id
    })


@miner_secrets_bp.route('/<int:miner_id>/capability', methods=['PUT'])
@require_user_auth
def update_miner_capability(miner_id):
    """
    Update miner capability level and/or bound device
    
    Request:
        {
            "capability_level": 3,  // 1=DISCOVERY, 2=TELEMETRY, 3=CONTROL
            "bound_device_id": 1    // optional - bind miner to specific device
        }
    
    Response:
        {
            "success": true,
            "miner_id": 100,
            "capability_level": 3,
            "capability_name": "CONTROL",
            "bound_device_id": 1
        }
    
    Notes:
        - Level 3 (CONTROL) requires encrypted credentials via /secrets endpoint
        - Bound device restricts credential access to a single Edge Collector
    """
    miner = HostingMiner.query.filter_by(id=miner_id).first()
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    site = HostingSite.query.filter_by(id=miner.site_id, user_id=g.tenant_id).first()
    if not site:
        return jsonify({'error': 'Miner not owned by you'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    
    old_level = miner.capability_level or 1
    old_device = miner.bound_device_id
    
    if 'capability_level' in data:
        level = data['capability_level']
        if not isinstance(level, int) or level not in [1, 2, 3]:
            return jsonify({
                'error': 'capability_level must be 1, 2, or 3',
                'level_names': {1: 'DISCOVERY', 2: 'TELEMETRY', 3: 'CONTROL'}
            }), 400
        miner.capability_level = level
    
    if 'bound_device_id' in data:
        device_id = data['bound_device_id']
        if device_id is not None:
            device = EdgeDevice.query.filter_by(
                id=device_id,
                tenant_id=g.tenant_id,
                status='ACTIVE'
            ).first()
            if not device:
                return jsonify({'error': 'Device not found or not active'}), 404
        miner.bound_device_id = device_id
    
    miner.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_audit_event(
        'CAPABILITY_UPDATED',
        miner_id=miner_id,
        event_data={
            'old_level': old_level,
            'new_level': miner.capability_level,
            'old_device': old_device,
            'new_device': miner.bound_device_id
        }
    )
    
    level_names = {1: 'DISCOVERY', 2: 'TELEMETRY', 3: 'CONTROL'}
    
    logger.info(f"Updated capability for miner {miner_id}: level {old_level}->{miner.capability_level}")
    
    return jsonify({
        'success': True,
        'miner_id': miner_id,
        'capability_level': miner.capability_level,
        'capability_name': level_names.get(miner.capability_level, 'UNKNOWN'),
        'bound_device_id': miner.bound_device_id
    })


@miner_secrets_bp.route('/batch-capability', methods=['PUT'])
@require_user_auth
def batch_update_capability():
    """
    Batch update capability levels for multiple miners
    
    Request:
        {
            "miner_ids": [100, 101, 102],
            "capability_level": 2,
            "bound_device_id": 1  // optional
        }
    
    Response:
        {
            "success": true,
            "updated": 3,
            "failed": 0
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    
    miner_ids = data.get('miner_ids', [])
    capability_level = data.get('capability_level')
    bound_device_id = data.get('bound_device_id')
    
    if not miner_ids or not isinstance(miner_ids, list):
        return jsonify({'error': 'miner_ids must be a non-empty array'}), 400
    
    if capability_level is not None:
        if not isinstance(capability_level, int) or capability_level not in [1, 2, 3]:
            return jsonify({'error': 'capability_level must be 1, 2, or 3'}), 400
    
    if bound_device_id is not None:
        device = EdgeDevice.query.filter_by(
            id=bound_device_id,
            tenant_id=g.tenant_id,
            status='ACTIVE'
        ).first()
        if not device:
            return jsonify({'error': 'Device not found or not active'}), 404
    
    updated = 0
    failed = 0
    
    for mid in miner_ids:
        miner = HostingMiner.query.filter_by(id=mid).first()
        if not miner:
            failed += 1
            continue
        
        site = HostingSite.query.filter_by(id=miner.site_id, user_id=g.tenant_id).first()
        if not site:
            failed += 1
            continue
        
        if capability_level is not None:
            miner.capability_level = capability_level
        if bound_device_id is not None:
            miner.bound_device_id = bound_device_id
        miner.updated_at = datetime.utcnow()
        updated += 1
    
    db.session.commit()
    
    log_audit_event(
        'BATCH_CAPABILITY_UPDATED',
        event_data={
            'miner_count': len(miner_ids),
            'updated': updated,
            'failed': failed,
            'capability_level': capability_level,
            'bound_device_id': bound_device_id
        }
    )
    
    return jsonify({
        'success': True,
        'updated': updated,
        'failed': failed
    })


edge_secrets_bp = Blueprint('edge_secrets', __name__, url_prefix='/api/edge')


def require_device_auth(f):
    """Decorator to require device token authentication only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Device token required'}), 401
        
        token = auth_header[7:]
        device = EdgeDevice.query.filter_by(device_token=token, status='ACTIVE').first()
        if not device:
            return jsonify({'error': 'Invalid or revoked device token'}), 401
        
        g.auth_type = 'device'
        g.tenant_id = device.tenant_id
        g.device_id = device.id
        g.device = device
        device.last_seen_at = datetime.utcnow()
        db.session.commit()
        return f(*args, **kwargs)
    return decorated_function


def require_capability(min_level):
    """
    Decorator factory for capability level checking
    
    Capability Levels:
        Level 1 (DISCOVERY): Read-only discovery - can view miner list/status
        Level 2 (TELEMETRY): Read telemetry data - can access performance metrics
        Level 3 (CONTROL): Full control - can access credentials and control miners
    
    Usage:
        @require_capability(CapabilityLevel.TELEMETRY.value)
        def my_endpoint(miner_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            miner_id = kwargs.get('miner_id') or request.args.get('miner_id', type=int)
            
            if miner_id:
                miner = HostingMiner.query.get(miner_id)
                if miner:
                    miner_level = miner.capability_level or 1
                    if miner_level < min_level:
                        log_audit_event(
                            'CAPABILITY_DENIED',
                            device_id=getattr(g, 'device_id', None),
                            miner_id=miner_id,
                            event_data={
                                'required_level': min_level,
                                'miner_level': miner_level
                            },
                            result='denied'
                        )
                        return jsonify({
                            'error': 'Capability level insufficient',
                            'required_level': min_level,
                            'miner_level': miner_level,
                            'level_names': {
                                1: 'DISCOVERY',
                                2: 'TELEMETRY',
                                3: 'CONTROL'
                            }
                        }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_miner_capability(miner_id, min_level):
    """
    Helper function to check miner capability level
    
    Returns:
        tuple: (is_allowed, miner_level, error_response)
    """
    miner = HostingMiner.query.get(miner_id)
    if not miner:
        return False, None, jsonify({'error': 'Miner not found'}), 404
    
    miner_level = miner.capability_level or 1
    if miner_level < min_level:
        return False, miner_level, jsonify({
            'error': 'Capability level insufficient',
            'required_level': min_level,
            'miner_level': miner_level
        }), 403
    
    return True, miner_level, None, None


@edge_secrets_bp.route('/secrets', methods=['GET'])
@require_device_auth
def get_edge_secrets():
    """
    Get all encrypted secrets assigned to this edge device
    
    This is the primary endpoint for Edge Collectors to pull their miner credentials.
    The device uses its private key to unseal the wrapped DEK, then uses the DEK
    to decrypt the AES-256-GCM encrypted payload.
    
    Query params:
        since_counter: Only return secrets with counter > this value (for incremental sync)
        site_id: Filter by site (optional)
    
    Response:
        {
            "device_id": 1,
            "key_version": 1,
            "secrets": [
                {
                    "miner_id": 100,
                    "ip_address": "192.168.1.10",  // from miner record
                    "encrypted_payload": "...",
                    "wrapped_dek": "...",
                    "nonce": "...",
                    "aad": {...},
                    "counter": 3,
                    "key_version": 1
                }
            ],
            "total": 5
        }
    """
    device = g.device
    
    query = MinerSecret.query.filter_by(device_id=device.id)
    
    since_counter = request.args.get('since_counter', type=int)
    if since_counter is not None:
        query = query.filter(MinerSecret.counter > since_counter)
    
    site_id = request.args.get('site_id', type=int)
    if site_id:
        query = query.join(HostingMiner).filter(HostingMiner.site_id == site_id)
    
    secrets = query.all()
    
    result_secrets = []
    skipped_capability = 0
    skipped_bound = 0
    
    for secret in secrets:
        miner = HostingMiner.query.get(secret.miner_id)
        if not miner:
            continue
        
        miner_level = miner.capability_level or 1
        if miner_level < CapabilityLevel.CONTROL.value:
            skipped_capability += 1
            continue
        
        if miner.bound_device_id and miner.bound_device_id != device.id:
            skipped_bound += 1
            continue
        
        secret_data = secret.to_dict(include_encrypted=True)
        secret_data['ip_address'] = miner.ip_address
        secret_data['serial_number'] = miner.serial_number
        secret_data['site_id'] = miner.site_id
        secret_data['capability_level'] = miner_level
        result_secrets.append(secret_data)
    
    log_audit_event(
        'SECRETS_PULLED',
        device_id=device.id,
        event_data={
            'count': len(result_secrets),
            'since_counter': since_counter,
            'site_id': site_id,
            'skipped_capability': skipped_capability,
            'skipped_bound': skipped_bound
        }
    )
    
    return jsonify({
        'device_id': device.id,
        'key_version': device.key_version,
        'secrets': result_secrets,
        'total': len(result_secrets)
    })


@edge_secrets_bp.route('/secrets/<int:miner_id>', methods=['GET'])
@require_device_auth
def get_edge_secret_for_miner(miner_id):
    """
    Get encrypted secret for a specific miner
    
    Requires miner capability_level >= 3 (CONTROL)
    Respects bound_device_id restriction
    
    Response:
        {
            "miner_id": 100,
            "encrypted_payload": "...",
            "wrapped_dek": "...",
            "nonce": "...",
            "aad": {...},
            "counter": 3,
            "key_version": 1
        }
    """
    device = g.device
    
    miner = HostingMiner.query.get(miner_id)
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    miner_level = miner.capability_level or 1
    if miner_level < CapabilityLevel.CONTROL.value:
        log_audit_event(
            'CAPABILITY_DENIED',
            device_id=device.id,
            miner_id=miner_id,
            event_data={
                'required_level': CapabilityLevel.CONTROL.value,
                'miner_level': miner_level
            },
            result='denied'
        )
        return jsonify({
            'error': 'Capability level insufficient',
            'required_level': CapabilityLevel.CONTROL.value,
            'miner_level': miner_level,
            'message': 'Miner must be set to CONTROL level (3) to access credentials'
        }), 403
    
    if miner.bound_device_id and miner.bound_device_id != device.id:
        log_audit_event(
            'BOUND_DEVICE_DENIED',
            device_id=device.id,
            miner_id=miner_id,
            event_data={
                'bound_device_id': miner.bound_device_id,
                'requesting_device_id': device.id
            },
            result='denied'
        )
        return jsonify({
            'error': 'Miner bound to different device',
            'message': 'This miner is restricted to a specific Edge Collector'
        }), 403
    
    secret = MinerSecret.query.filter_by(
        device_id=device.id,
        miner_id=miner_id
    ).first()
    
    if not secret:
        return jsonify({'error': 'Secret not found for this miner'}), 404
    
    secret_data = secret.to_dict(include_encrypted=True)
    secret_data['ip_address'] = miner.ip_address
    secret_data['serial_number'] = miner.serial_number
    secret_data['capability_level'] = miner_level
    
    log_audit_event(
        'SECRET_PULLED',
        device_id=device.id,
        miner_id=miner_id,
        event_data={'counter': secret.counter, 'capability_level': miner_level}
    )
    
    return jsonify(secret_data)


@edge_secrets_bp.route('/status', methods=['GET'])
@require_device_auth
def get_edge_status():
    """
    Get edge device status and key information
    
    Used by Edge Collector to verify its registration and get current key version.
    If key_version changed, the device knows it needs to re-register with a new keypair.
    
    Response:
        {
            "device_id": 1,
            "device_name": "Site-A-Collector",
            "status": "ACTIVE",
            "key_version": 1,
            "secret_count": 10,
            "last_seen_at": "..."
        }
    """
    device = g.device
    
    secret_count = MinerSecret.query.filter_by(device_id=device.id).count()
    
    return jsonify({
        'device_id': device.id,
        'device_name': device.device_name,
        'site_id': device.site_id,
        'status': device.status,
        'key_version': device.key_version,
        'secret_count': secret_count,
        'last_seen_at': device.last_seen_at.isoformat() if device.last_seen_at else None
    })


@edge_secrets_bp.route('/ack', methods=['POST'])
@require_device_auth
def ack_secrets():
    """
    Acknowledge successful decryption of secrets (for auditing)
    
    Request:
        {
            "miner_ids": [100, 101, 102],
            "status": "decrypted"  // or "failed"
        }
    
    This is optional but helps with security auditing - the server can
    track which secrets were successfully decrypted by the device.
    """
    device = g.device
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    
    miner_ids = data.get('miner_ids', [])
    status = data.get('status', 'decrypted')
    
    if not isinstance(miner_ids, list):
        return jsonify({'error': 'miner_ids must be an array'}), 400
    
    log_audit_event(
        'SECRETS_ACK',
        device_id=device.id,
        event_data={
            'miner_ids': miner_ids,
            'status': status,
            'count': len(miner_ids)
        }
    )
    
    logger.info(f"Device {device.id} acked {len(miner_ids)} secrets with status={status}")
    
    return jsonify({
        'success': True,
        'acknowledged': len(miner_ids)
    })


audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit')

SENSITIVE_KEYS = {'password', 'secret', 'token', 'credential', 'key', 'private'}

def redact_sensitive_data(data):
    """Redact sensitive fields from audit event data"""
    if data is None:
        return None
    if isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            k_lower = k.lower()
            if any(sensitive in k_lower for sensitive in SENSITIVE_KEYS):
                redacted[k] = '[REDACTED]'
            elif isinstance(v, (dict, list)):
                redacted[k] = redact_sensitive_data(v)
            else:
                redacted[k] = v
        return redacted
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data

def mask_ip_address(ip):
    """Mask IP address for privacy (show only first two octets)"""
    if not ip:
        return None
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return ip[:8] + '***' if len(ip) > 8 else ip


@audit_bp.route('/events', methods=['GET'])
@require_user_auth
def list_audit_events():
    """
    List audit events for the current tenant (admin use)
    
    Query params:
        event_type: Filter by event type (e.g., DEVICE_REGISTERED, SECRET_CREATED)
        device_id: Filter by device ID
        miner_id: Filter by miner ID
        result: Filter by result (success, error)
        limit: Max number of events to return (default 100, max 500)
        offset: Pagination offset
        start_date: Filter events after this date (ISO format)
        end_date: Filter events before this date (ISO format)
    
    Response:
        {
            "events": [...],
            "total": 150,
            "limit": 100,
            "offset": 0
        }
    """
    from sqlalchemy import desc
    
    query = DeviceAuditEvent.query.filter_by(tenant_id=g.tenant_id)
    
    event_type = request.args.get('event_type')
    if event_type:
        query = query.filter_by(event_type=event_type.upper())
    
    device_id = request.args.get('device_id', type=int)
    if device_id:
        query = query.filter_by(device_id=device_id)
    
    miner_id = request.args.get('miner_id', type=int)
    if miner_id:
        query = query.filter_by(miner_id=miner_id)
    
    result = request.args.get('result')
    if result:
        query = query.filter_by(result=result.lower())
    
    start_date = request.args.get('start_date')
    if start_date:
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(DeviceAuditEvent.created_at >= start_dt)
        except ValueError:
            pass
    
    end_date = request.args.get('end_date')
    if end_date:
        try:
            from datetime import datetime
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(DeviceAuditEvent.created_at <= end_dt)
        except ValueError:
            pass
    
    total = query.count()
    
    limit = min(request.args.get('limit', 100, type=int), 500)
    offset = request.args.get('offset', 0, type=int)
    
    events = query.order_by(desc(DeviceAuditEvent.created_at)).offset(offset).limit(limit).all()
    
    return jsonify({
        'events': [{
            'id': e.id,
            'event_type': e.event_type,
            'device_id': e.device_id,
            'miner_id': e.miner_id,
            'actor_id': e.actor_id,
            'actor_type': e.actor_type,
            'ip_address': mask_ip_address(e.ip_address),
            'result': e.result,
            'error_message': '[REDACTED]' if e.error_message else None,
            'event_data': redact_sensitive_data(e.event_data),
            'created_at': e.created_at.isoformat()
        } for e in events],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@audit_bp.route('/events/<int:event_id>', methods=['GET'])
@require_user_auth
def get_audit_event(event_id):
    """
    Get details of a specific audit event
    """
    event = DeviceAuditEvent.query.filter_by(
        id=event_id,
        tenant_id=g.tenant_id
    ).first()
    
    if not event:
        return jsonify({'error': 'Audit event not found'}), 404
    
    return jsonify({
        'event': {
            'id': event.id,
            'event_type': event.event_type,
            'tenant_id': event.tenant_id,
            'device_id': event.device_id,
            'miner_id': event.miner_id,
            'actor_id': event.actor_id,
            'actor_type': event.actor_type,
            'ip_address': mask_ip_address(event.ip_address),
            'user_agent': event.user_agent[:50] + '...' if event.user_agent and len(event.user_agent) > 50 else event.user_agent,
            'event_data': redact_sensitive_data(event.event_data),
            'result': event.result,
            'error_message': '[REDACTED]' if event.error_message else None,
            'created_at': event.created_at.isoformat()
        }
    })


@audit_bp.route('/stats', methods=['GET'])
@require_user_auth
def get_audit_stats():
    """
    Get audit event statistics for the current tenant
    
    Response:
        {
            "total_events": 500,
            "by_type": {
                "DEVICE_REGISTERED": 10,
                "SECRET_CREATED": 200,
                ...
            },
            "by_result": {
                "success": 490,
                "error": 10
            },
            "recent_errors": [...]
        }
    """
    from sqlalchemy import func, desc
    
    total_events = DeviceAuditEvent.query.filter_by(tenant_id=g.tenant_id).count()
    
    type_counts = db.session.query(
        DeviceAuditEvent.event_type,
        func.count(DeviceAuditEvent.id)
    ).filter_by(tenant_id=g.tenant_id).group_by(DeviceAuditEvent.event_type).all()
    
    result_counts = db.session.query(
        DeviceAuditEvent.result,
        func.count(DeviceAuditEvent.id)
    ).filter_by(tenant_id=g.tenant_id).group_by(DeviceAuditEvent.result).all()
    
    recent_errors = DeviceAuditEvent.query.filter_by(
        tenant_id=g.tenant_id,
        result='error'
    ).order_by(desc(DeviceAuditEvent.created_at)).limit(10).all()
    
    return jsonify({
        'total_events': total_events,
        'by_type': {t: c for t, c in type_counts},
        'by_result': {r: c for r, c in result_counts},
        'recent_errors': [{
            'id': e.id,
            'event_type': e.event_type,
            'error_message': e.error_message,
            'created_at': e.created_at.isoformat()
        } for e in recent_errors]
    })


# ==================== Site Miners API ====================

sites_api_bp = Blueprint('sites_api', __name__, url_prefix='/api/sites')


@sites_api_bp.route('/<int:site_id>/miners', methods=['GET'])
@require_user_auth
def get_site_miners(site_id):
    """
    Get all miners for a site (for IP encryption batch operations)
    
    Response:
        {
            "miners": [
                {"id": 1, "name": "Miner-01", "ip_encryption_mode": 1},
                ...
            ],
            "total": 100
        }
    """
    from models import UserAccess
    
    # Verify site exists
    site = HostingSite.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    # Get authenticated user for RBAC
    user = UserAccess.query.get(g.tenant_id)
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    # Admin/Owner roles can see all miners
    if user.role in ['owner', 'admin', 'super_admin', 'tenant_admin']:
        miners = HostingMiner.query.filter_by(site_id=site_id).all()
    else:
        # Non-admin users can only see their own miners
        miners = HostingMiner.query.filter_by(site_id=site_id, customer_id=g.tenant_id).all()
    
    return jsonify({
        'miners': [{
            'id': m.id,
            'name': m.serial_number or f'Miner-{m.id}',
            'ip_address': m.ip_address,
            'ip_encryption_mode': getattr(m, 'ip_encryption_mode', 1) or 1
        } for m in miners],
        'total': len(miners)
    })


# ==================== IP Encryption Management API ====================

ip_encryption_bp = Blueprint('ip_encryption', __name__, url_prefix='/api/ip-encryption')


@ip_encryption_bp.route('/modes', methods=['GET'])
def get_encryption_modes():
    """
    Get available IP encryption modes
    
    Response:
        {
            "modes": [
                {"id": 1, "name_en": "UI Masking", "name_zh": "UI脱敏", "description": "..."},
                {"id": 2, "name_en": "Server Encrypted", "name_zh": "服务器加密", "description": "..."},
                {"id": 3, "name_en": "E2EE Protected", "name_zh": "E2EE加密", "description": "..."}
            ]
        }
    """
    modes = [
        {
            'id': 1,
            'name_en': 'UI Masking',
            'name_zh': 'UI脱敏',
            'description_en': 'IP stored in plaintext, masked in UI (192.168.1.xxx). RBAC controls who can reveal.',
            'description_zh': 'IP明文存储，UI显示脱敏格式。RBAC控制谁可以查看完整IP。'
        },
        {
            'id': 2,
            'name_en': 'Server Encrypted',
            'name_zh': '服务器加密',
            'description_en': 'IP encrypted at rest using server-side encryption. Decryptable with proper permissions.',
            'description_zh': 'IP使用服务器端密钥加密存储。有权限的用户可以解密查看。'
        },
        {
            'id': 3,
            'name_en': 'E2EE Protected',
            'name_zh': 'E2EE加密',
            'description_en': 'IP encrypted end-to-end. Server never sees plaintext. Only Edge Collector can decrypt.',
            'description_zh': 'IP端到端加密，服务器永不见明文。只有边缘采集器可以解密。'
        }
    ]
    return jsonify({'modes': modes})


def _validate_miner_access(miner_id):
    """Validate that the current user has access to the miner via ownership or admin role"""
    from models import UserAccess
    
    miner = HostingMiner.query.get(miner_id)
    if not miner:
        return None, jsonify({'error': 'Miner not found'}), 404
    
    # Get authenticated user
    user = UserAccess.query.get(g.tenant_id)
    if not user:
        return None, jsonify({'error': 'User not found'}), 401
    
    # Admin/Owner roles have full access
    if user.role in ['owner', 'admin', 'super_admin', 'tenant_admin']:
        return miner, None, None
    
    # Otherwise, check miner ownership (customer_id must match user)
    if miner.customer_id != g.tenant_id:
        return None, jsonify({'error': 'Access denied to this miner'}), 403
    
    return miner, None, None


@ip_encryption_bp.route('/miner/<int:miner_id>/mode', methods=['GET'])
@require_user_auth
def get_miner_ip_mode(miner_id):
    """Get current IP encryption mode for a miner"""
    miner, error_response, status_code = _validate_miner_access(miner_id)
    if error_response:
        return error_response, status_code
    
    mode = getattr(miner, 'ip_encryption_mode', 1) or 1
    mode_names = {1: 'MASK', 2: 'SERVER_ENCRYPT', 3: 'E2EE'}
    
    return jsonify({
        'miner_id': miner_id,
        'ip_encryption_mode': mode,
        'mode_name': mode_names.get(mode, 'UNKNOWN')
    })


@ip_encryption_bp.route('/miner/<int:miner_id>/mode', methods=['PUT'])
@require_user_auth
def update_miner_ip_mode(miner_id):
    """
    Update IP encryption mode for a miner
    
    Request:
        {
            "mode": 2,  // 1=MASK, 2=SERVER_ENCRYPT, 3=E2EE
            "encrypt_existing": true,  // Optional: encrypt existing IP when switching to mode 2
            "encrypted_ip_envelope": {}  // Optional: E2EE envelope for Strategy 3
        }
    """
    from services.ip_encryption_service import ip_encryption_service, IPEncryptionMode
    
    miner, error_response, status_code = _validate_miner_access(miner_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json() or {}
    new_mode = data.get('mode')
    encrypt_existing = data.get('encrypt_existing', True)
    encrypted_ip_envelope = data.get('encrypted_ip_envelope')  # For E2EE mode
    
    if not new_mode or new_mode not in [1, 2, 3]:
        return jsonify({
            'error': 'mode must be 1, 2, or 3',
            'mode_names': {1: 'MASK', 2: 'SERVER_ENCRYPT', 3: 'E2EE'}
        }), 400
    
    old_mode = getattr(miner, 'ip_encryption_mode', 1) or 1
    transition_note = None
    
    # Mode transition logic
    if new_mode == IPEncryptionMode.MASK:
        # Switching to UI Masking - need to restore plaintext IP
        if old_mode == IPEncryptionMode.SERVER_ENCRYPT:
            if miner.encrypted_ip and ip_encryption_service.is_encrypted(miner.encrypted_ip):
                try:
                    miner.ip_address = ip_encryption_service.decrypt_ip(miner.encrypted_ip)
                    miner.encrypted_ip = None
                    transition_note = 'IP decrypted from server encryption'
                except Exception as e:
                    logger.error(f"Failed to decrypt IP for miner {miner_id}: {e}")
                    return jsonify({'error': 'Failed to decrypt IP', 'detail': str(e)}), 500
        elif old_mode == IPEncryptionMode.E2EE:
            # Cannot transition from E2EE to MASK without re-entering IP
            transition_note = 'E2EE IP cannot be recovered - requires re-entering IP address'
            miner.encrypted_ip = None  # Clear the E2EE marker
    
    elif new_mode == IPEncryptionMode.SERVER_ENCRYPT:
        if encrypt_existing and miner.ip_address:
            if not ip_encryption_service.is_encrypted(miner.ip_address):
                miner.encrypted_ip = ip_encryption_service.encrypt_ip(miner.ip_address)
                miner.ip_address = None
                transition_note = 'IP encrypted with server-side Fernet'
    
    elif new_mode == IPEncryptionMode.E2EE:
        # Store E2EE envelope if provided, otherwise mark as pending
        if encrypted_ip_envelope:
            import json
            miner.encrypted_ip = 'E2EE:' + json.dumps(encrypted_ip_envelope)
            transition_note = 'E2EE envelope stored'
        else:
            miner.encrypted_ip = 'E2EE:pending-client-encryption'
            transition_note = 'Awaiting client-side E2EE encryption'
        miner.ip_address = None
    
    miner.ip_encryption_mode = new_mode
    db.session.commit()
    
    log_audit_event(
        'IP_ENCRYPTION_MODE_CHANGED',
        miner_id=miner_id,
        event_data={
            'old_mode': old_mode,
            'new_mode': new_mode,
            'encrypt_existing': encrypt_existing,
            'transition_note': transition_note
        }
    )
    
    mode_names = {1: 'MASK', 2: 'SERVER_ENCRYPT', 3: 'E2EE'}
    
    return jsonify({
        'success': True,
        'miner_id': miner_id,
        'old_mode': old_mode,
        'new_mode': new_mode,
        'mode_name': mode_names.get(new_mode, 'UNKNOWN'),
        'transition_note': transition_note
    })


@ip_encryption_bp.route('/miner/<int:miner_id>/reveal', methods=['POST'])
@require_user_auth
def reveal_miner_ip(miner_id):
    """
    Reveal (decrypt) miner IP address
    
    Requires appropriate permissions. All reveals are logged for audit.
    
    Response:
        {
            "miner_id": 1,
            "ip_address": "192.168.1.100",
            "revealed": true
        }
    """
    from services.ip_encryption_service import ip_encryption_service, IPEncryptionMode
    
    miner, error_response, status_code = _validate_miner_access(miner_id)
    if error_response:
        return error_response, status_code
    
    mode = getattr(miner, 'ip_encryption_mode', 1) or 1
    
    if mode == IPEncryptionMode.E2EE:
        log_audit_event(
            'IP_REVEAL_DENIED',
            miner_id=miner_id,
            event_data={'reason': 'E2EE protected'},
            result='denied'
        )
        return jsonify({
            'error': 'Cannot reveal E2EE protected IP',
            'message': 'IP is encrypted end-to-end and only accessible by Edge Collector'
        }), 403
    
    ip_address = None
    
    if mode == IPEncryptionMode.SERVER_ENCRYPT:
        if miner.encrypted_ip:
            try:
                ip_address = ip_encryption_service.decrypt_ip(miner.encrypted_ip)
            except Exception as e:
                logger.error(f"Failed to decrypt IP for reveal: {e}")
                return jsonify({'error': 'Failed to decrypt IP'}), 500
        else:
            ip_address = miner.ip_address
    else:
        ip_address = miner.ip_address
    
    log_audit_event(
        'IP_REVEALED',
        miner_id=miner_id,
        event_data={'mode': mode}
    )
    
    return jsonify({
        'miner_id': miner_id,
        'ip_address': ip_address,
        'revealed': True
    })


@ip_encryption_bp.route('/batch-update', methods=['POST'])
@require_user_auth
def batch_update_ip_mode():
    """
    Batch update IP encryption mode for multiple miners
    
    Request:
        {
            "miner_ids": [1, 2, 3],
            "mode": 2,
            "encrypt_existing": true
        }
    """
    from services.ip_encryption_service import ip_encryption_service, IPEncryptionMode
    
    data = request.get_json() or {}
    miner_ids = data.get('miner_ids', [])
    new_mode = data.get('mode')
    encrypt_existing = data.get('encrypt_existing', True)
    
    if not miner_ids:
        return jsonify({'error': 'miner_ids required'}), 400
    
    if not new_mode or new_mode not in [1, 2, 3]:
        return jsonify({'error': 'mode must be 1, 2, or 3'}), 400
    
    from models import UserAccess
    
    updated = 0
    errors = []
    skipped_no_access = 0
    
    # Get authenticated user for RBAC
    user = UserAccess.query.get(g.tenant_id)
    is_admin = user and user.role in ['owner', 'admin', 'super_admin', 'tenant_admin']
    
    for miner_id in miner_ids:
        try:
            miner = HostingMiner.query.get(miner_id)
            if not miner:
                errors.append({'miner_id': miner_id, 'error': 'not found'})
                continue
            
            # RBAC check: admins can update any miner, others only their own
            if not is_admin and miner.customer_id != g.tenant_id:
                skipped_no_access += 1
                errors.append({'miner_id': miner_id, 'error': 'access denied'})
                continue
            
            old_mode = getattr(miner, 'ip_encryption_mode', 1) or 1
            
            if new_mode == IPEncryptionMode.SERVER_ENCRYPT and encrypt_existing:
                if miner.ip_address and not ip_encryption_service.is_encrypted(miner.ip_address):
                    miner.encrypted_ip = ip_encryption_service.encrypt_ip(miner.ip_address)
                    miner.ip_address = None
            
            elif new_mode == IPEncryptionMode.MASK:
                if miner.encrypted_ip and ip_encryption_service.is_encrypted(miner.encrypted_ip):
                    try:
                        miner.ip_address = ip_encryption_service.decrypt_ip(miner.encrypted_ip)
                        miner.encrypted_ip = None
                    except Exception:
                        errors.append({'miner_id': miner_id, 'error': 'decrypt failed'})
                        continue
            
            elif new_mode == IPEncryptionMode.E2EE:
                miner.encrypted_ip = 'E2EE:pending-client-encryption'
                miner.ip_address = None
            
            miner.ip_encryption_mode = new_mode
            updated += 1
            
        except Exception as e:
            errors.append({'miner_id': miner_id, 'error': str(e)})
    
    db.session.commit()
    
    log_audit_event(
        'BATCH_IP_ENCRYPTION_MODE_CHANGED',
        event_data={
            'miner_count': len(miner_ids),
            'updated': updated,
            'errors': len(errors),
            'skipped_no_access': skipped_no_access,
            'new_mode': new_mode
        }
    )
    
    return jsonify({
        'success': True,
        'updated': updated,
        'errors': errors,
        'skipped_no_access': skipped_no_access,
        'total': len(miner_ids)
    })
