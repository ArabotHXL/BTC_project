"""
Control Plane API - 控制平面核心API
统一的 v1 命令协议，支持审批门禁、ABAC隔离

Edge-facing endpoints:
- POST /api/edge/v1/register
- GET /api/edge/v1/commands/poll
- POST /api/edge/v1/commands/{command_id}/ack
- POST /api/edge/v1/telemetry/ingest

User-facing endpoints:
- POST /api/v1/commands/propose
- POST /api/v1/commands/{id}/approve
- POST /api/v1/commands/{id}/deny
- POST /api/v1/commands/{id}/rollback
- GET /api/v1/commands/{id}
- GET /api/v1/commands
- POST /api/v1/price-plans/upload
- GET /api/v1/price-plans/{plan_id}/versions
- GET /api/v1/demand/monthly-ledger
- POST /api/v1/demand/replay
"""
import os
import csv
import json
import uuid
import hmac
import logging
import hashlib
from io import StringIO
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, g, session

from db import db
from models import UserAccess, HostingSite, HostingMiner
from models_device_encryption import EdgeDevice
from models_remote_control import RemoteCommand, RemoteCommandResult, CommandStatus
from models_control_plane import (
    Zone, HostingCustomer, MinerAsset, MinerCapability,
    PricePlan, PricePlanVersion, DemandLedgerMonthly, Demand15Min,
    CommandApproval, CommandTarget, RetentionPolicy, AuditEvent,
    ApprovalPolicy, get_approval_requirement
)
from api.collector_api import MinerCommand
from services.rate_limiter import check_rate_limit, record_command_dispatch
from services.metrics_service import inc_commands_dispatched, inc_commands_acked, inc_commands_failed

logger = logging.getLogger(__name__)

control_plane_bp = Blueprint('control_plane', __name__)

RISK_TIER_MAP = {
    'REBOOT': 'MEDIUM',
    'POWER_MODE': 'MEDIUM',
    'CHANGE_POOL': 'HIGH',
    'SET_FREQ': 'MEDIUM',
    'THERMAL_POLICY': 'LOW',
    'LED': 'LOW',
}

COMMAND_TYPE_MAP = {
    'reboot': 'MINER_RESTART',
    'restart': 'MINER_RESTART',
    'device_reboot': 'DEVICE_REBOOT',
    'stop': 'HASHING_DISABLE',
    'start': 'HASHING_ENABLE',
    'disable': 'HASHING_DISABLE',
    'enable': 'HASHING_ENABLE',
    'set_pool': 'POOL_SET',
    'pool_set': 'POOL_SET',
    'set_fan': 'SET_FAN',
    'set_frequency': 'SET_FREQUENCY',
    'power_mode': 'POWER_MODE',
}


def normalize_command_type(cmd_type: str) -> str:
    """Normalize legacy command types to v1.1 standard."""
    if not cmd_type:
        return cmd_type
    return COMMAND_TYPE_MAP.get(cmd_type.lower(), cmd_type.upper())


def require_user_auth(f):
    """Require user authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id or not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        g.user = user
        g.user_id = user.id
        g.user_role = user.role or 'user'
        return f(*args, **kwargs)
    return decorated


def require_device_auth(f):
    """Require edge device token authentication with zone binding"""
    @wraps(f)
    def decorated(*args, **kwargs):
        import hashlib
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Device token required'}), 401
        token = auth_header[7:]
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        device = EdgeDevice.query.filter_by(token_hash=token_hash, status='ACTIVE').first()
        if not device:
            device = EdgeDevice.query.filter_by(device_token=token, status='ACTIVE').first()
        if not device:
            return jsonify({'error': 'Invalid or revoked device token'}), 401
        
        device.last_seen_at = datetime.utcnow()
        db.session.commit()
        
        g.device = device
        g.device_id = device.id
        g.site_id = device.site_id
        g.zone_id = device.zone_id
        return f(*args, **kwargs)
    return decorated


def require_edge_auth(f):
    """Unified edge auth: supports EdgeDevice token OR CollectorKey token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        import hashlib
        auth_header = request.headers.get('Authorization', '')
        token = None
        
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            device = EdgeDevice.query.filter_by(token_hash=token_hash, status='ACTIVE').first()
            if not device:
                device = EdgeDevice.query.filter_by(device_token=token, status='ACTIVE').first()
            if device:
                device.last_seen_at = datetime.utcnow()
                db.session.commit()
                g.device = device
                g.device_id = device.id
                g.site_id = device.site_id
                g.zone_id = device.zone_id
                g.auth_method = 'edge_device'
                return f(*args, **kwargs)
        
        collector_token = token or request.headers.get('X-Collector-Key')
        if collector_token:
            from api.collector_api import CollectorKey
            key_hash = hashlib.sha256(collector_token.encode()).hexdigest()
            collector_key = CollectorKey.query.filter_by(key_hash=key_hash, is_active=True).first()
            if collector_key:
                collector_key.last_used_at = datetime.utcnow()
                db.session.commit()
                g.collector_key = collector_key
                g.device = None
                g.device_id = None
                g.site_id = collector_key.site_id
                g.zone_id = None
                g.auth_method = 'collector_key'
                return f(*args, **kwargs)
        
        return jsonify({'error': 'Authentication required. Provide EdgeDevice token or CollectorKey.'}), 401
    return decorated


def require_customer_access(f):
    """ABAC: Ensure customer can only access their own data"""
    @wraps(f)
    def decorated(*args, **kwargs):
        customer_profile = getattr(g.user, 'hosting_customer_profile', None)
        if customer_profile:
            g.customer_id = customer_profile.id
            g.customer_filter = True
        else:
            g.customer_id = None
            g.customer_filter = False
        return f(*args, **kwargs)
    return decorated


def generate_canonical_signature(command_data: dict, hmac_secret: str) -> tuple[str, str, str]:
    """
    Generate HMAC-SHA256 signature using canonical JSON format.
    
    Args:
        command_data: dict with fields: command_id, site_id, zone_id, miner_id, 
                     command_type, params, priority, expires_at, dedupe_key, signed_at, nonce
        hmac_secret: the device's HMAC secret
    
    Returns:
        tuple of (signature_hex, sig_version, sig_encoding)
    """
    # Fixed field set for canonical JSON
    canonical_fields = {
        'command_id': command_data.get('command_id'),
        'site_id': command_data.get('site_id'),
        'zone_id': command_data.get('zone_id'),
        'miner_id': command_data.get('miner_id'),
        'command_type': command_data.get('command_type'),
        'params': command_data.get('params'),
        'priority': command_data.get('priority'),
        'expires_at': command_data.get('expires_at'),
        'dedupe_key': command_data.get('dedupe_key'),
        'signed_at': command_data.get('signed_at'),
        'nonce': command_data.get('nonce')
    }
    
    # Canonical JSON: sort_keys=True, separators=(",", ":"), ensure_ascii=False
    canonical_json = json.dumps(canonical_fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    
    # HMAC-SHA256
    signature = hmac.new(
        hmac_secret.encode('utf-8'),
        canonical_json.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature, "HMAC-SHA256-CANONICAL-JSON-V1", "hex"


def log_audit_event(event_type, actor_type, actor_id, site_id=None, ref_type=None, ref_id=None, payload=None):
    """Log audit event with hash chain"""
    try:
        last_event = AuditEvent.query.order_by(AuditEvent.id.desc()).first()
        prev_hash = last_event.event_hash if last_event else '0' * 64
        
        event = AuditEvent(
            site_id=site_id,
            actor_type=actor_type,
            actor_id=str(actor_id),
            event_type=event_type,
            ref_type=ref_type,
            ref_id=str(ref_id) if ref_id else None,
            payload_json=payload or {},
            prev_hash=prev_hash,
        )
        event.event_hash = event.compute_hash()
        db.session.add(event)
        db.session.commit()
        return event
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        return None


@control_plane_bp.route('/api/edge/v1/register', methods=['POST'])
def edge_register():
    """Edge device registration"""
    data = request.get_json() or {}
    edge_id = data.get('edge_id')
    site_id = data.get('site_id')
    zone_id = data.get('zone_id')
    
    if not edge_id or not site_id:
        return jsonify({'error': 'edge_id and site_id required'}), 400
    
    device = EdgeDevice.query.filter_by(edge_device_id=edge_id).first()
    if device:
        device.last_seen_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'registered': True,
            'server_time': datetime.utcnow().isoformat() + 'Z',
            'polling_hints': {'interval_seconds': 30, 'long_poll_timeout': 60}
        })
    
    return jsonify({'error': 'Device not registered. Contact admin.'}), 403


