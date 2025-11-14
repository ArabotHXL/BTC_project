
"""
托管功能路由
包含托管商和客户视角的所有功能
"""
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from . import hosting_bp
from auth import login_required
from decorators import requires_role
from models import db, HostingSite, HostingMiner, HostingTicket, HostingIncident, HostingUsageRecord, HostingUsageItem, MinerTelemetry, HostingBill, HostingBillItem
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
    """托管功能主仪表板"""
    user_role = session.get('role', 'guest')
    
    if user_role in ['owner', 'admin', 'mining_site']:
        # 托管商视角
        return render_template('hosting/host_dashboard.html')
    else:
        # 客户视角
        return render_template('hosting/client_dashboard.html')

@hosting_bp.route('/host/sites/<int:site_id>')
@requires_role(['owner', 'admin', 'mining_site'])
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
        return redirect(url_for('hosting.dashboard'))

@hosting_bp.route('/host')
@hosting_bp.route('/host/<path:subpath>')
@requires_role(['owner', 'admin', 'mining_site'])
def host_view(subpath='dashboard'):
    """托管商视角路由"""
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
        else:
            return render_template('hosting/host_dashboard.html')
    except Exception as e:
        logger.error(f"托管商视图错误: {e}")
        current_lang = session.get('language', 'zh')
        if current_lang == 'en':
            flash('Page loading failed', 'error')
        else:
            flash('页面加载失败', 'error')
        return redirect(url_for('hosting.dashboard'))

@hosting_bp.route('/client')
@hosting_bp.route('/client/<path:subpath>')
@login_required
def client_view(subpath='dashboard'):
    """客户视角路由"""
    try:
        if subpath == 'dashboard':
            return render_template('hosting/client_dashboard.html')
        elif subpath == 'assets':
            return render_template('hosting/asset_overview.html')
        elif subpath == 'usage':
            return render_template('hosting/client_usage.html')
        elif subpath == 'reports':
            return render_template('hosting/client_reports.html')
        else:
            return render_template('hosting/client_dashboard.html')
    except Exception as e:
        logger.error(f"客户视图错误: {e}")
        current_lang = session.get('language', 'zh')
        if current_lang == 'en':
            flash('Page loading failed', 'error')
        else:
            flash('页面加载失败', 'error')
        return redirect(url_for('hosting.dashboard'))

# ==================== 托管商API路由 ====================

