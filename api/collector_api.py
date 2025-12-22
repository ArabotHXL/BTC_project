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
from models import db, HostingSite, HostingMiner, MinerModel

logger = logging.getLogger(__name__)

# 默认值用于自动创建矿机
DEFAULT_MINER_MODEL_ID = 1  # Antminer S19
DEFAULT_OWNER_ID = 7  # 系统默认 owner

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
    """矿机实时遥测数据（最新状态）
    
    Real-time miner telemetry with board-level health tracking
    """
    __tablename__ = 'miner_telemetry_live'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(50), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    ip_address = db.Column(db.String(45))
    
    online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime)
    
    hashrate_ghs = db.Column(db.Float, default=0)
    hashrate_5s_ghs = db.Column(db.Float, default=0)
    hashrate_expected_ghs = db.Column(db.Float, default=0)
    temperature_avg = db.Column(db.Float, default=0)
    temperature_min = db.Column(db.Float, default=0)
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
    pool_latency_ms = db.Column(db.Float, default=0)
    
    boards_data = db.Column(db.JSON)
    boards_total = db.Column(db.Integer, default=0)
    boards_healthy = db.Column(db.Integer, default=0)
    overall_health = db.Column(db.String(20), default='offline')
    
    model = db.Column(db.String(100))
    firmware_version = db.Column(db.String(50))
    error_message = db.Column(db.Text)
    
    latency_ms = db.Column(db.Float, default=0)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('site_id', 'miner_id', name='uq_site_miner'),
        db.Index('ix_telemetry_live_site_online', 'site_id', 'online'),
    )


class MinerTelemetryHistory(db.Model):
    """矿机历史遥测数据（时序）
    
    Historical miner telemetry for charts and analysis
    """
    __tablename__ = 'miner_telemetry_history'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(50), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    
    hashrate_ghs = db.Column(db.Float, default=0)
    temperature_avg = db.Column(db.Float, default=0)
    temperature_min = db.Column(db.Float, default=0)
    temperature_max = db.Column(db.Float, default=0)
    fan_speed_avg = db.Column(db.Integer, default=0)
    power_consumption = db.Column(db.Float, default=0)
    accepted_shares = db.Column(db.Integer, default=0)
    rejected_shares = db.Column(db.Integer, default=0)
    online = db.Column(db.Boolean, default=True)
    
    boards_healthy = db.Column(db.Integer, default=0)
    boards_total = db.Column(db.Integer, default=0)
    overall_health = db.Column(db.String(20), default='offline')
    
    net_profit_usd = db.Column(db.Float, default=0)
    revenue_usd = db.Column(db.Float, default=0)
    
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


