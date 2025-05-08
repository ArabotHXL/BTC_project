"""
客户关系管理 (CRM) 系统路由
此模块包含CRM系统的所有路由和功能
"""
import json
from datetime import datetime

# Flask和SQLAlchemy导入
from flask import (
    Blueprint, render_template, redirect, url_for, 
    request, flash, jsonify, session
)
from sqlalchemy import or_

# 内部模块导入
from models import db, Customer, Contact, Lead, Deal, Activity, LeadStatus, DealStatus
from auth import login_required

# 创建蓝图
crm = Blueprint('crm', __name__, url_prefix='/crm')

# 权限验证装饰器
def crm_access_required(view_function):
    """验证用户是否有CRM访问权限"""
    @login_required
    def wrapped_view(*args, **kwargs):
        if session.get('role') not in ['owner', 'admin', 'manager', 'mining_site']:
            flash('您没有权限访问CRM系统', 'danger')
            return redirect(url_for('index'))
        return view_function(*args, **kwargs)
    wrapped_view.__name__ = view_function.__name__
    return wrapped_view

def get_user_customers(user_id=None, include_all=False):
    """
    获取用户可以访问的客户列表
    
    参数:
    - user_id: 用户ID，如果为None则使用当前登录用户
    - include_all: 是否包含所有客户(仅对owner和admin有效)
    
    返回:
    - 查询对象，包含用户可以访问的客户
    """
    # 如果没有提供user_id，则尝试从session获取
    if user_id is None:
        user_id = session.get('user_id', 0)  # 如果session中也没有，则使用0（不存在的ID）
    
    # 确保user_id不为None，避免SQL查询错误
    if user_id is None:
        user_id = 0  # 使用0作为默认值，通常数据库ID从1开始
    
    # 管理员和拥有者可以查看所有客户
    if include_all and session.get('role') in ['owner', 'admin']:
        return Customer.query
    
    # 所有其他用户(包括矿场主和经理)只能查看自己创建的客户
    return Customer.query.filter_by(created_by_id=user_id)

# CRM仪表盘
@crm.route('/')
@crm_access_required
def dashboard():
    """CRM系统仪表盘"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    # 初始化查询
    customer_query = get_user_customers(user_id, include_all=is_admin)
    
    # 统计数据
    customers_count = customer_query.count()
    
    # 获取用户可以访问的客户ID列表
    customer_ids = [c.id for c in customer_query.all()]
    
    # 如果用户没有客户，显示空仪表盘
    if not customer_ids:
        return render_template(
            'crm/dashboard.html',
            customers_count=0,
            leads_count=0,
            deals_count=0,
            deals_value=0,
            recent_activities=[],
            follow_up_leads=[],
            recent_deals=[]
        )
    
    # 基于用户可访问的客户进行相关数据查询
    leads_count = Lead.query.filter(Lead.customer_id.in_(customer_ids)).count()
    deals_count = Deal.query.filter(Deal.customer_id.in_(customer_ids)).count()
    deals_value = db.session.query(db.func.sum(Deal.value)).filter(
        Deal.customer_id.in_(customer_ids)
    ).scalar() or 0
    
    # 最近活动
    recent_activities = Activity.query.filter(
        Activity.customer_id.in_(customer_ids)
    ).order_by(Activity.created_at.desc()).limit(10).all()
    
    # 待跟进线索
    follow_up_leads = Lead.query.filter(
        Lead.customer_id.in_(customer_ids),
        Lead.status != LeadStatus.WON,
        Lead.status != LeadStatus.LOST,
        Lead.next_follow_up >= datetime.utcnow()
    ).order_by(Lead.next_follow_up).limit(5).all()
    
    # 近期交易
    recent_deals = Deal.query.filter(
        Deal.customer_id.in_(customer_ids),
        Deal.status != DealStatus.COMPLETED,
        Deal.status != DealStatus.CANCELED
    ).order_by(Deal.expected_close_date).limit(5).all()
    
    return render_template(
        'crm/dashboard.html',
        customers_count=customers_count,
        leads_count=leads_count,
        deals_count=deals_count,
        deals_value=deals_value,
        recent_activities=recent_activities,
        follow_up_leads=follow_up_leads,
        recent_deals=recent_deals
    )

# 客户管理
@crm.route('/customers')
@crm_access_required
def customers():
    """客户列表页面"""
    search = request.args.get('search', '')
    tag = request.args.get('tag', '')
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    # 获取用户可访问的客户
    query = get_user_customers(user_id, include_all=is_admin)
    
    if search:
        query = query.filter(or_(
            Customer.name.ilike(f'%{search}%'),
            Customer.company.ilike(f'%{search}%'),
            Customer.email.ilike(f'%{search}%')
        ))
    
    if tag:
        query = query.filter(Customer.tags.ilike(f'%{tag}%'))
        
    customers_list = query.order_by(Customer.name).all()
    
    # 获取所有标签 (仅从用户可访问的客户中)
    all_tags = set()
    for customer in customers_list:
        if customer.tags:
            customer_tags = [t.strip() for t in customer.tags.split(',')]
            all_tags.update(customer_tags)
    
    return render_template(
        'crm/customers.html',
        customers=customers_list,
        search=search,
        tag=tag,
        all_tags=sorted(all_tags),
        is_admin=is_admin
    )

@crm.route('/customers/<int:customer_id>')
@crm_access_required
def customer_detail(customer_id):
    """客户详情页面"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    customer = Customer.query.get_or_404(customer_id)
    
    # 验证用户是否有权限访问此客户
    if customer.created_by_id != user_id and not is_admin:
        flash('您没有权限查看此客户', 'danger')
        return redirect(url_for('crm.customers'))
        
    return render_template('crm/customer_detail.html', customer=customer)

