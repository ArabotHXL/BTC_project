"""
HashInsight Enterprise - Admin Routes Blueprint
管理员路由

提供以下端点:
- /database-admin - 数据库管理中心 (SYSTEM_HEALTH)
- /api-management - API集成管理中心 (SYSTEM_PERFORMANCE)
- /security-center - 安全中心 (SYSTEM_HEALTH)
- /backup-recovery - 备份恢复中心 (SYSTEM_HEALTH)
- /admin/login_records, /login-records - 登录记录 (SYSTEM_EVENT)
- /admin/login_dashboard, /login-dashboard - 登录数据分析仪表盘 (SYSTEM_EVENT)
- /admin/user_access, /user-access - 用户访问管理 (USER_LIST_VIEW)
- /admin/user_access/add - 添加用户访问权限 (USER_CREATE)
- /admin/user_access/extend/<int:user_id>/<int:days> - 延长用户访问权限 (USER_EDIT)
- /admin/user_access/view/<int:user_id> - 查看用户详情 (USER_LIST_VIEW)
- /admin/user_access/edit/<int:user_id> - 编辑用户信息 (USER_EDIT)
- /admin/user_access/revoke/<int:user_id> - 撤销用户访问权限 (USER_DISABLE)
- /admin/user_access/delete/<int:user_id> - 永久删除用户 (USER_DELETE - Owner only!)
- /admin/migrate_to_crm - 迁移用户数据到CRM (SYSTEM_HEALTH)
- /admin/create-user - 管理员创建用户 (USER_CREATE)
- /admin/users - 用户列表 (USER_LIST_VIEW)
- /admin/verify-user/<int:user_id> - 验证用户邮箱 (USER_EDIT)
- /admin/extend-access/<int:user_id> - 延长用户访问时间 (USER_EDIT)

Site Owner Management:
- /admin/site-owners - 站点负责人列表 (USER_LIST_VIEW)
- /admin/site-owners/create - 创建站点负责人 (USER_CREATE)
- /admin/site-owners/<id>/toggle-status - 启用/禁用站点负责人 (USER_DISABLE)
- /admin/site-owners/<id>/assign-site - 分配站点给负责人 (USER_EDIT)
- /admin/site-owners/<id> - 查看站点负责人详情 (USER_LIST_VIEW)

RBAC Permission Matrix Applied (via @requires_module_access decorator):
- SYSTEM_HEALTH: Owner/Admin = FULL, others = NONE (database-admin, security-center, backup-recovery, migrate_to_crm)
- SYSTEM_PERFORMANCE: Owner/Admin = FULL, others = NONE (api-management)
- SYSTEM_EVENT: Owner/Admin = FULL, Mining_Site_Owner = READ, others = NONE (login_records, login_dashboard)
- USER_CREATE: Owner/Admin = FULL
- USER_EDIT: Owner/Admin = FULL  
- USER_DISABLE: Owner/Admin = FULL
- USER_DELETE: ONLY Owner = FULL (Admin cannot delete!)
- USER_ROLE_ASSIGN: Owner/Admin = FULL
- USER_LIST_VIEW: Owner/Admin = FULL, Mining_Site_Owner/Client/Customer = READ

Decorator Layering (correct order, outermost first):
1. @admin_bp.route() - Route registration
2. @login_required - Authentication check
3. @requires_module_access() - RBAC permission check
4. Other decorators (rate_limit, csrf_protect, log_access_attempt)

Code Organization:
- Extracted helper functions for lazy loading models
- Centralized user list query in get_user_list() function
- All routes use proper RBAC decorators instead of ad-hoc session role checks
"""

import os
import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session, g, render_template, redirect, url_for, flash, render_template_string

from common.rbac import requires_module_access, Module

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


def get_db():
    """Lazy load database to avoid circular imports"""
    from db import db
    return db


def get_user_access_model():
    """Lazy load UserAccess model"""
    from models import UserAccess
    return UserAccess


def get_login_record_model():
    """Lazy load LoginRecord model"""
    from models import LoginRecord
    return LoginRecord


def get_user_list():
    """Get ordered user list for admin pages
    
    Note: Caching of ORM objects is intentionally avoided to prevent
    DetachedInstanceError and stale data issues. Admin pages are accessed
    infrequently enough that database query overhead is acceptable.
    """
    UserAccess = get_user_access_model()
    return UserAccess.query.order_by(UserAccess.created_at.desc()).all()


def get_user_role(email):
    """根据用户邮箱获取角色"""
    UserAccess = get_user_access_model()
    user = UserAccess.query.filter_by(email=email).first()
    if user and user.has_access:
        return user.role
    return None


def has_role(required_roles):
    """检查当前用户是否拥有指定角色之一"""
    email = session.get('email')
    if not email:
        return False
    
    user_role = get_user_role(email)
    if not user_role:
        return False
        
    if user_role == 'owner':
        return True
        
    return user_role in required_roles


