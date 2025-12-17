"""
IP Scan Job API
Network scanning for miner discovery

Endpoints:
    POST /api/scans - Create new scan job
    GET /api/scans - List scan jobs for tenant
    GET /api/scans/<id> - Get scan job details with progress
    GET /api/scans/<id>/miners - Get discovered miners
    POST /api/scans/<id>/import - Import discovered miners to hosting_miners
    DELETE /api/scans/<id> - Cancel/delete scan job
    
    POST /api/edge/scan - Edge device starts a scan
    POST /api/edge/scan/<id>/results - Edge device reports scan results
"""

import logging
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g

from db import db
from models import UserAccess, HostingSite, HostingMiner, MinerModel
from models_device_encryption import EdgeDevice, IPScanJob, DiscoveredMiner, DeviceAuditEvent
from api.device_api import require_user_auth, require_auth, log_audit_event

logger = logging.getLogger(__name__)

scan_bp = Blueprint('scan', __name__, url_prefix='/api/scans')
edge_scan_bp = Blueprint('edge_scan', __name__, url_prefix='/api/edge/scan')


def parse_ip_range_input(data: dict) -> tuple:
    """
    Parse IP range from request data
    
    Returns:
        Tuple of (start_ip, end_ip, total_ips, error_message)
    """
    try:
        from edge_collector.ip_scanner import IPRangeParser, IPRangeError
    except ImportError:
        return None, None, 0, "IP scanner module not available"
    
    parser = IPRangeParser()
    
    cidr = data.get('cidr', '').strip()
    ip_range = data.get('ip_range', '').strip()
    
    if cidr:
        try:
            start_ip, end_ip, total = parser.parse_cidr(cidr)
            return start_ip, end_ip, total, None
        except IPRangeError as e:
            return None, None, 0, str(e)
    
    if ip_range:
        try:
            start_ip, end_ip, total = parser.parse(ip_range)
            return start_ip, end_ip, total, None
        except IPRangeError as e:
            return None, None, 0, str(e)
    
    start_ip = data.get('ip_range_start', '').strip()
    end_ip = data.get('ip_range_end', '').strip()
    
    if start_ip and end_ip:
        if not parser.validate_ip(start_ip):
            return None, None, 0, f"Invalid start IP: {start_ip}"
        if not parser.validate_ip(end_ip):
            return None, None, 0, f"Invalid end IP: {end_ip}"
        
        start_int = parser.ip_to_int(start_ip)
        end_int = parser.ip_to_int(end_ip)
        
        if start_int > end_int:
            return None, None, 0, "Start IP must be less than or equal to end IP"
        
        total = end_int - start_int + 1
        return start_ip, end_ip, total, None
    
    return None, None, 0, "Please provide cidr, ip_range, or ip_range_start/ip_range_end"


