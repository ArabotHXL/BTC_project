"""
客户关系管理 (CRM) 系统路由
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session
from datetime import datetime
import json
from sqlalchemy import or_

from models import db, Customer, Contact, Lead, Deal, Activity, LeadStatus, DealStatus
from auth import login_required

# 创建蓝图
crm = Blueprint('crm', __name__, url_prefix='/crm')

# 权限验证装饰器
def crm_access_required(view_function):
    """验证用户是否有CRM访问权限"""
    @login_required
    def wrapped_view(*args, **kwargs):
        if session.get('role') not in ['owner', 'admin', 'manager']:
            flash('您没有权限访问CRM系统', 'danger')
            return redirect(url_for('index'))
        return view_function(*args, **kwargs)
    wrapped_view.__name__ = view_function.__name__
    return wrapped_view

# CRM仪表盘
@crm.route('/')
@crm_access_required
def dashboard():
    """CRM系统仪表盘"""
    # 统计数据
    customers_count = Customer.query.count()
    leads_count = Lead.query.count()
    deals_count = Deal.query.count()
    deals_value = db.session.query(db.func.sum(Deal.value)).scalar() or 0
    
    # 最近活动
    recent_activities = Activity.query.order_by(Activity.created_at.desc()).limit(10).all()
    
    # 待跟进线索
    follow_up_leads = Lead.query.filter(
        Lead.status != LeadStatus.WON,
        Lead.status != LeadStatus.LOST,
        Lead.next_follow_up >= datetime.utcnow()
    ).order_by(Lead.next_follow_up).limit(5).all()
    
    # 近期交易
    recent_deals = Deal.query.filter(
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
    
    query = Customer.query
    
    if search:
        query = query.filter(or_(
            Customer.name.ilike(f'%{search}%'),
            Customer.company.ilike(f'%{search}%'),
            Customer.email.ilike(f'%{search}%')
        ))
    
    if tag:
        query = query.filter(Customer.tags.ilike(f'%{tag}%'))
        
    customers_list = query.order_by(Customer.name).all()
    
    # 获取所有标签
    all_tags = set()
    for customer in Customer.query.all():
        if customer.tags:
            customer_tags = [t.strip() for t in customer.tags.split(',')]
            all_tags.update(customer_tags)
    
    return render_template(
        'crm/customers.html',
        customers=customers_list,
        search=search,
        tag=tag,
        all_tags=sorted(all_tags)
    )

@crm.route('/customers/<int:customer_id>')
@crm_access_required
def customer_detail(customer_id):
    """客户详情页面"""
    customer = Customer.query.get_or_404(customer_id)
    return render_template('crm/customer_detail.html', customer=customer)

@crm.route('/customers/new', methods=['GET', 'POST'])
@crm_access_required
def new_customer():
    """新建客户"""
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
            mining_capacity=float(request.form.get('mining_capacity', 0)) if request.form.get('mining_capacity') else None
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash(f'已成功创建客户: {name}', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=customer.id))
    
    return render_template('crm/customer_form.html', customer=None)

@crm.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@crm_access_required
def edit_customer(customer_id):
    """编辑客户"""
    customer = Customer.query.get_or_404(customer_id)
    
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
        
        flash(f'已成功更新客户: {customer.name}', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=customer.id))
    
    return render_template('crm/customer_form.html', customer=customer)

@crm.route('/customers/<int:customer_id>/delete', methods=['POST'])
@crm_access_required
def delete_customer(customer_id):
    """删除客户"""
    customer = Customer.query.get_or_404(customer_id)
    name = customer.name
    
    db.session.delete(customer)
    db.session.commit()
    
    flash(f'已成功删除客户: {name}', 'success')
    return redirect(url_for('crm.customers'))

# 联系人管理
@crm.route('/customers/<int:customer_id>/contacts/new', methods=['GET', 'POST'])
@crm_access_required
def new_contact(customer_id):
    """新建联系人"""
    customer = Customer.query.get_or_404(customer_id)
    
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
        
        flash(f'已成功添加联系人: {name}', 'success')
        return redirect(url_for('crm.customer_detail', customer_id=customer_id))
    
    return render_template('crm/contact_form.html', customer=customer, contact=None)

# 商机管理
@crm.route('/leads')
@crm_access_required
def leads():
    """商机列表页面"""
    status = request.args.get('status', '')
    
    query = Lead.query
    
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
    lead = Lead.query.get_or_404(lead_id)
    return render_template('crm/lead_detail.html', lead=lead)

@crm.route('/customers/<int:customer_id>/leads/new', methods=['GET', 'POST'])
@crm_access_required
def new_lead(customer_id):
    """新建商机"""
    customer = Customer.query.get_or_404(customer_id)
    
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
        
        lead = Lead(
            customer_id=customer_id,
            title=title,
            status=status,
            source=request.form.get('source'),
            estimated_value=estimated_value,
            assigned_to=request.form.get('assigned_to'),
            description=request.form.get('description'),
            next_follow_up=next_follow_up
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
            created_by=session.get('email')
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
    
    query = Deal.query
    
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
    deal = Deal.query.get_or_404(deal_id)
    return render_template('crm/deal_detail.html', deal=deal)

@crm.route('/customers/<int:customer_id>/deals/new', methods=['GET', 'POST'])
@crm_access_required
def new_deal(customer_id):
    """新建交易"""
    customer = Customer.query.get_or_404(customer_id)
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
        
        deal = Deal(
            customer_id=customer_id,
            lead_id=lead_id,
            title=title,
            status=status,
            value=value,
            currency=request.form.get('currency', 'USD'),
            assigned_to=request.form.get('assigned_to'),
            description=request.form.get('description'),
            expected_close_date=expected_close_date,
            mining_capacity=mining_capacity,
            electricity_cost=electricity_cost,
            contract_term=contract_term
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
            created_by=session.get('email')
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
                estimated_value=lead.estimated_value,
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
    activities_list = Activity.query.order_by(Activity.created_at.desc()).limit(100).all()
    return render_template('crm/activities.html', activities=activities_list)

@crm.route('/activities/new', methods=['POST'])
@crm_access_required
def new_activity():
    """新建活动记录 (AJAX)"""
    try:
        data = request.json
        
        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({'success': False, 'message': '未提供客户ID'}), 400
            
        # 检查客户是否存在
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'success': False, 'message': '客户不存在'}), 404
        
        activity = Activity(
            customer_id=customer_id,
            lead_id=data.get('lead_id'),
            deal_id=data.get('deal_id'),
            type=data.get('type', '备注'),
            summary=data.get('summary', ''),
            details=data.get('details', ''),
            created_by=session.get('email')
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
    customer = Customer.query.get_or_404(customer_id)
    
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
                created_by=session.get('email')
            )
            db.session.add(activity)
            db.session.commit()
        
        flash('客户备注已更新', 'success')
        
    return redirect(url_for('crm.customer_detail', customer_id=customer_id))

# 添加到应用程序
def init_crm_routes(app):
    app.register_blueprint(crm)