@control_plane_bp.route('/api/edge/v1/commands/poll', methods=['GET'])
@require_edge_auth
def edge_poll_commands():
    """Poll for queued commands - production-grade with atomic lease dispatch
    
    Returns both MinerCommand (newer, single-miner) and RemoteCommand (legacy, multi-miner).
    Each command is clearly labeled with command_source: 'miner' or 'remote'.
    
    Zone binding: Device token is bound to (site_id, zone_id).
    If zone_id param provided, it must match device's zone_id (validation only).
    CollectorKey auth bypasses zone binding (zone_id is None).
    
    Features:
    - Atomic lease dispatch using SELECT FOR UPDATE SKIP LOCKED
    - Rate limiting integration
    - Optional HMAC signature for command integrity
    - Idempotent ACK support via ack_nonce
    - Backward compatibility with both RemoteCommand and MinerCommand
    - CollectorKey authentication support for Remote compatibility
    """
    site_id = g.site_id
    device_zone_id = g.zone_id
    device_id = str(g.device_id) if g.device_id else f"collector_key:{getattr(g, 'collector_key', None) and g.collector_key.id or 'unknown'}"
    requested_zone_id = request.args.get('zone_id', type=int)
    limit = min(request.args.get('limit', 10, type=int), 50)
    
    if requested_zone_id and device_zone_id and requested_zone_id != device_zone_id:
        log_audit_event(
            event_type='security.zone_access_denied',
            actor_type='device',
            actor_id=device_id,
            site_id=site_id,
            payload={'requested_zone': requested_zone_id, 'bound_zone': device_zone_id}
        )
        return jsonify({'error': 'Zone access denied - device bound to different zone'}), 403
    
    now = datetime.utcnow()
    lease_duration_sec = 60
    lease_until = now + timedelta(seconds=lease_duration_sec)
    enable_signature = os.environ.get('ENABLE_COMMAND_SIGNATURE', '').lower() == 'true'
    
    result = []
    dispatched_count = 0
    rate_limited_count = 0
    miner_command_count = 0
    remote_command_count = 0
    
    # Section 1: Poll MinerCommand objects (newer, single-miner commands)
    miner_query = MinerCommand.query.filter(
        MinerCommand.site_id == site_id,
        MinerCommand.status == 'pending',
        MinerCommand.next_attempt_at <= now,
        MinerCommand.expires_at > now
    ).order_by(
        MinerCommand.priority.desc(),
        MinerCommand.created_at.asc()
    ).with_for_update(skip_locked=True).limit(limit * 2)
    
    miner_commands = miner_query.all()
    
    for cmd in miner_commands:
        if dispatched_count >= limit:
            break
        
        allowed, rate_info = check_rate_limit(site_id, cmd.command_type)
        if not allowed:
            log_audit_event(
                event_type='command.rate_limited_dispatch',
                actor_type='device',
                actor_id=device_id,
                site_id=site_id,
                ref_type='miner_command',
                ref_id=cmd.id,
                payload={
                    'command_type': cmd.command_type,
                    'rate_limit': rate_info.get('limit'),
                    'current_count': rate_info.get('current_count'),
                    'reset_at': rate_info.get('reset_at')
                }
            )
            rate_limited_count += 1
            continue
        
        dispatch_nonce = str(uuid.uuid4())
        
        cmd.status = 'dispatched'
        cmd.lease_owner = device_id
        cmd.lease_until = lease_until
        cmd.sent_at = now
        cmd.dispatch_nonce = dispatch_nonce
        
        record_command_dispatch(site_id, cmd.command_type)
        
        normalized_command_type = normalize_command_type(cmd.command_type)
        
        command_data = {
            'command_source': 'miner',
            'command_id': cmd.id,
            'site_id': site_id,
            'zone_id': device_zone_id,
            'miner_id': cmd.miner_id,
            'command_type': normalized_command_type,
            'params': cmd.parameters or {},
            'priority': cmd.priority if cmd.priority is not None else 0,
            'expires_at': cmd.expires_at.isoformat() + 'Z' if cmd.expires_at else None,
            'dedupe_key': cmd.dedupe_key,
            'nonce': dispatch_nonce,
            'ack_nonce': dispatch_nonce,
            'lease_expires_at': lease_until.isoformat() + 'Z',
            'retry_count': cmd.retry_count,
            'max_retries': cmd.max_retries,
        }
        
        if cmd.remote_command_id:
            command_data['remote_command_id'] = cmd.remote_command_id
        
        if enable_signature and getattr(g, 'device', None):
            device = g.device
            hmac_secret = device.device_token or device.token_hash
            
            canonical_sig_data = {
                'command_id': cmd.id,
                'site_id': site_id,
                'zone_id': device_zone_id,
                'miner_id': cmd.miner_id,
                'command_type': normalized_command_type,
                'params': cmd.parameters or {},
                'priority': cmd.priority if cmd.priority is not None else 0,
                'expires_at': cmd.expires_at.isoformat() + 'Z' if cmd.expires_at else None,
                'dedupe_key': cmd.dedupe_key,
                'signed_at': now.isoformat() + 'Z',
                'nonce': dispatch_nonce
            }
            
            signature, sig_version, sig_encoding = generate_canonical_signature(canonical_sig_data, hmac_secret)
            
            cmd.signature = signature
            command_data['signature'] = signature
            command_data['sig_version'] = sig_version
            command_data['sig_encoding'] = sig_encoding
            command_data['signed_at'] = now.isoformat() + 'Z'
        
        result.append(command_data)
        dispatched_count += 1
        miner_command_count += 1
        
        log_audit_event(
            event_type='command.dispatched',
            actor_type='device',
            actor_id=device_id,
            site_id=site_id,
            ref_type='miner_command',
            ref_id=cmd.id,
            payload={
                'command_type': cmd.command_type,
                'miner_id': cmd.miner_id,
                'dispatch_nonce': dispatch_nonce,
                'lease_until': lease_until.isoformat()
            }
        )
        
        inc_commands_dispatched(site_id, cmd.command_type)
    
    # Section 2: Poll RemoteCommand objects (legacy, multi-miner commands) for backward compatibility
    remaining_limit = limit - dispatched_count
    if remaining_limit > 0:
        remote_query = RemoteCommand.query.filter(
            RemoteCommand.site_id == site_id,
            RemoteCommand.status == 'QUEUED',
            RemoteCommand.expires_at > now
        ).order_by(
            RemoteCommand.created_at.asc()
        ).with_for_update(skip_locked=True).limit(remaining_limit)
        
        remote_commands = remote_query.all()
        
        for cmd in remote_commands:
            if dispatched_count >= limit:
                break
            
            allowed, rate_info = check_rate_limit(site_id, cmd.command_type)
            if not allowed:
                log_audit_event(
                    event_type='command.rate_limited_dispatch',
                    actor_type='device',
                    actor_id=device_id,
                    site_id=site_id,
                    ref_type='remote_command',
                    ref_id=cmd.id,
                    payload={
                        'command_type': cmd.command_type,
                        'rate_limit': rate_info.get('limit'),
                        'current_count': rate_info.get('current_count'),
                        'reset_at': rate_info.get('reset_at')
                    }
                )
                rate_limited_count += 1
                continue
            
            dispatch_nonce = str(uuid.uuid4())
            
            cmd.status = 'RUNNING'
            cmd.updated_at = now
            
            record_command_dispatch(site_id, cmd.command_type)
            
            normalized_command_type = normalize_command_type(cmd.command_type)
            
            command_data = {
                'command_source': 'remote',
                'command_id': cmd.id,
                'site_id': site_id,
                'zone_id': cmd.zone_id,
                'miner_id': None,
                'command_type': normalized_command_type,
                'params': cmd.payload_json or {},
                'priority': 0,
                'expires_at': cmd.expires_at.isoformat() + 'Z' if cmd.expires_at else None,
                'dedupe_key': None,
                'nonce': dispatch_nonce,
                'ack_nonce': dispatch_nonce,
                'target_ids': cmd.target_ids,
                'payload': cmd.payload_json or {},
            }
            
            if enable_signature and getattr(g, 'device', None):
                device = g.device
                hmac_secret = device.device_token or device.token_hash
                
                canonical_sig_data = {
                    'command_id': cmd.id,
                    'site_id': site_id,
                    'zone_id': cmd.zone_id,
                    'miner_id': None,
                    'command_type': normalized_command_type,
                    'params': cmd.payload_json or {},
                    'priority': 0,
                    'expires_at': cmd.expires_at.isoformat() + 'Z' if cmd.expires_at else None,
                    'dedupe_key': None,
                    'signed_at': now.isoformat() + 'Z',
                    'nonce': dispatch_nonce
                }
                
                signature, sig_version, sig_encoding = generate_canonical_signature(canonical_sig_data, hmac_secret)
                
                command_data['signature'] = signature
                command_data['sig_version'] = sig_version
                command_data['sig_encoding'] = sig_encoding
                command_data['signed_at'] = now.isoformat() + 'Z'
            
            result.append(command_data)
            dispatched_count += 1
            remote_command_count += 1
            
            log_audit_event(
                event_type='command.dispatched',
                actor_type='device',
                actor_id=device_id,
                site_id=site_id,
                ref_type='remote_command',
                ref_id=cmd.id,
                payload={
                    'command_type': cmd.command_type,
                    'target_count': len(cmd.target_ids) if cmd.target_ids else 0,
                    'dispatch_nonce': dispatch_nonce,
                }
            )
            
            inc_commands_dispatched(site_id, cmd.command_type)
    
    db.session.commit()
    
    return jsonify({
        'commands': result,
        'server_time': now.isoformat() + 'Z',
        'dispatched_count': dispatched_count,
        'miner_command_count': miner_command_count,
        'remote_command_count': remote_command_count,
        'rate_limited_count': rate_limited_count,
        'lease_duration_sec': lease_duration_sec,
    })


