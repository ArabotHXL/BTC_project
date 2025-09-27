"""
CRM Routes
客户关系管理系统路由 - 提供完整的CRM功能
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime, timedelta
import logging
# Import from the current module structure
import sys
import os

# Add user_management_module to path for absolute imports
module_dir = os.path.dirname(os.path.dirname(__file__))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

try:
    from auth.decorators import requires_crm_access
    from auth.authentication import login_required
    from models import Customer, Contact, Lead, Deal, Activity, UserAccess
    from database import db
    from services.crm_service import CRMService
except ImportError as e:
    # Fallback for when running as part of the main application
    try:
        from user_management_module.auth.decorators import requires_crm_access
        from user_management_module.auth.authentication import login_required
        from user_management_module.models import Customer, Contact, Lead, Deal, Activity, UserAccess
        from user_management_module.database import db
        from user_management_module.services.crm_service import CRMService
    except ImportError:
        # Emergency fallback functions
        def requires_crm_access(f):
            return f
        def login_required(f):
            return f
        class Customer:
            @staticmethod
            def query():
                return MockQuery()
        class Contact:
            pass
        class Lead:
            pass
        class Deal:
            pass
        class Activity:
            pass
        class UserAccess:
            pass
        class MockQuery:
            def order_by(self, *args):
                return self
            def paginate(self, **kwargs):
                return MockPagination()
        class MockPagination:
            items = []
            total = 0
            pages = 0
        db = None
        class CRMService:
            @staticmethod
            def get_dashboard_stats():
                return {}

logger = logging.getLogger(__name__)

# 创建蓝图
crm_bp = Blueprint('crm', __name__)

@crm_bp.route('/dashboard')
@login_required
@requires_crm_access
def dashboard():
    """CRM主仪表盘"""
    try:
        # 获取统计数据
        stats = CRMService.get_dashboard_stats()
        
        return render_template('crm/dashboard.html',
                             title='CRM Dashboard',
                             stats=stats)
    except Exception as e:
        logger.error(f"CRM仪表盘错误: {e}")
        flash('无法加载CRM页面', 'error')
        return redirect(url_for('index'))

@crm_bp.route('/customers')
@login_required
@requires_crm_access
def customers():
    """客户列表页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        customers = Customer.query.order_by(Customer.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('crm/customers.html',
                             title='客户管理',
                             customers=customers)
    except Exception as e:
        logger.error(f"客户列表页面错误: {e}")
        flash('加载客户列表失败', 'error')
        return redirect(url_for('crm.dashboard'))

@crm_bp.route('/customers/<int:customer_id>')
@login_required
@requires_crm_access
def customer_detail(customer_id):
    """客户详情页面"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        # 获取客户相关的联系人、线索、交易和活动
        contacts = Contact.query.filter_by(customer_id=customer_id).all()
        leads = Lead.query.filter_by(customer_id=customer_id).all()
        deals = Deal.query.filter_by(customer_id=customer_id).all()
        activities = Activity.query.filter_by(customer_id=customer_id).order_by(
            Activity.created_at.desc()
        ).limit(20).all()
        
        return render_template('crm/customer_detail.html',
                             title=f'客户详情 - {customer.name}',
                             customer=customer,
                             contacts=contacts,
                             leads=leads,
                             deals=deals,
                             activities=activities)
    except Exception as e:
        logger.error(f"客户详情页面错误: {e}")
        flash('加载客户详情失败', 'error')
        return redirect(url_for('crm.customers'))

@crm_bp.route('/customers/create', methods=['GET', 'POST'])
@login_required
@requires_crm_access
def create_customer():
    """创建客户"""
    if request.method == 'GET':
        return render_template('crm/create_customer.html',
                             title='创建客户')
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        customer = CRMService.create_customer(
            name=data['name'],
            company=data.get('company'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            customer_type=data.get('customer_type', '企业'),
            tags=data.get('tags'),
            notes=data.get('notes'),
            created_by_id=session.get('user_id')
        )
        
        if customer:
            message = f'客户 {customer.name} 创建成功'
            logger.info(message)
            
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'customer': customer.to_dict()})
            else:
                flash(message, 'success')
                return redirect(url_for('crm.customer_detail', customer_id=customer.id))
        else:
            error = '创建客户失败'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 500
            else:
                flash(error, 'error')
                return redirect(url_for('crm.create_customer'))
                
    except Exception as e:
        logger.error(f"创建客户错误: {e}")
        error = f'创建客户失败: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('crm.create_customer'))

@crm_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_crm_access
def edit_customer(customer_id):
    """编辑客户"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        if request.method == 'GET':
            return render_template('crm/edit_customer.html',
                                 title=f'编辑客户 - {customer.name}',
                                 customer=customer)
        
        data = request.get_json() if request.is_json else request.form
        
        # 更新客户信息
        customer.name = data.get('name', customer.name)
        customer.company = data.get('company', customer.company)
        customer.email = data.get('email', customer.email)
        customer.phone = data.get('phone', customer.phone)
        customer.address = data.get('address', customer.address)
        customer.customer_type = data.get('customer_type', customer.customer_type)
        customer.tags = data.get('tags', customer.tags)
        customer.notes = data.get('notes', customer.notes)
        customer.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        message = f'客户 {customer.name} 更新成功'
        logger.info(message)
        
        if request.is_json:
            return jsonify({'success': True, 'message': message, 'customer': customer.to_dict()})
        else:
            flash(message, 'success')
            return redirect(url_for('crm.customer_detail', customer_id=customer.id))
            
    except Exception as e:
        logger.error(f"编辑客户错误: {e}")
        db.session.rollback()
        error = f'编辑客户失败: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('crm.customer_detail', customer_id=customer_id))

@crm_bp.route('/leads')
@login_required
@requires_crm_access
def leads():
    """线索管理页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        leads = Lead.query.order_by(Lead.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('crm/leads.html',
                             title='线索管理',
                             leads=leads)
    except Exception as e:
        logger.error(f"线索管理页面错误: {e}")
        flash('加载线索列表失败', 'error')
        return redirect(url_for('crm.dashboard'))

@crm_bp.route('/leads/create', methods=['GET', 'POST'])
@login_required
@requires_crm_access
def create_lead():
    """创建线索"""
    if request.method == 'GET':
        customers = Customer.query.all()
        return render_template('crm/create_lead.html',
                             title='创建线索',
                             customers=customers)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        lead = CRMService.create_lead(
            title=data['title'],
            description=data.get('description'),
            customer_id=data.get('customer_id'),
            source=data.get('source'),
            estimated_value=data.get('estimated_value'),
            assigned_to_id=data.get('assigned_to_id'),
            created_by_id=session.get('user_id')
        )
        
        if lead:
            message = f'线索 {lead.title} 创建成功'
            logger.info(message)
            
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'lead': lead.to_dict()})
            else:
                flash(message, 'success')
                return redirect(url_for('crm.leads'))
        else:
            error = '创建线索失败'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 500
            else:
                flash(error, 'error')
                return redirect(url_for('crm.create_lead'))
                
    except Exception as e:
        logger.error(f"创建线索错误: {e}")
        error = f'创建线索失败: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('crm.create_lead'))

@crm_bp.route('/deals')
@login_required
@requires_crm_access
def deals():
    """交易管理页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        deals = Deal.query.order_by(Deal.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('crm/deals.html',
                             title='交易管理',
                             deals=deals)
    except Exception as e:
        logger.error(f"交易管理页面错误: {e}")
        flash('加载交易列表失败', 'error')
        return redirect(url_for('crm.dashboard'))

@crm_bp.route('/deals/create', methods=['GET', 'POST'])
@login_required
@requires_crm_access
def create_deal():
    """创建交易"""
    if request.method == 'GET':
        customers = Customer.query.all()
        return render_template('crm/create_deal.html',
                             title='创建交易',
                             customers=customers)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        deal = CRMService.create_deal(
            customer_id=data['customer_id'],
            title=data['title'],
            amount=float(data['amount']),
            description=data.get('description'),
            currency=data.get('currency', 'USD'),
            assigned_to_id=data.get('assigned_to_id'),
            created_by_id=session.get('user_id')
        )
        
        if deal:
            message = f'交易 {deal.title} 创建成功'
            logger.info(message)
            
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'deal': deal.to_dict()})
            else:
                flash(message, 'success')
                return redirect(url_for('crm.deals'))
        else:
            error = '创建交易失败'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 500
            else:
                flash(error, 'error')
                return redirect(url_for('crm.create_deal'))
                
    except Exception as e:
        logger.error(f"创建交易错误: {e}")
        error = f'创建交易失败: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('crm.create_deal'))