@hosting_bp.route('/api/overview', methods=['GET'])
@login_required
def get_hosting_overview():
    """获取托管商总览数据"""
    try:
        # 站点统计
        total_sites = HostingSite.query.count()
        online_sites = HostingSite.query.filter_by(status='online').count()
        
        # 矿机统计
        total_miners = HostingMiner.query.count()
        active_miners = HostingMiner.query.filter_by(status='active').count()
        
        # 容量统计
        capacity_stats = db.session.query(
            db.func.sum(HostingSite.capacity_mw).label('total_capacity'),
            db.func.sum(HostingSite.used_capacity_mw).label('used_capacity')
        ).first()
        
        total_capacity = float(capacity_stats[0] or 0) if capacity_stats and capacity_stats[0] else 0
        used_capacity = float(capacity_stats[1] or 0) if capacity_stats and capacity_stats[1] else 0
        utilization_rate = round((used_capacity / total_capacity * 100) if total_capacity > 0 else 0, 1)
        
        # 近期事件
        recent_incidents = HostingIncident.query.filter(
            HostingIncident.created_at >= datetime.now() - timedelta(days=7)
        ).count()
        
        # 待处理工单
        pending_tickets = HostingTicket.query.filter(
            HostingTicket.status.in_(['open', 'assigned', 'in_progress'])
        ).count()
        
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
    """获取托管站点列表"""
    try:
        sites = HostingSite.query.all()
        sites_data = []
        
        for site in sites:
            # 计算设备数量
            devices_count = HostingMiner.query.filter_by(site_id=site.id).count()
            active_devices = HostingMiner.query.filter_by(site_id=site.id, status='active').count()
            
            site_data = site.to_dict()
            site_data['devices_count'] = devices_count
            site_data['active_devices'] = active_devices
            sites_data.append(site_data)
        
        return jsonify({'success': True, 'sites': sites_data})
    except Exception as e:
        logger.error(f"获取站点列表失败: {e}")
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
    """获取客户仪表板数据"""
    try:
        user_id = session.get('user_id')
        
        # 获取客户矿机统计
        miners = HostingMiner.query.filter_by(customer_id=user_id).all()
        total_miners = len(miners)
        active_miners = len([m for m in miners if m.status == 'active'])
        
        # 计算算力和功耗
        total_hashrate = sum(m.actual_hashrate or 0 for m in miners if m.status == 'active')
        total_power = sum(m.actual_power or 0 for m in miners if m.status == 'active')
        
        # 估算收益（简化计算）
        daily_revenue = total_hashrate * 0.000005 * 110000  # 估算日收益
        monthly_revenue = daily_revenue * 30
        
        # 估算成本
        daily_power_cost = total_power * 24 * 0.08 / 1000  # 估算电费
        monthly_power_cost = daily_power_cost * 30
        
        dashboard_data = {
            'miners': {
                'total': total_miners,
                'active': active_miners,
                'offline': total_miners - active_miners
            },
            'performance': {
                'total_hashrate': round(total_hashrate, 2),
                'total_power': round(total_power, 0),
                'efficiency': round(total_hashrate / (total_power / 1000), 2) if total_power > 0 else 0
            },
            'revenue': {
                'daily': round(daily_revenue, 2),
                'monthly': round(monthly_revenue, 2),
                'daily_cost': round(daily_power_cost, 2),
                'monthly_cost': round(monthly_power_cost, 2),
                'daily_profit': round(daily_revenue - daily_power_cost, 2),
                'monthly_profit': round(monthly_revenue - monthly_power_cost, 2)
            }
        }
        
        return jsonify({'success': True, 'data': dashboard_data})
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
        
        chart_data = {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Revenue',
                    'data': revenue_data,
                    'borderColor': 'rgb(255, 193, 7)',
                    'backgroundColor': 'rgba(255, 193, 7, 0.1)'
                },
                {
                    'label': 'Cost',
                    'data': cost_data,
                    'borderColor': 'rgb(220, 53, 69)',
                    'backgroundColor': 'rgba(220, 53, 69, 0.1)'
                }
            ]
        }
        
        return jsonify({'success': True, 'chart': chart_data})
    except Exception as e:
        logger.error(f"获取收益图表数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/client/miner-distribution', methods=['GET'])
@login_required
def get_client_miner_distribution():
    """获取客户矿机分布数据"""
    try:
        user_id = session.get('user_id')
        
        # 按站点统计矿机分布
        miners = HostingMiner.query.filter_by(customer_id=user_id).all()
        
        site_distribution = {}
        for miner in miners:
            site_name = miner.site.name if miner.site else 'Unknown'
            if site_name not in site_distribution:
                site_distribution[site_name] = 0
            site_distribution[site_name] += 1
        
        # 转换为图表数据格式
        labels = list(site_distribution.keys())
        data = list(site_distribution.values())
        
        # 颜色方案
        colors = ['#FFB800', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57']
        background_colors = [colors[i % len(colors)] for i in range(len(labels))]
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': background_colors,
                'borderWidth': 2,
                'borderColor': '#2c3e50'
            }]
        }
        
        return jsonify({'success': True, 'chart': chart_data})
    except Exception as e:
        logger.error(f"获取矿机分布数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        # 权限控制
        if user_role in ['owner', 'admin', 'mining_site']:
            # 托管商可以查看所有矿机
            pass
        else:
            # 客户只能查看自己的矿机
            query = query.filter_by(customer_id=user_id)
        
        # 应用筛选条件
        if status:
            query = query.filter_by(status=status)
        if approval_status:
            query = query.filter_by(approval_status=approval_status)
        if site_id:
            query = query.filter_by(site_id=site_id)
        if customer_id and user_role in ['owner', 'admin', 'mining_site']:
            query = query.filter_by(customer_id=customer_id)
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        current_lang = session.get('language', 'zh')
        
        miners_data = []
        for miner in pagination.items:
            miner_data = miner.to_dict()
            
            # 添加关联信息
            if miner.customer:
                miner_data['customer_name'] = miner.customer.email
                miner_data['customer_email'] = miner.customer.email
            
            if miner.submitter:
                miner_data['submitted_by_name'] = miner.submitter.email
            
            if miner.approver:
                miner_data['approved_by_name'] = miner.approver.email
            
            # 添加站点名称
            if miner.site:
                miner_data['site_name'] = miner.site.name
            
            # 添加告警信息
            alerts_info = get_miner_alerts(miner, lang=current_lang)
            miner_data['alerts'] = alerts_info
            
            miners_data.append(miner_data)
        
        # Calculate counts for UI display
        base_query = HostingMiner.query
        if user_role not in ['owner', 'admin', 'mining_site']:
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
        if user_role in ['owner', 'admin', 'mining_site']:
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
        if user_role not in ['owner', 'admin', 'mining_site'] and miner.customer_id != user_id:
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
    """获取矿机24小时遥测历史数据"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        miner = HostingMiner.query.get_or_404(miner_id)
        
        # 权限检查：防御性检查确保session完整性
        if user_role not in ['owner', 'admin', 'mining_site']:
            if not user_id or miner.customer_id != user_id:
                return jsonify({'success': False, 'error': '无权限'}), 403
        
        # 查询最近24小时的遥测数据
        time_24h_ago = datetime.utcnow() - timedelta(hours=24)
        
        telemetry_records = MinerTelemetry.query.filter(
            MinerTelemetry.miner_id == miner_id,
            MinerTelemetry.recorded_at >= time_24h_ago
        ).order_by(MinerTelemetry.recorded_at.asc()).all()
        
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

@hosting_bp.route('/hosting/miner/<int:miner_id>/detail')
@login_required
def miner_detail_page(miner_id):
    """矿机详情页面"""
    try:
        miner = HostingMiner.query.get_or_404(miner_id)
        user_role = session.get('role', 'guest')
        user_id = session.get('user_id')
        
        # 权限检查：防御性检查确保session完整性
        if user_role not in ['owner', 'admin', 'mining_site']:
            if not user_id or miner.customer_id != user_id:
                flash('无权限访问' if session.get('language', 'zh') == 'zh' else 'Access denied', 'error')
                return redirect(url_for('hosting.host_view', subpath='devices'))
        
        return render_template('hosting/miner_detail.html', miner=miner, current_lang=session.get('language', 'zh'))
    except Exception as e:
        logger.error(f"矿机详情页面错误: {e}")
        flash('矿机未找到' if session.get('language', 'zh') == 'zh' else 'Miner not found', 'error')
        return redirect(url_for('hosting.host_view', subpath='devices'))

@hosting_bp.route('/api/miners/<int:miner_id>', methods=['PUT'])
@login_required
def update_miner(miner_id):
    """更新矿机信息"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        user_role = session.get('role', 'guest')
        
        miner = HostingMiner.query.get_or_404(miner_id)
        
        # 权限检查
        if user_role not in ['owner', 'admin', 'mining_site'] and miner.customer_id != user_id:
            return jsonify({
                'success': False,
                'error': '无权限操作'
            }), 403
        
        # 更新允许的字段
        updateable_fields = ['rack_position', 'ip_address', 'mac_address', 'actual_hashrate', 'actual_power', 'status']
        
        for field in updateable_fields:
            if field in data:
                setattr(miner, field, data[field])
        
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

@hosting_bp.route('/api/miners/<int:miner_id>', methods=['DELETE'])
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
            
            history_data.append({
                'id': plan.id,
                'site_id': plan.site_id,
                'site_name': site_name,
                'strategy_id': plan.strategy_id,
                'strategy_name': strategy_name,
                'target_power_reduction_kw': float(plan.target_power_reduction_kw),
                'actual_power_saved_kw': float(plan.actual_power_saved_kw or 0),
                'status': plan.status.value,
                'execution_mode': plan.execution_mode.value,
                'created_at': plan.created_at.isoformat() if plan.created_at else None,
                'executed_at': plan.executed_at.isoformat() if plan.executed_at else None
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
@requires_role(['owner', 'admin', 'mining_site'])
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


# ==================== CGMiner 实时监控 API ====================

@hosting_bp.route('/api/miners/<int:miner_id>/telemetry', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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