def _sync_remote_command_status(remote_command_id):
    """Synchronize RemoteCommand status based on child MinerCommands
    
    This function checks if all MinerCommands linked to a RemoteCommand have reached
    terminal state. If so, it updates the RemoteCommand status to:
    - SUCCEEDED: if all MinerCommands succeeded
    - FAILED: if any MinerCommand failed
    
    Terminal states for MinerCommand: 'completed', 'failed', 'expired', 'cancelled', 'superseded'
    
    Args:
        remote_command_id: The RemoteCommand ID to synchronize
    """
    try:
        remote_cmd = RemoteCommand.query.get(remote_command_id)
        if not remote_cmd:
            logger.warning(f"RemoteCommand {remote_command_id} not found for sync")
            return
        
        MINER_TERMINAL_STATES = {'completed', 'failed', 'expired', 'cancelled', 'superseded'}
        now = datetime.utcnow()
        
        # Query all MinerCommands linked to this RemoteCommand
        child_commands = MinerCommand.query.filter_by(remote_command_id=remote_command_id).all()
        
        if not child_commands:
            logger.debug(f"No MinerCommands found for RemoteCommand {remote_command_id}")
            return
        
        # Count commands in terminal state
        terminal_count = sum(1 for cmd in child_commands if cmd.status in MINER_TERMINAL_STATES)
        total_count = len(child_commands)
        
        # If not all are terminal, don't update RemoteCommand yet
        if terminal_count < total_count:
            logger.debug(
                f"RemoteCommand {remote_command_id}: {terminal_count}/{total_count} children terminal"
            )
            return
        
        # All child commands are terminal - determine final status
        failed_count = sum(1 for cmd in child_commands if cmd.status in {'failed', 'expired', 'cancelled'})
        final_status = 'FAILED' if failed_count > 0 else 'SUCCEEDED'
        
        # Check if status needs updating
        if remote_cmd.status in ('SUCCEEDED', 'FAILED', 'CANCELLED', 'EXPIRED'):
            logger.debug(f"RemoteCommand {remote_command_id} already in terminal state: {remote_cmd.status}")
            return
        
        # Update RemoteCommand status
        old_status = remote_cmd.status
        remote_cmd.status = final_status
        remote_cmd.updated_at = now
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            event_type='remote_command.completed',
            actor_type='system',
            actor_id='sync_worker',
            site_id=remote_cmd.site_id,
            ref_type='remote_command',
            ref_id=remote_command_id,
            payload={
                'old_status': old_status,
                'new_status': final_status,
                'total_children': total_count,
                'failed_children': failed_count,
                'succeeded_children': total_count - failed_count
            }
        )
        
        logger.info(
            f"RemoteCommand {remote_command_id} synced: {old_status} -> {final_status} "
            f"({total_count} children: {total_count - failed_count} succeeded, {failed_count} failed)"
        )
        
    except Exception as e:
        logger.error(f"Error syncing RemoteCommand {remote_command_id}: {e}", exc_info=True)


