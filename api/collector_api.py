"""
采集器数据接收API
Collector Data Receiving API

接收边缘采集器上传的矿机遥测数据
"""

import gzip
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func
from models import db, HostingSite

logger = logging.getLogger(__name__)

collector_bp = Blueprint('collector', __name__, url_prefix='/api/collector')


class CollectorKey(db.Model):
    """采集器API密钥"""
    __tablename__ = 'collector_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key_hash = db.Column(db.String(64), unique=True, nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    site = db.relationship('HostingSite', backref=db.backref('collector_keys', lazy='dynamic'))


class MinerTelemetryLive(db.Model):
    """矿机实时遥测数据（最新状态）"""
    __tablename__ = 'miner_telemetry_live'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(50), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    ip_address = db.Column(db.String(45))
    
    online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime)
    
    hashrate_ghs = db.Column(db.Float, default=0)
    hashrate_5s_ghs = db.Column(db.Float, default=0)
    temperature_avg = db.Column(db.Float, default=0)
    temperature_max = db.Column(db.Float, default=0)
    temperature_chips = db.Column(db.JSON)
    fan_speeds = db.Column(db.JSON)
    frequency_avg = db.Column(db.Float, default=0)
    
    accepted_shares = db.Column(db.Integer, default=0)
    rejected_shares = db.Column(db.Integer, default=0)
    hardware_errors = db.Column(db.Integer, default=0)
    uptime_seconds = db.Column(db.Integer, default=0)
    
    power_consumption = db.Column(db.Float, default=0)
    efficiency = db.Column(db.Float, default=0)
    
    pool_url = db.Column(db.String(255))
    worker_name = db.Column(db.String(100))
    firmware_version = db.Column(db.String(50))
    error_message = db.Column(db.Text)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('site_id', 'miner_id', name='uq_site_miner'),
        db.Index('ix_telemetry_live_site_online', 'site_id', 'online'),
    )


class MinerTelemetryHistory(db.Model):
    """矿机历史遥测数据（时序）"""
    __tablename__ = 'miner_telemetry_history'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(50), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    
    hashrate_ghs = db.Column(db.Float, default=0)
    temperature_avg = db.Column(db.Float, default=0)
    temperature_max = db.Column(db.Float, default=0)
    fan_speed_avg = db.Column(db.Integer, default=0)
    power_consumption = db.Column(db.Float, default=0)
    accepted_shares = db.Column(db.Integer, default=0)
    rejected_shares = db.Column(db.Integer, default=0)
    online = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.Index('ix_telemetry_history_miner_time', 'miner_id', 'timestamp'),
        db.Index('ix_telemetry_history_site_time', 'site_id', 'timestamp'),
    )


class CollectorUploadLog(db.Model):
    """采集器上传日志"""
    __tablename__ = 'collector_upload_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    collector_key_id = db.Column(db.Integer, db.ForeignKey('collector_keys.id'))
    
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    miner_count = db.Column(db.Integer, default=0)
    online_count = db.Column(db.Integer, default=0)
    offline_count = db.Column(db.Integer, default=0)
    data_size_bytes = db.Column(db.Integer, default=0)
    processing_time_ms = db.Column(db.Integer, default=0)
    
    error_message = db.Column(db.Text)


def verify_collector_key(f):
    """验证采集器API密钥"""
    @wraps(f)
    def decorated(*args, **kwargs):
        import hashlib
        
        api_key = request.headers.get('X-Collector-Key')
        site_id_header = request.headers.get('X-Site-ID')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'Missing collector API key'}), 401
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        collector_key = CollectorKey.query.filter_by(
            key_hash=key_hash,
            is_active=True
        ).first()
        
        if not collector_key:
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        collector_key.last_used_at = datetime.utcnow()
        
        g.collector_key = collector_key
        g.site_id = collector_key.site_id
        
        return f(*args, **kwargs)
    
    return decorated


