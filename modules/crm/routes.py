"""
CRM模块路由
独立的客户管理系统路由
"""
from flask import render_template, request, jsonify, session
from flask_login import login_required, current_user
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
    """获取客户列表API"""
    try:
        # 根据用户权限筛选客户 - admin可以看所有，其他角色只看自己创建的
        if current_user.role == 'admin':
            customers = Customer.query.all()
        else:
            customers = Customer.query.filter_by(created_by_id=current_user.id).all()
        
        customers_data = []
        for customer in customers:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'company': customer.company,
                'status': customer.status,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            })
        
        return jsonify({'success': True, 'customers': customers_data})
        
    except Exception as e:
        logger.error(f"获取客户列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@crm_bp.route('/api/customer', methods=['POST'])
@login_required
def create_customer():
    """创建新客户"""
    try:
        data = request.get_json()
        
        # 创建客户记录
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
    """获取交易列表"""
    try:
        # 根据权限获取交易 - admin可以看所有，其他角色只看自己创建的
        if current_user.role == 'admin':
            deals = Deal.query.all()
        else:
            deals = Deal.query.filter_by(created_by_id=current_user.id).all()
        
        deals_data = []
        for deal in deals:
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
        
        return jsonify({'success': True, 'deals': deals_data})
        
    except Exception as e:
        logger.error(f"获取交易列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@crm_bp.route('/api/stats')
@login_required
def get_stats():
    """获取CRM统计数据"""
    try:
        # 从数据库获取统计数据 - admin可以看所有，其他角色只看自己创建的
        if current_user.role == 'admin':
            total_customers = Customer.query.count()
            active_deals = Deal.query.filter_by(stage='negotiation').count()
            won_deals = Deal.query.filter_by(stage='won').count()
        else:
            total_customers = Customer.query.filter_by(created_by_id=current_user.id).count()
            active_deals = Deal.query.filter_by(created_by_id=current_user.id, stage='negotiation').count()
            won_deals = Deal.query.filter_by(created_by_id=current_user.id, stage='won').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_customers': total_customers,
                'active_deals': active_deals,
                'won_deals': won_deals
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)})