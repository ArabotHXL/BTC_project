"""
User Routes
用户路由 - 用户自服务和个人资料管理
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime
import logging
try:
    from ..auth.authentication import login_required, get_current_user, verify_password_login
    from ..auth.decorators import requires_role
    from ..models import UserAccess, User, LoginRecord
    from ..database import db
    from ..services.user_service import UserService
except ImportError:
    from auth.authentication import login_required, get_current_user, verify_password_login
    from auth.decorators import requires_role
    from models import UserAccess, User, LoginRecord
    from database import db
    from services.user_service import UserService

logger = logging.getLogger(__name__)

# 创建蓝图
users_bp = Blueprint('users', __name__)

@users_bp.route('/profile')
@login_required
def profile():
    """用户个人资料页面"""
    try:
        user = get_current_user()
        if not user:
            flash('用户信息不存在', 'error')
            return redirect(url_for('auth.login'))
        
        return render_template('users/profile.html',
                             title='个人资料',
                             user=user)
                             
    except Exception as e:
        logger.error(f"个人资料页面错误: {e}")
        flash('加载个人资料失败', 'error')
        return redirect(url_for('index'))

@users_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """编辑个人资料"""
    try:
        user = get_current_user()
        if not user:
            flash('用户信息不存在', 'error')
            return redirect(url_for('auth.login'))
        
        if request.method == 'GET':
            return render_template('users/edit_profile.html',
                                 title='编辑个人资料',
                                 user=user)
        
        # 处理POST请求
        data = request.get_json() if request.is_json else request.form
        
        # 更新用户信息
        user.name = data.get('name', user.name)
        user.company = data.get('company', user.company)
        user.position = data.get('position', user.position)
        
        # 更新用户名（如果提供且不重复）
        new_username = data.get('username', '').strip()
        if new_username and new_username != user.username:
            existing_user = UserAccess.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != user.id:
                error = '用户名已存在'
                if request.is_json:
                    return jsonify({'success': False, 'error': error}), 400
                else:
                    flash(error, 'error')
                    return redirect(url_for('users.edit_profile'))
            user.username = new_username
        
        db.session.commit()
        
        message = '个人资料更新成功'
        logger.info(f"用户 {user.email} 更新了个人资料")
        
        if request.is_json:
            return jsonify({'success': True, 'message': message, 'user': user.to_dict()})
        else:
            flash(message, 'success')
            return redirect(url_for('users.profile'))
            
    except Exception as e:
        logger.error(f"编辑个人资料错误: {e}")
        db.session.rollback()
        error = f'更新个人资料失败: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('users.edit_profile'))

@users_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    try:
        user = get_current_user()
        if not user:
            flash('用户信息不存在', 'error')
            return redirect(url_for('auth.login'))
        
        if request.method == 'GET':
            return render_template('users/change_password.html',
                                 title='修改密码')
        
        # 处理POST请求
        data = request.get_json() if request.is_json else request.form
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        # 验证必需字段
        if not all([current_password, new_password, confirm_password]):
            error = '所有字段都不能为空'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('users.change_password'))
        
        # 验证当前密码
        if not user.check_password(current_password):
            error = '当前密码错误'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('users.change_password'))
        
        # 验证新密码
        if new_password != confirm_password:
            error = '新密码和确认密码不匹配'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('users.change_password'))
        
        if len(new_password) < 6:
            error = '新密码长度至少6位'
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 400
            else:
                flash(error, 'error')
                return redirect(url_for('users.change_password'))
        
        # 更新密码
        user.set_password(new_password)
        db.session.commit()
        
        message = '密码修改成功'
        logger.info(f"用户 {user.email} 修改了密码")
        
        if request.is_json:
            return jsonify({'success': True, 'message': message})
        else:
            flash(message, 'success')
            return redirect(url_for('users.profile'))
            
    except Exception as e:
        logger.error(f"修改密码错误: {e}")
        db.session.rollback()
        error = f'修改密码失败: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        else:
            flash(error, 'error')
            return redirect(url_for('users.change_password'))

@users_bp.route('/login-history')
@login_required
def login_history():
    """登录历史"""
    try:
        user = get_current_user()
        if not user:
            flash('用户信息不存在', 'error')
            return redirect(url_for('auth.login'))
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # 查询登录记录
        login_records = LoginRecord.query.filter_by(user_id=user.id).order_by(
            LoginRecord.login_time.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('users/login_history.html',
                             title='登录历史',
                             login_records=login_records)
                             
    except Exception as e:
        logger.error(f"登录历史页面错误: {e}")
        flash('加载登录历史失败', 'error')
        return redirect(url_for('users.profile'))

@users_bp.route('/api/profile')
@login_required
def api_profile():
    """获取用户资料API"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取用户资料API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@users_bp.route('/api/subscription-info')
