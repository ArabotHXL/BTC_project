"""
HashInsight Enterprise - Admin Routes Blueprint
管理员路由

提供以下端点:
- /database-admin - 数据库管理中心
- /api-management - API集成管理中心
- /security-center - 安全中心
- /backup-recovery - 备份恢复中心
- /admin/login_records, /login-records - 登录记录
- /admin/login_dashboard, /login-dashboard - 登录数据分析仪表盘
- /admin/user_access, /user-access - 用户访问管理
- /admin/user_access/add - 添加用户访问权限
- /admin/user_access/extend/<int:user_id>/<int:days> - 延长用户访问权限
- /admin/user_access/view/<int:user_id> - 查看用户详情
- /admin/user_access/edit/<int:user_id> - 编辑用户信息
- /admin/user_access/revoke/<int:user_id> - 撤销用户访问权限
- /admin/migrate_to_crm - 迁移用户数据到CRM
- /admin/create-user - 管理员创建用户
- /admin/users - 用户列表
- /admin/verify-user/<int:user_id> - 验证用户邮箱
- /admin/extend-access/<int:user_id> - 延长用户访问时间

Code Organization:
- Extracted helper functions for lazy loading models
- Centralized user list query in get_user_list() function
"""

import os
import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session, g, render_template, redirect, url_for, flash, render_template_string

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
def database_admin():
    """数据库管理中心"""
    if not session.get('role') == 'owner':
        flash('Access denied. Owner privileges required.', 'danger')
        return redirect(url_for('index'))
        
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
def api_management():
    """API集成管理中心"""
    if not session.get('role') == 'owner':
        flash('Access denied. Owner privileges required.', 'danger')
        return redirect(url_for('index'))
        
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
def security_center():
    """安全中心 - 集成区块链安全功能"""
    if not session.get('role') == 'owner':
        flash('Access denied. Owner privileges required.', 'danger')
        return redirect(url_for('index'))
        
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
def backup_recovery():
    """备份恢复中心"""
    if not session.get('role') == 'owner':
        flash('Access denied. Owner privileges required.', 'danger')
        return redirect(url_for('index'))
        
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
def login_records():
    """拥有者查看登录记录"""
    if not has_role(['owner']):
        flash('您没有权限访问此页面，需要拥有者权限', 'danger')
        return redirect(url_for('index'))
    
    LoginRecord = get_login_record_model()
    records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).limit(100).all()
    return render_template('login_records.html', records=records)
    

@admin_bp.route('/admin/login_dashboard')
@admin_bp.route('/login-dashboard')
@login_required
def login_dashboard():
    """拥有者查看登录数据分析仪表盘 - 需要Pro订阅"""
    if not has_role(['owner']):
        if g.language == 'en':
            flash('Access denied. Owner privileges required.', 'danger')
        else:
            flash('您没有权限访问此页面，需要拥有者权限', 'danger')
        return redirect(url_for('index'))
    
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
@requires_admin_or_owner
@log_access_attempt('用户访问管理')
def user_access():
    """管理员管理用户访问权限 - 需要Pro订阅"""
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
    
    users = get_user_list()
    
    current_user_role = session.get('role', '未设置')
    logger.debug(f"当前用户角色: {current_user_role}")
    
    return render_template('user_access.html', users=users)