@control_plane_bp.route('/api/edge/v1/commands/<command_id>/ack', methods=['POST'])
@require_edge_auth
def edge_ack_command(command_id):
    """Acknowledge command completion - production-grade with idempotency and retry logic
    
    Features:
    - Idempotent ACK with replay protection via ack_hash
    - Lease owner verification
    - Automatic retry scheduling on failure
    - Terminal state tracking
    - Structured error codes
    - CollectorKey authentication support for Remote compatibility
    """
    device_id = str(g.device_id) if g.device_id else f"collector_key:{getattr(g, 'collector_key', None) and g.collector_key.id or 'unknown'}"
    site_id = g.site_id
    now = datetime.utcnow()
    
    TERMINAL_STATES = {'completed', 'failed', 'expired', 'cancelled', 'superseded'}
    
    command = MinerCommand.query.get(command_id)
    if not command:
        remote_cmd = RemoteCommand.query.get(command_id)
        if remote_cmd:
            return _handle_remote_command_ack(remote_cmd, command_id)
        return jsonify({
            'error': 'Command not found',
            'error_code': 'COMMAND_NOT_FOUND'
        }), 404
    
    command_source = 'miner'
    
    if command.site_id != site_id:
        return jsonify({
            'error': 'Access denied',
            'error_code': 'ACCESS_DENIED'
        }), 403
    
    data = request.get_json() or {}
    ack_status = data.get('status', 'completed')
    ack_nonce = data.get('ack_nonce')
    client_signature = data.get('signature')
    result_code = data.get('result_code')
    result_message = data.get('result_message')
    execution_time_ms = data.get('execution_time_ms') or data.get('duration_ms')
    enable_signature = os.environ.get('ENABLE_COMMAND_SIGNATURE', '').lower() == 'true'
    
    # Verify nonce matches dispatch_nonce (replay detection) - only if client sent it
    # This is optional for backward compatibility with legacy edge collectors
    if ack_nonce and command.dispatch_nonce and ack_nonce != command.dispatch_nonce:
        log_audit_event(
            event_type='command.ack_nonce_mismatch',
            actor_type='device',
            actor_id=device_id,
            site_id=site_id,
            ref_type='miner_command',
            ref_id=command_id,
            payload={
                'expected_nonce': command.dispatch_nonce,
                'received_nonce': ack_nonce
            }
        )
        return jsonify({
            'error': 'Nonce mismatch - possible replay attack',
            'error_code': 'NONCE_MISMATCH'
        }), 401
    
    # Verify signature if enabled and provided - only if client sent it
    # This is optional for backward compatibility with legacy edge collectors
    if enable_signature and client_signature and command.signature:
        if client_signature != command.signature:
            log_audit_event(
                event_type='command.ack_signature_invalid',
                actor_type='device',
                actor_id=device_id,
                site_id=site_id,
                ref_type='miner_command',
                ref_id=command_id,
                payload={
                    'signature_mismatch': True
                }
            )
            return jsonify({
                'error': 'Signature verification failed',
                'error_code': 'SIGNATURE_INVALID'
            }), 401
    
    # Log when legacy client doesn't send nonce or signature
    if not ack_nonce and not client_signature:
        logger.info(f"ACK accepted without signature/nonce verification (legacy client) for command {command_id} from device {device_id}")
    
    ack_payload = json.dumps({
        'command_id': command_id,
        'device_id': device_id,
        'status': ack_status,
        'nonce': ack_nonce
    }, sort_keys=True)
    computed_ack_hash = hashlib.sha256(ack_payload.encode()).hexdigest()
    
    if command.status in TERMINAL_STATES:
        log_audit_event(
            event_type='command.ack_replayed',
            actor_type='device',
            actor_id=device_id,
            site_id=site_id,
            ref_type='miner_command',
            ref_id=command_id,
            payload={
                'current_status': command.status,
                'ack_status': ack_status,
                'existing_ack_hash': command.ack_hash
            }
        )
        return jsonify({
            'acknowledged': True,
            'command_source': command_source,
            'command_status': command.status,
            'replayed': True,
            'terminal_at': command.terminal_at.isoformat() + 'Z' if command.terminal_at else None,
            'info': 'Command already in terminal state'
        })
    
    if command.lease_owner and command.lease_owner != device_id:
        log_audit_event(
            event_type='command.ack_not_lease_owner',
            actor_type='device',
            actor_id=device_id,
            site_id=site_id,
            ref_type='miner_command',
            ref_id=command_id,
            payload={
                'actual_lease_owner': command.lease_owner,
                'requesting_device': device_id
            }
        )
        return jsonify({
            'error': 'Not the lease owner for this command',
            'error_code': 'ACK_NOT_LEASE_OWNER',
            'lease_owner': command.lease_owner
        }), 409
    
    if command.expires_at and command.expires_at < now:
        command.status = 'expired'
        command.terminal_at = now
        command.lease_owner = None
        command.lease_until = None
        db.session.commit()
        
        log_audit_event(
            event_type='command.expired',
            actor_type='device',
            actor_id=device_id,
            site_id=site_id,
            ref_type='miner_command',
            ref_id=command_id,
            payload={'expired_at': command.expires_at.isoformat()}
        )
        
        # Synchronize RemoteCommand status if this MinerCommand is linked to one
        if command.remote_command_id:
            _sync_remote_command_status(command.remote_command_id)
        
        return jsonify({
            'error': 'Command has expired',
            'error_code': 'COMMAND_EXPIRED',
            'command_status': 'expired',
            'expired_at': command.expires_at.isoformat() + 'Z'
        }), 410
    
    command.executed_at = now
    command.result_code = result_code
    command.result_message = result_message
    command.edge_device_id = device_id
    command.ack_hash = computed_ack_hash
    if execution_time_ms:
        command.execution_time_ms = execution_time_ms
    
    command.lease_owner = None
    command.lease_until = None
    
    final_status = None
    should_retry = False
    
    if ack_status == 'completed' or ack_status == 'succeeded':
        command.status = 'completed'
        command.terminal_at = now
        final_status = 'completed'
        
        log_audit_event(
            event_type='command.completed',
            actor_type='device',
            actor_id=device_id,
            site_id=site_id,
            ref_type='miner_command',
            ref_id=command_id,
            payload={
                'execution_time_ms': execution_time_ms,
                'result_code': result_code
            }
        )
        
        inc_commands_acked(site_id, command.command_type, 'succeeded')
        
    elif ack_status == 'failed':
        if command.retry_count < command.max_retries:
            command.retry_count += 1
            backoff = command.retry_backoff_sec * (2 ** command.retry_count)
            command.next_attempt_at = now + timedelta(seconds=backoff)
            command.status = 'pending'
            should_retry = True
            final_status = 'pending_retry'
            
            log_audit_event(
                event_type='command.retried',
                actor_type='device',
                actor_id=device_id,
                site_id=site_id,
                ref_type='miner_command',
                ref_id=command_id,
                payload={
                    'retry_count': command.retry_count,
                    'max_retries': command.max_retries,
                    'next_attempt_at': command.next_attempt_at.isoformat(),
                    'backoff_seconds': backoff,
                    'error_code': result_code,
                    'error_message': result_message
                }
            )
        else:
            command.status = 'failed'
            command.terminal_at = now
            final_status = 'failed'
            
            log_audit_event(
                event_type='command.failed',
                actor_type='device',
                actor_id=device_id,
                site_id=site_id,
                ref_type='miner_command',
                ref_id=command_id,
                payload={
                    'retry_count': command.retry_count,
                    'max_retries': command.max_retries,
                    'error_code': result_code,
                    'error_message': result_message
                }
            )
            
            inc_commands_failed(site_id, command.command_type, result_code or 'UNKNOWN')
        
        inc_commands_acked(site_id, command.command_type, 'failed')
    else:
        command.status = ack_status
        if ack_status in TERMINAL_STATES:
            command.terminal_at = now
        final_status = ack_status
    
    db.session.commit()
    
    # Synchronize RemoteCommand status if this MinerCommand is linked to one
    MINER_TERMINAL_STATES = {'completed', 'failed', 'expired', 'cancelled', 'superseded'}
    if command.remote_command_id and command.status in MINER_TERMINAL_STATES:
        _sync_remote_command_status(command.remote_command_id)
    
    response = {
        'acknowledged': True,
        'command_source': command_source,
        'command_id': command_id,
        'command_status': command.status,
        'final_status': final_status,
    }
    
    if should_retry:
        response['will_retry'] = True
        response['retry_count'] = command.retry_count
        response['max_retries'] = command.max_retries
        response['next_attempt_at'] = command.next_attempt_at.isoformat() + 'Z'
    
    if command.terminal_at:
        response['terminal_at'] = command.terminal_at.isoformat() + 'Z'
    
    return jsonify(response)


