"""
Credential Protection API - 凭证保护相关接口
支持 reveal、update-credential、batch-migrate 操作
"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from functools import wraps
from db import db
from models import HostingSite, HostingMiner
from models_control_plane import AuditEvent
from services.credential_protection_service import credential_service


credential_protection_bp = Blueprint('credential_protection', __name__)


def require_auth(f):
    """验证用户登录"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """验证管理员权限"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        role = session.get('role', 'viewer')
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401
        if role not in ('admin', 'owner'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def log_audit_event(site_id, event_type, actor_id, ref_type, ref_id, payload=None, require_success=False):
    """记录审计事件（增强版，确保审计事件不会丢失）"""
    import logging
    try:
        last_event = AuditEvent.query.filter_by(site_id=site_id).order_by(AuditEvent.id.desc()).first()
        prev_hash = last_event.event_hash if last_event else '0' * 64
        
        event = AuditEvent(
            site_id=site_id,
            actor_type='user',
            actor_id=str(actor_id),
            event_type=event_type,
            ref_type=ref_type,
            ref_id=str(ref_id),
            payload_json=payload or {},
            prev_hash=prev_hash
        )
        event.event_hash = event.compute_hash()
        db.session.add(event)
        db.session.commit()
        logging.info(f"Audit event logged: {event_type} for {ref_type}/{ref_id}")
        return event
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to log audit event {event_type}: {e}")
        if require_success:
            raise RuntimeError(f"Audit logging failed: {e}")
        return None


@credential_protection_bp.route('/api/v1/sites/<int:site_id>/security-settings', methods=['GET'])
@require_auth
def get_site_security_settings(site_id):
    """获取站点安全设置"""
    site = HostingSite.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    mode_names = {1: 'UI Masking', 2: 'Server Envelope', 3: 'Device E2EE'}
    
    return jsonify({
        'site_id': site_id,
        'name': site.name,
        'ip_mode': site.ip_mode,
        'mode_name': mode_names.get(site.ip_mode, 'Unknown'),
        'has_dek': bool(site.site_dek_wrapped),
        'mode_descriptions': {
            1: 'UI脱敏：明文存储，通过角色控制显示',
            2: '服务器加密：使用站点密钥加密，管理员可解密',
            3: '设备端加密：端到端加密，服务器无法解密'
        }
    })


@credential_protection_bp.route('/api/v1/sites/<int:site_id>/security-settings', methods=['POST'])
@require_admin
def update_site_security_settings(site_id):
    """更新站点安全模式"""
    site = HostingSite.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    data = request.get_json()
    new_mode = data.get('ip_mode')
    
    if new_mode not in (1, 2, 3):
        return jsonify({'error': 'Invalid mode, must be 1, 2, or 3'}), 400
    
    old_mode = site.ip_mode
    site.ip_mode = new_mode
    
    log_audit_event(
        site_id=site_id,
        event_type='CHANGE_MODE',
        actor_id=session.get('user_id'),
        ref_type='site',
        ref_id=site_id,
        payload={'old_mode': old_mode, 'new_mode': new_mode}
    )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'site_id': site_id,
        'old_mode': old_mode,
        'new_mode': new_mode,
        'message': f'Security mode changed from {old_mode} to {new_mode}'
    })


@credential_protection_bp.route('/api/v1/miners/<int:miner_id>/credential', methods=['GET'])
@require_auth
def get_miner_credential_display(miner_id):
    """获取矿机凭证显示信息（脱敏）"""
    miner = HostingMiner.query.get(miner_id)
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    site = HostingSite.query.get(miner.site_id)
    role = session.get('role', 'viewer')
    
    display_info = credential_service.get_display_value(miner, site, role)
    
    return jsonify({
        'miner_id': miner_id,
        'serial_number': miner.serial_number,
        'credential': display_info,
        'last_accepted_counter': miner.last_accepted_counter,
        'fingerprint': miner.fingerprint
    })


