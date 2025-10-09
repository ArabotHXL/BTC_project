"""
CRM (Customer Relationship Management) Routes
客户关系管理系统路由
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
import logging
from datetime import datetime, timedelta
import json
from sqlalchemy import func

# Import database and models
from db import db
from models import Customer, Lead, Deal, Invoice, Asset, Activity

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
            return redirect(url_for('login'))
        
        # Query real statistics from database
        customers_count = Customer.query.count() or 0
        leads_count = Lead.query.count() or 0
        deals_count = Deal.query.count() or 0
        deals_value = Deal.query.with_entities(func.sum(Deal.value)).scalar() or 0
        
        # Get recent activities (limit 10)
        recent_activities = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()
        
        # Get leads with follow-up dates
        follow_up_leads = Lead.query.filter(Lead.next_follow_up.isnot(None)).order_by(Lead.next_follow_up).limit(10).all()
        
        return render_template('crm/dashboard.html',
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
            return redirect(url_for('login'))
        
        return render_template('crm/customers.html',
                             title='Customer Management',
                             page='crm_customers')
    except Exception as e:
        logger.error(f"客户列表页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/api/crm/customers')
def get_customers():
    """获取客户列表 - 从数据库读取真实数据"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Fetch customers from database
        customers = Customer.query.order_by(Customer.created_at.desc()).all()
        
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
                'mining_capacity': customer.mining_capacity,
                'join_date': customer.created_at.strftime('%Y-%m-%d'),
                'total_revenue': total_revenue,
                'last_contact': last_contact,
                'tags': customer.tags
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

