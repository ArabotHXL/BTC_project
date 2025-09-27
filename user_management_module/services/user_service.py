"""
User Service
用户服务 - 用户管理相关的业务逻辑
"""

import logging
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
try:
    from ..models import UserAccess, User, LoginRecord
    from ..database import db
    from ..auth.authentication import create_user, update_user_access
except ImportError:
    from models import UserAccess, User, LoginRecord
    from database import db
    from auth.authentication import create_user, update_user_access

logger = logging.getLogger(__name__)

class UserService:
    """用户服务类"""
    
    @staticmethod
    def create_user(name, email, username=None, password=None, role='guest', 
                   company=None, position=None, access_days=30, created_by_id=None):
        """创建新用户"""
        try:
            # 检查邮箱是否已存在
            existing_user = UserAccess.query.filter_by(email=email.lower().strip()).first()
            if existing_user:
                logger.warning(f"创建用户失败: 邮箱 {email} 已存在")
                return None
            
            # 检查用户名是否已存在
            if username:
                existing_username = UserAccess.query.filter_by(username=username.lower().strip()).first()
                if existing_username:
                    logger.warning(f"创建用户失败: 用户名 {username} 已存在")
                    return None
            
            # 创建用户
            user = UserAccess(
                name=name,
                email=email.lower().strip(),
                username=username.lower().strip() if username else None,
                company=company,
                position=position,
                role=role,
                access_days=access_days,
                notes=f"用户创建于 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                created_by_id=created_by_id
            )
            
            # 设置密码
            if password:
                user.set_password(password)
            
            # 自动验证邮箱（管理员创建的用户）
            user.verify_email()
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"成功创建用户: {email} (角色: {role})")
            return user
            
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """更新用户信息"""
        try:
            user = UserAccess.query.get(user_id)
            if not user:
                logger.warning(f"更新用户失败: 用户ID {user_id} 不存在")
                return None
            
            # 更新可修改的字段
            updatable_fields = [
                'name', 'email', 'username', 'company', 'position', 
                'role', 'access_days', 'notes', 'subscription_plan'
            ]
            
            for field, value in kwargs.items():
                if field in updatable_fields and hasattr(user, field):
                    if field == 'email' and value:
                        value = value.lower().strip()
                    elif field == 'username' and value:
                        value = value.lower().strip()
                    
                    setattr(user, field, value)
            
            # 如果修改了access_days，重新计算过期时间
            if 'access_days' in kwargs:
                user.calculate_expiry()
            
            # 如果提供了新密码，更新密码
            if 'password' in kwargs and kwargs['password']:
                user.set_password(kwargs['password'])
            
            db.session.commit()
            
            logger.info(f"成功更新用户: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"更新用户失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def delete_user(user_id):
        """删除用户"""
        try:
            user = UserAccess.query.get(user_id)
            if not user:
                logger.warning(f"删除用户失败: 用户ID {user_id} 不存在")
                return False
            
            email = user.email
            db.session.delete(user)
            db.session.commit()
            
            logger.info(f"成功删除用户: {email}")
            return True
            
        except Exception as e:
            logger.error(f"删除用户失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_user_by_id(user_id):
        """根据ID获取用户"""
        try:
            return UserAccess.query.get(user_id)
        except Exception as e:
            logger.error(f"获取用户失败: {str(e)}")
            return None
    
    @staticmethod
    def get_user_by_email(email):
        """根据邮箱获取用户"""
        try:
            return UserAccess.query.filter_by(email=email.lower().strip()).first()
        except Exception as e:
            logger.error(f"根据邮箱获取用户失败: {str(e)}")
            return None
    
    @staticmethod
    def get_users_by_role(role, page=1, per_page=20):
        """根据角色获取用户列表"""
        try:
            return UserAccess.query.filter_by(role=role).paginate(
                page=page, per_page=per_page, error_out=False
            )
        except Exception as e:
            logger.error(f"根据角色获取用户列表失败: {str(e)}")
            return None
    
    @staticmethod
    def search_users(search_term, page=1, per_page=20):
        """搜索用户"""
        try:
            search_pattern = f"%{search_term}%"
            return UserAccess.query.filter(
                (UserAccess.name.like(search_pattern)) |
                (UserAccess.email.like(search_pattern)) |
                (UserAccess.company.like(search_pattern))
            ).paginate(page=page, per_page=per_page, error_out=False)
        except Exception as e:
            logger.error(f"搜索用户失败: {str(e)}")
            return None
    
    @staticmethod
    def extend_user_access(user_id, additional_days):
        """延长用户访问权限"""
        try:
            user = UserAccess.query.get(user_id)
            if not user:
                logger.warning(f"延长访问权限失败: 用户ID {user_id} 不存在")
                return False
            
            user.extend_access(additional_days)
            db.session.commit()
            
            logger.info(f"成功延长用户 {user.email} 访问权限 {additional_days} 天")
            return True
            
        except Exception as e:
            logger.error(f"延长用户访问权限失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def toggle_user_access(user_id):
        """切换用户访问权限"""
        try:
            user = UserAccess.query.get(user_id)
            if not user:
                logger.warning(f"切换访问权限失败: 用户ID {user_id} 不存在")
                return False
            
            if user.has_access:
                # 禁用访问
                user.expires_at = datetime.utcnow() - timedelta(days=1)
            else:
                # 启用访问
                user.expires_at = datetime.utcnow() + timedelta(days=user.access_days)
            
            db.session.commit()
            
            status = '启用' if user.has_access else '禁用'
            logger.info(f"成功{status}用户 {user.email} 访问权限")
            return True
            
        except Exception as e:
            logger.error(f"切换用户访问权限失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def verify_user_email(user_id):
        """验证用户邮箱"""
        try:
            user = UserAccess.query.get(user_id)
            if not user:
                logger.warning(f"验证邮箱失败: 用户ID {user_id} 不存在")
                return False
            
            user.verify_email()
            db.session.commit()
            
            logger.info(f"成功验证用户 {user.email} 邮箱")
            return True
            
        except Exception as e:
            logger.error(f"验证用户邮箱失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def record_login(user_id, ip_address=None, user_agent=None, login_method='password'):
        """记录用户登录"""
        try:
            login_record = LoginRecord(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                login_method=login_method
            )
            
            db.session.add(login_record)
            db.session.commit()
            
            logger.debug(f"记录用户 {user_id} 登录")
            return login_record
            
        except Exception as e:
            logger.error(f"记录用户登录失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_user_login_history(user_id, page=1, per_page=20):
        """获取用户登录历史"""
        try:
            return LoginRecord.query.filter_by(user_id=user_id).order_by(
                LoginRecord.login_time.desc()
            ).paginate(page=page, per_page=per_page, error_out=False)
        except Exception as e:
            logger.error(f"获取用户登录历史失败: {str(e)}")
            return None
    
    @staticmethod
    def get_user_stats():
        """获取用户统计信息"""
        try:
            total_users = UserAccess.query.count()
            active_users = UserAccess.query.filter(UserAccess.has_access == True).count()
            recent_users = UserAccess.query.filter(
                UserAccess.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
            
            # 角色分布
            role_stats = {}
            roles = ['owner', 'admin', 'guest']
            for role in roles:
                count = UserAccess.query.filter_by(role=role).count()
                role_stats[role] = count
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'recent_users': recent_users,
                'role_stats': role_stats
            }
            
        except Exception as e:
            logger.error(f"获取用户统计信息失败: {str(e)}")
            return None
    
    @staticmethod
    def change_user_password(user_id, new_password):
        """修改用户密码"""
        try:
            user = UserAccess.query.get(user_id)
            if not user:
                logger.warning(f"修改密码失败: 用户ID {user_id} 不存在")
                return False
            
            user.set_password(new_password)
            db.session.commit()
            
            logger.info(f"成功修改用户 {user.email} 密码")
            return True
            
        except Exception as e:
            logger.error(f"修改用户密码失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def bulk_update_users(user_ids, update_data):
        """批量更新用户"""
        try:
            updated_count = 0
            
            for user_id in user_ids:
                user = UserAccess.query.get(user_id)
                if user:
                    for field, value in update_data.items():
                        if hasattr(user, field):
                            setattr(user, field, value)
                    updated_count += 1
            
            db.session.commit()
            
            logger.info(f"批量更新了 {updated_count} 个用户")
            return updated_count
            
        except Exception as e:
            logger.error(f"批量更新用户失败: {str(e)}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_expiring_users(days_threshold=7):
        """获取即将过期的用户"""
        try:
            threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
            
            return UserAccess.query.filter(
                UserAccess.expires_at <= threshold_date,
                UserAccess.expires_at > datetime.utcnow()
            ).all()
            
        except Exception as e:
            logger.error(f"获取即将过期用户失败: {str(e)}")
            return []