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
from models import Customer, Lead, Deal, Invoice, Asset, Activity, DealStatus, LeadStatus

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

@crm_bp.route('/crm/')
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
        
        # Query customer from database
        customer = Customer.query.get_or_404(customer_id)
        
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
            mining_capacity=mining_capacity
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

# ============================================================================
# 新版 CRM API 端点 - 匹配模板要求
# New CRM API Endpoints - Template Compliant
# ============================================================================

# -------------------- KPI 端点 (4个) --------------------

@crm_bp.route('/api/crm/kpi/customers')
def kpi_customers():
    """KPI: 客户统计"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
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

@crm_bp.route('/api/crm/kpi/deals')
def kpi_deals():
    """KPI: 交易统计"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
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

@crm_bp.route('/api/crm/kpi/capacity')
def kpi_capacity():
    """KPI: 容量统计"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 计算总容量
        total_mw = Customer.query.with_entities(func.sum(Customer.mining_capacity)).scalar() or 0
        
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

@crm_bp.route('/api/crm/kpi/active-deals')
def kpi_active_deals():
    """KPI: 活跃交易统计"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 计算活跃交易数量
        active_deals = Deal.query.filter(
            Deal.status.in_([DealStatus.PENDING, DealStatus.APPROVED, DealStatus.SIGNED])
        ).all()
        
        active_count = len(active_deals)
        pending_value = sum([deal.value for deal in active_deals if deal.value]) or 0
        
        # 计算转化率
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

@crm_bp.route('/api/crm/analytics/revenue-trend')
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

@crm_bp.route('/api/crm/analytics/sales-funnel')
def analytics_sales_funnel():
    """分析: 销售漏斗"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 统计各状态的线索数量
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

@crm_bp.route('/api/crm/analytics/capacity-distribution')
def analytics_capacity_distribution():
    """分析: 容量分布 - TOP 10客户"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 获取TOP 10容量客户
        top_customers = Customer.query.filter(
            Customer.mining_capacity.isnot(None),
            Customer.mining_capacity > 0
        ).order_by(Customer.mining_capacity.desc()).limit(10).all()
        
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

@crm_bp.route('/api/crm/analytics/customer-type')
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

@crm_bp.route('/api/crm/rankings/miners')
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

@crm_bp.route('/api/crm/rankings/customer-capacity')
def rankings_customer_capacity():
    """排行: 客户容量TOP榜 - TOP 5"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 获取TOP 5容量客户
        top_customers = Customer.query.filter(
            Customer.mining_capacity.isnot(None),
            Customer.mining_capacity > 0
        ).order_by(Customer.mining_capacity.desc()).limit(5).all()
        
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

@crm_bp.route('/api/crm/followups/today')
def followups_today():
    """智能提醒: 今日跟进"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 获取今日跟进的线索
        today = datetime.now().date()
        today_followups = Lead.query.filter(
            func.date(Lead.next_follow_up) == today
        ).all()
        
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

@crm_bp.route('/api/crm/alerts/urgent')
def alerts_urgent():
    """智能提醒: 紧急提醒"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        alerts = []
        now = datetime.now()
        seven_days_later = now + timedelta(days=7)
        
        # 检查即将到期的交易
        expiring_deals = Deal.query.filter(
            Deal.expected_close_date.isnot(None),
            Deal.expected_close_date <= seven_days_later,
            Deal.expected_close_date >= now,
            Deal.status.in_([DealStatus.PENDING, DealStatus.APPROVED])
        ).all()
        
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

def init_crm_routes(app):
    """初始化CRM路由到应用"""
    try:
        app.register_blueprint(crm_bp)
        logger.info("CRM routes registered successfully")
    except Exception as e:
        logger.error(f"Failed to register CRM routes: {e}")

def register_crm_routes(app):
    """注册CRM路由到应用（别名）"""
    return init_crm_routes(app)

# 兼容性导出
__all__ = ['crm_bp', 'init_crm_routes', 'register_crm_routes']