class MinerCommand(db.Model):
    """矿机控制命令队列
    
    用于云端向边缘采集器下发控制命令
    Miner Control Command Queue for cloud-to-edge control
    """
    __tablename__ = 'miner_commands'
    
    id = db.Column(db.Integer, primary_key=True)
    miner_id = db.Column(db.String(50), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    ip_address = db.Column(db.String(45))
    
    command_type = db.Column(db.String(30), nullable=False, index=True)
    parameters = db.Column(db.JSON, default={})
    
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    priority = db.Column(db.Integer, default=5)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime)
    executed_at = db.Column(db.DateTime)
    
    result_code = db.Column(db.Integer)
    result_message = db.Column(db.Text)
    
    operator_id = db.Column(db.Integer, db.ForeignKey('user_access.id'))
    
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    __table_args__ = (
        db.Index('ix_miner_commands_site_status', 'site_id', 'status'),
        db.Index('ix_miner_commands_miner_status', 'miner_id', 'status'),
        db.Index('ix_miner_commands_expires', 'expires_at'),
    )
    
    COMMAND_TYPES = {
        'enable': '启动挖矿 / Enable Mining',
        'disable': '停止挖矿 / Disable Mining',
        'restart': '重启矿机 / Restart Miner',
        'reboot': '重启系统 / Reboot System',
        'set_pool': '切换矿池 / Switch Pool',
        'set_fan': '设置风扇 / Set Fan Speed',
        'set_frequency': '调整频率 / Adjust Frequency'
    }
    
    STATUS_TYPES = {
        'pending': '等待发送',
        'sent': '已发送',
        'executing': '执行中',
        'completed': '已完成',
        'failed': '执行失败',
        'expired': '已过期',
        'cancelled': '已取消'
    }
    
    def to_dict(self):
        return {
            'id': self.id,
            'miner_id': self.miner_id,
            'site_id': self.site_id,
            'ip_address': self.ip_address,
            'command_type': self.command_type,
            'command_desc': self.COMMAND_TYPES.get(self.command_type, self.command_type),
            'parameters': self.parameters,
            'status': self.status,
            'status_desc': self.STATUS_TYPES.get(self.status, self.status),
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'result_code': self.result_code,
            'result_message': self.result_message,
            'operator_id': self.operator_id,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    def to_command_payload(self):
        """生成发送给采集器的命令载荷"""
        return {
            'command_id': self.id,
            'miner_id': self.miner_id,
            'ip_address': self.ip_address,
            'command': self.command_type,
            'params': self.parameters or {},
            'priority': self.priority,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


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


def find_or_create_hosting_miner(site_id: int, miner_data: dict) -> HostingMiner:
    """
    查找或创建 HostingMiner 记录
    
    匹配优先级（同站点内）:
    1. serial_number = miner_id（最可靠的唯一标识）
    2. IP地址匹配（miner_id 可能变化时使用）
    3. 自动创建新矿机（使用 miner_id 作为 serial_number）
    
    Args:
        site_id: 站点ID
        miner_data: 采集器上传的矿机数据
    
    Returns:
        HostingMiner: 矿机对象
    """
    miner_id = miner_data.get('miner_id', '')
    ip_address = miner_data.get('ip_address', '')
    
    # 1. 先尝试用 miner_id = serial_number 匹配（最可靠）
    if miner_id:
        miner = HostingMiner.query.filter_by(
            site_id=site_id,
            serial_number=miner_id
        ).first()
        if miner:
            # 更新 IP 如果有变化
            if ip_address and miner.ip_address != ip_address:
                miner.ip_address = ip_address
            return miner
    
    # 2. 再尝试用 IP 地址匹配（适用于 miner_id 变化的情况）
    if ip_address:
        miner = HostingMiner.query.filter_by(
            site_id=site_id,
            ip_address=ip_address
        ).first()
        if miner:
            # 如果通过 IP 找到，且有新的 miner_id，更新 serial_number
            if miner_id and miner.serial_number != miner_id:
                # 检查新 miner_id 是否与其他记录冲突
                conflict = HostingMiner.query.filter_by(serial_number=miner_id).first()
                if not conflict:
                    miner.serial_number = miner_id
            return miner
    
    # 3. 都没找到，自动创建新矿机
    # 使用 miner_id 作为 serial_number（保持一致性）
    serial_number = miner_id if miner_id else f"AUTO_{ip_address.replace('.', '_')}_{site_id}"
    
    # 确保 serial_number 全局唯一（跨站点）
    existing = HostingMiner.query.filter_by(serial_number=serial_number).first()
    if existing:
        # 如果已存在相同 serial，添加站点ID和时间戳后缀
        serial_number = f"{serial_number}_{site_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # 获取默认 miner_model
    default_model = MinerModel.query.filter_by(id=DEFAULT_MINER_MODEL_ID).first()
    if not default_model:
        default_model = MinerModel.query.first()
    
    model_id = default_model.id if default_model else 1
    
    # 从上传数据推断算力和功耗
    hashrate_ths = miner_data.get('hashrate_ghs', 0) / 1000  # GH/s -> TH/s
    power_w = miner_data.get('power_consumption', 3250)  # 默认 3250W
    
    if hashrate_ths == 0:
        # 如果没有算力数据，使用型号参考值
        hashrate_ths = default_model.reference_hashrate if default_model else 110
    
    new_miner = HostingMiner(
        site_id=site_id,
        customer_id=DEFAULT_OWNER_ID,
        miner_model_id=model_id,
        serial_number=serial_number,
        actual_hashrate=hashrate_ths,
        actual_power=power_w,
        ip_address=ip_address,
        status='online',
        health_score=100,
        approval_status='approved',
        install_date=datetime.utcnow(),
        cgminer_online=True,
        last_seen=datetime.utcnow()
    )
    
    db.session.add(new_miner)
    logger.info(f"Auto-created miner: {serial_number} at {ip_address} for site {site_id}")
    
    return new_miner


def sync_hosting_miner_telemetry(miner: HostingMiner, miner_data: dict, now: datetime):
    """
    同步采集器数据到 hosting_miners 表
    
    Args:
        miner: HostingMiner 对象
        miner_data: 采集器上传的矿机数据
        now: 当前时间
    """
    import json as json_lib
    
    is_online = miner_data.get('online', False)
    
    # 更新基础状态
    miner.cgminer_online = is_online
    if is_online:
        miner.last_seen = now
        miner.status = 'online'
    else:
        miner.status = 'offline'
    
    # 更新实时数据
    hashrate_ghs = miner_data.get('hashrate_ghs', 0)
    miner.actual_hashrate = hashrate_ghs / 1000  # GH/s -> TH/s
    miner.hashrate_5s = miner_data.get('hashrate_5s_ghs', 0) / 1000
    
    miner.temperature_avg = miner_data.get('temperature_avg', 0)
    miner.temperature_max = miner_data.get('temperature_max', 0)
    
    # 风扇转速
    fan_speeds = miner_data.get('fan_speeds', [])
    if fan_speeds:
        miner.fan_speeds = json_lib.dumps(fan_speeds)
        miner.fan_avg = sum(fan_speeds) // len(fan_speeds) if fan_speeds else 0
    
    # 矿池信息
    miner.pool_url = miner_data.get('pool_url', '')
    miner.pool_worker = miner_data.get('worker_name', '')
    
    # 份额统计
    miner.accepted_shares = miner_data.get('accepted_shares', 0)
    miner.rejected_shares = miner_data.get('rejected_shares', 0)
    miner.hardware_errors = miner_data.get('hardware_errors', 0)
    miner.uptime_seconds = miner_data.get('uptime_seconds', 0)
    
    # 功耗
    power = miner_data.get('power_consumption', 0)
    if power > 0:
        miner.actual_power = power
    
    # 计算拒绝率
    total_shares = miner.accepted_shares + miner.rejected_shares
    if total_shares > 0:
        miner.reject_rate = (miner.rejected_shares / total_shares) * 100
    
    # 更新 IP (如果提供)
    ip = miner_data.get('ip_address')
    if ip:
        miner.ip_address = ip


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
        now = datetime.utcnow()
        
        miner_ids = [m.get('miner_id') for m in data if m.get('miner_id')]
        
        existing_records = MinerTelemetryLive.query.filter(
            MinerTelemetryLive.site_id == site_id,
            MinerTelemetryLive.miner_id.in_(miner_ids)
        ).all() if miner_ids else []
        existing_map = {r.miner_id: r for r in existing_records}
        
        updates = []
        inserts = []
        history_inserts = []
        
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
                
                existing_record = existing_map.get(miner_id)
                
                record_data = {
                    'site_id': site_id,
                    'miner_id': miner_id,
                    'ip_address': miner_data.get('ip_address'),
                    'online': is_online,
                    'last_seen': now if is_online else (existing_record.last_seen if existing_record else None),
                    'hashrate_ghs': miner_data.get('hashrate_ghs', 0),
                    'hashrate_5s_ghs': miner_data.get('hashrate_5s_ghs', 0),
                    'hashrate_expected_ghs': miner_data.get('hashrate_expected_ghs', 0),
                    'temperature_avg': miner_data.get('temperature_avg', 0),
                    'temperature_min': miner_data.get('temperature_min', miner_data.get('temperature_avg', 0)),
                    'temperature_max': miner_data.get('temperature_max', 0),
                    'temperature_chips': miner_data.get('temperature_chips', []),
                    'fan_speeds': miner_data.get('fan_speeds', []),
                    'frequency_avg': miner_data.get('frequency_avg', 0),
                    'accepted_shares': miner_data.get('accepted_shares', 0),
                    'rejected_shares': miner_data.get('rejected_shares', 0),
                    'hardware_errors': miner_data.get('hardware_errors', 0),
                    'uptime_seconds': miner_data.get('uptime_seconds', 0),
                    'power_consumption': miner_data.get('power_consumption', 0),
                    'efficiency': miner_data.get('efficiency', 0),
                    'pool_url': miner_data.get('pool_url', ''),
                    'worker_name': miner_data.get('worker_name', ''),
                    'pool_latency_ms': miner_data.get('pool_latency_ms', 0),
                    'boards_data': miner_data.get('boards', []),
                    'boards_total': miner_data.get('boards_total', len(miner_data.get('boards', []))),
                    'boards_healthy': miner_data.get('boards_healthy', 0),
                    'overall_health': miner_data.get('overall_health', 'offline' if not is_online else 'healthy'),
                    'model': miner_data.get('model', ''),
                    'firmware_version': miner_data.get('firmware_version', ''),
                    'error_message': miner_data.get('error_message', ''),
                    'latency_ms': miner_data.get('latency_ms', 0),
                    'updated_at': now,
                }
                
                if existing_record:
                    record_data['id'] = existing_record.id
                    updates.append(record_data)
                else:
                    inserts.append(record_data)
                
                if is_online:
                    fan_speeds = miner_data.get('fan_speeds', [])
                    fan_speed_avg = sum(fan_speeds) // max(len(fan_speeds), 1) if fan_speeds else 0
                    
                    history_inserts.append({
                        'miner_id': miner_id,
                        'site_id': site_id,
                        'timestamp': now,
                        'hashrate_ghs': miner_data.get('hashrate_ghs', 0),
                        'temperature_avg': miner_data.get('temperature_avg', 0),
                        'temperature_min': miner_data.get('temperature_min', miner_data.get('temperature_avg', 0)),
                        'temperature_max': miner_data.get('temperature_max', 0),
                        'fan_speed_avg': fan_speed_avg,
                        'power_consumption': miner_data.get('power_consumption', 0),
                        'accepted_shares': miner_data.get('accepted_shares', 0),
                        'rejected_shares': miner_data.get('rejected_shares', 0),
                        'online': True,
                        'boards_healthy': miner_data.get('boards_healthy', 0),
                        'boards_total': miner_data.get('boards_total', 0),
                        'overall_health': miner_data.get('overall_health', 'healthy'),
                        'net_profit_usd': 0.0,
                        'revenue_usd': 0.0,
                    })
                
                # 同步数据到 hosting_miners 表（自动创建不存在的矿机）
                try:
                    hosting_miner = find_or_create_hosting_miner(site_id, miner_data)
                    sync_hosting_miner_telemetry(hosting_miner, miner_data, now)
                except Exception as sync_err:
                    logger.warning(f"Failed to sync hosting miner {miner_id}: {sync_err}")
                    
            except Exception as e:
                logger.error(f"Error processing miner {miner_data.get('miner_id')}: {e}")
                continue
        
        if updates:
            db.session.bulk_update_mappings(MinerTelemetryLive, updates)
        if inserts:
            db.session.bulk_insert_mappings(MinerTelemetryLive, inserts)
        if history_inserts:
            db.session.bulk_insert_mappings(MinerTelemetryHistory, history_inserts)
        
        raw_inserted = 0
        try:
            from services.telemetry_storage import TelemetryStorageManager
            raw_records = [{'site_id': site_id, 'ts': now, **m} for m in data if m.get('online', False)]
            raw_inserted = TelemetryStorageManager.batch_insert_raw(raw_records)
        except Exception as raw_err:
            logger.warning(f"Raw telemetry insert failed (non-critical): {raw_err}")
        
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
        
        logger.info(f"Received telemetry: site={site_id}, miners={miner_count}, inserted={len(inserts)}, updated={len(updates)}, online={online_count}")
        
        return jsonify({
            'success': True,
            'inserted': len(inserts),
            'updated': len(updates),
            'data': {
                'processed': miner_count,
                'inserted': len(inserts),
                'updated': len(updates),
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


# ============ Monitor API Endpoints ============

@collector_bp.route('/monitor/sites/<int:site_id>/miners/latest', methods=['GET'])
def get_miners_latest(site_id):
    """
    获取站点最新矿机列表
    
    GET /api/collector/monitor/sites/<site_id>/miners/latest
    
    Query params:
        - page: 页码 (默认 1)
        - per_page: 每页数量 (默认 100)
        - online_only: 是否只返回在线矿机 (默认 false)
    
    Returns:
        - miners: 矿机列表 (按 updated_at 降序)
        - pagination: 分页信息
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        online_only = request.args.get('online_only', 'false').lower() == 'true'
        
        query = MinerTelemetryLive.query.filter_by(site_id=site_id)
        
        if online_only:
            query = query.filter_by(online=True)
        
        query = query.order_by(MinerTelemetryLive.updated_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        miners = []
        for m in pagination.items:
            miners.append({
                'miner_id': m.miner_id,
                'ip_address': m.ip_address,
                'online': m.online,
                'updated_at': m.updated_at.isoformat() if m.updated_at else None,
                'last_seen': m.last_seen.isoformat() if m.last_seen else None,
                'hashrate_ghs': m.hashrate_ghs or 0,
                'hashrate_ths': (m.hashrate_ghs or 0) / 1000,
                'temperature_avg': m.temperature_avg or 0,
                'temperature_max': m.temperature_max or 0,
                'fan_speeds': m.fan_speeds or [],
                'accepted_shares': m.accepted_shares or 0,
                'rejected_shares': m.rejected_shares or 0,
                'hardware_errors': m.hardware_errors or 0,
                'uptime_seconds': m.uptime_seconds or 0,
                'pool_url': m.pool_url or '',
                'worker_name': m.worker_name or '',
                'model': m.model or '',
                'overall_health': m.overall_health or 'unknown'
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
        logger.error(f"Get miners latest error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/monitor/sites/<int:site_id>/miners/<miner_id>/history', methods=['GET'])
def get_miner_history(site_id, miner_id):
    """
    获取矿机历史遥测数据 - 4层智能路由
    
    GET /api/collector/monitor/sites/<site_id>/miners/<miner_id>/history
    
    Query params:
        - metric: 指标类型 (hashrate_ghs, temperature_avg, temperature_max, fan_speed_avg, power_consumption)
        - hours: 查询小时数 (默认 24)
        - layer: 强制指定层 (raw, history, daily) - 可选
    
    Intelligent Layer Routing:
        - hours ≤ 24: telemetry_raw_24h (high resolution ~30s)
        - hours ≤ 1440 (60 days): telemetry_history_5min (5-min rollups)
        - hours > 1440: telemetry_daily (daily aggregates)
    
    Returns:
        - points: 时间序列数据点 [{timestamp, value}]
        - metric: 请求的指标名
        - layer: 使用的存储层
    """
    try:
        from services.telemetry_storage import TelemetryRaw24h, TelemetryHistory5min, TelemetryDaily
        
        metric = request.args.get('metric', 'hashrate_ghs')
        hours = request.args.get('hours', 24, type=int)
        force_layer = request.args.get('layer')
        
        valid_metrics = ['hashrate_ghs', 'temperature_avg', 'temperature_max', 'fan_speed_avg', 'power_consumption']
        if metric not in valid_metrics:
            return jsonify({
                'success': False, 
                'error': f'Invalid metric. Valid options: {", ".join(valid_metrics)}'
            }), 400
        
        since = datetime.utcnow() - timedelta(hours=hours)
        points = []
        layer_used = 'unknown'
        
        if force_layer == 'raw' or (not force_layer and hours <= 24):
            layer_used = 'raw_24h'
            history = TelemetryRaw24h.query.filter(
                TelemetryRaw24h.site_id == site_id,
                TelemetryRaw24h.miner_id == miner_id,
                TelemetryRaw24h.timestamp >= since
            ).order_by(TelemetryRaw24h.timestamp.asc()).all()
            
            for h in history:
                value = getattr(h, metric, None)
                if value is not None:
                    points.append({
                        'timestamp': h.timestamp.isoformat(),
                        'value': value
                    })
                    
        elif force_layer == 'history' or (not force_layer and hours <= 1440):
            layer_used = 'history_5min'
            history = TelemetryHistory5min.query.filter(
                TelemetryHistory5min.site_id == site_id,
                TelemetryHistory5min.miner_id == miner_id,
                TelemetryHistory5min.bucket_time >= since
            ).order_by(TelemetryHistory5min.bucket_time.asc()).all()
            
            metric_map = {
                'hashrate_ghs': 'hashrate_avg',
                'temperature_avg': 'temp_avg',
                'temperature_max': 'temp_max',
                'fan_speed_avg': 'fan_avg',
                'power_consumption': 'power_avg'
            }
            attr_name = metric_map.get(metric, metric)
            
            for h in history:
                value = getattr(h, attr_name, None)
                if value is not None:
                    points.append({
                        'timestamp': h.bucket_time.isoformat(),
                        'value': value
                    })
                    
        else:
            layer_used = 'daily'
            history = TelemetryDaily.query.filter(
                TelemetryDaily.site_id == site_id,
                TelemetryDaily.miner_id == miner_id,
                TelemetryDaily.date >= since.date()
            ).order_by(TelemetryDaily.date.asc()).all()
            
            metric_map = {
                'hashrate_ghs': 'hashrate_avg',
                'temperature_avg': 'temp_avg',
                'temperature_max': 'temp_max',
                'fan_speed_avg': 'fan_avg',
                'power_consumption': 'power_total'
            }
            attr_name = metric_map.get(metric, metric)
            
            for h in history:
                value = getattr(h, attr_name, None)
                if value is not None:
                    points.append({
                        'timestamp': h.date.isoformat(),
                        'value': value
                    })
        
        if not points and layer_used == 'raw_24h':
            fallback_history = MinerTelemetryHistory.query.filter(
                MinerTelemetryHistory.site_id == site_id,
                MinerTelemetryHistory.miner_id == miner_id,
                MinerTelemetryHistory.timestamp >= since
            ).order_by(MinerTelemetryHistory.timestamp.asc()).all()
            
            for h in fallback_history:
                value = getattr(h, metric, None)
                if value is not None:
                    points.append({
                        'timestamp': h.timestamp.isoformat(),
                        'value': value
                    })
            if points:
                layer_used = 'legacy_history'
        
        return jsonify({
            'success': True,
            'data': {
                'miner_id': miner_id,
                'site_id': site_id,
                'metric': metric,
                'hours': hours,
                'layer': layer_used,
                'points': points,
                'count': len(points)
            }
        })
        
    except Exception as e:
        logger.error(f"Get miner history error: {e}")
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


@collector_bp.route('/stats', methods=['GET'])
def get_collector_stats():
    """获取采集器总体统计 - 优化版 (4 queries instead of 1+3N)"""
    from auth import login_required as auth_login_required
    
    try:
        miner_stats = db.session.query(
            MinerTelemetryLive.site_id,
            func.count(MinerTelemetryLive.id).label('total'),
            func.sum(db.case((MinerTelemetryLive.online == True, 1), else_=0)).label('online'),
            func.sum(MinerTelemetryLive.hashrate_ghs).label('hashrate'),
            func.avg(MinerTelemetryLive.temperature_avg).label('temp')
        ).group_by(MinerTelemetryLive.site_id).all()
        
        miner_stats_map = {s.site_id: s for s in miner_stats}
        
        latest_upload_subq = db.session.query(
            CollectorUploadLog.site_id,
            func.max(CollectorUploadLog.upload_time).label('last_upload')
        ).group_by(CollectorUploadLog.site_id).subquery()
        
        active_keys_stats = db.session.query(
            CollectorKey.site_id,
            func.count(CollectorKey.id).label('key_count')
        ).filter(CollectorKey.is_active == True).group_by(CollectorKey.site_id).all()
        
        active_keys_map = {s.site_id: s.key_count for s in active_keys_stats}
        
        sites = db.session.query(
            HostingSite.id,
            HostingSite.name,
            latest_upload_subq.c.last_upload
        ).outerjoin(
            latest_upload_subq,
            HostingSite.id == latest_upload_subq.c.site_id
        ).all()
        
        site_stats = {}
        total_miners = 0
        total_online = 0
        active_collectors = 0
        now = datetime.utcnow()
        
        for site in sites:
            stats = miner_stats_map.get(site.id)
            active_keys = active_keys_map.get(site.id, 0)
            
            miners_total = stats.total if stats else 0
            miners_online = int(stats.online or 0) if stats else 0
            hashrate = (stats.hashrate or 0) / 1000 if stats else 0
            temp = round(stats.temp or 0, 1) if stats else 0
            
            if active_keys > 0 and site.last_upload and (now - site.last_upload).total_seconds() < 300:
                active_collectors += 1
            
            site_stats[site.id] = {
                'total_miners': miners_total,
                'online_miners': miners_online,
                'total_hashrate_ths': hashrate,
                'avg_temperature': temp,
                'last_upload': site.last_upload.strftime('%Y-%m-%d %H:%M') if site.last_upload else None
            }
            
            total_miners += miners_total
            total_online += miners_online
        
        try:
            from services.alert_engine import MinerAlert
            active_alerts = MinerAlert.query.filter(MinerAlert.resolved_at == None).count()
        except:
            active_alerts = 0
        
        return jsonify({
            'success': True,
            'total_sites': len(sites),
            'active_collectors': active_collectors,
            'total_miners': total_miners,
            'total_online': total_online,
            'active_alerts': active_alerts,
            'sites': site_stats
        })
        
    except Exception as e:
        logger.error(f"Get collector stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/alerts', methods=['GET'])
def get_collector_alerts():
    """获取告警列表"""
    try:
        from services.alert_engine import MinerAlert
        
        limit = request.args.get('limit', 20, type=int)
        site_id = request.args.get('site_id', type=int)
        
        query = MinerAlert.query.filter(MinerAlert.resolved_at == None)
        
        if site_id:
            query = query.filter(MinerAlert.site_id == site_id)
        
        alerts = query.order_by(MinerAlert.triggered_at.desc()).limit(limit).all()
        
        result = []
        for alert in alerts:
            result.append({
                'id': alert.id,
                'site_id': alert.site_id,
                'miner_id': alert.miner_id,
                'alert_type': alert.alert_type,
                'level': alert.level,
                'message': alert.message,
                'message_zh': alert.message_zh,
                'value': alert.value,
                'threshold': alert.threshold,
                'triggered_at': alert.triggered_at.strftime('%Y-%m-%d %H:%M') if alert.triggered_at else None,
                'acknowledged': alert.acknowledged
            })
        
        return jsonify({
            'success': True,
            'alerts': result
        })
        
    except ImportError:
        return jsonify({'success': True, 'alerts': []})
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/keys', methods=['GET'])
def list_collector_keys():
    """列出站点的采集器密钥"""
    try:
        site_id = request.args.get('site_id', type=int)
        
        if not site_id:
            return jsonify({'success': False, 'error': 'site_id required'}), 400
        
        keys = CollectorKey.query.filter_by(site_id=site_id).order_by(CollectorKey.created_at.desc()).all()
        
        result = []
        for key in keys:
            result.append({
                'id': key.id,
                'key_id': key.key_hash[:16] + '...',
                'name': key.name,
                'is_active': key.is_active,
                'created_at': key.created_at.strftime('%Y-%m-%d %H:%M') if key.created_at else None,
                'last_used_at': key.last_used_at.strftime('%Y-%m-%d %H:%M') if key.last_used_at else None
            })
        
        return jsonify({
            'success': True,
            'keys': result
        })
        
    except Exception as e:
        logger.error(f"List keys error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/keys', methods=['POST'])
def create_collector_key():
    """创建新的采集器密钥"""
    import secrets
    import hashlib
    
    try:
        data = request.get_json()
        site_id = data.get('site_id')
        name = data.get('name', f'Key-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}')
        
        if not site_id:
            return jsonify({'success': False, 'error': 'site_id required'}), 400
        
        site = HostingSite.query.get(site_id)
        if not site:
            return jsonify({'success': False, 'error': 'Site not found'}), 404
        
        api_key = f"hsc_{secrets.token_urlsafe(32)}"
        secret = secrets.token_urlsafe(16)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        collector_key = CollectorKey(
            key_hash=key_hash,
            site_id=site_id,
            name=name
        )
        db.session.add(collector_key)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'key_id': api_key,
            'secret': secret,
            'message': 'API key created successfully'
        })
        
    except Exception as e:
        logger.error(f"Create key error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/keys/<key_id>', methods=['DELETE'])
def revoke_collector_key(key_id):
    """撤销采集器密钥"""
    try:
        key = CollectorKey.query.filter(
            CollectorKey.key_hash.like(f'{key_id}%')
        ).first()
        
        if not key:
            return jsonify({'success': False, 'error': 'Key not found'}), 404
        
        key.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'API key revoked successfully'
        })
        
    except Exception as e:
        logger.error(f"Revoke key error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/commands', methods=['POST'])
def create_command():
    """创建矿机控制命令
    
    请求体:
    {
        "miner_id": "SN123456",
        "site_id": 1,
        "ip_address": "192.168.1.100",  // 可选
        "command_type": "enable|disable|restart|reboot|set_pool|set_fan",
        "parameters": {},  // 命令参数
        "priority": 5,  // 1-10, 10最高
        "ttl_minutes": 30  // 命令有效期（分钟）
    }
    """
    try:
        from flask import session
        
        data = request.get_json()
        
        miner_id = data.get('miner_id')
        site_id = data.get('site_id')
        command_type = data.get('command_type')
        
        if not all([miner_id, site_id, command_type]):
            return jsonify({'success': False, 'error': 'miner_id, site_id, command_type required'}), 400
        
        if command_type not in MinerCommand.COMMAND_TYPES:
            return jsonify({
                'success': False, 
                'error': f'Invalid command_type. Valid types: {list(MinerCommand.COMMAND_TYPES.keys())}'
            }), 400
        
        ttl_minutes = data.get('ttl_minutes', 30)
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        
        command = MinerCommand(
            miner_id=miner_id,
            site_id=site_id,
            ip_address=data.get('ip_address'),
            command_type=command_type,
            parameters=data.get('parameters', {}),
            priority=data.get('priority', 5),
            expires_at=expires_at,
            operator_id=session.get('user_id')
        )
        
        db.session.add(command)
        db.session.commit()
        
        logger.info(f"Command created: {command.id} - {command_type} for miner {miner_id}")
        
        return jsonify({
            'success': True,
            'command': command.to_dict(),
            'message': 'Command created successfully'
        })
        
    except Exception as e:
        logger.error(f"Create command error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/commands/batch', methods=['POST'])
def create_batch_commands():
    """批量创建矿机控制命令
    
    请求体:
    {
        "miner_ids": ["SN1", "SN2", ...],
        "site_id": 1,
        "command_type": "disable",
        "parameters": {},
        "priority": 5,
        "ttl_minutes": 30
    }
    """
    try:
        from flask import session
        
        data = request.get_json()
        
        miner_ids = data.get('miner_ids', [])
        site_id = data.get('site_id')
        command_type = data.get('command_type')
        
        if not all([miner_ids, site_id, command_type]):
            return jsonify({'success': False, 'error': 'miner_ids, site_id, command_type required'}), 400
        
        if command_type not in MinerCommand.COMMAND_TYPES:
            return jsonify({
                'success': False, 
                'error': f'Invalid command_type. Valid types: {list(MinerCommand.COMMAND_TYPES.keys())}'
            }), 400
        
        ttl_minutes = data.get('ttl_minutes', 30)
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        operator_id = session.get('user_id')
        
        commands = []
        for miner_id in miner_ids:
            command = MinerCommand(
                miner_id=miner_id,
                site_id=site_id,
                command_type=command_type,
                parameters=data.get('parameters', {}),
                priority=data.get('priority', 5),
                expires_at=expires_at,
                operator_id=operator_id
            )
            db.session.add(command)
            commands.append(command)
        
        db.session.commit()
        
        logger.info(f"Batch commands created: {len(commands)} {command_type} commands for site {site_id}")
        
        return jsonify({
            'success': True,
            'count': len(commands),
            'command_ids': [c.id for c in commands],
            'message': f'{len(commands)} commands created successfully'
        })
        
    except Exception as e:
        logger.error(f"Create batch commands error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/commands/pending', methods=['GET'])
@verify_collector_key
def fetch_pending_commands():
    """采集器获取待执行命令
    
    边缘采集器轮询此接口获取需要执行的命令
    返回按优先级排序的待执行命令列表
    """
    try:
        site_id = g.site_id
        now = datetime.utcnow()
        
        expired_count = MinerCommand.query.filter(
            MinerCommand.site_id == site_id,
            MinerCommand.status == 'pending',
            MinerCommand.expires_at < now
        ).update({'status': 'expired'})
        
        if expired_count > 0:
            db.session.commit()
            logger.info(f"Marked {expired_count} expired commands for site {site_id}")
        
        commands = MinerCommand.query.filter(
            MinerCommand.site_id == site_id,
            MinerCommand.status == 'pending',
            MinerCommand.expires_at >= now
        ).order_by(
            MinerCommand.priority.desc(),
            MinerCommand.created_at.asc()
        ).limit(50).all()
        
        command_payloads = []
        for cmd in commands:
            cmd.status = 'sent'
            cmd.sent_at = now
            command_payloads.append(cmd.to_command_payload())
        
        if commands:
            db.session.commit()
            logger.info(f"Sent {len(commands)} commands to collector for site {site_id}")
        
        return jsonify({
            'success': True,
            'commands': command_payloads,
            'count': len(command_payloads)
        })
        
    except Exception as e:
        logger.error(f"Fetch pending commands error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/commands/<int:command_id>/result', methods=['POST'])
@verify_collector_key
def report_command_result(command_id):
    """采集器报告命令执行结果
    
    请求体:
    {
        "status": "completed|failed",
        "result_code": 0,  // 0=成功, 非0=错误
        "result_message": "Success" 
    }
    """
    try:
        site_id = g.site_id
        
        command = MinerCommand.query.filter_by(
            id=command_id,
            site_id=site_id
        ).first()
        
        if not command:
            return jsonify({'success': False, 'error': 'Command not found'}), 404
        
        data = request.get_json()
        
        command.status = data.get('status', 'completed')
        command.result_code = data.get('result_code', 0)
        command.result_message = data.get('result_message')
        command.executed_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Command {command_id} result: {command.status} - {command.result_message}")
        
        return jsonify({
            'success': True,
            'message': 'Result reported successfully'
        })
        
    except Exception as e:
        logger.error(f"Report command result error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/commands/<int:command_id>', methods=['DELETE'])
def cancel_command(command_id):
    """取消待执行的命令"""
    try:
        command = MinerCommand.query.get(command_id)
        
        if not command:
            return jsonify({'success': False, 'error': 'Command not found'}), 404
        
        if command.status not in ['pending', 'sent']:
            return jsonify({
                'success': False, 
                'error': f'Cannot cancel command with status: {command.status}'
            }), 400
        
        command.status = 'cancelled'
        db.session.commit()
        
        logger.info(f"Command {command_id} cancelled")
        
        return jsonify({
            'success': True,
            'message': 'Command cancelled successfully'
        })
        
    except Exception as e:
        logger.error(f"Cancel command error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/commands/history', methods=['GET'])
def get_command_history():
    """获取命令执行历史"""
    try:
        site_id = request.args.get('site_id', type=int)
        miner_id = request.args.get('miner_id')
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        
        query = MinerCommand.query
        
        if site_id:
            query = query.filter(MinerCommand.site_id == site_id)
        if miner_id:
            query = query.filter(MinerCommand.miner_id == miner_id)
        if status:
            query = query.filter(MinerCommand.status == status)
        
        commands = query.order_by(MinerCommand.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'commands': [cmd.to_dict() for cmd in commands],
            'count': len(commands)
        })
        
    except Exception as e:
        logger.error(f"Get command history error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/commands/stats', methods=['GET'])
def get_command_stats():
    """获取命令统计信息"""
    try:
        site_id = request.args.get('site_id', type=int)
        
        query = db.session.query(
            MinerCommand.status,
            func.count(MinerCommand.id).label('count')
        )
        
        if site_id:
            query = query.filter(MinerCommand.site_id == site_id)
        
        stats = query.group_by(MinerCommand.status).all()
        
        result = {s.status: s.count for s in stats}
        
        pending_count = MinerCommand.query.filter(
            MinerCommand.status == 'pending',
            MinerCommand.expires_at >= datetime.utcnow()
        )
        if site_id:
            pending_count = pending_count.filter(MinerCommand.site_id == site_id)
        
        return jsonify({
            'success': True,
            'stats': result,
            'active_pending': pending_count.count(),
            'total': sum(result.values())
        })
        
    except Exception as e:
        logger.error(f"Get command stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/miners/<int:miner_id>/status', methods=['GET'])
def get_miner_comprehensive_status(miner_id):
    """获取矿机综合状态 - 整合遥测数据、收益预测、矿池信息、板健康
    
    GET /api/collector/miners/{miner_id}/status
    
    Returns:
        {
            "success": true,
            "miner": {
                "id": 3021,
                "name": "S19-3021",
                "model": "Antminer S19 Pro",
                "ip_address": "192.168.1.100",
                "site_name": "Site A",
                "online": true,
                "last_seen": "2 minutes ago",
                "overall_health": "healthy"
            },
            "performance": {
                "hashrate_ths": 194.3,
                "hashrate_5s_ths": 193.8,
                "hashrate_expected_ths": 195.0,
                "hashrate_deviation_pct": -0.36,
                "power_kw": 3.25,
                "efficiency_jths": 16.7,
                "temp_min_c": 68,
                "temp_max_c": 75,
                "temp_avg_c": 71.5,
                "uptime_hours": 720
            },
            "pool": {
                "url": "stratum+tcp://pool.antpool.com:3333",
                "worker": "user.worker001",
                "latency_ms": 45,
                "shares_accepted_24h": 12456,
                "shares_rejected_24h": 23,
                "rejected_rate_pct": 0.18
            },
            "boards": {
                "total": 3,
                "healthy": 3,
                "data": [
                    {"index": 0, "hashrate_ths": 65.2, "temp_c": 72, "chips_ok": 63, "chips_total": 63, "health": "healthy"},
                    {"index": 1, "hashrate_ths": 64.8, "temp_c": 74, "chips_ok": 63, "chips_total": 63, "health": "healthy"},
                    {"index": 2, "hashrate_ths": 64.3, "temp_c": 71, "chips_ok": 63, "chips_total": 63, "health": "healthy"}
                ]
            },
            "revenue": {
                "daily_btc": 0.000275,
                "daily_usd": 23.50,
                "power_cost_usd": 11.20,
                "net_profit_usd": 12.30,
                "btc_price": 85400,
                "profit_margin_pct": 52.3,
                "roi_days": 450
            },
            "history_24h": [
                {"hour": "00:00", "hashrate_ths": 194.1, "net_profit_usd": 0.51},
                ...
            ]
        }
    """
    from models import HostingMiner, HostingSite
    from app import db
    
    try:
        miner = HostingMiner.query.get(miner_id)
        if not miner:
            return jsonify({'success': False, 'error': 'Miner not found'}), 404
        
        site = HostingSite.query.get(miner.site_id)
        
        serial = getattr(miner, 'serial_number', None) or f"MINER-{miner_id}"
        telemetry = MinerTelemetryLive.query.filter_by(
            site_id=miner.site_id,
            miner_id=serial
        ).first()
        
        last_seen_text = "Never"
        last_seen_ts = None
        if telemetry and telemetry.last_seen:
            last_seen_ts = telemetry.last_seen
        elif hasattr(miner, 'last_seen') and miner.last_seen:
            last_seen_ts = miner.last_seen
        
        if last_seen_ts:
            delta = datetime.utcnow() - last_seen_ts
            if delta.total_seconds() < 60:
                last_seen_text = "Just now"
            elif delta.total_seconds() < 3600:
                last_seen_text = f"{int(delta.total_seconds() // 60)} minutes ago"
            elif delta.total_seconds() < 86400:
                last_seen_text = f"{int(delta.total_seconds() // 3600)} hours ago"
            else:
                last_seen_text = f"{int(delta.days)} days ago"
        
        miner_hashrate = miner.actual_hashrate if hasattr(miner, 'actual_hashrate') and miner.actual_hashrate else 0
        miner_hashrate_5s = miner.hashrate_5s if hasattr(miner, 'hashrate_5s') and miner.hashrate_5s else miner_hashrate
        miner_power = miner.actual_power if hasattr(miner, 'actual_power') and miner.actual_power else 0
        
        hashrate_ths = (telemetry.hashrate_ghs / 1000) if telemetry and telemetry.hashrate_ghs else miner_hashrate_5s
        hashrate_5s_ths = (telemetry.hashrate_5s_ghs / 1000) if telemetry and telemetry.hashrate_5s_ghs else miner_hashrate_5s
        hashrate_expected_ths = (telemetry.hashrate_expected_ghs / 1000) if telemetry and telemetry.hashrate_expected_ghs else (miner_hashrate if miner_hashrate > 0 else hashrate_ths)
        
        if hashrate_expected_ths > 0:
            hashrate_deviation_pct = ((hashrate_ths - hashrate_expected_ths) / hashrate_expected_ths) * 100
        else:
            hashrate_deviation_pct = 0
        
        power_kw = (telemetry.power_consumption / 1000) if telemetry and telemetry.power_consumption else (miner_power / 1000 if miner_power else 3.3)
        efficiency_jths = (power_kw * 1000 / hashrate_ths) if hashrate_ths > 0 else 0
        
        miner_temp_avg = getattr(miner, 'temperature_avg', None) or 0
        miner_temp_max = getattr(miner, 'temperature_max', None) or (miner_temp_avg + 8 if miner_temp_avg else 0)
        temp_min_c = telemetry.temperature_min if telemetry and telemetry.temperature_min else (miner_temp_avg - 5 if miner_temp_avg else 0)
        temp_max_c = telemetry.temperature_max if telemetry and telemetry.temperature_max else miner_temp_max
        temp_avg_c = telemetry.temperature_avg if telemetry and telemetry.temperature_avg else miner_temp_avg
        
        miner_uptime = getattr(miner, 'uptime_seconds', None) or 0
        uptime_hours = (telemetry.uptime_seconds / 3600) if telemetry and telemetry.uptime_seconds else (miner_uptime / 3600 if miner_uptime else 0)
        
        miner_pool_url = getattr(miner, 'pool_url', None) or ""
        miner_pool_worker = getattr(miner, 'pool_worker', None) or ""
        pool_url = telemetry.pool_url if telemetry and telemetry.pool_url else miner_pool_url
        worker_name = telemetry.worker_name if telemetry and telemetry.worker_name else miner_pool_worker
        pool_latency_ms = telemetry.pool_latency_ms if telemetry and telemetry.pool_latency_ms else 0
        
        miner_accepted = getattr(miner, 'accepted_shares', None) or 0
        miner_rejected = getattr(miner, 'rejected_shares', None) or 0
        shares_accepted = telemetry.accepted_shares if telemetry and telemetry.accepted_shares else miner_accepted
        shares_rejected = telemetry.rejected_shares if telemetry and telemetry.rejected_shares else miner_rejected
        total_shares = shares_accepted + shares_rejected
        rejected_rate_pct = (shares_rejected / total_shares * 100) if total_shares > 0 else 0
        
        raw_boards_data = []
        if telemetry and telemetry.boards_data:
            if isinstance(telemetry.boards_data, list):
                raw_boards_data = telemetry.boards_data
            elif isinstance(telemetry.boards_data, dict):
                raw_boards_data = [telemetry.boards_data]
        
        boards_total = telemetry.boards_total if telemetry and telemetry.boards_total else 3
        boards_healthy = telemetry.boards_healthy if telemetry and telemetry.boards_healthy else 3
        
        miner_online = getattr(miner, 'cgminer_online', False) or (getattr(miner, 'status', '') == 'online')
        is_online = (telemetry.online if telemetry else False) or miner_online
        
        if is_online:
            overall_health = telemetry.overall_health if telemetry and telemetry.overall_health else "healthy"
        else:
            overall_health = "offline"
        
        boards_data = []
        for board in raw_boards_data:
            if isinstance(board, dict):
                boards_data.append({
                    "index": board.get("board_index", board.get("index", 0)),
                    "hashrate_ths": board.get("hashrate_ths", 0),
                    "temp_c": board.get("temperature_c", board.get("temp_c", 0)),
                    "chips_ok": board.get("chips_ok", 0),
                    "chips_total": board.get("chips_total", 0),
                    "health": board.get("health", "offline")
                })
        
        revenue_data = calculate_miner_revenue(
            hashrate_ths=hashrate_ths,
            power_kw=power_kw,
            electricity_rate=miner.electricity_rate if hasattr(miner, 'electricity_rate') and miner.electricity_rate else 0.08
        )
        
        history_24h = get_miner_history_24h(miner.site_id, serial)
        
        miner_model_name = "Unknown"
        try:
            if telemetry and telemetry.model:
                miner_model_name = telemetry.model
            elif hasattr(miner, 'miner_model_id') and miner.miner_model_id:
                from models import MinerModel
                model_record = MinerModel.query.get(miner.miner_model_id)
                if model_record:
                    miner_model_name = model_record.model_name
        except Exception as model_err:
            logger.warning(f"Error fetching miner model: {model_err}")
            miner_model_name = "Unknown"
        
        miner_fan_avg = getattr(miner, 'fan_avg', None) or 0
        miner_hw_errors = getattr(miner, 'hardware_errors', None) or 0
        fan_speeds = telemetry.fan_speeds if telemetry and telemetry.fan_speeds else ([miner_fan_avg] if miner_fan_avg else [])
        hw_errors = telemetry.hardware_errors if telemetry else miner_hw_errors
        
        result = {
            "success": True,
            "miner": {
                "id": miner_id,
                "name": serial,
                "model": miner_model_name,
                "ip_address": telemetry.ip_address if telemetry else (miner.ip_address if hasattr(miner, 'ip_address') else ""),
                "site_name": site.name if site else "Unknown",
                "online": is_online,
                "last_seen": last_seen_text,
                "overall_health": overall_health
            },
            "performance": {
                "hashrate_ths": round(hashrate_ths, 2),
                "hashrate_5s_ths": round(hashrate_5s_ths, 2),
                "hashrate_expected_ths": round(hashrate_expected_ths, 2),
                "hashrate_deviation_pct": round(hashrate_deviation_pct, 2),
                "power_kw": round(power_kw, 2),
                "efficiency_jths": round(efficiency_jths, 2),
                "temp_min_c": round(temp_min_c, 1),
                "temp_max_c": round(temp_max_c, 1),
                "temp_avg_c": round(temp_avg_c, 1),
                "uptime_hours": round(uptime_hours, 1),
                "fan_speeds": fan_speeds,
                "hardware_errors": hw_errors
            },
            "pool": {
                "url": pool_url,
                "worker": worker_name,
                "latency_ms": round(pool_latency_ms, 1),
                "shares_accepted_24h": shares_accepted,
                "shares_rejected_24h": shares_rejected,
                "rejected_rate_pct": round(rejected_rate_pct, 2)
            },
            "boards": {
                "total": boards_total,
                "healthy": boards_healthy,
                "data": boards_data
            },
            "revenue": revenue_data,
            "history_24h": history_24h
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get miner status error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def calculate_miner_revenue(hashrate_ths: float, power_kw: float, electricity_rate: float = 0.08) -> dict:
    """计算矿机收益"""
    try:
        from services.hosting_revenue_service import HostingRevenueService
        service = HostingRevenueService()
        
        if hashrate_ths <= 0:
            return {
                "daily_btc": 0,
                "daily_usd": 0,
                "power_cost_usd": 0,
                "net_profit_usd": 0,
                "btc_price": service._btc_price,
                "profit_margin_pct": 0,
                "roi_days": 0
            }
        
        hashrate_h = hashrate_ths * 1e12
        network_hashrate = service._network_hashrate
        block_reward = service._block_reward
        btc_price = service._btc_price
        
        blocks_per_day = 144
        daily_btc = (hashrate_h / network_hashrate) * blocks_per_day * block_reward
        daily_usd = daily_btc * btc_price
        
        daily_power_kwh = power_kw * 24
        power_cost_usd = daily_power_kwh * electricity_rate
        
        net_profit_usd = daily_usd - power_cost_usd
        
        profit_margin_pct = (net_profit_usd / daily_usd * 100) if daily_usd > 0 else 0
        
        miner_cost = 5000
        roi_days = (miner_cost / net_profit_usd) if net_profit_usd > 0 else 9999
        
        return {
            "daily_btc": round(daily_btc, 8),
            "daily_usd": round(daily_usd, 2),
            "power_cost_usd": round(power_cost_usd, 2),
            "net_profit_usd": round(net_profit_usd, 2),
            "btc_price": btc_price,
            "profit_margin_pct": round(profit_margin_pct, 1),
            "roi_days": round(roi_days, 0)
        }
        
    except Exception as e:
        logger.error(f"Calculate revenue error: {e}")
        return {
            "daily_btc": 0,
            "daily_usd": 0,
            "power_cost_usd": 0,
            "net_profit_usd": 0,
            "btc_price": 95000,
            "profit_margin_pct": 0,
            "roi_days": 0
        }


def get_miner_history_24h(site_id: int, miner_id: str) -> list:
    """获取矿机24小时历史数据 (含算力效率)
    
    Returns hourly data with:
    - hashrate_ths: Average hashrate in TH/s
    - power_w: Average power consumption in watts
    - efficiency_thkw: Power efficiency in TH/kW (higher is better)
    """
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        history = MinerTelemetryHistory.query.filter(
            MinerTelemetryHistory.site_id == site_id,
            MinerTelemetryHistory.miner_id == miner_id,
            MinerTelemetryHistory.timestamp >= cutoff
        ).order_by(MinerTelemetryHistory.timestamp.asc()).all()
        
        if not history:
            return []
        
        hourly_data = {}
        for record in history:
            hour_key = record.timestamp.strftime("%H:00")
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    "hashrate_samples": [],
                    "power_samples": []
                }
            hourly_data[hour_key]["hashrate_samples"].append(record.hashrate_ghs / 1000)
            if record.power_consumption and record.power_consumption > 0:
                hourly_data[hour_key]["power_samples"].append(record.power_consumption)
        
        result = []
        for hour, data in sorted(hourly_data.items()):
            avg_hashrate = sum(data["hashrate_samples"]) / len(data["hashrate_samples"]) if data["hashrate_samples"] else 0
            avg_power = sum(data["power_samples"]) / len(data["power_samples"]) if data["power_samples"] else 3300
            
            efficiency_thkw = (avg_hashrate * 1000 / avg_power) if avg_power > 0 else 0
            
            result.append({
                "hour": hour,
                "hashrate_ths": round(avg_hashrate, 2),
                "power_w": round(avg_power, 0),
                "efficiency_thkw": round(efficiency_thkw, 2)
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Get history error: {e}")
        return []


@collector_bp.route('/manual')
def deployment_manual():
    """显示 Edge Collector 部署手册"""
    from flask import render_template
    return render_template('collector/deployment_manual.html')


@collector_bp.route('/download-package')
def download_package():
    """下载 Edge Collector 部署包"""
    import io
    import zipfile
    from flask import send_file
    
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        try:
            with open('edge_collector/cgminer_collector.py', 'r') as f:
                zf.writestr('edge_collector/cgminer_collector.py', f.read())
        except:
            zf.writestr('edge_collector/cgminer_collector.py', '# Edge Collector - See README for full version')
        
        try:
            with open('edge_collector/README.md', 'r') as f:
                zf.writestr('edge_collector/README.md', f.read())
        except:
            zf.writestr('edge_collector/README.md', '''# HashInsight Edge Collector

## Quick Start

1. Install dependencies: `pip install requests`
2. Edit `collector_config.json` with your API key and site ID
3. Run: `python cgminer_collector.py`

For full documentation, visit: https://calc.hashinsight.net/api/collector/manual
''')
        
        zf.writestr('edge_collector/collector_config.json', '''{
    "api_url": "https://calc.hashinsight.net",
    "api_key": "hsc_your_api_key_here",
    "site_id": "site_001",
    "collection_interval": 30,
    "max_workers": 50,
    "retry_attempts": 3,
    "cache_dir": "./cache",
    "log_level": "INFO",
    "miners": [],
    "ip_ranges": [
        {
            "range": "192.168.1.100-192.168.1.199",
            "prefix": "S19_",
            "type": "antminer"
        }
    ]
}''')
        
        zf.writestr('edge_collector/requirements.txt', '''# HashInsight Edge Collector Dependencies
requests>=2.28.0
''')
        
        zf.writestr('edge_collector/Dockerfile', '''FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "cgminer_collector.py"]
''')
    
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='edge_collector.zip'
    )


@collector_bp.route('/storage-stats', methods=['GET'])
def get_storage_stats():
    """
    获取遥测存储统计
    
    GET /api/collector/storage-stats
    
    Returns:
        - Table sizes and row counts
        - Oldest/newest data timestamps
        - Total telemetry storage size
    """
    try:
        from services.telemetry_storage import TelemetryStorageManager
        stats = TelemetryStorageManager.get_storage_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Get storage stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collector_bp.route('/scheduler-status', methods=['GET'])
def get_scheduler_status():
    """
    获取遥测调度器状态
    
    GET /api/collector/scheduler-status
    """
    try:
        from services.telemetry_scheduler import telemetry_scheduler
        status = telemetry_scheduler.get_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"Get scheduler status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def register_collector_routes(app):
    """注册采集器路由"""
    app.register_blueprint(collector_bp)
    logger.info("Edge Collector API registered successfully")
