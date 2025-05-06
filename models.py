from datetime import datetime, timedelta
import json
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
    role = db.Column(db.String(20), default="guest", nullable=False)
    
    def __init__(self, name, email, access_days=30, company=None, position=None, notes=None, role="guest"):
        self.name = name
        self.email = email
        self.company = company
        self.position = position
        self.access_days = access_days
        self.expires_at = datetime.utcnow() + timedelta(days=access_days)
        self.notes = notes
        self.role = role
    
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


class CryptoAsset(db.Model):
    """加密货币资产模型"""
    __tablename__ = 'crypto_assets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(256), db.ForeignKey('user_access.email'), nullable=False)
    crypto_id = db.Column(db.String(50), nullable=False)  # 如 'bitcoin', 'ethereum'
    crypto_symbol = db.Column(db.String(20), nullable=False)  # 如 'BTC', 'ETH'
    crypto_name = db.Column(db.String(100), nullable=False)  # 如 'Bitcoin', 'Ethereum'
    amount = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=True)  # 购买时的价格（USD）
    purchase_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    # 存储历史价格数据的JSON字段
    price_history = db.Column(db.Text, nullable=True)  # 存储为JSON字符串
    
    # 与用户的关系
    user = db.relationship('UserAccess', backref=db.backref('crypto_assets', lazy=True))
    
    def __init__(self, user_email, crypto_id, crypto_symbol, crypto_name, amount, 
                 purchase_price=None, purchase_date=None, notes=None):
        self.user_email = user_email
        self.crypto_id = crypto_id
        self.crypto_symbol = crypto_symbol
        self.crypto_name = crypto_name
        self.amount = amount
        self.purchase_price = purchase_price
        self.purchase_date = purchase_date
        self.notes = notes
    
    def set_price_history(self, price_data):
        """设置价格历史数据"""
        if isinstance(price_data, dict):
            self.price_history = json.dumps(price_data)
        else:
            self.price_history = price_data
            
    def get_price_history(self):
        """获取价格历史数据"""
        if not self.price_history:
            return {}
        try:
            return json.loads(self.price_history)
        except:
            return {}
    
    def __repr__(self):
        return f"<CryptoAsset {self.crypto_symbol} ({self.amount}) - {self.user_email}>"


class Portfolio(db.Model):
    """加密货币投资组合模型，记录用户的组合设置和历史表现"""
    __tablename__ = 'portfolios'
    
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(256), db.ForeignKey('user_access.email'), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False, default="主投资组合")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 存储历史表现数据（每日总资产价值）
    performance_history = db.Column(db.Text, nullable=True)  # 存储为JSON字符串
    # 存储风险评估数据
    risk_metrics = db.Column(db.Text, nullable=True)  # 存储为JSON字符串
    # 优化建议
    optimization_suggestions = db.Column(db.Text, nullable=True)  # 存储为JSON字符串
    
    # 与用户的关系
    user = db.relationship('UserAccess', backref=db.backref('portfolio', uselist=False, lazy=True))
    
    def __init__(self, user_email, name="主投资组合"):
        self.user_email = user_email
        self.name = name
    
    def set_performance_history(self, history_data):
        """设置表现历史数据"""
        if isinstance(history_data, dict):
            self.performance_history = json.dumps(history_data)
        else:
            self.performance_history = history_data
            
    def get_performance_history(self):
        """获取表现历史数据"""
        if not self.performance_history:
            return {}
        try:
            return json.loads(self.performance_history)
        except:
            return {}
    
    def set_risk_metrics(self, metrics_data):
        """设置风险评估数据"""
        if isinstance(metrics_data, dict):
            self.risk_metrics = json.dumps(metrics_data)
        else:
            self.risk_metrics = metrics_data
            
    def get_risk_metrics(self):
        """获取风险评估数据"""
        if not self.risk_metrics:
            return {}
        try:
            return json.loads(self.risk_metrics)
        except:
            return {}
    
    def set_optimization_suggestions(self, suggestions_data):
        """设置优化建议"""
        if isinstance(suggestions_data, dict) or isinstance(suggestions_data, list):
            self.optimization_suggestions = json.dumps(suggestions_data)
        else:
            self.optimization_suggestions = suggestions_data
            
    def get_optimization_suggestions(self):
        """获取优化建议"""
        if not self.optimization_suggestions:
            return []
        try:
            return json.loads(self.optimization_suggestions)
        except:
            return []
    
    def __repr__(self):
        return f"<Portfolio {self.name} - {self.user_email}>"