def _handle_remote_command_ack(command, command_id):
    """Handle ACK for RemoteCommand (legacy compatibility)"""
    if command.site_id != g.site_id:
        return jsonify({'error': 'Access denied', 'error_code': 'ACCESS_DENIED'}), 403
    
    data = request.get_json() or {}
    results = data.get('results', [])
    
    all_succeeded = True
    for r in results:
        asset_id = r.get('asset_id')
        status = r.get('status', 'SUCCEEDED')
        
        existing = RemoteCommandResult.query.filter_by(
            command_id=command_id,
            target_miner_id=str(asset_id)
        ).first()
        
        if existing:
            continue
        
        ack_device_id = g.device_id if g.device_id else f"collector_key:{getattr(g, 'collector_key', None) and g.collector_key.id or 'unknown'}"
        result = RemoteCommandResult(
            command_id=command_id,
            target_miner_id=str(asset_id),
            executed_by_device_id=ack_device_id,
            result_status=status,
            before_snapshot=r.get('before_snapshot'),
            after_snapshot=r.get('after_snapshot'),
            error_code=r.get('error_code') or r.get('error_class'),
            error_message=r.get('error_message') or r.get('error'),
            started_at=datetime.fromisoformat(r['started_at'].replace('Z', '')) if r.get('started_at') else datetime.utcnow(),
            finished_at=datetime.fromisoformat(r['finished_at'].replace('Z', '')) if r.get('finished_at') else datetime.utcnow(),
        )
        db.session.add(result)
        
        if status != 'SUCCEEDED':
            all_succeeded = False
    
    total_targets = len(command.target_ids) if command.target_ids else CommandTarget.query.filter_by(command_id=command_id).count()
    completed_count = RemoteCommandResult.query.filter_by(command_id=command_id).count()
    
    if completed_count >= total_targets:
        command.status = 'SUCCEEDED' if all_succeeded else 'FAILED'
        command.updated_at = datetime.utcnow()
    elif command.status == 'QUEUED':
        command.status = 'RUNNING'
        command.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    ack_actor_id = g.device_id if g.device_id else f"collector_key:{getattr(g, 'collector_key', None) and g.collector_key.id or 'unknown'}"
    log_audit_event(
        event_type='command.ack',
        actor_type='edge',
        actor_id=ack_actor_id,
        site_id=command.site_id,
        ref_type='command',
        ref_id=command_id,
        payload={'results_count': len(results), 'final_status': command.status}
    )
    
    return jsonify({
        'acknowledged': True,
        'command_source': 'remote',
        'command_status': command.status,
    })


@control_plane_bp.route('/api/edge/v1/telemetry/ingest', methods=['POST'])
@control_plane_bp.route('/api/edge/v1/telemetry/batch', methods=['POST'])
@require_edge_auth
def edge_ingest_telemetry():
    """Ingest telemetry from edge - supports gzip, envelope, and plain JSON"""
    import gzip as gzip_mod
    
    received_at = datetime.utcnow()
    warnings = []
    
    try:
        if request.headers.get('Content-Encoding') == 'gzip':
            raw_data = gzip_mod.decompress(request.data)
            data = json.loads(raw_data.decode('utf-8'))
        else:
            data = request.get_json(force=True)
    except Exception as e:
        return jsonify({'error': f'Invalid payload: {e}', 'error_code': 'INVALID_PAYLOAD'}), 400
    
    if data is None:
        return jsonify({'error': 'Empty payload', 'error_code': 'EMPTY_PAYLOAD'}), 400
    
    source = 'v1'
    zone_id = g.zone_id
    device_id = str(g.device_id) if g.device_id else None
    edge_meta = {'device_id': device_id, 'zone_id': zone_id}
    
    if isinstance(data, list):
        records = data
        source = 'legacy'
    elif isinstance(data, dict):
        schema = data.get('schema', '')
        
        if data.get('payload_enc') and not data.get('records'):
            return jsonify({'error': 'ENCRYPTED_PAYLOAD_UNSUPPORTED', 'error_code': 'ENCRYPTED_PAYLOAD_UNSUPPORTED'}), 422
        
        if schema == 'telemetry_envelope.v1' or 'records' in data:
            records = data.get('records', [])
            envelope_site_id = data.get('site_id')
            envelope_zone_id = data.get('zone_id')
            envelope_record_count = data.get('record_count')
            
            if envelope_zone_id:
                zone_id = envelope_zone_id
                edge_meta['zone_id'] = zone_id
            
            if envelope_site_id and str(envelope_site_id) != str(g.site_id):
                warnings.append(f'envelope.site_id={envelope_site_id} differs from auth site_id={g.site_id}, using auth site_id')
            
            if envelope_record_count is not None and envelope_record_count != len(records):
                warnings.append(f'envelope.record_count={envelope_record_count} != actual records={len(records)}')
            
            edge_meta['sent_at'] = data.get('sent_at')
            edge_meta['source_seq_start'] = data.get('source_seq_start')
            edge_meta['source_seq_end'] = data.get('source_seq_end')
        elif 'telemetry' in data:
            records = data.get('telemetry', [])
            source = 'legacy'
        else:
            return jsonify({'error': 'Unrecognized payload format', 'error_code': 'UNKNOWN_FORMAT'}), 400
    else:
        return jsonify({'error': 'Payload must be JSON array or object', 'error_code': 'INVALID_FORMAT'}), 400
    
    if not records:
        return jsonify({
            'success': True, 'processed': 0, 'received_at': received_at.isoformat() + 'Z',
            'source': source, 'site_id': g.site_id, 'zone_id': zone_id,
            'device_id': device_id, 'warnings': warnings
        })
    
    from services.edge_ingest_service import ingest_miner_records
    result = ingest_miner_records(
        site_id=g.site_id,
        records=records,
        received_at=received_at,
        source=source,
        edge_meta=edge_meta
    )
    
    warnings.extend(result.get('errors', []))
    
    return jsonify({
        'success': True,
        'processed': result['processed_count'],
        'received_at': received_at.isoformat() + 'Z',
        'source': source,
        'site_id': g.site_id,
        'zone_id': zone_id,
        'device_id': device_id,
        'warnings': warnings
    })


