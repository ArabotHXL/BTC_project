"""
挖矿核心模块 - 数据库模型
Mining Core Module - Database Models

独立的挖矿相关数据模型，无用户认证依赖
"""

from datetime import datetime, timedelta
import enum
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# 创建数据库基类
class Base(DeclarativeBase):
    pass

# 创建数据库实例
db = SQLAlchemy(model_class=Base)

# ============================================================================
# 枚举类型定义
# ============================================================================

class BlockchainVerificationStatus(enum.Enum):
    """区块链验证状态"""
    PENDING = "待验证"
    REGISTERED = "已注册"
    VERIFIED = "已验证"
    FAILED = "验证失败"
    EXPIRED = "已过期"

class SLAStatus(enum.Enum):
    """SLA状态"""
    EXCELLENT = "优秀"    # 95%+
    GOOD = "良好"         # 90-95%
    ACCEPTABLE = "合格"   # 85-90%
    POOR = "不足"        # 80-85%
    FAILED = "失败"      # <80%

# ============================================================================
# 矿机模型
# ============================================================================

class MinerModel(db.Model):
    """矿机型号信息数据库模型"""
    __tablename__ = 'miner_models'

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    manufacturer = db.Column(db.String(50), nullable=False)  # 制造商 (Antminer, WhatsMiner, etc.)
    reference_hashrate = db.Column(db.Float, nullable=False)  # 参考算力 (TH/s)
    reference_power = db.Column(db.Integer, nullable=False)  # 参考功耗 (W)
    reference_efficiency = db.Column(db.Float, nullable=True)  # 参考能效比 (W/TH)
    release_date = db.Column(db.Date, nullable=True)  # 发布日期
    reference_price = db.Column(db.Float, nullable=True)  # 参考价格 ($)
    is_active = db.Column(db.Boolean, default=True)  # 是否可用
    is_liquid_cooled = db.Column(db.Boolean, default=False)  # 是否水冷
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 技术规格
    chip_type = db.Column(db.String(50), nullable=True)  # 芯片类型
    fan_count = db.Column(db.Integer, nullable=True)  # 风扇数量
    operating_temp_min = db.Column(db.Integer, nullable=True)  # 最低工作温度
    operating_temp_max = db.Column(db.Integer, nullable=True)  # 最高工作温度
    noise_level = db.Column(db.Integer, nullable=True)  # 噪音等级 (dB)

    # 尺寸信息
    length_mm = db.Column(db.Float, nullable=True)  # 长度(mm)
    width_mm = db.Column(db.Float, nullable=True)   # 宽度(mm) 
    height_mm = db.Column(db.Float, nullable=True)  # 高度(mm)
    weight_kg = db.Column(db.Float, nullable=True)  # 重量(kg)

    def __init__(self, model_name, manufacturer, reference_hashrate, reference_power, **kwargs):
        self.model_name = model_name
        self.manufacturer = manufacturer
        self.reference_hashrate = reference_hashrate
        self.reference_power = reference_power

        # 自动计算参考能效比
        if reference_hashrate > 0:
            self.reference_efficiency = round(reference_power / reference_hashrate, 2)

        # 处理其他可选参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f"<MinerModel {self.model_name}: {self.reference_hashrate}TH/s, {self.reference_power}W>"

    def to_dict(self):
        """转换为字典格式，便于JSON序列化"""
        return {
            'id': self.id,
            'model_name': self.model_name,
            'manufacturer': self.manufacturer,
            'reference_hashrate': self.reference_hashrate,
            'reference_power': self.reference_power,
            'reference_efficiency': self.reference_efficiency,
            'reference_price': self.reference_price,
            'is_active': self.is_active,
            'is_liquid_cooled': self.is_liquid_cooled,
            'chip_type': self.chip_type,
            'release_date': self.release_date.isoformat() if self.release_date else None
        }

    @classmethod
    def get_active_miners(cls):
        """获取所有启用的矿机型号"""
        return cls.query.filter_by(is_active=True).order_by(cls.model_name).all()

    @classmethod
    def get_by_name(cls, model_name):
        """根据型号名称获取矿机"""
        return cls.query.filter_by(model_name=model_name, is_active=True).first()

    @classmethod
    def get_by_manufacturer(cls, manufacturer):
        """根据制造商获取矿机列表"""
        return cls.query.filter_by(manufacturer=manufacturer, is_active=True).order_by(cls.model_name).all()

