"""
采集器管理路由
Collector Management Routes

提供采集器密钥管理和实时遥测数据展示
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from sqlalchemy import func, desc
from models import db, HostingSite
from auth import login_required
from common.rbac import require_permission

logger = logging.getLogger(__name__)

collector_routes_bp = Blueprint('collector_routes', __name__, url_prefix='/collector')

try:
    from api.collector_api import (
        CollectorKey, MinerTelemetryLive, MinerTelemetryHistory, CollectorUploadLog
    )
except ImportError:
    CollectorKey = None
    MinerTelemetryLive = None
    MinerTelemetryHistory = None
    CollectorUploadLog = None


@collector_routes_bp.route('/')
@login_required
def index():
    """采集器管理首页"""
    from flask import session
    lang = session.get('language', 'en')
    
    sites = HostingSite.query.all()
    
    site_stats = []
    for site in sites:
        if MinerTelemetryLive:
            stats = db.session.query(
                func.count(MinerTelemetryLive.id).label('total'),
                func.sum(db.case((MinerTelemetryLive.online == True, 1), else_=0)).label('online'),
                func.sum(MinerTelemetryLive.hashrate_ghs).label('hashrate'),
                func.avg(MinerTelemetryLive.temperature_avg).label('temp')
            ).filter(MinerTelemetryLive.site_id == site.id).first()
            
            key_count = CollectorKey.query.filter_by(site_id=site.id, is_active=True).count() if CollectorKey else 0
            
            site_stats.append({
                'site': site,
                'total_miners': stats.total or 0,
                'online_miners': int(stats.online or 0),
                'total_hashrate_ths': (stats.hashrate or 0) / 1000,
                'avg_temperature': round(stats.temp or 0, 1),
                'collector_keys': key_count
            })
        else:
            site_stats.append({
                'site': site,
                'total_miners': 0,
                'online_miners': 0,
                'total_hashrate_ths': 0,
                'avg_temperature': 0,
                'collector_keys': 0
            })
    
    return render_template('collector/index.html', 
                         site_stats=site_stats,
                         lang=lang)


@collector_routes_bp.route('/guide')
@login_required
def guide():
    """Edge Collector部署指南"""
    from flask import session
    lang = session.get('language', 'en')
    return render_template('collector/guide.html', lang=lang)


@collector_routes_bp.route('/local-guide')
@login_required
def local_guide():
    """本地部署指南 - 直接连接矿机"""
    from flask import session
    lang = session.get('language', 'en')
    return render_template('collector/local_guide.html', lang=lang)


@collector_routes_bp.route('/site/<int:site_id>')
@login_required
def site_detail(site_id):
    """站点实时监控详情"""
    from flask import session
    lang = session.get('language', 'en')
    
    site = HostingSite.query.get_or_404(site_id)
    
    if MinerTelemetryLive:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        online_only = request.args.get('online', 'all')
        search = request.args.get('search', '')
        
        query = MinerTelemetryLive.query.filter_by(site_id=site_id)
        
        if online_only == 'online':
            query = query.filter_by(online=True)
        elif online_only == 'offline':
            query = query.filter_by(online=False)
        
        if search:
            query = query.filter(MinerTelemetryLive.miner_id.ilike(f'%{search}%'))
        
        query = query.order_by(MinerTelemetryLive.miner_id)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        miners = pagination.items
        
        stats = db.session.query(
            func.count(MinerTelemetryLive.id).label('total'),
            func.sum(db.case((MinerTelemetryLive.online == True, 1), else_=0)).label('online'),
            func.sum(MinerTelemetryLive.hashrate_ghs).label('hashrate'),
            func.avg(MinerTelemetryLive.temperature_avg).label('temp'),
            func.max(MinerTelemetryLive.temperature_max).label('max_temp')
        ).filter(MinerTelemetryLive.site_id == site_id).first()
        
        recent_uploads = CollectorUploadLog.query.filter_by(
            site_id=site_id
        ).order_by(desc(CollectorUploadLog.upload_time)).limit(10).all() if CollectorUploadLog else []
    else:
        miners = []
        pagination = None
        stats = None
        recent_uploads = []
    
    collector_keys = CollectorKey.query.filter_by(site_id=site_id).all() if CollectorKey else []
    
    return render_template('collector/site_detail.html',
                         site=site,
                         miners=miners,
                         pagination=pagination,
                         stats=stats,
                         recent_uploads=recent_uploads,
                         collector_keys=collector_keys,
                         lang=lang,
                         online_filter=request.args.get('online', 'all'),
                         search=request.args.get('search', ''))


@collector_routes_bp.route('/site/<int:site_id>/keys', methods=['GET', 'POST'])
@login_required
@require_permission('hosting.site_management', 'FULL')
def manage_keys(site_id):
    """管理采集器密钥"""
    from flask import session
    lang = session.get('language', 'en')
    
    site = HostingSite.query.get_or_404(site_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name', 'New Collector')
            
            api_key = f"hsc_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            new_key = CollectorKey(
                key_hash=key_hash,
                site_id=site_id,
                name=name,
                is_active=True
            )
            db.session.add(new_key)
            db.session.commit()
            
            if lang == 'zh':
                flash(f'采集器密钥已创建: {api_key}', 'success')
            else:
                flash(f'Collector key created: {api_key}', 'success')
            
            return render_template('collector/key_created.html',
                                 site=site,
                                 api_key=api_key,
                                 key_name=name,
                                 lang=lang)
        
        elif action == 'delete':
            key_id = request.form.get('key_id', type=int)
            key = CollectorKey.query.get(key_id)
            if key and key.site_id == site_id:
                db.session.delete(key)
                db.session.commit()
                if lang == 'zh':
                    flash('密钥已删除', 'success')
                else:
                    flash('Key deleted', 'success')
        
        elif action == 'toggle':
            key_id = request.form.get('key_id', type=int)
            key = CollectorKey.query.get(key_id)
            if key and key.site_id == site_id:
                key.is_active = not key.is_active
                db.session.commit()
                status = 'enabled' if key.is_active else 'disabled'
                if lang == 'zh':
                    flash(f'密钥已{("启用" if key.is_active else "禁用")}', 'success')
                else:
                    flash(f'Key {status}', 'success')
        
        return redirect(url_for('collector_routes.manage_keys', site_id=site_id))
    
    keys = CollectorKey.query.filter_by(site_id=site_id).order_by(desc(CollectorKey.created_at)).all() if CollectorKey else []
    
    return render_template('collector/manage_keys.html',
                         site=site,
                         keys=keys,
                         lang=lang)


@collector_routes_bp.route('/api/live/<int:site_id>')
@login_required
def api_live_data(site_id):
    """获取实时矿机数据 (JSON API for dashboard refresh)"""
    if not MinerTelemetryLive:
        return jsonify({'success': False, 'error': 'Telemetry not available'})
    
    try:
        stats = db.session.query(
            func.count(MinerTelemetryLive.id).label('total'),
            func.sum(db.case((MinerTelemetryLive.online == True, 1), else_=0)).label('online'),
            func.sum(MinerTelemetryLive.hashrate_ghs).label('hashrate'),
            func.avg(MinerTelemetryLive.temperature_avg).label('temp'),
            func.max(MinerTelemetryLive.temperature_max).label('max_temp')
        ).filter(MinerTelemetryLive.site_id == site_id).first()
        
        recent_miners = MinerTelemetryLive.query.filter_by(
            site_id=site_id
        ).order_by(desc(MinerTelemetryLive.updated_at)).limit(20).all()
        
        miners_data = []
        for m in recent_miners:
            miners_data.append({
                'miner_id': m.miner_id,
                'ip_address': m.ip_address,
                'online': m.online,
                'hashrate_ths': m.hashrate_ghs / 1000 if m.hashrate_ghs else 0,
                'temperature': m.temperature_avg,
                'temp_max': m.temperature_max,
                'fan_speeds': m.fan_speeds or [],
                'uptime_hours': m.uptime_seconds / 3600 if m.uptime_seconds else 0,
                'updated': m.updated_at.strftime('%H:%M:%S') if m.updated_at else '-'
            })
        
        return jsonify({
            'success': True,
            'data': {
                'stats': {
                    'total': stats.total or 0,
                    'online': int(stats.online or 0),
                    'offline': (stats.total or 0) - int(stats.online or 0),
                    'hashrate_ths': round((stats.hashrate or 0) / 1000, 2),
                    'avg_temp': round(stats.temp or 0, 1),
                    'max_temp': round(stats.max_temp or 0, 1),
                    'online_rate': round(int(stats.online or 0) / max(stats.total or 1, 1) * 100, 1)
                },
                'miners': miners_data,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"API live data error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@collector_routes_bp.route('/api/history/<int:site_id>/<miner_id>')
@login_required
def api_miner_history(site_id, miner_id):
    """获取矿机历史数据 (用于图表)"""
    if not MinerTelemetryHistory:
        return jsonify({'success': False, 'error': 'History not available'})
    
    try:
        hours = request.args.get('hours', 24, type=int)
        since = datetime.utcnow() - timedelta(hours=hours)
        
        records = MinerTelemetryHistory.query.filter(
            MinerTelemetryHistory.site_id == site_id,
            MinerTelemetryHistory.miner_id == miner_id,
            MinerTelemetryHistory.timestamp >= since
        ).order_by(MinerTelemetryHistory.timestamp).all()
        
        history = []
        for r in records:
            history.append({
                'timestamp': r.timestamp.isoformat(),
                'hashrate_ths': r.hashrate_ghs / 1000 if r.hashrate_ghs else 0,
                'temperature': r.temperature_avg,
                'temp_max': r.temperature_max,
                'online': r.online
            })
        
        return jsonify({
            'success': True,
            'data': {
                'miner_id': miner_id,
                'history': history,
                'hours': hours
            }
        })
        
    except Exception as e:
        logger.error(f"API history error: {e}")
        return jsonify({'success': False, 'error': str(e)})


def register_collector_routes(app):
    """注册采集器管理路由"""
    app.register_blueprint(collector_routes_bp)
    logger.info("Collector management routes registered successfully")
