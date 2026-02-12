"""
Remote Miner Control API - COMPATIBILITY LAYER
远程矿机控制 - 兼容层 (已弃用，请迁移到 /api/v1/commands)

**DEPRECATION NOTICE**
This API is deprecated and will be removed on 2026-06-01.
Please migrate to the v1 Control Plane API:
  - POST /api/v1/commands/propose (replaces /api/sites/<site_id>/commands POST)
  - GET /api/v1/commands (replaces /api/sites/<site_id>/commands GET)
  - GET /api/v1/commands/<id> (replaces /api/commands/<id> GET)
  - POST /api/v1/commands/<id>/deny (replaces /api/commands/<id>/cancel)
  - POST /api/v1/commands/<id>/approve (unchanged)

All endpoints in this file forward to v1 Control Plane internally.
Deprecation header: Deprecation-Date: 2026-06-01

RBAC权限矩阵:
- REMOTE_CONTROL_REQUEST: Owner/Admin/Mining_Site_Owner/Client = FULL, Customer/Guest = NONE
- REMOTE_CONTROL_AUDIT: Owner/Admin/Mining_Site_Owner = FULL, Client/Customer = READ, Guest = NONE
- REMOTE_CONTROL_EXECUTE: Owner/Admin/Mining_Site_Owner = FULL, others NONE
"""

import os
import logging
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, g, session

from db import db
from models import UserAccess, HostingSite, HostingMiner
from models_device_encryption import EdgeDevice
from models_remote_control import (
    RemoteCommand, RemoteCommandResult, 
    CommandType, CommandStatus, ResultStatus,
    COMMAND_PAYLOAD_SCHEMAS
)
from common.rbac import requires_module_access, Module, AccessLevel, check_site_access

logger = logging.getLogger(__name__)

remote_control_bp = Blueprint('remote_control', __name__)

@remote_control_bp.before_request
def log_request_info():
    """Log request info before RBAC check (minimal logging for production)"""
    logger.debug(f"[REMOTE_CONTROL_BP] Request: {request.method} {request.path}, "
                 f"user_id={session.get('user_id')}, role={session.get('role')}")

REMOTE_CONTROL_ENABLED = os.environ.get('REMOTE_CONTROL_ENABLED', 'true').lower() == 'true'
COMMAND_EXPIRY_HOURS = int(os.environ.get('COMMAND_EXPIRY_HOURS', '24'))
MAX_BATCH_SIZE_USER = 10
MAX_BATCH_SIZE_ADMIN = 100

DEPRECATION_DATE = '2026-06-01'
DEPRECATION_MESSAGE = 'This endpoint is deprecated. Please migrate to /api/v1/commands. See docs/COMMAND_API_CONVERGENCE.md'


def add_deprecation_headers(response):
    """Add deprecation headers to response"""
    response.headers['Deprecation'] = f'date="{DEPRECATION_DATE}"'
    response.headers['Sunset'] = 'Sat, 01 Jun 2026 00:00:00 GMT'
    response.headers['Link'] = '</api/v1/commands>; rel="successor-version"'
    return response


