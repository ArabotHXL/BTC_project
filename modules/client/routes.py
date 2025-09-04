"""
客户功能路由
为托管平台客户提供资产管理、账单查询、工单系统等功能
"""
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from . import client_bp
from auth import login_required
from models import db, HostingMiner, HostingTicket, HostingBill, HostingSite, MinerTelemetry
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ==================== 客户主要页面路由 ====================

@client_bp.route('/')
@client_bp.route('/dashboard')
@login_required
def dashboard():
    """客户仪表板"""
    try:
        user_id = session.get('user_id')
        
        # 获取客户基本统计
        total_miners = HostingMiner.query.filter_by(customer_id=user_id).count()
        active_miners = HostingMiner.query.filter_by(customer_id=user_id, status='active').count()
        
        # 获取近期工单
        recent_tickets = HostingTicket.query.filter_by(customer_id=user_id).filter(
            HostingTicket.created_at >= datetime.now() - timedelta(days=30)
        ).count()
        
        dashboard_data = {
            'total_miners': total_miners,
            'active_miners': active_miners,
            'recent_tickets': recent_tickets
        }
        
        return render_template('hosting/client_dashboard.html', data=dashboard_data)
    except Exception as e:
        logger.error(f"客户仪表板加载失败: {e}")
        flash('仪表板加载失败', 'error')
        return render_template('hosting/client_dashboard.html', data={})

@client_bp.route('/miners')
@login_required
def miners():
    """我的矿机页面"""
    return render_template('hosting/client_miners.html')

@client_bp.route('/billing')
@login_required
def billing():
    """账单查询页面"""
    return render_template('hosting/client_billing.html')

@client_bp.route('/reports')
@login_required
def reports():
    """透明月报页面"""
    return render_template('hosting/client_reports.html')

@client_bp.route('/tickets')
@login_required
def tickets():
    """我的工单页面"""
    return render_template('hosting/client_tickets.html')

@client_bp.route('/alerts')
@login_required
def alerts():
    """告警中心页面"""
    return render_template('hosting/client_alerts.html')

# ==================== 客户API路由 ====================