try:
    from auth import login_required
except ImportError:
    def login_required(f):
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get('authenticated'):
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated

try:
    from decorators import requires_admin_or_owner, log_access_attempt
except ImportError:
    logger.warning("Decorators module not available, using fallback decorators")
    def requires_admin_or_owner(f):
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            if not has_role(['owner', 'admin']):
                flash('Access denied. Admin or Owner privileges required.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    
    def log_access_attempt(name):
        def decorator(f):
            return f
        return decorator

try:
    from rate_limiting import rate_limit
except ImportError:
    logger.warning("Rate limiting module not available, using fallback")
    def rate_limit(max_requests=10, window_minutes=60, feature_name=""):
        def decorator(f):
            return f
        return decorator

try:
    from security_enhancements import SecurityManager
except ImportError:
    logger.warning("Security enhancements module not available, using fallback")
    class SecurityManager:
        @staticmethod
        def csrf_protect(f):
            return f


@admin_bp.route('/database-admin')
@login_required
@requires_module_access(Module.SYSTEM_HEALTH, require_full=True)
def database_admin():
    """数据库管理中心 - SYSTEM_HEALTH权限 (Owner/Admin only)"""
    try:
        db = get_db()
        from sqlalchemy import text
        
        db_stats = {
            'total_tables': 0,
            'total_records': 0,
            'database_size': '0 MB',
            'last_backup': 'Never',
            'connection_status': 'Connected'
        }
        
        table_info = []
        try:
            result = db.session.execute(text("SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public'"))
            for row in result:
                table_info.append({
                    'name': row[1],
                    'schema': row[0],
                    'estimated_rows': 0
                })
        except Exception as e:
            logger.warning(f"获取表信息失败: {e}")
        
        return render_template('owner/database_admin.html',
                             db_stats=db_stats,
                             table_info=table_info,
                             current_lang=session.get('language', 'en'))
    except Exception as e:
        logger.error(f"数据库管理页面错误: {e}")
        return render_template('error.html', error=str(e)), 500


@admin_bp.route('/api-management')
@login_required
@requires_module_access(Module.SYSTEM_PERFORMANCE, require_full=True)
def api_management():
    """API集成管理中心 - SYSTEM_PERFORMANCE权限 (Owner/Admin only)"""
    try:
        api_status = {
            'coingecko': {'status': 'active', 'last_call': '2 minutes ago', 'rate_limit': '100/min'},
            'blockchain_info': {'status': 'active', 'last_call': '5 minutes ago', 'rate_limit': 'Unlimited'},
            'pinata_ipfs': {'status': 'configured', 'last_call': 'Never', 'rate_limit': '1000/month'},
            'ankr_rpc': {'status': 'error', 'last_call': '1 hour ago', 'rate_limit': '100/day'},
            'base_rpc': {'status': 'active', 'last_call': '30 seconds ago', 'rate_limit': 'Unlimited'}
        }
        
        web3_integrations = [
            {'name': 'Base L2网络', 'type': 'Blockchain', 'status': 'connected', 'url': 'https://base.org'},
            {'name': 'SLA NFT合约', 'type': 'Smart Contract', 'status': 'pending', 'url': '#'},
            {'name': 'IPFS存储', 'type': 'Storage', 'status': 'configured', 'url': 'https://pinata.cloud'}
        ]
        
        return render_template('owner/api_management.html',
                             api_status=api_status,
                             web3_integrations=web3_integrations,
                             current_lang=session.get('language', 'en'))
    except Exception as e:
        logger.error(f"API管理页面错误: {e}")
        return render_template('error.html', error=str(e)), 500


@admin_bp.route('/security-center')
@login_required
@requires_module_access(Module.SYSTEM_HEALTH, require_full=True)
def security_center():
    """安全中心 - 集成区块链安全功能 - SYSTEM_HEALTH权限 (Owner/Admin only)"""
    try:
        security_status = {
            'encryption_enabled': bool(os.environ.get('ENCRYPTION_PASSWORD')),
            'blockchain_secured': bool(os.environ.get('BLOCKCHAIN_PRIVATE_KEY')),
            'ssl_enabled': True,
            'csrf_protection': True,
            'rate_limiting': True,
            'audit_logging': True
        }
        
        recent_events = [
            {'time': '5 minutes ago', 'event': 'Successful login', 'user': session.get('email', 'Unknown'), 'risk': 'low'},
            {'time': '1 hour ago', 'event': 'API key validation', 'user': 'System', 'risk': 'low'},
            {'time': '2 hours ago', 'event': 'Blockchain verification', 'user': 'System', 'risk': 'low'}
        ]
        
        return render_template('owner/security_center.html',
                             security_status=security_status,
                             recent_events=recent_events,
                             current_lang=session.get('language', 'en'))
    except Exception as e:
        logger.error(f"安全中心页面错误: {e}")
        return render_template('error.html', error=str(e)), 500


@admin_bp.route('/backup-recovery')
@login_required
@requires_module_access(Module.SYSTEM_HEALTH, require_full=True)
def backup_recovery():
    """备份恢复中心 - SYSTEM_HEALTH权限 (Owner/Admin only)"""
    try:
        backup_status = {
            'last_backup': 'Never',
            'backup_size': '0 MB',
            'auto_backup_enabled': False,
            'backup_location': 'Local Storage',
            'retention_days': 30
        }
        
        backup_history = []
        
        return render_template('owner/backup_recovery.html',
                             backup_status=backup_status,
                             backup_history=backup_history,
                             current_lang=session.get('language', 'en'))
    except Exception as e:
        logger.error(f"备份恢复页面错误: {e}")
        return render_template('error.html', error=str(e)), 500


@admin_bp.route('/admin/login_records')
@admin_bp.route('/login-records')
@login_required
@requires_module_access(Module.SYSTEM_EVENT, require_full=True)
def login_records():
    """拥有者查看登录记录 - SYSTEM_EVENT权限 (Owner/Admin only)"""
    LoginRecord = get_login_record_model()
    records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).limit(100).all()
    return render_template('login_records.html', records=records)
    