# ============================================================================
# 网络数据模型
# ============================================================================

class NetworkSnapshot(db.Model):
    """网络状态快照记录"""
    __tablename__ = 'network_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    btc_price = db.Column(db.Float, nullable=False)
    network_difficulty = db.Column(db.Float, nullable=False)
    network_hashrate = db.Column(db.Float, nullable=False)  # 单位: EH/s
    block_reward = db.Column(db.Float, nullable=False, default=3.125)

    # API来源标记
    price_source = db.Column(db.String(50), default='coingecko')
    data_source = db.Column(db.String(50), default='blockchain.info')

    # 数据质量标记
    is_valid = db.Column(db.Boolean, default=True)
    api_response_time = db.Column(db.Float, nullable=True)  # API响应时间(秒)

    def __init__(self, btc_price, network_difficulty, network_hashrate, block_reward=3.125, 
                 price_source='coingecko', data_source='blockchain.info', is_valid=True, api_response_time=None):
        self.btc_price = btc_price
        self.network_difficulty = network_difficulty
        self.network_hashrate = network_hashrate
        self.block_reward = block_reward
        self.price_source = price_source
        self.data_source = data_source
        self.is_valid = is_valid
        self.api_response_time = api_response_time

    def __repr__(self):
        return f"<NetworkSnapshot {self.recorded_at}: BTC=${self.btc_price}, Difficulty={self.network_difficulty}T>"

    def to_dict(self):
        """转换为字典格式，便于JSON序列化"""
        return {
            'id': self.id,
            'recorded_at': self.recorded_at.isoformat(),
            'btc_price': self.btc_price,
            'network_difficulty': self.network_difficulty,
            'network_hashrate': self.network_hashrate,
            'block_reward': self.block_reward,
            'price_source': self.price_source,
            'data_source': self.data_source,
            'is_valid': self.is_valid
        }

# ============================================================================
# 市场分析数据模型
# ============================================================================

class MarketAnalytics(db.Model):
    """市场分析数据"""
    __tablename__ = 'market_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    btc_price = db.Column(db.Float, nullable=False)
    btc_market_cap = db.Column(db.BigInteger, nullable=True)
    btc_volume_24h = db.Column(db.BigInteger, nullable=True)
    network_hashrate = db.Column(db.Float, nullable=True)  # EH/s
    network_difficulty = db.Column(db.Float, nullable=True)
    block_reward = db.Column(db.Float, nullable=True, default=3.125)
    fear_greed_index = db.Column(db.Integer, nullable=True)
    price_change_1h = db.Column(db.Float, nullable=True)
    price_change_24h = db.Column(db.Float, nullable=True)
    price_change_7d = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(50), default='multiple')
    
    def __init__(self, btc_price, **kwargs):
        self.btc_price = btc_price
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'recorded_at': self.recorded_at.isoformat(),
            'btc_price': self.btc_price,
            'btc_market_cap': self.btc_market_cap,
            'btc_volume_24h': self.btc_volume_24h,
            'network_hashrate': self.network_hashrate,
            'network_difficulty': self.network_difficulty,
            'block_reward': self.block_reward,
            'fear_greed_index': self.fear_greed_index,
            'price_change_1h': self.price_change_1h,
            'price_change_24h': self.price_change_24h,
            'price_change_7d': self.price_change_7d,
            'source': self.source
        }

# ============================================================================
# 技术指标模型
# ============================================================================

