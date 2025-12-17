"""
矿机告警规则引擎
Miner Alert Rules Engine

功能:
- 温度阈值告警 (过热/临界温度)
- 离线检测 (矿机掉线)
- 算力异常 (算力下降/波动)
- 自动恢复检测
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass
from sqlalchemy import func, and_
from models import db, HostingSite

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""
    TEMPERATURE_HIGH = "temperature_high"
    TEMPERATURE_CRITICAL = "temperature_critical"
    MINER_OFFLINE = "miner_offline"
    HASHRATE_LOW = "hashrate_low"
    HASHRATE_DROP = "hashrate_drop"
    HARDWARE_ERROR = "hardware_error"
    FAN_FAILURE = "fan_failure"
    BATCH_OFFLINE = "batch_offline"


@dataclass
class AlertRule:
    """告警规则配置"""
    rule_id: str
    name: str
    name_zh: str
    alert_type: AlertType
    level: AlertLevel
    threshold: float
    comparison: str  # gt, lt, eq, gte, lte
    enabled: bool = True
    cooldown_minutes: int = 30


@dataclass
class Alert:
    """告警记录"""
    alert_id: str
    site_id: int
    miner_id: Optional[str]
    alert_type: AlertType
    level: AlertLevel
    rule_id: str
    message: str
    message_zh: str
    value: float
    threshold: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False


class MinerAlertRule(db.Model):
    """矿机告警规则数据模型"""
    __tablename__ = 'miner_alert_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    
    rule_name = db.Column(db.String(100), nullable=False)
    rule_name_zh = db.Column(db.String(100))
    alert_type = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), default='warning')
    
    threshold = db.Column(db.Float, nullable=False)
    comparison = db.Column(db.String(10), default='gt')
    
    enabled = db.Column(db.Boolean, default=True)
    cooldown_minutes = db.Column(db.Integer, default=30)
    
    notify_email = db.Column(db.Boolean, default=False)
    notify_webhook = db.Column(db.Boolean, default=False)
    webhook_url = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MinerAlert(db.Model):
    """矿机告警记录"""
    __tablename__ = 'miner_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False)
    miner_id = db.Column(db.String(50))
    
    alert_type = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey('miner_alert_rules.id'))
    
    message = db.Column(db.Text)
    message_zh = db.Column(db.Text)
    
    value = db.Column(db.Float)
    threshold = db.Column(db.Float)
    
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.Integer)
    acknowledged_at = db.Column(db.DateTime)
    
    notes = db.Column(db.Text)
    
    __table_args__ = (
        db.Index('ix_alerts_site_type', 'site_id', 'alert_type'),
        db.Index('ix_alerts_site_resolved', 'site_id', 'resolved_at'),
    )


class AlertEngine:
    """告警引擎"""
    
    DEFAULT_RULES = [
        AlertRule(
            rule_id="temp_high",
            name="High Temperature",
            name_zh="高温告警",
            alert_type=AlertType.TEMPERATURE_HIGH,
            level=AlertLevel.WARNING,
            threshold=75.0,
            comparison="gt"
        ),
        AlertRule(
            rule_id="temp_critical",
            name="Critical Temperature",
            name_zh="临界温度告警",
            alert_type=AlertType.TEMPERATURE_CRITICAL,
            level=AlertLevel.CRITICAL,
            threshold=85.0,
            comparison="gt"
        ),
        AlertRule(
            rule_id="offline",
            name="Miner Offline",
            name_zh="矿机离线",
            alert_type=AlertType.MINER_OFFLINE,
            level=AlertLevel.WARNING,
            threshold=1,
            comparison="eq"
        ),
        AlertRule(
            rule_id="hashrate_low",
            name="Low Hashrate",
            name_zh="算力过低",
            alert_type=AlertType.HASHRATE_LOW,
            level=AlertLevel.WARNING,
            threshold=50.0,
            comparison="lt"
        ),
        AlertRule(
            rule_id="hardware_error",
            name="Hardware Errors",
            name_zh="硬件错误",
            alert_type=AlertType.HARDWARE_ERROR,
            level=AlertLevel.WARNING,
            threshold=100,
            comparison="gt"
        ),
    ]
    
    def __init__(self, app=None):
        self.app = app
        self.alert_cooldowns = {}
    
    def init_app(self, app):
        """初始化Flask应用"""
        self.app = app
    
    def check_site_alerts(self, site_id: int) -> List[MinerAlert]:
        """检查站点所有告警"""
        try:
            from api.collector_api import MinerTelemetryLive
        except ImportError:
            logger.warning("MinerTelemetryLive not available")
            return []
        
        alerts = []
        
        rules = MinerAlertRule.query.filter_by(
            site_id=site_id,
            enabled=True
        ).all()
        
        if not rules:
            rules = self._get_default_rules()
        
        for rule in rules:
            rule_alerts = self._evaluate_rule(site_id, rule)
            alerts.extend(rule_alerts)
        
        return alerts
    
    def _evaluate_rule(self, site_id: int, rule) -> List[MinerAlert]:
        """评估单条规则"""
        try:
            from api.collector_api import MinerTelemetryLive
        except ImportError:
            return []
        
        alerts = []
        alert_type = rule.alert_type if isinstance(rule.alert_type, str) else rule.alert_type.value
        
        if alert_type in ['temperature_high', 'temperature_critical']:
            alerts = self._check_temperature(site_id, rule)
        elif alert_type == 'miner_offline':
            alerts = self._check_offline(site_id, rule)
        elif alert_type == 'hashrate_low':
            alerts = self._check_hashrate(site_id, rule)
        elif alert_type == 'hardware_error':
            alerts = self._check_hardware_errors(site_id, rule)
        
        return alerts
    
    def _check_temperature(self, site_id: int, rule) -> List[MinerAlert]:
        """检查温度告警"""
        try:
            from api.collector_api import MinerTelemetryLive
        except ImportError:
            return []
        
        alerts = []
        threshold = rule.threshold if isinstance(rule, MinerAlertRule) else rule.threshold
        level = rule.level if isinstance(rule.level, str) else rule.level.value
        alert_type = rule.alert_type if isinstance(rule.alert_type, str) else rule.alert_type.value
        
        hot_miners = MinerTelemetryLive.query.filter(
            MinerTelemetryLive.site_id == site_id,
            MinerTelemetryLive.online == True,
            MinerTelemetryLive.temperature_max > threshold
        ).all()
        
        for miner in hot_miners:
            if self._is_in_cooldown(site_id, miner.miner_id, alert_type):
                continue
            
            existing = MinerAlert.query.filter(
                MinerAlert.site_id == site_id,
                MinerAlert.miner_id == miner.miner_id,
                MinerAlert.alert_type == alert_type,
                MinerAlert.resolved_at == None
            ).first()
            
            if existing:
                continue
            
            alert = MinerAlert(
                site_id=site_id,
                miner_id=miner.miner_id,
                alert_type=alert_type,
                level=level,
                rule_id=rule.id if isinstance(rule, MinerAlertRule) else None,
                message=f"Miner {miner.miner_id} temperature {miner.temperature_max:.1f}°C exceeds threshold {threshold}°C",
                message_zh=f"矿机 {miner.miner_id} 温度 {miner.temperature_max:.1f}°C 超过阈值 {threshold}°C",
                value=miner.temperature_max,
                threshold=threshold
            )
            db.session.add(alert)
            alerts.append(alert)
            
            self._set_cooldown(site_id, miner.miner_id, alert_type)
        
        if alerts:
            db.session.commit()
        
        return alerts
    
    def _check_offline(self, site_id: int, rule) -> List[MinerAlert]:
        """检查离线矿机"""
        try:
            from api.collector_api import MinerTelemetryLive
        except ImportError:
            return []
        
        alerts = []
        level = rule.level if isinstance(rule.level, str) else rule.level.value
        alert_type = 'miner_offline'
        
        offline_threshold = datetime.utcnow() - timedelta(minutes=5)
        
        offline_miners = MinerTelemetryLive.query.filter(
            MinerTelemetryLive.site_id == site_id,
            MinerTelemetryLive.online == False
        ).all()
        
        for miner in offline_miners:
            if self._is_in_cooldown(site_id, miner.miner_id, alert_type):
                continue
            
            existing = MinerAlert.query.filter(
                MinerAlert.site_id == site_id,
                MinerAlert.miner_id == miner.miner_id,
                MinerAlert.alert_type == alert_type,
                MinerAlert.resolved_at == None
            ).first()
            
            if existing:
                continue
            
            last_seen = miner.last_seen.strftime('%Y-%m-%d %H:%M:%S') if miner.last_seen else 'Unknown'
            
            alert = MinerAlert(
                site_id=site_id,
                miner_id=miner.miner_id,
                alert_type=alert_type,
                level=level,
                rule_id=rule.id if isinstance(rule, MinerAlertRule) else None,
                message=f"Miner {miner.miner_id} is offline. Last seen: {last_seen}",
                message_zh=f"矿机 {miner.miner_id} 已离线。最后在线: {last_seen}",
                value=0,
                threshold=1
            )
            db.session.add(alert)
            alerts.append(alert)
            
            self._set_cooldown(site_id, miner.miner_id, alert_type)
        
        if alerts:
            db.session.commit()
        
        return alerts
    
    def _check_hashrate(self, site_id: int, rule) -> List[MinerAlert]:
        """检查算力异常"""
        try:
            from api.collector_api import MinerTelemetryLive
        except ImportError:
            return []
        
        alerts = []
        threshold = rule.threshold if isinstance(rule, MinerAlertRule) else rule.threshold
        level = rule.level if isinstance(rule.level, str) else rule.level.value
        alert_type = 'hashrate_low'
        
        low_hashrate_miners = MinerTelemetryLive.query.filter(
            MinerTelemetryLive.site_id == site_id,
            MinerTelemetryLive.online == True,
            MinerTelemetryLive.hashrate_ghs > 0,
            MinerTelemetryLive.hashrate_ghs < threshold * 1000
        ).all()
        
        for miner in low_hashrate_miners:
            if self._is_in_cooldown(site_id, miner.miner_id, alert_type):
                continue
            
            existing = MinerAlert.query.filter(
                MinerAlert.site_id == site_id,
                MinerAlert.miner_id == miner.miner_id,
                MinerAlert.alert_type == alert_type,
                MinerAlert.resolved_at == None
            ).first()
            
            if existing:
                continue
            
            hashrate_ths = miner.hashrate_ghs / 1000
            
            alert = MinerAlert(
                site_id=site_id,
                miner_id=miner.miner_id,
                alert_type=alert_type,
                level=level,
                rule_id=rule.id if isinstance(rule, MinerAlertRule) else None,
                message=f"Miner {miner.miner_id} hashrate {hashrate_ths:.2f} TH/s below threshold {threshold} TH/s",
                message_zh=f"矿机 {miner.miner_id} 算力 {hashrate_ths:.2f} TH/s 低于阈值 {threshold} TH/s",
                value=hashrate_ths,
                threshold=threshold
            )
            db.session.add(alert)
            alerts.append(alert)
            
            self._set_cooldown(site_id, miner.miner_id, alert_type)
        
        if alerts:
            db.session.commit()
        
        return alerts
    
    def _check_hardware_errors(self, site_id: int, rule) -> List[MinerAlert]:
        """检查硬件错误"""
        try:
            from api.collector_api import MinerTelemetryLive
        except ImportError:
            return []
        
        alerts = []
        threshold = rule.threshold if isinstance(rule, MinerAlertRule) else rule.threshold
        level = rule.level if isinstance(rule.level, str) else rule.level.value
        alert_type = 'hardware_error'
        
        error_miners = MinerTelemetryLive.query.filter(
            MinerTelemetryLive.site_id == site_id,
            MinerTelemetryLive.hardware_errors > threshold
        ).all()
        
        for miner in error_miners:
            if self._is_in_cooldown(site_id, miner.miner_id, alert_type):
                continue
            
            existing = MinerAlert.query.filter(
                MinerAlert.site_id == site_id,
                MinerAlert.miner_id == miner.miner_id,
                MinerAlert.alert_type == alert_type,
                MinerAlert.resolved_at == None
            ).first()
            
            if existing:
                continue
            
            alert = MinerAlert(
                site_id=site_id,
                miner_id=miner.miner_id,
                alert_type=alert_type,
                level=level,
                rule_id=rule.id if isinstance(rule, MinerAlertRule) else None,
                message=f"Miner {miner.miner_id} has {miner.hardware_errors} hardware errors (threshold: {threshold})",
                message_zh=f"矿机 {miner.miner_id} 有 {miner.hardware_errors} 个硬件错误 (阈值: {threshold})",
                value=miner.hardware_errors,
                threshold=threshold
            )
            db.session.add(alert)
            alerts.append(alert)
            
            self._set_cooldown(site_id, miner.miner_id, alert_type)
        
        if alerts:
            db.session.commit()
        
        return alerts
    
    def auto_resolve_alerts(self, site_id: int) -> int:
        """自动解决已恢复的告警"""
        try:
            from api.collector_api import MinerTelemetryLive
        except ImportError:
            return 0
        
        resolved_count = 0
        
        active_alerts = MinerAlert.query.filter(
            MinerAlert.site_id == site_id,
            MinerAlert.resolved_at == None
        ).all()
        
        for alert in active_alerts:
            miner = MinerTelemetryLive.query.filter_by(
                site_id=site_id,
                miner_id=alert.miner_id
            ).first()
            
            if not miner:
                continue
            
            should_resolve = False
            
            if alert.alert_type in ['temperature_high', 'temperature_critical']:
                if miner.temperature_max <= alert.threshold:
                    should_resolve = True
            elif alert.alert_type == 'miner_offline':
                if miner.online:
                    should_resolve = True
            elif alert.alert_type == 'hashrate_low':
                if miner.hashrate_ghs >= alert.threshold * 1000:
                    should_resolve = True
            elif alert.alert_type == 'hardware_error':
                pass
            
            if should_resolve:
                alert.resolved_at = datetime.utcnow()
                resolved_count += 1
        
        if resolved_count > 0:
            db.session.commit()
            logger.info(f"Auto-resolved {resolved_count} alerts for site {site_id}")
        
        return resolved_count
    
    def get_active_alerts(self, site_id: int, limit: int = 50) -> List[MinerAlert]:
        """获取活动告警列表"""
        return MinerAlert.query.filter(
            MinerAlert.site_id == site_id,
            MinerAlert.resolved_at == None
        ).order_by(MinerAlert.triggered_at.desc()).limit(limit).all()
    
    def get_alert_summary(self, site_id: int) -> Dict[str, Any]:
        """获取告警摘要"""
        active_alerts = MinerAlert.query.filter(
            MinerAlert.site_id == site_id,
            MinerAlert.resolved_at == None
        )
        
        critical_count = active_alerts.filter(MinerAlert.level == 'critical').count()
        warning_count = active_alerts.filter(MinerAlert.level == 'warning').count()
        info_count = active_alerts.filter(MinerAlert.level == 'info').count()
        
        by_type = db.session.query(
            MinerAlert.alert_type,
            func.count(MinerAlert.id)
        ).filter(
            MinerAlert.site_id == site_id,
            MinerAlert.resolved_at == None
        ).group_by(MinerAlert.alert_type).all()
        
        return {
            'total': critical_count + warning_count + info_count,
            'critical': critical_count,
            'warning': warning_count,
            'info': info_count,
            'by_type': {t: c for t, c in by_type}
        }
    
    def acknowledge_alert(self, alert_id: int, user_id: int, notes: str = None) -> bool:
        """确认告警"""
        alert = MinerAlert.query.get(alert_id)
        if not alert:
            return False
        
        alert.acknowledged = True
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()
        if notes:
            alert.notes = notes
        
        db.session.commit()
        return True
    
    def resolve_alert(self, alert_id: int) -> bool:
        """手动解决告警"""
        alert = MinerAlert.query.get(alert_id)
        if not alert:
            return False
        
        alert.resolved_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def _is_in_cooldown(self, site_id: int, miner_id: str, alert_type: str) -> bool:
        """检查是否在冷却期"""
        key = f"{site_id}:{miner_id}:{alert_type}"
        if key in self.alert_cooldowns:
            cooldown_until = self.alert_cooldowns[key]
            if datetime.utcnow() < cooldown_until:
                return True
        return False
    
    def _set_cooldown(self, site_id: int, miner_id: str, alert_type: str, minutes: int = 30):
        """设置冷却期"""
        key = f"{site_id}:{miner_id}:{alert_type}"
        self.alert_cooldowns[key] = datetime.utcnow() + timedelta(minutes=minutes)
    
    def _get_default_rules(self) -> List[AlertRule]:
        """获取默认规则"""
        return self.DEFAULT_RULES


alert_engine = AlertEngine()


def create_alert_tables():
    """创建告警相关数据库表"""
    try:
        db.create_all()
        logger.info("Alert tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create alert tables: {e}")