@admin_bp.route('/admin/login_dashboard')
@admin_bp.route('/login-dashboard')
@login_required
@requires_module_access(Module.SYSTEM_EVENT, require_full=True)
def login_dashboard():
    """拥有者查看登录数据分析仪表盘 - SYSTEM_EVENT权限 (Owner/Admin only) - 需要Pro订阅"""
    current_role = session.get('role', 'guest')
    if current_role != 'owner':
        try:
            from decorators import get_user_plan
            user_plan = get_user_plan()
            
            if not getattr(user_plan, 'allow_advanced_analytics', False):
                return render_template('upgrade_required.html',
                                     feature='Advanced Analytics Dashboard',
                                     required_plan='pro',
                                     current_plan=getattr(user_plan, 'id', 'free')), 402
        except ImportError:
            pass
    
    LoginRecord = get_login_record_model()
    all_records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).all()
    
    utc_to_est_offset = timedelta(hours=-5)
    
    records_with_est = []
    for record in all_records:
        record_copy = {
            'id': record.id,
            'email': record.email,
            'login_time': record.login_time,
            'successful': record.successful,
            'ip_address': record.ip_address,
            'login_location': record.login_location,
            'est_time': (record.login_time + utc_to_est_offset).strftime("%Y-%m-%d %H:%M:%S")
        }
        
        display_location = "未知/Unknown"
        if record.login_location and ',' in record.login_location:
            parts = record.login_location.split(',')
            if len(parts) >= 3:
                country = parts[0].strip()
                region = parts[1].strip()
                city = parts[2].strip()
                display_location = f"{city}, {region}, {country}"
            elif len(parts) == 2:
                country = parts[0].strip()
                region = parts[1].strip()
                display_location = f"{region}, {country}"
            else:
                display_location = parts[0].strip()
        
        record_copy['display_location'] = display_location
        records_with_est.append(record_copy)
    
    recent_records = records_with_est[:100]
    
    unique_users = len(set(r['email'] for r in records_with_est))
    total_logins = len(records_with_est)
    failed_logins = sum(1 for r in records_with_est if not r['successful'])
    
    today = datetime.utcnow() + utc_to_est_offset
    today_start = datetime(today.year, today.month, today.day, 0, 0, 0) - utc_to_est_offset
    today_logins = sum(1 for r in records_with_est if r['login_time'] >= today_start)
    
    stats = {
        'unique_users': unique_users,
        'total_logins': total_logins,
        'failed_logins': failed_logins,
        'today_logins': today_logins
    }
    
    trend_data = {'dates': [], 'counts': []}
    
    end_date = today
    start_date = end_date - timedelta(days=29)
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        trend_data['dates'].append(date_str)
        
        day_start = datetime(current_date.year, current_date.month, current_date.day, 0, 0, 0) - utc_to_est_offset
        day_end = day_start + timedelta(days=1)
        day_count = sum(1 for r in records_with_est 
                        if r['login_time'] >= day_start and r['login_time'] < day_end)
        
        trend_data['counts'].append(day_count)
        current_date += timedelta(days=1)
    
    time_data = {'hours': [], 'counts': []}
    hour_counts = [0] * 24
    
    for record in records_with_est:
        login_time = record['login_time'] + utc_to_est_offset
        hour = login_time.hour
        hour_counts[hour] += 1
    
    for hour in range(24):
        hour_str = f"{hour:02d}:00"
        time_data['hours'].append(hour_str)
        time_data['counts'].append(hour_counts[hour])
    
    geo_data = {'countries': [], 'counts': []}
    country_counts = {}
    
    for record in records_with_est:
        if record['login_location'] and ',' in record['login_location']:
            country = record['login_location'].split(',')[0].strip()
            if country in country_counts:
                country_counts[country] += 1
            else:
                country_counts[country] = 1
        else:
            country = "未知/Unknown"
            if country in country_counts:
                country_counts[country] += 1
            else:
                country_counts[country] = 1
    
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    top_countries = sorted_countries[:10]
    
    for country, count in top_countries:
        geo_data['countries'].append(country)
        geo_data['counts'].append(count)
    
    if len(sorted_countries) > 10:
        others_count = sum(count for _, count in sorted_countries[10:])
        if g.language == 'en':
            geo_data['countries'].append("Others")
        else:
            geo_data['countries'].append("其他")
        geo_data['counts'].append(others_count)
    
    return render_template('login_dashboard.html', 
                          records=recent_records, 
                          stats=stats, 
                          trend_data=trend_data,
                          time_data=time_data,
                          geo_data=geo_data)