@credential_protection_bp.route('/api/v1/miners/<int:miner_id>/reveal', methods=['POST'])
@require_admin
def reveal_miner_credential(miner_id):
    """揭示矿机凭证（仅管理员，敏感模式需要原因）"""
    miner = HostingMiner.query.get(miner_id)
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    site = HostingSite.query.get(miner.site_id)
    
    data = request.get_json() or {}
    reason = data.get('reason', '').strip()
    
    if miner.credential_mode in (2, 3) and len(reason) < 10:
        return jsonify({
            'error': 'Detailed reason (10+ chars) is required for encrypted credentials reveal',
            'code': 'REASON_REQUIRED'
        }), 400
    
    actor_id = session.get('user_id')
    
    audit_event = log_audit_event(
        site_id=miner.site_id,
        event_type='REVEAL',
        actor_id=actor_id,
        ref_type='miner',
        ref_id=miner_id,
        payload={
            'reason': reason,
            'mode': miner.credential_mode
        },
        require_success=True
    )
    
    if not audit_event:
        return jsonify({
            'error': 'Audit logging failed - reveal blocked for security',
            'code': 'AUDIT_REQUIRED'
        }), 500
    
    result = credential_service.reveal_credential(miner, site, reason, str(actor_id))
    
    if result.get('success'):
        return jsonify({
            'miner_id': miner_id,
            'credential': result.get('credential'),
            'mode': result.get('mode'),
            'audit_id': audit_event.id if audit_event else None
        })
    else:
        return jsonify({
            'miner_id': miner_id,
            'error': result.get('error'),
            'mode': result.get('mode')
        }), 403 if 'E2EE' in result.get('error', '') else 400


@credential_protection_bp.route('/api/v1/miners/<int:miner_id>/credential', methods=['POST'])
@require_admin
def update_miner_credential(miner_id):
    """更新矿机凭证（所有模式都支持反回滚保护）"""
    miner = HostingMiner.query.get(miner_id)
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    site = HostingSite.query.get(miner.site_id)
    data = request.get_json()
    
    counter = data.get('counter', miner.last_accepted_counter + 1)
    
    valid, msg = credential_service.validate_anti_rollback(miner, counter)
    if not valid:
        log_audit_event(
            site_id=miner.site_id,
            event_type='ANTI_ROLLBACK_REJECT',
            actor_id=session.get('user_id'),
            ref_type='miner',
            ref_id=miner_id,
            payload={'counter': counter, 'last_accepted': miner.last_accepted_counter}
        )
        return jsonify({'error': msg, 'code': 'ANTI_ROLLBACK_REJECT'}), 400
    
    if site.ip_mode == 3:
        e2ee_ciphertext = data.get('credential_e2ee_b64')
        device_id = data.get('device_id')
        
        if not e2ee_ciphertext:
            return jsonify({'error': 'Mode 3 requires credential_e2ee_b64 from client'}), 400
        
        if not e2ee_ciphertext.startswith('E2EE:') and len(e2ee_ciphertext) < 32:
            return jsonify({
                'error': 'E2EE ciphertext format invalid (expected base64 or E2EE: prefix)',
                'code': 'E2EE_FORMAT_INVALID'
            }), 400
        
        cred_value, cred_mode, fingerprint = credential_service.store_credential(
            site, None, device_id, e2ee_ciphertext, counter
        )
    else:
        credential_json = data.get('credential_plaintext_json')
        if not credential_json:
            credential_data = data.get('credential', {})
            credential_json = json.dumps(credential_data)
        
        cred_value, cred_mode, fingerprint = credential_service.store_credential(site, credential_json)
    
    miner.last_accepted_counter = counter
    
    miner.credential_value = cred_value
    miner.credential_mode = cred_mode
    miner.fingerprint = fingerprint
    
    log_audit_event(
        site_id=miner.site_id,
        event_type='UPDATE_CREDENTIAL',
        actor_id=session.get('user_id'),
        ref_type='miner',
        ref_id=miner_id,
        payload={'mode': cred_mode, 'fingerprint': fingerprint}
    )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'miner_id': miner_id,
        'credential_mode': cred_mode,
        'fingerprint': fingerprint
    })


