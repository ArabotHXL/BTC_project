from datetime import datetime, timedelta
from db import db

class LoginRecord(db.Model):
    """记录用户登录信息的模型"""
    __tablename__ = 'login_records'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    successful = db.Column(db.Boolean, default=True, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    login_location = db.Column(db.String(512), nullable=True)
    
    def __repr__(self):
        """格式化模型的字符串表示"""
        status = "成功" if self.successful else "失败"
        return f"<LoginRecord {self.email} - {self.login_time} - {status}>"

class UserAccess(db.Model):
    """用户访问权限管理"""
    __tablename__ = 'user_access'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(256), nullable=False, unique=True)
    company = db.Column(db.String(200), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    access_days = db.Column(db.Integer, default=30, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, name, email, access_days=30, company=None, position=None, notes=None):
        self.name = name
        self.email = email
        self.company = company
        self.position = position
        self.access_days = access_days
        self.expires_at = datetime.utcnow() + timedelta(days=access_days)
        self.notes = notes
    
    @property
    def has_access(self):
        """检查用户是否有访问权限"""
        return datetime.utcnow() <= self.expires_at
    
    @property
    def access_status(self):
        """获取用户访问状态"""
        if self.has_access:
            return "授权访问"
        else:
            return "访问已过期"
    
    @property
    def days_remaining(self):
        """获取剩余访问天数"""
        if not self.has_access:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def extend_access(self, days):
        """延长访问期限"""
        if self.has_access:
            self.expires_at = self.expires_at + timedelta(days=days)
        else:
            self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.access_days += days
        
    def revoke_access(self):
        """撤销访问权限"""
        self.expires_at = datetime.utcnow() - timedelta(days=1)
        
    def __repr__(self):
        return f"<UserAccess {self.name} ({self.email}) - {self.access_status}>"