@admin_bp.route('/admin/user_access')
@admin_bp.route('/user-access')
@login_required
@requires_module_access(Module.USER_LIST_VIEW)
@log_access_attempt('用户访问管理')
def user_access():
    """管理员管理用户访问权限 - 需要Pro订阅"""
    logger.info(f"[user_access] 进入路由, session role={session.get('role')}, email={session.get('email')}")
    if session.get('role') != 'owner':
        try:
            from decorators import get_user_plan
            user_plan = get_user_plan()
            
            if not getattr(user_plan, 'allow_user_management', False):
                return render_template('upgrade_required.html',
                                     feature='User Management System',
                                     required_plan='pro',
                                     current_plan=getattr(user_plan, 'id', 'free')), 402
        except ImportError:
            pass
    
    try:
        users = get_user_list()
        logger.info(f"[user_access] 获取到 {len(users)} 个用户")
    except Exception as e:
        logger.error(f"[user_access] 获取用户列表失败: {e}")
        flash('加载用户列表失败，请刷新重试', 'danger')
        return redirect(url_for('index'))
    
    current_user_role = session.get('role', '未设置')
    logger.info(f"[user_access] 准备渲染模板, 角色: {current_user_role}")
    
    return render_template('user_access.html', users=users)


@admin_bp.route('/admin/user_access/add', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_minutes=60, feature_name="admin_user_add")
@SecurityManager.csrf_protect
@requires_module_access(Module.USER_CREATE, require_full=True)
@log_access_attempt('添加用户访问权限')
def add_user_access():
    """添加新用户访问权限"""
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        name = request.form['name']
        email = request.form['email']
        
        company = request.form.get('company')
        position = request.form.get('position')
        notes = request.form.get('notes')
        role = request.form.get('role', 'guest')
        
        valid_roles = ['owner', 'admin', 'mining_site_owner', 'operator', 'client', 'guest']
        if role not in valid_roles:
            role = 'guest'
            
        current_user_role = get_user_role(session.get('email'))
        if current_user_role == 'admin' and role == 'owner':
            flash('管理员不能创建拥有者角色用户', 'warning')
            role = 'admin'
            
        existing_user = UserAccess.query.filter_by(email=email).first()
        if existing_user:
            flash(f'邮箱 {email} 已存在，请使用其他邮箱', 'warning')
            return redirect(url_for('admin.user_access'))
        
        new_user = UserAccess(
            name=name,
            email=email,
            company=company,
            position=position,
            notes=notes,
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        role_names = {
            "owner": "拥有者", "admin": "管理员", "mining_site_owner": "矿场站点负责人",
            "operator": "运维人员", "client": "客户", "guest": "访客"
        }
        role_name = role_names.get(role, role)
        flash(f'用户 {name} ({email}) 已成功添加，角色为"{role_name}"，永久有效', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加用户访问权限时出错: {str(e)}")
        flash(f'添加用户失败: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_access'))


@admin_bp.route('/admin/user_access/extend/<int:user_id>/<int:days>', methods=['POST'])
@login_required
@requires_module_access(Module.USER_EDIT, require_full=True)
def extend_user_access(user_id, days):
    """延长用户访问权限"""
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        user = UserAccess.query.get_or_404(user_id)
        
        user.extend_access(days)
        db.session.commit()
        
        
        flash(f'用户 {user.name} 的访问权限已延长 {days} 天', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"延长用户访问权限时出错: {str(e)}")
        flash(f'延长用户访问权限失败: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_access'))