@control_plane_bp.route('/api/edge/v1/events/safety/batch', methods=['POST'])
@require_device_auth
def edge_safety_events_batch():
    """
    Receive batch of safety events from edge collector.
    
    POST body:
    {
        "events": [
            {
                "miner_id": 123,
                "action": "THERMAL_SHUTDOWN",
                "reason": "Temperature exceeded 95C threshold",
                "temp_max": 98.5,
                "ts": "2026-01-18T10:30:00Z",
                "snapshot_json": {...}
            }
        ]
    }
    """
    from api.collector_api import SafetyEvent
    
    data = request.get_json() or {}
    events = data.get('events', [])
    
    if not events:
        return jsonify({'error': 'No events provided'}), 400
    
    device_id = g.device_id
    site_id = g.site_id
    edge_device = g.device
    
    received_at = datetime.utcnow()
    processed_count = 0
    error_count = 0
    errors = []
    
    for event_data in events:
        try:
            miner_id = event_data.get('miner_id')
            action = event_data.get('action')
            reason = event_data.get('reason')
            temp_max = event_data.get('temp_max')
            ts_str = event_data.get('ts')
            snapshot_json = event_data.get('snapshot_json')
            
            # Validate required fields
            if not action:
                error_count += 1
                errors.append({'miner_id': miner_id, 'error': 'action is required'})
                continue
            
            if not reason:
                error_count += 1
                errors.append({'miner_id': miner_id, 'error': 'reason is required'})
                continue
            
            if not ts_str:
                error_count += 1
                errors.append({'miner_id': miner_id, 'error': 'ts is required'})
                continue
            
            # Parse timestamp
            try:
                event_ts = datetime.fromisoformat(ts_str.replace('Z', ''))
            except (ValueError, AttributeError):
                error_count += 1
                errors.append({'miner_id': miner_id, 'error': f'Invalid timestamp format: {ts_str}'})
                continue
            
            # Convert snapshot_json to string if it's a dict
            snapshot_str = None
            if snapshot_json:
                if isinstance(snapshot_json, dict):
                    snapshot_str = json.dumps(snapshot_json)
                else:
                    snapshot_str = str(snapshot_json)
            
            # Create safety event record
            safety_event = SafetyEvent(
                edge_device_id=device_id,
                site_id=site_id,
                miner_id=miner_id,
                action=action,
                reason=reason,
                temp_max=temp_max,
                ts=event_ts,
                snapshot_json=snapshot_str
            )
            
            db.session.add(safety_event)
            processed_count += 1
            
            # Log audit event for each safety event
            log_audit_event(
                event_type=f'safety.event.{action.lower()}',
                actor_type='edge_device',
                actor_id=device_id,
                site_id=site_id,
                ref_type='safety_event',
                ref_id=None,
                payload={
                    'miner_id': miner_id,
                    'action': action,
                    'reason': reason,
                    'temp_max': temp_max,
                    'event_ts': event_ts.isoformat()
                }
            )
        
        except Exception as e:
            logger.error(f"Error processing safety event: {e}")
            error_count += 1
            errors.append({'miner_id': event_data.get('miner_id'), 'error': str(e)})
            continue
    
    # Commit all valid events
    if processed_count > 0:
        try:
            db.session.commit()
            logger.info(f"Processed {processed_count} safety events from device {device_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit safety events: {e}")
            return jsonify({
                'error': 'Failed to save events',
                'processed': 0,
                'failed': len(events)
            }), 500
    
    response = {
        'processed': processed_count,
        'failed': error_count,
        'received_at': received_at.isoformat() + 'Z',
        'device_id': device_id,
        'site_id': site_id,
    }
    
    if errors:
        response['errors'] = errors
    
    status_code = 200 if error_count == 0 else 207
    return jsonify(response), status_code


@control_plane_bp.route('/api/v1/commands/propose', methods=['POST'])
@require_user_auth
@require_customer_access
def propose_command():
    """Propose a new command"""
    data = request.get_json() or {}
    
    site_id = data.get('site_id')
    zone_id = data.get('zone_id')
    command_type = data.get('command_type')
    payload = data.get('payload', {})
    target_ids = data.get('target_ids', [])
    ttl_seconds = data.get('ttl_seconds', 86400)
    
    if not site_id or not command_type:
        return jsonify({'error': 'site_id and command_type required'}), 400
    
    if 'ip' in str(payload).lower():
        return jsonify({'error': 'IP addresses are not allowed in cloud'}), 400
    
    site = HostingSite.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    if g.customer_filter:
        customer_assets = MinerAsset.query.filter_by(customer_id=g.customer_id).all()
        allowed_ids = {a.id for a in customer_assets}
        if not all(tid in allowed_ids for tid in target_ids):
            log_audit_event('access.denied', 'user', g.user_id, site_id, 'command', None, {'reason': 'ABAC violation'})
            return jsonify({'error': 'Access denied - ABAC violation'}), 403
    
    risk_tier = RISK_TIER_MAP.get(command_type, 'MEDIUM')
    est_kw_impact = len(target_ids) * 3.5
    approval_req = get_approval_requirement(site_id, command_type, len(target_ids), est_kw_impact)
    
    initial_status = 'PENDING_APPROVAL' if approval_req['require_approval'] else 'QUEUED'
    
    command = RemoteCommand(
        id=str(uuid.uuid4()),
        tenant_id=g.user_id,
        site_id=site_id,
        requested_by_user_id=g.user_id,
        requested_by_role=g.user_role,
        command_type=command_type,
        payload_json=payload,
        target_ids=target_ids,
        status=initial_status,
        require_approval=approval_req['require_approval'],
        expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
    )
    
    if zone_id:
        command.zone_id = zone_id
    
    db.session.add(command)
    
    for tid in target_ids:
        target = CommandTarget(command_id=command.id, asset_id=tid)
        db.session.add(target)
    
    db.session.commit()
    
    log_audit_event(
        event_type='command.proposed',
        actor_type='user',
        actor_id=g.user_id,
        site_id=site_id,
        ref_type='command',
        ref_id=command.id,
        payload={
            'command_type': command_type,
            'target_count': len(target_ids),
            'risk_tier': risk_tier,
            'require_dual_approval': approval_req['require_dual_approval'],
        }
    )
    
    return jsonify({
        'success': True,
        'command_id': command.id,
        'status': command.status,
        'require_approval': approval_req['require_approval'],
        'require_dual_approval': approval_req['require_dual_approval'],
        'steps_required': approval_req['steps_required'],
    }), 201


@control_plane_bp.route('/api/v1/commands/<command_id>/approve', methods=['POST'])
@require_user_auth
@require_customer_access
def approve_command(command_id):
    """Approve a pending command"""
    command = RemoteCommand.query.get(command_id)
    if not command:
        return jsonify({'error': 'Command not found'}), 404
    
    if command.status not in ('PENDING', 'PENDING_APPROVAL'):
        return jsonify({'error': f'Command cannot be approved in status {command.status}'}), 400
    
    if g.customer_filter:
        targets = CommandTarget.query.filter_by(command_id=command_id).all()
        customer_assets = MinerAsset.query.filter_by(customer_id=g.customer_id).all()
        allowed_ids = {a.id for a in customer_assets}
        if not all(t.asset_id in allowed_ids for t in targets):
            return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json() or {}
    reason = data.get('reason', '')
    step = data.get('step', 1)
    
    existing_approval = CommandApproval.query.filter_by(
        command_id=command_id,
        approver_user_id=g.user_id,
        decision='APPROVE'
    ).first()
    if existing_approval:
        return jsonify({'error': 'You have already approved this command'}), 400
    
    approval = CommandApproval(
        command_id=command_id,
        approver_user_id=g.user_id,
        decision='APPROVE',
        reason=reason,
        step=step,
    )
    db.session.add(approval)
    
    approval_req = get_approval_requirement(
        command.site_id, 
        command.command_type, 
        len(command.target_ids) if command.target_ids else 0,
        0
    )
    
    current_approvals = CommandApproval.query.filter_by(
        command_id=command_id,
        decision='APPROVE'
    ).count() + 1
    
    if current_approvals >= approval_req['steps_required']:
        command.status = 'QUEUED'
        command.approved_by_user_id = g.user_id
        command.approved_at = datetime.utcnow()
    
    command.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_audit_event(
        event_type='command.approved',
        actor_type='user',
        actor_id=g.user_id,
        site_id=command.site_id,
        ref_type='command',
        ref_id=command_id,
        payload={'step': step, 'reason': reason, 'new_status': command.status}
    )
    
    return jsonify({
        'success': True,
        'command_status': command.status,
        'approvals_count': current_approvals,
        'steps_required': approval_req['steps_required'],
    })


@control_plane_bp.route('/api/v1/commands/<command_id>/deny', methods=['POST'])
@require_user_auth
@require_customer_access
def deny_command(command_id):
    """Deny a pending command"""
    command = RemoteCommand.query.get(command_id)
    if not command:
        return jsonify({'error': 'Command not found'}), 404
    
    if command.status not in ('PENDING', 'PENDING_APPROVAL'):
        return jsonify({'error': f'Command cannot be denied in status {command.status}'}), 400
    
    data = request.get_json() or {}
    reason = data.get('reason', '')
    
    approval = CommandApproval(
        command_id=command_id,
        approver_user_id=g.user_id,
        decision='DENY',
        reason=reason,
        step=1,
    )
    db.session.add(approval)
    
    command.status = 'CANCELLED'
    command.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_audit_event(
        event_type='command.denied',
        actor_type='user',
        actor_id=g.user_id,
        site_id=command.site_id,
        ref_type='command',
        ref_id=command_id,
        payload={'reason': reason}
    )
    
    return jsonify({'success': True, 'command_status': command.status})


