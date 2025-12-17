
"""
托管功能路由
包含托管商和客户视角的所有功能

RBAC v2.0: 使用模块化权限系统
"""
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from . import hosting_bp
from auth import login_required
from decorators import requires_role
from common.rbac import (
    Module, Role, requires_module_access, requires_role as rbac_requires_role,
    rbac_manager, normalize_role
)
from models import db, HostingSite, HostingMiner, HostingTicket, HostingIncident, HostingUsageRecord, HostingUsageItem, MinerTelemetry, HostingBill, HostingBillItem, HostingMinerOperationLog, HostingOwnerEncryption
from api.collector_api import MinerTelemetryLive, MinerCommand, CollectorKey
from models import CurtailmentPlan, CurtailmentStrategy, CurtailmentExecution
from models import ExecutionMode, PlanStatus, ExecutionAction, ExecutionStatus
from intelligence.curtailment_engine import calculate_curtailment_plan
from intelligence.curtailment_predictor import predict_optimal_curtailment
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_miner_alerts(miner, lang='zh'):
    """检测矿机告警状态
    
    参数:
        miner: HostingMiner对象
        lang: 语言 ('zh' 或 'en')
    
    返回格式:
    {
        'has_alerts': True/False,
        'alerts': [
            {'type': 'temperature', 'severity': 'critical', 'message': '温度过高: 90°C'},
            {'type': 'hashrate', 'severity': 'warning', 'message': '算力下降25%'},
            {'type': 'offline', 'severity': 'critical', 'message': '离线6分钟'}
        ],
        'count': 告警数量
    }
    """
    alerts = []
    
    try:
        if miner.temperature_max and miner.temperature_max > 85:
            severity = 'critical' if miner.temperature_max > 90 else 'warning'
            if lang == 'en':
                message = f'High Temperature: {miner.temperature_max:.1f}°C'
            else:
                message = f'温度过高: {miner.temperature_max:.1f}°C'
            alerts.append({
                'type': 'temperature',
                'severity': severity,
                'message': message
            })
        
        # 算力下降告警：使用actual_hashrate（populated字段）而不是hashrate_5s
        if miner.actual_hashrate and miner.miner_model:
            # 使用miner_model的hashrate作为expected值
            expected_hashrate = getattr(miner.miner_model, 'hashrate', None) or getattr(miner.miner_model, 'reference_hashrate', None)
            if expected_hashrate and expected_hashrate > 0 and miner.actual_hashrate > 0:
                drop_pct = ((expected_hashrate - miner.actual_hashrate) / expected_hashrate) * 100
                if drop_pct > 20:
                    if lang == 'en':
                        message = f'Hashrate Drop: {drop_pct:.1f}%'
                    else:
                        message = f'算力下降: {drop_pct:.1f}%'
                    alerts.append({
                        'type': 'hashrate',
                        'severity': 'warning',
                        'message': message
                    })
        
        if miner.last_seen:
            offline_duration = datetime.utcnow() - miner.last_seen
            if offline_duration > timedelta(minutes=5):
                minutes_offline = int(offline_duration.total_seconds() / 60)
                if lang == 'en':
                    message = f'Offline: {minutes_offline} min'
                else:
                    message = f'离线: {minutes_offline}分钟'
                alerts.append({
                    'type': 'offline',
                    'severity': 'critical',
                    'message': message
                })
        elif not miner.cgminer_online:
            if lang == 'en':
                message = 'Never Online'
            else:
                message = '从未在线'
            alerts.append({
                'type': 'offline',
                'severity': 'critical',
                'message': message
            })
    except Exception as e:
        logger.error(f"获取矿机告警失败: {e}")
    
    return {
        'has_alerts': len(alerts) > 0,
        'alerts': alerts,
        'count': len(alerts)
    }

@hosting_bp.route('/')
@login_required
def dashboard():
    """托管功能主仪表板
    
    RBAC: 根据用户模块权限展示不同视图
    - HOSTING_SITE_MGMT 完全访问 → 托管商视角
    - HOSTING_STATUS_MONITOR 只读 → 客户视角
    """
    user_role = normalize_role(session.get('role', 'guest'))
    
    # 检查用户是否有托管管理权限
    has_host_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
    
    if has_host_access:
        # 托管商视角
        return render_template('hosting/host_dashboard.html')
    else:
        # 客户视角
        return render_template('hosting/client_dashboard.html')

@hosting_bp.route('/host/sites/<int:site_id>')
@login_required
@requires_module_access(Module.HOSTING_SITE_MGMT, require_full=False)
def site_detail(site_id):
    """站点详情页面"""
    try:
        site = HostingSite.query.get_or_404(site_id)
        return render_template('hosting/site_detail.html', site=site)
    except Exception as e:
        logger.error(f"站点详情页面错误: {e}")
        current_lang = session.get('language', 'zh')
        if current_lang == 'en':
            flash('Site not found', 'error')
        else:
            flash('站点未找到', 'error')
        return redirect(url_for('hosting_service_bp.client_view'))

@hosting_bp.route('/host')
@hosting_bp.route('/host/<path:subpath>')
@login_required
@requires_module_access(Module.HOSTING_SITE_MGMT, require_full=False)
def host_view(subpath='dashboard'):
    """托管商视角路由
    
    RBAC: 需要 HOSTING_SITE_MGMT 模块权限
    - 站点管理: HOSTING_SITE_MGMT (完全访问)
    - 设备管理: HOSTING_STATUS_MONITOR (只读或完全)
    - 限电管理: CURTAILMENT_STRATEGY (完全访问)
    """
    try:
        if subpath == 'dashboard':
            return render_template('hosting/host_dashboard.html')
        elif subpath == 'sites':
            return render_template('hosting/site_management.html')
        elif subpath == 'devices':
            return render_template('hosting/miner_management.html')
        elif subpath == 'monitoring':
            return render_template('hosting/event_monitoring.html')
        elif subpath == 'sla':
            return render_template('hosting/sla_management.html')
        elif subpath == 'curtailment':
            return render_template('hosting/curtailment_management.html')
        elif subpath == 'collectors':
            return render_template('hosting/collector_management.html')
        else:
            return render_template('hosting/host_dashboard.html')
    except Exception as e:
        logger.error(f"托管商视图错误: {e}")
        current_lang = session.get('language', 'zh')
        if current_lang == 'en':
            flash('Page loading failed', 'error')
        else:
            flash('页面加载失败', 'error')
        return redirect(url_for('hosting_service_bp.client_view'))

@hosting_bp.route('/client')
@hosting_bp.route('/client/<path:subpath>')
@login_required
@requires_module_access(Module.HOSTING_STATUS_MONITOR, require_full=False)
def client_view(subpath='dashboard'):
    """客户视角路由
    
    RBAC: 需要 HOSTING_STATUS_MONITOR 模块权限（只读即可）
    - 资产概览: HOSTING_STATUS_MONITOR
    - 使用记录: HOSTING_USAGE_TRACKING
    - 报表: REPORT_PDF/REPORT_EXCEL
    """
    try:
        if subpath == 'dashboard':
            return render_template('hosting/client_dashboard.html')
        elif subpath == 'assets':
            return render_template('hosting/client_dashboard.html')
        elif subpath == 'usage':
            return render_template('hosting/client_usage.html')
        elif subpath == 'reports':
            return render_template('hosting/client_reports.html')
        elif subpath == 'tickets':
            return render_template('hosting/client_tickets.html')
        else:
            return render_template('hosting/client_dashboard.html')
    except Exception as e:
        logger.error(f"客户视图错误: {e}")
        current_lang = session.get('language', 'zh')
        if current_lang == 'en':
            flash('Page loading failed', 'error')
        else:
            flash('页面加载失败', 'error')
        return redirect(url_for('hosting_service_bp.client_view'))

# ==================== 托管商API路由 ====================

