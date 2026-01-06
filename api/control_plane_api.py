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
@require_device_auth
def edge_poll_commands():
    """Poll for queued commands - only returns approved commands
    
    Zone binding: Device token is bound to (site_id, zone_id).
    If zone_id param provided, it must match device's zone_id (validation only).
    """
    site_id = g.site_id
    device_zone_id = g.zone_id
    requested_zone_id = request.args.get('zone_id', type=int)
    limit = min(request.args.get('limit', 10, type=int), 50)
    
    if requested_zone_id and device_zone_id and requested_zone_id != device_zone_id:
        log_audit_event(
            event_type='security.zone_access_denied',
            actor_type='device',
            actor_id=g.device_id,
            site_id=site_id,
            payload={'requested_zone': requested_zone_id, 'bound_zone': device_zone_id}
        )
        return jsonify({'error': 'Zone access denied - device bound to different zone'}), 403
    
    zone_id = device_zone_id or requested_zone_id
    
    query = RemoteCommand.query.filter(
        RemoteCommand.site_id == site_id,
        RemoteCommand.status == 'QUEUED',
        RemoteCommand.expires_at > datetime.utcnow()
    )
    
    if zone_id:
        query = query.filter(RemoteCommand.zone_id == zone_id)
    
    commands = query.order_by(RemoteCommand.created_at.asc()).limit(limit).all()
    
    result = []
    for cmd in commands:
        targets = CommandTarget.query.filter_by(command_id=cmd.id).all()
        result.append({
            'command_id': cmd.id,
            'command_type': cmd.command_type,
            'payload': cmd.payload_json,
            'target_asset_ids': [t.asset_id for t in targets] if targets else cmd.target_ids,
            'created_at': cmd.created_at.isoformat() + 'Z',
            'expires_at': cmd.expires_at.isoformat() + 'Z' if cmd.expires_at else None,
        })
    
    return jsonify({
        'commands': result,
        'server_time': datetime.utcnow().isoformat() + 'Z',
    })


@control_plane_bp.route('/api/edge/v1/commands/<command_id>/ack', methods=['POST'])
@require_device_auth
def edge_ack_command(command_id):
    """Acknowledge command completion - idempotent"""
    command = RemoteCommand.query.get(command_id)
    if not command:
        return jsonify({'error': 'Command not found'}), 404
    
    if command.site_id != g.site_id:
        return jsonify({'error': 'Access denied'}), 403
    
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
        
        result = RemoteCommandResult(
            command_id=command_id,
            target_miner_id=str(asset_id),
            executed_by_device_id=g.device_id,
            result_status=status,
            before_snapshot=r.get('before_snapshot'),
            after_snapshot=r.get('after_snapshot'),
            error_code=r.get('error_code'),
            error_message=r.get('error_message'),
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
    
    log_audit_event(
        event_type='command.ack',
        actor_type='edge',
        actor_id=g.device_id,
        site_id=command.site_id,
        ref_type='command',
        ref_id=command_id,
        payload={'results_count': len(results), 'final_status': command.status}
    )
    
    return jsonify({
        'acknowledged': True,
        'command_status': command.status,
    })


@control_plane_bp.route('/api/edge/v1/telemetry/ingest', methods=['POST'])
@require_device_auth
def edge_ingest_telemetry():
    """Ingest telemetry batch from edge"""
    data = request.get_json() or {}
    telemetry_batch = data.get('telemetry', [])
    client_timestamp = data.get('client_timestamp')
    
    received_at = datetime.utcnow()
    is_delayed = False
    if client_timestamp:
        try:
            client_dt = datetime.fromisoformat(client_timestamp.replace('Z', ''))
            delay_seconds = (received_at - client_dt).total_seconds()
            is_delayed = delay_seconds > 300
        except:
            pass
    
    processed = 0
    for item in telemetry_batch:
        asset_id = item.get('asset_id')
        if not asset_id:
            continue
        processed += 1
    
    return jsonify({
        'processed': processed,
        'received_at': received_at.isoformat() + 'Z',
        'is_delayed': is_delayed,
    })


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
