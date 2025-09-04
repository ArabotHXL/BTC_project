
"""
托管功能路由
包含托管商和客户视角的所有功能
"""
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from . import hosting_bp
from auth import login_required
from decorators import requires_role
from models import HostingSite, HostingMiner, HostingTicket, HostingIncident, db
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
            return render_template('hosting/device_management.html')
        elif subpath == 'monitoring':
            return render_template('hosting/event_monitoring.html')
        elif subpath == 'sla':
            return render_template('hosting/sla_management.html')
        else:
            return render_template('hosting/host_dashboard.html')
    except Exception as e:
        logger.error(f"托管商视图错误: {e}")
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
        elif subpath == 'billing':
            return render_template('hosting/billing_view.html')
        elif subpath == 'reports':
            return render_template('hosting/client_reports.html')
        else:
            return render_template('hosting/client_dashboard.html')
    except Exception as e:
        logger.error(f"客户视图错误: {e}")
        flash('页面加载失败', 'error')
        return redirect(url_for('hosting.dashboard'))

# ==================== 托管商API路由 ====================

@hosting_bp.route('/api/overview', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site'])
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
@requires_role(['owner', 'admin', 'mining_site'])
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

# ==================== 账单和对账系统 ====================

@hosting_bp.route('/api/billing/preview', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site'])
def generate_billing_preview():
    """生成账单预估"""
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
        
        # 创建账单预估
        bill_preview = {
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
        
        return jsonify({'success': True, 'preview': bill_preview})
    except Exception as e:
        logger.error(f"生成账单预估失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/billing/create', methods=['POST'])
@requires_role(['owner', 'admin', 'mining_site'])
def create_bill():
    """根据预估创建正式账单"""
    try:
        data = request.get_json()
        
        # 生成账单编号
        bill_number = f"BILL-{datetime.now().strftime('%Y%m%d')}-{data['customer_id']:04d}-{data['site_id']:02d}"
        
        bill = HostingBill(
            bill_number=bill_number,
            customer_id=data['customer_id'],
            site_id=data['site_id'],
            billing_period_start=datetime.fromisoformat(data['period_start']).date(),
            billing_period_end=datetime.fromisoformat(data['period_end']).date(),
            electricity_cost=data['costs']['electricity_cost'],
            hosting_fee=data['costs']['hosting_fee'],
            maintenance_cost=data['costs']['maintenance_cost'],
            total_amount=data['costs']['total_amount'],
            due_date=datetime.now().date() + timedelta(days=30)  # 30天付款期
        )
        
        db.session.add(bill)
        db.session.flush()  # 获取ID
        
        # 创建账单明细
        for item in data['breakdown']:
            bill_item = HostingBillItem(
                bill_id=bill.id,
                item_type=item['item'].lower(),
                description=item['description'],
                quantity=1,
                unit_price=item['amount'],
                amount=item['amount']
            )
            db.session.add(bill_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '账单创建成功',
            'bill_id': bill.id,
            'bill_number': bill.bill_number
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建账单失败: {e}")
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
        
        if not file.filename.endswith('.csv'):
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

# Sprint 1 KPI API Routes
@hosting_bp.route("/api/kpi-summary", methods=["GET"])  
@requires_role(["owner", "admin", "mining_site"])
def get_kpi_summary():
    """获取KPI总览数据"""
    try:
        sites = HostingSite.query.all()
        online_miners = HostingMiner.query.filter_by(status="active").all()
        total_hashrate = sum(miner.actual_hashrate for miner in online_miners)
        kpi_data = {
            "online_miners": len(online_miners),
            "total_hashrate": total_hashrate,
            "sites": [{"name": s.name, "status": s.status} for s in sites]
        }
        return jsonify({"success": True, "kpi": kpi_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@hosting_bp.route("/api/generate-demo-data", methods=["POST"])
@requires_role(["owner", "admin"])  
def generate_demo_data_api():
    """生成演示数据API"""
    try:
        from demo_data_generator import generate_demo_data
        success = generate_demo_data()
        return jsonify({"success": success, "message": "演示数据生成" + ("成功" if success else "失败")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