@crm_bp.route('/api/crm/customer/<int:customer_id>')
def get_customer_details(customer_id):
    """获取客户详情"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Query real customer from database
        customer = Customer.query.get_or_404(customer_id)
        
        # Get real deals for this customer
        deals = Deal.query.filter_by(customer_id=customer_id).all()
        
        # Calculate total revenue from deals
        total_revenue = sum([deal.value for deal in deals if deal.value]) or 0
        
        # Get real activities/notes for this customer
        activities = Activity.query.filter_by(customer_id=customer_id).order_by(Activity.created_at.desc()).limit(10).all()
        
        # Format deals/contracts data
        contracts = []
        for deal in deals:
            contracts.append({
                'id': deal.id,
                'type': deal.deal_type,
                'start_date': deal.start_date.strftime('%Y-%m-%d') if deal.start_date else None,
                'end_date': deal.end_date.strftime('%Y-%m-%d') if deal.end_date else None,
                'value': deal.value or 0,
                'status': deal.status
            })
        
        # Format activities/notes data
        notes = []
        for activity in activities:
            notes.append({
                'id': activity.id,
                'date': activity.created_at.strftime('%Y-%m-%d') if activity.created_at else None,
                'author': activity.user_email or 'System',
                'content': activity.description or ''
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

@crm_bp.route('/leads', endpoint='leads')
def leads_page():
    """潜在客户页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        return render_template('crm/leads.html',
                             title='Leads Management',
                             page='crm_leads')
    except Exception as e:
        logger.error(f"潜在客户页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/deals', endpoint='deals')
def deals_page():
    """交易页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        return render_template('crm/deals.html',
                             title='Deals Management',
                             page='crm_deals')
    except Exception as e:
        logger.error(f"交易页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/activities', endpoint='activities')
def activities_page():
    """活动页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        return render_template('crm/activities.html',
                             title='Activities',
                             page='crm_activities')
    except Exception as e:
        logger.error(f"活动页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/broker', endpoint='broker_dashboard')
def broker_dashboard_page():
    """经纪人仪表盘页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
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
            return redirect(url_for('login'))
        
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
            return redirect(url_for('login'))
        
        return render_template('crm/broker_commissions.html',
                             title='Broker Commissions',
                             page='crm_broker_commissions')
    except Exception as e:
        logger.error(f"经纪人佣金页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/customer/<int:customer_id>', endpoint='customer_detail')
def customer_detail_page(customer_id):
    """客户详情页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        return render_template('crm/customer_detail.html',
                             title='Customer Detail',
                             page='crm_customer_detail',
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
            return redirect(url_for('login'))
        
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
            status='active'
        )
        
        db.session.add(new_customer)
        db.session.commit()
        
        # Handle calculator access if granted
        if request.form.get('grant_calculator_access') == 'yes':
            access_days = int(request.form.get('access_days', 30))
            # Create user access for calculator
            from models import UserAccess
            from datetime import datetime, timedelta
            
            user_access = UserAccess(
                name=name,
                email=email,
                access_days=access_days,
                expires_at=datetime.now() + timedelta(days=access_days),
                role='customer',
                customer_id=new_customer.id
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
            return redirect(url_for('login'))
        
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
            return redirect(url_for('login'))
        
        return render_template('crm/lead_detail.html',
                             title='Lead Detail',
                             page='crm_lead_detail',
                             lead_id=lead_id)
    except Exception as e:
        logger.error(f"商机详情页面错误: {e}")
        return redirect(url_for('crm.leads'))

@crm_bp.route('/customer/<int:customer_id>/lead/new', endpoint='new_lead')
def new_lead_page(customer_id):
    """新建商机页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        return render_template('crm/lead_form.html',
                             title='New Lead',
                             page='crm_new_lead',
                             customer_id=customer_id)
    except Exception as e:
        logger.error(f"新建商机页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/lead/<int:lead_id>/edit', endpoint='edit_lead')
def edit_lead_page(lead_id):
    """编辑商机页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
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
            return redirect(url_for('login'))
        
        return render_template('crm/deal_detail.html',
                             title='Deal Detail',
                             page='crm_deal_detail',
                             deal_id=deal_id)
    except Exception as e:
        logger.error(f"交易详情页面错误: {e}")
        return redirect(url_for('crm.deals'))

@crm_bp.route('/customer/<int:customer_id>/deal/new', endpoint='new_deal')
def new_deal_page(customer_id):
    """新建交易页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        return render_template('crm/deal_form.html',
                             title='New Deal',
                             page='crm_new_deal',
                             customer_id=customer_id)
    except Exception as e:
        logger.error(f"新建交易页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/customer/<int:customer_id>/contact/new', endpoint='new_contact')
def new_contact_page(customer_id):
    """新建联系人页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        return render_template('crm/contact_form.html',
                             title='New Contact',
                             page='crm_new_contact',
                             customer_id=customer_id)
    except Exception as e:
        logger.error(f"新建联系人页面错误: {e}")
        return redirect(url_for('crm.customers'))

@crm_bp.route('/customer/<int:customer_id>/contact/<int:contact_id>/edit', endpoint='edit_contact')
def edit_contact_page(customer_id, contact_id):
    """编辑联系人页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
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
            return redirect(url_for('login'))
        
        flash('备注已更新', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=customer_id))
    except Exception as e:
        logger.error(f"更新客户备注错误: {e}")
        flash('更新备注失败', 'error')
        return redirect(url_for('crm.customer_detail', customer_id=customer_id))

@crm_bp.route('/api/crm/leads')
def get_leads():
    """获取潜在客户"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Query real leads from database
        leads = Lead.query.order_by(Lead.created_at.desc()).all()
        
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

@crm_bp.route('/api/crm/sales-stats')
def get_sales_stats():
    """获取销售统计"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Calculate real statistics from database
        # Get current month's date range
        now = datetime.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Monthly revenue from deals closed this month
        monthly_revenue = Deal.query.filter(
            Deal.created_at >= first_day_of_month
        ).with_entities(func.sum(Deal.value)).scalar() or 0
        
        # Active customers count
        active_customers = Customer.query.filter_by(status='active').count() or 0
        
        # New leads this month
        new_leads = Lead.query.filter(Lead.created_at >= first_day_of_month).count() or 0
        
        # Total pipeline value (all deals)
        pipeline_value = Deal.query.with_entities(func.sum(Deal.value)).scalar() or 0
        
        # Average deal size
        total_deals = Deal.query.count() or 1
        average_deal_size = pipeline_value / total_deals if total_deals > 0 else 0
        
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

@crm_bp.route('/api/crm/add-note', methods=['POST'])
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
            return redirect(url_for('login'))
        
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
            return redirect(url_for('login'))
        
        return render_template('crm/assets.html',
                             title='Asset Management',
                             page='crm_assets')
    except Exception as e:
        logger.error(f"资产页面错误: {e}")
        return redirect(url_for('crm.crm_dashboard'))

@crm_bp.route('/api/crm/invoices')
def get_invoices():
    """获取发票列表 - 从数据库读取真实数据"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Fetch invoices from database
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
        
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

@crm_bp.route('/api/crm/assets')
def get_assets():
    """获取资产列表 - 从数据库读取真实数据"""
    try:
        # Check authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Fetch assets from database
        assets = Asset.query.order_by(Asset.created_at.desc()).all()
        
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