@admin_bp.route('/admin/user_access/view/<int:user_id>', methods=['GET'])
@login_required
@requires_module_access(Module.USER_LIST_VIEW)
def view_user_details(user_id):
    """查看用户详细信息"""
    
    UserAccess = get_user_access_model()
    
    try:
        user = UserAccess.query.get_or_404(user_id)
        
        current_lang = session.get('language', 'zh')
        
        html = render_template_string('''
        <div class="user-details">
            <div class="row g-3">
                <div class="col-12 text-center mb-3">
                    <div class="user-avatar-large mx-auto mb-3">
                        {{ user.name[0]|upper if user.name else '?' }}
                    </div>
                    <h5>{{ user.name }}</h5>
                    <span class="role-badge role-{{ user.role }} mb-2 d-inline-block">
                        {% if user.role == 'owner' %}{% if current_lang == 'en' %}Owner{% else %}拥有者{% endif %}
                        {% elif user.role == 'admin' %}{% if current_lang == 'en' %}Admin{% else %}管理员{% endif %}
                        {% elif user.role == 'mining_site_owner' %}{% if current_lang == 'en' %}Mining Manager{% else %}矿场管理{% endif %}
                        {% else %}{% if current_lang == 'en' %}Guest{% else %}客人{% endif %}
                        {% endif %}
                    </span>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Email{% else %}邮箱{% endif %}</label>
                    <p class="mb-2">{{ user.email }}</p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Username{% else %}用户名{% endif %}</label>
                    <p class="mb-2">{{ user.username or '-' }}</p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Company{% else %}公司{% endif %}</label>
                    <p class="mb-2">{{ user.company or '-' }}</p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Position{% else %}职位{% endif %}</label>
                    <p class="mb-2">{{ user.position or '-' }}</p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Access Status{% else %}访问状态{% endif %}</label>
                    <p class="mb-2">
                        {% if user.has_access %}
                        <span class="badge bg-success">
                            <i class="bi bi-check-circle me-1"></i>{% if current_lang == 'en' %}Active{% else %}有效{% endif %}
                        </span>
                        {% else %}
                        <span class="badge bg-danger">
                            <i class="bi bi-x-circle me-1"></i>{% if current_lang == 'en' %}Expired{% else %}过期{% endif %}
                        </span>
                        {% endif %}
                    </p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Days Remaining{% else %}剩余天数{% endif %}</label>
                    <p class="mb-2">{{ user.days_remaining }}{% if current_lang == 'en' %} days{% else %} 天{% endif %}</p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Created Date{% else %}创建时间{% endif %}</label>
                    <p class="mb-2">{{ user.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Last Login{% else %}最后登录{% endif %}</label>
                    <p class="mb-2">
                        {% if user.last_login %}
                            {{ user.last_login.strftime('%Y-%m-%d %H:%M:%S') }}
                        {% else %}
                            {% if current_lang == 'en' %}Never logged in{% else %}从未登录{% endif %}
                        {% endif %}
                    </p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Email Verified{% else %}邮箱验证{% endif %}</label>
                    <p class="mb-2">
                        {% if user.is_email_verified %}
                        <span class="badge bg-success">{% if current_lang == 'en' %}Verified{% else %}已验证{% endif %}</span>
                        {% else %}
                        <span class="badge bg-warning">{% if current_lang == 'en' %}Not Verified{% else %}未验证{% endif %}</span>
                        {% endif %}
                    </p>
                </div>
                <div class="col-md-6">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Expires At{% else %}过期时间{% endif %}</label>
                    <p class="mb-2">{{ user.expires_at.strftime('%Y-%m-%d %H:%M:%S') if user.expires_at else '-' }}</p>
                </div>
                {% if user.notes %}
                <div class="col-12">
                    <label class="form-label small text-muted">{% if current_lang == 'en' %}Notes{% else %}备注{% endif %}</label>
                    <p class="mb-2">{{ user.notes }}</p>
                </div>
                {% endif %}
            </div>
        </div>
        <style>
            .user-avatar-large {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #ffc107, #ffb300);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                color: #000;
                font-size: 2rem;
            }
        </style>
        ''', user=user, current_lang=current_lang)
        
        return jsonify({'success': True, 'html': html})
    except Exception as e:
        logger.error(f"查看用户详情时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'查看用户详情失败: {str(e)}'})


@admin_bp.route('/admin/user_access/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@requires_module_access(Module.USER_EDIT, require_full=True)
def edit_user_access(user_id):
    """编辑用户信息"""
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        user = UserAccess.query.get_or_404(user_id)
        
        if request.method == 'POST':
            user.name = request.form['name']
            user.email = request.form['email']
            
            username_value = request.form.get('username', '').strip()
            user.username = username_value if username_value else None
            
            user.company = request.form.get('company')
            user.position = request.form.get('position')
            user.notes = request.form.get('notes')
            
            access_days = request.form.get('access_days')
            if access_days:
                user.access_days = int(access_days)
                user.calculate_expiry()
            
            if has_role(['owner', 'admin']):
                new_role = request.form.get('role')
                if new_role in ['owner', 'admin', 'mining_site_owner', 'guest']:
                    current_user_role = get_user_role(session.get('email'))
                    if current_user_role == 'admin' and new_role == 'owner':
                        flash('管理员不能将用户角色设置为拥有者', 'warning')
                    else:
                        user.role = new_role
            
            if has_role(['owner']):
                subscription_plan = request.form.get('subscription_plan')
                if subscription_plan in ['free', 'basic', 'pro']:
                    user.subscription_plan = subscription_plan
                    logger.info(f"用户 {user.name} 的订阅计划已更新为: {subscription_plan}")
            
            db.session.commit()
            
            flash(f'用户 {user.name} 信息已成功更新', 'success')
            return redirect(url_for('admin.user_access'))
        
        current_lang = session.get('language', 'en')
        try:
            return render_template('admin/edit_user_standalone.html', user=user, current_lang=current_lang)
        except Exception as template_error:
            logger.error(f"模板渲染错误: {str(template_error)}")
            flash(f'无法加载编辑页面: {str(template_error)}', 'danger')
            return redirect('/admin/user_access')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"编辑用户信息时出错: {str(e)}")
        flash(f'编辑用户信息失败: {str(e)}', 'danger')
        return redirect(url_for('admin.user_access'))


@admin_bp.route('/admin/user_access/revoke/<int:user_id>', methods=['POST'])
@login_required
@requires_module_access(Module.USER_DISABLE, require_full=True)
def revoke_user_access(user_id):
    """撤销用户访问权限"""
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        user = UserAccess.query.get_or_404(user_id)
        
        user.revoke_access()
        db.session.commit()
        
        
        flash(f'用户 {user.name} 的访问权限已撤销', 'warning')
    except Exception as e:
        db.session.rollback()
        logger.error(f"撤销用户访问权限时出错: {str(e)}")
        flash(f'撤销用户访问权限失败: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_access'))