@client_bp.route('/api/overview', methods=['GET'])
@login_required
def get_client_overview():
    """获取客户总览数据"""
    try:
        user_id = session.get('user_id')
        
        # 矿机统计
        total_miners = HostingMiner.query.filter_by(customer_id=user_id).count()
        active_miners = HostingMiner.query.filter_by(customer_id=user_id, status='active').count()
        offline_miners = HostingMiner.query.filter_by(customer_id=user_id, status='offline').count()
        maintenance_miners = HostingMiner.query.filter_by(customer_id=user_id, status='maintenance').count()
        
        # 算力和功耗统计
        active_miners_data = HostingMiner.query.filter_by(customer_id=user_id, status='active').all()
        total_hashrate = sum(miner.actual_hashrate for miner in active_miners_data)
        total_power = sum(miner.actual_power for miner in active_miners_data)
        
        # 站点分布
        site_distribution = {}
        for miner in HostingMiner.query.filter_by(customer_id=user_id).all():
            site_name = miner.site.name if miner.site else 'Unknown'
            if site_name not in site_distribution:
                site_distribution[site_name] = {'total': 0, 'active': 0}
            site_distribution[site_name]['total'] += 1
            if miner.status == 'active':
                site_distribution[site_name]['active'] += 1
        
        # 近期工单统计
        open_tickets = HostingTicket.query.filter_by(customer_id=user_id).filter(
            HostingTicket.status.in_(['open', 'assigned', 'in_progress'])
        ).count()
        
        resolved_tickets_30d = HostingTicket.query.filter_by(customer_id=user_id).filter(
            HostingTicket.status == 'resolved',
            HostingTicket.resolved_at >= datetime.now() - timedelta(days=30)
        ).count()
        
        overview_data = {
            'miners': {
                'total': total_miners,
                'active': active_miners,
                'offline': offline_miners,
                'maintenance': maintenance_miners,
                'total_hashrate_th': round(total_hashrate, 1),
                'total_power_w': round(total_power, 0)
            },
            'sites': [
                {
                    'name': site_name,
                    'total_miners': stats['total'],
                    'active_miners': stats['active']
                }
                for site_name, stats in site_distribution.items()
            ],
            'tickets': {
                'open': open_tickets,
                'resolved_30d': resolved_tickets_30d
            }
        }
        
        return jsonify({'success': True, 'data': overview_data})
    except Exception as e:
        logger.error(f"获取客户总览失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@client_bp.route('/api/miners', methods=['GET'])
@login_required
def get_client_miners():
    """获取客户矿机列表"""
    try:
        user_id = session.get('user_id')
        
        # 获取查询参数
        status = request.args.get('status')
        site_id = request.args.get('site_id')
        
        query = HostingMiner.query.filter_by(customer_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        if site_id:
            query = query.filter_by(site_id=int(site_id))
            
        miners = query.order_by(HostingMiner.created_at.desc()).all()
        
        miners_data = []
        for miner in miners:
            # 获取最新的性能数据
            latest_telemetry = MinerTelemetry.query.filter_by(miner_id=miner.id).order_by(
                MinerTelemetry.recorded_at.desc()
            ).first()
            
            miner_data = miner.to_dict()
            miner_data['site_name'] = miner.site.name if miner.site else 'Unknown'
            miner_data['miner_model_name'] = miner.miner_model.model_name if miner.miner_model else 'Unknown'
            
            if latest_telemetry:
                miner_data['current_performance'] = {
                    'hashrate': latest_telemetry.hashrate,
                    'power_consumption': latest_telemetry.power_consumption,
                    'temperature': latest_telemetry.temperature,
                    'last_update': latest_telemetry.recorded_at.isoformat()
                }
            else:
                miner_data['current_performance'] = None
                
            miners_data.append(miner_data)
        
        return jsonify({'success': True, 'miners': miners_data})
    except Exception as e:
        logger.error(f"获取客户矿机列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@client_bp.route('/api/bills', methods=['GET'])
@login_required
def get_client_bills():
    """获取客户账单列表"""
    try:
        user_id = session.get('user_id')
        
        # 获取查询参数
        status = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        
        query = HostingBill.query.filter_by(customer_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
            
        bills = query.order_by(HostingBill.created_at.desc()).limit(limit).all()
        
        bills_data = []
        for bill in bills:
            bill_data = {
                'id': bill.id,
                'bill_number': bill.bill_number,
                'site_name': bill.site.name if bill.site else 'Unknown',
                'billing_period_start': bill.billing_period_start.isoformat(),
                'billing_period_end': bill.billing_period_end.isoformat(),
                'electricity_cost': bill.electricity_cost,
                'hosting_fee': bill.hosting_fee,
                'maintenance_cost': bill.maintenance_cost,
                'total_amount': bill.total_amount,
                'status': bill.status,
                'created_at': bill.created_at.isoformat(),
                'due_date': bill.due_date.isoformat() if bill.due_date else None
            }
            bills_data.append(bill_data)
        
        return jsonify({'success': True, 'bills': bills_data})
    except Exception as e:
        logger.error(f"获取客户账单失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@client_bp.route('/api/tickets', methods=['GET'])
@login_required
def get_client_tickets():
    """获取客户工单列表"""
    try:
        user_id = session.get('user_id')
        
        # 获取查询参数
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        query = HostingTicket.query.filter_by(customer_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
            
        tickets = query.order_by(HostingTicket.created_at.desc()).limit(limit).all()
        
        tickets_data = []
        for ticket in tickets:
            ticket_data = {
                'id': ticket.id,
                'title': ticket.title,
                'description': ticket.description,
                'priority': ticket.priority,
                'status': ticket.status,
                'category': ticket.category,
                'created_at': ticket.created_at.isoformat(),
                'first_response_at': ticket.first_response_at.isoformat() if ticket.first_response_at else None,
                'resolved_at': ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                'response_time_minutes': ticket.response_time_minutes,
                'resolution_time_hours': ticket.resolution_time_hours
            }
            
            if ticket.site:
                ticket_data['site_name'] = ticket.site.name
            
            tickets_data.append(ticket_data)
        
        return jsonify({'success': True, 'tickets': tickets_data})
    except Exception as e:
        logger.error(f"获取客户工单失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@client_bp.route('/api/tickets', methods=['POST'])
@login_required
def create_client_ticket():
    """客户创建工单"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # 验证必要字段
        if not data.get('title'):
            return jsonify({'success': False, 'error': '工单标题不能为空'}), 400
        
        ticket = HostingTicket(
            title=data['title'],
            customer_id=user_id,
            description=data.get('description', ''),
            priority=data.get('priority', 'medium'),
            category=data.get('category', 'other'),
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
        logger.error(f"创建客户工单失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@client_bp.route('/api/performance/<int:miner_id>', methods=['GET'])
@login_required
def get_miner_performance(miner_id):
    """获取矿机性能历史数据"""
    try:
        user_id = session.get('user_id')
        
        # 验证矿机归属
        miner = HostingMiner.query.filter_by(id=miner_id, customer_id=user_id).first()
        if not miner:
            return jsonify({'success': False, 'error': '矿机不存在或无权限'}), 404
        
        # 获取时间范围参数
        days = int(request.args.get('days', 7))
        start_date = datetime.now() - timedelta(days=days)
        
        # 获取性能数据
        telemetry_data = MinerTelemetry.query.filter(
            MinerTelemetry.miner_id == miner_id,
            MinerTelemetry.recorded_at >= start_date
        ).order_by(MinerTelemetry.recorded_at.asc()).all()
        
        performance_data = []
        for record in telemetry_data:
            performance_data.append({
                'timestamp': record.recorded_at.isoformat(),
                'hashrate': record.hashrate,
                'power_consumption': record.power_consumption,
                'temperature': record.temperature,
                'fan_speed': record.fan_speed
            })
        
        return jsonify({
            'success': True,
            'miner_info': miner.to_dict(),
            'performance_data': performance_data
        })
    except Exception as e:
        logger.error(f"获取矿机性能数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@client_bp.route('/api/sites', methods=['GET'])
@login_required
def get_client_sites():
    """获取客户可见的站点列表"""
    try:
        user_id = session.get('user_id')
        
        # 获取客户有矿机托管的站点
        site_ids = db.session.query(HostingMiner.site_id.distinct()).filter_by(customer_id=user_id).all()
        site_ids = [site_id[0] for site_id in site_ids]
        
        sites = HostingSite.query.filter(HostingSite.id.in_(site_ids)).all()
        
        sites_data = []
        for site in sites:
            # 计算该客户在此站点的矿机数量
            customer_miners = HostingMiner.query.filter_by(customer_id=user_id, site_id=site.id).count()
            active_miners = HostingMiner.query.filter_by(
                customer_id=user_id, 
                site_id=site.id, 
                status='active'
            ).count()
            
            site_data = {
                'id': site.id,
                'name': site.name,
                'location': site.location,
                'status': site.status,
                'customer_miners': customer_miners,
                'active_miners': active_miners
            }
            sites_data.append(site_data)
        
        return jsonify({'success': True, 'sites': sites_data})
    except Exception as e:
        logger.error(f"获取客户站点列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500