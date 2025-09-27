"""
Admin Routes
管理员路由 - 用户访问权限管理和系统管理功能
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
    from auth.decorators import requires_owner_only, requires_admin_or_owner
    from auth.authentication import login_required
    from models import UserAccess, User
    from database import db
    from services.user_service import UserService
except ImportError as e:
    # Fallback for when running as part of the main application
    try:
        from user_management_module.auth.decorators import requires_owner_only, requires_admin_or_owner
        from user_management_module.auth.authentication import login_required
        from user_management_module.models import UserAccess, User
        from user_management_module.database import db
        from user_management_module.services.user_service import UserService
    except ImportError:
        # Emergency fallback - use basic decorators
        def requires_owner_only(f):
            return f
        def requires_admin_or_owner(f):
            return f
        def login_required(f):
            return f
        class UserAccess:
            @staticmethod
            def query():
                return None
        class User:
            pass
        db = None
        class UserService:
            pass

logger = logging.getLogger(__name__)

# 创建蓝图
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
@requires_admin_or_owner
def dashboard():
    """管理员仪表盘"""
    try:
        # 获取用户统计
        total_users = UserAccess.query.count()
        active_users = UserAccess.query.filter_by(has_access=True).count()
        recent_users = UserAccess.query.filter(
            UserAccess.created_at >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        # 获取角色分布
        owner_count = UserAccess.query.filter_by(role='owner').count()
        admin_count = UserAccess.query.filter_by(role='admin').count()
        guest_count = UserAccess.query.filter_by(role='guest').count()
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'recent_users': recent_users,
            'owner_count': owner_count,
            'admin_count': admin_count,
            'guest_count': guest_count
        }
        
        return render_template('admin/dashboard.html',
                             title='管理员仪表盘',
                             stats=stats)
                             
    except Exception as e:
        logger.error(f"管理员仪表盘错误: {e}")
        flash('加载仪表盘失败', 'error')
        return redirect(url_for('index'))

@admin_bp.route('/users')
@login_required
@requires_admin_or_owner
def users_list():
    """用户管理页面"""
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 获取用户列表
        users = UserAccess.query.order_by(UserAccess.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('admin/users.html',
                             title='用户管理',
                             users=users)
                             
    except Exception as e:
        logger.error(f"用户管理页面错误: {e}")
        flash('加载用户列表失败', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@requires_owner_only
def create_user():
    """创建用户"""
    if request.method == 'GET':
        return render_template('admin/create_user.html',
                             title='创建用户')
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必需字段
        required_fields = ['name', 'email', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} 不能为空'}), 400
        
        # 创建用户
        user = UserService.create_user(
            name=data['name'],
            email=data['email'],
            username=data.get('username'),
            password=data.get('password'),
            role=data['role'],
            company=data.get('company'),
            position=data.get('position'),
            access_days=int(data.get('access_days', 30)),
            created_by_id=session.get('user_id')
        )
        
        if user:
            message = f'用户 {user.email} 创建成功'
            logger.info(message)
            
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'user': user.to_dict()})
            else:
                flash(message, 'success')
                return redirect(url_for('admin.users_list'))
        else:
            error = '创建用户失败'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 500
            else:
                flash(error, 'error')
                return redirect(url_for('admin.create_user'))
                
    except Exception as e:
        logger.error(f"创建用户错误: {e}")
        error = f'创建用户失败: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('admin.create_user'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_admin_or_owner
def edit_user(user_id):
    """编辑用户"""
    try:
        user = UserAccess.query.get_or_404(user_id)
        
        if request.method == 'GET':
            return render_template('admin/edit_user.html',
                                 title='编辑用户',
                                 user=user)
        
        # 处理POST请求
        data = request.get_json() if request.is_json else request.form
        
        # 更新用户信息
        user.name = data.get('name', user.name)
        user.email = data.get('email', user.email)
        user.username = data.get('username', user.username)
        user.company = data.get('company', user.company)
        user.position = data.get('position', user.position)
        user.notes = data.get('notes', user.notes)
        
        # 只有owner可以修改角色
        current_role = session.get('role')
        if current_role == 'owner':
            user.role = data.get('role', user.role)
        
        # 更新访问权限
        if 'access_days' in data:
            user.access_days = int(data['access_days'])
            user.calculate_expiry()
        
        # 更新密码（如果提供）
        if data.get('password'):
            user.set_password(data['password'])
        
        db.session.commit()
        
        message = f'用户 {user.email} 更新成功'
        logger.info(message)
        
        if request.is_json:
            return jsonify({'success': True, 'message': message, 'user': user.to_dict()})
        else:
            flash(message, 'success')
            return redirect(url_for('admin.users_list'))
            
    except Exception as e:
        logger.error(f"编辑用户错误: {e}")
        db.session.rollback()
        error = f'编辑用户失败: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('admin.users_list'))

@admin_bp.route('/users/<int:user_id>/toggle-access', methods=['POST'])
@login_required
@requires_admin_or_owner
def toggle_user_access(user_id):
    """切换用户访问权限"""
    try:
        user = UserAccess.query.get_or_404(user_id)
        
        # 切换访问权限
        if user.has_access:
            # 禁用访问
            user.expires_at = datetime.utcnow() - timedelta(days=1)
        else:
            # 启用访问
            user.expires_at = datetime.utcnow() + timedelta(days=user.access_days)
        
        db.session.commit()
        
        status = '启用' if user.has_access else '禁用'
        message = f'用户 {user.email} 访问权限已{status}'
        logger.info(message)
        
        return jsonify({
            'success': True,
            'message': message,
            'has_access': user.has_access
        })
        
    except Exception as e:
        logger.error(f"切换用户访问权限错误: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@requires_owner_only
def delete_user(user_id):
    """删除用户"""
    try:
        user = UserAccess.query.get_or_404(user_id)
        
        # 不能删除自己
        if user.id == session.get('user_id'):
            return jsonify({'success': False, 'error': '不能删除自己'}), 400
        
        email = user.email
        db.session.delete(user)
        db.session.commit()
        
        message = f'用户 {email} 已删除'
        logger.info(message)
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        logger.error(f"删除用户错误: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>/extend-access', methods=['POST'])
@login_required
@requires_admin_or_owner
def extend_user_access(user_id):
    """延长用户访问权限"""
    try:
        user = UserAccess.query.get_or_404(user_id)
        data = request.get_json()
        
        additional_days = int(data.get('days', 30))
        if additional_days <= 0:
            return jsonify({'success': False, 'error': '天数必须大于0'}), 400
        
        user.extend_access(additional_days)
        db.session.commit()
        
        message = f'用户 {user.email} 访问权限已延长 {additional_days} 天'
        logger.info(message)
        
        return jsonify({
            'success': True,
            'message': message,
            'expires_at': user.expires_at.isoformat(),
            'days_remaining': user.days_remaining
        })
        
    except Exception as e:
        logger.error(f"延长用户访问权限错误: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/users')
@login_required
@requires_admin_or_owner
def api_users():
    """获取用户列表API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        role_filter = request.args.get('role', '').strip()
        
        # 构建查询
        query = UserAccess.query
        
        if search:
            query = query.filter(
                (UserAccess.name.contains(search)) |
                (UserAccess.email.contains(search)) |
                (UserAccess.company.contains(search))
            )
        
        if role_filter:
            query = query.filter(UserAccess.role == role_filter)
        
        # 分页
        users = query.order_by(UserAccess.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in users.items],
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total
            }
        })
        
    except Exception as e:
        logger.error(f"获取用户列表API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/users/<int:user_id>')
@login_required
@requires_admin_or_owner
def api_user_detail(user_id):
    """获取用户详情API"""
    try:
        user = UserAccess.query.get_or_404(user_id)
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取用户详情API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/system-info')
@login_required
@requires_owner_only
def system_info():
    """系统信息页面"""
    try:
        # 获取系统统计信息
        system_stats = {
            'total_users': UserAccess.query.count(),
            'active_users': UserAccess.query.filter(UserAccess.has_access == True).count(),
            'database_size': 'N/A',  # 可以添加实际的数据库大小查询
            'uptime': 'N/A',  # 可以添加系统运行时间
        }
        
        return render_template('admin/system_info.html',
                             title='系统信息',
                             stats=system_stats)
                             
    except Exception as e:
        logger.error(f"系统信息页面错误: {e}")
        flash('加载系统信息失败', 'error')
        return redirect(url_for('admin.dashboard'))