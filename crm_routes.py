"""
CRM (Customer Relationship Management) Routes
客户关系管理系统路由
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from sqlalchemy import func

# Import database and models
from db import db
from models import Customer, Lead, Deal, Invoice, Asset, Activity, DealStatus, LeadStatus, CommissionRecord

# Import CRM service layer
from crm_services import (
    BaseService, get_current_user_id, success_response, error_response,
    success_response_with_polling, apply_tenant_filter, get_tenant_filter,
    verify_resource_access, can_access_all_data
)
from crm_services.geo import (
    get_city_coordinates, get_all_cities, is_city_supported, get_region_cities
)

# RBAC权限控制导入
from common.rbac import requires_module_access, Module, AccessLevel
from auth import login_required

logger = logging.getLogger(__name__)

# 创建蓝图
crm_bp = Blueprint('crm', __name__)

# Context processor for translations
@crm_bp.context_processor
def inject_translations():
    """为CRM模板注入翻译函数和语言设置"""
    from flask import g
    try:
        from language_engine import get_translation
        def translate(text):
            return get_translation(text, to_lang=g.language)
        return dict(t=translate, tr=translate, current_lang=g.language)
    except:
        # 如果语言引擎不可用，使用基本回退
        def translate(text):
            return text
        current_lang = session.get('language', 'zh')
        return dict(t=translate, tr=translate, current_lang=current_lang)

@crm_bp.route('/')
def crm_dashboard():
    """CRM主仪表盘"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        # Query real statistics from database - WITH TENANT ISOLATION
        tenant_filter = get_tenant_filter(Customer, user_id)
        if tenant_filter is not None:
            customers_count = Customer.query.filter(tenant_filter).count() or 0
            leads_count = Lead.query.filter(Lead.created_by_id == user_id).count() or 0
            deals_count = Deal.query.filter(Deal.created_by_id == user_id).count() or 0
            deals_value = Deal.query.filter(Deal.created_by_id == user_id).with_entities(func.sum(Deal.value)).scalar() or 0
        else:
            # Owner/Admin can see all data
            customers_count = Customer.query.count() or 0
            leads_count = Lead.query.count() or 0
            deals_count = Deal.query.count() or 0
            deals_value = Deal.query.with_entities(func.sum(Deal.value)).scalar() or 0
        
        # DEBUG: Log actual values to diagnose NaN issue
        logger.info(f"Dashboard Variables: customers_count={customers_count} (type={type(customers_count).__name__})")
        logger.info(f"Dashboard Variables: leads_count={leads_count} (type={type(leads_count).__name__})")
        logger.info(f"Dashboard Variables: deals_count={deals_count} (type={type(deals_count).__name__})")
        logger.info(f"Dashboard Variables: deals_value={deals_value} (type={type(deals_value).__name__})")
        
        # Get recent activities (limit 10) - WITH TENANT ISOLATION
        activities_query = Activity.query.order_by(Activity.created_at.desc())
        recent_activities = apply_tenant_filter(activities_query, Activity, user_id).limit(10).all()
        
        # Get leads with follow-up dates - WITH TENANT ISOLATION
        leads_query = Lead.query.filter(Lead.next_follow_up.isnot(None)).order_by(Lead.next_follow_up)
        follow_up_leads = apply_tenant_filter(leads_query, Lead, user_id).limit(10).all()
        
        return render_template('crm/dashboard_new.html',
                             title='CRM Dashboard',
                             page='crm',
                             customers_count=customers_count,
                             leads_count=leads_count,
                             deals_count=deals_count,
                             deals_value=deals_value,
                             recent_activities=recent_activities,
                             follow_up_leads=follow_up_leads)
    except Exception as e:
        logger.error(f"CRM仪表盘错误: {e}")
        flash('无法加载CRM页面', 'error')
        return redirect(url_for('dashboard'))