@admin_bp.route('/admin/user_access/delete/<int:user_id>', methods=['POST', 'DELETE'])
@login_required
@requires_module_access(Module.USER_DELETE, require_full=True)
def delete_user(user_id):
    """永久删除用户 - 仅限Owner角色
    
    CRITICAL: This operation permanently deletes the user from the database.
    Only Owner role can perform this action per RBAC matrix.
    """
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        user = UserAccess.query.get_or_404(user_id)
        user_name = user.name
        user_email = user.email
        
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"用户 {user_name} ({user_email}) 已被永久删除")
        flash(f'用户 {user_name} ({user_email}) 已被永久删除', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除用户时出错: {str(e)}")
        flash(f'删除用户失败: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_access'))


@admin_bp.route('/admin/migrate_to_crm')
@login_required
@requires_module_access(Module.SYSTEM_HEALTH, require_full=True)
def migrate_to_crm():
    """将用户访问权限数据迁移到CRM系统中 - SYSTEM_HEALTH权限 (Owner/Admin only)"""
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        from crm_models import Customer, Contact, Lead, Activity, LeadStatus
    except ImportError:
        logger.error("CRM models not available")
        flash('CRM模块不可用', 'danger')
        return redirect(url_for('admin.user_access'))
    
    try:
        users = UserAccess.query.all()
        logger.info(f"开始迁移 {len(users)} 个用户数据到CRM系统")
        
        migrated_count = 0
        already_exists_count = 0
        
        for user in users:
            from sqlalchemy import or_, and_
            existing_customer = Customer.query.filter(
                or_(
                    Customer.email == user.email,
                    and_(Customer.name == user.name, Customer.company == user.company)
                )
            ).first()
            
            if existing_customer:
                logger.info(f"客户已存在: {user.name} ({user.email})")
                already_exists_count += 1
                continue
            
            customer = Customer(
                name=user.name,
                company=user.company,
                email=user.email,
                customer_type="企业" if user.company else "个人",
                tags="已迁移用户,授权用户"
            )
            customer.created_at = user.created_at
            db.session.add(customer)
            db.session.flush()
            
            contact = Contact(
                customer_id=customer.id,
                name=user.name,
                email=user.email,
                position=user.position,
                primary=True,
                notes=f"从用户访问系统迁移 - 角色: {user.role}"
            )
            db.session.add(contact)
            
            lead = Lead(
                customer_id=customer.id,
                title=f"{user.name} 访问授权",
                status=LeadStatus.QUALIFIED if user.has_access else LeadStatus.LOST,
                source="系统迁移",
                estimated_value=0.0,
                assigned_to="系统管理员",
                description=f"用户访问授权信息 - 创建于 {user.created_at.strftime('%Y-%m-%d')}, "
                          f"过期于 {user.expires_at.strftime('%Y-%m-%d')}。"
                          f"\n备注: {user.notes if user.notes else '无'}"
            )
            db.session.add(lead)
            
            activity = Activity(
                customer_id=customer.id,
                lead_id=lead.id,
                type="创建",
                summary="从用户访问系统迁移",
                details=f"用户数据已从访问管理系统迁移到CRM系统。\n原始角色: {user.role}\n"
                        f"访问状态: {'永久有效' if user.expires_at is None else user.expires_at.strftime('%Y-%m-%d')}\n"
                        f"最后登录: {user.last_login.strftime('%Y-%m-%d') if user.last_login else '从未登录'}",
                created_by="系统管理员"
            )
            db.session.add(activity)
            
            db.session.commit()
            
            logger.info(f"成功迁移用户: {user.name} ({user.email}) -> 客户ID: {customer.id}")
            migrated_count += 1
            
        flash(f'迁移完成！{migrated_count} 个用户已迁移，{already_exists_count} 个用户已跳过（已存在）。', 'success')
        return redirect(url_for('crm.crm_dashboard'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"用户数据迁移失败: {str(e)}")
        flash(f'迁移失败: {str(e)}', 'danger')
        return redirect(url_for('admin.user_access'))


@admin_bp.route('/admin/create-user', methods=['GET', 'POST'])
@login_required
@requires_module_access(Module.USER_CREATE, require_full=True)
def admin_create_user():
    """管理员创建测试用户"""
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    if request.method == 'GET':
        return render_template('admin/create_user.html')
    
    try:
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'guest')
        skip_email_verification = request.form.get('skip_email_verification') == 'on'
        
        if not email:
            flash('邮箱地址为必填项', 'error')
            return render_template('admin/create_user.html')
        
        if UserAccess.query.filter_by(email=email).first():
            flash('该邮箱已存在', 'error')
            return render_template('admin/create_user.html')
        
        if username and UserAccess.query.filter_by(username=username).first():
            flash('该用户名已存在', 'error')
            return render_template('admin/create_user.html')
        
        new_user = UserAccess(
            name=name or username or email.split('@')[0],
            email=email,
            username=username if username else None,
            role=role
        )
        
        if password:
            new_user.set_password(password)
        
        if skip_email_verification:
            new_user.is_email_verified = True
        else:
            new_user.generate_email_verification_token()
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'用户 {email} 创建成功！角色: {role}，永久有效', 'success')
        return redirect(url_for('admin.admin_create_user'))
        
    except Exception as e:
        logger.error(f"管理员创建用户错误: {e}")
        flash('创建用户失败，请重试', 'error')
        return render_template('admin/create_user.html')