class TechnicalIndicators(db.Model):
    """技术指标数据"""
    __tablename__ = 'technical_indicators'
    
    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    symbol = db.Column(db.String(10), default='BTC', nullable=False)
    
    # 移动平均线
    sma_20 = db.Column(db.Float, nullable=True)  # 20日简单移动平均
    sma_50 = db.Column(db.Float, nullable=True)  # 50日简单移动平均
    sma_200 = db.Column(db.Float, nullable=True) # 200日简单移动平均
    ema_12 = db.Column(db.Float, nullable=True)  # 12日指数移动平均
    ema_26 = db.Column(db.Float, nullable=True)  # 26日指数移动平均
    
    # 技术指标
    rsi_14 = db.Column(db.Float, nullable=True)  # 14日RSI
    macd = db.Column(db.Float, nullable=True)    # MACD
    macd_signal = db.Column(db.Float, nullable=True)  # MACD信号线
    macd_histogram = db.Column(db.Float, nullable=True)  # MACD柱状图
    
    # 布林带
    bb_upper = db.Column(db.Float, nullable=True)  # 布林带上轨
    bb_middle = db.Column(db.Float, nullable=True) # 布林带中轨
    bb_lower = db.Column(db.Float, nullable=True)  # 布林带下轨
    
    # 波动率指标
    volatility_30d = db.Column(db.Float, nullable=True)  # 30日波动率
    atr_14 = db.Column(db.Float, nullable=True)  # 14日ATR

    def to_dict(self):
        return {
            'id': self.id,
            'recorded_at': self.recorded_at.isoformat(),
            'symbol': self.symbol,
            'sma_20': self.sma_20,
            'sma_50': self.sma_50,
            'sma_200': self.sma_200,
            'ema_12': self.ema_12,
            'ema_26': self.ema_26,
            'rsi_14': self.rsi_14,
            'macd': self.macd,
            'macd_signal': self.macd_signal,
            'macd_histogram': self.macd_histogram,
            'bb_upper': self.bb_upper,
            'bb_middle': self.bb_middle,
            'bb_lower': self.bb_lower,
            'volatility_30d': self.volatility_30d,
            'atr_14': self.atr_14
        }

# ============================================================================
# 挖矿指标模型
# ============================================================================

class MiningMetrics(db.Model):
    """挖矿指标数据"""
    __tablename__ = 'mining_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # 网络指标
    hashrate_eh = db.Column(db.Float, nullable=False)  # 全网算力 (EH/s)
    difficulty = db.Column(db.Float, nullable=False)   # 挖矿难度
    difficulty_adjustment = db.Column(db.Float, nullable=True)  # 难度调整幅度 (%)
    next_difficulty_estimate = db.Column(db.Float, nullable=True)  # 下次难度预估
    
    # 区块指标
    block_height = db.Column(db.Integer, nullable=True)  # 区块高度
    blocks_found_24h = db.Column(db.Integer, nullable=True)  # 24小时出块数
    avg_block_time = db.Column(db.Float, nullable=True)  # 平均出块时间(分钟)
    
    # 收益指标
    btc_price = db.Column(db.Float, nullable=False)    # BTC价格
    mining_revenue_per_th = db.Column(db.Float, nullable=True)  # 每TH日收入(USD)
    hash_price = db.Column(db.Float, nullable=True)    # Hash价格指标
    puell_multiple = db.Column(db.Float, nullable=True)  # Puell倍数
    
    # 矿工行为指标
    miner_outflow = db.Column(db.Float, nullable=True)   # 矿工流出量(BTC)
    miner_reserves = db.Column(db.Float, nullable=True)  # 矿工储备量(BTC)
    
    def to_dict(self):
        return {
            'id': self.id,
            'recorded_at': self.recorded_at.isoformat(),
            'hashrate_eh': self.hashrate_eh,
            'difficulty': self.difficulty,
            'difficulty_adjustment': self.difficulty_adjustment,
            'next_difficulty_estimate': self.next_difficulty_estimate,
            'block_height': self.block_height,
            'blocks_found_24h': self.blocks_found_24h,
            'avg_block_time': self.avg_block_time,
            'btc_price': self.btc_price,
            'mining_revenue_per_th': self.mining_revenue_per_th,
            'hash_price': self.hash_price,
            'puell_multiple': self.puell_multiple,
            'miner_outflow': self.miner_outflow,
            'miner_reserves': self.miner_reserves
        }

