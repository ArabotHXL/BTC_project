"""
Legacy API Adapter - 旧接口兼容层
将旧的 /api/collector/commands/* 接口代理到新的 v1 接口

DEPRECATED: These endpoints are for migration only.
Will be removed after 2026-06-01.
"""
import logging
import warnings
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g

from db import db
from models_device_encryption import EdgeDevice
from models_remote_control import RemoteCommand, RemoteCommandResult
from models_control_plane import CommandTarget, AuditEvent

logger = logging.getLogger(__name__)

legacy_bp = Blueprint('legacy_adapter', __name__, url_prefix='/api/collector')

DEPRECATION_NOTICE = "DEPRECATED: This endpoint will be removed after 2026-06-01. Please migrate to /api/edge/v1/*"


def deprecated_endpoint(f):
    """Mark endpoint as deprecated"""
    @wraps(f)
    def decorated(*args, **kwargs):
        warnings.warn(DEPRECATION_NOTICE, DeprecationWarning, stacklevel=2)
        logger.warning(f"Deprecated endpoint called: {request.path}")
        
        response = f(*args, **kwargs)
        
        if isinstance(response, tuple):
            data, status = response
            if isinstance(data, dict):
                data['_deprecated'] = True
                data['_deprecation_notice'] = DEPRECATION_NOTICE
                return jsonify(data), status
        
        return response
    return decorated


def require_legacy_device_auth(f):
    """Legacy device authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        api_key = request.headers.get('X-API-Key', '')
        
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif api_key:
            token = api_key
        
        if not token:
            return jsonify({'error': 'Device token required', '_deprecated': True}), 401
        
        device = EdgeDevice.query.filter_by(device_token=token, status='ACTIVE').first()
        if not device:
            return jsonify({'error': 'Invalid token', '_deprecated': True}), 401
        
        device.last_seen_at = datetime.utcnow()
        db.session.commit()
        
        g.device = device
        g.device_id = device.id
        g.site_id = device.site_id
        return f(*args, **kwargs)
    return decorated


@legacy_bp.route('/commands/pending', methods=['GET'])
@deprecated_endpoint
@require_legacy_device_auth
def legacy_poll_commands():
    """
    DEPRECATED: Legacy command polling.
    Proxies to /api/edge/v1/commands/poll
    """
    site_id = g.site_id
    
    commands = RemoteCommand.query.filter(
        RemoteCommand.site_id == site_id,
        RemoteCommand.status == 'QUEUED',
        RemoteCommand.expires_at > datetime.utcnow()
    ).order_by(RemoteCommand.created_at.asc()).limit(10).all()
    
    result = []
    for cmd in commands:
        targets = CommandTarget.query.filter_by(command_id=cmd.id).all()
        target_ids = [t.asset_id for t in targets] if targets else cmd.target_ids
        
        result.append({
            'id': cmd.id,
            'command_id': cmd.id,
            'type': cmd.command_type,
            'command_type': cmd.command_type,
            'payload': cmd.payload_json,
            'target_ids': target_ids,
            'miner_ids': target_ids,
            'created_at': cmd.created_at.isoformat() + 'Z' if cmd.created_at else None,
        })
    
    return jsonify({
        'commands': result,
        'count': len(result),
        '_deprecated': True,
        '_deprecation_notice': DEPRECATION_NOTICE,
    }), 200


@legacy_bp.route('/commands/<command_id>/result', methods=['POST'])
@deprecated_endpoint
@require_legacy_device_auth
def legacy_submit_result(command_id):
    """
    DEPRECATED: Legacy result submission.
    Proxies to /api/edge/v1/commands/{id}/ack
    """
    command = RemoteCommand.query.get(command_id)
    if not command:
        return jsonify({'error': 'Command not found', '_deprecated': True}), 404
    
    if command.site_id != g.site_id:
        return jsonify({'error': 'Access denied', '_deprecated': True}), 403
    
    data = request.get_json() or {}
    
    miner_id = data.get('miner_id') or data.get('asset_id')
    status = data.get('status', 'SUCCEEDED')
    error = data.get('error') or data.get('error_message')
    
    existing = RemoteCommandResult.query.filter_by(
        command_id=command_id,
        target_miner_id=str(miner_id)
    ).first()
    
    if not existing:
        result = RemoteCommandResult(
            command_id=command_id,
            target_miner_id=str(miner_id),
            executed_by_device_id=g.device_id,
            result_status=status.upper() if status else 'SUCCEEDED',
            error_message=error,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        db.session.add(result)
    
    total_targets = len(command.target_ids) if command.target_ids else 1
    completed = RemoteCommandResult.query.filter_by(command_id=command_id).count()
    
    if completed >= total_targets:
        failed_count = RemoteCommandResult.query.filter_by(
            command_id=command_id,
            result_status='FAILED'
        ).count()
        command.status = 'FAILED' if failed_count > 0 else 'SUCCEEDED'
    elif command.status == 'QUEUED':
        command.status = 'RUNNING'
    
    command.updated_at = datetime.utcnow()
    db.session.commit()
    
    try:
        last_event = AuditEvent.query.order_by(AuditEvent.id.desc()).first()
        prev_hash = last_event.event_hash if last_event else '0' * 64
        event = AuditEvent(
            site_id=command.site_id,
            actor_type='edge',
            actor_id=str(g.device_id),
            event_type='legacy.command.result',
            ref_type='command',
            ref_id=command_id,
            payload_json={'miner_id': miner_id, 'status': status},
            prev_hash=prev_hash,
        )
        event.event_hash = event.compute_hash()
        db.session.add(event)
        db.session.commit()
    except:
        pass
    
    return jsonify({
        'success': True,
        'command_status': command.status,
        '_deprecated': True,
        '_deprecation_notice': DEPRECATION_NOTICE,
    }), 200


@legacy_bp.route('/health', methods=['GET'])
@deprecated_endpoint
def legacy_health():
    """DEPRECATED: Health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        '_deprecated': True,
        '_deprecation_notice': DEPRECATION_NOTICE,
    }), 200


def register_legacy_routes(app):
    """Register legacy adapter routes"""
    app.register_blueprint(legacy_bp)
    logger.info("Legacy adapter routes registered (DEPRECATED)")