@collector_bp.route('/upload', methods=['POST'])
@verify_collector_key
def upload_telemetry():
    """接收矿机遥测数据上传
    
    请求头:
        X-Collector-Key: 采集器API密钥
        X-Site-ID: 站点ID
        Content-Encoding: gzip (可选)
    
    请求体:
        gzip压缩的JSON数组，包含矿机数据
    """
    import time
    start_time = time.time()
    
    try:
        if request.headers.get('Content-Encoding') == 'gzip':
            raw_data = gzip.decompress(request.data)
            data = json.loads(raw_data.decode('utf-8'))
        else:
            data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'success': False, 'error': 'Expected array of miner data'}), 400
        
        site_id = g.site_id
        miner_count = len(data)
        online_count = 0
        offline_count = 0
        
        for miner_data in data:
            try:
                miner_id = miner_data.get('miner_id')
                if not miner_id:
                    continue
                
                is_online = miner_data.get('online', False)
                if is_online:
                    online_count += 1
                else:
                    offline_count += 1
                
                live_record = MinerTelemetryLive.query.filter_by(
                    site_id=site_id,
                    miner_id=miner_id
                ).first()
                
                if not live_record:
                    live_record = MinerTelemetryLive(
                        site_id=site_id,
                        miner_id=miner_id
                    )
                    db.session.add(live_record)
                
                live_record.ip_address = miner_data.get('ip_address')
                live_record.online = is_online
                live_record.last_seen = datetime.utcnow() if is_online else live_record.last_seen
                live_record.hashrate_ghs = miner_data.get('hashrate_ghs', 0)
                live_record.hashrate_5s_ghs = miner_data.get('hashrate_5s_ghs', 0)
                live_record.temperature_avg = miner_data.get('temperature_avg', 0)
                live_record.temperature_max = miner_data.get('temperature_max', 0)
                live_record.temperature_chips = miner_data.get('temperature_chips', [])
                live_record.fan_speeds = miner_data.get('fan_speeds', [])
                live_record.frequency_avg = miner_data.get('frequency_avg', 0)
                live_record.accepted_shares = miner_data.get('accepted_shares', 0)
                live_record.rejected_shares = miner_data.get('rejected_shares', 0)
                live_record.hardware_errors = miner_data.get('hardware_errors', 0)
                live_record.uptime_seconds = miner_data.get('uptime_seconds', 0)
                live_record.power_consumption = miner_data.get('power_consumption', 0)
                live_record.efficiency = miner_data.get('efficiency', 0)
                live_record.pool_url = miner_data.get('pool_url', '')
                live_record.worker_name = miner_data.get('worker_name', '')
                live_record.firmware_version = miner_data.get('firmware_version', '')
                live_record.error_message = miner_data.get('error_message', '')
                
                if is_online:
                    history_record = MinerTelemetryHistory(
                        miner_id=miner_id,
                        site_id=site_id,
                        timestamp=datetime.utcnow(),
                        hashrate_ghs=miner_data.get('hashrate_ghs', 0),
                        temperature_avg=miner_data.get('temperature_avg', 0),
                        temperature_max=miner_data.get('temperature_max', 0),
                        fan_speed_avg=sum(miner_data.get('fan_speeds', [0])) // max(len(miner_data.get('fan_speeds', [1])), 1),
                        power_consumption=miner_data.get('power_consumption', 0),
                        accepted_shares=miner_data.get('accepted_shares', 0),
                        rejected_shares=miner_data.get('rejected_shares', 0),
                        online=True
                    )
                    db.session.add(history_record)
                    
            except Exception as e:
                logger.error(f"Error processing miner {miner_data.get('miner_id')}: {e}")
                continue
        
        processing_time = int((time.time() - start_time) * 1000)
        
        upload_log = CollectorUploadLog(
            site_id=site_id,
            collector_key_id=g.collector_key.id,
            miner_count=miner_count,
            online_count=online_count,
            offline_count=offline_count,
            data_size_bytes=len(request.data),
            processing_time_ms=processing_time
        )
        db.session.add(upload_log)
        
        db.session.commit()
        
        logger.info(f"Received telemetry: site={site_id}, miners={miner_count}, online={online_count}")
        
        return jsonify({
            'success': True,
            'data': {
                'processed': miner_count,
                'online': online_count,
                'offline': offline_count,
                'processing_time_ms': processing_time
            }
        })
        
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'Invalid JSON: {e}'}), 400
    except Exception as e:
        logger.error(f"Upload error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/status', methods=['GET'])
@verify_collector_key
def collector_status():
    """获取采集器状态"""
    site_id = g.site_id
    
    try:
        live_stats = db.session.query(
            func.count(MinerTelemetryLive.id).label('total'),
            func.sum(db.case((MinerTelemetryLive.online == True, 1), else_=0)).label('online')
        ).filter(MinerTelemetryLive.site_id == site_id).first()
        
        last_upload = CollectorUploadLog.query.filter_by(
            site_id=site_id
        ).order_by(CollectorUploadLog.upload_time.desc()).first()
        
        return jsonify({
            'success': True,
            'data': {
                'site_id': site_id,
                'total_miners': live_stats.total or 0,
                'online_miners': int(live_stats.online or 0),
                'last_upload': last_upload.upload_time.isoformat() if last_upload else None,
                'collector_name': g.collector_key.name
            }
        })
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/live/<int:site_id>', methods=['GET'])
def get_live_telemetry(site_id):
    """获取站点实时矿机数据（需要登录）"""
    from auth import login_required
    from flask import session
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        online_only = request.args.get('online_only', 'false').lower() == 'true'
        
        query = MinerTelemetryLive.query.filter_by(site_id=site_id)
        
        if online_only:
            query = query.filter_by(online=True)
        
        query = query.order_by(MinerTelemetryLive.miner_id)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        miners = []
        for m in pagination.items:
            miners.append({
                'miner_id': m.miner_id,
                'ip_address': m.ip_address,
                'online': m.online,
                'last_seen': m.last_seen.isoformat() if m.last_seen else None,
                'hashrate_ths': m.hashrate_ghs / 1000 if m.hashrate_ghs else 0,
                'hashrate_5s_ths': m.hashrate_5s_ghs / 1000 if m.hashrate_5s_ghs else 0,
                'temperature_avg': m.temperature_avg,
                'temperature_max': m.temperature_max,
                'fan_speeds': m.fan_speeds or [],
                'accepted_shares': m.accepted_shares,
                'rejected_shares': m.rejected_shares,
                'uptime_hours': m.uptime_seconds / 3600 if m.uptime_seconds else 0,
                'pool_url': m.pool_url,
                'worker_name': m.worker_name
            })
        
        return jsonify({
            'success': True,
            'data': {
                'miners': miners,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Get live telemetry error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/summary/<int:site_id>', methods=['GET'])
def get_site_summary(site_id):
    """获取站点遥测摘要"""
    try:
        stats = db.session.query(
            func.count(MinerTelemetryLive.id).label('total'),
            func.sum(db.case((MinerTelemetryLive.online == True, 1), else_=0)).label('online'),
            func.sum(MinerTelemetryLive.hashrate_ghs).label('total_hashrate'),
            func.avg(MinerTelemetryLive.temperature_avg).label('avg_temp'),
            func.max(MinerTelemetryLive.temperature_max).label('max_temp')
        ).filter(
            MinerTelemetryLive.site_id == site_id
        ).first()
        
        return jsonify({
            'success': True,
            'data': {
                'total_miners': stats.total or 0,
                'online_miners': int(stats.online or 0),
                'offline_miners': (stats.total or 0) - int(stats.online or 0),
                'total_hashrate_ths': (stats.total_hashrate or 0) / 1000,
                'avg_temperature': round(stats.avg_temp or 0, 1),
                'max_temperature': round(stats.max_temp or 0, 1),
                'online_rate': round(int(stats.online or 0) / max(stats.total or 1, 1) * 100, 1)
            }
        })
        
    except Exception as e:
        logger.error(f"Get summary error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_collector_key(site_id: int, name: str) -> str:
    """生成采集器API密钥"""
    import secrets
    import hashlib
    
    api_key = f"hsc_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    collector_key = CollectorKey(
        key_hash=key_hash,
        site_id=site_id,
        name=name
    )
    db.session.add(collector_key)
    db.session.commit()
    
    return api_key


def register_collector_routes(app):
    """注册采集器路由"""
    app.register_blueprint(collector_bp)
    logger.info("Collector API routes registered successfully")
