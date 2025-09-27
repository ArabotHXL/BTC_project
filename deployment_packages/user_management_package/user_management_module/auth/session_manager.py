"""
Session Management Module
会话管理模块 - 用户会话管理和状态维护
"""

import logging
from datetime import datetime, timedelta
from flask import session, request
import json

logger = logging.getLogger(__name__)

class SessionManager:
    """会话管理器"""
    
    @staticmethod
    def create_user_session(user, remember_me=False):
        """创建用户会话"""
        try:
            # 设置基本会话信息
            session['authenticated'] = True
            session['user_id'] = user.id
            session['email'] = user.email
            session['username'] = user.username
            session['name'] = user.name
            session['role'] = user.role
            session['company'] = user.company
            session['subscription_plan'] = user.subscription_plan
            
            # 设置登录时间
            session['login_time'] = datetime.utcnow().isoformat()
            
            # 设置会话过期时间
            if remember_me:
                session.permanent = True
                session['remember_me'] = True
            else:
                session.permanent = False
                session['remember_me'] = False
            
            # 记录用户代理和IP
            session['user_agent'] = request.headers.get('User-Agent', '')
            session['ip_address'] = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            # 设置语言偏好
            session['language'] = session.get('language', 'zh')
            
            logger.info(f"用户 {user.email} 会话创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建用户会话失败: {e}")
            return False
    
    @staticmethod
    def update_user_session(user):
        """更新用户会话信息"""
        try:
            if session.get('authenticated') and session.get('user_id') == user.id:
                # 更新可能变化的信息
                session['role'] = user.role
                session['subscription_plan'] = user.subscription_plan
                session['company'] = user.company
                session['name'] = user.name
                
                logger.debug(f"用户 {user.email} 会话信息已更新")
                return True
            return False
            
        except Exception as e:
            logger.error(f"更新用户会话失败: {e}")
            return False
    
    @staticmethod
    def destroy_user_session():
        """销毁用户会话"""
        try:
            user_email = session.get('email')
            
            # 记录登出信息
            SessionManager._record_logout()
            
            # 清除所有会话数据
            session.clear()
            
            logger.info(f"用户 {user_email} 会话已销毁")
            return True
            
        except Exception as e:
            logger.error(f"销毁用户会话失败: {e}")
            return False
    
    @staticmethod
    def is_session_valid():
        """检查会话是否有效"""
        try:
            # 检查基本会话状态
            if not session.get('authenticated'):
                return False
            
            # 检查必要的会话字段
            required_fields = ['user_id', 'email', 'role']
            for field in required_fields:
                if not session.get(field):
                    logger.warning(f"会话验证失败: 缺少字段 {field}")
                    return False
            
            # 检查会话过期时间
            login_time_str = session.get('login_time')
            if login_time_str:
                try:
                    login_time = datetime.fromisoformat(login_time_str)
                    
                    # 非永久会话的过期时间检查（24小时）
                    if not session.get('remember_me'):
                        if datetime.utcnow() - login_time > timedelta(hours=24):
                            logger.warning(f"用户 {session.get('email')} 会话已过期")
                            return False
                    else:
                        # 记住我会话的过期时间检查（30天）
                        if datetime.utcnow() - login_time > timedelta(days=30):
                            logger.warning(f"用户 {session.get('email')} 记住我会话已过期")
                            return False
                            
                except ValueError:
                    logger.warning("会话时间格式无效")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"会话有效性检查失败: {e}")
            return False
    
    @staticmethod
    def refresh_session():
        """刷新会话活动时间"""
        try:
            if session.get('authenticated'):
                session['last_activity'] = datetime.utcnow().isoformat()
                return True
            return False
            
        except Exception as e:
            logger.error(f"刷新会话失败: {e}")
            return False
    
    @staticmethod
    def get_session_info():
        """获取会话信息"""
        try:
            if not session.get('authenticated'):
                return None
            
            return {
                'user_id': session.get('user_id'),
                'email': session.get('email'),
                'username': session.get('username'),
                'name': session.get('name'),
                'role': session.get('role'),
                'company': session.get('company'),
                'subscription_plan': session.get('subscription_plan'),
                'login_time': session.get('login_time'),
                'last_activity': session.get('last_activity'),
                'remember_me': session.get('remember_me', False),
                'language': session.get('language', 'zh'),
                'ip_address': session.get('ip_address'),
                'user_agent': session.get('user_agent')
            }
            
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            return None
    
    @staticmethod
    def set_language(language):
        """设置语言偏好"""
        try:
            if language in ['zh', 'en']:
                session['language'] = language
                logger.debug(f"语言设置为: {language}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"设置语言失败: {e}")
            return False
    
    @staticmethod
    def _record_logout():
        """记录登出信息"""
        try:
            if session.get('authenticated'):
                from ..models import LoginRecord
                from ..database import db
                
                login_record = LoginRecord.query.filter_by(
                    user_id=session.get('user_id'),
                    logout_time=None
                ).order_by(LoginRecord.login_time.desc()).first()
                
                if login_record:
                    login_record.logout_time = datetime.utcnow()
                    login_record.session_duration = (
                        login_record.logout_time - login_record.login_time
                    ).total_seconds()
                    db.session.commit()
                    
        except Exception as e:
            logger.error(f"记录登出信息失败: {e}")
    
    @staticmethod
    def cleanup_expired_sessions():
        """清理过期会话（通常在后台任务中调用）"""
        try:
            # 这个方法在实际应用中可能需要配合Redis或其他会话存储来实现
            # 目前只是一个占位符方法
            logger.info("会话清理任务执行完成")
            return True
            
        except Exception as e:
            logger.error(f"会话清理失败: {e}")
            return False
    
    @staticmethod
    def check_security_constraints():
        """检查安全约束"""
        try:
            if not session.get('authenticated'):
                return True  # 未登录用户无需检查
            
            # 检查IP地址是否发生变化（可选的安全检查）
            current_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            session_ip = session.get('ip_address')
            
            if session_ip and current_ip != session_ip:
                logger.warning(f"用户 {session.get('email')} IP地址发生变化: {session_ip} -> {current_ip}")
                # 这里可以选择是否要求重新登录
                # 目前只记录警告，不强制退出
            
            # 检查用户代理是否发生变化
            current_user_agent = request.headers.get('User-Agent', '')
            session_user_agent = session.get('user_agent', '')
            
            if session_user_agent and current_user_agent != session_user_agent:
                logger.warning(f"用户 {session.get('email')} 用户代理发生变化")
                # 同样只记录警告
            
            return True
            
        except Exception as e:
            logger.error(f"安全约束检查失败: {e}")
            return False
    
    @staticmethod
    def get_active_sessions_count(user_id):
        """获取用户活跃会话数量（需要配合Redis实现）"""
        try:
            # 这个方法需要配合Redis或其他会话存储来实现
            # 目前返回固定值
            return 1
            
        except Exception as e:
            logger.error(f"获取活跃会话数量失败: {e}")
            return 0

# 会话中间件
def session_middleware():
    """会话中间件"""
    # 在每次请求前检查会话有效性
    if session.get('authenticated'):
        if not SessionManager.is_session_valid():
            SessionManager.destroy_user_session()
        else:
            SessionManager.refresh_session()
            SessionManager.check_security_constraints()