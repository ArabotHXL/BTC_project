
"""
托管功能数据模型
定义托管站点、设备、SLA等相关数据结构
"""
from datetime import datetime
from db import db
import enum

class HostingSiteStatus(enum.Enum):
    """托管站点状态"""
    ONLINE = "在线"
    OFFLINE = "离线"
    MAINTENANCE = "维护中"
    EMERGENCY = "紧急状态"

class DeviceStatus(enum.Enum):
    """设备状态"""
    RUNNING = "运行中"
    STOPPED = "已停止"
    ERROR = "故障"
    MAINTENANCE = "维护中"

class HostingSite(db.Model):
    """托管站点信息"""
    __tablename__ = 'hosting_sites'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(500), nullable=False)
    capacity_mw = db.Column(db.Float, nullable=False)  # 总容量(MW)
    used_capacity_mw = db.Column(db.Float, default=0.0)  # 已用容量(MW)
    electricity_rate = db.Column(db.Float, nullable=False)  # 电费单价
    status = db.Column(db.Enum(HostingSiteStatus), default=HostingSiteStatus.ONLINE)
    
    # 联系信息
    contact_name = db.Column(db.String(100))
    contact_phone = db.Column(db.String(50))
    contact_email = db.Column(db.String(256))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联设备
    hosted_devices = db.relationship('HostedDevice', backref='site', lazy=True)
    
    def __repr__(self):
        return f"<HostingSite {self.name} - {self.capacity_mw}MW>"

class HostedDevice(db.Model):
    """托管设备信息"""
    __tablename__ = 'hosted_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    
    # 设备基本信息
    device_serial = db.Column(db.String(100), unique=True, nullable=False)
    miner_model = db.Column(db.String(100), nullable=False)
    hashrate_th = db.Column(db.Float, nullable=False)  # 算力(TH/s)
    power_consumption_w = db.Column(db.Integer, nullable=False)  # 功耗(W)
    
    # 设备状态
    status = db.Column(db.Enum(DeviceStatus), default=DeviceStatus.RUNNING)
    uptime_hours = db.Column(db.Integer, default=0)  # 运行时间(小时)
    last_maintenance = db.Column(db.DateTime)
    
    # 托管信息
    hosting_start_date = db.Column(db.DateTime, nullable=False)
    hosting_end_date = db.Column(db.DateTime)
    monthly_hosting_fee = db.Column(db.Float, nullable=False)  # 月托管费
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联客户
    client = db.relationship('UserAccess', backref='hosted_devices')
    
    def __repr__(self):
        return f"<HostedDevice {self.device_serial} - {self.miner_model}>"

class SLATemplate(db.Model):
    """SLA模板"""
    __tablename__ = 'sla_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # SLA指标
    uptime_guarantee_percent = db.Column(db.Float, default=99.5)  # 正常运行时间保证
    response_time_hours = db.Column(db.Integer, default=4)  # 响应时间(小时)
    resolution_time_hours = db.Column(db.Integer, default=24)  # 解决时间(小时)
    
    # 赔偿条款
    penalty_rate_percent = db.Column(db.Float, default=5.0)  # 违约赔偿比例
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SLATemplate {self.name}>"

class ClientHostingContract(db.Model):
    """客户托管合同"""
    __tablename__ = 'hosting_contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    sla_template_id = db.Column(db.Integer, db.ForeignKey('sla_templates.id'), nullable=False)
    
    # 合同基本信息
    contract_number = db.Column(db.String(100), unique=True, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # 费用信息
    monthly_fee = db.Column(db.Float, nullable=False)
    deposit_amount = db.Column(db.Float, default=0.0)
    
    # 合同状态
    is_active = db.Column(db.Boolean, default=True)
    signed_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    client = db.relationship('UserAccess', backref='hosting_contracts')
    site = db.relationship('HostingSite', backref='contracts')
    sla_template = db.relationship('SLATemplate', backref='contracts')
    
    def __repr__(self):
        return f"<HostingContract {self.contract_number}>"