@admin_bp.route('/admin/users')
@login_required
@requires_module_access(Module.USER_LIST_VIEW)
def admin_user_list():
    """管理员查看用户列表"""
    
    users = get_user_list()
    return render_template('admin/user_list.html', users=users)


@admin_bp.route('/admin/verify-user/<int:user_id>', methods=['POST'])
@login_required
@requires_module_access(Module.USER_EDIT, require_full=True)
def admin_verify_user(user_id):
    """管理员验证用户邮箱"""
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    user = UserAccess.query.get_or_404(user_id)
    user.verify_email()
    db.session.commit()
    
    
    return jsonify({'success': True})


@admin_bp.route('/admin/extend-access/<int:user_id>', methods=['POST'])
@login_required
@requires_module_access(Module.USER_EDIT, require_full=True)
def admin_extend_access(user_id):
    """管理员延长用户访问时间"""
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    data = request.get_json()
    days = data.get('days', 30)
    
    user = UserAccess.query.get_or_404(user_id)
    user.extend_access(days)
    db.session.commit()
    
    
    return jsonify({'success': True})


# ==================== Site Owner Management ====================

def get_hosting_site_model():
    """Lazy load HostingSite model"""
    from models import HostingSite
    return HostingSite


@admin_bp.route('/admin/site-owners')
@login_required
@requires_module_access(Module.USER_LIST_VIEW, require_full=True)
def site_owner_list():
    """List all site owners (mining_site_owner role) - USER_LIST_VIEW permission"""
    try:
        db = get_db()
        UserAccess = get_user_access_model()
        HostingSite = get_hosting_site_model()
        
        site_owners = UserAccess.query.filter_by(role='mining_site_owner').order_by(UserAccess.created_at.desc()).all()
        
        owners_data = []
        for owner in site_owners:
            sites_owned = HostingSite.query.filter_by(owner_id=owner.id).all()
            customer_count = 0
            for site in sites_owned:
                customer_count += UserAccess.query.filter_by(managed_by_site_id=site.id).count()
            
            owners_data.append({
                'owner': owner,
                'sites_owned': sites_owned,
                'sites_count': len(sites_owned),
                'customer_count': customer_count
            })
        
        all_sites = HostingSite.query.filter(HostingSite.owner_id == None).all()
        
        return render_template('owner/site_owner_management.html',
                             owners_data=owners_data,
                             unassigned_sites=all_sites,
                             current_lang=session.get('language', 'en'))
    except Exception as e:
        logger.error(f"Site owner list error: {e}")
        flash(f'Error loading site owners: {str(e)}', 'danger')
        return redirect(url_for('index'))