@crm.route('/customers/new', methods=['GET', 'POST'])
@crm_access_required
def new_customer():
    """新建客户"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('客户名称不能为空', 'danger')
            return redirect(url_for('crm.new_customer'))
        
        customer = Customer(
            name=name,
            company=request.form.get('company'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            tags=request.form.get('tags'),
            customer_type=request.form.get('customer_type', '企业'),
            mining_capacity=float(request.form.get('mining_capacity', 0)) if request.form.get('mining_capacity') else None,
            created_by_id=user_id  # 记录创建者ID
        )
        
        db.session.add(customer)
        db.session.commit()
        
        # 记录客户创建活动
        activity = Activity(
            customer_id=customer.id,
            type="创建",
            summary=f"创建了新客户: {name}",
            details=f"客户类型: {request.form.get('customer_type', '企业')}",
            created_by=session.get('email'),
            created_by_id=user_id
        )
        db.session.add(activity)
        db.session.commit()
        
        flash(f'已成功创建客户: {name}', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=customer.id))
    
    return render_template('crm/customer_form.html', customer=None)

@crm.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@crm_access_required
def edit_customer(customer_id):
    """编辑客户"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    customer = Customer.query.get_or_404(customer_id)
    
    # 验证用户是否有权限编辑此客户
    if customer.created_by_id != user_id and not is_admin:
        flash('您没有权限编辑此客户', 'danger')
        return redirect(url_for('crm.customers'))
    
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.company = request.form.get('company')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')
        customer.tags = request.form.get('tags')
        customer.customer_type = request.form.get('customer_type', '企业')
        customer.mining_capacity = float(request.form.get('mining_capacity', 0)) if request.form.get('mining_capacity') else None
        
        db.session.commit()
        
        # 记录客户编辑活动
        activity = Activity(
            customer_id=customer_id,
            type="编辑",
            summary=f"更新了客户信息: {customer.name}",
            details="更新了客户基本信息",
            created_by=session.get('email'),
            created_by_id=user_id
        )
        db.session.add(activity)
        db.session.commit()
        
        flash(f'已成功更新客户: {customer.name}', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=customer.id))
    
    return render_template('crm/customer_form.html', customer=customer)

