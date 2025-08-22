"""
矿场中介业务管理路由
专门为矿场中介业务设计的CRM功能
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session
from sqlalchemy import func, extract
from models import db, Customer, Deal, CommissionRecord, Activity
from auth import login_required

# 创建蓝图
broker = Blueprint('broker', __name__, url_prefix='/broker')

def broker_access_required(view_function):
    """验证用户是否有矿场中介业务访问权限"""
    @login_required
    def wrapped_view(*args, **kwargs):
        if session.get('role') != 'owner':
            flash('只有所有者可以访问矿场中介业务管理', 'danger')
            return redirect(url_for('index'))
        return view_function(*args, **kwargs)
    wrapped_view.__name__ = view_function.__name__
    return wrapped_view

@broker.route('/')
@broker_access_required
def dashboard():
    """矿场中介业务仪表盘"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    # 获取用户的交易数据
    if is_admin:
        deals = Deal.query.filter(Deal.status.in_(['SIGNED', 'COMPLETED'])).all()
    else:
        deals = Deal.query.filter(
            Deal.created_by_id == user_id,
            Deal.status.in_(['SIGNED', 'COMPLETED'])
        ).all()
    
    # 统计数据
    total_deals = len(deals)
    active_deals = len([d for d in deals if d.status.name == 'SIGNED'])
    
    # 计算总佣金收入
    current_month = datetime.now().strftime('%Y-%m')
    monthly_commission = db.session.query(func.sum(CommissionRecord.commission_amount)).filter(
        CommissionRecord.record_month == current_month
    ).scalar() or 0
    
    total_commission = db.session.query(func.sum(CommissionRecord.commission_amount)).scalar() or 0
    
    # 未收佣金
    unpaid_commission = db.session.query(func.sum(CommissionRecord.commission_amount)).filter(
        CommissionRecord.paid == False
    ).scalar() or 0
    
    # 最近的佣金记录
    recent_commissions = CommissionRecord.query.order_by(
        CommissionRecord.record_date.desc()
    ).limit(10).all()
    
    return render_template(
        'broker/dashboard.html',
        total_deals=total_deals,
        active_deals=active_deals,
        monthly_commission=monthly_commission,
        total_commission=total_commission,
        unpaid_commission=unpaid_commission,
        recent_commissions=recent_commissions
    )

