"""
Portal Lite API - 客户门户（严格隔离）
只读 + 审批 + 报表下载

Endpoints:
- GET /api/v1/portal/my-miners
- GET /api/v1/portal/my-approvals
- POST /api/v1/portal/approvals/{command_id}/approve
- POST /api/v1/portal/approvals/{command_id}/deny
- GET /api/v1/portal/my-reports
"""
import logging
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g, session

from db import db
from models import UserAccess
from models_control_plane import (
    HostingCustomer, MinerAsset, CommandApproval, CommandTarget, AuditEvent
)
from models_remote_control import RemoteCommand

logger = logging.getLogger(__name__)

portal_bp = Blueprint('portal_lite', __name__, url_prefix='/api/v1/portal')


def require_customer_auth(f):
    """Require customer authentication with strict isolation"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id or not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        customer = HostingCustomer.query.filter_by(user_id=user_id, is_active=True).first()
        if not customer:
            return jsonify({'error': 'No customer profile found'}), 403
        
        g.user = user
        g.user_id = user.id
        g.customer = customer
        g.customer_id = customer.id
        g.site_id = customer.site_id
        return f(*args, **kwargs)
    return decorated


def log_portal_audit(event_type, ref_type=None, ref_id=None, payload=None):
    """Log portal audit event"""
    try:
        last_event = AuditEvent.query.order_by(AuditEvent.id.desc()).first()
        prev_hash = last_event.event_hash if last_event else '0' * 64
        
        event = AuditEvent(
            site_id=g.site_id,
            actor_type='customer',
            actor_id=str(g.customer_id),
            event_type=f'portal.{event_type}',
            ref_type=ref_type,
            ref_id=str(ref_id) if ref_id else None,
            payload_json=payload or {},
            prev_hash=prev_hash,
        )
        event.event_hash = event.compute_hash()
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        logger.error(f"Portal audit log error: {e}")


@portal_bp.route('/my-miners', methods=['GET'])
@require_customer_auth
def my_miners():
    """Get customer's miners only"""
    miners = MinerAsset.query.filter_by(
        customer_id=g.customer_id,
        is_active=True
    ).all()
    
    return jsonify({
        'miners': [m.to_dict() for m in miners],
        'total': len(miners),
        'customer_id': g.customer.customer_id,
    })


@portal_bp.route('/my-approvals', methods=['GET'])
@require_customer_auth
def my_approvals():
    """Get pending approvals for customer's assets"""
    customer_assets = MinerAsset.query.filter_by(customer_id=g.customer_id).all()
    asset_ids = [a.id for a in customer_assets]
    
    if not asset_ids:
        return jsonify({'pending': [], 'total': 0})
    
    command_ids = db.session.query(CommandTarget.command_id).filter(
        CommandTarget.asset_id.in_(asset_ids)
    ).distinct().all()
    command_ids = [c[0] for c in command_ids]
    
    pending_commands = RemoteCommand.query.filter(
        RemoteCommand.id.in_(command_ids),
        RemoteCommand.status.in_(['PENDING', 'PENDING_APPROVAL'])
    ).order_by(RemoteCommand.created_at.desc()).all()
    
    result = []
    for cmd in pending_commands:
        targets = CommandTarget.query.filter_by(command_id=cmd.id).all()
        my_targets = [t for t in targets if t.asset_id in asset_ids]
        
        approvals = CommandApproval.query.filter_by(command_id=cmd.id).all()
        
        result.append({
            'command_id': cmd.id,
            'command_type': cmd.command_type,
            'status': cmd.status,
            'created_at': cmd.created_at.isoformat() + 'Z' if cmd.created_at else None,
            'expires_at': cmd.expires_at.isoformat() + 'Z' if cmd.expires_at else None,
            'my_affected_assets': len(my_targets),
            'total_targets': len(targets),
            'approvals': [a.to_dict() for a in approvals],
        })
    
    return jsonify({
        'pending': result,
        'total': len(result),
    })


