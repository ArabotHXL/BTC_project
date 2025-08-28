"""
计算器模块数据模型
定义计算器特定的数据结构
"""
from datetime import datetime
from app import db

class CalculatorSession(db.Model):
    """计算器会话记录"""
    __tablename__ = 'calculator_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=False)
    
    # 计算参数
    miner_model = db.Column(db.String(100))
    hashrate = db.Column(db.Float)
    power_consumption = db.Column(db.Float)
    electricity_cost = db.Column(db.Float)
    miner_count = db.Column(db.Integer, default=1)
    
    # 计算结果
    daily_btc = db.Column(db.Float)
    daily_revenue = db.Column(db.Float)
    daily_cost = db.Column(db.Float)
    daily_profit = db.Column(db.Float)
    roi_days = db.Column(db.Integer)
    
    # 网络状态快照
    btc_price = db.Column(db.Float)
    network_hashrate = db.Column(db.Float)
    network_difficulty = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'miner_model': self.miner_model,
            'hashrate': self.hashrate,
            'electricity_cost': self.electricity_cost,
            'daily_profit': self.daily_profit,
            'roi_days': self.roi_days,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CalculatorPreset(db.Model):
    """用户保存的计算器预设"""
    __tablename__ = 'calculator_presets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    preset_name = db.Column(db.String(100), nullable=False)
    
    # 预设参数
    miners = db.Column(db.JSON)  # 矿机配置列表
    electricity_cost = db.Column(db.Float)
    pool_fee = db.Column(db.Float, default=2.5)
    
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'preset_name': self.preset_name,
            'miners': self.miners,
            'electricity_cost': self.electricity_cost,
            'pool_fee': self.pool_fee,
            'is_default': self.is_default
        }