@login_required
def api_subscription_info():
    """获取用户订阅信息API"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        subscription_info = {
            'subscription_plan': user.subscription_plan,
            'access_days': user.access_days,
            'days_remaining': user.days_remaining,
            'expires_at': user.expires_at.isoformat() if user.expires_at else None,
            'has_access': user.has_access,
            'access_status': user.access_status
        }
        
        return jsonify({
            'success': True,
            'data': subscription_info
        })
        
    except Exception as e:
        logger.error(f"获取订阅信息API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@users_bp.route('/api/login-records')
@login_required
def api_login_records():
    """获取登录记录API"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        login_records = LoginRecord.query.filter_by(user_id=user.id).order_by(
            LoginRecord.login_time.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': [record.to_dict() for record in login_records.items],
            'pagination': {
                'page': login_records.page,
                'pages': login_records.pages,
                'per_page': login_records.per_page,
                'total': login_records.total
            }
        })
        
    except Exception as e:
        logger.error(f"获取登录记录API错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@users_bp.route('/settings')
@login_required
def settings():
    """用户设置页面"""
    try:
        user = get_current_user()
        if not user:
            flash('用户信息不存在', 'error')
            return redirect(url_for('auth.login'))
        
        return render_template('users/settings.html',
                             title='用户设置',
                             user=user)
                             
    except Exception as e:
        logger.error(f"用户设置页面错误: {e}")
        flash('加载用户设置失败', 'error')
        return redirect(url_for('users.profile'))

@users_bp.route('/verify-email')
@login_required
def verify_email():
    """邮箱验证页面"""
    try:
        user = get_current_user()
        if not user:
            flash('用户信息不存在', 'error')
            return redirect(url_for('auth.login'))
        
        if user.is_email_verified:
            flash('邮箱已验证', 'info')
            return redirect(url_for('users.profile'))
        
        return render_template('users/verify_email.html',
                             title='邮箱验证',
                             user=user)
                             
    except Exception as e:
        logger.error(f"邮箱验证页面错误: {e}")
        flash('加载邮箱验证页面失败', 'error')
        return redirect(url_for('users.profile'))

@users_bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification():
    """重新发送验证邮件"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        if user.is_email_verified:
            return jsonify({'success': False, 'error': '邮箱已验证'}), 400
        
        # 生成新的验证令牌
        token = user.generate_email_verification_token()
        db.session.commit()
        
        # 这里可以添加发送邮件的逻辑
        logger.info(f"用户 {user.email} 请求重新发送验证邮件，令牌: {token}")
        
        return jsonify({
            'success': True,
            'message': '验证邮件已发送，请检查您的邮箱'
        })
        
    except Exception as e:
        logger.error(f"重新发送验证邮件错误: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@users_bp.route('/dashboard')
@login_required
def dashboard():
    """用户仪表盘"""
    try:
        user = get_current_user()
        if not user:
            flash('用户信息不存在', 'error')
            return redirect(url_for('auth.login'))
        
        # 获取用户统计信息
        total_logins = LoginRecord.query.filter_by(user_id=user.id).count()
        recent_logins = LoginRecord.query.filter_by(user_id=user.id).filter(
            LoginRecord.login_time >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        stats = {
            'total_logins': total_logins,
            'recent_logins': recent_logins,
            'subscription_plan': user.subscription_plan,
            'days_remaining': user.days_remaining,
            'access_status': user.access_status
        }
        
        return render_template('users/dashboard.html',
                             title='用户仪表盘',
                             user=user,
                             stats=stats)
                             
    except Exception as e:
        logger.error(f"用户仪表盘错误: {e}")
        flash('加载用户仪表盘失败', 'error')
        return redirect(url_for('index'))