def make_deprecated_response(data, status_code=200):
    """Create a response with deprecation warning included"""
    if isinstance(data, dict):
        data['_deprecation'] = {
            'warning': DEPRECATION_MESSAGE,
            'sunset_date': DEPRECATION_DATE,
            'migration_guide': '/docs/COMMAND_API_CONVERGENCE.md',
            'new_endpoint': '/api/v1/commands'
        }
    response = jsonify(data)
    response.status_code = status_code
    return add_deprecation_headers(response)


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
    """Require edge device token authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Device token required'}), 401
        
        token = auth_header[7:]
        device = EdgeDevice.query.filter_by(device_token=token, status='ACTIVE').first()
        if not device:
            return jsonify({'error': 'Invalid or revoked device token'}), 401
        
        device.last_seen_at = datetime.utcnow()
        db.session.commit()
        
        g.device = device
        g.device_id = device.id
        g.site_id = device.site_id
        return f(*args, **kwargs)
    return decorated


def validate_payload(command_type: str, payload: dict) -> tuple:
    """Validate command payload against schema"""
    schema = COMMAND_PAYLOAD_SCHEMAS.get(command_type)
    if not schema:
        return False, f"Unknown command type: {command_type}"
    
    required = schema.get('required', [])
    properties = schema.get('properties', {})
    
    for field in required:
        if field not in payload:
            return False, f"Missing required field: {field}"
    
    for field, value in payload.items():
        if field in properties:
            prop_schema = properties[field]
            if prop_schema.get('type') == 'string' and 'enum' in prop_schema:
                if value not in prop_schema['enum']:
                    return False, f"Invalid value for {field}: {value}. Allowed: {prop_schema['enum']}"
            if prop_schema.get('type') == 'integer':
                if not isinstance(value, int):
                    return False, f"Field {field} must be an integer"
                if 'minimum' in prop_schema and value < prop_schema['minimum']:
                    return False, f"Field {field} must be >= {prop_schema['minimum']}"
                if 'maximum' in prop_schema and value > prop_schema['maximum']:
                    return False, f"Field {field} must be <= {prop_schema['maximum']}"
    
    return True, None


def log_command_event(command: RemoteCommand, action: str, extra_data: dict = None):
    """Log command event for audit - unified with v1 Control Plane audit"""
    try:
        from models_control_plane import AuditEvent
        import hashlib
        
        event_type_map = {
            'create': 'command.proposed.legacy',
            'cancel': 'command.cancelled.legacy',
            'approve': 'command.approved.legacy',
        }
        event_type = event_type_map.get(action, f'command.{action}.legacy')
        
        payload = {
            'command_id': command.id,
            'command_type': command.command_type,
            'target_ids': command.target_ids,
            'status': command.status,
            'action': action,
            'source': 'legacy_api',
            'deprecation_notice': DEPRECATION_MESSAGE,
        }
        if extra_data:
            payload.update(extra_data)
        
        last_event = AuditEvent.query.order_by(AuditEvent.id.desc()).first()
        prev_hash = last_event.event_hash if last_event else '0' * 64
        
        event = AuditEvent(
            event_type=event_type,
            actor_type='user',
            actor_id=getattr(g, 'user_id', None),
            site_id=command.site_id,
            ref_type='remote_command',
            ref_id=str(command.id),
            payload=payload,
            ip_address=request.remote_addr,
            prev_hash=prev_hash,
        )
        
        hash_input = f"{event.event_type}:{event.actor_id}:{event.ref_id}:{prev_hash}"
        event.event_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        db.session.add(event)
        db.session.commit()
        
    except Exception as e:
        logger.warning(f"Failed to log audit event: {e}")
        try:
            from audit.audit_logger import AuditLogger, AuditCategory, AuditAction
            AuditLogger.log(
                category=AuditCategory.DATA_MODIFICATION,
                action=AuditAction.UPDATE if action != 'create' else AuditAction.CREATE,
                resource_type='remote_command',
                resource_id=command.id,
                user_id=getattr(g, 'user_id', None),
                details={'action': action, 'command_type': command.command_type},
                ip_address=request.remote_addr
            )
        except Exception as e2:
            logger.error(f"Fallback audit also failed: {e2}")


@remote_control_bp.route('/api/sites/<int:site_id>/commands', methods=['POST'])
@requires_module_access(Module.REMOTE_CONTROL_REQUEST, require_full=True)
def create_command(site_id):
    """Create a new remote control command
    
    RBAC权限: REMOTE_CONTROL_REQUEST
    - Owner/Admin/Mining_Site_Owner/Client: FULL (可以提交命令)
    - Customer/Guest: NONE (无权限)
    """
    import traceback
    
    try:
        return _create_command_impl(site_id)
    except Exception as e:
        logger.error(f"[create_command] Unhandled exception for user_id={session.get('user_id')}, site_id={site_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'error': 'An unexpected error occurred. Please try again later.', 'error_code': 'INTERNAL_ERROR'}), 500


def _create_command_impl(site_id):
    """Internal implementation of create_command"""
    if not REMOTE_CONTROL_ENABLED:
        return jsonify({'error': 'Remote control is disabled'}), 503
    
    # 获取用户信息
    user_id = session.get('user_id')
    user_role_str = session.get('role', 'user')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    # 设置 g.user_id 供后续使用
    g.user_id = user_id
    if not hasattr(g, 'user_role') or g.user_role is None:
        g.user_role = user_role_str
    
    site = HostingSite.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    # 验证用户是否有权访问该站点
    if not check_site_access(site_id):
        logger.warning(f"User {session.get('email')} attempted to control site {site_id} without access")
        return jsonify({'error': 'Access denied: You do not have permission to control this site'}), 403
    
    if not site.remote_control_enabled:
        logger.warning(f"Remote control disabled for site {site_id} ({site.name}), rejecting command from user {session.get('email')}")
        return jsonify({
            'error': 'Remote control is disabled for this site',
            'error_code': 'SITE_RC_DISABLED',
            'message_zh': '该站点已关闭远程控制功能'
        }), 403
    
    data = request.get_json() or {}
    
    command_type = data.get('command_type')
    if command_type not in [ct.value for ct in CommandType]:
        return jsonify({'error': f'Invalid command_type. Allowed: {[ct.value for ct in CommandType]}'}), 400
    
    payload = data.get('payload', {})
    valid, error = validate_payload(command_type, payload)
    if not valid:
        return jsonify({'error': error}), 400
    
    target_scope = data.get('target_scope', 'MINER')
    target_ids = data.get('target_ids', [])
    
    if not target_ids:
        return jsonify({'error': 'target_ids required'}), 400
    
    user_role_check = g.user_role if isinstance(g.user_role, str) else (g.user_role.value if hasattr(g.user_role, 'value') else str(g.user_role))
    is_admin = user_role_check in ('admin', 'owner')
    max_batch = MAX_BATCH_SIZE_ADMIN if is_admin else MAX_BATCH_SIZE_USER
    
    if len(target_ids) > max_batch:
        return jsonify({'error': f'Batch size exceeds limit ({max_batch})'}), 400
    
    require_approval = False
    if not is_admin:
        if len(target_ids) > MAX_BATCH_SIZE_USER:
            require_approval = True
        if command_type == 'REBOOT' and payload.get('mode') == 'hard' and len(target_ids) > 1:
            require_approval = True
    
    idempotency_key = data.get('idempotency_key')
    if idempotency_key:
        existing = RemoteCommand.query.filter_by(
            tenant_id=g.user_id,
            requested_by_user_id=g.user_id,
            idempotency_key=idempotency_key
        ).first()
        if existing:
            return jsonify({'command': existing.to_dict(include_results=True)}), 200
    
    logger.info(f"Creating remote command: user_id={g.user_id}, site_id={site_id}, type={command_type}, targets={target_ids}")
    
    try:
        command = RemoteCommand(
            tenant_id=g.user_id,
            site_id=site_id,
            requested_by_user_id=g.user_id,
            requested_by_role=user_role_check,
            command_type=command_type,
            payload_json=payload,
            target_scope=target_scope,
            target_ids=target_ids,
            status='PENDING_APPROVAL' if require_approval else 'QUEUED',
            require_approval=require_approval,
            idempotency_key=idempotency_key,
            expires_at=datetime.utcnow() + timedelta(hours=COMMAND_EXPIRY_HOURS)
        )
        
        db.session.add(command)
        db.session.flush()
        logger.info(f"Remote command created with id={command.id}")
        
        for miner_id in target_ids:
            result = RemoteCommandResult(
                command_id=command.id,
                miner_id=str(miner_id),
                result_status='PENDING'
            )
            db.session.add(result)
        
        db.session.commit()
        logger.info(f"Remote command committed successfully: {command.id}")
    except Exception as e:
        db.session.rollback()
        import traceback
        logger.error(f"Error creating remote command: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    
    log_command_event(command, 'create')
    
    return make_deprecated_response({
        'success': True,
        'command': command.to_dict(include_results=True),
        'message': 'Command queued' if not require_approval else 'Command pending approval'
    }, 201)


@remote_control_bp.route('/api/sites/<int:site_id>/commands', methods=['GET'])
@requires_module_access(Module.REMOTE_CONTROL_AUDIT)
def list_commands(site_id):
    """List commands for a site
    
    RBAC权限: REMOTE_CONTROL_AUDIT
    - Owner/Admin/Mining_Site_Owner: FULL (完整访问)
    - Client/Customer: READ (只读访问)
    - Guest: NONE (无权限)
    """
    site = HostingSite.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    # 验证用户是否有权访问该站点
    if not check_site_access(site_id):
        return jsonify({'error': 'Access denied: You do not have permission to view commands for this site'}), 403
    
    status = request.args.get('status')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    query = RemoteCommand.query.filter_by(site_id=site_id)
    
    if status:
        query = query.filter_by(status=status)
    
    total = query.count()
    commands = query.order_by(RemoteCommand.created_at.desc()).offset(offset).limit(limit).all()
    
    return make_deprecated_response({
        'commands': [cmd.to_dict(include_results=True) for cmd in commands],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@remote_control_bp.route('/api/commands/<command_id>', methods=['GET'])
@requires_module_access(Module.REMOTE_CONTROL_AUDIT)
def get_command(command_id):
    """Get command details
    
    RBAC权限: REMOTE_CONTROL_AUDIT
    - Owner/Admin/Mining_Site_Owner: FULL (完整访问)
    - Client/Customer: READ (只读访问)
    - Guest: NONE (无权限)
    """
    command = RemoteCommand.query.get(command_id)
    if not command:
        return make_deprecated_response({'error': 'Command not found'}, 404)
    
    return make_deprecated_response({'command': command.to_dict(include_results=True)})


@remote_control_bp.route('/api/commands/<command_id>/cancel', methods=['POST'])
@requires_module_access(Module.REMOTE_CONTROL_REQUEST, require_full=True)
def cancel_command(command_id):
    """Cancel a pending command
    
    RBAC权限: REMOTE_CONTROL_REQUEST
    - Owner/Admin/Mining_Site_Owner/Client: FULL (可以取消命令)
    - Customer/Guest: NONE (无权限)
    """
    command = RemoteCommand.query.get(command_id)
    if not command:
        return make_deprecated_response({'error': 'Command not found'}, 404)
    
    if not command.can_cancel():
        return make_deprecated_response({'error': f'Cannot cancel command in {command.status} status'}, 400)
    
    command.status = 'CANCELLED'
    command.updated_at = datetime.utcnow()
    
    RemoteCommandResult.query.filter_by(command_id=command_id, result_status='PENDING').update({
        'result_status': 'SKIPPED',
        'result_message': 'Command cancelled'
    })
    
    db.session.commit()
    
    log_command_event(command, 'cancel')
    
    return make_deprecated_response({
        'success': True,
        'command': command.to_dict(include_results=True)
    })


@remote_control_bp.route('/api/commands/<command_id>/approve', methods=['POST'])
@requires_module_access(Module.REMOTE_CONTROL_EXECUTE, require_full=True)
def approve_command(command_id):
    """Approve a pending command (admin only)
    
    RBAC权限: REMOTE_CONTROL_EXECUTE
    - Owner/Admin/Mining_Site_Owner: FULL (可以批准执行)
    - 其他角色: NONE (无权限)
    
    审批后自动调度到 MinerCommand 队列，供 Edge Collector 轮询
    """
    
    command = RemoteCommand.query.get(command_id)
    if not command:
        return make_deprecated_response({'error': 'Command not found'}, 404)
    
    site = HostingSite.query.get(command.site_id)
    if site and not site.remote_control_enabled:
        logger.warning(f"Remote control disabled for site {command.site_id} ({site.name}), rejecting approval from user {session.get('email')}")
        return jsonify({
            'error': 'Remote control is disabled for this site',
            'error_code': 'SITE_RC_DISABLED',
            'message_zh': '该站点已关闭远程控制功能'
        }), 403
    
    if command.status != 'PENDING_APPROVAL':
        return make_deprecated_response({'error': f'Command not pending approval (status={command.status})'}, 400)
    
    command.status = 'QUEUED'
    command.approved_by_user_id = g.user_id
    command.approved_at = datetime.utcnow()
    command.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    dispatch_result = None
    try:
        from services.command_dispatcher import dispatch_remote_command
        success_list, error_list = dispatch_remote_command(
            remote_command_id=command.id,
            site_id=command.site_id,
            target_ids=command.target_ids,
            command_type=command.command_type,
            parameters=command.payload_json,
            operator_id=g.user_id,
            expires_at=command.expires_at
        )
        dispatch_result = {
            'dispatched': len(success_list),
            'errors': len(error_list),
            'error_details': error_list if error_list else None
        }
        logger.info(f"Dispatched RemoteCommand {command_id}: {len(success_list)} commands, {len(error_list)} errors")
    except Exception as e:
        logger.error(f"Failed to dispatch commands: {e}")
        dispatch_result = {'error': str(e)}
    
    log_command_event(command, 'approve', {'approved_by': g.user_id, 'dispatch': dispatch_result})
    
    response_data = command.to_dict(include_results=True)
    response_data['dispatch'] = dispatch_result
    
    return make_deprecated_response({
        'success': True,
        'command': response_data
    })


# =============================================================================
# DEPRECATED: v1 Edge endpoints removed - use control_plane_api.py instead
# The following endpoints have been moved to api/control_plane_api.py:
#   - GET /api/edge/v1/commands/poll
#   - POST /api/edge/v1/commands/<command_id>/ack
# This ensures single control plane with no secrets/IP leakage
# =============================================================================


def register_blueprint(app):
    """Register the remote control blueprint with the Flask app"""
    app.register_blueprint(remote_control_bp)
    logger.info("Remote Control API blueprint registered")