# ============================================================================
# SLA指标模型（用于挖矿运营监控）
# ============================================================================

class SLAMetrics(db.Model):
    """SLA指标数据表 - 用于挖矿系统运营监控"""
    __tablename__ = 'sla_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 时间信息
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    month_year = db.Column(db.Integer, nullable=False, index=True)  # YYYYMM格式
    
    # 系统可用性指标
    uptime_percentage = db.Column(db.Numeric(5,2), nullable=False)  # 运行时间百分比
    availability_percentage = db.Column(db.Numeric(5,2), nullable=False)  # 服务可用性
    
    # 响应性能指标
    avg_response_time_ms = db.Column(db.Integer, nullable=False)  # 平均响应时间(毫秒)
    max_response_time_ms = db.Column(db.Integer, nullable=False)  # 最大响应时间
    min_response_time_ms = db.Column(db.Integer, nullable=False)  # 最小响应时间
    
    # 数据准确性指标
    data_accuracy_percentage = db.Column(db.Numeric(5,2), nullable=False)  # 数据准确性
    api_success_rate = db.Column(db.Numeric(5,2), nullable=False)  # API调用成功率
    
    # 透明度指标
    blockchain_verifications = db.Column(db.Integer, default=0)  # 区块链验证次数
    ipfs_uploads = db.Column(db.Integer, default=0)  # IPFS上传次数
    transparency_score = db.Column(db.Numeric(5,2), nullable=False)  # 透明度评分
    
    # 系统错误指标
    error_count = db.Column(db.Integer, default=0)  # 错误总数
    critical_error_count = db.Column(db.Integer, default=0)  # 严重错误数
    downtime_minutes = db.Column(db.Integer, default=0)  # 停机时间(分钟)
    
    # 综合评分
    composite_sla_score = db.Column(db.Numeric(6,2), nullable=False)  # 综合SLA评分(0-100)
    sla_status = db.Column(db.Enum(SLAStatus), nullable=False)  # SLA状态等级
    
    # 元数据
    data_source = db.Column(db.String(50), default='system_monitor')  # 数据源
    verified_by_blockchain = db.Column(db.Boolean, default=False)  # 是否已区块链验证
    
    def __init__(self, month_year, uptime_percentage, availability_percentage, 
                 avg_response_time_ms, data_accuracy_percentage, api_success_rate,
                 transparency_score, **kwargs):
        self.month_year = month_year
        self.uptime_percentage = uptime_percentage
        self.availability_percentage = availability_percentage
        self.avg_response_time_ms = avg_response_time_ms
        self.data_accuracy_percentage = data_accuracy_percentage
        self.api_success_rate = api_success_rate
        self.transparency_score = transparency_score
        
        # 计算综合SLA评分
        self.composite_sla_score = self.calculate_composite_score()
        self.sla_status = self.get_sla_status()
        
        # 处理其他可选参数
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def calculate_composite_score(self):
        """计算综合SLA评分"""
        # 权重分配：可用性40%，响应性能20%，数据准确性25%，透明度15%
        weights = {
            'availability': 0.40,
            'performance': 0.20,
            'accuracy': 0.25,
            'transparency': 0.15
        }
        
        # 响应性能评分（响应时间越低分数越高）
        performance_score = max(0, 100 - (float(self.avg_response_time_ms) / 10))
        performance_score = min(100, performance_score)  # 确保不超过100
        
        composite = (
            float(self.availability_percentage) * weights['availability'] +
            performance_score * weights['performance'] +
            float(self.data_accuracy_percentage) * weights['accuracy'] +
            float(self.transparency_score) * weights['transparency']
        )
        
        return round(composite, 2)
    
    def get_sla_status(self):
        """根据综合评分确定SLA状态"""
        score = float(self.composite_sla_score)
        if score >= 95:
            return SLAStatus.EXCELLENT
        elif score >= 90:
            return SLAStatus.GOOD
        elif score >= 85:
            return SLAStatus.ACCEPTABLE
        elif score >= 80:
            return SLAStatus.POOR
        else:
            return SLAStatus.FAILED