@admin_bp.route('/admin/site-owners/create', methods=['POST'])
@login_required
@requires_module_access(Module.USER_CREATE, require_full=True)
@SecurityManager.csrf_protect
def create_site_owner():
    """Create a new site owner account - USER_CREATE permission"""
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        company = request.form.get('company', '').strip()
        password = request.form.get('password', '').strip()
        
        if not name or not email:
            flash('Name and email are required', 'danger')
            return redirect(url_for('admin.site_owner_list'))
        
        existing_user = UserAccess.query.filter_by(email=email).first()
        if existing_user:
            flash(f'Email {email} already exists', 'warning')
            return redirect(url_for('admin.site_owner_list'))
        
        new_owner = UserAccess(
            name=name,
            email=email,
            company=company,
            role='mining_site_owner'
        )
        
        if password:
            new_owner.set_password(password)
        
        db.session.add(new_owner)
        db.session.commit()
        
        flash(f'Site owner {name} created successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Create site owner error: {e}")
        flash(f'Failed to create site owner: {str(e)}', 'danger')
    
    return redirect(url_for('admin.site_owner_list'))


@admin_bp.route('/admin/site-owners/<int:owner_id>/toggle-status', methods=['POST'])
@login_required
@requires_module_access(Module.USER_DISABLE, require_full=True)
def toggle_site_owner_status(owner_id):
    """Enable/disable site owner - USER_DISABLE permission"""
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        owner = UserAccess.query.get_or_404(owner_id)
        
        if owner.role != 'mining_site_owner':
            flash('Invalid site owner', 'danger')
            return redirect(url_for('admin.site_owner_list'))
        
        owner.is_active = not owner.is_active
        db.session.commit()
        
        status = 'enabled' if owner.is_active else 'disabled'
        flash(f'Site owner {owner.name} has been {status}', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Toggle site owner status error: {e}")
        flash(f'Failed to toggle status: {str(e)}', 'danger')
    
    return redirect(url_for('admin.site_owner_list'))


@admin_bp.route('/admin/site-owners/<int:owner_id>/assign-site', methods=['POST'])
@login_required
@requires_module_access(Module.USER_EDIT, require_full=True)
def assign_site_to_owner(owner_id):
    """Assign a site to a site owner - USER_EDIT permission"""
    db = get_db()
    UserAccess = get_user_access_model()
    HostingSite = get_hosting_site_model()
    
    try:
        owner = UserAccess.query.get_or_404(owner_id)
        
        if owner.role != 'mining_site_owner':
            flash('Invalid site owner', 'danger')
            return redirect(url_for('admin.site_owner_list'))
        
        site_id = request.form.get('site_id')
        if not site_id:
            flash('Please select a site', 'warning')
            return redirect(url_for('admin.site_owner_list'))
        
        site = HostingSite.query.get_or_404(int(site_id))
        site.owner_id = owner.id
        db.session.commit()
        
        flash(f'Site "{site.name}" assigned to {owner.name}', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Assign site to owner error: {e}")
        flash(f'Failed to assign site: {str(e)}', 'danger')
    
    return redirect(url_for('admin.site_owner_list'))


@admin_bp.route('/admin/site-owners/<int:owner_id>')
@login_required
@requires_module_access(Module.USER_LIST_VIEW, require_full=True)
def view_site_owner_details(owner_id):
    """View site owner details with their customers and sites - USER_LIST_VIEW permission"""
    try:
        UserAccess = get_user_access_model()
        HostingSite = get_hosting_site_model()
        
        owner = UserAccess.query.get_or_404(owner_id)
        
        if owner.role != 'mining_site_owner':
            flash('Invalid site owner', 'danger')
            return redirect(url_for('admin.site_owner_list'))
        
        sites_owned = HostingSite.query.filter_by(owner_id=owner.id).all()
        
        sites_data = []
        total_customers = 0
        for site in sites_owned:
            customers = UserAccess.query.filter_by(managed_by_site_id=site.id).all()
            total_customers += len(customers)
            sites_data.append({
                'site': site,
                'customers': customers,
                'customer_count': len(customers)
            })
        
        unassigned_sites = HostingSite.query.filter(HostingSite.owner_id == None).all()
        
        return render_template('owner/site_owner_detail.html',
                             owner=owner,
                             sites_data=sites_data,
                             total_customers=total_customers,
                             unassigned_sites=unassigned_sites,
                             current_lang=session.get('language', 'en'))
    except Exception as e:
        logger.error(f"View site owner details error: {e}")
        flash(f'Error loading site owner details: {str(e)}', 'danger')
        return redirect(url_for('admin.site_owner_list'))
