"""
CRM模块路由
独立的客户管理系统路由
"""
from flask import render_template, request, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import func, case
from . import crm_bp
from models import Customer, Deal, db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@crm_bp.route('/')
@login_required
def index():
    """CRM主页面"""
    return render_template('crm/dashboard.html')

@crm_bp.route('/api/customers')
@login_required
def get_customers():
    """获取客户列表API - 支持分页"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        per_page = min(per_page, 100)
        
        query = Customer.query
        if current_user.role != 'admin':
            query = query.filter_by(created_by_id=current_user.id)
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        customers_data = []
        for customer in paginated.items:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'company': customer.company,
                'status': customer.status,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            })
        
        return jsonify({
            'success': True,
            'customers': customers_data,
            'pagination': {
                'page': paginated.page,
                'per_page': paginated.per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"获取客户列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@crm_bp.route('/api/customer', methods=['POST'])
@login_required
def create_customer():
    """创建新客户"""
    try:
        data = request.get_json()
        
        customer = Customer(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            company=data.get('company'),
            created_by_id=current_user.id,
            status='lead'
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'customer_id': customer.id,
            'message': '客户创建成功'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建客户失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@crm_bp.route('/api/deals')
@login_required
def get_deals():
    """获取交易列表 - 支持分页，使用eager loading避免N+1"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        per_page = min(per_page, 100)
        
        query = Deal.query.options(joinedload(Deal.customer))
        if current_user.role != 'admin':
            query = query.filter_by(created_by_id=current_user.id)
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        deals_data = []
        for deal in paginated.items:
            deals_data.append({
                'id': deal.id,
                'title': deal.title,
                'customer_id': deal.customer_id,
                'customer_name': deal.customer.name if deal.customer else None,
                'amount': float(deal.amount) if deal.amount else 0,
                'stage': deal.stage,
                'probability': deal.probability,
                'expected_close': deal.expected_close.isoformat() if deal.expected_close else None
            })
        
        return jsonify({
            'success': True,
            'deals': deals_data,
            'pagination': {
                'page': paginated.page,
                'per_page': paginated.per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"获取交易列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@crm_bp.route('/api/stats')
@login_required
def get_stats():
    """获取CRM统计数据 - 优化为单次查询"""
    try:
        if current_user.role == 'admin':
            customer_count = db.session.query(
                func.count(Customer.id).label('total_customers')
            ).scalar() or 0
            
            deal_stats = db.session.query(
                func.sum(case((Deal.stage == 'negotiation', 1), else_=0)).label('active'),
                func.sum(case((Deal.stage == 'won', 1), else_=0)).label('won')
            ).first()
        else:
            customer_count = db.session.query(
                func.count(Customer.id).label('total_customers')
            ).filter(Customer.created_by_id == current_user.id).scalar() or 0
            
            deal_stats = db.session.query(
                func.sum(case((Deal.stage == 'negotiation', 1), else_=0)).label('active'),
                func.sum(case((Deal.stage == 'won', 1), else_=0)).label('won')
            ).filter(Deal.created_by_id == current_user.id).first()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_customers': customer_count,
                'active_deals': int(deal_stats.active or 0) if deal_stats else 0,
                'won_deals': int(deal_stats.won or 0) if deal_stats else 0
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