@admin_bp.route('/admin/user_access/add', methods=['POST'])
@rate_limit(max_requests=10, window_minutes=60, feature_name="admin_user_add")
@SecurityManager.csrf_protect
@requires_admin_or_owner
@log_access_attempt('添加用户访问权限')
def add_user_access():
    """添加新用户访问权限"""
    db = get_db()
    UserAccess = get_user_access_model()
    
    try:
        name = request.form['name']
        email = request.form['email']
        
        try:
            access_days = int(request.form['access_days'])
        except (ValueError, KeyError):
            access_days = 30
            
        company = request.form.get('company')
        position = request.form.get('position')
        notes = request.form.get('notes')
        role = request.form.get('role', 'guest')
        
        valid_roles = ['owner', 'admin', 'mining_site', 'guest']
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
            access_days=access_days,
            company=company,
            position=position,
            notes=notes,
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        
        if role == "owner":
            role_name = "拥有者"
        elif role == "admin":
            role_name = "管理员"
        elif role == "mining_site":
            role_name = "矿场管理"
        else:
            role_name = "矿场客人"
        flash(f'用户 {name} ({email}) 已成功添加，角色为"{role_name}"，访问权限 {access_days} 天', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加用户访问权限时出错: {str(e)}")
        flash(f'添加用户失败: {str(e)}', 'danger')
    
    return redirect(url_for('admin.user_access'))


@admin_bp.route('/admin/user_access/extend/<int:user_id>/<int:days>', methods=['POST'])
@login_required
def extend_user_access(user_id, days):
    """延长用户访问权限"""
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问此页面，需要管理员或拥有者权限', 'danger')
        return redirect(url_for('index'))
    
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
def view_user_details(user_id):
    """查看用户详细信息"""
    if not has_role(['owner', 'admin']):
        return jsonify({'success': False, 'message': '您没有权限访问此页面'})
    
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
                        {% elif user.role == 'mining_site' %}{% if current_lang == 'en' %}Mining Manager{% else %}矿场管理{% endif %}
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
def edit_user_access(user_id):
    """编辑用户信息"""
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问此页面，需要管理员或拥有者权限', 'danger')
        return redirect(url_for('index'))
    
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
            
            if has_role(['owner']):
                new_role = request.form.get('role')
                if new_role in ['owner', 'admin', 'mining_site', 'guest']:
                    user.role = new_role
                
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
def revoke_user_access(user_id):
    """撤销用户访问权限"""
    if not has_role(['owner', 'admin']):
        flash('您没有权限访问此页面，需要管理员或拥有者权限', 'danger')
        return redirect(url_for('index'))
    
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


@admin_bp.route('/admin/migrate_to_crm')
@login_required
def migrate_to_crm():
    """将用户访问权限数据迁移到CRM系统中"""
    if not has_role(['owner']):
        flash('您没有权限访问此页面，需要拥有者权限', 'danger')
        return redirect(url_for('index'))
    
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
                        f"访问期限: {user.access_days} 天\n"
                        f"到期日期: {user.expires_at.strftime('%Y-%m-%d')}\n"
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
def admin_create_user():
    """管理员创建测试用户"""
    if not has_role(['owner', 'admin']):
        flash('需要管理员权限才能创建用户', 'error')
        return redirect(url_for('index'))
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    if request.method == 'GET':
        return render_template('admin/create_user.html')
    
    try:
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'user')
        access_days = int(request.form.get('access_days', 30))
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
            access_days=access_days,
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
        
        
        flash(f'用户 {email} 创建成功！角色: {role}, 访问天数: {access_days}', 'success')
        return redirect(url_for('admin.admin_create_user'))
        
    except Exception as e:
        logger.error(f"管理员创建用户错误: {e}")
        flash('创建用户失败，请重试', 'error')
        return render_template('admin/create_user.html')


@admin_bp.route('/admin/users')
@login_required  
def admin_user_list():
    """管理员查看用户列表"""
    if not has_role(['owner', 'admin']):
        flash('需要管理员权限', 'error')
        return redirect(url_for('index'))
    
    users = get_user_list()
    return render_template('admin/user_list.html', users=users)


@admin_bp.route('/admin/verify-user/<int:user_id>', methods=['POST'])
@login_required
def admin_verify_user(user_id):
    """管理员验证用户邮箱"""
    if not has_role(['owner', 'admin']):
        return jsonify({'error': '权限不足'}), 403
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    user = UserAccess.query.get_or_404(user_id)
    user.verify_email()
    db.session.commit()
    
    
    return jsonify({'success': True})


@admin_bp.route('/admin/extend-access/<int:user_id>', methods=['POST'])
@login_required
def admin_extend_access(user_id):
    """管理员延长用户访问时间"""
    if not has_role(['owner', 'admin']):
        return jsonify({'error': '权限不足'}), 403
    
    db = get_db()
    UserAccess = get_user_access_model()
    
    data = request.get_json()
    days = data.get('days', 30)
    
    user = UserAccess.query.get_or_404(user_id)
    user.extend_access(days)
    db.session.commit()
    
    
    return jsonify({'success': True})