# ============================================================================
# 区块链记录模型
# ============================================================================

class BlockchainRecord(db.Model):
    """区块链数据记录模型 - 存储链上记录和IPFS数据"""
    __tablename__ = 'blockchain_records'

    id = db.Column(db.Integer, primary_key=True)
    
    # 数据标识
    data_hash = db.Column(db.String(66), unique=True, nullable=False, index=True)  # 0x + 64位十六进制
    ipfs_cid = db.Column(db.String(100), nullable=False, index=True)  # IPFS内容标识符
    
    # 站点信息
    site_id = db.Column(db.String(100), nullable=False, index=True)  # 矿场站点ID
    site_name = db.Column(db.String(200), nullable=True)  # 站点名称
    
    # 区块链信息
    blockchain_network = db.Column(db.String(50), default='Base L2', nullable=False)  # 区块链网络
    contract_address = db.Column(db.String(42), nullable=True)  # 智能合约地址
    transaction_hash = db.Column(db.String(66), nullable=True, index=True)  # 交易哈希
    block_number = db.Column(db.BigInteger, nullable=True)  # 区块号
    gas_used = db.Column(db.Integer, nullable=True)  # 使用的gas
    gas_price = db.Column(db.BigInteger, nullable=True)  # gas价格
    
    # 数据内容摘要
    mining_data_summary = db.Column(db.Text, nullable=True)  # 挖矿数据摘要（JSON格式）
    hashrate_th = db.Column(db.Float, nullable=True)  # 算力 (TH/s)
    power_consumption_w = db.Column(db.Float, nullable=True)  # 功耗 (W)
    daily_btc_production = db.Column(db.Float, nullable=True)  # 日产BTC
    daily_revenue_usd = db.Column(db.Float, nullable=True)  # 日收入 (USD)
    
    # 验证状态
    verification_status = db.Column(
        db.Enum(BlockchainVerificationStatus), 
        default=BlockchainVerificationStatus.PENDING, 
        nullable=False
    )
    verification_count = db.Column(db.Integer, default=0, nullable=False)  # 验证次数
    last_verified_at = db.Column(db.DateTime, nullable=True)  # 最后验证时间
    
    # 数据完整性
    data_version = db.Column(db.String(10), default='1.0', nullable=False)  # 数据版本
    encryption_enabled = db.Column(db.Boolean, default=True, nullable=False)  # 是否加密
    data_integrity_hash = db.Column(db.String(64), nullable=True)  # 数据完整性哈希
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    blockchain_timestamp = db.Column(db.DateTime, nullable=True)  # 区块链时间戳
    data_timestamp = db.Column(db.DateTime, nullable=False)  # 数据生成时间戳
    
    # 元数据
    record_metadata = db.Column(db.Text, nullable=True)  # 额外元数据（JSON格式）
    notes = db.Column(db.Text, nullable=True)  # 备注
    
    def __init__(self, data_hash, ipfs_cid, site_id, **kwargs):
        self.data_hash = data_hash
        self.ipfs_cid = ipfs_cid
        self.site_id = site_id
        self.data_timestamp = datetime.utcnow()
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_hash': self.data_hash,
            'ipfs_cid': self.ipfs_cid,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'blockchain_network': self.blockchain_network,
            'contract_address': self.contract_address,
            'transaction_hash': self.transaction_hash,
            'block_number': self.block_number,
            'hashrate_th': self.hashrate_th,
            'power_consumption_w': self.power_consumption_w,
            'daily_btc_production': self.daily_btc_production,
            'daily_revenue_usd': self.daily_revenue_usd,
            'verification_status': self.verification_status.value if self.verification_status else None,
            'verification_count': self.verification_count,
            'last_verified_at': self.last_verified_at.isoformat() if self.last_verified_at else None,
            'created_at': self.created_at.isoformat(),
            'data_timestamp': self.data_timestamp.isoformat()
        }