@credential_protection_bp.route('/api/v1/sites/<int:site_id>/batch-migrate', methods=['POST'])
@require_admin
def batch_migrate_credentials(site_id):
    """批量迁移站点下所有矿机的凭证到当前模式"""
    site = HostingSite.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    data = request.get_json() or {}
    device_id = data.get('device_id')
    
    if site.ip_mode == 3 and not device_id:
        return jsonify({
            'error': 'Mode 3 requires device_id for E2EE encryption. Client must encrypt each miner individually.',
            'requires_client_encryption': True
        }), 400
    
    miners = HostingMiner.query.filter_by(site_id=site_id).all()
    results = {'success': [], 'failed': [], 'skipped': []}
    
    for miner in miners:
        if miner.credential_mode == site.ip_mode:
            results['skipped'].append({'miner_id': miner.id, 'reason': 'Same mode'})
            continue
        
        if miner.credential_mode == 3:
            results['failed'].append({
                'miner_id': miner.id, 
                'error': 'Cannot migrate from E2EE without Edge device'
            })
            continue
        
        try:
            success, msg = credential_service.migrate_credential(miner, site, site)
            if success:
                results['success'].append({'miner_id': miner.id, 'message': msg})
            else:
                results['failed'].append({'miner_id': miner.id, 'error': msg})
        except Exception as e:
            results['failed'].append({'miner_id': miner.id, 'error': str(e)})
    
    db.session.commit()
    
    log_audit_event(
        site_id=site_id,
        event_type='BATCH_MIGRATE',
        actor_id=session.get('user_id'),
        ref_type='site',
        ref_id=site_id,
        payload={
            'target_mode': site.ip_mode,
            'success_count': len(results['success']),
            'failed_count': len(results['failed']),
            'skipped_count': len(results['skipped'])
        }
    )
    
    return jsonify({
        'site_id': site_id,
        'target_mode': site.ip_mode,
        'results': results
    })


@credential_protection_bp.route('/api/v1/edge/decrypt', methods=['POST'])
def edge_decrypt_credential():
    """Edge 设备解密凭证（模拟）"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Device token required'}), 401
    
    device_token = auth_header[7:]
    
    from models_device_encryption import EdgeDevice
    import hashlib
    
    token_hash = hashlib.sha256(device_token.encode()).hexdigest()
    device = EdgeDevice.query.filter(
        (EdgeDevice.device_token == device_token) | 
        (EdgeDevice.token_hash == token_hash)
    ).first()
    
    if not device or device.status != 'ACTIVE':
        return jsonify({'error': 'Invalid or inactive device'}), 401
    
    data = request.get_json()
    miner_id = data.get('miner_id')
    
    miner = HostingMiner.query.get(miner_id)
    if not miner:
        return jsonify({'error': 'Miner not found'}), 404
    
    if device.site_id and device.site_id != miner.site_id:
        return jsonify({'error': 'Device not authorized for this site'}), 403
    
    if miner.credential_mode != 3:
        return jsonify({'error': 'Miner not using E2EE mode'}), 400
    
    counter = data.get('counter', 0)
    
    valid, msg = credential_service.validate_anti_rollback(miner, counter)
    if not valid:
        log_audit_event(
            site_id=miner.site_id,
            event_type='ANTI_ROLLBACK_REJECT',
            actor_id=f'device_{device.id}',
            ref_type='miner',
            ref_id=miner_id,
            payload={'counter': counter, 'last_accepted': miner.last_accepted_counter}
        )
        return jsonify({'error': msg, 'event': 'ANTI_ROLLBACK_REJECT'}), 400
    
    miner.last_accepted_counter = counter
    db.session.commit()
    
    log_audit_event(
        site_id=miner.site_id,
        event_type='EDGE_DECRYPT_OK',
        actor_id=f'device_{device.id}',
        ref_type='miner',
        ref_id=miner_id,
        payload={'counter': counter}
    )
    
    ciphertext = miner.credential_value[5:] if miner.credential_value.startswith('E2EE:') else None
    
    return jsonify({
        'miner_id': miner_id,
        'ciphertext_b64': ciphertext,
        'counter': counter,
        'device_id': device.id,
        'note': 'In production, Edge device decrypts locally with its secret key'
    })


@credential_protection_bp.route('/api/v1/audit/verify', methods=['GET'])
@require_auth
def verify_audit_chain():
    """验证审计链完整性"""
    site_id = request.args.get('site_id', type=int)
    
    events = AuditEvent.query.filter_by(site_id=site_id).order_by(AuditEvent.id.asc()).all()
    
    if not events:
        return jsonify({
            'verify_ok': True,
            'total_events': 0,
            'message': 'No events to verify'
        })
    
    verify_ok = True
    first_broken_id = None
    
    for i, event in enumerate(events):
        expected_prev = events[i-1].event_hash if i > 0 else '0' * 64
        
        if event.prev_hash != expected_prev:
            verify_ok = False
            first_broken_id = event.event_id
            break
        
        computed = event.compute_hash()
        if computed != event.event_hash:
            verify_ok = False
            first_broken_id = event.event_id
            break
    
    return jsonify({
        'verify_ok': verify_ok,
        'total_events': len(events),
        'first_broken_event_id': first_broken_id,
        'message': 'Audit chain verified OK' if verify_ok else 'Audit chain integrity compromised'
    })
