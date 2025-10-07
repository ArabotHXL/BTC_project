"""
CRM (Customer Relationship Management) Routes
客户关系管理系统路由
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
import logging
from datetime import datetime, timedelta
import json

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
        
        # 模拟统计数据
        customers_count = 15
        leads_count = 8
        deals_count = 12
        deals_value = 125000.00
        recent_activities = []
        follow_up_leads = []
        
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
        # 模拟客户详情数据
        customer_detail = {
            'success': True,
            'data': {
                'id': customer_id,
                'name': 'ABC Mining Corp',
                'email': 'contact@abcmining.com',
                'phone': '+1-555-0123',
                'address': '123 Mining Street, Bitcoin City, BC 12345',
                'status': 'active',
                'tier': 'enterprise',
                'join_date': '2023-01-15',
                'total_revenue': 25000.00,
                'mining_capacity': '50 PH/s',
                'electricity_cost': 0.05,
                'contracts': [
                    {
                        'id': 1,
                        'type': 'hosting',
                        'start_date': '2023-01-15',
                        'end_date': '2024-01-15',
                        'value': 15000.00,
                        'status': 'active'
                    },
                    {
                        'id': 2,
                        'type': 'maintenance',
                        'start_date': '2023-06-01',
                        'end_date': '2024-06-01',
                        'value': 10000.00,
                        'status': 'active'
                    }
                ],
                'notes': [
                    {
                        'id': 1,
                        'date': '2024-08-20',
                        'author': 'Sales Rep',
                        'content': '客户对新的S21矿机感兴趣，已发送报价'
                    },
                    {
                        'id': 2,
                        'date': '2024-08-15',
                        'author': 'Support',
                        'content': '解决了电力供应问题，客户满意'
                    }
                ]
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

@crm_bp.route('/customer/new', endpoint='new_customer')
def new_customer_page():
    """新建客户页面"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        return render_template('crm/customer_form.html',
                             title='New Customer',
                             page='crm_new_customer')
    except Exception as e:
        logger.error(f"新建客户页面错误: {e}")
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
        leads_data = {
            'success': True,
            'data': [
                {
                    'id': 1,
                    'name': 'New Mining Venture',
                    'email': 'contact@newmining.com',
                    'phone': '+1-555-9999',
                    'source': 'website',
                    'status': 'qualified',
                    'interest_level': 'high',
                    'estimated_value': 50000.00,
                    'created_date': '2024-08-20',
                    'last_contact': '2024-08-21',
                    'next_followup': '2024-08-25'
                },
                {
                    'id': 2,
                    'name': 'Bitcoin Farm LLC',
                    'email': 'info@bitcoinfarm.com',
                    'phone': '+1-555-8888',
                    'source': 'referral',
                    'status': 'contacted',
                    'interest_level': 'medium',
                    'estimated_value': 25000.00,
                    'created_date': '2024-08-18',
                    'last_contact': '2024-08-19',
                    'next_followup': '2024-08-24'
                }
            ],
            'total': 2
        }
        
        return jsonify(leads_data)
        
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
        stats_data = {
            'success': True,
            'data': {
                'monthly_revenue': 45000.00,
                'monthly_target': 50000.00,
                'active_customers': 15,
                'new_leads': 8,
                'conversion_rate': 0.65,
                'average_deal_size': 18500.00,
                'pipeline_value': 125000.00,
                'top_performers': [
                    {'name': 'John Smith', 'revenue': 15000.00},
                    {'name': 'Sarah Johnson', 'revenue': 12500.00},
                    {'name': 'Mike Wilson', 'revenue': 10000.00}
                ]
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