@crm_bp.route('/customers', endpoint='customers')
def customers_list():
    """客户列表页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/customers.html',
                             title='Customer Management',
                             page='crm_customers')
    except Exception as e:
        logger.error(f"客户列表页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/api/customers')
def get_customers():
    """获取客户列表 - 从数据库读取真实数据 (WITH TENANT ISOLATION)"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Fetch customers from database - WITH TENANT ISOLATION
        customers_query = Customer.query.order_by(Customer.created_at.desc())
        customers = apply_tenant_filter(customers_query, Customer, user_id).all()
        
        customers_data = []
        for customer in customers:
            # Calculate total revenue from deals
            total_revenue = sum([deal.value for deal in customer.deals if deal.value])
            
            # Get last activity date
            last_activity = Activity.query.filter_by(customer_id=customer.id).order_by(Activity.created_at.desc()).first()
            last_contact = last_activity.created_at.strftime('%Y-%m-%d') if last_activity else None
            
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'company': customer.company,
                'email': customer.email,
                'phone': customer.phone,
                'customer_type': customer.customer_type,
                'mining_capacity': customer.mining_capacity or 0,
                'join_date': customer.created_at.strftime('%Y-%m-%d'),
                'total_revenue': total_revenue,
                'last_contact': last_contact,
                'tags': customer.tags,
                # 新增矿场专属字段
                'status': getattr(customer, 'status', 'active') or 'active',
                'electricity_cost': getattr(customer, 'electricity_cost', 0) or 0,
                'miners_count': getattr(customer, 'miners_count', 0) or 0,
                'primary_miner_model': getattr(customer, 'primary_miner_model', None) or 'N/A',
                'monthly_revenue': total_revenue / 12 if total_revenue > 0 else 0
            })
        
        return jsonify({
            'success': True,
            'data': customers_data,
            'total': len(customers_data),
            'page': 1,
            'per_page': 50
        })
        
    except Exception as e:
        logger.error(f"获取客户列表错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/customer/<int:customer_id>')
def get_customer_details(customer_id):
    """获取客户详情 (WITH TENANT ISOLATION)"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Query real customer from database
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Get real deals for this customer
        deals = Deal.query.filter_by(customer_id=customer_id).all()
        
        # Calculate total revenue from deals
        total_revenue = sum([deal.value for deal in deals if deal.value]) or 0
        
        # Get real activities/notes for this customer
        activities = Activity.query.filter_by(customer_id=customer_id).order_by(Activity.created_at.desc()).limit(10).all()
        
        # Format deals/contracts data
        contracts = []
        for deal in deals:
            # Infer deal type from mining_capacity
            deal_type = 'hosting' if deal.mining_capacity and deal.mining_capacity > 0 else 'sales'
            
            contracts.append({
                'id': deal.id,
                'type': deal_type,
                'start_date': deal.created_at.strftime('%Y-%m-%d') if deal.created_at else None,
                'end_date': deal.expected_close_date.strftime('%Y-%m-%d') if deal.expected_close_date else (deal.closed_date.strftime('%Y-%m-%d') if deal.closed_date else None),
                'value': deal.value or 0,
                'status': deal.status.value if hasattr(deal.status, 'value') else str(deal.status)
            })
        
        # Format activities/notes data
        notes = []
        for activity in activities:
            # Get author name from created_by field or relationship
            author = activity.created_by or 'System'
            if not author and activity.created_by_user:
                author = activity.created_by_user.email or activity.created_by_user.username or 'System'
            
            notes.append({
                'id': activity.id,
                'date': activity.created_at.strftime('%Y-%m-%d') if activity.created_at else None,
                'author': author,
                'content': activity.details or activity.summary or ''
            })
        
        # Build response with actual customer data
        customer_detail = {
            'success': True,
            'data': {
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'address': customer.address or '',
                'status': customer.status or 'active',
                'tier': customer.customer_type or 'standard',
                'join_date': customer.created_at.strftime('%Y-%m-%d') if customer.created_at else None,
                'total_revenue': total_revenue,
                'mining_capacity': customer.mining_capacity or '',
                'electricity_cost': customer.electricity_cost or 0,
                'contracts': contracts,
                'notes': notes
            }
        }
        
        return jsonify(customer_detail)
        
    except Exception as e:
        logger.error(f"获取客户详情错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/customer/<int:customer_id>/revenue-trend')
def get_customer_revenue_trend(customer_id):
    """获取客户收入趋势数据（用于图表）"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Query customer
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Get all deals for this customer
        deals = Deal.query.filter_by(customer_id=customer_id).order_by(Deal.created_at.asc()).all()
        
        # Calculate monthly revenue (past 12 months)
        from collections import defaultdict
        from dateutil.relativedelta import relativedelta
        
        end_date = datetime.now()
        start_date = end_date - relativedelta(months=11)
        
        monthly_sales = defaultdict(float)
        monthly_hosting = defaultdict(float)
        
        for deal in deals:
            if deal.created_at and deal.created_at >= start_date:
                month_key = deal.created_at.strftime('%Y-%m')
                
                # Categorize by mining_capacity (if exists, it's hosting)
                if deal.mining_capacity and deal.mining_capacity > 0:
                    monthly_hosting[month_key] += deal.value or 0
                else:
                    monthly_sales[month_key] += deal.value or 0
        
        # Generate month labels for past 12 months
        months = []
        miner_sales = []
        hosting_fees = []
        
        for i in range(12):
            month = start_date + relativedelta(months=i)
            month_key = month.strftime('%Y-%m')
            month_label = month.strftime('%b %Y')
            
            months.append(month_label)
            miner_sales.append(monthly_sales.get(month_key, 0))
            hosting_fees.append(monthly_hosting.get(month_key, 0))
        
        # Calculate ROI metrics
        total_investment = sum([deal.value for deal in deals if deal.value]) or 0
        total_return = total_investment * 1.15  # Simplified calculation
        roi_percent = ((total_return - total_investment) / total_investment * 100) if total_investment > 0 else 0
        
        # Calculate breakeven point (simplified)
        monthly_avg = total_return / 12 if total_return > 0 else 0
        breakeven_months = int(total_investment / monthly_avg) if monthly_avg > 0 else 0
        
        # Annual projection
        annual_projection = monthly_avg * 12
        
        return jsonify({
            'success': True,
            'months': months,
            'miner_sales': miner_sales,
            'hosting_fees': hosting_fees,
            'total_investment': round(total_investment, 2),
            'total_return': round(total_return, 2),
            'roi_percent': round(roi_percent, 2),
            'breakeven_months': breakeven_months,
            'annual_projection': round(annual_projection, 2)
        })
        
    except Exception as e:
        logger.error(f"获取收入趋势错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/customer/<int:customer_id>/assets')
def get_customer_assets(customer_id):
    """获取客户矿机资产列表"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Query customer
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Query assets for this customer
        assets = Asset.query.filter_by(customer_id=customer_id).all()
        
        assets_data = []
        total_power = 0
        total_hashrate = 0
        
        for asset in assets:
            # Parse configuration if JSON
            config = {}
            if asset.configuration:
                try:
                    import json
                    config = json.loads(asset.configuration)
                except:
                    pass
            
            power_w = config.get('power_w', 0) or 0
            hashrate_th = config.get('hashrate_th', 0) or 0
            
            total_power += power_w
            total_hashrate += hashrate_th
            
            assets_data.append({
                'id': asset.id,
                'model': asset.model or 'Unknown',
                'quantity': 1,  # Could be extracted from config
                'status': asset.status or 'active',
                'location': asset.location or 'Not specified',
                'power_w': power_w,
                'hashrate_th': hashrate_th,
                'purchase_value': asset.purchase_value or 0,
                'current_value': asset.current_value or 0
            })
        
        # Calculate utilization rate
        total_capacity = customer.mining_capacity or 1
        used_capacity = total_power / 1000000  # Convert W to MW
        utilization_rate = min(100, (used_capacity / total_capacity * 100)) if total_capacity > 0 else 0
        
        return jsonify({
            'success': True,
            'assets': assets_data,
            'total_power': total_power,
            'total_hashrate': total_hashrate,
            'utilization_rate': round(utilization_rate, 2),
            'total_capacity_mw': total_capacity,
            'used_capacity_mw': round(used_capacity, 2)
        })
        
    except Exception as e:
        logger.error(f"获取资产列表错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/customer/<int:customer_id>/deals')
def get_customer_deals(customer_id):
    """获取客户交易历史"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Query customer
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Query deals for this customer
        deals = Deal.query.filter_by(customer_id=customer_id).order_by(Deal.created_at.desc()).all()
        
        deals_data = []
        deal_types = {}
        monthly_counts = {}
        
        for deal in deals:
            # Determine deal type based on attributes
            if deal.mining_capacity and deal.mining_capacity > 0:
                deal_type = 'Hosting'
            elif deal.commission_type:
                deal_type = 'Commission'
            else:
                deal_type = 'Equipment Sale'
            
            # Format deal data
            deals_data.append({
                'id': deal.id,
                'title': deal.title,
                'value': deal.value or 0,
                'status': deal.status.value if deal.status else 'Unknown',
                'deal_type': deal_type,
                'created_at': deal.created_at.strftime('%Y-%m-%d') if deal.created_at else None,
                'expected_close_date': deal.expected_close_date.strftime('%Y-%m-%d') if deal.expected_close_date else None,
                'description': deal.description or '',
                'mining_capacity': deal.mining_capacity or 0,
                'electricity_cost': deal.electricity_cost or 0
            })
            
            # Count by type
            deal_types[deal_type] = deal_types.get(deal_type, 0) + 1
            
            # Count by month
            if deal.created_at:
                month_key = deal.created_at.strftime('%b %Y')
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        # Prepare monthly labels and counts (last 6 months)
        from dateutil.relativedelta import relativedelta
        end_date = datetime.now()
        monthly_labels = []
        monthly_deal_counts = []
        
        for i in range(5, -1, -1):
            month = end_date - relativedelta(months=i)
            month_label = month.strftime('%b %Y')
            monthly_labels.append(month_label)
            monthly_deal_counts.append(monthly_counts.get(month_label, 0))
        
        return jsonify({
            'success': True,
            'deals': deals_data,
            'total_deals': len(deals_data),
            'deal_types': deal_types,
            'monthly_labels': monthly_labels,
            'monthly_counts': monthly_deal_counts
        })
        
    except Exception as e:
        logger.error(f"获取交易历史错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/customer/<int:customer_id>/activities')
def get_customer_activities(customer_id):
    """获取客户活动记录"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Query customer
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 30
        
        # Query activities for this customer
        activities_query = Activity.query.filter_by(customer_id=customer_id).order_by(Activity.created_at.desc())
        activities = activities_query.limit(per_page).offset((page - 1) * per_page).all()
        
        activities_data = []
        for activity in activities:
            activities_data.append({
                'id': activity.id,
                'type': activity.type or '备注',
                'summary': activity.summary,
                'details': activity.details,
                'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M:%S') if activity.created_at else None,
                'created_by': activity.created_by or 'System',
                'customer_id': activity.customer_id,
                'deal_id': activity.deal_id,
                'lead_id': activity.lead_id
            })
        
        return jsonify({
            'success': True,
            'activities': activities_data,
            'total': activities_query.count(),
            'page': page,
            'per_page': per_page,
            'has_more': activities_query.count() > page * per_page
        })
        
    except Exception as e:
        logger.error(f"获取活动记录错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/leads', endpoint='leads')
def leads_page():
    """线索管理页面 - 带KPI、可视化和跟进提醒"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        # 验证status参数，防止无效输入
        status_filter = request.args.get('status', '').upper()
        valid_statuses = ['NEW', 'CONTACTED', 'QUALIFIED', 'NEGOTIATION', 'WON', 'LOST']
        if status_filter and status_filter not in valid_statuses:
            status_filter = None  # 忽略无效的状态参数
        
        leads_query = Lead.query
        if status_filter:
            leads_query = leads_query.filter(Lead.status == LeadStatus[status_filter])
        
        # Apply tenant isolation
        leads = apply_tenant_filter(leads_query.order_by(Lead.created_at.desc()), Lead, user_id).all()
        
        today = datetime.now().date()
        today_followups_query = Lead.query.filter(
            func.date(Lead.next_follow_up) == today
        ).order_by(Lead.next_follow_up)
        today_followups = apply_tenant_filter(today_followups_query, Lead, user_id).all()
        
        all_statuses = [status.name for status in LeadStatus]
        
        return render_template('crm/leads.html',
                             title='线索管理',
                             page='crm_leads',
                             leads=leads,
                             today_followups=today_followups,
                             status=status_filter,
                             all_statuses=all_statuses)
    except Exception as e:
        logger.error(f"线索页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/deals', endpoint='deals')
def deals_page():
    """交易页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/deals.html',
                             title='Deals Management',
                             page='crm_deals')
    except Exception as e:
        logger.error(f"交易页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/api/deals/kpi')
def deals_kpi():
    """获取交易KPI统计数据"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        from sqlalchemy.orm import joinedload
        
        # Apply tenant filter for all queries
        tenant_filter = get_tenant_filter(Deal, user_id)
        
        if tenant_filter is not None:
            # 总交易数量
            total_deals = Deal.query.filter(tenant_filter).count() or 0
            
            # 总交易价值
            total_value = Deal.query.filter(tenant_filter).with_entities(func.sum(Deal.value)).scalar() or 0
            
            # 活跃项目数（状态非COMPLETED/CANCELED）
            active_projects = Deal.query.filter(
                tenant_filter,
                ~Deal.status.in_([DealStatus.COMPLETED, DealStatus.CANCELED])
            ).count() or 0
            
            # 计算平均成交周期（已完成的交易）
            completed_deals = Deal.query.filter(
                tenant_filter,
                Deal.status == DealStatus.COMPLETED,
                Deal.closed_date.isnot(None),
                Deal.created_at.isnot(None)
            ).all()
        else:
            # Owner/Admin can see all data
            # 总交易数量
            total_deals = Deal.query.count() or 0
            
            # 总交易价值
            total_value = Deal.query.with_entities(func.sum(Deal.value)).scalar() or 0
            
            # 活跃项目数（状态非COMPLETED/CANCELED）
            active_projects = Deal.query.filter(
                ~Deal.status.in_([DealStatus.COMPLETED, DealStatus.CANCELED])
            ).count() or 0
            
            # 计算平均成交周期（已完成的交易）
            completed_deals = Deal.query.filter(
                Deal.status == DealStatus.COMPLETED,
                Deal.closed_date.isnot(None),
                Deal.created_at.isnot(None)
            ).all()
        
        if completed_deals:
            total_days = sum([
                (deal.closed_date - deal.created_at).days 
                for deal in completed_deals 
                if deal.closed_date and deal.created_at
            ])
            avg_cycle = total_days / len(completed_deals) if len(completed_deals) > 0 else 0
        else:
            avg_cycle = 0
        
        logger.info(f"Deals KPI: total={total_deals}, value={total_value}, active={active_projects}, avg_cycle={avg_cycle}")
        
        return jsonify({
            'success': True,
            'data': {
                'total_deals': total_deals,
                'total_value': float(total_value),
                'active_projects': active_projects,
                'avg_close_cycle': round(avg_cycle, 1)
            }
        })
        
    except Exception as e:
        logger.error(f"获取交易KPI错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/revenue-trend')
def deals_revenue_trend():
    """获取月度收入趋势数据"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # 获取最近6个月的数据
        now = datetime.now()
        months_data = []
        
        for i in range(5, -1, -1):
            # 计算月份
            target_month = now - timedelta(days=30*i)
            month_start = target_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # 下个月的第一天
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            # 查询该月所有交易 - with tenant filter
            month_deals_query = Deal.query.filter(
                Deal.created_at >= month_start,
                Deal.created_at < month_end
            )
            month_deals = apply_tenant_filter(month_deals_query, Deal, user_id).all()
            
            # 计算总收入和已完成收入
            total_revenue = sum([deal.value or 0 for deal in month_deals])
            completed_revenue = sum([
                deal.value or 0 
                for deal in month_deals 
                if deal.status == DealStatus.COMPLETED
            ])
            
            months_data.append({
                'month': month_start.strftime('%Y-%m'),
                'month_label': month_start.strftime('%m月'),
                'total_revenue': float(total_revenue),
                'completed_revenue': float(completed_revenue)
            })
        
        logger.info(f"Revenue trend calculated for {len(months_data)} months")
        
        return jsonify({
            'success': True,
            'data': months_data
        })
        
    except Exception as e:
        logger.error(f"获取收入趋势错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/mining-stats')
def deals_mining_stats():
    """获取矿场业务统计数据"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # 获取所有有挖矿容量的交易 - with tenant filter
        mining_deals_query = Deal.query.filter(
            Deal.mining_capacity.isnot(None),
            Deal.mining_capacity > 0
        )
        mining_deals = apply_tenant_filter(mining_deals_query, Deal, user_id).all()
        
        # 托管容量统计
        total_capacity = sum([deal.mining_capacity or 0 for deal in mining_deals])
        signed_capacity = sum([
            deal.mining_capacity or 0 
            for deal in mining_deals 
            if deal.status in [DealStatus.SIGNED, DealStatus.COMPLETED]
        ])
        pending_capacity = total_capacity - signed_capacity
        
        # 电费价格分析
        deals_with_electricity = [
            deal for deal in mining_deals 
            if deal.electricity_cost and deal.electricity_cost > 0
        ]
        
        if deals_with_electricity:
            electricity_costs = [deal.electricity_cost for deal in deals_with_electricity]
            avg_electricity = sum(electricity_costs) / len(electricity_costs)
            min_electricity = min(electricity_costs)
            max_electricity = max(electricity_costs)
        else:
            avg_electricity = 0
            min_electricity = 0
            max_electricity = 0
        
        # 电费分布（用于柱状图）
        electricity_distribution = []
        for deal in deals_with_electricity[:10]:  # 前10个项目
            electricity_distribution.append({
                'deal_title': deal.title,
                'electricity_cost': float(deal.electricity_cost or 0)
            })
        
        logger.info(f"Mining stats: capacity={total_capacity}MW, avg_elec={avg_electricity}")
        
        return jsonify({
            'success': True,
            'data': {
                'total_capacity': float(total_capacity),
                'signed_capacity': float(signed_capacity),
                'pending_capacity': float(pending_capacity),
                'avg_electricity_cost': float(avg_electricity),
                'min_electricity_cost': float(min_electricity),
                'max_electricity_cost': float(max_electricity),
                'electricity_distribution': electricity_distribution
            }
        })
        
    except Exception as e:
        logger.error(f"获取矿场统计错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/kanban')
def deals_kanban():
    """获取Kanban看板数据（按状态分组）"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        from sqlalchemy.orm import joinedload
        
        # 预加载customer关系，防止N+1查询 - with tenant filter
        deals_query = Deal.query.options(joinedload(Deal.customer))
        all_deals = apply_tenant_filter(deals_query, Deal, user_id).all()
        
        # 按状态分组
        kanban_data = {}
        
        for status in DealStatus:
            status_deals = [deal for deal in all_deals if deal.status == status]
            
            # 计算该状态的总金额
            status_value = sum([deal.value or 0 for deal in status_deals])
            
            # 格式化交易数据
            deals_list = []
            for deal in status_deals:
                deals_list.append({
                    'id': deal.id,
                    'title': deal.title,
                    'customer_name': deal.customer.name if deal.customer else '未知客户',
                    'value': float(deal.value or 0),
                    'mining_capacity': float(deal.mining_capacity or 0),
                    'expected_close_date': deal.expected_close_date.strftime('%Y-%m-%d') if deal.expected_close_date else None,
                    'status': status.value
                })
            
            kanban_data[status.name] = {
                'status_name': status.value,
                'count': len(status_deals),
                'total_value': float(status_value),
                'deals': deals_list
            }
        
        logger.info(f"Kanban data prepared for {len(DealStatus)} statuses")
        
        return jsonify({
            'success': True,
            'data': kanban_data
        })
        
    except Exception as e:
        logger.error(f"获取Kanban数据错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/top-investments')
def deals_top_investments():
    """获取TOP投资客户排行"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        from sqlalchemy.orm import joinedload
        
        # 获取所有交易，预加载客户关系 - with tenant filter
        deals_query = Deal.query.options(joinedload(Deal.customer))
        all_deals = apply_tenant_filter(deals_query, Deal, user_id).all()
        
        # 按客户聚合投资额
        customer_investments = {}
        for deal in all_deals:
            if deal.customer:
                customer_id = deal.customer.id
                customer_name = deal.customer.name
                
                if customer_id not in customer_investments:
                    customer_investments[customer_id] = {
                        'customer_name': customer_name,
                        'total_investment': 0,
                        'monthly_profit': 0
                    }
                
                customer_investments[customer_id]['total_investment'] += deal.value or 0
                customer_investments[customer_id]['monthly_profit'] += deal.monthly_profit_estimate or 0
        
        # 排序并获取TOP 5
        top_investments = sorted(
            customer_investments.values(),
            key=lambda x: x['total_investment'],
            reverse=True
        )[:5]
        
        # 格式化数据
        top_investments_data = []
        for inv in top_investments:
            top_investments_data.append({
                'customer_name': inv['customer_name'],
                'total_investment': float(inv['total_investment']),
                'monthly_profit': float(inv['monthly_profit'])
            })
        
        logger.info(f"Top investments calculated for {len(top_investments_data)} customers")
        
        return jsonify({
            'success': True,
            'data': top_investments_data
        })
        
    except Exception as e:
        logger.error(f"获取投资排行错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/activities', endpoint='activities')
def activities_page():
    """活动页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/activities.html',
                             title='Activities',
                             page='crm_activities')
    except Exception as e:
        logger.error(f"活动页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/api/activities/stats')
def get_activities_stats():
    """获取活动统计KPI数据"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        from collections import Counter
        
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Get tenant filter for Activity
        activity_filter = get_tenant_filter(Activity, user_id)
        customer_filter = get_tenant_filter(Customer, user_id)
        
        if activity_filter is not None:
            total_activities = Activity.query.filter(activity_filter).count() or 0
            
            today_activities = Activity.query.filter(
                activity_filter,
                func.date(Activity.created_at) == today
            ).count() or 0
            
            week_activities = Activity.query.filter(
                activity_filter,
                Activity.created_at >= week_start
            ).count() or 0
            
            month_activities = Activity.query.filter(
                activity_filter,
                Activity.created_at >= month_start
            ).count() or 0
            
            customer_activity_query = db.session.query(
                Customer.name,
                func.count(Activity.id).label('activity_count')
            ).join(Activity, Activity.customer_id == Customer.id)
            
            if customer_filter is not None:
                customer_activity_query = customer_activity_query.filter(customer_filter)
            
            customer_activity_counts = customer_activity_query\
             .group_by(Customer.id, Customer.name)\
             .order_by(func.count(Activity.id).desc())\
             .first()
            
            type_counts = db.session.query(
                Activity.type,
                func.count(Activity.id).label('count')
            ).filter(activity_filter)\
             .group_by(Activity.type)\
             .order_by(func.count(Activity.id).desc())\
             .first()
        else:
            total_activities = Activity.query.count() or 0
            
            today_activities = Activity.query.filter(
                func.date(Activity.created_at) == today
            ).count() or 0
            
            week_activities = Activity.query.filter(
                Activity.created_at >= week_start
            ).count() or 0
            
            month_activities = Activity.query.filter(
                Activity.created_at >= month_start
            ).count() or 0
            
            customer_activity_counts = db.session.query(
                Customer.name,
                func.count(Activity.id).label('activity_count')
            ).join(Activity, Activity.customer_id == Customer.id)\
             .group_by(Customer.id, Customer.name)\
             .order_by(func.count(Activity.id).desc())\
             .first()
            
            type_counts = db.session.query(
                Activity.type,
                func.count(Activity.id).label('count')
            ).group_by(Activity.type)\
             .order_by(func.count(Activity.id).desc())\
             .first()
        
        most_active_customer = {
            'name': customer_activity_counts[0] if customer_activity_counts else 'N/A',
            'count': int(customer_activity_counts[1]) if customer_activity_counts else 0
        }
        
        most_active_type = {
            'type': type_counts[0] if type_counts else '备注',
            'count': int(type_counts[1]) if type_counts else 0
        }
        
        return jsonify({
            'success': True,
            'total_activities': int(total_activities),
            'today_activities': int(today_activities),
            'week_activities': int(week_activities),
            'month_activities': int(month_activities),
            'most_active_customer': most_active_customer,
            'most_active_type': most_active_type
        })
        
    except Exception as e:
        logger.error(f"获取活动统计错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/activities/heatmap')
def get_activities_heatmap():
    """获取客户互动热力图数据"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Get tenant filter
        customer_filter = get_tenant_filter(Customer, user_id)
        
        customer_activities_query = db.session.query(
            Customer.id,
            Customer.name,
            func.count(Activity.id).label('activity_count')
        ).join(Activity, Activity.customer_id == Customer.id)
        
        if customer_filter is not None:
            customer_activities_query = customer_activities_query.filter(customer_filter)
        
        customer_activities = customer_activities_query\
         .group_by(Customer.id, Customer.name)\
         .order_by(func.count(Activity.id).desc())\
         .limit(10)\
         .all()
        
        heatmap_data = []
        for customer_id, customer_name, activity_count in customer_activities:
            type_distribution = db.session.query(
                Activity.type,
                func.count(Activity.id).label('count')
            ).filter(Activity.customer_id == customer_id)\
             .group_by(Activity.type)\
             .all()
            
            types = {}
            for activity_type, count in type_distribution:
                types[activity_type or '备注'] = int(count)
            
            heatmap_data.append({
                'customer_id': int(customer_id),
                'customer_name': customer_name,
                'activity_count': int(activity_count),
                'type_distribution': types
            })
        
        return jsonify({
            'success': True,
            'data': heatmap_data
        })
        
    except Exception as e:
        logger.error(f"获取热力图数据错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/activities/timeline')
def get_activities_timeline():
    """获取活动时间线数据（过去30天）"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=29)
        
        daily_counts = {}
        for i in range(30):
            date = start_date + timedelta(days=i)
            daily_counts[date.strftime('%Y-%m-%d')] = {
                'total': 0,
                'types': {}
            }
        
        activities_query = Activity.query.filter(
            Activity.created_at >= start_date
        )
        activities = apply_tenant_filter(activities_query, Activity, session.get('user_id')).all()
        
        for activity in activities:
            date_key = activity.created_at.strftime('%Y-%m-%d')
            if date_key in daily_counts:
                daily_counts[date_key]['total'] += 1
                activity_type = activity.type or '备注'
                daily_counts[date_key]['types'][activity_type] = \
                    daily_counts[date_key]['types'].get(activity_type, 0) + 1
        
        timeline_data = []
        for date_str, data in sorted(daily_counts.items()):
            timeline_data.append({
                'date': date_str,
                'total': data['total'],
                'types': data['types']
            })
        
        milestones = []
        user_id = session.get('user_id')
        first_contact_query = Activity.query.order_by(Activity.created_at.asc())
        first_contact = apply_tenant_filter(first_contact_query, Activity, user_id).first()
        if first_contact:
            milestones.append({
                'date': first_contact.created_at.strftime('%Y-%m-%d'),
                'event': '首次接触',
                'description': first_contact.summary
            })
        
        recent_deals_query = Deal.query.filter(
            Deal.status == DealStatus.COMPLETED,
            Deal.created_at >= start_date
        ).order_by(Deal.created_at.desc()).limit(3)
        recent_deals = apply_tenant_filter(recent_deals_query, Deal, user_id).all()
        
        for deal in recent_deals:
            milestones.append({
                'date': deal.created_at.strftime('%Y-%m-%d'),
                'event': '交易成交',
                'description': deal.title
            })
        
        return jsonify({
            'success': True,
            'timeline': timeline_data,
            'milestones': milestones
        })
        
    except Exception as e:
        logger.error(f"获取时间线数据错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/activities/type-trend')
def get_activities_type_trend():
    """获取活动类型趋势（过去7天）"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        
        activity_types = ['备注', '电话', '会议', '邮件', '现场拜访', '创建', '其他']
        
        # Get tenant filter
        activity_filter = get_tenant_filter(Activity, user_id)
        
        trend_data = {
            'dates': [],
            'types': {t: [] for t in activity_types}
        }
        
        for i in range(7):
            date = start_date + timedelta(days=i)
            trend_data['dates'].append(date.strftime('%m-%d'))
            
            for activity_type in activity_types:
                if activity_filter is not None:
                    count = Activity.query.filter(
                        activity_filter,
                        func.date(Activity.created_at) == date,
                        Activity.type == activity_type
                    ).count() or 0
                else:
                    count = Activity.query.filter(
                        func.date(Activity.created_at) == date,
                        Activity.type == activity_type
                    ).count() or 0
                
                trend_data['types'][activity_type].append(int(count))
        
        return jsonify({
            'success': True,
            'data': trend_data
        })
        
    except Exception as e:
        logger.error(f"获取类型趋势错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/broker', endpoint='broker_dashboard')
def broker_dashboard_page():
    """经纪人仪表盘页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/broker_dashboard.html',
                             title='Broker Dashboard',
                             page='crm_broker')
    except Exception as e:
        logger.error(f"经纪人仪表盘错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/broker/deals', endpoint='broker_deals')
def broker_deals_page():
    """经纪人交易页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/broker_deals.html',
                             title='Broker Deals',
                             page='crm_broker_deals')
    except Exception as e:
        logger.error(f"经纪人交易页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/broker/commissions', endpoint='broker_commissions')
def broker_commissions_page():
    """经纪人佣金页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/broker_commissions.html',
                             title='Broker Commissions',
                             page='crm_broker_commissions')
    except Exception as e:
        logger.error(f"经纪人佣金页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

# ==================== Broker API Endpoints ====================

@crm_bp.route('/api/broker/stats')
def broker_stats():
    """经纪人统计KPI - Refactored with service layer"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return error_response('Unauthorized', 401)
        
        # 总交易数（按created_by_id过滤）
        total_deals = Deal.query.filter(Deal.created_by_id == user_id).count() or 0
        
        # 活跃交易数（排除CANCELLED/COMPLETED）
        active_deals = Deal.query.filter(
            Deal.created_by_id == user_id,
            ~Deal.status.in_([DealStatus.CANCELED, DealStatus.COMPLETED])
        ).count() or 0
        
        # 总佣金收入（已支付）- 使用BaseService.safe_float安全转换
        total_commission = BaseService.safe_float(
            db.session.query(func.sum(CommissionRecord.commission_amount))
            .filter(CommissionRecord.created_by_id == user_id, CommissionRecord.paid == True)
            .scalar()
        )
        
        # 待结算佣金（未支付）- 使用BaseService.safe_float安全转换
        pending_commission = BaseService.safe_float(
            db.session.query(func.sum(CommissionRecord.commission_amount))
            .filter(CommissionRecord.created_by_id == user_id, CommissionRecord.paid == False)
            .scalar()
        )
        
        # 本月佣金收入
        current_month = datetime.now().strftime('%Y-%m')
        month_commission = BaseService.safe_float(
            db.session.query(func.sum(CommissionRecord.commission_amount))
            .filter(
                CommissionRecord.created_by_id == user_id,
                CommissionRecord.paid == True,
                CommissionRecord.record_month == current_month
            )
            .scalar()
        )
        
        # 平均佣金金额 - 使用BaseService.safe_float安全转换
        avg_commission = BaseService.safe_float(
            db.session.query(func.avg(CommissionRecord.commission_amount))
            .filter(CommissionRecord.created_by_id == user_id)
            .scalar()
        )
        
        logger.info(f"Broker stats: total={total_deals}, active={active_deals}, total_comm={total_commission}")
        
        # 使用统一成功响应格式
        return success_response(data={
            'total_deals': BaseService.safe_int(total_deals),
            'active_deals': BaseService.safe_int(active_deals),
            'total_commission': total_commission,
            'pending_commission': pending_commission,
            'month_commission': month_commission,
            'avg_commission': avg_commission
        })
        
    except Exception as e:
        logger.error(f"获取经纪人统计错误: {e}")
        return error_response(str(e), 500)

@crm_bp.route('/api/broker/commission-trend')
def broker_commission_trend():
    """佣金收入趋势（过去12个月）"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        # 使用relativedelta正确计算日历月
        current_date = datetime.now()
        months = []
        paid_amounts = []
        unpaid_amounts = []
        
        for i in range(11, -1, -1):
            month_date = current_date - relativedelta(months=i)
            month_key = month_date.strftime('%Y-%m')
            month_label = month_date.strftime('%b %Y')
            
            months.append(month_label)
            
            # 已支付金额
            paid = db.session.query(func.sum(CommissionRecord.commission_amount))\
                .filter(
                    CommissionRecord.created_by_id == user_id,
                    CommissionRecord.record_month == month_key,
                    CommissionRecord.paid == True
                )\
                .scalar() or 0
            
            # 未支付金额
            unpaid = db.session.query(func.sum(CommissionRecord.commission_amount))\
                .filter(
                    CommissionRecord.created_by_id == user_id,
                    CommissionRecord.record_month == month_key,
                    CommissionRecord.paid == False
                )\
                .scalar() or 0
            
            paid_amounts.append(float(paid))
            unpaid_amounts.append(float(unpaid))
        
        return jsonify({
            'success': True,
            'data': {
                'months': months,
                'paid': paid_amounts,
                'unpaid': unpaid_amounts
            }
        })
        
    except Exception as e:
        logger.error(f"获取佣金趋势错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/broker/customer-distribution')
def broker_customer_distribution():
    """客户分布（按矿场位置分组）- Refactored with service layer and geo validation"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return error_response('Unauthorized', 401)
        
        # 按矿场位置分组
        distribution = db.session.query(
            Deal.mining_farm_location,
            func.count(Deal.id).label('count'),
            func.sum(Deal.client_investment).label('total_investment')
        ).filter(Deal.created_by_id == user_id)\
         .group_by(Deal.mining_farm_location)\
         .all()
        
        locations = []
        counts = []
        investments = []
        validated_count = 0
        
        for location, count, investment in distribution:
            # 处理空位置
            loc_name = location or 'Unknown'
            
            # 使用geo服务验证城市是否支持
            is_validated = is_city_supported(loc_name) if loc_name != 'Unknown' else False
            if is_validated:
                validated_count += 1
            
            locations.append(loc_name)
            counts.append(BaseService.safe_int(count))
            investments.append(BaseService.safe_float(investment))
        
        # 使用统一成功响应格式，附带轮询支持
        return success_response_with_polling(data={
            'locations': locations,
            'counts': counts,
            'investments': investments,
            'validated_locations': validated_count,
            'total_locations': len(locations)
        })
        
    except Exception as e:
        logger.error(f"获取客户分布错误: {e}")
        return error_response(str(e), 500)

@crm_bp.route('/api/broker/performance-ranking')
def broker_performance_ranking():
    """业绩排行（TOP 5客户和矿场）"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        # TOP 5客户（按client_investment排序）
        top_customers_query = db.session.query(
            Customer.id,
            Customer.name,
            func.sum(Deal.client_investment).label('total_investment'),
            func.sum(Deal.commission_amount).label('total_commission')
        ).join(Deal, Deal.customer_id == Customer.id)\
         .filter(Deal.created_by_id == user_id)\
         .group_by(Customer.id, Customer.name)\
         .order_by(func.sum(Deal.client_investment).desc())\
         .limit(5)\
         .all()
        
        top_customers = []
        for cust_id, name, investment, commission in top_customers_query:
            top_customers.append({
                'customer_id': cust_id,
                'name': name,
                'investment': float(investment or 0),
                'commission': float(commission or 0)
            })
        
        # TOP 5矿场（按交易数量和总投资）
        top_farms_query = db.session.query(
            Deal.mining_farm_name,
            func.count(Deal.id).label('deal_count'),
            func.sum(Deal.client_investment).label('total_investment')
        ).filter(Deal.created_by_id == user_id)\
         .group_by(Deal.mining_farm_name)\
         .order_by(func.sum(Deal.client_investment).desc())\
         .limit(5)\
         .all()
        
        top_farms = []
        for farm_name, deal_count, investment in top_farms_query:
            top_farms.append({
                'name': farm_name or 'Unknown',
                'deal_count': int(deal_count),
                'investment': float(investment or 0)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'top_customers': top_customers,
                'top_farms': top_farms
            }
        })
        
    except Exception as e:
        logger.error(f"获取业绩排行错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Broker Commissions Page APIs ====================

@crm_bp.route('/api/broker/commissions/stats')
def broker_commissions_stats():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        total_commission = db.session.query(func.sum(CommissionRecord.commission_amount))\
            .filter(CommissionRecord.created_by_id == user_id)\
            .scalar() or 0
        
        paid_commission = db.session.query(func.sum(CommissionRecord.commission_amount))\
            .filter(CommissionRecord.created_by_id == user_id, CommissionRecord.paid == True)\
            .scalar() or 0
        
        unpaid_commission = total_commission - paid_commission
        
        current_month = datetime.now().strftime('%Y-%m')
        this_month_commission = db.session.query(func.sum(CommissionRecord.commission_amount))\
            .filter(
                CommissionRecord.created_by_id == user_id,
                CommissionRecord.record_month == current_month
            )\
            .scalar() or 0
        
        total_records = CommissionRecord.query.filter(CommissionRecord.created_by_id == user_id).count() or 0
        
        avg_monthly_commission = db.session.query(func.avg(CommissionRecord.commission_amount))\
            .filter(CommissionRecord.created_by_id == user_id)\
            .scalar() or 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_commission': float(total_commission),
                'paid_commission': float(paid_commission),
                'unpaid_commission': float(unpaid_commission),
                'this_month_commission': float(this_month_commission),
                'total_records': int(total_records),
                'avg_monthly_commission': float(avg_monthly_commission)
            }
        })
        
    except Exception as e:
        logger.error(f"获取佣金统计错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/broker/commissions/trend')
def broker_commissions_trend():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        current_date = datetime.now()
        months = []
        paid_amounts = []
        unpaid_amounts = []
        
        for i in range(11, -1, -1):
            month_date = current_date - relativedelta(months=i)
            month_key = month_date.strftime('%Y-%m')
            month_label = month_date.strftime('%b %Y')
            
            months.append(month_label)
            
            paid = db.session.query(func.sum(CommissionRecord.commission_amount))\
                .filter(
                    CommissionRecord.created_by_id == user_id,
                    CommissionRecord.record_month == month_key,
                    CommissionRecord.paid == True
                )\
                .scalar() or 0
            
            unpaid = db.session.query(func.sum(CommissionRecord.commission_amount))\
                .filter(
                    CommissionRecord.created_by_id == user_id,
                    CommissionRecord.record_month == month_key,
                    CommissionRecord.paid == False
                )\
                .scalar() or 0
            
            paid_amounts.append(float(paid))
            unpaid_amounts.append(float(unpaid))
        
        return jsonify({
            'success': True,
            'data': {
                'months': months,
                'paid': paid_amounts,
                'unpaid': unpaid_amounts
            }
        })
        
    except Exception as e:
        logger.error(f"获取佣金趋势错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/broker/commissions/settlement-status')
@login_required
@requires_module_access(Module.FINANCE_BTC_SETTLE)
def broker_commissions_settlement_status():
    """佣金结算状态查询
    
    RBAC权限 (FINANCE_BTC_SETTLE):
    - Owner/Admin/Mining_Site_Owner: FULL
    - Client/Customer: READ
    - Guest: NONE
    """
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        settlement_status = db.session.query(
            CommissionRecord.paid,
            func.sum(CommissionRecord.commission_amount).label('total_amount'),
            func.count(CommissionRecord.id).label('count')
        ).filter(CommissionRecord.created_by_id == user_id)\
         .group_by(CommissionRecord.paid)\
         .all()
        
        labels = []
        amounts = []
        counts = []
        
        for paid, total_amount, count in settlement_status:
            labels.append('Paid' if paid else 'Unpaid')
            amounts.append(float(total_amount or 0))
            counts.append(int(count))
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'amounts': amounts,
                'counts': counts
            }
        })
        
    except Exception as e:
        logger.error(f"获取结算状态错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/broker/commissions/list')
def broker_commissions_list():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        paid_filter = request.args.get('paid', None)
        
        query = CommissionRecord.query.filter(CommissionRecord.created_by_id == user_id)
        
        if paid_filter == 'true':
            query = query.filter(CommissionRecord.paid == True)
        elif paid_filter == 'false':
            query = query.filter(CommissionRecord.paid == False)
        
        records = query.order_by(CommissionRecord.record_date.desc()).all()
        
        commissions_data = []
        for record in records:
            deal = Deal.query.get(record.deal_id)
            customer = Customer.query.get(record.customer_id)
            
            commissions_data.append({
                'id': record.id,
                'deal_id': record.deal_id,
                'customer_id': record.customer_id,
                'customer_name': customer.name if customer else 'Unknown',
                'mining_farm_name': deal.mining_farm_name if deal else 'Unknown',
                'commission_amount': float(record.commission_amount or 0),
                'paid': record.paid,
                'record_month': record.record_month,
                'payment_date': record.paid_date.strftime('%Y-%m-%d') if record.paid_date else None,
                'record_date': record.record_date.strftime('%Y-%m-%d') if record.record_date else None,
                'commission_type': record.commission_type,
                'notes': record.notes or ''
            })
        
        return jsonify({
            'success': True,
            'data': commissions_data,
            'total': len(commissions_data)
        })
        
    except Exception as e:
        logger.error(f"获取佣金列表错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Broker Deals Page APIs ====================

@crm_bp.route('/api/broker/deals/stats')
def broker_deals_stats():
    """交易统计KPI - 用于broker_deals.html页面"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        # 总交易数
        total_deals = Deal.query.filter(Deal.created_by_id == user_id).count() or 0
        
        # 活跃交易数（排除CANCELLED和COMPLETED）
        active_deals = Deal.query.filter(
            Deal.created_by_id == user_id,
            ~Deal.status.in_([DealStatus.CANCELED, DealStatus.COMPLETED])
        ).count() or 0
        
        # 总投资金额（client_investment）
        total_investment = db.session.query(func.sum(Deal.client_investment))\
            .filter(Deal.created_by_id == user_id)\
            .scalar() or 0
        
        # 总佣金收入（CommissionRecord已支付）
        total_commission = db.session.query(func.sum(CommissionRecord.commission_amount))\
            .filter(CommissionRecord.created_by_id == user_id, CommissionRecord.paid == True)\
            .scalar() or 0
        
        # 平均交易金额
        avg_deal_value = db.session.query(func.avg(Deal.client_investment))\
            .filter(Deal.created_by_id == user_id)\
            .scalar() or 0
        
        # 本月新增交易数
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_deals_this_month = Deal.query.filter(
            Deal.created_by_id == user_id,
            Deal.created_at >= current_month_start
        ).count() or 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_deals': int(total_deals),
                'active_deals': int(active_deals),
                'total_investment': float(total_investment),
                'total_commission': float(total_commission),
                'avg_deal_value': float(avg_deal_value),
                'new_deals_this_month': int(new_deals_this_month)
            }
        })
        
    except Exception as e:
        logger.error(f"获取broker deals统计错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/broker/deals/capacity')
def broker_deals_capacity():
    """托管容量统计 - 按矿场分组"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        # 按矿场分组统计容量和交易数量
        capacity_data = db.session.query(
            Deal.mining_farm_name,
            func.count(Deal.id).label('deal_count'),
            func.sum(Deal.client_investment).label('total_investment')
        ).filter(Deal.created_by_id == user_id)\
         .group_by(Deal.mining_farm_name)\
         .order_by(func.sum(Deal.client_investment).desc())\
         .all()
        
        farms = []
        deal_counts = []
        investments = []
        
        for farm_name, deal_count, investment in capacity_data:
            farms.append(farm_name or 'Unknown')
            deal_counts.append(int(deal_count))
            investments.append(float(investment or 0))
        
        return jsonify({
            'success': True,
            'data': {
                'farms': farms,
                'deal_counts': deal_counts,
                'investments': investments
            }
        })
        
    except Exception as e:
        logger.error(f"获取托管容量统计错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/broker/deals/revenue-trend')
def broker_deals_revenue_trend():
    """收益趋势 - 投资金额vs佣金收入（过去12个月）"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        # 使用relativedelta正确计算日历月
        current_date = datetime.now()
        months = []
        investment_amounts = []
        commission_amounts = []
        
        for i in range(11, -1, -1):
            month_date = current_date - relativedelta(months=i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = month_start + relativedelta(months=1)
            month_label = month_date.strftime('%b %Y')
            month_key = month_date.strftime('%Y-%m')
            
            months.append(month_label)
            
            # 该月的投资金额（按创建日期）
            investment = db.session.query(func.sum(Deal.client_investment))\
                .filter(
                    Deal.created_by_id == user_id,
                    Deal.created_at >= month_start,
                    Deal.created_at < next_month
                )\
                .scalar() or 0
            
            # 该月的佣金收入（按record_month）
            commission = db.session.query(func.sum(CommissionRecord.commission_amount))\
                .filter(
                    CommissionRecord.created_by_id == user_id,
                    CommissionRecord.record_month == month_key,
                    CommissionRecord.paid == True
                )\
                .scalar() or 0
            
            investment_amounts.append(float(investment))
            commission_amounts.append(float(commission))
        
        return jsonify({
            'success': True,
            'data': {
                'months': months,
                'investment': investment_amounts,
                'commission': commission_amounts
            }
        })
        
    except Exception as e:
        logger.error(f"获取收益趋势错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/broker/deals/list')
def broker_deals_list():
    """交易列表 - 支持状态过滤"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        # 获取过滤参数
        status_filter = request.args.get('status', None)
        
        # 构建查询
        query = Deal.query.filter(Deal.created_by_id == user_id)
        
        # 应用状态过滤
        if status_filter:
            try:
                status_enum = DealStatus[status_filter.upper()]
                query = query.filter(Deal.status == status_enum)
            except KeyError:
                logger.warning(f"Invalid status filter: {status_filter}")
        
        # 按创建时间倒序排列
        deals = query.order_by(Deal.created_at.desc()).all()
        
        deals_data = []
        for deal in deals:
            # 获取客户名称
            customer = Customer.query.get(deal.customer_id)
            customer_name = customer.name if customer else 'Unknown'
            
            # 计算佣金金额
            if deal.commission_type == 'percentage' and deal.commission_rate and deal.client_investment:
                commission_amount = (deal.commission_rate * deal.client_investment / 100)
            elif deal.commission_type == 'fixed' and deal.commission_amount:
                commission_amount = deal.commission_amount
            else:
                commission_amount = 0
            
            deals_data.append({
                'id': deal.id,
                'customer_id': deal.customer_id,
                'customer_name': customer_name,
                'mining_farm_name': deal.mining_farm_name or 'Unknown',
                'client_investment': float(deal.client_investment or 0),
                'commission_type': deal.commission_type,
                'commission_rate': float(deal.commission_rate or 0),
                'commission_amount': float(commission_amount),
                'status': deal.status.name,
                'created_at': deal.created_at.strftime('%Y-%m-%d')
            })
        
        return jsonify({
            'success': True,
            'data': deals_data,
            'total': len(deals_data)
        })
        
    except Exception as e:
        logger.error(f"获取交易列表错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/broker/recent-deals')
def broker_recent_deals():
    """最近交易（最近10个broker交易）"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        # 查询最近10个交易
        recent_deals = Deal.query\
            .filter(Deal.created_by_id == user_id)\
            .order_by(Deal.created_at.desc())\
            .limit(10)\
            .all()
        
        deals_data = []
        for deal in recent_deals:
            # 获取客户名称
            customer_name = deal.customer.name if deal.customer else 'Unknown'
            
            # 处理状态（枚举类型）
            status_value = deal.status.value if deal.status else 'Unknown'
            
            deals_data.append({
                'id': deal.id,
                'customer_id': deal.customer_id,
                'customer_name': customer_name,
                'mining_farm_name': deal.mining_farm_name or '-',
                'mining_farm_location': deal.mining_farm_location or '-',
                'client_investment': float(deal.client_investment or 0),
                'commission_type': deal.commission_type,
                'commission_rate': float(deal.commission_rate or 0),
                'commission_amount': float(deal.commission_amount or 0),
                'status': status_value,
                'created_at': deal.created_at.strftime('%Y-%m-%d') if deal.created_at else None
            })
        
        return jsonify({
            'success': True,
            'data': deals_data
        })
        
    except Exception as e:
        logger.error(f"获取最近交易错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/customer/<int:customer_id>', endpoint='customer_detail')
def customer_detail_page(customer_id):
    """客户详情页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        # Query customer from database
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            flash('Access denied', 'error')
            return redirect(url_for('crm.customers'))
        
        return render_template('crm/customer_detail.html',
                             title='Customer Detail',
                             page='crm_customer_detail',
                             customer=customer,
                             customer_id=customer_id)
    except Exception as e:
        logger.error(f"客户详情页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/customer/new', methods=['GET', 'POST'], endpoint='new_customer')
def new_customer_page():
    """新建客户页面和创建处理"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        # Handle GET request - show form
        if request.method == 'GET':
            return render_template('crm/customer_form.html',
                                 title='New Customer',
                                 page='crm_new_customer')
        
        # Handle POST request - create customer
        name = request.form.get('name', '').strip()
        company = request.form.get('company', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        customer_type = request.form.get('customer_type', '企业')
        tags = request.form.get('tags', '').strip()
        mining_capacity = request.form.get('mining_capacity', type=float)
        
        # Validate required fields
        if not name:
            flash('客户名称为必填项', 'error')
            return render_template('crm/customer_form.html',
                                 title='New Customer',
                                 page='crm_new_customer')
        
        # Create new customer
        new_customer = Customer(
            name=name,
            company=company,
            email=email,
            phone=phone,
            address=address,
            customer_type=customer_type,
            tags=tags,
            mining_capacity=mining_capacity,
            created_by_id=user_id
        )
        
        db.session.add(new_customer)
        db.session.commit()
        
        # Handle calculator access if granted
        if request.form.get('grant_calculator_access') == 'yes':
            access_days = int(request.form.get('access_days', 30))
            # Create user access for calculator
            from models import UserAccess
            
            # Check if user already exists with this email
            existing_user = UserAccess.query.filter_by(email=email).first()
            if not existing_user:
                user_access = UserAccess(
                    name=name,
                    email=email,
                    access_days=access_days,
                    role='customer',
                    notes=f'CRM客户: {name}'
                )
                db.session.add(user_access)
                db.session.commit()
        
        flash(f'客户 {name} 创建成功', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=new_customer.id))
        
    except Exception as e:
        logger.error(f"新建客户错误: {e}")
        db.session.rollback()
        flash('创建客户失败，请重试', 'error')
        return redirect(url_for('crm.customers'))

@crm_bp.route('/customer/<int:customer_id>/edit', endpoint='edit_customer')
def edit_customer_page(customer_id):
    """编辑客户页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/customer_form.html',
                             title='Edit Customer',
                             page='crm_edit_customer',
                             customer_id=customer_id)
    except Exception as e:
        logger.error(f"编辑客户页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/lead/<int:lead_id>', endpoint='lead_detail')
def lead_detail_page(lead_id):
    """商机详情页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        # 从数据库加载lead对象 - 预加载activities关系以避免NaN
        from sqlalchemy.orm import joinedload
        lead = Lead.query.options(joinedload(Lead.activities)).get_or_404(lead_id)
        
        # Verify tenant access
        if not verify_resource_access(lead):
            flash('Access denied', 'error')
            return redirect(url_for('crm.leads'))
        
        return render_template('crm/lead_detail.html',
                             title=f'Lead Detail - {lead.title}',
                             page='crm_lead_detail',
                             lead=lead)
    except Exception as e:
        logger.error(f"商机详情页面错误: {e}")
        flash('无法加载商机详情', 'error')
        return redirect(url_for('crm.leads'))

@crm_bp.route('/lead/<int:lead_id>/status', methods=['POST'], endpoint='update_lead_status')
def update_lead_status(lead_id):
    """更新商机状态"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        lead = Lead.query.get_or_404(lead_id)
        
        # Verify tenant access
        if not verify_resource_access(lead):
            flash('Access denied', 'error')
            return redirect(url_for('crm.leads'))
        
        # 获取表单数据
        new_status_name = request.form.get('status')
        status_comment = request.form.get('status_comment', '')
        
        # 更新状态
        if new_status_name:
            try:
                new_status = LeadStatus[new_status_name]
                old_status = lead.status
                lead.status = new_status
                
                # 创建状态变更活动记录
                if status_comment:
                    activity_summary = f"状态更新: {old_status.value} → {new_status.value}"
                    activity = Activity(
                        customer_id=lead.customer_id,
                        lead_id=lead.id,
                        type='状态变更',
                        summary=activity_summary,
                        details=status_comment,
                        created_by=session.get('email', 'System')
                    )
                    db.session.add(activity)
                
                db.session.commit()
                flash(f'商机状态已更新为: {new_status.value}', 'success')
            except KeyError:
                flash('无效的状态值', 'error')
        
        return redirect(url_for('crm.lead_detail', lead_id=lead_id))
        
    except Exception as e:
        logger.error(f"更新商机状态错误: {e}")
        db.session.rollback()
        flash('更新状态失败', 'error')
        return redirect(url_for('crm.lead_detail', lead_id=lead_id))

@crm_bp.route('/activity/new', methods=['POST'], endpoint='new_activity')
def create_activity():
    """创建新活动记录"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # 获取JSON数据
        data = request.get_json()
        
        # 创建新活动
        activity = Activity(
            customer_id=data.get('customer_id'),
            lead_id=data.get('lead_id'),
            type=data.get('type'),
            summary=data.get('summary'),
            details=data.get('details'),
            created_by=session.get('email', 'System')
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'activity': {
                'id': activity.id,
                'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M'),
                'created_by': activity.created_by
            }
        })
        
    except Exception as e:
        logger.error(f"创建活动记录错误: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@crm_bp.route('/customer/<int:customer_id>/lead/new', endpoint='new_lead')
def new_lead_page(customer_id):
    """新建商机页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        # Query customer object for template breadcrumb
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            flash('Access denied', 'error')
            return redirect(url_for('crm.customers'))
        
        return render_template('crm/lead_form.html',
                             title='New Lead',
                             page='crm_new_lead',
                             customer_id=customer_id,
                             customer=customer)
    except Exception as e:
        logger.error(f"新建商机页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/lead/<int:lead_id>/edit', endpoint='edit_lead')
def edit_lead_page(lead_id):
    """编辑商机页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/lead_form.html',
                             title='Edit Lead',
                             page='crm_edit_lead',
                             lead_id=lead_id)
    except Exception as e:
        logger.error(f"编辑商机页面错误: {e}")
        return redirect(url_for('crm.leads'))

@crm_bp.route('/deal/<int:deal_id>', endpoint='deal_detail')
def deal_detail_page(deal_id):
    """交易详情页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        deal = Deal.query.get_or_404(deal_id)
        
        # Verify tenant access
        if not verify_resource_access(deal):
            flash('Access denied', 'error')
            return redirect(url_for('crm.deals'))
        
        return render_template('crm/deal_detail.html',
                             title='Deal Detail',
                             page='crm_deal_detail',
                             deal=deal)
    except Exception as e:
        logger.error(f"交易详情页面错误: {e}")
        return redirect(url_for('crm.deals'))

@crm_bp.route('/customer/<int:customer_id>/deal/new', endpoint='new_deal')
def new_deal_page(customer_id):
    """新建交易页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        # Query customer object for template breadcrumb
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            flash('Access denied', 'error')
            return redirect(url_for('crm.customers'))
        
        return render_template('crm/deal_form.html',
                             title='New Deal',
                             page='crm_new_deal',
                             customer_id=customer_id,
                             customer=customer)
    except Exception as e:
        logger.error(f"新建交易页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/customer/<int:customer_id>/contact/new', endpoint='new_contact')
def new_contact_page(customer_id):
    """新建联系人页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        # Query customer object for template breadcrumb
        customer = Customer.query.get_or_404(customer_id)
        
        # Verify tenant access
        if not verify_resource_access(customer):
            flash('Access denied', 'error')
            return redirect(url_for('crm.customers'))
        
        return render_template('crm/contact_form.html',
                             title='New Contact',
                             page='crm_new_contact',
                             customer_id=customer_id,
                             customer=customer)
    except Exception as e:
        logger.error(f"新建联系人页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/customer/<int:customer_id>/contact/<int:contact_id>/edit', endpoint='edit_contact')
def edit_contact_page(customer_id, contact_id):
    """编辑联系人页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/contact_form.html',
                             title='Edit Contact',
                             page='crm_edit_contact',
                             customer_id=customer_id,
                             contact_id=contact_id)
    except Exception as e:
        logger.error(f"编辑联系人页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/customer/<int:customer_id>/notes', methods=['POST'], endpoint='update_customer_notes')
def update_customer_notes(customer_id):
    """更新客户备注"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        flash('备注已更新', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=customer_id))
    except Exception as e:
        logger.error(f"更新客户备注错误: {e}")
        flash('更新备注失败', 'error')
        return redirect(url_for('crm.customer_detail', customer_id=customer_id))

@crm_bp.route('/api/geo/cities')
def get_cities():
    """获取所有支持的城市列表 - Get all supported cities"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return error_response('Unauthorized', 401)
        
        cities = get_all_cities()
        
        return success_response(data={
            'cities': cities,
            'count': len(cities),
            'regions': {
                'china': get_region_cities('china'),
                'asia': get_region_cities('asia'),
                'international': get_region_cities('international')
            }
        })
    except Exception as e:
        logger.error(f"获取城市列表错误: {e}")
        return error_response(str(e), 500)

@crm_bp.route('/api/geo/coordinates/<city_name>')
def get_coordinates(city_name):
    """获取指定城市的坐标 - Get coordinates for a specific city"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return error_response('Unauthorized', 401)
        
        if not is_city_supported(city_name):
            return error_response(f'City {city_name} not supported', 404)
        
        coords = get_city_coordinates(city_name)
        
        return success_response(data={
            'city': city_name,
            'latitude': coords[0],
            'longitude': coords[1]
        })
    except Exception as e:
        logger.error(f"获取城市坐标错误: {e}")
        return error_response(str(e), 500)

@crm_bp.route('/api/leads')
def get_leads():
    """获取潜在客户"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Query real leads from database - with tenant filter
        user_id = session.get('user_id')
        leads = apply_tenant_filter(Lead.query.order_by(Lead.created_at.desc()), Lead, user_id).all()
        
        leads_data = []
        for lead in leads:
            # Get last activity for this lead
            last_activity = Activity.query.filter_by(lead_id=lead.id).order_by(Activity.created_at.desc()).first()
            
            leads_data.append({
                'id': lead.id,
                'name': lead.name,
                'email': lead.email,
                'phone': lead.phone,
                'source': lead.source or 'unknown',
                'status': lead.status,
                'interest_level': lead.interest_level or 'medium',
                'estimated_value': lead.estimated_value or 0,
                'created_date': lead.created_at.strftime('%Y-%m-%d') if lead.created_at else None,
                'last_contact': last_activity.created_at.strftime('%Y-%m-%d') if last_activity else None,
                'next_followup': lead.next_follow_up.strftime('%Y-%m-%d') if lead.next_follow_up else None
            })
        
        return jsonify({
            'success': True,
            'data': leads_data,
            'total': len(leads_data)
        })
        
    except Exception as e:
        logger.error(f"获取潜在客户错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/sales-stats')
def get_sales_stats():
    """获取销售统计"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Calculate real statistics from database with tenant filter
        # Get current month's date range
        now = datetime.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get tenant filters
        deal_filter = get_tenant_filter(Deal, user_id)
        customer_filter = get_tenant_filter(Customer, user_id)
        lead_filter = get_tenant_filter(Lead, user_id)
        
        if deal_filter is not None:
            # Monthly revenue from deals closed this month
            monthly_revenue = Deal.query.filter(
                deal_filter,
                Deal.created_at >= first_day_of_month
            ).with_entities(func.sum(Deal.value)).scalar() or 0
            
            # Total pipeline value (all deals)
            pipeline_value = Deal.query.filter(deal_filter).with_entities(func.sum(Deal.value)).scalar() or 0
            
            # Average deal size
            total_deals = Deal.query.filter(deal_filter).count() or 1
        else:
            # Monthly revenue from deals closed this month
            monthly_revenue = Deal.query.filter(
                Deal.created_at >= first_day_of_month
            ).with_entities(func.sum(Deal.value)).scalar() or 0
            
            # Total pipeline value (all deals)
            pipeline_value = Deal.query.with_entities(func.sum(Deal.value)).scalar() or 0
            
            # Average deal size
            total_deals = Deal.query.count() or 1
        
        average_deal_size = pipeline_value / total_deals if total_deals > 0 else 0
        
        if customer_filter is not None:
            # Active customers count
            active_customers = Customer.query.filter(customer_filter, Customer.status == 'active').count() or 0
        else:
            # Active customers count
            active_customers = Customer.query.filter_by(status='active').count() or 0
        
        if lead_filter is not None:
            # New leads this month
            new_leads = Lead.query.filter(lead_filter, Lead.created_at >= first_day_of_month).count() or 0
            
            # Conversion rate (won deals / total leads)
            won_deals_count = Lead.query.filter(lead_filter).filter_by(status='WON').count() or 0
            total_leads = Lead.query.filter(lead_filter).count() or 1
        else:
            # New leads this month
            new_leads = Lead.query.filter(Lead.created_at >= first_day_of_month).count() or 0
            
            # Conversion rate (won deals / total leads)
            won_deals_count = Lead.query.filter_by(status='WON').count() or 0
            total_leads = Lead.query.count() or 1
        conversion_rate = won_deals_count / total_leads if total_leads > 0 else 0
        
        # Top performers (customers by revenue)
        top_performers = []
        top_customers = db.session.query(
            Customer.name,
            func.sum(Deal.value).label('revenue')
        ).join(Deal, Customer.id == Deal.customer_id).group_by(
            Customer.id, Customer.name
        ).order_by(func.sum(Deal.value).desc()).limit(3).all()
        
        for customer in top_customers:
            top_performers.append({
                'name': customer.name,
                'revenue': customer.revenue or 0
            })
        
        stats_data = {
            'success': True,
            'data': {
                'monthly_revenue': monthly_revenue,
                'monthly_target': 50000.00,  # This could be configurable
                'active_customers': active_customers,
                'new_leads': new_leads,
                'conversion_rate': round(conversion_rate, 2),
                'average_deal_size': round(average_deal_size, 2),
                'pipeline_value': pipeline_value,
                'top_performers': top_performers
            }
        }
        
        return jsonify(stats_data)
        
    except Exception as e:
        logger.error(f"获取销售统计错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/add-note', methods=['POST'])
def add_customer_note():
    """添加客户备注"""
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        content = data.get('content', '').strip()
        
        if not customer_id or not content:
            return jsonify({
                'success': False,
                'error': '客户ID和备注内容不能为空'
            }), 400
        
        # 模拟保存备注
        note = {
            'id': 999,  # 模拟生成的ID
            'customer_id': customer_id,
            'content': content,
            'author': session.get('user_email', 'Unknown'),
            'created_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': note,
            'message': '备注添加成功'
        })
        
    except Exception as e:
        logger.error(f"添加客户备注错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/invoices', endpoint='invoices')
def invoices_page():
    """发票管理页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/invoices.html',
                             title='Invoice Management',
                             page='crm_invoices')
    except Exception as e:
        logger.error(f"发票页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/assets', endpoint='assets')
def assets_page():
    """资产管理页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
        
        return render_template('crm/assets.html',
                             title='Asset Management',
                             page='crm_assets')
    except Exception as e:
        logger.error(f"资产页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/api/invoices')
def get_invoices():
    """获取发票列表 - 从数据库读取真实数据"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Build query with user filtering
        invoices_query = Invoice.query.filter(Invoice.created_by_id == user_id)
        
        # Apply status filter if provided
        status_filter = request.args.get('status', '').strip()
        if status_filter:
            invoices_query = invoices_query.filter(Invoice.status == status_filter)
        
        # Fetch invoices from database
        invoices = invoices_query.order_by(Invoice.created_at.desc()).all()
        
        invoices_data = []
        for invoice in invoices:
            invoices_data.append({
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'customer_id': invoice.customer_id,
                'customer_name': invoice.customer.name if invoice.customer else 'N/A',
                'deal_id': invoice.deal_id,
                'status': invoice.status,
                'amount': invoice.amount,
                'tax_amount': invoice.tax_amount,
                'total_amount': invoice.total_amount,
                'currency': invoice.currency,
                'issue_date': invoice.issue_date.strftime('%Y-%m-%d') if invoice.issue_date else None,
                'due_date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else None,
                'paid_date': invoice.paid_date.strftime('%Y-%m-%d') if invoice.paid_date else None,
                'description': invoice.description,
                'notes': invoice.notes
            })
        
        return jsonify({
            'success': True,
            'data': invoices_data,
            'total': len(invoices_data)
        })
        
    except Exception as e:
        logger.error(f"获取发票列表错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/invoices/stats')
def get_invoice_stats():
    """财务统计KPI - 发票总览数据"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # 总收入 - 所有已支付发票（按用户过滤）
        total_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id,
            Invoice.status == 'paid'
        ).scalar() or 0
        
        # 待收款金额 - sent状态发票（按用户过滤）
        accounts_receivable = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id,
            Invoice.status == 'sent'
        ).scalar() or 0
        
        # 逾期金额 - overdue状态发票（按用户过滤）
        overdue_amount = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id,
            Invoice.status == 'overdue'
        ).scalar() or 0
        
        # 本月收入 - 当月已支付发票（按用户过滤）
        now = datetime.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id,
            Invoice.status == 'paid',
            Invoice.paid_date >= first_day_of_month
        ).scalar() or 0
        
        # 发票总数按状态分组（按用户过滤）
        invoice_counts = {}
        for status in ['draft', 'sent', 'paid', 'overdue', 'cancelled']:
            count = Invoice.query.filter(
                Invoice.created_by_id == user_id,
                Invoice.status == status
            ).count() or 0
            invoice_counts[status] = count
        
        # 平均发票金额（按用户过滤）
        total_invoices = Invoice.query.filter(Invoice.created_by_id == user_id).count() or 1
        avg_invoice_amount = db.session.query(func.avg(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_revenue': float(total_revenue),
                'accounts_receivable': float(accounts_receivable),
                'overdue_amount': float(overdue_amount),
                'monthly_revenue': float(monthly_revenue),
                'invoice_counts': invoice_counts,
                'total_invoices': total_invoices,
                'avg_invoice_amount': float(avg_invoice_amount)
            }
        })
        
    except Exception as e:
        logger.error(f"获取发票统计错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/invoices/revenue-trend')
def get_revenue_trend():
    """收款趋势 - 过去12个月的收款数据"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # 计算过去12个月 - 使用relativedelta确保日历月准确
        current_date = datetime.now()
        months_data = []
        
        for i in range(11, -1, -1):
            # 从11个月前到当月，使用relativedelta计算准确的日历月
            month_date = current_date - relativedelta(months=i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # 下月初 - 使用relativedelta确保跨年等边界情况正确
            next_month = month_start + relativedelta(months=1)
            
            # 按月份边界过滤该月的已支付发票（按用户过滤）
            monthly_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
                Invoice.created_by_id == user_id,
                Invoice.status == 'paid',
                Invoice.paid_date >= month_start,
                Invoice.paid_date < next_month
            ).scalar() or 0
            
            monthly_count = Invoice.query.filter(
                Invoice.created_by_id == user_id,
                Invoice.status == 'paid',
                Invoice.paid_date >= month_start,
                Invoice.paid_date < next_month
            ).count() or 0
            
            months_data.append({
                'month': month_start.strftime('%Y-%m'),
                'month_label': month_start.strftime('%b %Y'),
                'revenue': float(monthly_revenue),
                'count': monthly_count
            })
        
        return jsonify({
            'success': True,
            'data': months_data
        })
        
    except Exception as e:
        logger.error(f"获取收款趋势错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/invoices/aging')
def get_invoice_aging():
    """账龄分析 - 基于due_date和当前日期计算"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        now = datetime.now()
        
        # 0-30天账龄（只计算应收账款：sent和overdue状态，按用户过滤）
        aging_0_30_amount = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id,
            Invoice.status.in_(['sent', 'overdue']),
            Invoice.due_date >= now - timedelta(days=30)
        ).scalar() or 0
        
        aging_0_30_count = Invoice.query.filter(
            Invoice.created_by_id == user_id,
            Invoice.status.in_(['sent', 'overdue']),
            Invoice.due_date >= now - timedelta(days=30)
        ).count() or 0
        
        # 31-60天账龄（按用户过滤）
        aging_31_60_amount = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id,
            Invoice.status.in_(['sent', 'overdue']),
            Invoice.due_date >= now - timedelta(days=60),
            Invoice.due_date < now - timedelta(days=30)
        ).scalar() or 0
        
        aging_31_60_count = Invoice.query.filter(
            Invoice.created_by_id == user_id,
            Invoice.status.in_(['sent', 'overdue']),
            Invoice.due_date >= now - timedelta(days=60),
            Invoice.due_date < now - timedelta(days=30)
        ).count() or 0
        
        # 61-90天账龄（按用户过滤）
        aging_61_90_amount = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id,
            Invoice.status.in_(['sent', 'overdue']),
            Invoice.due_date >= now - timedelta(days=90),
            Invoice.due_date < now - timedelta(days=60)
        ).scalar() or 0
        
        aging_61_90_count = Invoice.query.filter(
            Invoice.created_by_id == user_id,
            Invoice.status.in_(['sent', 'overdue']),
            Invoice.due_date >= now - timedelta(days=90),
            Invoice.due_date < now - timedelta(days=60)
        ).count() or 0
        
        # 90天以上账龄（按用户过滤）
        aging_90_plus_amount = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.created_by_id == user_id,
            Invoice.status.in_(['sent', 'overdue']),
            Invoice.due_date < now - timedelta(days=90)
        ).scalar() or 0
        
        aging_90_plus_count = Invoice.query.filter(
            Invoice.created_by_id == user_id,
            Invoice.status.in_(['sent', 'overdue']),
            Invoice.due_date < now - timedelta(days=90)
        ).count() or 0
        
        return jsonify({
            'success': True,
            'data': {
                'aging_0_30': {
                    'amount': float(aging_0_30_amount),
                    'count': aging_0_30_count
                },
                'aging_31_60': {
                    'amount': float(aging_31_60_amount),
                    'count': aging_31_60_count
                },
                'aging_61_90': {
                    'amount': float(aging_61_90_amount),
                    'count': aging_61_90_count
                },
                'aging_90_plus': {
                    'amount': float(aging_90_plus_amount),
                    'count': aging_90_plus_count
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取账龄分析错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/invoices/top-customers')
def get_top_customers():
    """TOP 5付款客户 - 按总支付金额排序"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # 查询每个客户的总支付金额（只统计已支付发票，按用户过滤）
        top_customers = db.session.query(
            Customer.name,
            func.sum(Invoice.total_amount).label('total_paid')
        ).join(Invoice, Invoice.customer_id == Customer.id).filter(
            Invoice.created_by_id == user_id,
            Invoice.status == 'paid'
        ).group_by(Customer.id, Customer.name).order_by(
            func.sum(Invoice.total_amount).desc()
        ).limit(5).all()
        
        # 格式化数据
        customers_data = []
        for customer_name, total_paid in top_customers:
            customers_data.append({
                'customer_name': customer_name,
                'total_amount': float(total_paid or 0)
            })
        
        return jsonify({
            'success': True,
            'data': customers_data
        })
        
    except Exception as e:
        logger.error(f"获取TOP客户错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/assets')
def get_assets():
    """获取资产列表 - 从数据库读取真实数据，支持类型和状态过滤"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Build query with filters
        assets_query = Asset.query.filter_by(created_by_id=user_id)
        
        # Filter by type
        asset_type = request.args.get('type', '').strip()
        if asset_type:
            assets_query = assets_query.filter_by(asset_type=asset_type)
        
        # Filter by status
        status = request.args.get('status', '').strip()
        if status:
            assets_query = assets_query.filter_by(status=status)
        
        # Fetch assets from database
        assets = assets_query.order_by(Asset.created_at.desc()).all()
        
        assets_data = []
        for asset in assets:
            assets_data.append({
                'id': asset.id,
                'customer_id': asset.customer_id,
                'customer_name': asset.customer.name if asset.customer else 'N/A',
                'deal_id': asset.deal_id,
                'asset_type': asset.asset_type,
                'asset_name': asset.asset_name,
                'serial_number': asset.serial_number,
                'model': asset.model,
                'status': asset.status,
                'purchase_value': asset.purchase_value,
                'current_value': asset.current_value,
                'currency': asset.currency,
                'location': asset.location,
                'purchase_date': asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else None,
                'warranty_expiry': asset.warranty_expiry.strftime('%Y-%m-%d') if asset.warranty_expiry else None,
                'description': asset.description,
                'notes': asset.notes
            })
        
        return jsonify({
            'success': True,
            'data': assets_data,
            'total': len(assets_data)
        })
        
    except Exception as e:
        logger.error(f"获取资产列表错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/assets/stats')
def get_asset_stats():
    """资产统计KPI - A. GET /crm/api/assets/stats"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Query all assets for current user
        assets = Asset.query.filter_by(created_by_id=user_id).all()
        
        # Calculate statistics
        total_assets = len(assets)
        active_assets = sum(1 for a in assets if a.status == 'active')
        maintenance_assets = sum(1 for a in assets if a.status == 'maintenance')
        total_value = sum(float(a.current_value or 0) for a in assets)
        
        # Group by type
        type_stats = {}
        for asset in assets:
            asset_type = asset.asset_type or 'unknown'
            if asset_type not in type_stats:
                type_stats[asset_type] = {'count': 0, 'value': 0}
            type_stats[asset_type]['count'] += 1
            type_stats[asset_type]['value'] += float(asset.current_value or 0)
        
        # Average asset value
        avg_value = total_value / total_assets if total_assets > 0 else 0
        
        return jsonify({
            'success': True,
            'total_assets': total_assets,
            'active_assets': active_assets,
            'maintenance_assets': maintenance_assets,
            'total_value': round(total_value, 2),
            'avg_value': round(avg_value, 2),
            'type_stats': type_stats
        })
        
    except Exception as e:
        logger.error(f"获取资产统计错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/assets/inventory')
def get_asset_inventory():
    """库存分布 - B. GET /crm/api/assets/inventory"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Query all assets for current user
        assets = Asset.query.filter_by(created_by_id=user_id).all()
        
        # Group by model (for miners)
        model_stats = {}
        for asset in assets:
            if asset.asset_type == 'miner' and asset.model:
                model = asset.model
                model_stats[model] = model_stats.get(model, 0) + 1
        
        # Group by status
        status_stats = {}
        for asset in assets:
            status = asset.status or 'unknown'
            status_stats[status] = status_stats.get(status, 0) + 1
        
        # Group by customer (TOP 5)
        customer_stats = {}
        for asset in assets:
            if asset.customer:
                customer_name = asset.customer.name
                customer_stats[customer_name] = customer_stats.get(customer_name, 0) + 1
        
        # Sort and get top 5 customers
        top_customers = sorted(customer_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return jsonify({
            'success': True,
            'model_stats': model_stats,
            'status_stats': status_stats,
            'top_customers': dict(top_customers)
        })
        
    except Exception as e:
        logger.error(f"获取库存分布错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/assets/maintenance-alerts')
def get_maintenance_alerts():
    """维护预警 - C. GET /crm/api/assets/maintenance-alerts"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Query assets that need maintenance
        maintenance_assets = Asset.query.filter_by(
            created_by_id=user_id,
            status='maintenance'
        ).all()
        
        # Build maintenance alerts list
        alerts = []
        for asset in maintenance_assets:
            # Determine priority based on asset value
            value = float(asset.current_value or 0)
            if value > 10000:
                priority = 'high'
                priority_color = 'danger'
            elif value > 5000:
                priority = 'medium'
                priority_color = 'warning'
            else:
                priority = 'low'
                priority_color = 'info'
            
            alerts.append({
                'id': asset.id,
                'asset_name': asset.asset_name,
                'customer_name': asset.customer.name if asset.customer else 'N/A',
                'serial_number': asset.serial_number or 'N/A',
                'priority': priority,
                'priority_color': priority_color,
                'value': value,
                'maintenance_due': asset.warranty_expiry.strftime('%Y-%m-%d') if asset.warranty_expiry else None
            })
        
        # Sort by priority (high first) and value
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda x: (priority_order.get(x['priority'], 3), -x['value']))
        
        # Return top 5
        return jsonify({
            'success': True,
            'alerts': alerts[:5],
            'total': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"获取维护预警错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@crm_bp.route('/api/assets/value-trend')
def get_asset_value_trend():
    """资产价值趋势 - D. GET /crm/api/assets/value-trend"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        
        # Query all assets for current user
        assets = Asset.query.filter_by(created_by_id=user_id).all()
        
        # Group by type and calculate total value
        type_values = {}
        for asset in assets:
            asset_type = asset.asset_type or 'unknown'
            type_values[asset_type] = type_values.get(asset_type, 0) + float(asset.current_value or 0)
        
        # Generate past 6 months labels (simplified - using current values)
        from dateutil.relativedelta import relativedelta
        end_date = datetime.now()
        months = []
        
        for i in range(5, -1, -1):
            month = end_date - relativedelta(months=i)
            months.append(month.strftime('%b %Y'))
        
        # For each type, create trend data (using current value for all months as simplified implementation)
        trend_data = {}
        for asset_type, value in type_values.items():
            trend_data[asset_type] = [round(value, 2)] * 6  # Same value for all 6 months
        
        return jsonify({
            'success': True,
            'months': months,
            'type_values': type_values,
            'trend_data': trend_data
        })
        
    except Exception as e:
        logger.error(f"获取资产价值趋势错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# 新版 CRM API 端点 - 匹配模板要求
# New CRM API Endpoints - Template Compliant
# ============================================================================

# -------------------- KPI 端点 (4个) --------------------

@crm_bp.route('/api/kpi/customers')
def kpi_customers():
    """KPI: 客户统计"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user_id = session.get('user_id')
        tenant_filter = get_tenant_filter(Customer, user_id)
        
        if tenant_filter is not None:
            # 计算总客户数
            total_customers = Customer.query.filter(tenant_filter).count() or 0
            
            # 计算本月新增客户
            now = datetime.now()
            first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            this_month_customers = Customer.query.filter(tenant_filter, Customer.created_at >= first_day_of_month).count() or 0
        else:
            # 计算总客户数
            total_customers = Customer.query.count() or 0
            
            # 计算本月新增客户
            now = datetime.now()
            first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            this_month_customers = Customer.query.filter(Customer.created_at >= first_day_of_month).count() or 0
        
        # 计算增长率
        growth_rate = (this_month_customers / total_customers * 100) if total_customers > 0 else 0
        
        logger.info(f"KPI Customers: total={total_customers}, this_month={this_month_customers}")
        
        return jsonify({
            'success': True,
            'total': total_customers,
            'this_month': this_month_customers,
            'growth_rate': round(growth_rate, 1)
        })
        
    except Exception as e:
        logger.error(f"获取客户KPI错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/kpi/deals')
def kpi_deals():
    """KPI: 交易统计"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user_id = session.get('user_id')
        tenant_filter = get_tenant_filter(Deal, user_id)
        
        if tenant_filter is not None:
            # 计算总交易价值和数量
            total_value = Deal.query.filter(tenant_filter).with_entities(func.sum(Deal.value)).scalar() or 0
            total_count = Deal.query.filter(tenant_filter).count() or 0
            
            # 计算本月交易价值
            now = datetime.now()
            first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            this_month_value = Deal.query.filter(
                tenant_filter,
                Deal.created_at >= first_day_of_month
            ).with_entities(func.sum(Deal.value)).scalar() or 0
        else:
            # 计算总交易价值和数量
            total_value = Deal.query.with_entities(func.sum(Deal.value)).scalar() or 0
            total_count = Deal.query.count() or 0
            
            # 计算本月交易价值
            now = datetime.now()
            first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            this_month_value = Deal.query.filter(
                Deal.created_at >= first_day_of_month
            ).with_entities(func.sum(Deal.value)).scalar() or 0
        
        logger.info(f"KPI Deals: total_value={total_value}, count={total_count}")
        
        return jsonify({
            'success': True,
            'total_value': float(total_value),
            'count': total_count,
            'this_month_value': float(this_month_value)
        })
        
    except Exception as e:
        logger.error(f"获取交易KPI错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/kpi/capacity')
def kpi_capacity():
    """KPI: 容量统计"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user_id = session.get('user_id')
        customer_filter = get_tenant_filter(Customer, user_id)
        deal_filter = get_tenant_filter(Deal, user_id)
        
        if customer_filter is not None:
            # 计算总容量
            total_mw = Customer.query.filter(customer_filter).with_entities(func.sum(Customer.mining_capacity)).scalar() or 0
        else:
            total_mw = Customer.query.with_entities(func.sum(Customer.mining_capacity)).scalar() or 0
        
        if deal_filter is not None:
            # 计算已使用容量（从交易中）
            used_capacity = Deal.query.filter(
                deal_filter,
                Deal.mining_capacity.isnot(None)
            ).with_entities(func.sum(Deal.mining_capacity)).scalar() or 0
        else:
            # 计算已使用容量（从交易中）
            used_capacity = Deal.query.filter(
                Deal.mining_capacity.isnot(None)
            ).with_entities(func.sum(Deal.mining_capacity)).scalar() or 0
        
        # 计算利用率和可用容量
        utilization_rate = (used_capacity / total_mw * 100) if total_mw > 0 else 0
        available_mw = total_mw - used_capacity
        
        logger.info(f"KPI Capacity: total_mw={total_mw}, utilization={utilization_rate}%")
        
        return jsonify({
            'success': True,
            'total_mw': float(total_mw),
            'utilization_rate': round(float(utilization_rate), 1),
            'available_mw': float(available_mw)
        })
        
    except Exception as e:
        logger.error(f"获取容量KPI错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/kpi/active-deals')
def kpi_active_deals():
    """KPI: 活跃交易统计"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user_id = session.get('user_id')
        
        # 计算活跃交易数量 - with tenant filter
        active_deals_query = Deal.query.filter(
            Deal.status.in_([DealStatus.PENDING, DealStatus.APPROVED, DealStatus.SIGNED])
        )
        active_deals = apply_tenant_filter(active_deals_query, Deal, user_id).all()
        
        active_count = len(active_deals)
        pending_value = sum([deal.value for deal in active_deals if deal.value]) or 0
        
        # 计算转化率 - with tenant filter
        lead_filter = get_tenant_filter(Lead, user_id)
        if lead_filter is not None:
            total_leads = Lead.query.filter(lead_filter).count() or 0
            won_leads = Lead.query.filter(lead_filter, Lead.status == LeadStatus.WON).count() or 0
        else:
            total_leads = Lead.query.count() or 0
            won_leads = Lead.query.filter(Lead.status == LeadStatus.WON).count() or 0
        conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
        
        logger.info(f"KPI Active Deals: count={active_count}, conversion_rate={conversion_rate}%")
        
        return jsonify({
            'success': True,
            'count': active_count,
            'conversion_rate': round(conversion_rate, 1),
            'pending_value': float(pending_value)
        })
        
    except Exception as e:
        logger.error(f"获取活跃交易KPI错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# -------------------- Analytics 端点 (4个) --------------------

@crm_bp.route('/api/analytics/revenue-trend')
def analytics_revenue_trend():
    """分析: 收入趋势 - 最近12个月"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        now = datetime.now()
        twelve_months_ago = now - timedelta(days=365)
        
        # 按月统计收入
        revenue_by_month = db.session.query(
            func.date_trunc('month', Deal.created_at).label('month'),
            func.sum(Deal.value).label('total')
        ).filter(
            Deal.created_at >= twelve_months_ago
        ).group_by('month').order_by('month').all()
        
        labels = []
        miner_sales_data = []
        hosting_data = []
        
        for month_data in revenue_by_month:
            if month_data.month:
                labels.append(month_data.month.strftime('%Y-%m'))
                total_revenue = float(month_data.total or 0)
                # 假设60%是矿机销售，40%是托管费用
                miner_sales_data.append(round(total_revenue * 0.6, 2))
                hosting_data.append(round(total_revenue * 0.4, 2))
        
        # 如果没有数据，返回空列表
        if not labels:
            labels = [(now - timedelta(days=30*i)).strftime('%Y-%m') for i in range(11, -1, -1)]
            miner_sales_data = [0] * 12
            hosting_data = [0] * 12
        
        logger.info(f"Analytics Revenue Trend: {len(labels)} months")
        
        return jsonify({
            'success': True,
            'labels': labels,
            'datasets': [
                {
                    'label': 'Miner Sales',
                    'data': miner_sales_data
                },
                {
                    'label': 'Hosting',
                    'data': hosting_data
                }
            ]
        })
        
    except Exception as e:
        logger.error(f"获取收入趋势分析错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/analytics/sales-funnel')
def analytics_sales_funnel():
    """分析: 销售漏斗"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 统计各状态的线索数量 - with tenant filter
        user_id = session.get('user_id')
        lead_filter = get_tenant_filter(Lead, user_id)
        
        if lead_filter is not None:
            funnel_data = {
                LeadStatus.NEW.value: Lead.query.filter(lead_filter).filter_by(status=LeadStatus.NEW).count() or 0,
                LeadStatus.CONTACTED.value: Lead.query.filter(lead_filter).filter_by(status=LeadStatus.CONTACTED).count() or 0,
                LeadStatus.QUALIFIED.value: Lead.query.filter(lead_filter).filter_by(status=LeadStatus.QUALIFIED).count() or 0,
                LeadStatus.NEGOTIATION.value: Lead.query.filter(lead_filter).filter_by(status=LeadStatus.NEGOTIATION).count() or 0,
                LeadStatus.WON.value: Lead.query.filter(lead_filter).filter_by(status=LeadStatus.WON).count() or 0
            }
        else:
            funnel_data = {
                LeadStatus.NEW.value: Lead.query.filter_by(status=LeadStatus.NEW).count() or 0,
                LeadStatus.CONTACTED.value: Lead.query.filter_by(status=LeadStatus.CONTACTED).count() or 0,
                LeadStatus.QUALIFIED.value: Lead.query.filter_by(status=LeadStatus.QUALIFIED).count() or 0,
                LeadStatus.NEGOTIATION.value: Lead.query.filter_by(status=LeadStatus.NEGOTIATION).count() or 0,
                LeadStatus.WON.value: Lead.query.filter_by(status=LeadStatus.WON).count() or 0
            }
        
        labels = list(funnel_data.keys())
        data = list(funnel_data.values())
        
        logger.info(f"Analytics Sales Funnel: total={sum(data)} leads")
        
        return jsonify({
            'success': True,
            'labels': labels,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"获取销售漏斗分析错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/analytics/capacity-distribution')
def analytics_capacity_distribution():
    """分析: 容量分布 - TOP 10客户"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 获取TOP 10容量客户 - with tenant filter
        user_id = session.get('user_id')
        top_customers_query = Customer.query.filter(
            Customer.mining_capacity.isnot(None),
            Customer.mining_capacity > 0
        ).order_by(Customer.mining_capacity.desc())
        top_customers = apply_tenant_filter(top_customers_query, Customer, user_id).limit(10).all()
        
        labels = []
        data = []
        colors = []
        
        # 生成图表颜色
        chart_colors = [
            '#f7931a', '#ffa500', '#ff8c00', '#ff7f00', '#ff6f00',
            '#ff5f00', '#ff4f00', '#ff3f00', '#ff2f00', '#ff1f00'
        ]
        
        for idx, customer in enumerate(top_customers):
            labels.append(customer.name or 'Unknown')
            data.append(float(customer.mining_capacity or 0))
            colors.append(chart_colors[idx] if idx < len(chart_colors) else '#cccccc')
        
        logger.info(f"Analytics Capacity Distribution: {len(labels)} customers")
        
        return jsonify({
            'success': True,
            'labels': labels,
            'data': data,
            'colors': colors
        })
        
    except Exception as e:
        logger.error(f"获取容量分布分析错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/analytics/customer-type')
def analytics_customer_type():
    """分析: 客户类型分布"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 按客户类型分组统计
        type_stats = db.session.query(
            Customer.customer_type,
            func.count(Customer.id).label('count')
        ).group_by(Customer.customer_type).all()
        
        labels = []
        data = []
        
        for type_data in type_stats:
            labels.append(type_data.customer_type or '未分类')
            data.append(int(type_data.count or 0))
        
        # 如果没有数据，返回空列表
        if not labels:
            labels = []
            data = []
        
        logger.info(f"Analytics Customer Type: {len(labels)} types")
        
        return jsonify({
            'success': True,
            'labels': labels,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"获取客户类型分析错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# -------------------- Rankings 端点 (2个) --------------------

@crm_bp.route('/api/rankings/miners')
def rankings_miners():
    """排行: 矿机型号销售排行"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 统计矿机型号销售情况
        miner_stats = db.session.query(
            Asset.model,
            func.count(Asset.id).label('sales'),
            func.sum(Asset.purchase_value).label('revenue')
        ).filter(
            Asset.asset_type == 'miner',
            Asset.model.isnot(None)
        ).group_by(Asset.model).order_by(func.count(Asset.id).desc()).limit(10).all()
        
        models = []
        for stat in miner_stats:
            models.append({
                'name': stat.model or 'Unknown',
                'sales': int(stat.sales or 0),
                'revenue': float(stat.revenue or 0)
            })
        
        logger.info(f"Rankings Miners: {len(models)} models")
        
        return jsonify({
            'success': True,
            'models': models
        })
        
    except Exception as e:
        logger.error(f"获取矿机排行错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/rankings/customer-capacity')
def rankings_customer_capacity():
    """排行: 客户容量TOP榜 - TOP 5"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 获取TOP 5容量客户 - with tenant filter
        user_id = session.get('user_id')
        top_customers_query = Customer.query.filter(
            Customer.mining_capacity.isnot(None),
            Customer.mining_capacity > 0
        ).order_by(Customer.mining_capacity.desc())
        top_customers = apply_tenant_filter(top_customers_query, Customer, user_id).limit(5).all()
        
        customers = []
        for customer in top_customers:
            # 计算客户的总收入
            total_revenue = sum([deal.value for deal in customer.deals if deal.value]) or 0
            
            customers.append({
                'name': customer.name or 'Unknown',
                'capacity': float(customer.mining_capacity or 0),
                'company': customer.company or '',
                'revenue': float(total_revenue)
            })
        
        logger.info(f"Rankings Customer Capacity: {len(customers)} customers")
        
        return jsonify({
            'success': True,
            'customers': customers
        })
        
    except Exception as e:
        logger.error(f"获取客户容量排行错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# -------------------- 智能提醒端点 (2个) --------------------

@crm_bp.route('/api/followups/today')
def followups_today():
    """智能提醒: 今日跟进"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 获取今日跟进的线索 - with tenant filter
        user_id = session.get('user_id')
        today = datetime.now().date()
        today_followups_query = Lead.query.filter(
            func.date(Lead.next_follow_up) == today
        )
        today_followups = apply_tenant_filter(today_followups_query, Lead, user_id).all()
        
        leads = []
        for lead in today_followups:
            customer_name = lead.customer.name if lead.customer else lead.name
            leads.append({
                'id': lead.id,
                'title': lead.title or f'{customer_name}的商机',
                'customer': customer_name,
                'scheduled': lead.next_follow_up.strftime('%Y-%m-%d %H:%M') if lead.next_follow_up else ''
            })
        
        logger.info(f"Follow-ups Today: {len(leads)} leads")
        
        return jsonify({
            'success': True,
            'leads': leads
        })
        
    except Exception as e:
        logger.error(f"获取今日跟进错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/alerts/urgent')
def alerts_urgent():
    """智能提醒: 紧急提醒"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        alerts = []
        now = datetime.now()
        seven_days_later = now + timedelta(days=7)
        user_id = session.get('user_id')
        
        # 检查即将到期的交易 - with tenant filter
        expiring_deals_query = Deal.query.filter(
            Deal.expected_close_date.isnot(None),
            Deal.expected_close_date <= seven_days_later,
            Deal.expected_close_date >= now,
            Deal.status.in_([DealStatus.PENDING, DealStatus.APPROVED])
        )
        expiring_deals = apply_tenant_filter(expiring_deals_query, Deal, user_id).all()
        
        for deal in expiring_deals:
            days_left = (deal.expected_close_date - now).days
            alerts.append({
                'type': 'deal',
                'id': deal.id,
                'message': f'交易即将在{days_left}天后到期',
                'priority': 'high' if days_left <= 3 else 'medium'
            })
        
        # 检查逾期发票
        overdue_invoices = Invoice.query.filter(
            Invoice.status == 'overdue'
        ).all()
        
        for invoice in overdue_invoices:
            alerts.append({
                'type': 'invoice',
                'id': invoice.id,
                'message': f'发票已逾期 - 金额: {invoice.amount}',
                'priority': 'high'
            })
        
        logger.info(f"Urgent Alerts: {len(alerts)} alerts")
        
        return jsonify({
            'success': True,
            'alerts': alerts
        })
        
    except Exception as e:
        logger.error(f"获取紧急提醒错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/<int:deal_id>/overview')
def deal_overview(deal_id):
    """交易概览KPI"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        deal = Deal.query.get_or_404(deal_id)
        
        # Verify tenant access
        if not verify_resource_access(deal):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        deal_value = float(deal.value) if deal.value else 0
        client_investment = float(deal.client_investment) if deal.client_investment else 0
        mining_capacity = float(deal.mining_capacity) if deal.mining_capacity else 0
        electricity_cost = float(deal.electricity_cost) if deal.electricity_cost else 0.05
        commission_rate = float(deal.commission_rate) if deal.commission_rate else 0
        
        btc_price = 60000
        monthly_btc = mining_capacity * 50
        monthly_revenue = monthly_btc * btc_price
        monthly_electricity = mining_capacity * 1000 * 24 * 30 * electricity_cost
        monthly_profit = monthly_revenue - monthly_electricity
        
        roi_percent = (monthly_profit / client_investment * 100) if client_investment > 0 else 0
        
        if deal.commission_type == 'percentage':
            expected_commission = (commission_rate * monthly_profit / 100) if monthly_profit > 0 else 0
        elif deal.commission_type == 'fixed':
            expected_commission = commission_rate
        else:
            expected_commission = 0
        
        contract_term_days = (deal.contract_term or 12) * 30 if deal.contract_term else 360
        if deal.created_at and deal.expected_close_date:
            total_days = (deal.expected_close_date - deal.created_at).days
            used_days = (datetime.now() - deal.created_at).days
            contract_progress = min(100, (used_days / total_days * 100)) if total_days > 0 else 0
        else:
            contract_progress = 0
        
        return jsonify({
            'success': True,
            'data': {
                'deal_value': deal_value,
                'client_investment': client_investment,
                'monthly_profit': monthly_profit,
                'roi_percent': roi_percent,
                'contract_progress': contract_progress,
                'expected_commission': expected_commission
            }
        })
        
    except Exception as e:
        logger.error(f"获取交易概览错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/<int:deal_id>/timeline')
def deal_timeline(deal_id):
    """交易时间线"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        deal = Deal.query.get_or_404(deal_id)
        
        # Verify tenant access
        if not verify_resource_access(deal):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        milestones = []
        
        if deal.created_at:
            milestones.append({
                'date': deal.created_at.strftime('%Y-%m-%d'),
                'title': '创建交易',
                'description': f'交易已创建，金额: ${deal.value:,.2f}' if deal.value else '交易已创建',
                'status': 'completed',
                'icon': 'plus-circle'
            })
        
        status_activities = Activity.query.filter_by(deal_id=deal_id).filter(
            Activity.type.in_(['状态变更', '创建'])
        ).order_by(Activity.created_at).all()
        
        for activity in status_activities:
            if activity.type == '状态变更':
                milestones.append({
                    'date': activity.created_at.strftime('%Y-%m-%d'),
                    'title': activity.summary or '状态变更',
                    'description': activity.details or '',
                    'status': 'completed',
                    'icon': 'arrow-right-circle'
                })
        
        if deal.expected_close_date:
            is_future = deal.expected_close_date > datetime.now()
            milestones.append({
                'date': deal.expected_close_date.strftime('%Y-%m-%d'),
                'title': '预计完成日期',
                'description': '预计交易完成时间',
                'status': 'pending' if is_future else 'completed',
                'icon': 'calendar-check'
            })
        
        if deal.closed_date:
            milestones.append({
                'date': deal.closed_date.strftime('%Y-%m-%d'),
                'title': '实际完成日期',
                'description': f'交易已{deal.status.value}',
                'status': 'completed',
                'icon': 'check-circle'
            })
        
        milestones.sort(key=lambda x: x['date'])
        
        return jsonify({
            'success': True,
            'milestones': milestones
        })
        
    except Exception as e:
        logger.error(f"获取交易时间线错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/<int:deal_id>/profitability')
def deal_profitability(deal_id):
    """收益预测"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        deal = Deal.query.get_or_404(deal_id)
        
        # Verify tenant access
        if not verify_resource_access(deal):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        mining_capacity = float(deal.mining_capacity) if deal.mining_capacity else 0
        electricity_cost = float(deal.electricity_cost) if deal.electricity_cost else 0.05
        
        btc_price = 60000
        monthly_btc = mining_capacity * 50
        monthly_revenue = monthly_btc * btc_price
        monthly_electricity = mining_capacity * 1000 * 24 * 30 * electricity_cost
        monthly_profit = monthly_revenue - monthly_electricity
        
        months = []
        revenues = []
        cumulative_profits = []
        cumulative = 0
        
        for i in range(1, 13):
            months.append(f'月{i}')
            revenues.append(monthly_revenue)
            cumulative += monthly_profit
            cumulative_profits.append(cumulative)
        
        client_investment = float(deal.client_investment) if deal.client_investment else 0
        roi_breakeven_months = int(client_investment / monthly_profit) if monthly_profit > 0 else 12
        
        return jsonify({
            'success': True,
            'data': {
                'months': months,
                'revenues': revenues,
                'cumulative_profits': cumulative_profits,
                'roi_breakeven_months': min(roi_breakeven_months, 12)
            }
        })
        
    except Exception as e:
        logger.error(f"获取收益预测错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/<int:deal_id>/power-analysis')
def deal_power_analysis(deal_id):
    """功耗分析"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        deal = Deal.query.get_or_404(deal_id)
        
        # Verify tenant access
        if not verify_resource_access(deal):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        mining_capacity = float(deal.mining_capacity) if deal.mining_capacity else 0
        electricity_cost = float(deal.electricity_cost) if deal.electricity_cost else 0.05
        
        total_power_kw = mining_capacity * 1000
        monthly_kwh = total_power_kw * 24 * 30
        monthly_electricity_cost = monthly_kwh * electricity_cost
        
        btc_price = 60000
        monthly_btc = mining_capacity * 50
        monthly_revenue = monthly_btc * btc_price
        
        electricity_ratio = (monthly_electricity_cost / monthly_revenue * 100) if monthly_revenue > 0 else 0
        
        market_avg_cost = 0.06
        comparison = ((electricity_cost - market_avg_cost) / market_avg_cost * 100) if market_avg_cost > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_power_kw': total_power_kw,
                'monthly_electricity_cost': monthly_electricity_cost,
                'electricity_ratio': electricity_ratio,
                'market_comparison': comparison
            }
        })
        
    except Exception as e:
        logger.error(f"获取功耗分析错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals/<int:deal_id>/sensitivity')
def deal_sensitivity(deal_id):
    """敏感性分析"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        deal = Deal.query.get_or_404(deal_id)
        
        # Verify tenant access
        if not verify_resource_access(deal):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        mining_capacity = float(deal.mining_capacity) if deal.mining_capacity else 0
        electricity_cost = float(deal.electricity_cost) if deal.electricity_cost else 0.05
        client_investment = float(deal.client_investment) if deal.client_investment else 0
        
        base_btc_price = 60000
        scenarios = [-20, -10, 0, 10, 20]
        
        price_scenarios = []
        monthly_profits = []
        roi_values = []
        
        for change in scenarios:
            btc_price = base_btc_price * (1 + change / 100)
            monthly_btc = mining_capacity * 50
            monthly_revenue = monthly_btc * btc_price
            monthly_electricity = mining_capacity * 1000 * 24 * 30 * electricity_cost
            monthly_profit = monthly_revenue - monthly_electricity
            roi = (monthly_profit / client_investment * 100) if client_investment > 0 else 0
            
            price_scenarios.append(f'${btc_price:,.0f}')
            monthly_profits.append(monthly_profit)
            roi_values.append(roi)
        
        return jsonify({
            'success': True,
            'data': {
                'price_scenarios': price_scenarios,
                'monthly_profits': monthly_profits,
                'roi_values': roi_values
            }
        })
        
    except Exception as e:
        logger.error(f"获取敏感性分析错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# CRM-Hosting Integration API
# ============================================

@crm_bp.route('/api/customer/<int:customer_id>/hosting-stats')
def get_customer_hosting_stats(customer_id):
    """获取客户的托管矿机统计数据"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        customer = Customer.query.get_or_404(customer_id)
        
        if not verify_resource_access(customer):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        from crm_services.hosting_integration import crm_hosting_service
        stats = crm_hosting_service.get_customer_hosting_stats(customer_id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取客户托管统计错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/customer/<int:customer_id>/hosting-miners')
def get_customer_hosting_miners(customer_id):
    """获取客户的托管矿机列表"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        customer = Customer.query.get_or_404(customer_id)
        
        if not verify_resource_access(customer):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        status = request.args.get('status')
        
        from crm_services.hosting_integration import crm_hosting_service
        miners = crm_hosting_service.get_customer_miners_list(customer_id, status)
        
        return jsonify({
            'success': True,
            'data': miners
        })
        
    except Exception as e:
        logger.error(f"获取客户矿机列表错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/customer/<int:customer_id>/sync-hosting', methods=['POST'])
def sync_customer_hosting(customer_id):
    """同步客户的托管数据到CRM"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        customer = Customer.query.get_or_404(customer_id)
        
        if not verify_resource_access(customer):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        from crm_services.hosting_integration import crm_hosting_service
        success = crm_hosting_service.sync_customer_from_hosting(customer_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '托管数据同步成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '未找到关联的托管账户或无矿机数据'
            }), 404
        
    except Exception as e:
        logger.error(f"同步客户托管数据错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/sync-all-hosting', methods=['POST'])
def sync_all_hosting():
    """批量同步所有客户的托管数据"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        from crm_services.hosting_integration import crm_hosting_service
        results = crm_hosting_service.sync_all_customers()
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f"已同步 {results['synced']} 个客户的托管数据"
        })
        
    except Exception as e:
        logger.error(f"批量同步托管数据错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/sync-status')
def get_sync_status():
    """获取CRM-Hosting同步状态"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        from crm_services.hosting_integration import crm_hosting_service
        status = crm_hosting_service.get_sync_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"获取同步状态错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def init_crm_routes(app):
    """初始化CRM路由到应用"""
    try:
        app.register_blueprint(crm_bp, url_prefix='/crm')
        logger.info("CRM routes registered successfully")
    except Exception as e:
        logger.error(f"Failed to register CRM routes: {e}")

def register_crm_routes(app):
    """注册CRM路由到应用（别名）"""
    return init_crm_routes(app)

# 兼容性导出
__all__ = ['crm_bp', 'init_crm_routes', 'register_crm_routes']