@crm_bp.route('/activities')
@login_required
@requires_crm_access
def activities():
    """活动记录页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        activities = Activity.query.order_by(Activity.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('crm/activities.html',
                             title='活动记录',
                             activities=activities)
    except Exception as e:
        logger.error(f"活动记录页面错误: {e}")
        flash('加载活动记录失败', 'error')
        return redirect(url_for('crm.dashboard'))

@crm_bp.route('/add-activity', methods=['POST'])
@login_required
@requires_crm_access
def add_activity():
    """添加活动记录"""
    try:
        data = request.get_json()
        
        activity = CRMService.create_activity(
            customer_id=data['customer_id'],
            activity_type=data['activity_type'],
            title=data['title'],
            description=data.get('description'),
            lead_id=data.get('lead_id'),
            deal_id=data.get('deal_id'),
            performed_by_id=session.get('user_id')
        )
        
        if activity:
            message = '活动记录添加成功'
            logger.info(message)
            
            return jsonify({
                'success': True,
                'message': message,
                'activity': activity.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': '添加活动记录失败'}), 500
                
    except Exception as e:
        logger.error(f"添加活动记录错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API接口
@crm_bp.route('/api/customers')
@login_required
@requires_crm_access
def api_customers():
    """获取客户列表API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        
        query = Customer.query
        
        if search:
            query = query.filter(
                (Customer.name.contains(search)) |
                (Customer.company.contains(search)) |
                (Customer.email.contains(search))
            )
        
        customers = query.order_by(Customer.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [customer.to_dict() for customer in customers.items],
            'pagination': {
                'page': customers.page,
                'pages': customers.pages,
                'per_page': customers.per_page,
                'total': customers.total
            }
        })
        
    except Exception as e:
        logger.error(f"获取客户列表API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/leads')
@login_required
@requires_crm_access
def api_leads():
    """获取线索列表API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        leads = Lead.query.order_by(Lead.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [lead.to_dict() for lead in leads.items],
            'pagination': {
                'page': leads.page,
                'pages': leads.pages,
                'per_page': leads.per_page,
                'total': leads.total
            }
        })
        
    except Exception as e:
        logger.error(f"获取线索列表API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/deals')
@login_required
@requires_crm_access
def api_deals():
    """获取交易列表API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        deals = Deal.query.order_by(Deal.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [deal.to_dict() for deal in deals.items],
            'pagination': {
                'page': deals.page,
                'pages': deals.pages,
                'per_page': deals.per_page,
                'total': deals.total
            }
        })
        
    except Exception as e:
        logger.error(f"获取交易列表API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/stats')
@login_required
@requires_crm_access
def api_stats():
    """获取CRM统计API"""
    try:
        stats = CRMService.get_dashboard_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取CRM统计API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500