@crm.route('/customers/<int:customer_id>/delete', methods=['POST'])
@crm_access_required
def delete_customer(customer_id):
    """删除客户"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    customer = Customer.query.get_or_404(customer_id)
    
    # 验证用户是否有权限删除此客户
    if customer.created_by_id != user_id and not is_admin:
        flash('您没有权限删除此客户', 'danger')
        return redirect(url_for('crm.customers'))
    
    name = customer.name
    
    # 记录删除操作（但不与特定客户关联，因为客户将被删除）
    activity_info = f"删除了客户: {name} (ID: {customer_id})"
    
    db.session.delete(customer)
    db.session.commit()
    
    # 记录删除动作到日志（可选）
    print(f"用户 {session.get('email')} {activity_info}")
    
    flash(f'已成功删除客户: {name}', 'success')
    return redirect(url_for('crm.customers'))

# 联系人管理
@crm.route('/customers/<int:customer_id>/contacts/new', methods=['GET', 'POST'])
@crm_access_required
def new_contact(customer_id):
    """新建联系人"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    customer = Customer.query.get_or_404(customer_id)
    
    # 验证用户是否有权限为此客户添加联系人
    if customer.created_by_id != user_id and not is_admin:
        flash('您没有权限为此客户添加联系人', 'danger')
        return redirect(url_for('crm.customers'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('联系人姓名不能为空', 'danger')
            return redirect(url_for('crm.new_contact', customer_id=customer_id))
        
        is_primary = request.form.get('primary', '0') == '1'
        
        # 如果是主要联系人，先将其他联系人设为非主要
        if is_primary:
            for contact in customer.contacts:
                contact.primary = False
        
        contact = Contact(
            customer_id=customer_id,
            name=name,
            position=request.form.get('position'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            primary=is_primary,
            notes=request.form.get('notes')
        )
        
        db.session.add(contact)
        db.session.commit()
        
        # 记录活动
        activity = Activity(
            customer_id=customer_id,
            type="联系人",
            summary=f"添加了新联系人: {name}",
            details=f"添加了联系人信息，职位: {request.form.get('position') or '未填写'}",
            created_by=session.get('email'),
            created_by_id=user_id
        )
        db.session.add(activity)
        db.session.commit()
        
        flash(f'已成功添加联系人: {name}', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=customer_id))
    
    return render_template('crm/contact_form.html', customer=customer, contact=None)

# 商机管理
@crm.route('/leads')
@crm_access_required
def leads():
    """商机列表页面"""
    status = request.args.get('status', '')
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    # 获取用户可访问的客户ID列表
    customer_ids = [c.id for c in get_user_customers(user_id, include_all=is_admin).all()]
    
    # 如果没有可访问的客户，显示空列表
    if not customer_ids:
        return render_template(
            'crm/leads.html',
            leads=[],
            status=status,
            all_statuses=[s.name for s in LeadStatus]
        )
    
    # 基于可访问的客户进行查询
    query = Lead.query.filter(Lead.customer_id.in_(customer_ids))
    
    if status:
        try:
            status_enum = LeadStatus[status]
            query = query.filter(Lead.status == status_enum)
        except KeyError:
            pass
        
    leads_list = query.order_by(Lead.created_at.desc()).all()
    
    return render_template(
        'crm/leads.html',
        leads=leads_list,
        status=status,
        all_statuses=[s.name for s in LeadStatus]
    )

@crm.route('/leads/<int:lead_id>')
@crm_access_required
def lead_detail(lead_id):
    """商机详情页面"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    lead = Lead.query.get_or_404(lead_id)
    customer = Customer.query.get(lead.customer_id)
    
    # 验证用户是否有权限访问此商机
    if customer.created_by_id != user_id and not is_admin:
        flash('您没有权限查看此商机', 'danger')
        return redirect(url_for('crm.leads'))
        
    return render_template('crm/lead_detail.html', lead=lead)

@crm.route('/leads/<int:lead_id>/update-status', methods=['POST'])
@crm_access_required
def update_lead_status(lead_id):
    """更新商机状态"""
    lead = Lead.query.get_or_404(lead_id)
    
    if request.method == 'POST':
        old_status = lead.status
        status_name = request.form.get('status')
        status_comment = request.form.get('status_comment', '')
        
        try:
            new_status = LeadStatus[status_name]
            
            # 只有状态有变化时才更新
            if new_status != old_status:
                lead.status = new_status
                
                # 如果状态变为"已成交"，记录成交日期
                if new_status == LeadStatus.WON:
                    # 如果没有相关交易，可以创建一个
                    if not lead.deals:
                        flash('请为此商机创建相关交易', 'info')
                
                # 更新时间戳
                lead.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                # 记录状态变更活动
                status_change_desc = f"商机状态从 {old_status.value} 变更为 {new_status.value}"
                if status_comment:
                    status_change_desc += f"\n\n变更说明: {status_comment}"
                
                activity = Activity(
                    customer_id=lead.customer_id,
                    lead_id=lead.id,
                    type="状态变更",
                    summary=f"更新了商机状态: {new_status.value}",
                    details=status_change_desc,
                    created_by=session.get('email')
                )
                
                db.session.add(activity)
                db.session.commit()
                
                flash(f'商机状态已更新为: {new_status.value}', 'success')
            else:
                flash('状态未变更', 'info')
                
        except KeyError:
            flash('无效的状态值', 'danger')
        
    return redirect(url_for('crm.lead_detail', lead_id=lead_id))

@crm.route('/customers/<int:customer_id>/leads/new', methods=['GET', 'POST'])
@crm_access_required
def new_lead(customer_id):
    """新建商机"""
    user_id = session.get('user_id')
    customer = Customer.query.get_or_404(customer_id)
    
    # 验证用户是否有权限访问此客户
    if customer.created_by_id != user_id and session.get('role') not in ['owner', 'admin']:
        flash('您没有权限为此客户创建商机', 'danger')
        return redirect(url_for('crm.customers'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('商机标题不能为空', 'danger')
            return redirect(url_for('crm.new_lead', customer_id=customer_id))
        
        try:
            status = LeadStatus[request.form.get('status', 'NEW')]
        except KeyError:
            status = LeadStatus.NEW
        
        estimated_value = float(request.form.get('estimated_value', 0))
        
        next_follow_up = None
        if request.form.get('next_follow_up'):
            try:
                next_follow_up = datetime.strptime(request.form.get('next_follow_up'), '%Y-%m-%d')
            except ValueError:
                pass
        
        # 负责人默认为创建者
        assigned_to = request.form.get('assigned_to')
        
        lead = Lead(
            customer_id=customer_id,
            title=title,
            status=status,
            source=request.form.get('source'),
            estimated_value=estimated_value,
            assigned_to=assigned_to,
            assigned_to_id=user_id,  # 设置负责人ID
            description=request.form.get('description'),
            next_follow_up=next_follow_up,
            created_by_id=user_id  # 记录创建者ID
        )
        
        db.session.add(lead)
        db.session.commit()
        
        # 添加活动记录
        activity = Activity(
            customer_id=customer_id,
            lead_id=lead.id,
            type="创建",
            summary=f"创建了新商机: {title}",
            details=request.form.get('description'),
            created_by=session.get('email'),
            created_by_id=user_id
        )
        db.session.add(activity)
        db.session.commit()
        
        flash(f'已成功创建商机: {title}', 'success')
        return redirect(url_for('crm.lead_detail', lead_id=lead.id))
    
    return render_template('crm/lead_form.html', customer=customer, lead=None, all_statuses=LeadStatus)

# 交易管理
@crm.route('/deals')
@crm_access_required
def deals():
    """交易列表页面"""
    status = request.args.get('status', '')
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    # 获取用户可访问的客户ID列表
    customer_ids = [c.id for c in get_user_customers(user_id, include_all=is_admin).all()]
    
    # 如果没有可访问的客户，显示空列表
    if not customer_ids:
        return render_template(
            'crm/deals.html',
            deals=[],
            status=status,
            all_statuses=[s.name for s in DealStatus]
        )
    
    # 基于可访问的客户进行查询
    query = Deal.query.filter(Deal.customer_id.in_(customer_ids))
    
    if status:
        try:
            status_enum = DealStatus[status]
            query = query.filter(Deal.status == status_enum)
        except KeyError:
            pass
        
    deals_list = query.order_by(Deal.expected_close_date).all()
    
    return render_template(
        'crm/deals.html',
        deals=deals_list,
        status=status,
        all_statuses=[s.name for s in DealStatus]
    )

@crm.route('/deals/<int:deal_id>')
@crm_access_required
def deal_detail(deal_id):
    """交易详情页面"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    deal = Deal.query.get_or_404(deal_id)
    customer = Customer.query.get(deal.customer_id)
    
    # 验证用户是否有权限访问此交易
    if customer.created_by_id != user_id and not is_admin:
        flash('您没有权限查看此交易', 'danger')
        return redirect(url_for('crm.deals'))
        
    return render_template('crm/deal_detail.html', deal=deal)

@crm.route('/customers/<int:customer_id>/deals/new', methods=['GET', 'POST'])
@crm_access_required
def new_deal(customer_id):
    """新建交易"""
    user_id = session.get('user_id')
    customer = Customer.query.get_or_404(customer_id)
    
    # 验证用户是否有权限访问此客户
    if customer.created_by_id != user_id and session.get('role') not in ['owner', 'admin']:
        flash('您没有权限为此客户创建交易', 'danger')
        return redirect(url_for('crm.customers'))
    
    leads = Lead.query.filter_by(customer_id=customer_id).all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('交易标题不能为空', 'danger')
            return redirect(url_for('crm.new_deal', customer_id=customer_id))
        
        try:
            status = DealStatus[request.form.get('status', 'DRAFT')]
        except KeyError:
            status = DealStatus.DRAFT
        
        value = float(request.form.get('value', 0))
        
        expected_close_date = None
        if request.form.get('expected_close_date'):
            try:
                expected_close_date = datetime.strptime(request.form.get('expected_close_date'), '%Y-%m-%d')
            except ValueError:
                pass
        
        # 挖矿相关数据
        mining_capacity = float(request.form.get('mining_capacity', 0)) if request.form.get('mining_capacity') else None
        electricity_cost = float(request.form.get('electricity_cost', 0)) if request.form.get('electricity_cost') else None
        contract_term = int(request.form.get('contract_term', 0)) if request.form.get('contract_term') else None
        
        lead_id = int(request.form.get('lead_id')) if request.form.get('lead_id') else None
        
        # 负责人默认为创建者
        assigned_to = request.form.get('assigned_to')
        
        deal = Deal(
            customer_id=customer_id,
            lead_id=lead_id,
            title=title,
            status=status,
            value=value,
            currency=request.form.get('currency', 'USD'),
            assigned_to=assigned_to,
            assigned_to_id=user_id,  # 设置负责人ID
            description=request.form.get('description'),
            expected_close_date=expected_close_date,
            mining_capacity=mining_capacity,
            electricity_cost=electricity_cost,
            contract_term=contract_term,
            created_by_id=user_id  # 记录创建者ID
        )
        
        db.session.add(deal)
        db.session.commit()
        
        # 添加活动记录
        activity = Activity(
            customer_id=customer_id,
            deal_id=deal.id,
            lead_id=lead_id,
            type="创建",
            summary=f"创建了新交易: {title}",
            details=request.form.get('description'),
            created_by=session.get('email'),
            created_by_id=user_id
        )
        db.session.add(activity)
        db.session.commit()
        
        # 如果从商机创建，更新商机状态
        if lead_id:
            lead = Lead.query.get(lead_id)
            if lead:
                lead.status = LeadStatus.NEGOTIATION
                db.session.commit()
        
        flash(f'已成功创建交易: {title}', 'success')
        return redirect(url_for('crm.deal_detail', deal_id=deal.id))
    
    # 默认值
    deal = None
    lead_id = request.args.get('lead_id')
    if lead_id:
        lead = Lead.query.get(lead_id)
        if lead:
            deal = Deal(
                title=lead.title,
                value=lead.estimated_value,  # 使用value而不是estimated_value
                description=lead.description
            )
    
    return render_template(
        'crm/deal_form.html', 
        customer=customer, 
        leads=leads,
        deal=deal, 
        lead_id=lead_id,
        all_statuses=DealStatus
    )

# 活动记录
@crm.route('/activities')
@crm_access_required
def activities():
    """活动记录列表页面"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    # 获取用户可访问的客户ID列表
    customer_ids = [c.id for c in get_user_customers(user_id, include_all=is_admin).all()]
    
    # 如果没有可访问的客户，显示空列表
    if not customer_ids:
        return render_template('crm/activities.html', activities=[])
    
    # 基于可访问的客户进行查询
    activities_list = Activity.query.filter(
        Activity.customer_id.in_(customer_ids)
    ).order_by(Activity.created_at.desc()).limit(100).all()
    
    return render_template('crm/activities.html', activities=activities_list)

@crm.route('/activities/new', methods=['POST'])
@crm_access_required
def new_activity():
    """新建活动记录 (AJAX)"""
    try:
        data = request.json
        user_id = session.get('user_id')
        
        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({'success': False, 'message': '未提供客户ID'}), 400
            
        # 检查客户是否存在
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'success': False, 'message': '客户不存在'}), 404
        
        # 验证用户是否有权限访问此客户
        if customer.created_by_id != user_id and session.get('role') not in ['owner', 'admin']:
            return jsonify({'success': False, 'message': '您没有权限为此客户添加活动'}), 403
            
        activity = Activity(
            customer_id=customer_id,
            lead_id=data.get('lead_id'),
            deal_id=data.get('deal_id'),
            type=data.get('type', '备注'),
            summary=data.get('summary', ''),
            details=data.get('details', ''),
            created_by=session.get('email'),
            created_by_id=user_id
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'activity': {
                'id': activity.id,
                'type': activity.type,
                'summary': activity.summary,
                'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M'),
                'created_by': activity.created_by
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 客户备注更新
@crm.route('/customers/<int:customer_id>/update-notes', methods=['POST'])
@crm_access_required
def update_customer_notes(customer_id):
    """更新客户备注"""
    user_id = session.get('user_id')
    is_admin = session.get('role') in ['owner', 'admin']
    
    customer = Customer.query.get_or_404(customer_id)
    
    # 验证用户是否有权限访问此客户
    if customer.created_by_id != user_id and not is_admin:
        flash('您没有权限更新此客户的备注', 'danger')
        return redirect(url_for('crm.customers'))
    
    if request.method == 'POST':
        notes = request.form.get('notes', '')
        
        # 保存以前的备注以比较变化
        old_notes = customer.notes or ''
        
        # 更新备注
        customer.notes = notes
        db.session.commit()
        
        # 如果备注有变化，记录一条活动
        if old_notes != notes:
            activity = Activity(
                customer_id=customer_id,
                type="备注",
                summary="更新了客户备注",
                details="更新了客户备注信息",
                created_by=session.get('email'),
                created_by_id=user_id
            )
            db.session.add(activity)
            db.session.commit()
        
        flash('客户备注已更新', 'success')
        
    return redirect(url_for('crm.customer_detail', customer_id=customer_id))

# 添加到应用程序
def init_crm_routes(app):
    app.register_blueprint(crm)