@control_plane_bp.route('/api/v1/commands/<command_id>/rollback', methods=['POST'])
@require_user_auth
@require_customer_access
def rollback_command(command_id):
    """Create a rollback command for a previously executed command.
    
    Rollback also requires approval based on the same risk tier as the original command.
    """
    original_command = RemoteCommand.query.get(command_id)
    if not original_command:
        return jsonify({'error': 'Command not found'}), 404
    
    # Only completed/succeeded commands can be rolled back
    rollback_eligible_statuses = ('COMPLETED', 'PARTIAL', 'SUCCEEDED', 'FAILED')
    if original_command.status not in rollback_eligible_statuses:
        return jsonify({
            'error': f'Cannot rollback command in status {original_command.status}. Only commands in terminal states ({", ".join(rollback_eligible_statuses)}) can be rolled back.'
        }), 400
    
    data = request.get_json() or {}
    reason = data.get('reason', 'User requested rollback')
    
    # Get original targets
    original_targets = CommandTarget.query.filter_by(command_id=command_id).all()
    target_asset_ids = [t.asset_id for t in original_targets]
    
    if not target_asset_ids:
        return jsonify({'error': 'No targets found for original command'}), 400
    
    # Create rollback command with ROLLBACK action type
    rollback_command_id = str(uuid.uuid4())
    
    # Inherit risk tier from original command (rollbacks are equally risky)
    original_risk_tier = RISK_TIER_MAP.get(original_command.command_type, 'MEDIUM')
    
    rollback_cmd = RemoteCommand(
        id=rollback_command_id,
        tenant_id=g.user_id,
        site_id=original_command.site_id,
        requested_by_user_id=g.user_id,
        requested_by_role=g.user_role,
        command_type='ROLLBACK',
        payload_json={
            'original_command_id': command_id,
            'original_action': original_command.command_type,
            'reason': reason,
        },
        target_ids=target_asset_ids,
        status='PENDING_APPROVAL',
        require_approval=True,
    )
    db.session.add(rollback_cmd)
    
    # Create targets for rollback command
    for asset_id in target_asset_ids:
        target = CommandTarget(
            command_id=rollback_command_id,
            asset_id=asset_id,
        )
        db.session.add(target)
    
    db.session.commit()
    
    # Get approval requirement for rollback (same as original risk tier)
    approval_req = get_approval_requirement(
        original_command.site_id,
        'ROLLBACK',
        len(target_asset_ids)
    )
    
    log_audit_event(
        event_type='command.rollback_proposed',
        actor_type='user',
        actor_id=g.user_id,
        site_id=original_command.site_id,
        ref_type='command',
        ref_id=rollback_command_id,
        payload={
            'original_command_id': command_id,
            'original_action': original_command.command_type,
            'target_count': len(target_asset_ids),
            'reason': reason,
            'approval_required': approval_req,
        }
    )
    
    return jsonify({
        'success': True,
        'rollback_command_id': rollback_command_id,
        'original_command_id': command_id,
        'status': 'PENDING_APPROVAL',
        'approval_required': approval_req,
        'message': 'Rollback command created. Approval required before execution.',
    }), 201


@control_plane_bp.route('/api/v1/commands/<command_id>', methods=['GET'])
@require_user_auth
@require_customer_access
def get_command(command_id):
    """Get command details"""
    command = RemoteCommand.query.get(command_id)
    if not command:
        return jsonify({'error': 'Command not found'}), 404
    
    if g.customer_filter:
        targets = CommandTarget.query.filter_by(command_id=command_id).all()
        customer_assets = MinerAsset.query.filter_by(customer_id=g.customer_id).all()
        allowed_ids = {a.id for a in customer_assets}
        if not any(t.asset_id in allowed_ids for t in targets):
            return jsonify({'error': 'Access denied'}), 403
    
    approvals = CommandApproval.query.filter_by(command_id=command_id).all()
    
    return jsonify({
        'command': command.to_dict(include_results=True),
        'approvals': [a.to_dict() for a in approvals],
    })


@control_plane_bp.route('/api/v1/commands', methods=['GET'])
@require_user_auth
@require_customer_access
def list_commands():
    """List commands with filters"""
    site_id = request.args.get('site_id', type=int)
    zone_id = request.args.get('zone_id', type=int)
    status = request.args.get('status')
    limit = min(request.args.get('limit', 50, type=int), 200)
    offset = request.args.get('offset', 0, type=int)
    
    query = RemoteCommand.query
    
    if site_id:
        query = query.filter(RemoteCommand.site_id == site_id)
    if zone_id:
        query = query.filter(RemoteCommand.zone_id == zone_id)
    if status:
        query = query.filter(RemoteCommand.status == status)
    
    if g.customer_filter:
        customer_assets = MinerAsset.query.filter_by(customer_id=g.customer_id).all()
        asset_ids = [a.id for a in customer_assets]
        command_ids = db.session.query(CommandTarget.command_id).filter(
            CommandTarget.asset_id.in_(asset_ids)
        ).distinct().subquery()
        query = query.filter(RemoteCommand.id.in_(command_ids))
    
    total = query.count()
    commands = query.order_by(RemoteCommand.created_at.desc()).offset(offset).limit(limit).all()
    
    return jsonify({
        'commands': [c.to_dict() for c in commands],
        'total': total,
        'limit': limit,
        'offset': offset,
    })


@control_plane_bp.route('/api/v1/price-plans/upload', methods=['POST'])
@require_user_auth
def upload_price_plan():
    """Upload price plan (CSV or JSON)"""
    site_id = request.form.get('site_id', type=int) or request.args.get('site_id', type=int)
    plan_name = request.form.get('plan_name') or request.args.get('plan_name', 'Default Plan')
    effective_from = request.form.get('effective_from') or request.args.get('effective_from')
    missing_policy = request.form.get('missing_data_policy', 'carry_forward')
    
    if not site_id:
        return jsonify({'error': 'site_id required'}), 400
    
    site = HostingSite.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    file = request.files.get('file')
    json_data = request.get_json() if request.is_json else None
    
    if not file and not json_data:
        return jsonify({'error': 'File or JSON data required'}), 400
    
    try:
        if file:
            content = file.read().decode('utf-8')
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            file_name = file.filename
            
            if file.filename.endswith('.csv'):
                reader = csv.DictReader(StringIO(content))
                payload = list(reader)
            else:
                payload = json.loads(content)
        else:
            payload = json_data.get('rates', json_data)
            file_hash = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
            file_name = 'api_upload.json'
        
        plan = PricePlan.query.filter_by(site_id=site_id, name=plan_name).first()
        if not plan:
            plan = PricePlan(site_id=site_id, name=plan_name)
            db.session.add(plan)
            db.session.flush()
        
        max_version = db.session.query(db.func.max(PricePlanVersion.version_number)).filter_by(
            price_plan_id=plan.id
        ).scalar() or 0
        
        effective_dt = datetime.fromisoformat(effective_from) if effective_from else datetime.utcnow()
        
        version = PricePlanVersion(
            price_plan_id=plan.id,
            version_number=max_version + 1,
            effective_from=effective_dt,
            source_file_hash=file_hash,
            source_file_name=file_name,
            missing_data_policy=missing_policy,
            payload_json=payload,
            created_by=g.user_id,
        )
        db.session.add(version)
        db.session.commit()
        
        log_audit_event(
            event_type='price_plan.uploaded',
            actor_type='user',
            actor_id=g.user_id,
            site_id=site_id,
            ref_type='price_plan_version',
            ref_id=version.version_id,
            payload={
                'plan_name': plan_name,
                'version_number': version.version_number,
                'file_hash': file_hash,
                'missing_policy': missing_policy,
            }
        )
        
        return jsonify({
            'success': True,
            'price_plan_id': plan.price_plan_id,
            'version_id': version.version_id,
            'version_number': version.version_number,
        }), 201
        
    except Exception as e:
        logger.error(f"Price plan upload error: {e}")
        return jsonify({'error': str(e)}), 400