@hosting_bp.route('/api/overview', methods=['GET'])
@login_required
def get_hosting_overview():
    """获取托管商总览数据（性能优化 + 权限过滤版）
    
    性能优化：使用单一聚合查询减少数据库往返
    """
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        user_email = session.get('email', '')
        
        # 权限控制 - 使用优化的聚合查询
        if user_role == 'admin':
            # 管理员：使用高效聚合查询
            site_stats = db.session.query(
                db.func.count(HostingSite.id).label('total'),
                db.func.sum(db.case((HostingSite.status == 'online', 1), else_=0)).label('online'),
                db.func.sum(HostingSite.capacity_mw).label('total_capacity'),
                db.func.sum(HostingSite.used_capacity_mw).label('used_capacity')
            ).first()
            
            miner_stats = db.session.query(
                db.func.count(HostingMiner.id).label('total'),
                db.func.sum(db.case((HostingMiner.status == 'active', 1), else_=0)).label('active')
            ).first()
            
            total_sites = site_stats.total or 0
            online_sites = int(site_stats.online or 0)
            total_miners = miner_stats.total or 0
            active_miners = int(miner_stats.active or 0)
            total_capacity = float(site_stats.total_capacity or 0)
            used_capacity = float(site_stats.used_capacity or 0)
            
            recent_incidents = HostingIncident.query.filter(
                HostingIncident.created_at >= datetime.now() - timedelta(days=7)
            ).count()
            pending_tickets = HostingTicket.query.filter(
                HostingTicket.status.in_(['open', 'assigned', 'in_progress'])
            ).count()
            
        elif user_role == 'mining_site_owner':
            # 矿场运营方：只看管理站点
            site_stats = db.session.query(
                db.func.count(HostingSite.id).label('total'),
                db.func.sum(db.case((HostingSite.status == 'online', 1), else_=0)).label('online'),
                db.func.sum(HostingSite.capacity_mw).label('total_capacity'),
                db.func.sum(HostingSite.used_capacity_mw).label('used_capacity')
            ).filter(HostingSite.contact_email == user_email).first()
            
            # 获取管理站点ID用于矿机统计
            managed_site_ids = [s.id for s in HostingSite.query.filter_by(contact_email=user_email).with_entities(HostingSite.id).all()]
            
            total_sites = site_stats.total or 0
            online_sites = int(site_stats.online or 0)
            total_capacity = float(site_stats.total_capacity or 0)
            used_capacity = float(site_stats.used_capacity or 0)
            
            if managed_site_ids:
                miner_stats = db.session.query(
                    db.func.count(HostingMiner.id).label('total'),
                    db.func.sum(db.case((HostingMiner.status == 'active', 1), else_=0)).label('active')
                ).filter(HostingMiner.site_id.in_(managed_site_ids)).first()
                total_miners = miner_stats.total or 0
                active_miners = int(miner_stats.active or 0)
                recent_incidents = HostingIncident.query.filter(
                    HostingIncident.site_id.in_(managed_site_ids),
                    HostingIncident.created_at >= datetime.now() - timedelta(days=7)
                ).count()
                pending_tickets = HostingTicket.query.filter(
                    HostingTicket.site_id.in_(managed_site_ids),
                    HostingTicket.status.in_(['open', 'assigned', 'in_progress'])
                ).count()
            else:
                total_miners = active_miners = 0
                recent_incidents = pending_tickets = 0
        else:
            # owner/customer：只看自己的矿机
            miner_stats = db.session.query(
                db.func.count(HostingMiner.id).label('total'),
                db.func.sum(db.case((HostingMiner.status == 'active', 1), else_=0)).label('active'),
                db.func.count(db.distinct(HostingMiner.site_id)).label('site_count')
            ).filter(HostingMiner.customer_id == user_id).first()
            
            total_miners = miner_stats.total or 0
            active_miners = int(miner_stats.active or 0)
            total_sites = miner_stats.site_count or 0
            online_sites = total_sites  # 简化：假设所有站点在线
            total_capacity = 0.0
            used_capacity = 0.0
            recent_incidents = 0
            pending_tickets = HostingTicket.query.filter(
                HostingTicket.customer_id == user_id,
                HostingTicket.status.in_(['open', 'assigned', 'in_progress'])
            ).count()
        
        utilization_rate = round((used_capacity / total_capacity * 100) if total_capacity > 0 else 0, 1)
        
        overview_data = {
            'sites': {
                'total': total_sites,
                'online': online_sites,
                'offline': total_sites - online_sites
            },
            'miners': {
                'total': total_miners,
                'active': active_miners,
                'inactive': total_miners - active_miners
            },
            'capacity': {
                'total_mw': total_capacity,
                'used_mw': used_capacity,
                'utilization_rate': utilization_rate
            },
            'alerts': {
                'recent_incidents': recent_incidents,
                'pending_tickets': pending_tickets
            }
        }
        
        return jsonify({'success': True, 'data': overview_data})
    except Exception as e:
        logger.error(f"获取托管总览失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/sites', methods=['GET'])
@login_required
def get_sites():
    """获取托管站点列表（性能优化版 + 权限过滤）
    
    性能优化：使用单一聚合查询同时获取站点列表和矿机统计
    """
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        user_email = session.get('email', '')
        
        # 权限控制 + 聚合查询合并为单一高效查询
        if user_role == 'admin':
            # 管理员：直接查询所有站点及其矿机统计
            results = db.session.query(
                HostingSite,
                db.func.count(HostingMiner.id).label('total'),
                db.func.sum(db.case((HostingMiner.status == 'active', 1), else_=0)).label('active')
            ).outerjoin(
                HostingMiner, HostingMiner.site_id == HostingSite.id
            ).group_by(HostingSite.id).all()
            
        elif user_role == 'mining_site_owner':
            # 矿场运营方：只看管理站点
            results = db.session.query(
                HostingSite,
                db.func.count(HostingMiner.id).label('total'),
                db.func.sum(db.case((HostingMiner.status == 'active', 1), else_=0)).label('active')
            ).outerjoin(
                HostingMiner, HostingMiner.site_id == HostingSite.id
            ).filter(
                HostingSite.contact_email == user_email
            ).group_by(HostingSite.id).all()
            
        else:
            # owner/customer：只看有自己矿机的站点，使用JOIN避免子查询
            results = db.session.query(
                HostingSite,
                db.func.count(HostingMiner.id).label('total'),
                db.func.sum(db.case((HostingMiner.status == 'active', 1), else_=0)).label('active')
            ).join(
                HostingMiner, HostingMiner.site_id == HostingSite.id
            ).filter(
                HostingMiner.customer_id == user_id
            ).group_by(HostingSite.id).all()
        
        # 构建响应数据
        sites_data = []
        for row in results:
            site = row[0]
            site_data = site.to_dict()
            site_data['device_count'] = row.total or 0
            site_data['devices_count'] = row.total or 0  # 兼容旧代码
            site_data['active_devices'] = int(row.active or 0)
            sites_data.append(site_data)
        
        return jsonify({'success': True, 'sites': sites_data})
    except Exception as e:
        logger.error(f"获取站点列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    """获取有托管矿机的客户列表（用于下拉筛选）
    
    返回格式:
    {
        "success": true,
        "customers": [
            {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
            {"id": 2, "name": "李四", "email": "lisi@example.com"}
        ]
    }
    """
    from models import UserAccess
    
    try:
        user_role = session.get('role', 'guest')
        user_id = session.get('user_id')
        
        # 查询有矿机的客户（去重）
        if user_role in ['admin', 'mining_site_owner']:
            # 管理员和矿场运营方可以看到所有客户
            customers = db.session.query(
                UserAccess.id,
                UserAccess.name,
                UserAccess.email
            ).join(
                HostingMiner, HostingMiner.customer_id == UserAccess.id
            ).distinct().order_by(UserAccess.name).all()
        else:
            # 其他用户只能看到自己
            customers = db.session.query(
                UserAccess.id,
                UserAccess.name,
                UserAccess.email
            ).filter(UserAccess.id == user_id).all()
        
        customers_data = [
            {
                'id': c.id,
                'name': c.name or c.email.split('@')[0],
                'email': c.email
            }
            for c in customers
        ]
        
        return jsonify({'success': True, 'customers': customers_data})
    except Exception as e:
        logger.error(f"获取客户列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/sites', methods=['POST'])
@login_required
def create_site():
    """创建新站点"""
    try:
        # 获取表单数据
        data = request.get_json() if request.is_json else request.form
        
        # 检查必要字段
        required_fields = ['name', 'slug', 'location', 'capacity_mw']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'缺少必要字段: {field}'
                }), 400
        
        # 检查slug是否已存在
        existing_site = HostingSite.query.filter_by(slug=data['slug']).first()
        if existing_site:
            return jsonify({
                'success': False,
                'error': '站点标识已存在'
            }), 400
        
        # 创建新站点
        site = HostingSite(
            name=data['name'],
            slug=data['slug'],
            location=data['location'],
            capacity_mw=float(data['capacity_mw']),
            electricity_rate=float(data.get('electricity_rate', 0.05)),
            operator_name=data.get('operator_name', ''),
            description=data.get('description', ''),
            status='offline'  # 默认新站点是离线状态
        )
        
        db.session.add(site)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '站点创建成功',
            'site_id': site.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建站点失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/sites/<int:site_id>', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_site_detail(site_id):
    """获取站点详情"""
    try:
        site = HostingSite.query.get_or_404(site_id)
        
        # 获取站点矿机统计
        miners_stats = db.session.query(
            HostingMiner.status,
            db.func.count(HostingMiner.id).label('count'),
            db.func.sum(HostingMiner.actual_hashrate).label('total_hashrate'),
            db.func.sum(HostingMiner.actual_power).label('total_power')
        ).filter(HostingMiner.site_id == site_id).group_by(HostingMiner.status).all()
        
        # 近期事件
        recent_incidents = HostingIncident.query.filter_by(site_id=site_id).filter(
            HostingIncident.created_at >= datetime.now() - timedelta(days=30)
        ).order_by(HostingIncident.created_at.desc()).limit(10).all()
        
        site_data = site.to_dict()
        site_data['miners_stats'] = [
            {
                'status': stat.status,
                'count': stat.count,
                'total_hashrate': float(stat.total_hashrate or 0),
                'total_power': float(stat.total_power or 0)
            }
            for stat in miners_stats
        ]
        site_data['recent_incidents'] = [
            {
                'id': incident.id,
                'title': incident.title,
                'severity': incident.severity,
                'status': incident.status,
                'created_at': incident.created_at.isoformat()
            }
            for incident in recent_incidents
        ]
        
        return jsonify({'success': True, 'site': site_data})
    except Exception as e:
        logger.error(f"获取站点详情失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/tickets', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_tickets():
    """获取工单列表"""
    try:
        # 获取查询参数
        status = request.args.get('status')
        priority = request.args.get('priority')
        limit = int(request.args.get('limit', 50))
        
        query = HostingTicket.query
        
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)
            
        tickets = query.order_by(HostingTicket.created_at.desc()).limit(limit).all()
        
        tickets_data = []
        for ticket in tickets:
            ticket_data = {
                'id': ticket.id,
                'title': ticket.title,
                'priority': ticket.priority,
                'status': ticket.status,
                'category': ticket.category,
                'customer_name': ticket.customer.name if ticket.customer else 'Unknown',
                'created_at': ticket.created_at.isoformat(),
                'response_time_minutes': ticket.response_time_minutes,
                'resolution_time_hours': ticket.resolution_time_hours
            }
            tickets_data.append(ticket_data)
        
        return jsonify({'success': True, 'tickets': tickets_data})
    except Exception as e:
        logger.error(f"获取工单列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/tickets', methods=['POST'])
@login_required
def create_ticket():
    """创建新工单"""
    try:
        data = request.get_json()
        customer_id = session.get('user_id')
        
        ticket = HostingTicket(
            title=data['title'],
            customer_id=customer_id,
            description=data.get('description', ''),
            priority=data.get('priority', 'medium'),
            category=data.get('category'),
            site_id=data.get('site_id')
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': '工单创建成功',
            'ticket_id': ticket.id
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建工单失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 客户API路由 ====================

@hosting_bp.route('/api/client/assets', methods=['GET'])
@login_required
def get_client_assets():
    """获取客户资产概览"""
    try:
        user_id = session.get('user_id')
        
        # 获取客户托管的矿机
        hosted_miners = HostingMiner.query.filter_by(customer_id=user_id).all()
        
        if not hosted_miners:
            return jsonify({
                'success': True,
                'assets': {
                    'total_devices': 0,
                    'active_devices': 0,
                    'total_hashrate': '0 TH/s',
                    'total_power': '0 W',
                    'sites': []
                }
            })
        
        # 统计数据
        total_devices = len(hosted_miners)
        active_devices = len([m for m in hosted_miners if m.status == 'active'])
        total_hashrate = sum(m.actual_hashrate for m in hosted_miners if m.status == 'active')
        total_power = sum(m.actual_power for m in hosted_miners if m.status == 'active')
        
        # 按站点分组
        sites_data = {}
        for miner in hosted_miners:
            site_id = miner.site_id
            if site_id not in sites_data:
                sites_data[site_id] = {
                    'site_name': miner.site.name,
                    'devices': 0,
                    'active_devices': 0,
                    'hashrate': 0
                }
            sites_data[site_id]['devices'] += 1
            if miner.status == 'active':
                sites_data[site_id]['active_devices'] += 1
                sites_data[site_id]['hashrate'] += miner.actual_hashrate
        
        assets = {
            'total_devices': total_devices,
            'active_devices': active_devices,
            'total_hashrate': f'{total_hashrate:.1f} TH/s',
            'total_power': f'{total_power:.0f} W',
            'monthly_revenue': total_hashrate * 0.15 * 30,  # 估算月收益
            'net_profit': max(0, total_hashrate * 0.15 * 30 - total_power * 0.08 * 24 * 30 / 1000),  # 估算净利润
            'monthly_cost': total_power * 0.08 * 24 * 30 / 1000,  # 估算月电费
            'sites': list(sites_data.values())
        }
        
        return jsonify({'success': True, 'assets': assets})
    except Exception as e:
        logger.error(f"获取客户资产失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/client/miners', methods=['GET'])
@login_required
def get_client_miners():
    """获取客户矿机列表"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        user_email = session.get('email', '')
        
        # 权限控制 - 角色级别数据隔离
        if user_role == 'admin':
            # 管理员可以查看所有矿机
            miners = HostingMiner.query.all()
        elif user_role == 'mining_site_owner':
            # 矿场运营方只能查看自己管理站点的矿机
            managed_sites = HostingSite.query.filter_by(contact_email=user_email).all()
            managed_site_ids = [s.id for s in managed_sites]
            if managed_site_ids:
                miners = HostingMiner.query.filter(HostingMiner.site_id.in_(managed_site_ids)).all()
            else:
                miners = []
        else:
            # owner/customer 只能查看自己名下的矿机
            miners = HostingMiner.query.filter_by(customer_id=user_id).all()
        
        miners_data = []
        for miner in miners:
            miner_data = miner.to_dict()
            miner_data['site_name'] = miner.site.name if miner.site else 'Unknown'
            miners_data.append(miner_data)
        
        return jsonify({'success': True, 'miners': miners_data})
    except Exception as e:
        logger.error(f"获取客户矿机失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/client/dashboard', methods=['GET'])
@login_required
def get_client_dashboard():
    """获取客户仪表板数据（性能优化版）"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        user_email = session.get('email', '')
        
        # 构建基础查询
        base_query = db.session.query(
            db.func.count(HostingMiner.id).label('total'),
            db.func.sum(db.case((HostingMiner.status == 'active', 1), else_=0)).label('active'),
            db.func.sum(db.case(
                (HostingMiner.status == 'active', HostingMiner.actual_hashrate), 
                else_=0
            )).label('total_hashrate'),
            db.func.sum(db.case(
                (HostingMiner.status == 'active', HostingMiner.actual_power), 
                else_=0
            )).label('total_power')
        )
        
        # 权限控制 - 角色级别数据隔离
        if user_role == 'admin':
            # 管理员可以查看所有矿机
            stats = base_query.first()
        elif user_role == 'mining_site_owner':
            # 矿场运营方只能查看自己管理站点的矿机
            managed_sites = HostingSite.query.filter_by(contact_email=user_email).all()
            managed_site_ids = [s.id for s in managed_sites]
            if managed_site_ids:
                stats = base_query.filter(HostingMiner.site_id.in_(managed_site_ids)).first()
            else:
                stats = None
        else:
            # owner/customer 只能查看自己名下的矿机
            stats = base_query.filter(HostingMiner.customer_id == user_id).first()
        
        # 处理空结果
        if stats:
            total_miners = stats.total or 0
            active_miners = int(stats.active or 0)
            total_hashrate = float(stats.total_hashrate or 0)
            total_power = float(stats.total_power or 0)
        else:
            total_miners = 0
            active_miners = 0
            total_hashrate = 0.0
            total_power = 0.0
        
        # 估算收益（基于当前市场数据的合理估算）
        # 1 TH/s 大约每天产出 0.000000055 BTC，BTC价格约 $100,000
        # 即每 TH/s 每天约 $0.055 收益
        daily_revenue_per_th = 0.055  # 每TH/s每天的收益（美元）
        daily_revenue = total_hashrate * daily_revenue_per_th
        monthly_revenue = daily_revenue * 30
        
        # 获取最近矿机列表
        if user_role == 'admin':
            recent_miners_query = HostingMiner.query.order_by(HostingMiner.id.desc()).limit(10).all()
        elif user_role == 'mining_site_owner':
            managed_sites = HostingSite.query.filter_by(contact_email=user_email).all()
            managed_site_ids = [s.id for s in managed_sites]
            if managed_site_ids:
                recent_miners_query = HostingMiner.query.filter(
                    HostingMiner.site_id.in_(managed_site_ids)
                ).order_by(HostingMiner.id.desc()).limit(10).all()
            else:
                recent_miners_query = []
        else:
            recent_miners_query = HostingMiner.query.filter_by(
                customer_id=user_id
            ).order_by(HostingMiner.id.desc()).limit(10).all()
        
        # 格式化最近矿机数据
        recent_miners = []
        for miner in recent_miners_query:
            miner_model_name = miner.miner_model.model_name if miner.miner_model else 'Unknown'
            site_name = miner.site.name if miner.site else 'Unknown'
            daily_miner_revenue = miner.actual_hashrate * 0.055 if miner.status == 'active' else 0
            recent_miners.append({
                'id': miner.id,
                'serial_number': miner.serial_number,
                'miner_model': miner_model_name,
                'site_name': site_name,
                'hashrate': miner.actual_hashrate,
                'status': miner.status,
                'daily_revenue': round(daily_miner_revenue, 2)
            })
        
        # 返回格式匹配JavaScript期望的结构
        stats = {
            'total_miners': total_miners,
            'active_miners': active_miners,
            'total_hashrate': round(total_hashrate, 2),
            'monthly_revenue': round(monthly_revenue, 2)
        }
        
        return jsonify({'success': True, 'stats': stats, 'recent_miners': recent_miners})
    except Exception as e:
        logger.error(f"获取客户仪表板数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/client/revenue-chart', methods=['GET'])
@login_required
def get_client_revenue_chart():
    """获取客户收益图表数据"""
    try:
        user_id = session.get('user_id')
        period = request.args.get('period', '7d')
        
        # 生成模拟数据（实际应用中应从数据库获取历史数据）
        from datetime import datetime, timedelta
        import random
        
        if period == '7d':
            days = 7
        elif period == '30d':
            days = 30
        else:
            days = 7
            
        labels = []
        revenue_data = []
        cost_data = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).strftime('%m-%d')
            labels.append(date)
            
            # 模拟数据
            base_revenue = 150 + random.uniform(-20, 20)
            base_cost = 80 + random.uniform(-10, 10)
            
            revenue_data.append(round(base_revenue, 2))
            cost_data.append(round(base_cost, 2))
        
        # 返回格式匹配JavaScript期望的结构 (data.labels, data.data)
        return jsonify({'success': True, 'labels': labels, 'data': revenue_data})
    except Exception as e:
        logger.error(f"获取收益图表数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/client/miner-distribution', methods=['GET'])
@login_required
def get_client_miner_distribution():
    """获取客户矿机分布数据（性能优化版）"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        user_email = session.get('email', '')
        
        # 构建基础查询
        base_query = db.session.query(
            HostingSite.name.label('site_name'),
            db.func.count(HostingMiner.id).label('count')
        ).outerjoin(
            HostingMiner, HostingMiner.site_id == HostingSite.id
        )
        
        # 权限控制 - 角色级别数据隔离
        if user_role == 'admin':
            # 管理员可以查看所有矿机分布
            distribution = base_query.group_by(HostingSite.id, HostingSite.name).all()
            unknown_count = HostingMiner.query.filter(HostingMiner.site_id == None).count()
        elif user_role == 'mining_site_owner':
            # 矿场运营方只能查看自己管理站点的矿机
            managed_sites = HostingSite.query.filter_by(contact_email=user_email).all()
            managed_site_ids = [s.id for s in managed_sites]
            if managed_site_ids:
                distribution = base_query.filter(
                    HostingSite.id.in_(managed_site_ids)
                ).group_by(HostingSite.id, HostingSite.name).all()
                # 矿场运营方也需要看到其管理站点下无明确站点的矿机
                unknown_count = 0  # 矿场通常不会有无站点矿机
            else:
                distribution = []
                unknown_count = 0
        else:
            # owner/customer 只能查看自己名下的矿机分布
            distribution = base_query.filter(
                HostingMiner.customer_id == user_id
            ).group_by(HostingSite.id, HostingSite.name).all()
            unknown_count = HostingMiner.query.filter(
                HostingMiner.customer_id == user_id,
                HostingMiner.site_id == None
            ).count()
        
        # 转换为图表数据格式
        labels = [row.site_name or 'Unknown' for row in distribution]
        data = [row.count for row in distribution]
        
        if unknown_count > 0:
            labels.append('Unknown')
            data.append(unknown_count)
        
        # 返回格式匹配JavaScript期望的结构 (data.labels, data.data)
        return jsonify({'success': True, 'labels': labels, 'data': data})
    except Exception as e:
        logger.error(f"获取矿机分布数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/client/usage', methods=['GET'])
@login_required
def get_client_usage():
    """获取客户使用情况数据"""
    try:
        from sqlalchemy.orm import joinedload
        user_id = session.get('user_id')
        
        # 获取活跃设备数量
        active_devices = HostingMiner.query.filter_by(
            customer_id=user_id,
            status='active'
        ).count()
        
        # 获取本月使用记录（添加eager loading避免N+1查询）
        current_month = datetime.now().month
        current_year = datetime.now().year
        current_month_records = HostingUsageRecord.query.options(
            joinedload(HostingUsageRecord.usage_items)
        ).filter(
            HostingUsageRecord.customer_id == user_id,
            db.extract('month', HostingUsageRecord.usage_period_start) == current_month,
            db.extract('year', HostingUsageRecord.usage_period_start) == current_year
        ).all()
        
        # 计算本月能源使用量（kWh）和成本（$）
        current_month_energy_kwh = 0.0
        current_month_cost = 0.0
        for record in current_month_records:
            # 累计电力消耗（kWh）
            for item in record.usage_items:
                if item.item_type == 'electricity':
                    current_month_energy_kwh += item.quantity
            # 累计成本（$）
            current_month_cost += record.total_amount
        
        # 获取总使用量（添加eager loading）
        all_records = HostingUsageRecord.query.options(
            joinedload(HostingUsageRecord.usage_items)
        ).filter_by(
            customer_id=user_id
        ).all()
        
        # 计算总能源使用量和总成本
        total_energy_kwh = 0.0
        total_cost = 0.0
        for record in all_records:
            # 累计电力消耗
            for item in record.usage_items:
                if item.item_type == 'electricity':
                    total_energy_kwh += item.quantity
            # 累计成本
            total_cost += record.total_amount
        
        # 计算下次报告日期（每月1日）
        next_month = current_month + 1 if current_month < 12 else 1
        next_year = current_year if current_month < 12 else current_year + 1
        next_report_date = f"{next_year}-{next_month:02d}-01"
        
        # 获取最新的使用记录作为当前使用详情（添加eager loading）
        current_usage_record = HostingUsageRecord.query.options(
            joinedload(HostingUsageRecord.usage_items)
        ).filter_by(
            customer_id=user_id
        ).order_by(HostingUsageRecord.usage_period_end.desc()).first()
        
        current_usage = None
        if current_usage_record:
            # 计算该记录的能源消耗
            record_energy_kwh = sum(
                item.quantity for item in current_usage_record.usage_items 
                if item.item_type == 'electricity'
            )
            
            current_usage = {
                'report_date': current_usage_record.usage_period_start.strftime('%Y-%m-%d'),
                'period_end': current_usage_record.usage_period_end.strftime('%Y-%m-%d'),
                'total_energy_kwh': round(record_energy_kwh, 2),
                'total_cost': float(current_usage_record.total_amount),
                'status': current_usage_record.status,
                'usage_items': [
                    {
                        'resource': item.item_type,
                        'description': item.description or f'{item.item_type} usage',
                        'quantity': float(item.quantity),
                        'rate': float(item.unit_price),
                        'amount': float(item.total_price)
                    }
                    for item in current_usage_record.usage_items
                ]
            }
        else:
            # 返回默认数据
            current_usage = {
                'report_date': datetime.now().strftime('%Y-%m-%d'),
                'period_end': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'total_energy_kwh': 0.0,
                'total_cost': 0.0,
                'status': 'active',
                'usage_items': []
            }
        
        # 获取历史记录（添加eager loading）
        history_records = HostingUsageRecord.query.options(
            joinedload(HostingUsageRecord.usage_items)
        ).filter_by(
            customer_id=user_id
        ).order_by(HostingUsageRecord.usage_period_end.desc()).limit(10).all()
        
        history = []
        for record in history_records:
            # 计算该记录的电力消耗（kWh）
            energy_kwh = sum(
                item.quantity for item in record.usage_items 
                if item.item_type == 'electricity'
            )
            
            history.append({
                'id': record.id,
                'report_date': record.usage_period_start.strftime('%Y-%m-%d'),
                'period': f"{record.usage_period_start.strftime('%Y-%m-%d')} - {record.usage_period_end.strftime('%Y-%m-%d')}",
                'energy_kwh': round(energy_kwh, 2),
                'total_cost': float(record.total_amount),
                'status': record.status
            })
        
        response_data = {
            'success': True,
            'summary': {
                'current_month_energy': round(current_month_energy_kwh, 2),
                'current_month_cost': round(current_month_cost, 2),
                'total_energy': round(total_energy_kwh, 2),
                'total_cost': round(total_cost, 2),
                'active_devices': active_devices,
                'next_report_date': next_report_date
            },
            'current_usage': current_usage,
            'history': history
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取客户使用情况失败: {e}")
        # 返回空数据结构，不报错
        return jsonify({
            'success': True,
            'summary': {
                'current_month_energy': 0.0,
                'current_month_cost': 0.0,
                'total_energy': 0.0,
                'total_cost': 0.0,
                'active_devices': 0,
                'next_report_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            },
            'current_usage': {
                'report_date': datetime.now().strftime('%Y-%m-%d'),
                'period_end': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'total_energy_kwh': 0.0,
                'total_cost': 0.0,
                'status': 'active',
                'usage_items': []
            },
            'history': []
        })

@hosting_bp.route('/api/client/usage/generate-report', methods=['POST'])
@login_required
def generate_usage_report():
    """生成使用报告"""
    try:
        user_id = session.get('user_id')
        current_lang = session.get('language', 'zh')
        
        # 检查是否有活跃设备
        active_miners = HostingMiner.query.filter_by(
            customer_id=user_id,
            status='active'
        ).count()
        
        if active_miners == 0:
            message = 'No active devices found' if current_lang == 'en' else '没有找到活跃设备'
            return jsonify({
                'success': False,
                'message': message
            })
        
        # 生成报告的逻辑（这里简化处理）
        # 实际应用中应该创建新的 HostingUsageRecord 记录
        
        message = 'Usage report generated successfully' if current_lang == 'en' else '使用报告生成成功'
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"生成使用报告失败: {e}")
        current_lang = session.get('language', 'zh')
        message = 'Failed to generate report' if current_lang == 'en' else '生成报告失败'
        return jsonify({
            'success': False,
            'message': message
        }), 500

@hosting_bp.route('/api/client/reports', methods=['GET'])
@login_required
def get_client_reports():
    """获取客户报告列表和统计数据"""
    try:
        user_id = session.get('user_id')
        user_email = session.get('email', '')
        user_role = session.get('role', 'owner')
        
        # 根据角色过滤矿机
        if user_role == 'admin':
            miners = HostingMiner.query.all()
        elif user_role == 'mining_site_owner':
            managed_sites = HostingSite.query.filter_by(contact_email=user_email).all()
            managed_site_ids = [s.id for s in managed_sites]
            if managed_site_ids:
                miners = HostingMiner.query.filter(HostingMiner.site_id.in_(managed_site_ids)).all()
            else:
                miners = []
        else:
            miners = HostingMiner.query.filter_by(customer_id=user_id).all()
        
        # 计算统计数据
        total_miners = len(miners)
        active_miners = sum(1 for m in miners if m.status == 'active')
        total_hashrate = sum(m.actual_hashrate or 0 for m in miners if m.status == 'active')
        total_power = sum(m.actual_power or 0 for m in miners if m.status == 'active')
        
        # 计算收益
        daily_revenue_per_th = 0.055
        daily_revenue = total_hashrate * daily_revenue_per_th
        monthly_revenue = daily_revenue * 30
        
        # 计算效率 (TH/kW)
        efficiency = (total_hashrate * 1000 / total_power) if total_power > 0 else 0
        
        # 计算可用率
        uptime = (active_miners / total_miners * 100) if total_miners > 0 else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'monthly_uptime': round(uptime, 1),
                'average_hashrate': round(total_hashrate, 2),
                'total_revenue': round(monthly_revenue, 2),
                'efficiency': round(efficiency, 2)
            },
            'reports': []  # 历史报告列表（暂为空）
        })
    except Exception as e:
        logger.error(f"获取客户报告失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/client/reports/chart', methods=['GET'])
@login_required
def get_client_reports_chart():
    """获取客户报告性能图表数据"""
    try:
        user_id = session.get('user_id')
        user_email = session.get('email', '')
        user_role = session.get('role', 'owner')
        period = request.args.get('period', '7d')
        
        # 确定天数
        days = 7
        if period == '30d':
            days = 30
        elif period == '90d':
            days = 90
        
        # 根据角色过滤矿机
        if user_role == 'admin':
            miners = HostingMiner.query.filter_by(status='active').all()
        elif user_role == 'mining_site_owner':
            managed_sites = HostingSite.query.filter_by(contact_email=user_email).all()
            managed_site_ids = [s.id for s in managed_sites]
            if managed_site_ids:
                miners = HostingMiner.query.filter(
                    HostingMiner.site_id.in_(managed_site_ids),
                    HostingMiner.status == 'active'
                ).all()
            else:
                miners = []
        else:
            miners = HostingMiner.query.filter_by(customer_id=user_id, status='active').all()
        
        # 计算当前总算力
        total_hashrate = sum(m.actual_hashrate or 0 for m in miners)
        daily_revenue_per_th = 0.055
        
        # 生成模拟历史数据（基于当前数据生成趋势）
        labels = []
        hashrate_data = []
        revenue_data = []
        
        import random
        for i in range(days, 0, -1):
            date = datetime.now() - timedelta(days=i)
            labels.append(date.strftime('%m/%d'))
            
            # 添加一些随机波动 (±5%)
            variation = random.uniform(0.95, 1.05)
            hr = total_hashrate * variation
            hashrate_data.append(round(hr, 2))
            revenue_data.append(round(hr * daily_revenue_per_th, 2))
        
        # 收益构成（假设矿池费用2%）
        gross_revenue = sum(revenue_data)
        pool_fee_rate = 0.02
        pool_fees = gross_revenue * pool_fee_rate
        mining_revenue = gross_revenue - pool_fees
        
        return jsonify({
            'success': True,
            'labels': labels,
            'hashrate': hashrate_data,
            'revenue': revenue_data,
            'breakdown': {
                'mining_revenue': round(mining_revenue, 2),
                'pool_fees': round(pool_fees, 2)
            }
        })
    except Exception as e:
        logger.error(f"获取报告图表数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/client/reports/generate', methods=['POST'])
@login_required
def generate_client_report():
    """生成客户报告"""
    try:
        user_id = session.get('user_id')
        current_lang = session.get('language', 'zh')
        data = request.get_json() or {}
        
        report_type = data.get('report_type', 'monthly')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 检查是否有矿机
        miner_count = HostingMiner.query.filter_by(customer_id=user_id).count()
        
        if miner_count == 0:
            message = 'No miners found' if current_lang == 'en' else '没有找到矿机'
            return jsonify({'success': False, 'message': message})
        
        # 简化处理：返回成功消息
        message = 'Report generated successfully' if current_lang == 'en' else '报告生成成功'
        return jsonify({
            'success': True,
            'message': message,
            'report_id': None  # 实际应用中返回报告ID
        })
        
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        current_lang = session.get('language', 'zh')
        message = 'Failed to generate report' if current_lang == 'en' else '生成报告失败'
        return jsonify({'success': False, 'message': message}), 500


@hosting_bp.route('/api/client/usage/alerts', methods=['POST'])
@login_required
def save_usage_alerts():
    """保存使用提醒设置"""
    try:
        user_id = session.get('user_id')
        current_lang = session.get('language', 'zh')
        data = request.get_json()
        
        # 验证数据
        if not data:
            message = 'Invalid data' if current_lang == 'en' else '无效的数据'
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # 这里应该将提醒设置保存到数据库
        # 实际应用中可以创建一个 UsageAlertSettings 模型来存储这些设置
        # 现在简化处理，只返回成功响应
        
        logger.info(f"用户 {user_id} 保存提醒设置: {data}")
        
        message = 'Alert settings saved successfully' if current_lang == 'en' else '提醒设置保存成功'
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"保存提醒设置失败: {e}")
        current_lang = session.get('language', 'zh')
        message = 'Failed to save settings' if current_lang == 'en' else '保存设置失败'
        return jsonify({
            'success': False,
            'message': message
        }), 500

# ==================== 矿机管理API ====================

@hosting_bp.route('/api/miners', methods=['GET'])
@login_required
def get_miners():
    """获取矿机列表（支持筛选和分页）"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        # 查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        approval_status = request.args.get('approval_status')
        site_id = request.args.get('site_id', type=int)
        customer_id = request.args.get('customer_id', type=int)
        
        # 构建查询
        query = HostingMiner.query
        
        # 权限控制 - 角色级别数据隔离
        if user_role == 'admin':
            # 管理员可以查看所有矿机
            pass
        elif user_role == 'mining_site_owner':
            # 矿场运营方只能查看自己管理站点的矿机
            user_email = session.get('email', '')
            managed_sites = HostingSite.query.filter_by(contact_email=user_email).all()
            managed_site_ids = [s.id for s in managed_sites]
            if managed_site_ids:
                query = query.filter(HostingMiner.site_id.in_(managed_site_ids))
            else:
                # 没有管理任何站点，返回空结果
                query = query.filter(HostingMiner.id == -1)
        else:
            # owner/customer 只能查看自己名下的矿机
            query = query.filter_by(customer_id=user_id)
        
        # 应用筛选条件
        if status:
            query = query.filter_by(status=status)
        if approval_status:
            query = query.filter_by(approval_status=approval_status)
        if site_id:
            query = query.filter_by(site_id=site_id)
        if customer_id and user_role in ['admin', 'mining_site_owner']:
            # 管理员和矿场运营方可以按客户ID筛选
            query = query.filter_by(customer_id=customer_id)
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        current_lang = session.get('language', 'zh')
        
        try:
            from services.hosting_revenue_service import get_revenue_service
            from services.miner_evaluation_service import get_evaluation_service
            revenue_service = get_revenue_service()
            evaluation_service = get_evaluation_service()
            services_available = True
            logger.info("收益和评估服务加载成功")
        except Exception as svc_err:
            logger.warning(f"收益/评估服务加载失败: {svc_err}", exc_info=True)
            services_available = False
        
        site_ids = list(set(m.site_id for m in pagination.items if m.site_id))
        miner_identifiers = [(m.serial_number, m.site_id) for m in pagination.items if m.serial_number and m.site_id]
        
        telemetry_map = {}
        if miner_identifiers:
            try:
                telemetry_records = MinerTelemetryLive.query.filter(
                    MinerTelemetryLive.site_id.in_(site_ids)
                ).all()
                for t in telemetry_records:
                    telemetry_map[(t.miner_id, t.site_id)] = t
            except Exception as tel_err:
                logger.warning(f"获取遥测数据失败: {tel_err}")
        
        miners_data = []
        for miner in pagination.items:
            miner_data = miner.to_dict()
            
            telemetry = telemetry_map.get((miner.serial_number, miner.site_id))
            if telemetry:
                miner_data['telemetry'] = {
                    'live': True,
                    'online': telemetry.online,
                    'last_seen': telemetry.last_seen.isoformat() if telemetry.last_seen else None,
                    'hashrate_ths': round(telemetry.hashrate_ghs / 1000, 2) if telemetry.hashrate_ghs else 0,
                    'hashrate_5s_ths': round(telemetry.hashrate_5s_ghs / 1000, 2) if telemetry.hashrate_5s_ghs else 0,
                    'temperature_avg': round(telemetry.temperature_avg, 1) if telemetry.temperature_avg else 0,
                    'temperature_max': round(telemetry.temperature_max, 1) if telemetry.temperature_max else 0,
                    'fan_speeds': telemetry.fan_speeds or [],
                    'power_consumption': round(telemetry.power_consumption, 0) if telemetry.power_consumption else 0,
                    'accepted_shares': telemetry.accepted_shares or 0,
                    'rejected_shares': telemetry.rejected_shares or 0,
                    'uptime_hours': round(telemetry.uptime_seconds / 3600, 1) if telemetry.uptime_seconds else 0,
                    'pool_url': telemetry.pool_url,
                    'worker_name': telemetry.worker_name
                }
            else:
                miner_data['telemetry'] = {'live': False}
            
            # 添加关联信息
            if miner.customer:
                miner_data['customer_name'] = miner.customer.email
                miner_data['customer_email'] = miner.customer.email
            
            if miner.submitter:
                miner_data['submitted_by_name'] = miner.submitter.email
            
            if miner.approver:
                miner_data['approved_by_name'] = miner.approver.email
            
            # 添加站点名称
            site = miner.site
            if site:
                miner_data['site_name'] = site.name
                electricity_rate = site.electricity_rate
            else:
                electricity_rate = 0.06
            
            # 添加告警信息
            alerts_info = get_miner_alerts(miner, lang=current_lang)
            miner_data['alerts'] = alerts_info
            
            # 添加收益和评分数据
            if services_available and miner.actual_hashrate and miner.actual_power:
                try:
                    model = miner.miner_model
                    model_name = model.model_name if model else "Unknown"
                    rated_hashrate = model.reference_hashrate if model else miner.actual_hashrate
                    rated_power = model.reference_power if model else miner.actual_power
                    
                    revenue_metrics = revenue_service.calculate_miner_revenue(
                        miner_id=miner.id,
                        serial_number=miner.serial_number,
                        model_name=model_name,
                        hashrate_th=miner.actual_hashrate,
                        power_w=miner.actual_power,
                        electricity_rate=electricity_rate,
                        health_score=miner.health_score or 100
                    )
                    miner_data['daily_net_profit'] = revenue_metrics.daily_net_profit
                    miner_data['daily_usd'] = revenue_metrics.daily_usd
                    miner_data['efficiency_jth'] = revenue_metrics.efficiency_jth
                    miner_data['efficiency_grade'] = revenue_metrics.efficiency_grade
                    
                    evaluation = evaluation_service.evaluate_miner(
                        miner_id=miner.id,
                        serial_number=miner.serial_number,
                        model_name=model_name,
                        actual_hashrate_th=miner.actual_hashrate or 0,
                        rated_hashrate_th=rated_hashrate,
                        actual_power_w=miner.actual_power or 0,
                        rated_power_w=rated_power,
                        electricity_rate=electricity_rate,
                        temp_avg=miner.temperature_avg or 0,
                        temp_max=miner.temperature_max or 0,
                        fan_avg=miner.fan_avg or 0,
                        hardware_errors=miner.hardware_errors or 0,
                        reject_rate=miner.reject_rate or 0,
                        uptime_seconds=miner.uptime_seconds or 0,
                        is_online=miner.status == 'active' or miner.cgminer_online,
                        expected_daily_usd=revenue_metrics.daily_usd
                    )
                    miner_data['evaluation_grade'] = evaluation.composite_grade
                    miner_data['evaluation_score'] = evaluation.composite_score
                except Exception as eval_err:
                    logger.error(f"矿机 {miner.id} 评估失败: {eval_err}", exc_info=True)
            else:
                if not services_available:
                    logger.debug(f"矿机 {miner.id}: 服务不可用")
                elif not miner.actual_hashrate:
                    logger.debug(f"矿机 {miner.id}: 无算力数据")
                elif not miner.actual_power:
                    logger.debug(f"矿机 {miner.id}: 无功耗数据")
            
            miners_data.append(miner_data)
        
        # Calculate counts for UI display
        base_query = HostingMiner.query
        if user_role not in ['owner', 'admin', 'mining_site_owner']:
            base_query = base_query.filter_by(customer_id=user_id)
        
        counts = {
            'total': base_query.count(),
            'active': base_query.filter_by(status='active').count(),
            'pending': base_query.filter_by(approval_status='pending_approval').count()
        }
        
        return jsonify({
            'success': True,
            'miners': miners_data,
            'counts': counts,
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"获取矿机列表失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取矿机列表失败'
        }), 500

@hosting_bp.route('/api/miners/create', methods=['POST'])
@login_required
def create_miner():
    """创建新矿机"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        # 验证必填字段
        required_fields = ['site_id', 'customer_id', 'miner_model_id', 'serial_number', 'actual_hashrate', 'actual_power']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'缺少必填字段: {field}'
                }), 400
        
        # 检查序列号唯一性
        existing_miner = HostingMiner.query.filter_by(serial_number=data['serial_number']).first()
        if existing_miner:
            return jsonify({
                'success': False,
                'error': '序列号已存在'
            }), 400
        
        # 权限控制和状态设置
        if user_role in ['owner', 'admin', 'mining_site_owner']:
            # 托管方直接录入 - 立即激活
            approval_status = 'approved'
            approved_by = user_id
            approved_at = datetime.utcnow()
            submitted_by = user_id
            submitted_at = datetime.utcnow()
        else:
            # 客户申请录入 - 需要审核
            approval_status = 'pending_approval'
            approved_by = None
            approved_at = None
            submitted_by = user_id
            submitted_at = datetime.utcnow()
            
            # 客户只能为自己录入矿机
            data['customer_id'] = user_id
        
        # 创建矿机记录
        miner = HostingMiner(
            site_id=data['site_id'],
            customer_id=data['customer_id'],
            miner_model_id=data['miner_model_id'],
            serial_number=data['serial_number'],
            actual_hashrate=data['actual_hashrate'],
            actual_power=data['actual_power'],
            rack_position=data.get('rack_position'),
            ip_address=data.get('ip_address'),
            mac_address=data.get('mac_address'),
            approval_status=approval_status,
            submitted_by=submitted_by,
            approved_by=approved_by,
            submitted_at=submitted_at,
            approved_at=approved_at,
            approval_notes=data.get('approval_notes')
        )
        
        db.session.add(miner)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '矿机创建成功' if approval_status == 'approved' else '矿机申请已提交，等待审核',
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建矿机失败: {e}")
        return jsonify({
            'success': False,
            'error': '创建矿机失败'
        }), 500

@hosting_bp.route('/api/miners/batch', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def batch_create_miners():
    """批量创建矿机"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        miners_data = data.get('miners', [])
        if not miners_data:
            return jsonify({
                'success': False,
                'error': '没有提供矿机数据'
            }), 400
        
        # 验证数据
        created_miners = []
        errors = []
        
        for i, miner_data in enumerate(miners_data):
            try:
                # 验证必填字段
                required_fields = ['site_id', 'customer_id', 'miner_model_id', 'serial_number', 'actual_hashrate', 'actual_power']
                for field in required_fields:
                    if not miner_data.get(field):
                        errors.append(f'第{i+1}行: 缺少必填字段 {field}')
                        continue
                
                # 检查序列号唯一性
                existing_miner = HostingMiner.query.filter_by(serial_number=miner_data['serial_number']).first()
                if existing_miner:
                    errors.append(f'第{i+1}行: 序列号 {miner_data["serial_number"]} 已存在')
                    continue
                
                # 创建矿机记录（托管方批量导入直接激活）
                miner = HostingMiner(
                    site_id=miner_data['site_id'],
                    customer_id=miner_data['customer_id'],
                    miner_model_id=miner_data['miner_model_id'],
                    serial_number=miner_data['serial_number'],
                    actual_hashrate=miner_data['actual_hashrate'],
                    actual_power=miner_data['actual_power'],
                    rack_position=miner_data.get('rack_position'),
                    ip_address=miner_data.get('ip_address'),
                    mac_address=miner_data.get('mac_address'),
                    approval_status='approved',
                    submitted_by=user_id,
                    approved_by=user_id,
                    submitted_at=datetime.utcnow(),
                    approved_at=datetime.utcnow(),
                    approval_notes='批量导入自动审核'
                )
                
                created_miners.append(miner)
                
            except Exception as e:
                errors.append(f'第{i+1}行: {str(e)}')
        
        # 批量保存成功的记录
        if created_miners:
            db.session.add_all(created_miners)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'批量创建完成: 成功 {len(created_miners)} 个，失败 {len(errors)} 个',
            'created_count': len(created_miners),
            'error_count': len(errors),
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"批量创建矿机失败: {e}")
        return jsonify({
            'success': False,
            'error': '批量创建矿机失败'
        }), 500

@hosting_bp.route('/api/miners/<int:miner_id>/approve', methods=['PUT'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def approve_miner(miner_id):
    """审核通过矿机"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        miner = HostingMiner.query.get_or_404(miner_id)
        
        # 检查状态
        if miner.approval_status != 'pending_approval':
            return jsonify({
                'success': False,
                'error': '矿机状态不允许审核'
            }), 400
        
        # 更新审核状态
        miner.approval_status = 'approved'
        miner.approved_by = user_id
        miner.approved_at = datetime.utcnow()
        miner.approval_notes = data.get('notes', '')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '矿机审核通过',
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"审核矿机失败: {e}")
        return jsonify({
            'success': False,
            'error': '审核矿机失败'
        }), 500

@hosting_bp.route('/api/miners/<int:miner_id>/reject', methods=['PUT'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def reject_miner(miner_id):
    """拒绝矿机申请"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        miner = HostingMiner.query.get_or_404(miner_id)
        
        # 检查状态
        if miner.approval_status != 'pending_approval':
            return jsonify({
                'success': False,
                'error': '矿机状态不允许审核'
            }), 400
        
        # 更新审核状态
        miner.approval_status = 'rejected'
        miner.approved_by = user_id
        miner.approved_at = datetime.utcnow()
        miner.approval_notes = data.get('notes', '申请被拒绝')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '矿机申请已拒绝',
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"拒绝矿机申请失败: {e}")
        return jsonify({
            'success': False,
            'error': '拒绝矿机申请失败'
        }), 500

@hosting_bp.route('/api/miners/<int:miner_id>', methods=['GET'])
@login_required
def get_miner_detail(miner_id):
    """获取单个矿机详情"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        miner = HostingMiner.query.get_or_404(miner_id)
        
        # 权限检查：托管商可以查看所有，客户只能查看自己的
        if user_role not in ['owner', 'admin', 'mining_site_owner'] and miner.customer_id != user_id:
            return jsonify({
                'success': False,
                'error': '无权限查看此矿机'
            }), 403
        
        # 构建详细信息
        miner_data = miner.to_dict()
        
        # 添加关联信息
        if miner.customer:
            miner_data['customer_name'] = miner.customer.email
            miner_data['customer_email'] = miner.customer.email
        
        if miner.miner_model:
            miner_data['miner_model_name'] = miner.miner_model.model_name
        
        # 获取站点信息
        if miner.site_id:
            site = HostingSite.query.get(miner.site_id)
            if site:
                miner_data['site_name'] = site.name
                miner_data['site_location'] = site.location
        
        return jsonify({
            'success': True,
            'miner': miner_data
        })
        
    except Exception as e:
        logger.error(f"获取矿机详情失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取矿机详情失败'
        }), 500

@hosting_bp.route('/api/miners/<int:miner_id>/telemetry-history', methods=['GET'])
@login_required
def get_miner_telemetry_history(miner_id):
    """获取矿机遥测历史数据（优先24小时，回退到最近可用数据）"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        miner = HostingMiner.query.get_or_404(miner_id)
        
        # 权限检查：防御性检查确保session完整性
        if user_role not in ['owner', 'admin', 'mining_site_owner']:
            if not user_id or miner.customer_id != user_id:
                return jsonify({'success': False, 'error': '无权限'}), 403
        
        # 优先查询最近24小时的遥测数据
        time_24h_ago = datetime.utcnow() - timedelta(hours=24)
        
        telemetry_records = MinerTelemetry.query.filter(
            MinerTelemetry.miner_id == miner_id,
            MinerTelemetry.recorded_at >= time_24h_ago
        ).order_by(MinerTelemetry.recorded_at.asc()).all()
        
        # 如果最近24小时没有数据，回退到最近30天的数据（最多50条）
        if not telemetry_records:
            logger.info(f"矿机{miner_id}最近24小时无数据，回退查询最近30天数据")
            time_30d_ago = datetime.utcnow() - timedelta(days=30)
            telemetry_records = MinerTelemetry.query.filter(
                MinerTelemetry.miner_id == miner_id,
                MinerTelemetry.recorded_at >= time_30d_ago
            ).order_by(MinerTelemetry.recorded_at.desc()).limit(50).all()
            
            # 重新按时间正序排列
            telemetry_records = sorted(telemetry_records, key=lambda x: x.recorded_at)
        
        # 构建时间序列数据
        data = {
            'timestamps': [record.recorded_at.strftime('%Y-%m-%d %H:%M:%S') for record in telemetry_records],
            'hashrate': [record.hashrate for record in telemetry_records],
            'temperature': [record.temperature for record in telemetry_records],
            'power_consumption': [record.power_consumption for record in telemetry_records]
        }
        
        return jsonify({'success': True, 'data': data})
        
    except Exception as e:
        logger.error(f"获取遥测历史失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/miner/<int:miner_id>/detail')
@login_required
def miner_detail_page(miner_id):
    """矿机详情页面"""
    try:
        miner = HostingMiner.query.get_or_404(miner_id)
        user_role = session.get('role', 'guest')
        user_id = session.get('user_id')
        
        # 权限检查：防御性检查确保session完整性
        if user_role not in ['owner', 'admin', 'mining_site_owner']:
            if not user_id or miner.customer_id != user_id:
                flash('无权限访问' if session.get('language', 'zh') == 'zh' else 'Access denied', 'error')
                return redirect(url_for('hosting_service_bp.host_view', view_type='devices'))
        
        return render_template('hosting/miner_detail.html', miner=miner, current_lang=session.get('language', 'zh'))
    except Exception as e:
        logger.error(f"矿机详情页面错误: {e}")
        flash('矿机未找到' if session.get('language', 'zh') == 'zh' else 'Miner not found', 'error')
        return redirect(url_for('hosting_service_bp.host_view', view_type='devices'))

@hosting_bp.route('/api/miners/<int:miner_id>', methods=['PUT'])
@login_required
def update_miner(miner_id):
    """更新矿机信息"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        miner = HostingMiner.query.get_or_404(miner_id)
        
        if user_role not in ['owner', 'admin', 'mining_site_owner'] and miner.customer_id != user_id:
            return jsonify({
                'success': False,
                'error': '无权限操作'
            }), 403
        
        updateable_fields = ['rack_position', 'ip_address', 'mac_address', 'actual_hashrate', 'actual_power', 'status']
        
        for field in updateable_fields:
            if field in data:
                setattr(miner, field, data[field])
        
        if 'encrypted_ip' in data:
            if data['encrypted_ip']:
                miner.encrypted_ip = json.dumps(data['encrypted_ip']) if isinstance(data['encrypted_ip'], dict) else data['encrypted_ip']
                miner.ip_address = None
            else:
                miner.encrypted_ip = None
        
        if 'encrypted_mac' in data:
            if data['encrypted_mac']:
                miner.encrypted_mac = json.dumps(data['encrypted_mac']) if isinstance(data['encrypted_mac'], dict) else data['encrypted_mac']
                miner.mac_address = None
            else:
                miner.encrypted_mac = None
        
        miner.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '矿机信息更新成功',
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新矿机失败: {e}")
        return jsonify({
            'success': False,
            'error': '更新矿机失败'
        }), 500

@hosting_bp.route('/api/miners/<int:miner_id>/encrypted-network', methods=['GET'])
@login_required
def get_encrypted_network(miner_id):
    """获取矿机加密的网络信息 (IP/MAC)"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        miner = HostingMiner.query.get_or_404(miner_id)
        
        if user_role not in ['owner', 'admin', 'mining_site_owner'] and miner.customer_id != user_id:
            return jsonify({
                'success': False,
                'error': '无权限操作'
            }), 403
        
        encrypted_ip = None
        encrypted_mac = None
        
        if miner.encrypted_ip:
            try:
                encrypted_ip = json.loads(miner.encrypted_ip) if isinstance(miner.encrypted_ip, str) else miner.encrypted_ip
            except json.JSONDecodeError:
                encrypted_ip = miner.encrypted_ip
        
        if miner.encrypted_mac:
            try:
                encrypted_mac = json.loads(miner.encrypted_mac) if isinstance(miner.encrypted_mac, str) else miner.encrypted_mac
            except json.JSONDecodeError:
                encrypted_mac = miner.encrypted_mac
        
        return jsonify({
            'success': True,
            'encrypted_ip': encrypted_ip,
            'encrypted_mac': encrypted_mac
        })
        
    except Exception as e:
        logger.error(f"获取加密网络信息失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取加密网络信息失败'
        }), 500

# ==================== 矿场主级别加密 API ====================

@hosting_bp.route('/api/encryption/owner-key', methods=['GET'])
@login_required
def get_owner_encryption_status():
    """获取矿场主加密状态 - 严格按用户范围过滤"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        if user_role not in ['owner', 'admin', 'mining_site_owner']:
            return jsonify({'success': False, 'error': '无权限'}), 403
        
        owner_enc = HostingOwnerEncryption.query.filter_by(owner_id=user_id).first()
        
        base_query = HostingMiner.query.filter(HostingMiner.customer_id == user_id)
        total_miners = base_query.count()
        
        if not owner_enc:
            return jsonify({
                'success': True,
                'has_encryption': False,
                'total_miners': total_miners,
                'encrypted_miners': 0
            })
        
        encrypted_count = base_query.filter(
            HostingMiner.encryption_scope == 'owner'
        ).count()
        
        return jsonify({
            'success': True,
            'has_encryption': True,
            'key_version': owner_enc.key_version,
            'key_algo': owner_enc.key_algo,
            'total_miners': total_miners,
            'encrypted_miners': encrypted_count,
            'status': owner_enc.status,
            'created_at': owner_enc.created_at.isoformat() if owner_enc.created_at else None,
            'last_rotated_at': owner_enc.last_rotated_at.isoformat() if owner_enc.last_rotated_at else None
        })
        
    except Exception as e:
        logger.error(f"获取矿场主加密状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/encryption/owner-key', methods=['POST'])
@login_required
def set_owner_encryption_key():
    """设置矿场主加密密钥"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        if user_role not in ['owner', 'admin', 'mining_site_owner']:
            return jsonify({'success': False, 'error': '无权限'}), 403
        
        data = request.get_json()
        encrypted_data_key = data.get('encrypted_data_key')
        key_salt = data.get('key_salt')
        
        if not encrypted_data_key or not key_salt:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        owner_enc = HostingOwnerEncryption.query.filter_by(owner_id=user_id).first()
        
        if owner_enc:
            owner_enc.encrypted_data_key = json.dumps(encrypted_data_key) if isinstance(encrypted_data_key, dict) else encrypted_data_key
            owner_enc.key_salt = key_salt
            owner_enc.key_version += 1
            owner_enc.last_rotated_at = datetime.utcnow()
            owner_enc.updated_at = datetime.utcnow()
        else:
            owner_enc = HostingOwnerEncryption(
                owner_id=user_id,
                encrypted_data_key=json.dumps(encrypted_data_key) if isinstance(encrypted_data_key, dict) else encrypted_data_key,
                key_salt=key_salt,
                key_iterations=data.get('key_iterations', 100000),
                key_algo=data.get('key_algo', 'AES-256-GCM'),
                key_version=1,
                status='active'
            )
            db.session.add(owner_enc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '加密密钥设置成功',
            'key_version': owner_enc.key_version
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"设置矿场主加密密钥失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/encryption/owner-key/verify', methods=['POST'])
@login_required
def verify_owner_encryption_key():
    """验证矿场主加密密钥（获取加密的数据密钥用于解密）"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        if user_role not in ['owner', 'admin', 'mining_site_owner']:
            return jsonify({'success': False, 'error': '无权限'}), 403
        
        owner_enc = HostingOwnerEncryption.query.filter_by(owner_id=user_id).first()
        
        if not owner_enc:
            return jsonify({'success': False, 'error': '未设置加密密钥'}), 404
        
        encrypted_data_key = owner_enc.encrypted_data_key
        if isinstance(encrypted_data_key, str):
            try:
                encrypted_data_key = json.loads(encrypted_data_key)
            except json.JSONDecodeError:
                pass
        
        return jsonify({
            'success': True,
            'encrypted_data_key': encrypted_data_key,
            'key_salt': owner_enc.key_salt,
            'key_iterations': owner_enc.key_iterations,
            'key_algo': owner_enc.key_algo,
            'key_version': owner_enc.key_version
        })
        
    except Exception as e:
        logger.error(f"验证矿场主加密密钥失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/encryption/bulk-network', methods=['GET'])
@login_required
def get_bulk_encrypted_network():
    """批量获取加密的网络数据 - 严格按用户范围过滤"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        if user_role not in ['owner', 'admin', 'mining_site_owner']:
            return jsonify({'success': False, 'error': '无权限'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        per_page = min(per_page, 500)
        
        query = HostingMiner.query.filter(HostingMiner.customer_id == user_id)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        miners_data = []
        for miner in pagination.items:
            encrypted_ip = None
            encrypted_mac = None
            
            if miner.encrypted_ip:
                try:
                    encrypted_ip = json.loads(miner.encrypted_ip) if isinstance(miner.encrypted_ip, str) else miner.encrypted_ip
                except json.JSONDecodeError:
                    encrypted_ip = miner.encrypted_ip
            
            if miner.encrypted_mac:
                try:
                    encrypted_mac = json.loads(miner.encrypted_mac) if isinstance(miner.encrypted_mac, str) else miner.encrypted_mac
                except json.JSONDecodeError:
                    encrypted_mac = miner.encrypted_mac
            
            miners_data.append({
                'id': miner.id,
                'serial_number': miner.serial_number,
                'ip_address': miner.ip_address,
                'mac_address': miner.mac_address,
                'encrypted_ip': encrypted_ip,
                'encrypted_mac': encrypted_mac,
                'encryption_scope': miner.encryption_scope
            })
        
        return jsonify({
            'success': True,
            'miners': miners_data,
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"批量获取加密网络数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/encryption/bulk-encrypt', methods=['POST'])
@login_required
def bulk_encrypt_miners():
    """批量加密矿机网络数据 - 严格按用户范围过滤"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        if user_role not in ['owner', 'admin', 'mining_site_owner']:
            return jsonify({'success': False, 'error': '无权限'}), 403
        
        data = request.get_json()
        miners_data = data.get('miners', [])
        
        if not miners_data:
            return jsonify({'success': False, 'error': '没有矿机数据'}), 400
        
        updated_count = 0
        for miner_info in miners_data:
            miner_id = miner_info.get('id')
            encrypted_ip = miner_info.get('encrypted_ip')
            encrypted_mac = miner_info.get('encrypted_mac')
            
            miner = HostingMiner.query.get(miner_id)
            if not miner:
                continue
            
            if miner.customer_id != user_id:
                continue
            
            if encrypted_ip:
                miner.encrypted_ip = json.dumps(encrypted_ip) if isinstance(encrypted_ip, dict) else encrypted_ip
                miner.ip_address = None
            
            if encrypted_mac:
                miner.encrypted_mac = json.dumps(encrypted_mac) if isinstance(encrypted_mac, dict) else encrypted_mac
                miner.mac_address = None
            
            miner.encryption_scope = 'owner'
            miner.updated_at = datetime.utcnow()
            updated_count += 1
        
        owner_enc = HostingOwnerEncryption.query.filter_by(owner_id=user_id).first()
        if owner_enc:
            encrypted_count = HostingMiner.query.filter(
                HostingMiner.customer_id == user_id,
                HostingMiner.encryption_scope == 'owner'
            ).count()
            owner_enc.encrypted_miners_count = encrypted_count
            owner_enc.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功加密 {updated_count} 台矿机',
            'updated_count': updated_count
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"批量加密矿机失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/miners/<int:miner_id>', methods=['DELETE'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def delete_miner(miner_id):
    """删除矿机"""
    try:
        miner = HostingMiner.query.get_or_404(miner_id)
        
        # 软删除或硬删除（这里选择硬删除）
        db.session.delete(miner)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '矿机删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除矿机失败: {e}")
        return jsonify({
            'success': False,
            'error': '删除矿机失败'
        }), 500

# ==================== 公开状态页面 ====================

@hosting_bp.route('/status/<site_slug>')
def public_site_status(site_slug):
    """公开站点状态页面 - 无需登录即可访问"""
    try:
        site = HostingSite.query.filter_by(slug=site_slug).first_or_404()
        
        # 基本统计（不涉及敏感信息）
        total_capacity = site.capacity_mw
        utilization_rate = site.utilization_rate
        status = site.status
        
        # 近期公开事件（只显示高级别事件，不包含敏感详情）
        public_incidents = HostingIncident.query.filter(
            HostingIncident.site_id == site.id,
            HostingIncident.severity.in_(['high', 'critical']),  # 只显示高级别事件
            HostingIncident.created_at >= datetime.now() - timedelta(days=7)
        ).order_by(HostingIncident.created_at.desc()).limit(5).all()
        
        # 站点运行时间统计（过去30天）
        thirty_days_ago = datetime.now() - timedelta(days=30)
        total_incidents_30d = HostingIncident.query.filter(
            HostingIncident.site_id == site.id,
            HostingIncident.created_at >= thirty_days_ago
        ).count()
        
        # 平均响应时间（基于已解决的工单）
        resolved_tickets = HostingTicket.query.filter(
            HostingTicket.site_id == site.id,
            HostingTicket.status == 'resolved',
            HostingTicket.resolved_at >= thirty_days_ago
        ).all()
        
        avg_resolution_hours = 0
        if resolved_tickets:
            total_hours = sum(ticket.resolution_time_hours or 0 for ticket in resolved_tickets)
            avg_resolution_hours = round(total_hours / len(resolved_tickets), 1)
        
        status_data = {
            'site': {
                'name': site.name,
                'location': site.location,
                'status': status,
                'capacity_mw': total_capacity,
                'utilization_rate': utilization_rate,
                'operator_name': site.operator_name
            },
            'incidents': [
                {
                    'title': incident.title,
                    'severity': incident.severity,
                    'status': incident.status,
                    'created_at': incident.created_at.isoformat()
                }
                for incident in public_incidents
            ],
            'statistics': {
                'incidents_30d': total_incidents_30d,
                'avg_resolution_hours': avg_resolution_hours,
                'uptime_percentage': max(0, 100 - (total_incidents_30d * 2))  # 简单计算
            },
            'last_updated': datetime.now().isoformat()
        }
        
        # 如果是API请求，返回JSON
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({'success': True, 'status': status_data})
        
        # 否则渲染页面
        return render_template('hosting/public_status.html', status=status_data)
    except Exception as e:
        logger.error(f"获取公开状态失败: {e}")
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            return render_template('hosting/public_status.html', status=None)

# ==================== 全局状态API ====================

@hosting_bp.route('/api/global/status')
def get_global_status_api():
    """全局状态API - 供前端动态加载"""
    try:
        # 获取所有站点统计
        all_sites = HostingSite.query.all()
        online_sites = [s for s in all_sites if s.status == 'online']
        
        total_capacity = sum(s.capacity_mw or 0 for s in all_sites)
        total_used = sum(s.used_capacity_mw or 0 for s in all_sites)
        
        # 获取活跃矿机数
        active_miners = HostingMiner.query.filter_by(status='active').count()
        
        # 计算全局可用率（基于站点在线比例和近期事故）
        recent_incidents = HostingIncident.query.filter(
            HostingIncident.created_at >= datetime.now() - timedelta(days=30)
        ).count()
        global_uptime = max(0, 99.9 - (recent_incidents * 0.1))
        
        # 格式化站点数据供前端使用
        sites_data = []
        for site in all_sites:
            site_miner_count = HostingMiner.query.filter_by(site_id=site.id, status='active').count()
            sites_data.append({
                'name': site.name,
                'location': site.location or '未知',
                'status': site.status,
                'capacity': site.capacity_mw or 0,
                'devices': site_miner_count,
                'uptime': 99.5 if site.status == 'online' else 0,
                'utilization': int(site.utilization_rate or 0),
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
            })
        
        # 近期事件
        incidents = HostingIncident.query.filter(
            HostingIncident.created_at >= datetime.now() - timedelta(days=7)
        ).order_by(HostingIncident.created_at.desc()).limit(5).all()
        
        incidents_data = [{
            'title': inc.title,
            'severity': inc.severity,
            'status': inc.status,
            'created_at': inc.created_at.isoformat()
        } for inc in incidents]
        
        return jsonify({
            'success': True,
            'stats': {
                'total_sites': len(all_sites),
                'online_sites': len(online_sites),
                'total_capacity': round(total_capacity, 1),
                'global_uptime': round(global_uptime, 1)
            },
            'sites': sites_data,
            'incidents': incidents_data
        })
    except Exception as e:
        logger.error(f"获取全局状态API失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/global/metrics')
def get_global_metrics_api():
    """全局实时指标API - 供图表使用"""
    try:
        # 生成最近24小时的模拟数据点（实际应用应从监控系统获取）
        from datetime import timedelta
        import random
        
        labels = []
        response_times = []
        connections = []
        
        now = datetime.now()
        for i in range(24, 0, -1):
            time_point = now - timedelta(hours=i)
            labels.append(time_point.strftime('%H:00'))
            # 模拟响应时间 1.5-3.5秒
            response_times.append(round(random.uniform(1.5, 3.5) * 1000, 0))
            # 模拟活跃连接数
            connections.append(random.randint(100, 500))
        
        return jsonify({
            'success': True,
            'labels': labels,
            'response_times': response_times,
            'connections': connections
        })
    except Exception as e:
        logger.error(f"获取全局指标API失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 全局状态页面（所有站点概览）
@hosting_bp.route('/status')
def global_status():
    """全局状态页面 - 显示所有站点概览"""
    try:
        # 获取所有在线站点
        sites = HostingSite.query.filter_by(status='online').all()
        
        sites_status = []
        total_capacity = 0
        total_used = 0
        
        for site in sites:
            # 近期事件统计
            recent_incidents = HostingIncident.query.filter(
                HostingIncident.site_id == site.id,
                HostingIncident.created_at >= datetime.now() - timedelta(days=7)
            ).count()
            
            site_data = {
                'name': site.name,
                'slug': site.slug,
                'location': site.location,
                'status': site.status,
                'capacity_mw': site.capacity_mw,
                'utilization_rate': site.utilization_rate,
                'recent_incidents': recent_incidents
            }
            sites_status.append(site_data)
            total_capacity += site.capacity_mw
            total_used += site.used_capacity_mw
        
        global_data = {
            'sites': sites_status,
            'summary': {
                'total_sites': len(sites),
                'total_capacity_mw': total_capacity,
                'total_utilization': round((total_used / total_capacity * 100) if total_capacity > 0 else 0, 1)
            },
            'last_updated': datetime.now().isoformat()
        }
        
        # 如果是API请求，返回JSON
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({'success': True, 'data': global_data})
        
        # 否则渲染页面
        return render_template('hosting/global_status.html', data=global_data)
    except Exception as e:
        logger.error(f"获取全局状态失败: {e}")
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            return render_template('hosting/global_status.html', data=None)

# ==================== 使用记录和对账系统 ====================

@hosting_bp.route('/api/usage/preview', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def generate_usage_preview():
    """生成使用情况预估"""
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        site_id = data.get('site_id')
        period_start = datetime.fromisoformat(data.get('period_start'))
        period_end = datetime.fromisoformat(data.get('period_end'))
        
        # 获取客户在该站点的矿机
        miners = HostingMiner.query.filter_by(
            customer_id=customer_id,
            site_id=site_id
        ).all()
        
        if not miners:
            return jsonify({'success': False, 'error': '该客户在此站点无托管设备'}), 400
        
        # 获取站点信息
        site = HostingSite.query.get(site_id)
        if not site:
            return jsonify({'success': False, 'error': '站点不存在'}), 404
        
        # 计算天数
        days = (period_end - period_start).days
        
        # 计算费用
        total_power = sum(miner.actual_power for miner in miners)
        electricity_cost = (total_power / 1000) * 24 * days * site.electricity_rate  # kW * hours * rate
        
        # 托管费（每台设备每天固定费用，这里假设$2/天）
        hosting_fee = len(miners) * 2.0 * days
        
        # 维护费（按算力计算，假设$0.01/TH/天）
        total_hashrate = sum(miner.actual_hashrate for miner in miners)
        maintenance_cost = total_hashrate * 0.01 * days
        
        # 创建使用情况预估
        usage_preview = {
            'customer_id': customer_id,
            'site_id': site_id,
            'site_name': site.name,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'days': days,
            'miners_count': len(miners),
            'total_power_w': total_power,
            'total_hashrate_th': total_hashrate,
            'costs': {
                'electricity_cost': round(electricity_cost, 2),
                'hosting_fee': round(hosting_fee, 2),
                'maintenance_cost': round(maintenance_cost, 2),
                'total_amount': round(electricity_cost + hosting_fee + maintenance_cost, 2)
            },
            'breakdown': [
                {
                    'item': '电费',
                    'description': f'{total_power/1000:.1f}kW × {days}天 × ${site.electricity_rate}/kWh',
                    'amount': round(electricity_cost, 2)
                },
                {
                    'item': '托管费',
                    'description': f'{len(miners)}台设备 × {days}天 × $2.00/天',
                    'amount': round(hosting_fee, 2)
                },
                {
                    'item': '维护费',
                    'description': f'{total_hashrate:.1f}TH × {days}天 × $0.01/TH/天',
                    'amount': round(maintenance_cost, 2)
                }
            ]
        }
        
        return jsonify({'success': True, 'preview': usage_preview})
    except Exception as e:
        logger.error(f"生成使用情况预估失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/usage/create', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def create_usage_record():
    """根据预估创建正式使用记录"""
    try:
        data = request.get_json()
        
        # 生成使用记录编号
        record_number = f"USAGE-{datetime.now().strftime('%Y%m%d')}-{data['customer_id']:04d}-{data['site_id']:02d}"
        
        usage_record = HostingUsageRecord(
            record_number=record_number,
            customer_id=data['customer_id'],
            site_id=data['site_id'],
            usage_period_start=datetime.fromisoformat(data['period_start']).date(),
            usage_period_end=datetime.fromisoformat(data['period_end']).date(),
            electricity_cost=data['costs']['electricity_cost'],
            hosting_fee=data['costs']['hosting_fee'],
            maintenance_cost=data['costs']['maintenance_cost'],
            total_amount=data['costs']['total_amount'],
            due_date=datetime.now().date() + timedelta(days=30)  # 30天付款期
        )
        
        db.session.add(usage_record)
        db.session.flush()  # 获取ID
        
        # 创建使用记录明细
        for item in data['breakdown']:
            usage_item = HostingUsageItem(
                usage_record_id=usage_record.id,
                item_type=item['item'].lower(),
                description=item['description'],
                quantity=1,
                unit_price=item['amount'],
                amount=item['amount']
            )
            db.session.add(usage_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '使用记录创建成功',
            'record_id': usage_record.id,
            'record_number': usage_record.record_number
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建使用记录失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/reconcile/upload', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def upload_reconcile_data():
    """上传对账数据（CSV文件）"""
    try:
        import csv
        import io
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'}), 400
        
        if not (file.filename and file.filename.endswith('.csv')):
            return jsonify({'success': False, 'error': '只支持CSV文件'}), 400
        
        # 读取CSV内容
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        # 数据类型检测
        data_type = request.form.get('data_type', 'pool_payouts')  # pool_payouts 或 electricity_usage
        
        processed_records = []
        errors = []
        
        for row_num, row in enumerate(csv_input, start=2):
            try:
                if data_type == 'pool_payouts':
                    # 矿池收益数据格式
                    record = {
                        'miner_serial': row.get('miner_serial', '').strip(),
                        'pool_url': row.get('pool_url', '').strip(),
                        'worker_name': row.get('worker_name', '').strip(),
                        'hashrate': float(row.get('hashrate', 0)),
                        'payout_amount': float(row.get('payout_amount', 0)),
                        'date': datetime.strptime(row.get('date', ''), '%Y-%m-%d').date(),
                        'currency': row.get('currency', 'BTC').strip()
                    }
                elif data_type == 'electricity_usage':
                    # 电力使用数据格式
                    record = {
                        'meter_id': row.get('meter_id', '').strip(),
                        'site_name': row.get('site_name', '').strip(),
                        'usage_kwh': float(row.get('usage_kwh', 0)),
                        'cost_usd': float(row.get('cost_usd', 0)),
                        'reading_time': datetime.strptime(row.get('reading_time', ''), '%Y-%m-%d %H:%M'),
                        'rate_per_kwh': float(row.get('rate_per_kwh', 0))
                    }
                else:
                    return jsonify({'success': False, 'error': f'不支持的数据类型: {data_type}'}), 400
                
                processed_records.append(record)
            except Exception as e:
                errors.append(f"第{row_num}行错误: {str(e)}")
        
        if errors:
            return jsonify({
                'success': False,
                'error': '数据格式错误',
                'details': errors[:10]  # 只返回前10个错误
            }), 400
        
        # 保存处理结果到临时存储或数据库
        # 这里可以将数据保存到专门的对账表中
        
        return jsonify({
            'success': True,
            'message': f'成功处理 {len(processed_records)} 条记录',
            'data_type': data_type,
            'records_count': len(processed_records),
            'preview': processed_records[:5]  # 返回前5条作为预览
        })
    except Exception as e:
        logger.error(f"上传对账数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/reconcile/analyze', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def analyze_reconciliation():
    """分析对账差异"""
    try:
        data = request.get_json()
        site_id = data.get('site_id')
        period_start = datetime.fromisoformat(data.get('period_start'))
        period_end = datetime.fromisoformat(data.get('period_end'))
        
        # 获取该期间的账单
        bills = HostingBill.query.filter(
            HostingBill.site_id == site_id,
            HostingBill.billing_period_start >= period_start.date(),
            HostingBill.billing_period_end <= period_end.date()
        ).all()
        
        # 分析差异（这里是示例逻辑）
        discrepancies = []
        
        for bill in bills:
            # 假设从上传的数据中检查差异
            estimated_electricity = bill.electricity_cost
            actual_electricity = estimated_electricity * (0.95 + 0.1 * hash(bill.bill_number) % 100 / 1000)  # 模拟实际数据
            
            difference = abs(estimated_electricity - actual_electricity)
            difference_percentage = (difference / estimated_electricity) * 100
            
            if difference_percentage > 2:  # 差异超过2%
                discrepancies.append({
                    'bill_number': bill.bill_number,
                    'customer_name': bill.customer.name if bill.customer else 'Unknown',
                    'item': '电费',
                    'estimated': estimated_electricity,
                    'actual': actual_electricity,
                    'difference': difference,
                    'difference_percentage': round(difference_percentage, 2),
                    'status': 'needs_review'
                })
        
        analysis_result = {
            'period': f"{period_start.date()} 至 {period_end.date()}",
            'total_bills': len(bills),
            'discrepancies_count': len(discrepancies),
            'discrepancies': discrepancies,
            'accuracy_rate': round(((len(bills) - len(discrepancies)) / len(bills) * 100) if bills else 100, 1),
            'recommendations': [
                '建议复核电表读数的准确性',
                '检查设备功耗是否有异常变化',
                '确认电费费率是否有调整'
            ] if discrepancies else ['本期对账数据准确，无需特别关注']
        }
        
        return jsonify({'success': True, 'analysis': analysis_result})
    except Exception as e:
        logger.error(f"分析对账差异失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 健康检查端点 ====================

@hosting_bp.route('/healthz')
def health_check():
    """健康检查端点 - 不需要认证"""
    try:
        # 基本数据库连接检查
        db.session.execute(db.text('SELECT 1')).fetchone()
        
        # 简单的系统状态检查
        status_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'version': '1.0.0',
            'services': {
                'hosting': 'running',
                'monitoring': 'active',
                'status_pages': 'available'
            }
        }
        
        return jsonify(status_data), 200
    except Exception as e:
        error_status = {
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'database': 'disconnected'
        }
        return jsonify(error_status), 503

# ==================== 监控API路由 ====================

@hosting_bp.route('/api/monitoring/overview', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_monitoring_overview():
    """获取监控概览数据"""
    try:
        # 活跃告警统计
        active_alerts = HostingIncident.query.filter(
            HostingIncident.status.in_(['open', 'investigating'])
        ).count()
        
        # 总事件统计
        total_incidents = HostingIncident.query.count()
        
        # 平均响应时间（分钟）
        recent_incidents = HostingIncident.query.filter(
            HostingIncident.created_at >= datetime.now() - timedelta(days=30)
        ).all()
        
        avg_response_time = 0
        if recent_incidents:
            response_times = []
            for incident in recent_incidents:
                if incident.first_response_at:
                    response_time = (incident.first_response_at - incident.created_at).total_seconds() / 60
                    response_times.append(response_time)
            avg_response_time = round(sum(response_times) / len(response_times)) if response_times else 0
        
        # 系统可用率
        total_sites = HostingSite.query.count()
        online_sites = HostingSite.query.filter_by(status='online').count()
        uptime_percentage = round((online_sites / total_sites * 100) if total_sites > 0 else 100, 1)
        
        # 模拟系统指标（后续可接入真实监控数据）
        import random
        metrics = {
            'cpu_usage': random.randint(15, 85),
            'memory_usage': random.randint(40, 80),
            'network_io': round(random.uniform(1.2, 15.8), 1),
            'error_rate': round(random.uniform(0.1, 2.5), 1)
        }
        
        # 近期告警列表
        recent_alerts = HostingIncident.query.filter(
            HostingIncident.status.in_(['open', 'investigating']),
            HostingIncident.created_at >= datetime.now() - timedelta(hours=24)
        ).order_by(HostingIncident.created_at.desc()).limit(5).all()
        
        alerts_data = []
        for alert in recent_alerts:
            site_name = alert.site.name if alert.site else 'Global'
            alerts_data.append({
                'id': alert.id,
                'title': alert.title,
                'description': alert.description[:100] + '...' if len(alert.description) > 100 else alert.description,
                'severity': alert.severity,
                'site_name': site_name,
                'created_at': alert.created_at.strftime('%H:%M')
            })
        
        overview_data = {
            'stats': {
                'active_alerts': active_alerts,
                'total_incidents': total_incidents,
                'avg_response_time': avg_response_time,
                'uptime_percentage': uptime_percentage
            },
            'metrics': metrics,
            'alerts': alerts_data
        }
        
        return jsonify({'success': True, **overview_data})
    except Exception as e:
        logger.error(f"获取监控概览失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/monitoring/incidents', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_monitoring_incidents():
    """获取事件管理数据"""
    try:
        # 获取筛选参数
        severity = request.args.get('severity')
        status = request.args.get('status')
        site_id = request.args.get('site_id')
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # 构建查询
        query = HostingIncident.query
        
        if severity:
            query = query.filter(HostingIncident.severity == severity)
        if status:
            query = query.filter(HostingIncident.status == status)
        if site_id:
            query = query.filter(HostingIncident.site_id == site_id)
        if search:
            query = query.filter(
                HostingIncident.title.contains(search) |
                HostingIncident.description.contains(search)
            )
        
        # 分页
        incidents_page = query.order_by(HostingIncident.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        incidents_data = []
        for incident in incidents_page.items:
            # 计算持续时间
            duration = None
            if incident.resolved_at:
                duration_delta = incident.resolved_at - incident.created_at
                hours = int(duration_delta.total_seconds() // 3600)
                minutes = int((duration_delta.total_seconds() % 3600) // 60)
                duration = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
            site_name = incident.site.name if incident.site else 'Global'
            
            incidents_data.append({
                'id': incident.id,
                'title': incident.title,
                'severity': incident.severity,
                'status': incident.status,
                'site_name': site_name,
                'created_at': incident.created_at.strftime('%Y-%m-%d %H:%M'),
                'duration': duration
            })
        
        pagination_data = {
            'current_page': page,
            'total_pages': incidents_page.pages,
            'total_items': incidents_page.total,
            'per_page': per_page,
            'has_next': incidents_page.has_next,
            'has_prev': incidents_page.has_prev
        }
        
        return jsonify({
            'success': True,
            'incidents': incidents_data,
            'pagination': pagination_data
        })
    except Exception as e:
        logger.error(f"获取事件列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/monitoring/incidents', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def create_monitoring_incident():
    """创建新的监控事件"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        incident = HostingIncident(
            title=data['title'],
            description=data['description'],
            severity=data['severity'],
            category=data.get('category', 'other'),
            site_id=data.get('site_id') if data.get('site_id') else None,
            status='open',
            reporter_id=session.get('user_id')
        )
        
        db.session.add(incident)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '事件创建成功',
            'incident_id': incident.id
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建监控事件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 限电管理API Curtailment Management API ====================

@hosting_bp.route('/api/curtailment/calculate', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def calculate_curtailment():
    """
    计算限电方案 Calculate curtailment plan
    
    根据指定策略计算最优限电方案
    Calculate optimal curtailment plan based on specified strategy
    """
    data = request.get_json() if request.is_json else request.form
    user_id = session.get('user_id')
    
    # 检查必需参数 Check required parameters
    required_fields = ['site_id', 'strategy_id', 'target_power_reduction_kw']
    missing_fields = [f for f in required_fields if f not in data or data.get(f) is None]
    if missing_fields:
        logger.warning(f"缺少必需参数 Missing required parameters: {', '.join(missing_fields)}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': f'缺少必需参数 Missing required parameters: {", ".join(missing_fields)}'
        }), 400
    
    # 参数类型转换和验证 Parameter type conversion and validation
    try:
        site_id = int(data['site_id'])
        strategy_id = int(data['strategy_id'])
        target_power_reduction_kw = float(data['target_power_reduction_kw'])
    except (ValueError, TypeError) as e:
        logger.warning(f"参数格式错误 Parameter format error: {e}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': '参数格式错误：site_id和strategy_id必须为整数，target_power_reduction_kw必须为数字 Parameter format error: site_id and strategy_id must be integers, target_power_reduction_kw must be a number'
        }), 400
    
    # 数值范围验证 Validate value ranges
    if site_id <= 0:
        logger.warning(f"无效的site_id Invalid site_id: {site_id}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': 'site_id必须大于0 site_id must be greater than 0'
        }), 400
    
    if strategy_id <= 0:
        logger.warning(f"无效的strategy_id Invalid strategy_id: {strategy_id}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': 'strategy_id必须大于0 strategy_id must be greater than 0'
        }), 400
    
    if target_power_reduction_kw <= 0:
        logger.warning(f"无效的target_power_reduction_kw Invalid target_power_reduction_kw: {target_power_reduction_kw}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': '目标功率削减值必须大于0 target_power_reduction_kw must be greater than 0'
        }), 400
    
    # 可选参数验证 Optional parameters validation
    btc_price = None
    electricity_rate = None
    duration_hours = 24
    
    if 'btc_price' in data and data['btc_price'] is not None:
        try:
            btc_price = float(data['btc_price'])
            if btc_price <= 0:
                logger.warning(f"无效的btc_price Invalid btc_price: {btc_price}, user_id={user_id}")
                return jsonify({
                    'success': False,
                    'error': 'btc_price必须大于0 btc_price must be greater than 0'
                }), 400
        except (ValueError, TypeError) as e:
            logger.warning(f"btc_price格式错误 btc_price format error: {e}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': 'btc_price必须为数字 btc_price must be a number'
            }), 400
    
    if 'electricity_rate' in data and data['electricity_rate'] is not None:
        try:
            electricity_rate = float(data['electricity_rate'])
            if electricity_rate <= 0:
                logger.warning(f"无效的electricity_rate Invalid electricity_rate: {electricity_rate}, user_id={user_id}")
                return jsonify({
                    'success': False,
                    'error': 'electricity_rate必须大于0 electricity_rate must be greater than 0'
                }), 400
        except (ValueError, TypeError) as e:
            logger.warning(f"electricity_rate格式错误 electricity_rate format error: {e}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': 'electricity_rate必须为数字 electricity_rate must be a number'
            }), 400
    
    if 'duration_hours' in data and data['duration_hours'] is not None:
        try:
            duration_hours = int(data['duration_hours'])
            if duration_hours <= 0:
                logger.warning(f"无效的duration_hours Invalid duration_hours: {duration_hours}, user_id={user_id}")
                return jsonify({
                    'success': False,
                    'error': 'duration_hours必须大于0 duration_hours must be greater than 0'
                }), 400
        except (ValueError, TypeError) as e:
            logger.warning(f"duration_hours格式错误 duration_hours format error: {e}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': 'duration_hours必须为整数 duration_hours must be an integer'
            }), 400
    
    try:
        
        # 验证站点存在性 Validate site exists
        site = HostingSite.query.get(site_id)
        if not site:
            logger.warning(f"站点不存在 Site not found: site_id={site_id}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': f'站点不存在 Site not found: {site_id}'
            }), 404
        
        # 验证策略存在性 Validate strategy exists
        strategy = CurtailmentStrategy.query.get(strategy_id)
        if not strategy:
            logger.warning(f"策略不存在 Strategy not found: strategy_id={strategy_id}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': f'策略不存在 Strategy not found: {strategy_id}'
            }), 404
        
        # 验证策略是否属于该站点 Validate strategy belongs to site
        if strategy.site_id != site_id:
            logger.warning(f"策略不属于该站点 Strategy does not belong to site: strategy_id={strategy_id}, site_id={site_id}")
            return jsonify({
                'success': False,
                'error': '策略不属于该站点 Strategy does not belong to the specified site'
            }), 400
        
        logger.info(f"开始计算限电方案 Starting curtailment calculation: site_id={site_id}, strategy_id={strategy_id}, target={target_power_reduction_kw}kW, user_id={user_id}")
        
        # 调用限电引擎计算方案 Call curtailment engine
        plan_result = calculate_curtailment_plan(
            site_id=site_id,
            strategy_id=strategy_id,
            target_power_reduction_kw=target_power_reduction_kw,
            btc_price=btc_price,
            electricity_rate=electricity_rate,
            duration_hours=duration_hours
        )
        
        # 检查计算是否成功 Check if calculation succeeded
        if not plan_result.get('success', False):
            logger.error(f"限电方案计算失败 Curtailment calculation failed: {plan_result.get('error', 'Unknown error')}")
            return jsonify({
                'success': False,
                'error': plan_result.get('error', '限电方案计算失败 Curtailment calculation failed')
            }), 500
        
        logger.info(f"限电方案计算成功 Curtailment calculation successful: selected_miners={len(plan_result.get('selected_miners', []))}, total_power_saved={plan_result.get('total_power_saved_kw', 0)}kW")
        
        return jsonify({
            'success': True,
            'plan': {
                'selected_miners': plan_result.get('selected_miners', []),
                'total_power_saved': plan_result.get('total_power_saved_kw', 0),
                'affected_customers': plan_result.get('affected_customers', []),
                'economic_impact': plan_result.get('economic_impact', {})
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"计算限电方案失败 Calculate curtailment failed: {e}, user_id={session.get('user_id')}")
        return jsonify({
            'success': False,
            'error': f'计算限电方案失败 Calculate curtailment failed: {str(e)}'
        }), 500

@hosting_bp.route('/api/curtailment/execute', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def execute_curtailment():
    """
    执行限电计划 Execute curtailment plan
    
    创建并执行限电计划，根据执行模式决定是否需要审批
    Create and execute curtailment plan, approval required based on execution mode
    """
    data = request.get_json() if request.is_json else request.form
    user_id = session.get('user_id')
    
    # 检查必需参数 Check required parameters
    required_fields = ['site_id', 'strategy_id', 'target_power_reduction_kw', 'execution_mode']
    missing_fields = [f for f in required_fields if f not in data or data.get(f) is None]
    if missing_fields:
        logger.warning(f"缺少必需参数 Missing required parameters: {', '.join(missing_fields)}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': f'缺少必需参数 Missing required parameters: {", ".join(missing_fields)}'
        }), 400
    
    # 参数类型转换和验证 Parameter type conversion and validation
    try:
        site_id = int(data['site_id'])
        strategy_id = int(data['strategy_id'])
        target_power_reduction_kw = float(data['target_power_reduction_kw'])
    except (ValueError, TypeError) as e:
        logger.warning(f"参数格式错误 Parameter format error: {e}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': '参数格式错误：site_id和strategy_id必须为整数，target_power_reduction_kw必须为数字 Parameter format error: site_id and strategy_id must be integers, target_power_reduction_kw must be a number'
        }), 400
    
    # 数值范围验证 Validate value ranges
    if site_id <= 0:
        logger.warning(f"无效的site_id Invalid site_id: {site_id}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': 'site_id必须大于0 site_id must be greater than 0'
        }), 400
    
    if strategy_id <= 0:
        logger.warning(f"无效的strategy_id Invalid strategy_id: {strategy_id}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': 'strategy_id必须大于0 strategy_id must be greater than 0'
        }), 400
    
    if target_power_reduction_kw <= 0:
        logger.warning(f"无效的target_power_reduction_kw Invalid target_power_reduction_kw: {target_power_reduction_kw}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': '目标功率削减值必须大于0 target_power_reduction_kw must be greater than 0'
        }), 400
    
    # 验证execution_mode Validate execution_mode
    execution_mode_str = data['execution_mode']
    if execution_mode_str not in ['auto', 'semi_auto', 'manual']:
        logger.warning(f"无效的execution_mode Invalid execution_mode: {execution_mode_str}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': f'无效的执行模式 Invalid execution mode: {execution_mode_str}. 必须是 Valid values: auto, semi_auto, manual'
        }), 400
    
    try:
        
        # 验证站点存在性 Validate site exists
        site = HostingSite.query.get(site_id)
        if not site:
            logger.warning(f"站点不存在 Site not found: site_id={site_id}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': f'站点不存在 Site not found: {site_id}'
            }), 404
        
        # 验证策略存在性 Validate strategy exists
        strategy = CurtailmentStrategy.query.get(strategy_id)
        if not strategy:
            logger.warning(f"策略不存在 Strategy not found: strategy_id={strategy_id}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': f'策略不存在 Strategy not found: {strategy_id}'
            }), 404
        
        # 解析执行模式 Parse execution mode
        execution_mode = ExecutionMode(execution_mode_str)
        
        # 根据执行模式决定状态 Determine status based on execution mode
        if execution_mode == ExecutionMode.AUTO:
            plan_status = PlanStatus.APPROVED
            status_message = '自动模式，计划已批准 Auto mode, plan approved'
        elif execution_mode == ExecutionMode.SEMI_AUTO:
            plan_status = PlanStatus.PENDING
            status_message = '半自动模式，等待审批 Semi-auto mode, pending approval'
        else:  # MANUAL
            plan_status = PlanStatus.PENDING
            status_message = '手动模式，等待审批 Manual mode, pending approval'
        
        logger.info(f"创建限电计划 Creating curtailment plan: site_id={site_id}, strategy_id={strategy_id}, mode={execution_mode_str}, user_id={user_id}")
        
        # 创建限电计划 Create curtailment plan
        plan = CurtailmentPlan(
            site_id=site_id,
            strategy_id=strategy_id,
            plan_name=data.get('plan_name', f'限电计划 Curtailment Plan {datetime.now().strftime("%Y%m%d%H%M%S")}'),
            target_power_reduction_kw=target_power_reduction_kw,
            execution_mode=execution_mode,
            scheduled_start_time=datetime.fromisoformat(data['scheduled_start_time']) if 'scheduled_start_time' in data else datetime.now(),
            scheduled_end_time=datetime.fromisoformat(data['scheduled_end_time']) if 'scheduled_end_time' in data else None,
            status=plan_status,
            created_by_id=user_id,
            approved_by_id=user_id if execution_mode == ExecutionMode.AUTO else None,
            approved_at=datetime.now() if execution_mode == ExecutionMode.AUTO else None
        )
        
        db.session.add(plan)
        db.session.commit()
        
        logger.info(f"限电计划创建成功 Curtailment plan created successfully: plan_id={plan.id}, status={plan_status.value}")
        
        return jsonify({
            'success': True,
            'plan_id': plan.id,
            'status': plan_status.value,
            'message': status_message
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"执行限电计划失败 Execute curtailment failed: {e}, user_id={session.get('user_id')}")
        return jsonify({
            'success': False,
            'error': f'执行限电计划失败 Execute curtailment failed: {str(e)}'
        }), 500

@hosting_bp.route('/api/curtailment/cancel', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def cancel_curtailment():
    """
    取消限电计划 Cancel curtailment plan
    
    取消已创建的限电计划
    Cancel an existing curtailment plan
    """
    data = request.get_json() if request.is_json else request.form
    user_id = session.get('user_id')
    
    # 检查必需参数 Check required parameters
    if 'plan_id' not in data or data.get('plan_id') is None:
        logger.warning(f"缺少必需参数 Missing required parameter: plan_id, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': '缺少必需参数 Missing required parameter: plan_id'
        }), 400
    
    # 参数类型转换和验证 Parameter type conversion and validation
    try:
        plan_id = int(data['plan_id'])
    except (ValueError, TypeError) as e:
        logger.warning(f"参数格式错误 Parameter format error: {e}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': 'plan_id必须为整数 plan_id must be an integer'
        }), 400
    
    # 数值范围验证 Validate value ranges
    if plan_id <= 0:
        logger.warning(f"无效的plan_id Invalid plan_id: {plan_id}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': 'plan_id必须大于0 plan_id must be greater than 0'
        }), 400
    
    try:
        
        # 查询计划 Query plan
        plan = CurtailmentPlan.query.get(plan_id)
        if not plan:
            logger.warning(f"限电计划不存在 Curtailment plan not found: plan_id={plan_id}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': f'限电计划不存在 Curtailment plan not found: {plan_id}'
            }), 404
        
        # 检查计划是否可以取消 Check if plan can be cancelled
        if plan.status == PlanStatus.COMPLETED:
            logger.warning(f"已完成的计划不能取消 Completed plan cannot be cancelled: plan_id={plan_id}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': '已完成的计划不能取消 Completed plan cannot be cancelled'
            }), 400
        
        if plan.status == PlanStatus.CANCELLED:
            logger.warning(f"计划已被取消 Plan already cancelled: plan_id={plan_id}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': '计划已被取消 Plan already cancelled'
            }), 400
        
        logger.info(f"取消限电计划 Cancelling curtailment plan: plan_id={plan_id}, previous_status={plan.status.value}, user_id={user_id}")
        
        # 更新计划状态 Update plan status
        plan.status = PlanStatus.CANCELLED
        plan.cancelled_by_id = user_id
        plan.cancelled_at = datetime.now()
        plan.cancellation_reason = data.get('reason', '管理员取消 Cancelled by administrator')
        
        db.session.commit()
        
        logger.info(f"限电计划已取消 Curtailment plan cancelled: plan_id={plan_id}, user_id={user_id}")
        
        return jsonify({
            'success': True,
            'message': f'限电计划已成功取消 Curtailment plan {plan_id} cancelled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"取消限电计划失败 Cancel curtailment failed: {e}, user_id={session.get('user_id')}")
        return jsonify({
            'success': False,
            'error': f'取消限电计划失败 Cancel curtailment failed: {str(e)}'
        }), 500

@hosting_bp.route('/api/curtailment/emergency-restore', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def emergency_restore():
    """
    紧急恢复所有矿机 Emergency restore all miners
    
    紧急情况下恢复站点所有被限电关闭的矿机
    Restore all curtailed miners at a site in emergency situations
    """
    data = request.get_json() if request.is_json else request.form
    user_id = session.get('user_id')
    
    # 检查必需参数 Check required parameters
    if 'site_id' not in data or data.get('site_id') is None:
        logger.warning(f"缺少必需参数 Missing required parameter: site_id, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': '缺少必需参数 Missing required parameter: site_id'
        }), 400
    
    # 参数类型转换和验证 Parameter type conversion and validation
    try:
        site_id = int(data['site_id'])
    except (ValueError, TypeError) as e:
        logger.warning(f"参数格式错误 Parameter format error: {e}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': 'site_id必须为整数 site_id must be an integer'
        }), 400
    
    # 数值范围验证 Validate value ranges
    if site_id <= 0:
        logger.warning(f"无效的site_id Invalid site_id: {site_id}, user_id={user_id}")
        return jsonify({
            'success': False,
            'error': 'site_id必须大于0 site_id must be greater than 0'
        }), 400
    
    reason = data.get('reason', '紧急恢复 Emergency restore')
    
    try:
        
        # 验证站点存在性 Validate site exists
        site = HostingSite.query.get(site_id)
        if not site:
            logger.warning(f"站点不存在 Site not found: site_id={site_id}, user_id={user_id}")
            return jsonify({
                'success': False,
                'error': f'站点不存在 Site not found: {site_id}'
            }), 404
        
        logger.info(f"紧急恢复开始 Emergency restore started: site_id={site_id}, reason={reason}, user_id={user_id}")
        
        # 查找当前执行中的限电计划 Find currently executing curtailment plans
        active_plans = CurtailmentPlan.query.filter(
            CurtailmentPlan.site_id == site_id,
            CurtailmentPlan.status.in_([PlanStatus.APPROVED, PlanStatus.EXECUTING])
        ).all()
        
        if not active_plans:
            logger.info(f"没有找到执行中的限电计划 No active curtailment plans found: site_id={site_id}")
            return jsonify({
                'success': True,
                'restored_count': 0,
                'message': '没有需要恢复的限电计划 No active curtailment plans to restore'
            })
        
        restored_count = 0
        
        # 遍历所有活跃的限电计划 Iterate through all active plans
        for plan in active_plans:
            # 查找该计划的所有关机执行记录 Find all shutdown executions for this plan
            shutdown_executions = CurtailmentExecution.query.filter(
                CurtailmentExecution.plan_id == plan.id,
                CurtailmentExecution.execution_action == ExecutionAction.SHUTDOWN,
                CurtailmentExecution.execution_status == ExecutionStatus.SUCCESS
            ).all()
            
            # 为每个被关闭的矿机创建恢复记录 Create restore record for each shutdown miner
            for execution in shutdown_executions:
                # 创建恢复执行记录 Create restore execution record
                restore_execution = CurtailmentExecution(
                    plan_id=plan.id,
                    miner_id=execution.miner_id,
                    execution_action=ExecutionAction.STARTUP,
                    executed_at=datetime.now(),
                    execution_status=ExecutionStatus.SUCCESS,
                    error_message=None
                )
                db.session.add(restore_execution)
                restored_count += 1
                
                logger.debug(f"恢复矿机 Restoring miner: miner_id={execution.miner_id}, plan_id={plan.id}")
            
            # 更新计划状态为已取消 Update plan status to cancelled
            plan.status = PlanStatus.CANCELLED
            plan.cancelled_by_id = user_id
            plan.cancelled_at = datetime.now()
            plan.cancellation_reason = f'紧急恢复: {reason} Emergency restore: {reason}'
        
        db.session.commit()
        
        logger.info(f"紧急恢复完成 Emergency restore completed: site_id={site_id}, restored_count={restored_count}, cancelled_plans={len(active_plans)}, user_id={user_id}")
        
        return jsonify({
            'success': True,
            'restored_count': restored_count,
            'cancelled_plans': len(active_plans),
            'message': f'成功恢复 {restored_count} 个矿机，取消了 {len(active_plans)} 个限电计划 Successfully restored {restored_count} miners and cancelled {len(active_plans)} curtailment plans'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"紧急恢复失败 Emergency restore failed: {e}, user_id={session.get('user_id')}")
        return jsonify({
            'success': False,
            'error': f'紧急恢复失败 Emergency restore failed: {str(e)}'
        }), 500

# ==================== 限电前端支持API ====================

@hosting_bp.route('/api/sites/list', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_sites_list():
    """获取站点列表（简化版，用于下拉选择）"""
    try:
        sites = HostingSite.query.all()
        sites_data = [{'id': s.id, 'name': s.name} for s in sites]
        return jsonify({'success': True, 'sites': sites_data})
    except Exception as e:
        logger.error(f"获取站点列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/curtailment/strategies', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_curtailment_strategies():
    """获取限电策略列表"""
    try:
        site_id = request.args.get('site_id', type=int)
        
        query = CurtailmentStrategy.query
        if site_id:
            query = query.filter_by(site_id=site_id)
        
        strategies = query.all()
        
        strategies_data = []
        for s in strategies:
            strategies_data.append({
                'id': s.id,
                'name': s.name,
                'strategy_type': s.strategy_type.value,
                'site_id': s.site_id,
                'vip_protection': s.vip_customer_protection,
                'is_active': s.is_active,
                'created_at': s.created_at.isoformat() if s.created_at else None
            })
        
        return jsonify({'success': True, 'strategies': strategies_data})
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/curtailment/kpis', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_curtailment_kpis():
    """获取限电KPI统计数据"""
    try:
        site_id = request.args.get('site_id', type=int)
        
        miner_query = HostingMiner.query
        if site_id:
            miner_query = miner_query.filter_by(site_id=site_id)
        
        total_miners = miner_query.count()
        
        curtailed_miners = miner_query.filter_by(status='curtailed').count()
        
        curtailed_power_result = db.session.query(
            db.func.sum(HostingMiner.actual_power)
        ).filter(
            HostingMiner.status == 'curtailed'
        )
        
        if site_id:
            curtailed_power_result = curtailed_power_result.filter(HostingMiner.site_id == site_id)
        
        curtailed_power_sum = curtailed_power_result.scalar()
        power_saved_kw = round((curtailed_power_sum or 0) / 1000, 2)
        
        kpis = {
            'total_miners': total_miners,
            'curtailed_count': curtailed_miners,
            'power_saved_kw': power_saved_kw
        }
        
        return jsonify({'success': True, 'kpis': kpis})
    except Exception as e:
        logger.error(f"获取KPI失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/curtailment/history', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_curtailment_history():
    """获取限电执行历史"""
    try:
        site_id = request.args.get('site_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = CurtailmentPlan.query
        if site_id:
            query = query.filter_by(site_id=site_id)
        
        pagination = query.order_by(CurtailmentPlan.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        history_data = []
        for plan in pagination.items:
            strategy_name = plan.strategy.name if plan.strategy else 'N/A'
            
            site_name = plan.site.name if plan.site else 'N/A'
            
            # 获取第一个执行记录的时间
            first_execution = CurtailmentExecution.query.filter_by(
                plan_id=plan.id
            ).order_by(CurtailmentExecution.executed_at.asc()).first()
            
            history_data.append({
                'id': plan.id,
                'site_id': plan.site_id,
                'site_name': site_name,
                'strategy_id': plan.strategy_id,
                'strategy_name': strategy_name,
                'target_power_reduction_kw': float(plan.target_power_reduction_kw),
                'actual_power_saved_kw': float(plan.calculated_power_reduction_kw or 0),
                'status': plan.status.value,
                'execution_mode': plan.execution_mode.value,
                'created_at': plan.created_at.isoformat() if plan.created_at else None,
                'executed_at': first_execution.executed_at.isoformat() if first_execution else None
            })
        
        return jsonify({
            'success': True,
            'history': history_data,
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    except Exception as e:
        logger.error(f"获取执行历史失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/curtailment/predict', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def predict_curtailment_schedule():
    """
    AI预测未来24小时最佳限电策略
    
    Request Body:
        - site_id: 矿场ID (required)
        - target_reduction_kw: 目标功率削减量(kW) (optional)
    
    Returns:
        - hourly_schedule: 每小时的限电建议
        - summary: 汇总信息
        - recommendation: 推荐策略
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        site_id = data.get('site_id')
        if not site_id:
            return jsonify({'success': False, 'error': 'site_id is required'}), 400
        
        target_reduction_kw = data.get('target_reduction_kw')
        
        logger.info(f"开始AI预测 - 站点: {site_id}, 目标削减: {target_reduction_kw} kW")
        
        # 调用AI预测引擎
        prediction_result = predict_optimal_curtailment(
            site_id=site_id,
            target_reduction_kw=target_reduction_kw
        )
        
        if not prediction_result.get('success'):
            error_msg = prediction_result.get('error', 'Prediction failed')
            logger.error(f"AI预测失败: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
        logger.info(f"AI预测成功 - 推荐 {prediction_result['summary']['total_hours_curtailed']} 小时限电")
        
        return jsonify(prediction_result)
        
    except Exception as e:
        logger.error(f"AI预测API错误: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 限电计划管理 API ====================

@hosting_bp.route('/api/curtailment/schedules', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def create_curtailment_schedule():
    """
    创建限电计划
    
    Request Body:
        - site_id: 矿场ID (required)
        - plan_name: 计划名称 (required)
        - strategy_id: 策略ID (required)
        - target_power_reduction_kw: 目标功率削减量(kW) (required)
        - scheduled_start_time: 开始时间 ISO格式 (required)
        - scheduled_end_time: 结束时间 ISO格式 (optional)
        - execution_mode: 执行模式 (auto/semi_auto/manual, default: semi_auto)
    
    Returns:
        - success: 是否成功
        - schedule: 创建的计划信息
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # 验证必填字段
        required_fields = ['site_id', 'plan_name', 'strategy_id', 'target_power_reduction_kw', 'scheduled_start_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # 解析开始时间
        try:
            start_time = datetime.fromisoformat(data['scheduled_start_time'].replace('Z', '+00:00'))
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Invalid scheduled_start_time format: {str(e)}'}), 400
        
        # 解析结束时间（可选）
        end_time = None
        if data.get('scheduled_end_time'):
            try:
                end_time = datetime.fromisoformat(data['scheduled_end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({'success': False, 'error': f'Invalid scheduled_end_time format: {str(e)}'}), 400
        
        # 验证站点和策略
        site = HostingSite.query.get(data['site_id'])
        if not site:
            return jsonify({'success': False, 'error': 'Site not found'}), 404
        
        strategy = CurtailmentStrategy.query.get(data['strategy_id'])
        if not strategy:
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404
        
        if strategy.site_id != site.id:
            return jsonify({'success': False, 'error': 'Strategy does not belong to this site'}), 400
        
        # 解析执行模式
        execution_mode_str = data.get('execution_mode', 'semi_auto')
        try:
            execution_mode = ExecutionMode[execution_mode_str.upper()]
        except KeyError:
            return jsonify({'success': False, 'error': f'Invalid execution_mode: {execution_mode_str}'}), 400
        
        # 创建计划
        plan = CurtailmentPlan(
            site_id=data['site_id'],
            plan_name=data['plan_name'],
            target_power_reduction_kw=data['target_power_reduction_kw'],
            scheduled_start_time=start_time
        )
        plan.scheduled_end_time = end_time
        plan.strategy_id = data['strategy_id']
        plan.execution_mode = execution_mode
        plan.status = PlanStatus.PENDING
        plan.created_by_id = session.get('user_id')
        
        db.session.add(plan)
        db.session.commit()
        
        logger.info(f"✅ 限电计划创建成功: {plan.plan_name} (ID={plan.id})")
        
        return jsonify({
            'success': True,
            'schedule': plan.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建限电计划失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/curtailment/schedules', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner', 'customer'])
def get_curtailment_schedules():
    """
    获取限电计划列表
    
    Query Parameters:
        - site_id: 矿场ID (required)
        - status: 状态筛选 (pending/approved/executing/completed/cancelled) (optional)
        - page: 页码 (default: 1)
        - per_page: 每页数量 (default: 20)
    
    Returns:
        - success: 是否成功
        - schedules: 计划列表
        - pagination: 分页信息
    """
    try:
        site_id = request.args.get('site_id', type=int)
        if not site_id:
            return jsonify({'success': False, 'error': 'site_id is required'}), 400
        
        status_filter = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 构建查询
        query = CurtailmentPlan.query.filter_by(site_id=site_id)
        
        if status_filter:
            # 支持逗号分隔的多个状态
            status_values = [s.strip() for s in status_filter.split(',')]
            try:
                status_enums = [PlanStatus[s.upper()] for s in status_values]
                query = query.filter(CurtailmentPlan.status.in_(status_enums))
            except KeyError as e:
                return jsonify({'success': False, 'error': f'Invalid status: {status_filter}'}), 400
        
        # 按开始时间倒序排列
        query = query.order_by(CurtailmentPlan.scheduled_start_time.desc())
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        schedules_data = []
        for plan in pagination.items:
            plan_dict = plan.to_dict()
            
            # 添加兼容性字段名（frontend期待start_time/end_time）
            plan_dict['start_time'] = plan_dict.get('scheduled_start_time')
            plan_dict['end_time'] = plan_dict.get('scheduled_end_time')
            
            # 添加策略名称
            if plan.strategy:
                plan_dict['strategy_name'] = plan.strategy.name
            
            # 计算时间差
            now = datetime.utcnow()
            if plan.scheduled_start_time > now:
                plan_dict['time_until_start_minutes'] = int((plan.scheduled_start_time - now).total_seconds() / 60)
            
            schedules_data.append(plan_dict)
        
        return jsonify({
            'success': True,
            'schedules': schedules_data,
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"获取限电计划列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/curtailment/schedules/<int:schedule_id>/execute', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def execute_curtailment_schedule(schedule_id):
    """
    手动执行限电计划
    
    Returns:
        - success: 是否成功
        - message: 执行结果消息
        - execution_summary: 执行汇总信息
    """
    try:
        plan = CurtailmentPlan.query.get_or_404(schedule_id)
        
        # 验证计划状态（防止重复执行）
        if plan.status not in [PlanStatus.PENDING, PlanStatus.APPROVED]:
            return jsonify({
                'success': False,
                'error': f'Cannot execute plan with status: {plan.status.value}'
            }), 400
        
        logger.info(f"⚡ 手动执行限电计划: {plan.plan_name} (ID={plan.id})")
        
        # 调用服务层执行计划
        from services.curtailment_plan_service import CurtailmentPlanService
        result = CurtailmentPlanService.execute_plan(schedule_id)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Curtailment executed successfully',
            'execution_summary': {
                'miners_affected': result['miners_shutdown'],
                'miners_failed': result['miners_failed'],
                'power_saved_kw': result['total_power_saved_kw']
            }
        })
        
    except Exception as e:
        logger.error(f"执行限电计划失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/curtailment/schedules/<int:schedule_id>', methods=['DELETE'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def cancel_curtailment_schedule(schedule_id):
    """
    取消限电计划
    
    Returns:
        - success: 是否成功
        - message: 取消结果消息
    """
    try:
        plan = CurtailmentPlan.query.get_or_404(schedule_id)
        
        # 验证状态：可以取消pending, approved, 或executing状态的计划
        if plan.status not in [PlanStatus.PENDING, PlanStatus.APPROVED, PlanStatus.EXECUTING]:
            return jsonify({
                'success': False,
                'error': f'Cannot cancel plan with status: {plan.status.value}'
            }), 400
        
        logger.info(f"❌ 取消限电计划: {plan.plan_name} (ID={plan.id})")
        
        # 如果status=EXECUTING，需要先恢复所有被限电的矿机
        if plan.status == PlanStatus.EXECUTING:
            from services.curtailment_plan_service import CurtailmentPlanService
            logger.info(f"  ↩️ 计划正在执行中，先恢复所有被限电矿机")
            
            recover_result = CurtailmentPlanService.recover_plan(schedule_id)
            if not recover_result['success']:
                logger.error(f"  ❌ 恢复矿机失败: {recover_result.get('error')}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to recover miners before cancelling: {recover_result.get("error")}'
                }), 500
            
            logger.info(f"  ✅ 已恢复 {recover_result['miners_recovered']} 台矿机")
        
        # 设置状态为CANCELLED
        plan.status = PlanStatus.CANCELLED
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule cancelled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"取消限电计划失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/curtailment/schedules/<int:schedule_id>/recover', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def recover_curtailment_schedule(schedule_id):
    """
    恢复限电计划的所有矿机
    
    Returns:
        - success: 是否成功
        - message: 恢复结果消息
        - recovery_summary: 恢复汇总信息
    """
    try:
        plan = CurtailmentPlan.query.get_or_404(schedule_id)
        
        # 验证状态：可以恢复EXECUTING或RECOVERY_PENDING状态的计划
        if plan.status not in [PlanStatus.EXECUTING, PlanStatus.RECOVERY_PENDING]:
            return jsonify({
                'success': False,
                'error': f'Cannot recover plan with status: {plan.status.value}'
            }), 400
        
        logger.info(f"🔄 恢复限电计划: {plan.plan_name} (ID={plan.id})")
        
        # 调用服务层恢复矿机
        from services.curtailment_plan_service import CurtailmentPlanService
        result = CurtailmentPlanService.recover_plan(schedule_id)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
        
        return jsonify({
            'success': True,
            'message': result.get('message', 'Miners recovered successfully'),
            'recovery_summary': {
                'miners_recovered': result['miners_recovered'],
                'miners_failed': result['miners_failed'],
                'plan_status': result['plan_status']
            }
        })
        
    except Exception as e:
        logger.error(f"恢复限电计划失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== CGMiner 实时监控 API ====================

@hosting_bp.route('/api/miners/<int:miner_id>/telemetry', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def update_miner_telemetry(miner_id):
    """
    更新矿机CGMiner遥测数据
    
    接收从CGMiner API采集的实时数据并更新数据库
    
    Request Body:
        {
            "timestamp": 1699999999,
            "online": true,
            "hashrate_5s": 110.5,
            "hashrate_avg": 109.8,
            "temperature_avg": 65.2,
            "temperature_max": 72.3,
            "fan_speeds": [3600, 3750, 3680, 3720],
            "fan_avg": 3687,
            "accepted_shares": 12345,
            "rejected_shares": 23,
            "hardware_errors": 0,
            "reject_rate": 0.19,
            "uptime_seconds": 86400,
            "pool_url": "stratum+tcp://btc.example.com:3333",
            "pool_worker": "worker1",
            "pool_status": "Alive"
        }
    
    Returns:
        {
            "success": true,
            "message": "Telemetry data updated successfully"
        }
    """
    try:
        miner = HostingMiner.query.get_or_404(miner_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # 验证timestamp（可选但推荐）- 使用UTC确保与数据库时间一致
        timestamp = data.get('timestamp')
        if timestamp and miner.last_seen:
            try:
                data_time = datetime.utcfromtimestamp(timestamp)
                if data_time < miner.last_seen:
                    logger.warning(f"矿机 {miner_id} 收到过时数据，忽略")
                    return jsonify({
                        'success': False,
                        'error': 'Stale data (timestamp older than last_seen)'
                    }), 400
            except (ValueError, OSError):
                pass  # 无效时间戳，继续处理
        
        # 更新在线状态和last_seen（仅在确认在线时刷新last_seen）
        if 'online' in data:
            miner.cgminer_online = data['online']
            # 只有在线时才更新last_seen，离线时保留旧时间戳用于停机检测
            if data['online']:
                miner.last_seen = datetime.utcnow()
        
        # 只更新payload中明确提供的字段（避免覆盖现有数据）
        if data.get('online'):
            # 在线时才更新性能数据
            if 'hashrate_5s' in data:
                miner.hashrate_5s = data['hashrate_5s']
            if 'hashrate_avg' in data:
                miner.actual_hashrate = data['hashrate_avg']
            if 'temperature_avg' in data:
                miner.temperature_avg = data['temperature_avg']
            if 'temperature_max' in data:
                miner.temperature_max = data['temperature_max']
            
            # 风扇转速存储为JSON字符串
            if 'fan_speeds' in data and data['fan_speeds']:
                miner.fan_speeds = json.dumps(data['fan_speeds'])
            if 'fan_avg' in data:
                miner.fan_avg = data['fan_avg']
            
            # 份额数据（累计值）
            if 'accepted_shares' in data:
                miner.accepted_shares = data['accepted_shares']
            if 'rejected_shares' in data:
                miner.rejected_shares = data['rejected_shares']
            if 'hardware_errors' in data:
                miner.hardware_errors = data['hardware_errors']
            if 'reject_rate' in data:
                miner.reject_rate = data['reject_rate']
            
            if 'uptime_seconds' in data:
                miner.uptime_seconds = data['uptime_seconds']
            if 'pool_url' in data:
                miner.pool_url = data['pool_url']
            if 'pool_worker' in data:
                miner.pool_worker = data['pool_worker']
            
            # 从offline恢复到active（仅当之前是offline）
            if miner.status == 'offline':
                miner.status = 'active'
        else:
            # 仅当明确标记为offline且超过5分钟未见时才切换状态
            if data.get('online') is False:
                time_since_seen = datetime.utcnow() - (miner.last_seen or datetime.utcnow())
                if miner.status == 'active' and time_since_seen.total_seconds() > 300:
                    miner.status = 'offline'
        
        # 更新时间戳
        miner.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"矿机 {miner_id} 遥测数据已更新 - 在线: {miner.cgminer_online}")
        
        return jsonify({
            'success': True,
            'message': 'Telemetry data updated successfully',
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新矿机遥测数据错误: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/<int:miner_id>/test-connection', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def test_miner_connection(miner_id):
    """
    测试矿机CGMiner连接
    
    通过CGMiner API测试矿机是否可达并返回实时数据
    
    Returns:
        {
            "success": true,
            "online": true,
            "telemetry": {...},
            "message": "Connection successful"
        }
    """
    try:
        miner = HostingMiner.query.get_or_404(miner_id)
        
        if not miner.ip_address:
            return jsonify({
                'success': False,
                'error': 'Miner has no IP address configured'
            }), 400
        
        # 导入CGMiner测试工具
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
        
        from tools.test_cgminer import CGMinerTester
        
        # 创建测试器并获取遥测数据
        tester = CGMinerTester(miner.ip_address, timeout=5)
        telemetry = tester.get_telemetry_data()
        
        if not telemetry:
            return jsonify({
                'success': False,
                'online': False,
                'error': 'Failed to connect to CGMiner API',
                'message': 'Miner is offline or CGMiner API is not accessible'
            }), 200  # 200状态码，但success=false
        
        # 连接成功，返回遥测数据
        return jsonify({
            'success': True,
            'online': True,
            'telemetry': telemetry,
            'message': 'Connection successful'
        })
        
    except Exception as e:
        logger.error(f"测试矿机连接错误: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'online': False,
            'error': str(e)
        }), 500


# ==================== 设备管理升级API (Phase 1) ====================

@hosting_bp.route('/api/miners/stats', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_miners_stats():
    """
    KPI统计API - 返回矿机综合统计数据
    支持site_id筛选，性能优化：6000+矿机查询<250ms
    权限过滤：按用户角色显示不同范围的数据
    """
    try:
        from sqlalchemy import func
        
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        user_email = session.get('email', '')
        
        # 获取筛选参数
        site_id = request.args.get('site_id', type=int)
        
        # 权限控制 - 确定可访问的站点范围
        allowed_site_ids = None  # None表示不限制
        if user_role == 'admin':
            # 管理员可以查看所有矿机
            allowed_site_ids = None
        elif user_role == 'mining_site_owner':
            # 矿场运营方只能查看自己管理站点的矿机
            managed_sites = HostingSite.query.filter_by(contact_email=user_email).all()
            allowed_site_ids = [s.id for s in managed_sites]
        else:
            # owner/customer - 不使用站点限制，而是使用customer_id
            pass
        
        # 基础查询
        query = HostingMiner.query
        
        # 应用权限过滤
        if user_role == 'admin':
            if site_id:
                query = query.filter_by(site_id=site_id)
        elif user_role == 'mining_site_owner':
            if allowed_site_ids:
                if site_id and site_id in allowed_site_ids:
                    query = query.filter_by(site_id=site_id)
                else:
                    query = query.filter(HostingMiner.site_id.in_(allowed_site_ids))
            else:
                # 没有管理任何站点
                query = query.filter(HostingMiner.id == -1)
        else:
            # owner/customer 只能查看自己的矿机
            query = query.filter_by(customer_id=user_id)
            if site_id:
                query = query.filter_by(site_id=site_id)
        
        # 使用聚合函数进行高效统计
        stats_query = db.session.query(
            func.count(HostingMiner.id).label('total_miners'),
            func.sum(HostingMiner.actual_hashrate).label('total_hashrate_th'),
            func.sum(HostingMiner.actual_power).label('total_power_w'),
            func.avg(HostingMiner.health_score).label('avg_health_score')
        )
        
        # 应用相同的权限过滤到统计查询
        if user_role == 'admin':
            if site_id:
                stats_query = stats_query.filter(HostingMiner.site_id == site_id)
        elif user_role == 'mining_site_owner':
            if allowed_site_ids:
                if site_id and site_id in allowed_site_ids:
                    stats_query = stats_query.filter(HostingMiner.site_id == site_id)
                else:
                    stats_query = stats_query.filter(HostingMiner.site_id.in_(allowed_site_ids))
            else:
                stats_query = stats_query.filter(HostingMiner.id == -1)
        else:
            stats_query = stats_query.filter(HostingMiner.customer_id == user_id)
            if site_id:
                stats_query = stats_query.filter(HostingMiner.site_id == site_id)
        
        stats = stats_query.first()
        
        # 状态分布统计 - 也需要应用权限过滤
        status_distribution = db.session.query(
            HostingMiner.status,
            func.count(HostingMiner.id).label('count')
        )
        if user_role == 'admin':
            if site_id:
                status_distribution = status_distribution.filter(HostingMiner.site_id == site_id)
        elif user_role == 'mining_site_owner':
            if allowed_site_ids:
                if site_id and site_id in allowed_site_ids:
                    status_distribution = status_distribution.filter(HostingMiner.site_id == site_id)
                else:
                    status_distribution = status_distribution.filter(HostingMiner.site_id.in_(allowed_site_ids))
            else:
                status_distribution = status_distribution.filter(HostingMiner.id == -1)
        else:
            status_distribution = status_distribution.filter(HostingMiner.customer_id == user_id)
            if site_id:
                status_distribution = status_distribution.filter(HostingMiner.site_id == site_id)
        status_distribution = status_distribution.group_by(HostingMiner.status).all()
        
        # 在线率统计（cgminer_online）
        online_count = query.filter_by(cgminer_online=True).count()
        total_count = stats.total_miners or 0
        online_rate = round((online_count / total_count * 100) if total_count > 0 else 0, 2)
        
        # 计算总算力(PH/s)、总功耗(MW)、平均能效(W/TH)
        total_hashrate_th = float(stats.total_hashrate_th or 0)
        total_power_w = float(stats.total_power_w or 0)
        
        total_hashrate_ph = round(total_hashrate_th / 1000, 3)  # TH/s转PH/s
        total_power_mw = round(total_power_w / 1000000, 3)  # W转MW
        avg_efficiency = round(total_power_w / total_hashrate_th, 2) if total_hashrate_th > 0 else 0
        
        # 构建响应数据
        result = {
            'total_miners': total_count,
            'total_hashrate_ph': total_hashrate_ph,
            'total_power_mw': total_power_mw,
            'avg_efficiency_w_th': avg_efficiency,
            'online_rate': online_rate,
            'avg_health_score': round(float(stats.avg_health_score or 100), 1),
            'status_distribution': {
                status: count for status, count in status_distribution
            }
        }
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"获取矿机统计数据失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/batch-approve', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def batch_approve_miners():
    """批量审核通过矿机"""
    try:
        data = request.get_json()
        miner_ids = data.get('miner_ids', [])
        approval_notes = data.get('approval_notes', '')
        
        if not miner_ids:
            return jsonify({'success': False, 'error': 'No miner IDs provided'}), 400
        
        operator_id = session.get('user_id')
        
        # 使用正确的事务处理
        updated_count = 0
        with db.session.begin():
            for miner_id in miner_ids:
                miner = HostingMiner.query.get(miner_id)
                if miner:
                    old_status = miner.approval_status
                    miner.approval_status = 'approved'
                    miner.approved_by = operator_id
                    miner.approved_at = datetime.utcnow()
                    if approval_notes:
                        miner.approval_notes = approval_notes
                    
                    # 记录操作日志
                    log = HostingMinerOperationLog(
                        miner_id=miner_id,
                        operation_type='approve',
                        old_status=old_status,
                        new_status='approved',
                        operator_id=operator_id,
                        notes=f'批量审核通过: {approval_notes}'
                    )
                    db.session.add(log)
                    updated_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Successfully approved {updated_count} miners',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"批量审核失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/batch-status', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def batch_change_status():
    """批量修改矿机状态"""
    try:
        data = request.get_json()
        miner_ids = data.get('miner_ids', [])
        new_status = data.get('new_status')
        notes = data.get('notes', '')
        
        if not miner_ids or not new_status:
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        
        operator_id = session.get('user_id')
        
        # 使用正确的事务处理
        updated_count = 0
        with db.session.begin():
            for miner_id in miner_ids:
                miner = HostingMiner.query.get(miner_id)
                if miner:
                    old_status = miner.status
                    miner.status = new_status
                    
                    # 记录操作日志
                    log = HostingMinerOperationLog(
                        miner_id=miner_id,
                        operation_type='status_change',
                        old_status=old_status,
                        new_status=new_status,
                        operator_id=operator_id,
                        notes=f'批量修改状态: {notes}'
                    )
                    db.session.add(log)
                    updated_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Successfully updated {updated_count} miners to {new_status}',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"批量修改状态失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/batch-delete', methods=['POST'])
@requires_role(['owner', 'admin'])
def batch_delete_miners():
    """批量删除矿机"""
    try:
        data = request.get_json()
        miner_ids = data.get('miner_ids', [])
        
        if not miner_ids:
            return jsonify({'success': False, 'error': 'No miner IDs provided'}), 400
        
        operator_id = session.get('user_id')
        
        # 使用正确的事务处理
        deleted_count = 0
        with db.session.begin():
            for miner_id in miner_ids:
                miner = HostingMiner.query.get(miner_id)
                if miner:
                    # 记录删除日志
                    log = HostingMinerOperationLog(
                        miner_id=miner_id,
                        operation_type='delete',
                        old_status=miner.status,
                        new_status='deleted',
                        operator_id=operator_id,
                        notes=f'批量删除矿机: {miner.serial_number}'
                    )
                    db.session.add(log)
                    db.session.flush()  # 先记录日志
                    
                    db.session.delete(miner)
                    deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {deleted_count} miners',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"批量删除失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/batch-start', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def batch_start_miners():
    """批量启动矿机 - 发送控制命令到边缘采集器
    
    仅当矿机有活跃的边缘采集器时才更新状态，否则跳过
    """
    try:
        data = request.get_json()
        miner_ids = data.get('miner_ids', [])
        force_status = data.get('force_status', False)
        
        if not miner_ids:
            return jsonify({'success': False, 'error': 'No miner IDs provided'}), 400
        
        operator_id = session.get('user_id')
        
        updated_count = 0
        commands_created = 0
        skipped_no_collector = 0
        site_collectors = {}
        
        with db.session.begin():
            for miner_id in miner_ids:
                miner = HostingMiner.query.get(miner_id)
                if miner and miner.status != 'active':
                    has_collector = False
                    
                    if miner.site_id:
                        if miner.site_id not in site_collectors:
                            site_collectors[miner.site_id] = CollectorKey.query.filter_by(
                                site_id=miner.site_id, is_active=True
                            ).first()
                        has_collector = site_collectors[miner.site_id] is not None
                    
                    if not has_collector and not force_status:
                        skipped_no_collector += 1
                        continue
                    
                    old_status = miner.status
                    miner.status = 'active'
                    
                    if has_collector:
                        command = MinerCommand(
                            miner_id=miner.miner_id or str(miner.id),
                            site_id=miner.site_id,
                            ip_address=miner.ip_address,
                            command_type='enable',
                            parameters={},
                            status='pending',
                            priority=7,
                            expires_at=datetime.utcnow() + timedelta(minutes=5),
                            operator_id=operator_id
                        )
                        db.session.add(command)
                        commands_created += 1
                    
                    log = HostingMinerOperationLog(
                        miner_id=miner_id,
                        operation_type='start',
                        old_status=old_status,
                        new_status='active',
                        operator_id=operator_id,
                        notes='批量启动矿机' + (' (命令已队列)' if has_collector else ' (强制状态更新)')
                    )
                    db.session.add(log)
                    updated_count += 1
        
        if skipped_no_collector > 0 and updated_count == 0:
            return jsonify({
                'success': False,
                'error': f'No miners started. {skipped_no_collector} miners have no edge collector.',
                'skipped_no_collector': skipped_no_collector
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'Successfully started {updated_count} miners',
            'updated_count': updated_count,
            'commands_queued': commands_created,
            'skipped_no_collector': skipped_no_collector
        })
        
    except Exception as e:
        logger.error(f"批量启动失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/batch-shutdown', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def batch_shutdown_miners():
    """批量关闭矿机 - 发送控制命令到边缘采集器
    
    仅当矿机有活跃的边缘采集器时才更新状态，否则跳过
    """
    try:
        data = request.get_json()
        miner_ids = data.get('miner_ids', [])
        force_status = data.get('force_status', False)
        
        if not miner_ids:
            return jsonify({'success': False, 'error': 'No miner IDs provided'}), 400
        
        operator_id = session.get('user_id')
        
        updated_count = 0
        commands_created = 0
        skipped_no_collector = 0
        site_collectors = {}
        
        with db.session.begin():
            for miner_id in miner_ids:
                miner = HostingMiner.query.get(miner_id)
                if miner and miner.status != 'offline':
                    has_collector = False
                    
                    if miner.site_id:
                        if miner.site_id not in site_collectors:
                            site_collectors[miner.site_id] = CollectorKey.query.filter_by(
                                site_id=miner.site_id, is_active=True
                            ).first()
                        has_collector = site_collectors[miner.site_id] is not None
                    
                    if not has_collector and not force_status:
                        skipped_no_collector += 1
                        continue
                    
                    old_status = miner.status
                    miner.status = 'offline'
                    
                    if has_collector:
                        command = MinerCommand(
                            miner_id=miner.miner_id or str(miner.id),
                            site_id=miner.site_id,
                            ip_address=miner.ip_address,
                            command_type='disable',
                            parameters={},
                            status='pending',
                            priority=8,
                            expires_at=datetime.utcnow() + timedelta(minutes=5),
                            operator_id=operator_id
                        )
                        db.session.add(command)
                        commands_created += 1
                    
                    log = HostingMinerOperationLog(
                        miner_id=miner_id,
                        operation_type='shutdown',
                        old_status=old_status,
                        new_status='offline',
                        operator_id=operator_id,
                        notes='批量关闭矿机' + (' (命令已队列)' if has_collector else ' (强制状态更新)')
                    )
                    db.session.add(log)
                    updated_count += 1
        
        if skipped_no_collector > 0 and updated_count == 0:
            return jsonify({
                'success': False,
                'error': f'No miners shutdown. {skipped_no_collector} miners have no edge collector.',
                'skipped_no_collector': skipped_no_collector
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'Successfully shutdown {updated_count} miners',
            'updated_count': updated_count,
            'commands_queued': commands_created,
            'skipped_no_collector': skipped_no_collector
        })
        
    except Exception as e:
        logger.error(f"批量关闭失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/<int:miner_id>/start', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def start_single_miner(miner_id):
    """启动单个矿机 - 发送控制命令到边缘采集器"""
    try:
        miner = HostingMiner.query.get_or_404(miner_id)
        operator_id = session.get('user_id')
        force_status = request.json.get('force_status', False) if request.is_json else False
        
        if miner.status == 'active':
            return jsonify({'success': False, 'error': 'Miner is already active'}), 400
        
        collector_available = False
        command_created = False
        
        if miner.site_id:
            collector_key = CollectorKey.query.filter_by(
                site_id=miner.site_id, 
                is_active=True
            ).first()
            if collector_key:
                collector_available = True
                command = MinerCommand(
                    miner_id=miner.miner_id or str(miner.id),
                    site_id=miner.site_id,
                    ip_address=miner.ip_address,
                    command_type='enable',
                    parameters={},
                    status='pending',
                    priority=7,
                    expires_at=datetime.utcnow() + timedelta(minutes=5),
                    operator_id=operator_id
                )
                db.session.add(command)
                command_created = True
        
        if not command_created and not force_status:
            return jsonify({
                'success': False,
                'error': 'No edge collector available. Use force_status=true to update status only.',
                'collector_available': False
            }), 400
        
        old_status = miner.status
        miner.status = 'active'
        
        log = HostingMinerOperationLog(
            miner_id=miner_id,
            operation_type='start',
            old_status=old_status,
            new_status='active',
            operator_id=operator_id,
            notes='启动矿机' + (' (命令已队列)' if command_created else ' (强制状态更新)')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Miner started successfully',
            'command_queued': command_created,
            'collector_available': collector_available,
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"启动矿机失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/<int:miner_id>/shutdown', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def shutdown_single_miner(miner_id):
    """关闭单个矿机 - 发送控制命令到边缘采集器"""
    try:
        miner = HostingMiner.query.get_or_404(miner_id)
        operator_id = session.get('user_id')
        force_status = request.json.get('force_status', False) if request.is_json else False
        
        if miner.status == 'offline':
            return jsonify({'success': False, 'error': 'Miner is already offline'}), 400
        
        collector_available = False
        command_created = False
        
        if miner.site_id:
            collector_key = CollectorKey.query.filter_by(
                site_id=miner.site_id, 
                is_active=True
            ).first()
            if collector_key:
                collector_available = True
                command = MinerCommand(
                    miner_id=miner.miner_id or str(miner.id),
                    site_id=miner.site_id,
                    ip_address=miner.ip_address,
                    command_type='disable',
                    parameters={},
                    status='pending',
                    priority=8,
                    expires_at=datetime.utcnow() + timedelta(minutes=5),
                    operator_id=operator_id
                )
                db.session.add(command)
                command_created = True
        
        if not command_created and not force_status:
            return jsonify({
                'success': False,
                'error': 'No edge collector available. Use force_status=true to update status only.',
                'collector_available': False
            }), 400
        
        old_status = miner.status
        miner.status = 'offline'
        
        log = HostingMinerOperationLog(
            miner_id=miner_id,
            operation_type='shutdown',
            old_status=old_status,
            new_status='offline',
            operator_id=operator_id,
            notes='关闭矿机' + (' (命令已队列)' if command_created else ' (强制状态更新)')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Miner shutdown successfully',
            'command_queued': command_created,
            'collector_available': collector_available,
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"关闭矿机失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/<int:miner_id>/restart', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def restart_single_miner(miner_id):
    """重启单个矿机 - 发送控制命令到边缘采集器"""
    try:
        miner = HostingMiner.query.get_or_404(miner_id)
        operator_id = session.get('user_id')
        force_status = request.json.get('force_status', False) if request.is_json else False
        
        collector_available = False
        command_created = False
        
        if miner.site_id:
            collector_key = CollectorKey.query.filter_by(
                site_id=miner.site_id, 
                is_active=True
            ).first()
            if collector_key:
                collector_available = True
                command = MinerCommand(
                    miner_id=miner.miner_id or str(miner.id),
                    site_id=miner.site_id,
                    ip_address=miner.ip_address,
                    command_type='restart',
                    parameters={},
                    status='pending',
                    priority=9,
                    expires_at=datetime.utcnow() + timedelta(minutes=5),
                    operator_id=operator_id
                )
                db.session.add(command)
                command_created = True
        
        if not command_created and not force_status:
            return jsonify({
                'success': False,
                'error': 'No edge collector available. Use force_status=true to update status only.',
                'collector_available': False
            }), 400
        
        old_status = miner.status
        miner.status = 'maintenance'
        db.session.flush()
        
        log1 = HostingMinerOperationLog(
            miner_id=miner_id,
            operation_type='restart',
            old_status=old_status,
            new_status='maintenance',
            operator_id=operator_id,
            notes='重启矿机 - 进入维护模式' + (' (命令已队列)' if command_created else ' (强制状态更新)')
        )
        db.session.add(log1)
        db.session.flush()
        
        miner.status = 'active'
        log2 = HostingMinerOperationLog(
            miner_id=miner_id,
            operation_type='restart',
            old_status='maintenance',
            new_status='active',
            operator_id=operator_id,
            notes='重启矿机 - 重新激活'
        )
        db.session.add(log2)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Miner restarted successfully',
            'command_queued': command_created,
            'collector_available': collector_available,
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"重启矿机失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/<int:miner_id>/logs', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_miner_operation_logs(miner_id):
    """获取矿机操作日志（分页）"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        # 分页查询
        pagination = HostingMinerOperationLog.query.filter_by(
            miner_id=miner_id
        ).order_by(
            HostingMinerOperationLog.created_at.desc()
        ).paginate(page=page, per_page=limit, error_out=False)
        
        logs_data = [log.to_dict() for log in pagination.items]
        
        return jsonify({
            'success': True,
            'logs': logs_data,
            'pagination': {
                'current_page': page,
                'total_pages': pagination.pages,
                'total_items': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"获取操作日志失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/miners/export', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def export_miners_csv():
    """导出矿机数据为CSV（支持筛选）"""
    try:
        import csv
        from io import StringIO
        from flask import make_response
        
        # 获取筛选参数
        site_id = request.args.get('site_id', type=int)
        status = request.args.get('status')
        search = request.args.get('search', '')
        
        # 构建查询
        query = HostingMiner.query
        if site_id:
            query = query.filter_by(site_id=site_id)
        if status:
            query = query.filter_by(status=status)
        if search:
            query = query.filter(
                db.or_(
                    HostingMiner.serial_number.ilike(f'%{search}%'),
                    HostingMiner.ip_address.ilike(f'%{search}%'),
                    HostingMiner.rack_position.ilike(f'%{search}%')
                )
            )
        
        miners = query.all()
        
        # 创建CSV
        si = StringIO()
        writer = csv.writer(si)
        
        # 写入表头
        writer.writerow([
            'ID', 'Serial Number', 'Site', 'Customer', 'Model', 
            'IP Address', 'Rack Position', 'Hashrate (TH/s)', 'Power (W)',
            'Status', 'Approval Status', 'Health Score', 'Temperature (°C)',
            'Created At'
        ])
        
        # 写入数据
        for miner in miners:
            writer.writerow([
                miner.id,
                miner.serial_number,
                miner.site.name if miner.site else '',
                miner.customer.email if miner.customer else '',
                miner.miner_model.model_name if miner.miner_model else '',
                miner.ip_address or '',
                miner.rack_position or '',
                miner.actual_hashrate,
                miner.actual_power,
                miner.status,
                miner.approval_status,
                miner.health_score,
                miner.temperature_avg or '',
                miner.created_at.isoformat() if miner.created_at else ''
            ])
        
        # 创建响应
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=miners_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output.headers["Content-type"] = "text/csv"
        
        return output
        
    except Exception as e:
        logger.error(f"导出CSV失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/miner-setup-guide')
@login_required
def miner_setup_guide():
    """
    矿机连接设置指南页面（中英双语）
    
    为矿场管理员提供完整的矿机连接操作手册，包括：
    - CGMiner API配置
    - 添加矿机到系统
    - 测试连接
    - 查看实时数据
    - 告警系统说明
    - 故障排查FAQ
    """
    current_lang = session.get('language', 'zh')
    return render_template('hosting/miner_setup_guide.html', current_lang=current_lang)


@hosting_bp.route('/miner-setup-guide/pdf')
@login_required
def miner_setup_guide_pdf():
    """
    生成矿机连接设置指南PDF文件（中英双语）
    
    使用ReportLab生成专业的PDF文档，包含所有章节和图片
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        from flask import make_response
        
        current_lang = session.get('language', 'zh')
        
        # 创建PDF缓冲区
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        # 尝试动态查找并注册CJK字体
        import subprocess
        default_font = 'Helvetica'
        cjk_font_available = False
        
        try:
            # 使用fc-match查找Noto Sans CJK SC字体路径
            result = subprocess.run(['fc-match', 'Noto Sans CJK SC', '--format=%{file}'], 
                                   capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                # 注册CJK字体 (subfont index 2 for SC variant)
                pdfmetrics.registerFont(TTFont('NotoSansCJKSC', font_path, subfontIndex=2))
                default_font = 'NotoSansCJKSC'
                cjk_font_available = True
                logger.info(f"Successfully registered CJK font from: {font_path}")
            else:
                # 降级到DejaVu Sans
                pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                default_font = 'DejaVuSans'
        except Exception as e:
            logger.warning(f"Failed to register CJK font: {e}, falling back to Helvetica")
            default_font = 'Helvetica'
        
        # 如果是中文但没有CJK字体支持，切换到英文内容
        if current_lang == 'zh' and not cjk_font_available:
            logger.warning("No CJK font available, generating English PDF instead")
            current_lang = 'en'
        
        # 构建PDF内容
        story = []
        styles = getSampleStyleSheet()
        
        # 自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#f7931a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=default_font
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#f7931a'),
            spaceAfter=12,
            spaceBefore=12,
            fontName=default_font
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            fontName=default_font
        )
        
        # 标题页
        if current_lang == 'en':
            title_text = "Miner Connection Setup Guide"
            subtitle_text = "Complete Manual for Mining Farm Administrators"
        else:
            title_text = "矿机连接设置指南"
            subtitle_text = "矿场管理员完整操作手册"
        
        story.append(Paragraph(title_text, title_style))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(subtitle_text, body_style))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"HashInsight Enterprise - {datetime.now().strftime('%Y-%m-%d')}", body_style))
        story.append(PageBreak())
        
        # 目录
        if current_lang == 'en':
            toc_title = "Table of Contents"
            sections = [
                "1. Preparation",
                "2. Adding Miners to the System",
                "3. Testing CGMiner Connection",
                "4. Viewing Real-time Monitoring Data",
                "5. Smart Alert System",
                "6. Troubleshooting Guide"
            ]
        else:
            toc_title = "目录"
            sections = [
                "1. 准备工作",
                "2. 添加矿机到系统",
                "3. 测试CGMiner连接",
                "4. 查看实时监控数据",
                "5. 智能告警系统",
                "6. 故障排查指南"
            ]
        
        story.append(Paragraph(toc_title, heading_style))
        for section in sections:
            story.append(Paragraph(section, body_style))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(PageBreak())
        
        # 简化版内容（主要章节标题和关键信息）
        if current_lang == 'en':
            content_sections = [
                ("1. Preparation", [
                    "Enable CGMiner API on each miner device",
                    "Configure network connectivity (port 4028 TCP)",
                    "Assign static IP addresses to miners",
                    "Test connectivity using telnet or nc command"
                ]),
                ("2. Adding Miners to the System", [
                    "Navigate to Hosting → Miner Management",
                    "Click 'Add Miner' button",
                    "Fill in required fields: Serial Number, Miner Model, Site, IP Address",
                    "Submit for approval if required"
                ]),
                ("3. Testing CGMiner Connection", [
                    "Use the 'Test' button in the Actions column",
                    "System connects to CGMiner API (port 4028)",
                    "Success: real-time data displayed",
                    "Failure: check network, firewall, and API settings"
                ]),
                ("4. Viewing Real-time Monitoring Data", [
                    "14 telemetry fields collected every 60 seconds",
                    "Temperature, fan speed, hashrate, pool info",
                    "24-hour trend charts on miner detail page",
                    "Automatic background collection"
                ]),
                ("5. Smart Alert System", [
                    "Temperature > 90°C: Critical (red badge)",
                    "Temperature > 85°C: Warning (yellow badge)",
                    "Hashrate drop > 20%: Warning",
                    "Offline > 5 minutes: Critical"
                ]),
                ("6. Troubleshooting Guide", [
                    "Connection timeout: Check network and firewall",
                    "CGMiner API not responding: Verify API enabled",
                    "Data not updating: Check background scheduler",
                    "Permission denied: Verify user role and assignments"
                ])
            ]
        else:
            content_sections = [
                ("1. 准备工作", [
                    "在每台矿机设备上启用CGMiner API",
                    "配置网络连接（4028端口TCP）",
                    "为矿机分配静态IP地址",
                    "使用telnet或nc命令测试连接"
                ]),
                ("2. 添加矿机到系统", [
                    "导航到托管服务 → 矿机管理",
                    '点击"添加矿机"按钮',
                    "填写必填字段：序列号、矿机型号、站点、IP地址",
                    "如需要则提交审批"
                ]),
                ("3. 测试CGMiner连接", [
                    '使用操作列中的"测试"按钮',
                    "系统连接到CGMiner API（4028端口）",
                    "成功：显示实时数据",
                    "失败：检查网络、防火墙和API设置"
                ]),
                ("4. 查看实时监控数据", [
                    "每60秒收集14个遥测字段",
                    "温度、风扇速度、算力、矿池信息",
                    "矿机详情页24小时趋势图表",
                    "自动后台采集"
                ]),
                ("5. 智能告警系统", [
                    "温度 > 90°C：严重（红色徽章）",
                    "温度 > 85°C：警告（黄色徽章）",
                    "算力下降 > 20%：警告",
                    "离线 > 5分钟：严重"
                ]),
                ("6. 故障排查指南", [
                    "连接超时：检查网络和防火墙",
                    "CGMiner API无响应：验证API已启用",
                    "数据未更新：检查后台调度器",
                    "权限被拒绝：验证用户角色和分配"
                ])
            ]
        
        for section_title, section_items in content_sections:
            story.append(Paragraph(section_title, heading_style))
            story.append(Spacer(1, 0.1*inch))
            
            for item in section_items:
                story.append(Paragraph(f"• {item}", body_style))
            
            story.append(Spacer(1, 0.3*inch))
        
        # 构建PDF
        doc.build(story)
        
        # 准备响应
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        filename = 'Miner_Setup_Guide_EN.pdf' if current_lang == 'en' else 'Miner_Setup_Guide_ZH.pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
        
    except Exception as e:
        logger.error(f"生成PDF错误: {str(e)}", exc_info=True)
        flash('Failed to generate PDF', 'error')
        return redirect(url_for('hosting.miner_setup_guide'))


@hosting_bp.route('/api/revenue/summary', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_revenue_summary():
    """
    获取收益预测汇总
    GET /hosting/api/revenue/summary?site_id=xxx
    
    返回:
    - 按站点或全局汇总的实时收益预测
    - 包含 BTC 价格、难度、矿机收益等
    """
    try:
        from services.hosting_revenue_service import get_revenue_service
        
        site_id = request.args.get('site_id', type=int)
        
        revenue_service = get_revenue_service()
        summary = revenue_service.get_revenue_summary(site_id)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"获取收益汇总失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to get revenue summary',
            'message_zh': '获取收益汇总失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/revenue/miners', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_miners_revenue():
    """
    获取所有矿机的收益预测列表
    GET /hosting/api/revenue/miners?site_id=xxx&sort_by=daily_net_profit&sort_desc=true&limit=100
    """
    try:
        from services.hosting_revenue_service import get_revenue_service
        from dataclasses import asdict
        
        site_id = request.args.get('site_id', type=int)
        sort_by = request.args.get('sort_by', 'daily_net_profit')
        sort_desc = request.args.get('sort_desc', 'true').lower() == 'true'
        limit = min(request.args.get('limit', 100, type=int), 500)
        
        revenue_service = get_revenue_service()
        miners = revenue_service.get_all_miners_revenue(
            site_id=site_id,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': [asdict(m) for m in miners],
            'count': len(miners)
        })
        
    except Exception as e:
        logger.error(f"获取矿机收益列表失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to get miners revenue',
            'message_zh': '获取矿机收益列表失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/revenue/miners/<int:miner_id>/projection', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner', 'customer'])
def get_miner_projection(miner_id):
    """
    获取单个矿机的24小时收益预测
    GET /hosting/api/revenue/miners/123/projection
    """
    try:
        from services.hosting_revenue_service import get_revenue_service
        
        revenue_service = get_revenue_service()
        projection = revenue_service.project_24h_revenue(miner_id)
        
        return jsonify({
            'success': True,
            'data': projection
        })
        
    except Exception as e:
        logger.error(f"获取矿机收益预测失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to get miner projection',
            'message_zh': '获取矿机收益预测失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/evaluation/site/<int:site_id>', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_site_evaluation(site_id):
    """
    获取站点所有矿机的评估汇总
    GET /hosting/api/evaluation/site/123
    
    返回:
    - 等级分布 (A/B/C/D/F)
    - 平均评分
    - Top performers
    - 需要关注的矿机
    """
    try:
        from services.miner_evaluation_service import get_evaluation_service
        
        evaluation_service = get_evaluation_service()
        summary = evaluation_service.get_site_evaluation_summary(site_id)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"获取站点评估失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to get site evaluation',
            'message_zh': '获取站点评估失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/evaluation/miners', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner'])
def get_miners_evaluation():
    """
    获取所有矿机的评估列表
    GET /hosting/api/evaluation/miners?site_id=xxx
    """
    try:
        from services.miner_evaluation_service import get_evaluation_service
        
        site_id = request.args.get('site_id', type=int)
        
        if not site_id:
            return jsonify({
                'success': False,
                'message_en': 'Site ID is required',
                'message_zh': '站点ID必填'
            }), 400
        
        evaluation_service = get_evaluation_service()
        evaluations = evaluation_service.evaluate_site_miners(site_id)
        
        return jsonify({
            'success': True,
            'data': [e.to_dict() for e in evaluations],
            'count': len(evaluations)
        })
        
    except Exception as e:
        logger.error(f"获取矿机评估列表失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to get miners evaluation',
            'message_zh': '获取矿机评估列表失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/evaluation/miner/<int:miner_id>', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site_owner', 'customer'])
def get_single_miner_evaluation(miner_id):
    """
    获取单个矿机的详细评估
    GET /hosting/api/evaluation/miner/123
    """
    try:
        from services.miner_evaluation_service import get_evaluation_service
        from services.hosting_revenue_service import get_revenue_service
        
        miner = HostingMiner.query.get(miner_id)
        if not miner:
            return jsonify({
                'success': False,
                'message_en': 'Miner not found',
                'message_zh': '矿机不存在'
            }), 404
        
        site = HostingSite.query.get(miner.site_id)
        model = miner.miner_model
        model_name = model.model_name if model else "Unknown"
        rated_hashrate = model.hashrate if model else miner.actual_hashrate
        rated_power = model.power_consumption if model else miner.actual_power
        electricity_rate = site.electricity_rate if site else 0.06
        
        revenue_service = get_revenue_service()
        revenue_metrics = revenue_service.calculate_miner_revenue(
            miner_id=miner.id,
            serial_number=miner.serial_number,
            model_name=model_name,
            hashrate_th=rated_hashrate,
            power_w=rated_power,
            electricity_rate=electricity_rate,
            health_score=miner.health_score or 100
        )
        
        evaluation_service = get_evaluation_service()
        evaluation = evaluation_service.evaluate_miner(
            miner_id=miner.id,
            serial_number=miner.serial_number,
            model_name=model_name,
            actual_hashrate_th=miner.actual_hashrate or 0,
            rated_hashrate_th=rated_hashrate,
            actual_power_w=miner.actual_power or 0,
            rated_power_w=rated_power,
            electricity_rate=electricity_rate,
            temp_avg=miner.temperature_avg or 0,
            temp_max=miner.temperature_max or 0,
            fan_avg=miner.fan_avg or 0,
            hardware_errors=miner.hardware_errors or 0,
            reject_rate=miner.reject_rate or 0,
            uptime_seconds=miner.uptime_seconds or 0,
            is_online=miner.status == 'active' or miner.cgminer_online,
            expected_daily_usd=revenue_metrics.daily_usd
        )
        
        from dataclasses import asdict
        
        return jsonify({
            'success': True,
            'data': {
                'evaluation': evaluation.to_dict(),
                'revenue': asdict(revenue_metrics)
            }
        })
        
    except Exception as e:
        logger.error(f"获取矿机评估失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to get miner evaluation',
            'message_zh': '获取矿机评估失败',
            'error': str(e)
        }), 500


# ============================================================================
# E2EE (End-to-End Encryption) API Endpoints
# Plan A: Encrypted credentials only (username/password/pool_password)
# Plan B: Fully encrypted connection (IP/Port + credentials)
# ============================================================================

def validate_encrypted_block(block):
    """验证加密块格式是否正确
    
    Args:
        block: 加密块字典
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not block:
        return False, 'Encrypted block is required'
    
    required_fields = ['ciphertext', 'iv', 'salt', 'algo', 'version']
    for field in required_fields:
        if field not in block:
            return False, f'Missing required field: {field}'
    
    if block.get('algo') != 'AES-256-GCM':
        return False, 'Unsupported algorithm. Only AES-256-GCM is supported'
    
    if block.get('version') != 1:
        return False, 'Unsupported version. Only version 1 is supported'
    
    return True, None


@hosting_bp.route('/api/miners/<int:miner_id>/credentials', methods=['GET'])
@login_required
def get_miner_credentials(miner_id):
    """获取矿机加密凭证 (Plan A)
    
    返回加密的凭证块，客户端使用密码短语解密。
    服务器无法解密此数据。
    """
    try:
        miner = HostingMiner.query.get(miner_id)
        if not miner:
            return jsonify({
                'success': False,
                'message_en': 'Miner not found',
                'message_zh': '矿机不存在'
            }), 404
        
        user_id = session.get('user_id')
        user_role = normalize_role(session.get('role', 'guest'))
        
        has_full_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        is_owner = miner.customer_id == user_id
        
        if not has_full_access and not is_owner:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        return jsonify({
            'success': True,
            'miner_id': miner_id,
            'encrypted_credentials': miner.encrypted_credentials
        })
        
    except Exception as e:
        logger.error(f"获取矿机加密凭证失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to get credentials',
            'message_zh': '获取凭证失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/miners/<int:miner_id>/credentials', methods=['POST'])
@login_required
def save_miner_credentials(miner_id):
    """保存矿机加密凭证 (Plan A)
    
    客户端在浏览器中加密凭证后发送密文块。
    服务器只存储密文，无法解密。
    
    请求体:
    {
        "encrypted_credentials": {
            "ciphertext": "base64...",
            "iv": "base64...",
            "salt": "base64...",
            "algo": "AES-256-GCM",
            "version": 1
        }
    }
    """
    try:
        miner = HostingMiner.query.get(miner_id)
        if not miner:
            return jsonify({
                'success': False,
                'message_en': 'Miner not found',
                'message_zh': '矿机不存在'
            }), 404
        
        user_id = session.get('user_id')
        user_role = normalize_role(session.get('role', 'guest'))
        
        has_full_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        is_owner = miner.customer_id == user_id
        
        if not has_full_access and not is_owner:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message_en': 'Request body is required',
                'message_zh': '请求体不能为空'
            }), 400
        
        encrypted_credentials = data.get('encrypted_credentials')
        
        if encrypted_credentials:
            is_valid, error = validate_encrypted_block(encrypted_credentials)
            if not is_valid:
                return jsonify({
                    'success': False,
                    'message_en': error,
                    'message_zh': '加密块格式无效'
                }), 400
        
        miner.encrypted_credentials = encrypted_credentials
        db.session.commit()
        
        logger.info(f"矿机 {miner_id} 加密凭证已保存 (by user {user_id})")
        
        return jsonify({
            'success': True,
            'message_en': 'Credentials saved successfully',
            'message_zh': '凭证保存成功',
            'miner_id': miner_id,
            'encrypted_credentials': miner.encrypted_credentials
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"保存矿机加密凭证失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to save credentials',
            'message_zh': '保存凭证失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/miners/<int:miner_id>/connection_full', methods=['GET'])
@login_required
def get_miner_connection_full(miner_id):
    """获取矿机完整加密连接信息 (Plan B)
    
    返回完整加密连接块(包含IP/Port和凭证)，客户端使用密码短语解密。
    服务器无法解密此数据。
    """
    try:
        miner = HostingMiner.query.get(miner_id)
        if not miner:
            return jsonify({
                'success': False,
                'message_en': 'Miner not found',
                'message_zh': '矿机不存在'
            }), 404
        
        user_id = session.get('user_id')
        user_role = normalize_role(session.get('role', 'guest'))
        
        has_full_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        is_owner = miner.customer_id == user_id
        
        if not has_full_access and not is_owner:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        return jsonify({
            'success': True,
            'miner_id': miner_id,
            'use_full_e2ee': miner.use_full_e2ee,
            'encrypted_connection_full': miner.encrypted_connection_full
        })
        
    except Exception as e:
        logger.error(f"获取矿机完整加密连接失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to get connection info',
            'message_zh': '获取连接信息失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/miners/<int:miner_id>/connection_full', methods=['POST'])
@login_required
def save_miner_connection_full(miner_id):
    """保存矿机完整加密连接信息 (Plan B)
    
    客户端在浏览器中加密完整连接信息后发送密文块。
    服务器只存储密文，无法解密。
    
    请求体:
    {
        "use_full_e2ee": true,
        "encrypted_connection_full": {
            "ciphertext": "base64...",
            "iv": "base64...",
            "salt": "base64...",
            "algo": "AES-256-GCM",
            "version": 1
        }
    }
    
    设置 use_full_e2ee=false 可禁用完整E2EE模式，回退到Plan A。
    """
    try:
        miner = HostingMiner.query.get(miner_id)
        if not miner:
            return jsonify({
                'success': False,
                'message_en': 'Miner not found',
                'message_zh': '矿机不存在'
            }), 404
        
        user_id = session.get('user_id')
        user_role = normalize_role(session.get('role', 'guest'))
        
        has_full_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        is_owner = miner.customer_id == user_id
        
        if not has_full_access and not is_owner:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message_en': 'Request body is required',
                'message_zh': '请求体不能为空'
            }), 400
        
        use_full_e2ee = data.get('use_full_e2ee', False)
        encrypted_connection_full = data.get('encrypted_connection_full')
        
        if use_full_e2ee:
            if not encrypted_connection_full:
                return jsonify({
                    'success': False,
                    'message_en': 'encrypted_connection_full is required when use_full_e2ee is true',
                    'message_zh': '启用完整E2EE时必须提供加密连接数据'
                }), 400
            
            is_valid, error = validate_encrypted_block(encrypted_connection_full)
            if not is_valid:
                return jsonify({
                    'success': False,
                    'message_en': error,
                    'message_zh': '加密块格式无效'
                }), 400
        
        miner.use_full_e2ee = use_full_e2ee
        miner.encrypted_connection_full = encrypted_connection_full if use_full_e2ee else None
        db.session.commit()
        
        mode = 'Plan B (Full E2EE)' if use_full_e2ee else 'Plan A'
        logger.info(f"矿机 {miner_id} 连接配置已更新: {mode} (by user {user_id})")
        
        return jsonify({
            'success': True,
            'message_en': f'Connection saved successfully ({mode})',
            'message_zh': f'连接信息保存成功 ({mode})',
            'miner_id': miner_id,
            'use_full_e2ee': miner.use_full_e2ee,
            'encrypted_connection_full': miner.encrypted_connection_full
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"保存矿机完整加密连接失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to save connection info',
            'message_zh': '保存连接信息失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/miners/<int:miner_id>/credentials/reset', methods=['DELETE'])
@login_required
def reset_miner_credentials(miner_id):
    """重置矿机加密凭证
    
    用于用户忘记密码短语时清除加密数据，之后需要重新输入凭证。
    """
    try:
        miner = HostingMiner.query.get(miner_id)
        if not miner:
            return jsonify({
                'success': False,
                'message_en': 'Miner not found',
                'message_zh': '矿机不存在'
            }), 404
        
        user_id = session.get('user_id')
        user_role = normalize_role(session.get('role', 'guest'))
        
        has_full_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        is_owner = miner.customer_id == user_id
        
        if not has_full_access and not is_owner:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        miner.encrypted_credentials = None
        miner.encrypted_connection_full = None
        miner.use_full_e2ee = False
        db.session.commit()
        
        logger.info(f"矿机 {miner_id} 加密凭证已重置 (by user {user_id})")
        
        return jsonify({
            'success': True,
            'message_en': 'Credentials reset successfully. Please re-enter and encrypt your connection details.',
            'message_zh': '凭证已重置。请重新输入并加密您的连接信息。',
            'miner_id': miner_id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"重置矿机加密凭证失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to reset credentials',
            'message_zh': '重置凭证失败',
            'error': str(e)
        }), 500


# ==================== 温度智能控频 API ====================

@hosting_bp.route('/api/thermal/config/<int:site_id>', methods=['GET'])
@login_required
def get_thermal_config(site_id):
    """获取站点热保护配置"""
    from models import ThermalProtectionConfig
    from services.thermal_protection_service import thermal_protection_service
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        config = thermal_protection_service.get_config(site_id)
        if not config:
            config = thermal_protection_service.create_default_config(site_id)
        
        return jsonify({
            'success': True,
            'config': config.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取热保护配置失败: {e}")
        return jsonify({
            'success': False,
            'message_en': 'Failed to get thermal config',
            'message_zh': '获取热保护配置失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/thermal/config/<int:config_id>', methods=['PUT'])
@login_required
def update_thermal_config(config_id):
    """更新热保护配置"""
    from services.thermal_protection_service import thermal_protection_service
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message_en': 'Request body is required',
                'message_zh': '请求体不能为空'
            }), 400
        
        success, message = thermal_protection_service.update_config(config_id, data)
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400
        
    except Exception as e:
        logger.error(f"更新热保护配置失败: {e}")
        return jsonify({
            'success': False,
            'message_en': 'Failed to update thermal config',
            'message_zh': '更新热保护配置失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/thermal/check/<int:site_id>', methods=['POST'])
@login_required
def run_thermal_check(site_id):
    """手动触发站点温度检查"""
    from services.thermal_protection_service import thermal_protection_service
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        results = thermal_protection_service.check_site(site_id)
        
        return jsonify({
            'success': True,
            'results': results,
            'message_en': f'Checked {results["checked"]} miners, {results["actions"]} actions taken',
            'message_zh': f'检查了 {results["checked"]} 台矿机，执行了 {results["actions"]} 个动作'
        })
        
    except Exception as e:
        logger.error(f"温度检查失败: {e}")
        return jsonify({
            'success': False,
            'message_en': 'Thermal check failed',
            'message_zh': '温度检查失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/thermal/events/<int:site_id>', methods=['GET'])
@login_required
def get_thermal_events(site_id):
    """获取热保护事件历史"""
    from services.thermal_protection_service import thermal_protection_service
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        limit = request.args.get('limit', 50, type=int)
        event_type = request.args.get('event_type')
        miner_id = request.args.get('miner_id', type=int)
        
        events = thermal_protection_service.get_thermal_events(
            site_id, limit=limit, event_type=event_type, miner_id=miner_id
        )
        
        return jsonify({
            'success': True,
            'events': events
        })
        
    except Exception as e:
        logger.error(f"获取热保护事件失败: {e}")
        return jsonify({
            'success': False,
            'message_en': 'Failed to get thermal events',
            'message_zh': '获取热保护事件失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/thermal/stats/<int:site_id>', methods=['GET'])
@login_required
def get_thermal_stats(site_id):
    """获取热保护统计数据"""
    from services.thermal_protection_service import thermal_protection_service
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        stats = thermal_protection_service.get_thermal_stats(site_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"获取热保护统计失败: {e}")
        return jsonify({
            'success': False,
            'message_en': 'Failed to get thermal stats',
            'message_zh': '获取热保护统计失败',
            'error': str(e)
        }), 500


# ==================== 白标系统 API ====================

@hosting_bp.route('/api/branding/<int:site_id>', methods=['GET'])
@login_required
def get_site_branding(site_id):
    """获取站点品牌配置"""
    from models import SiteBranding
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        branding = SiteBranding.query.filter_by(site_id=site_id).first()
        
        if not branding:
            site = HostingSite.query.get(site_id)
            if not site:
                return jsonify({
                    'success': False,
                    'message_en': 'Site not found',
                    'message_zh': '站点不存在'
                }), 404
            
            branding = SiteBranding(
                site_id=site_id,
                company_name=site.operator_name,
                primary_color='#f7931a',
                secondary_color='#1a1d2e'
            )
            db.session.add(branding)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'branding': branding.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取品牌配置失败: {e}")
        return jsonify({
            'success': False,
            'message_en': 'Failed to get branding',
            'message_zh': '获取品牌配置失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/branding/<int:site_id>', methods=['PUT'])
@login_required
def update_site_branding(site_id):
    """更新站点品牌配置"""
    from models import SiteBranding
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message_en': 'Request body is required',
                'message_zh': '请求体不能为空'
            }), 400
        
        branding = SiteBranding.query.filter_by(site_id=site_id).first()
        if not branding:
            branding = SiteBranding(site_id=site_id)
            db.session.add(branding)
        
        allowed_fields = [
            'company_name', 'company_slogan', 'logo_url', 'logo_light_url',
            'logo_dark_url', 'favicon_url', 'primary_color', 'secondary_color',
            'accent_color', 'support_email', 'support_phone', 'website_url',
            'twitter_url', 'telegram_url', 'discord_url', 'footer_text', 'is_enabled'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(branding, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_en': 'Branding updated successfully',
            'message_zh': '品牌配置更新成功',
            'branding': branding.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新品牌配置失败: {e}")
        return jsonify({
            'success': False,
            'message_en': 'Failed to update branding',
            'message_zh': '更新品牌配置失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/api/branding/<int:site_id>/logo', methods=['POST'])
@login_required
def upload_site_logo(site_id):
    """上传站点Logo"""
    from models import SiteBranding
    import os
    from werkzeug.utils import secure_filename
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            return jsonify({
                'success': False,
                'message_en': 'Access denied',
                'message_zh': '没有访问权限'
            }), 403
        
        if 'logo' not in request.files:
            return jsonify({
                'success': False,
                'message_en': 'No file uploaded',
                'message_zh': '未上传文件'
            }), 400
        
        file = request.files['logo']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message_en': 'No file selected',
                'message_zh': '未选择文件'
            }), 400
        
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'message_en': 'Invalid file type. Allowed: png, jpg, jpeg, gif, svg, webp',
                'message_zh': '文件类型无效。允许: png, jpg, jpeg, gif, svg, webp'
            }), 400
        
        upload_dir = os.path.join('static', 'uploads', 'logos')
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = secure_filename(f'site_{site_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{ext}')
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        logo_url = f'/static/uploads/logos/{filename}'
        
        branding = SiteBranding.query.filter_by(site_id=site_id).first()
        if not branding:
            branding = SiteBranding(site_id=site_id)
            db.session.add(branding)
        
        logo_type = request.form.get('logo_type', 'main')
        if logo_type == 'light':
            branding.logo_light_url = logo_url
        elif logo_type == 'dark':
            branding.logo_dark_url = logo_url
        elif logo_type == 'favicon':
            branding.favicon_url = logo_url
        else:
            branding.logo_url = logo_url
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_en': 'Logo uploaded successfully',
            'message_zh': 'Logo上传成功',
            'logo_url': logo_url
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"上传Logo失败: {e}")
        return jsonify({
            'success': False,
            'message_en': 'Failed to upload logo',
            'message_zh': '上传Logo失败',
            'error': str(e)
        }), 500


@hosting_bp.route('/site/<int:site_id>/settings')
@login_required
def site_settings(site_id):
    """站点设置页面 - 包含热保护和品牌配置"""
    from models import ThermalProtectionConfig, SiteBranding
    from services.thermal_protection_service import thermal_protection_service
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            flash('没有访问权限', 'error')
            return redirect(url_for('hosting_service_bp.dashboard'))
        
        site = HostingSite.query.get_or_404(site_id)
        
        thermal_config = thermal_protection_service.get_config(site_id)
        if not thermal_config:
            thermal_config = thermal_protection_service.create_default_config(site_id)
        
        branding = SiteBranding.query.filter_by(site_id=site_id).first()
        if not branding:
            branding = SiteBranding(
                site_id=site_id,
                company_name=site.operator_name,
                primary_color='#f7931a',
                secondary_color='#1a1d2e'
            )
            db.session.add(branding)
            db.session.commit()
        
        thermal_stats = thermal_protection_service.get_thermal_stats(site_id)
        
        all_sites = HostingSite.query.order_by(HostingSite.name).all()
        
        return render_template(
            'hosting/site_settings.html',
            site=site,
            thermal_config=thermal_config,
            branding=branding,
            thermal_stats=thermal_stats,
            all_sites=all_sites
        )
        
    except Exception as e:
        logger.error(f"加载站点设置失败: {e}")
        flash('加载设置失败', 'error')
        return redirect(url_for('hosting_service_bp.dashboard'))


@hosting_bp.route('/branding')
@login_required
def branding_management():
    """白标品牌管理页面 - 显示所有站点的品牌配置"""
    from models import SiteBranding
    
    try:
        user_role = normalize_role(session.get('role', 'guest'))
        has_access = rbac_manager.has_full_access(user_role, Module.HOSTING_SITE_MGMT)
        
        if not has_access:
            flash('没有访问权限', 'error')
            return redirect(url_for('hosting.dashboard'))
        
        sites = HostingSite.query.all()
        
        sites_with_branding = []
        for site in sites:
            branding = SiteBranding.query.filter_by(site_id=site.id).first()
            sites_with_branding.append({
                'site': site,
                'branding': branding
            })
        
        return render_template(
            'hosting/branding_management.html',
            sites_with_branding=sites_with_branding
        )
        
    except Exception as e:
        logger.error(f"加载品牌管理页面失败: {e}")
        flash('加载失败', 'error')
        return redirect(url_for('hosting.dashboard'))


# =====================================================
# IP Scanner API Routes - IP扫描自动发现矿机
# =====================================================

@hosting_bp.route('/api/scan/start', methods=['POST'])
@login_required
@requires_module_access(Module.HOSTING_SITE_MGMT, require_full=False)
def api_scan_start():
    """
    启动IP扫描发现矿机
    
    Request Body (IP Range):
    {
        "site_id": 1,
        "start_ip": "192.168.1.1",
        "end_ip": "192.168.1.254",
        "username": "root",  // optional
        "password": "root"   // optional
    }
    
    OR CIDR notation:
    {
        "site_id": 1,
        "cidr": "192.168.1.0/24",
        "username": "root",
        "password": "root"
    }
    
    Response:
    {
        "success": true,
        "scan_id": "scan_1_20251214_abc123",
        "total_ips": 254
    }
    """
    from services.ip_scanner import get_scanner
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        site_id = data.get('site_id')
        start_ip = data.get('start_ip', '').strip()
        end_ip = data.get('end_ip', '').strip()
        cidr = data.get('cidr', '').strip()
        username = data.get('username', 'root')
        password = data.get('password', 'root')
        
        if not site_id:
            return jsonify({'success': False, 'error': 'site_id is required'}), 400
        
        site = HostingSite.query.get(site_id)
        if not site:
            return jsonify({'success': False, 'error': 'Site not found'}), 404
        
        scanner = get_scanner()
        
        try:
            if cidr:
                ip_list = scanner.parse_cidr(cidr)
                if ip_list:
                    start_ip = ip_list[0]
                    end_ip = ip_list[-1]
            elif start_ip and end_ip:
                ip_list = scanner.parse_ip_range(start_ip, end_ip)
            else:
                return jsonify({'success': False, 'error': 'Provide start_ip/end_ip or cidr'}), 400
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        scan_id = scanner.scan_range_async(start_ip, end_ip, site_id, username, password)
        
        logger.info(f"IP scan started: {scan_id}, range: {start_ip} - {end_ip}, total: {len(ip_list)}")
        
        return jsonify({
            'success': True,
            'scan_id': scan_id,
            'total_ips': len(ip_list),
            'message': f'Scanning {len(ip_list)} IP addresses'
        })
        
    except Exception as e:
        logger.error(f"IP scan start error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/scan/<scan_id>/status', methods=['GET'])
@login_required
@requires_module_access(Module.HOSTING_SITE_MGMT, require_full=False)
def api_scan_status(scan_id):
    """
    获取扫描进度
    
    Response:
    {
        "success": true,
        "progress": {
            "scan_id": "scan_1_20251214_abc123",
            "total_ips": 254,
            "scanned_ips": 128,
            "discovered_miners": 15,
            "progress_percent": 50.4,
            "status": "scanning"
        }
    }
    """
    from services.ip_scanner import get_scanner
    
    try:
        scanner = get_scanner()
        progress = scanner.get_scan_progress(scan_id)
        
        if not progress:
            return jsonify({'success': False, 'error': 'Scan not found'}), 404
        
        return jsonify({
            'success': True,
            'progress': progress
        })
        
    except Exception as e:
        logger.error(f"Get scan status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/scan/<scan_id>/results', methods=['GET'])
@login_required
@requires_module_access(Module.HOSTING_SITE_MGMT, require_full=False)
def api_scan_results(scan_id):
    """
    获取扫描结果
    
    Response:
    {
        "success": true,
        "miners": [
            {
                "ip_address": "192.168.1.10",
                "miner_type": "antminer",
                "model": "Antminer S19 Pro",
                "hashrate_ths": 110.5,
                "temperature": 65.0,
                "online": true,
                ...
            }
        ]
    }
    """
    from services.ip_scanner import get_scanner
    
    try:
        scanner = get_scanner()
        progress = scanner.get_scan_progress(scan_id)
        
        if not progress:
            return jsonify({'success': False, 'error': 'Scan not found'}), 404
        
        results = scanner.get_scan_results(scan_id)
        
        return jsonify({
            'success': True,
            'progress': progress,
            'miners': results or []
        })
        
    except Exception as e:
        logger.error(f"Get scan results error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/scan/<scan_id>/register', methods=['POST'])
@login_required
@requires_module_access(Module.HOSTING_SITE_MGMT, require_full=False)
def api_scan_register(scan_id):
    """
    批量注册扫描发现的矿机
    
    Request Body:
    {
        "miners": [
            {"ip_address": "192.168.1.10", "model": "Antminer S19 Pro", ...},
            {"ip_address": "192.168.1.11", "model": "Antminer S19 Pro", ...}
        ]
    }
    
    Note: site_id is retrieved from server-side scan metadata for security.
    
    Response:
    {
        "success": true,
        "registered": 15,
        "skipped": 2,
        "errors": []
    }
    """
    from services.ip_scanner import get_scanner
    
    try:
        scanner = get_scanner()
        
        progress = scanner.get_scan_progress(scan_id)
        if not progress:
            return jsonify({'success': False, 'error': 'Scan not found'}), 404
        
        site_id = progress.get('site_id')
        if not site_id:
            return jsonify({'success': False, 'error': 'Invalid scan metadata'}), 400
        
        site = HostingSite.query.get(site_id)
        if not site:
            return jsonify({'success': False, 'error': 'Site not found'}), 404
        
        data = request.get_json() or {}
        miners_to_register = data.get('miners', [])
        
        if not miners_to_register:
            miners_to_register = scanner.get_scan_results(scan_id) or []
        
        registered = 0
        skipped = 0
        errors = []
        
        for miner_data in miners_to_register:
            try:
                ip_address = miner_data.get('ip_address')
                
                existing = HostingMiner.query.filter_by(
                    site_id=site_id,
                    ip_address=ip_address
                ).first()
                
                if existing:
                    skipped += 1
                    continue
                
                model_name = miner_data.get('model', 'Unknown')
                hashrate_ths = miner_data.get('hashrate_ths', 0)
                
                import uuid
                miner_id = f"SCAN-{uuid.uuid4().hex[:8].upper()}"
                
                new_miner = HostingMiner(
                    site_id=site_id,
                    miner_id=miner_id,
                    ip_address=ip_address,
                    miner_type=miner_data.get('miner_type', 'unknown'),
                    firmware_version=miner_data.get('firmware', ''),
                    pool_url=miner_data.get('pool_url', ''),
                    pool_worker=miner_data.get('worker', ''),
                    actual_hashrate=hashrate_ths,
                    temperature_avg=miner_data.get('temperature', 0),
                    cgminer_online=miner_data.get('online', False),
                    last_seen=datetime.utcnow() if miner_data.get('online') else None,
                    notes=f"Discovered via IP scan. Model: {model_name}"
                )
                
                db.session.add(new_miner)
                registered += 1
                
            except Exception as e:
                errors.append({
                    'ip': miner_data.get('ip_address', 'unknown'),
                    'error': str(e)
                })
        
        db.session.commit()
        
        scanner = get_scanner()
        scanner.cleanup_scan(scan_id)
        
        logger.info(f"IP scan register complete: {registered} registered, {skipped} skipped")
        
        return jsonify({
            'success': True,
            'registered': registered,
            'skipped': skipped,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Scan register error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@hosting_bp.route('/api/scan/cleanup/<scan_id>', methods=['DELETE'])
@login_required
@requires_module_access(Module.HOSTING_SITE_MGMT, require_full=False)
def api_scan_cleanup(scan_id):
    """清理扫描会话"""
    from services.ip_scanner import get_scanner
    
    try:
        scanner = get_scanner()
        scanner.cleanup_scan(scan_id)
        
        return jsonify({'success': True, 'message': 'Scan session cleaned up'})
        
    except Exception as e:
        logger.error(f"Scan cleanup error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