@scan_bp.route('', methods=['POST'])
@require_user_auth
def create_scan():
    """
    Create a new IP scan job
    
    Request:
        {
            "cidr": "192.168.1.0/24",  // OR
            "ip_range": "192.168.1.1-192.168.1.254",  // OR
            "ip_range_start": "192.168.1.1",
            "ip_range_end": "192.168.1.254",
            "site_id": 123,  // optional
            "device_id": 456  // optional - edge device to perform scan
        }
    
    Response:
        {
            "success": true,
            "scan_job": {...}
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        start_ip, end_ip, total_ips, error = parse_ip_range_input(data)
        if error:
            return jsonify({'error': error}), 400
        
        if total_ips > 65536:
            return jsonify({'error': 'IP range too large. Maximum 65536 IPs per scan.'}), 400
        
        site_id = data.get('site_id')
        device_id = data.get('device_id')
        
        if site_id:
            site = HostingSite.query.filter_by(id=site_id, user_id=g.tenant_id).first()
            if not site:
                return jsonify({'error': 'Invalid site_id or not owned by you'}), 400
        
        if device_id:
            device = EdgeDevice.query.filter_by(id=device_id, tenant_id=g.tenant_id, status='ACTIVE').first()
            if not device:
                return jsonify({'error': 'Invalid device_id or device not active'}), 400
        
        scan_job = IPScanJob(
            tenant_id=g.tenant_id,
            site_id=site_id,
            device_id=device_id,
            ip_range_start=start_ip,
            ip_range_end=end_ip,
            total_ips=total_ips,
            status='PENDING',
            created_at=datetime.utcnow()
        )
        
        db.session.add(scan_job)
        db.session.commit()
        
        log_audit_event(
            'SCAN_JOB_CREATED',
            event_data={
                'scan_job_id': scan_job.id,
                'ip_range': f"{start_ip}-{end_ip}",
                'total_ips': total_ips,
                'site_id': site_id,
                'device_id': device_id
            }
        )
        
        logger.info(f"Created scan job {scan_job.id}: {start_ip}-{end_ip} ({total_ips} IPs)")
        
        return jsonify({
            'success': True,
            'scan_job': scan_job.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create scan job: {e}")
        return jsonify({'error': 'Failed to create scan job'}), 500


@scan_bp.route('', methods=['GET'])
@require_user_auth
def list_scans():
    """
    List scan jobs for current tenant
    
    Query params:
        status: Filter by status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
        site_id: Filter by site
        limit: Max results (default 50)
        offset: Pagination offset
    
    Returns:
        {
            "scan_jobs": [...],
            "total": 100
        }
    """
    query = IPScanJob.query.filter_by(tenant_id=g.tenant_id)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status.upper())
    
    site_id = request.args.get('site_id', type=int)
    if site_id:
        query = query.filter_by(site_id=site_id)
    
    total = query.count()
    
    limit = min(request.args.get('limit', 50, type=int), 100)
    offset = request.args.get('offset', 0, type=int)
    
    scan_jobs = query.order_by(IPScanJob.created_at.desc()).offset(offset).limit(limit).all()
    
    return jsonify({
        'scan_jobs': [j.to_dict() for j in scan_jobs],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@scan_bp.route('/<int:scan_id>', methods=['GET'])
@require_user_auth
def get_scan(scan_id):
    """Get scan job details with progress"""
    scan_job = IPScanJob.query.filter_by(id=scan_id, tenant_id=g.tenant_id).first()
    
    if not scan_job:
        return jsonify({'error': 'Scan job not found'}), 404
    
    result = scan_job.to_dict()
    result['device'] = None
    if scan_job.device:
        result['device'] = scan_job.device.to_dict()
    
    return jsonify({'scan_job': result})


@scan_bp.route('/<int:scan_id>/miners', methods=['GET'])
@require_user_auth
def get_scan_miners(scan_id):
    """
    Get discovered miners for a scan job
    
    Query params:
        imported: Filter by import status (true/false)
        limit: Max results (default 100)
        offset: Pagination offset
    """
    scan_job = IPScanJob.query.filter_by(id=scan_id, tenant_id=g.tenant_id).first()
    
    if not scan_job:
        return jsonify({'error': 'Scan job not found'}), 404
    
    query = DiscoveredMiner.query.filter_by(scan_job_id=scan_id)
    
    imported = request.args.get('imported')
    if imported is not None:
        is_imported = imported.lower() in ('true', '1', 'yes')
        query = query.filter_by(is_imported=is_imported)
    
    total = query.count()
    
    limit = min(request.args.get('limit', 100, type=int), 500)
    offset = request.args.get('offset', 0, type=int)
    
    miners = query.order_by(DiscoveredMiner.discovered_at.desc()).offset(offset).limit(limit).all()
    
    return jsonify({
        'miners': [m.to_dict() for m in miners],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@scan_bp.route('/<int:scan_id>/import', methods=['POST'])
@require_user_auth
def import_miners(scan_id):
    """
    Import discovered miners to hosting_miners table
    
    Request:
        {
            "miner_ids": [1, 2, 3],  // optional - import specific miners
            "all": true,  // or import all unimported miners
            "customer_id": 123,  // optional - assign to customer
            "miner_model_id": 456  // optional - override detected model
        }
    """
    scan_job = IPScanJob.query.filter_by(id=scan_id, tenant_id=g.tenant_id).first()
    
    if not scan_job:
        return jsonify({'error': 'Scan job not found'}), 404
    
    if scan_job.status not in ('COMPLETED', 'RUNNING'):
        return jsonify({'error': 'Scan must be completed or running to import miners'}), 400
    
    data = request.get_json() or {}
    
    miner_ids = data.get('miner_ids', [])
    import_all = data.get('all', False)
    customer_id = data.get('customer_id', g.tenant_id)
    miner_model_id = data.get('miner_model_id')
    
    if not miner_ids and not import_all:
        return jsonify({'error': 'Provide miner_ids or set all=true'}), 400
    
    query = DiscoveredMiner.query.filter_by(
        scan_job_id=scan_id,
        is_imported=False
    )
    
    if miner_ids:
        query = query.filter(DiscoveredMiner.id.in_(miner_ids))
    
    discovered_miners = query.all()
    
    if not discovered_miners:
        return jsonify({'error': 'No unimported miners found'}), 400
    
    default_model = None
    if miner_model_id:
        default_model = MinerModel.query.get(miner_model_id)
    
    if not default_model:
        default_model = MinerModel.query.filter_by(model_name='Generic ASIC').first()
        if not default_model:
            default_model = MinerModel.query.first()
    
    imported_count = 0
    errors = []
    
    for dm in discovered_miners:
        try:
            existing = HostingMiner.query.filter_by(
                site_id=scan_job.site_id,
                ip_address=dm.ip_address
            ).first() if scan_job.site_id else None
            
            if existing:
                dm.is_imported = True
                dm.imported_miner_id = existing.id
                continue
            
            model_id = miner_model_id
            if not model_id and dm.detected_model:
                matched_model = MinerModel.query.filter(
                    MinerModel.model_name.ilike(f"%{dm.detected_model.split()[-1]}%")
                ).first()
                if matched_model:
                    model_id = matched_model.id
            
            if not model_id and default_model:
                model_id = default_model.id
            
            if not model_id:
                errors.append(f"No model found for {dm.ip_address}")
                continue
            
            serial = f"SCAN-{scan_job.id}-{dm.ip_address.replace('.', '')}"
            
            hosting_miner = HostingMiner(
                site_id=scan_job.site_id or 1,
                customer_id=customer_id,
                miner_model_id=model_id,
                serial_number=serial,
                ip_address=dm.ip_address,
                mac_address=dm.mac_address,
                actual_hashrate=dm.detected_hashrate_ghs / 1000 if dm.detected_hashrate_ghs else 0,
                actual_power=0,
                status='active',
                approval_status='approved',
                notes=f"Discovered via scan job {scan_job.id}. Model: {dm.detected_model or 'Unknown'}",
                created_at=datetime.utcnow()
            )
            
            db.session.add(hosting_miner)
            db.session.flush()
            
            dm.is_imported = True
            dm.imported_miner_id = hosting_miner.id
            imported_count += 1
            
        except Exception as e:
            errors.append(f"Failed to import {dm.ip_address}: {str(e)}")
            logger.error(f"Import error for {dm.ip_address}: {e}")
    
    db.session.commit()
    
    log_audit_event(
        'MINERS_IMPORTED',
        event_data={
            'scan_job_id': scan_id,
            'imported_count': imported_count,
            'error_count': len(errors)
        }
    )
    
    return jsonify({
        'success': True,
        'imported_count': imported_count,
        'errors': errors
    })


@scan_bp.route('/<int:scan_id>', methods=['DELETE'])
@require_user_auth
def delete_scan(scan_id):
    """Delete or cancel a scan job"""
    scan_job = IPScanJob.query.filter_by(id=scan_id, tenant_id=g.tenant_id).first()
    
    if not scan_job:
        return jsonify({'error': 'Scan job not found'}), 404
    
    if scan_job.status == 'RUNNING':
        scan_job.status = 'CANCELLED'
        scan_job.completed_at = datetime.utcnow()
        db.session.commit()
        
        log_audit_event(
            'SCAN_JOB_CANCELLED',
            event_data={'scan_job_id': scan_id}
        )
        
        return jsonify({'success': True, 'message': 'Scan job cancelled'})
    
    db.session.delete(scan_job)
    db.session.commit()
    
    log_audit_event(
        'SCAN_JOB_DELETED',
        event_data={'scan_job_id': scan_id}
    )
    
    return jsonify({'success': True, 'message': 'Scan job deleted'})


@edge_scan_bp.route('', methods=['POST'])
@require_auth
def start_edge_scan():
    """
    Edge device requests to start a scan
    
    This endpoint is called by edge devices to get pending scan jobs
    or to start a specific scan.
    
    Request:
        {
            "scan_job_id": 123  // optional - start specific job
        }
    
    Response:
        {
            "scan_job": {...},
            "ip_list": ["192.168.1.1", "192.168.1.2", ...]
        }
    """
    data = request.get_json() or {}
    scan_job_id = data.get('scan_job_id')
    
    device_id = getattr(g, 'device_id', None)
    if not device_id:
        return jsonify({'error': 'Device authentication required'}), 403
    
    if scan_job_id:
        scan_job = IPScanJob.query.filter_by(
            id=scan_job_id,
            tenant_id=g.tenant_id,
            status='PENDING'
        ).first()
        
        if not scan_job:
            return jsonify({'error': 'Scan job not found or not pending'}), 404
    else:
        scan_job = IPScanJob.query.filter_by(
            tenant_id=g.tenant_id,
            device_id=device_id,
            status='PENDING'
        ).order_by(IPScanJob.created_at.asc()).first()
        
        if not scan_job:
            scan_job = IPScanJob.query.filter_by(
                tenant_id=g.tenant_id,
                device_id=None,
                status='PENDING'
            ).order_by(IPScanJob.created_at.asc()).first()
        
        if not scan_job:
            return jsonify({'message': 'No pending scan jobs'}), 200
    
    scan_job.status = 'RUNNING'
    scan_job.device_id = device_id
    scan_job.started_at = datetime.utcnow()
    db.session.commit()
    
    try:
        from edge_collector.ip_scanner import IPRangeParser
        parser = IPRangeParser()
        ip_list = list(parser.enumerate_ips(scan_job.ip_range_start, scan_job.ip_range_end))
    except Exception as e:
        logger.error(f"Failed to enumerate IPs: {e}")
        ip_list = []
    
    log_audit_event(
        'SCAN_JOB_STARTED',
        device_id=device_id,
        event_data={'scan_job_id': scan_job.id}
    )
    
    return jsonify({
        'scan_job': scan_job.to_dict(),
        'ip_list': ip_list
    })


@edge_scan_bp.route('/<int:scan_id>/progress', methods=['POST'])
@require_auth
def update_scan_progress(scan_id):
    """
    Edge device reports scan progress
    
    Request:
        {
            "scanned_ips": 150,
            "discovered_miners": 5
        }
    """
    device_id = getattr(g, 'device_id', None)
    if not device_id:
        return jsonify({'error': 'Device authentication required'}), 403
    
    scan_job = IPScanJob.query.filter_by(
        id=scan_id,
        tenant_id=g.tenant_id,
        device_id=device_id,
        status='RUNNING'
    ).first()
    
    if not scan_job:
        return jsonify({'error': 'Scan job not found or not running'}), 404
    
    data = request.get_json() or {}
    
    if 'scanned_ips' in data:
        scan_job.scanned_ips = data['scanned_ips']
    if 'discovered_miners' in data:
        scan_job.discovered_miners = data['discovered_miners']
    
    db.session.commit()
    
    return jsonify({'success': True, 'progress_percent': scan_job.progress_percent})


@edge_scan_bp.route('/<int:scan_id>/results', methods=['POST'])
@require_auth
def report_scan_results(scan_id):
    """
    Edge device reports scan results
    
    Request:
        {
            "status": "COMPLETED",  // or "FAILED"
            "error_message": "...",  // if failed
            "miners": [
                {
                    "ip_address": "192.168.1.10",
                    "api_port": 4028,
                    "detected_model": "Bitmain Antminer S19",
                    "detected_firmware": "20230415",
                    "detected_hashrate_ghs": 95000,
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "hostname": "miner-10",
                    "raw_response": {...}
                }
            ]
        }
    """
    device_id = getattr(g, 'device_id', None)
    if not device_id:
        return jsonify({'error': 'Device authentication required'}), 403
    
    scan_job = IPScanJob.query.filter_by(
        id=scan_id,
        tenant_id=g.tenant_id,
        device_id=device_id
    ).first()
    
    if not scan_job:
        return jsonify({'error': 'Scan job not found'}), 404
    
    if scan_job.status not in ('RUNNING', 'PENDING'):
        return jsonify({'error': 'Scan job is not in progress'}), 400
    
    data = request.get_json() or {}
    
    status = data.get('status', 'COMPLETED').upper()
    if status not in ('COMPLETED', 'FAILED'):
        status = 'COMPLETED'
    
    scan_job.status = status
    scan_job.completed_at = datetime.utcnow()
    scan_job.scanned_ips = scan_job.total_ips
    
    if status == 'FAILED':
        scan_job.error_message = data.get('error_message', 'Unknown error')
    
    miners = data.get('miners', [])
    discovered_count = 0
    
    for miner_data in miners:
        ip_address = miner_data.get('ip_address')
        if not ip_address:
            continue
        
        existing = DiscoveredMiner.query.filter_by(
            scan_job_id=scan_id,
            ip_address=ip_address
        ).first()
        
        if existing:
            existing.api_port = miner_data.get('api_port', 4028)
            existing.detected_model = miner_data.get('detected_model')
            existing.detected_firmware = miner_data.get('detected_firmware')
            existing.detected_hashrate_ghs = miner_data.get('detected_hashrate_ghs')
            existing.mac_address = miner_data.get('mac_address')
            existing.hostname = miner_data.get('hostname')
            existing.raw_response = miner_data.get('raw_response')
        else:
            discovered = DiscoveredMiner(
                scan_job_id=scan_id,
                tenant_id=g.tenant_id,
                ip_address=ip_address,
                api_port=miner_data.get('api_port', 4028),
                detected_model=miner_data.get('detected_model'),
                detected_firmware=miner_data.get('detected_firmware'),
                detected_hashrate_ghs=miner_data.get('detected_hashrate_ghs'),
                mac_address=miner_data.get('mac_address'),
                hostname=miner_data.get('hostname'),
                raw_response=miner_data.get('raw_response'),
                discovered_at=datetime.utcnow()
            )
            db.session.add(discovered)
            discovered_count += 1
    
    scan_job.discovered_miners = scan_job.discovered.count() + discovered_count
    
    db.session.commit()
    
    log_audit_event(
        'SCAN_JOB_COMPLETED',
        device_id=device_id,
        event_data={
            'scan_job_id': scan_id,
            'status': status,
            'discovered_miners': scan_job.discovered_miners
        }
    )
    
    logger.info(f"Scan job {scan_id} {status}: {scan_job.discovered_miners} miners discovered")
    
    return jsonify({
        'success': True,
        'scan_job': scan_job.to_dict()
    })