@portal_bp.route('/approvals/<command_id>/approve', methods=['POST'])
@require_customer_auth
def portal_approve(command_id):
    """Customer approves a command affecting their assets"""
    command = RemoteCommand.query.get(command_id)
    if not command:
        return jsonify({'error': 'Command not found'}), 404
    
    if command.status not in ('PENDING', 'PENDING_APPROVAL'):
        return jsonify({'error': f'Cannot approve in status {command.status}'}), 400
    
    targets = CommandTarget.query.filter_by(command_id=command_id).all()
    customer_assets = MinerAsset.query.filter_by(customer_id=g.customer_id).all()
    asset_ids = {a.id for a in customer_assets}
    
    if not any(t.asset_id in asset_ids for t in targets):
        log_portal_audit('access_denied', 'command', command_id, {'reason': 'No owned assets in targets'})
        return jsonify({'error': 'Access denied - command does not affect your assets'}), 403
    
    existing = CommandApproval.query.filter_by(
        command_id=command_id,
        approver_user_id=g.user_id,
        decision='APPROVE'
    ).first()
    if existing:
        return jsonify({'error': 'Already approved'}), 400
    
    data = request.get_json() or {}
    
    approval = CommandApproval(
        command_id=command_id,
        approver_user_id=g.user_id,
        decision='APPROVE',
        reason=data.get('reason', ''),
        step=1,
    )
    db.session.add(approval)
    
    approval_count = CommandApproval.query.filter_by(
        command_id=command_id,
        decision='APPROVE'
    ).count() + 1
    
    if approval_count >= 1 and not command.require_approval:
        command.status = 'QUEUED'
        command.approved_by_user_id = g.user_id
        command.approved_at = datetime.utcnow()
    elif approval_count >= 1:
        command.status = 'QUEUED'
        command.approved_by_user_id = g.user_id
        command.approved_at = datetime.utcnow()
    
    command.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_portal_audit('approved', 'command', command_id, {'new_status': command.status})
    
    return jsonify({
        'success': True,
        'command_status': command.status,
    })


@portal_bp.route('/approvals/<command_id>/deny', methods=['POST'])
@require_customer_auth
def portal_deny(command_id):
    """Customer denies a command"""
    command = RemoteCommand.query.get(command_id)
    if not command:
        return jsonify({'error': 'Command not found'}), 404
    
    targets = CommandTarget.query.filter_by(command_id=command_id).all()
    customer_assets = MinerAsset.query.filter_by(customer_id=g.customer_id).all()
    asset_ids = {a.id for a in customer_assets}
    
    if not any(t.asset_id in asset_ids for t in targets):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json() or {}
    
    approval = CommandApproval(
        command_id=command_id,
        approver_user_id=g.user_id,
        decision='DENY',
        reason=data.get('reason', ''),
        step=1,
    )
    db.session.add(approval)
    
    command.status = 'CANCELLED'
    command.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_portal_audit('denied', 'command', command_id, {'reason': data.get('reason')})
    
    return jsonify({
        'success': True,
        'command_status': command.status,
    })


@portal_bp.route('/my-reports', methods=['GET'])
@require_customer_auth
def my_reports():
    """Get available reports for customer"""
    customer_assets = MinerAsset.query.filter_by(customer_id=g.customer_id).count()
    
    reports = [
        {
            'report_type': 'sla_summary',
            'name': 'SLA Summary Report',
            'description': 'Monthly uptime and performance summary',
            'available': True,
            'download_url': f'/api/v1/portal/reports/sla?customer_id={g.customer_id}',
        },
        {
            'report_type': 'shadow_bill',
            'name': 'Shadow Bill',
            'description': 'Estimated electricity costs breakdown',
            'available': True,
            'download_url': f'/api/v1/portal/reports/shadow-bill?customer_id={g.customer_id}',
        },
        {
            'report_type': 'audit_summary',
            'name': 'Audit Summary',
            'description': 'Actions and changes affecting your assets',
            'available': True,
            'download_url': f'/api/v1/portal/reports/audit?customer_id={g.customer_id}',
        },
    ]
    
    return jsonify({
        'reports': reports,
        'total_assets': customer_assets,
        'customer_id': g.customer.customer_id,
    })


@portal_bp.route('/my-stats', methods=['GET'])
@require_customer_auth
def my_stats():
    """Get customer dashboard stats"""
    miners = MinerAsset.query.filter_by(customer_id=g.customer_id, is_active=True).all()
    
    total_hashrate = sum(m.hashrate_th or 0 for m in miners)
    total_power = sum(m.power_w or 0 for m in miners)
    
    pending_commands = db.session.query(RemoteCommand).join(
        CommandTarget, RemoteCommand.id == CommandTarget.command_id
    ).filter(
        CommandTarget.asset_id.in_([m.id for m in miners]),
        RemoteCommand.status.in_(['PENDING', 'PENDING_APPROVAL'])
    ).count()
    
    return jsonify({
        'total_miners': len(miners),
        'total_hashrate_th': total_hashrate,
        'total_power_w': total_power,
        'pending_approvals': pending_commands,
    })


def register_portal_routes(app):
    """Register portal routes"""
    app.register_blueprint(portal_bp)
    logger.info("Portal Lite API registered successfully")