@control_plane_bp.route('/api/v1/price-plans/<plan_id>/versions', methods=['GET'])
@require_user_auth
def list_price_plan_versions(plan_id):
    """List versions of a price plan"""
    plan = PricePlan.query.filter_by(price_plan_id=plan_id).first()
    if not plan:
        plan = PricePlan.query.get(plan_id)
    if not plan:
        return jsonify({'error': 'Price plan not found'}), 404
    
    versions = PricePlanVersion.query.filter_by(price_plan_id=plan.id).order_by(
        PricePlanVersion.version_number.desc()
    ).all()
    
    return jsonify({
        'plan': plan.to_dict(),
        'versions': [v.to_dict() for v in versions],
    })


@control_plane_bp.route('/api/v1/demand/monthly-ledger', methods=['GET'])
@require_user_auth
def get_monthly_ledger():
    """Get monthly demand ledger"""
    site_id = request.args.get('site_id', type=int)
    year = request.args.get('year', type=int) or datetime.utcnow().year
    month = request.args.get('month', type=int) or datetime.utcnow().month
    
    if not site_id:
        return jsonify({'error': 'site_id required'}), 400
    
    ledger = DemandLedgerMonthly.query.filter_by(
        site_id=site_id,
        year=year,
        month=month,
    ).first()
    
    if not ledger:
        return jsonify({
            'ledger': None,
            'message': 'No data for this period',
        })
    
    return jsonify({
        'ledger': ledger.to_dict(),
    })


@control_plane_bp.route('/api/v1/demand/replay', methods=['POST'])
@require_user_auth
def demand_replay():
    """What-if simulation for demand charge"""
    data = request.get_json() or {}
    
    site_id = data.get('site_id')
    year = data.get('year', datetime.utcnow().year)
    month = data.get('month', datetime.utcnow().month)
    price_plan_version_id = data.get('price_plan_version_id')
    simulation_params = data.get('simulation_params', {})
    
    if not site_id:
        return jsonify({'error': 'site_id required'}), 400
    
    current_ledger = DemandLedgerMonthly.query.filter_by(
        site_id=site_id,
        year=year,
        month=month,
    ).first()
    
    current_peak = current_ledger.peak_kw if current_ledger else 0
    current_demand_charge = current_ledger.demand_charge_usd if current_ledger else 0
    
    demand_records = Demand15Min.query.filter(
        Demand15Min.site_id == site_id,
        db.extract('year', Demand15Min.window_start) == year,
        db.extract('month', Demand15Min.window_start) == month,
    ).all()
    
    power_reduction_pct = simulation_params.get('power_reduction_pct', 0)
    curtailment_hours = simulation_params.get('curtailment_hours', [])
    
    simulated_peak = current_peak
    if power_reduction_pct > 0:
        for record in demand_records:
            hour = record.window_start.hour
            if not curtailment_hours or hour in curtailment_hours:
                adjusted_power = record.avg_power_kw * (1 - power_reduction_pct / 100)
                if adjusted_power < simulated_peak:
                    simulated_peak = adjusted_power
    
    if price_plan_version_id:
        version = PricePlanVersion.query.filter_by(version_id=price_plan_version_id).first()
        if version and version.payload_json:
            demand_rate = version.payload_json.get('demand_rate_per_kw', 15)
            simulated_demand_charge = simulated_peak * demand_rate
        else:
            simulated_demand_charge = simulated_peak * 15
    else:
        simulated_demand_charge = simulated_peak * 15
    
    log_audit_event(
        event_type='demand.replay',
        actor_type='user',
        actor_id=g.user_id,
        site_id=site_id,
        ref_type='demand_replay',
        ref_id=None,
        payload={
            'year': year,
            'month': month,
            'simulation_params': simulation_params,
        }
    )
    
    return jsonify({
        'current': {
            'peak_kw': current_peak,
            'demand_charge_usd': current_demand_charge,
        },
        'simulated': {
            'peak_kw': simulated_peak,
            'demand_charge_usd': simulated_demand_charge,
        },
        'delta': {
            'peak_kw_reduction': current_peak - simulated_peak,
            'demand_charge_savings': current_demand_charge - simulated_demand_charge,
        },
    })


@control_plane_bp.route('/api/v1/zones', methods=['GET'])
@require_user_auth
def list_zones():
    """List zones for a site"""
    site_id = request.args.get('site_id', type=int)
    if not site_id:
        return jsonify({'error': 'site_id required'}), 400
    
    zones = Zone.query.filter_by(site_id=site_id, is_active=True).all()
    return jsonify({'zones': [z.to_dict() for z in zones]})


@control_plane_bp.route('/api/v1/zones', methods=['POST'])
@require_user_auth
def create_zone():
    """Create a new zone"""
    data = request.get_json() or {}
    
    site_id = data.get('site_id')
    name = data.get('name')
    
    if not site_id or not name:
        return jsonify({'error': 'site_id and name required'}), 400
    
    zone = Zone(
        site_id=site_id,
        name=name,
        zone_type=data.get('zone_type', 'room'),
        description=data.get('description'),
        capacity_kw=data.get('capacity_kw', 0),
        energy_source=data.get('energy_source', 'grid'),
    )
    db.session.add(zone)
    db.session.commit()
    
    log_audit_event(
        event_type='zone.created',
        actor_type='user',
        actor_id=g.user_id,
        site_id=site_id,
        ref_type='zone',
        ref_id=zone.zone_id,
        payload={'name': name}
    )
    
    return jsonify({'success': True, 'zone': zone.to_dict()}), 201


@control_plane_bp.route('/api/v1/audit/events', methods=['GET'])
@require_user_auth
def list_audit_events():
    """List audit events"""
    site_id = request.args.get('site_id', type=int)
    event_type = request.args.get('event_type')
    limit = min(request.args.get('limit', 100, type=int), 1000)
    offset = request.args.get('offset', 0, type=int)
    
    query = AuditEvent.query
    
    if site_id:
        query = query.filter(AuditEvent.site_id == site_id)
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    
    total = query.count()
    events = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit).all()
    
    return jsonify({
        'events': [e.to_dict() for e in events],
        'total': total,
    })


@control_plane_bp.route('/api/v1/audit/export', methods=['GET'])
@require_user_auth
def export_audit_events():
    """Export audit events as JSON"""
    site_id = request.args.get('site_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = AuditEvent.query
    
    if site_id:
        query = query.filter(AuditEvent.site_id == site_id)
    if start_date:
        query = query.filter(AuditEvent.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(AuditEvent.created_at <= datetime.fromisoformat(end_date))
    
    events = query.order_by(AuditEvent.created_at.asc()).all()
    
    from flask import Response
    export_data = json.dumps([e.to_dict() for e in events], indent=2)
    
    return Response(
        export_data,
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=audit_export.json'}
    )


def register_control_plane_routes(app):
    """Register control plane routes"""
    app.register_blueprint(control_plane_bp)
    logger.info("Control Plane API registered successfully")