@broker.route('/deals')
@broker_access_required
def deals():
    """交易管理页面"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    if is_admin:
        deals_list = Deal.query.order_by(Deal.created_at.desc()).all()
    else:
        deals_list = Deal.query.filter(
            Deal.created_by_id == user_id
        ).order_by(Deal.created_at.desc()).all()
    
    return render_template('broker/deals.html', deals=deals_list)

@broker.route('/deals/<int:deal_id>')
@broker_access_required
def deal_detail(deal_id):
    """交易详情页面"""
    deal = Deal.query.get_or_404(deal_id)
    
    # 获取相关的佣金记录
    commission_records = CommissionRecord.query.filter_by(deal_id=deal_id).order_by(
        CommissionRecord.record_date.desc()
    ).all()
    
    return render_template(
        'broker/deal_detail.html',
        deal=deal,
        commission_records=commission_records
    )

@broker.route('/commissions')
@broker_access_required
def commissions():
    """佣金管理页面"""
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    status = request.args.get('status', '')
    
    query = CommissionRecord.query
    
    if month:
        query = query.filter(CommissionRecord.record_month == month)
    
    if status == 'paid':
        query = query.filter(CommissionRecord.paid == True)
    elif status == 'unpaid':
        query = query.filter(CommissionRecord.paid == False)
    
    commission_records = query.order_by(CommissionRecord.record_date.desc()).all()
    
    # 获取可用的月份列表
    available_months = db.session.query(CommissionRecord.record_month).distinct().all()
    available_months = [m[0] for m in available_months]
    
    return render_template(
        'broker/commissions.html',
        commission_records=commission_records,
        current_month=month,
        current_status=status,
        available_months=available_months
    )

@broker.route('/commissions/add', methods=['GET', 'POST'])
@broker_access_required
def add_commission():
    """添加佣金记录"""
    if request.method == 'POST':
        deal_id = request.form.get('deal_id')
        deal = Deal.query.get(deal_id)
        
        if not deal:
            flash('交易不存在', 'danger')
            return redirect(url_for('broker.commissions'))
        
        # 安全的数值转换函数
        def safe_float(value, default=0):
            """安全地将输入转换为float，防止NaN注入"""
            if not value:
                return default
            try:
                str_val = str(value).lower().strip()
                if 'nan' in str_val or 'inf' in str_val:
                    return default
                result = float(value)
                if result != result:  # NaN检查 (NaN != NaN 为True)
                    return default
                return result
            except (ValueError, TypeError):
                return default
        
        record_month = request.form.get('record_month')
        client_monthly_profit = safe_float(request.form.get('client_monthly_profit'))
        
        # 计算佣金
        if deal.commission_type == 'percentage':
            commission_amount = client_monthly_profit * (deal.commission_rate / 100)
        else:
            commission_amount = deal.commission_amount or 0
        
        # 创建佣金记录
        commission_record = CommissionRecord(
            deal_id=deal_id,
            customer_id=deal.customer_id,
            record_month=record_month,
            client_monthly_profit=client_monthly_profit,
            client_btc_mined=safe_float(request.form.get('client_btc_mined')),
            btc_price=safe_float(request.form.get('btc_price')),
            commission_type=deal.commission_type,
            commission_rate=deal.commission_rate,
            commission_amount=commission_amount,
            notes=request.form.get('notes'),
            created_by_id=session.get('user_id')
        )
        
        db.session.add(commission_record)
        db.session.commit()
        
        # 记录活动
        activity = Activity(
            customer_id=deal.customer_id,
            deal_id=deal_id,
            type="佣金",
            summary=f"添加了{record_month}的佣金记录",
            details=f"客户利润: ${client_monthly_profit:,.2f}, 佣金: ${commission_amount:,.2f}",
            created_by=session.get('email'),
            created_by_id=session.get('user_id')
        )
        db.session.add(activity)
        db.session.commit()
        
        flash(f'已成功添加{record_month}的佣金记录', 'success')
        return redirect(url_for('broker.commissions'))
    
    # GET请求 - 显示表单
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    if is_admin:
        deals = Deal.query.filter(Deal.status.in_(['SIGNED', 'COMPLETED'])).all()
    else:
        deals = Deal.query.filter(
            Deal.created_by_id == user_id,
            Deal.status.in_(['SIGNED', 'COMPLETED'])
        ).all()
    
    return render_template('broker/add_commission.html', deals=deals)

@broker.route('/commissions/<int:record_id>/edit', methods=['GET', 'POST'])
@broker_access_required
def edit_commission(record_id):
    """编辑佣金记录"""
    from models import CommissionEditHistory
    record = CommissionRecord.query.get_or_404(record_id)
    
    if request.method == 'POST':
        # 记录编辑历史的函数
        def record_change(field_name, old_value, new_value, reason=None):
            if str(old_value) != str(new_value):
                history = CommissionEditHistory(
                    commission_record_id=record_id,
                    edited_by_id=session.get('user_id'),
                    edited_by_name=session.get('user_email', '未知用户'),
                    field_name=field_name,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    change_reason=reason
                )
                db.session.add(history)
        
        # 获取修改原因
        change_reason = request.form.get('change_reason', '')
        
        # 安全的数值转换函数
        def safe_float(value, default=0):
            """安全地将输入转换为float，防止NaN注入"""
            if not value:
                return default
            try:
                str_val = str(value).lower().strip()
                if 'nan' in str_val or 'inf' in str_val:
                    return default
                result = float(value)
                if result != result:  # NaN检查 (NaN != NaN 为True)
                    return default
                return result
            except (ValueError, TypeError):
                return default
        
        # 记录所有字段变更
        old_profit = record.client_monthly_profit
        new_profit = safe_float(request.form.get('client_monthly_profit'))
        record_change('client_monthly_profit', old_profit, new_profit, change_reason)
        
        old_btc = record.client_btc_mined
        new_btc = safe_float(request.form.get('client_btc_mined')) if request.form.get('client_btc_mined') else 0
        record_change('client_btc_mined', old_btc, new_btc, change_reason)
        
        old_price = record.btc_price
        new_price = safe_float(request.form.get('btc_price')) if request.form.get('btc_price') else 0
        record_change('btc_price', old_price, new_price, change_reason)
        
        old_notes = record.notes
        new_notes = request.form.get('notes', '')
        record_change('notes', old_notes, new_notes, change_reason)
        
        # 更新记录
        record.client_monthly_profit = new_profit
        record.client_btc_mined = new_btc if new_btc > 0 else None
        record.btc_price = new_price if new_price > 0 else None
        record.notes = new_notes
        
        # 重新计算佣金
        deal = Deal.query.get(record.deal_id)
        if deal and deal.commission_type == 'percentage':
            old_commission = record.commission_amount
            new_commission = new_profit * (deal.commission_rate / 100)
            record_change('commission_amount', old_commission, new_commission, change_reason)
            record.commission_amount = new_commission
        
        db.session.commit()
        flash('佣金记录已更新，所有变更已记录', 'success')
        return redirect(url_for('broker.commissions'))
    
    return render_template('broker/edit_commission.html', record=record)

@broker.route('/commissions/<int:record_id>/mark-paid', methods=['POST'])
@broker_access_required
def mark_commission_paid(record_id):
    """标记佣金为已收款"""
    from models import CommissionEditHistory
    commission_record = CommissionRecord.query.get_or_404(record_id)
    
    # 记录支付状态变更
    history = CommissionEditHistory(
        commission_record_id=record_id,
        edited_by_id=session.get('user_id'),
        edited_by_name=session.get('user_email', '未知用户'),
        field_name='paid_status',
        old_value='未收款',
        new_value='已收款',
        change_reason='标记为已收款'
    )
    db.session.add(history)
    
    commission_record.paid = True
    commission_record.paid_date = datetime.utcnow()
    
    db.session.commit()
    
    flash('佣金状态已更新为已收款', 'success')
    return redirect(url_for('broker.commissions'))

@broker.route('/reports')
@broker_access_required
def reports():
    """业务报告页面"""
    # 月度佣金趋势
    monthly_data = db.session.query(
        CommissionRecord.record_month,
        func.sum(CommissionRecord.commission_amount).label('total_commission'),
        func.count(CommissionRecord.id).label('record_count')
    ).group_by(CommissionRecord.record_month).order_by(CommissionRecord.record_month.desc()).limit(12).all()
    
    # 按佣金类型统计
    commission_type_data = db.session.query(
        CommissionRecord.commission_type,
        func.sum(CommissionRecord.commission_amount).label('total_amount'),
        func.count(CommissionRecord.id).label('count')
    ).group_by(CommissionRecord.commission_type).all()
    
    return render_template(
        'broker/reports.html',
        monthly_data=monthly_data,
        commission_type_data=commission_type_data
    )

def init_broker_routes(app):
    """初始化矿场中介业务路由"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        app.register_blueprint(broker)
        logger.info("Broker routes registered successfully")
    except Exception as e:
        logger.error(f"Failed to register broker routes: {e}")

# 兼容性导出
__all__ = ['broker', 'init_broker_routes']