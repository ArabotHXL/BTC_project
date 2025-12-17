"""
热保护服务 - 温度智能控频系统
Temperature-based Intelligent Frequency Control Service

监控矿机温度并在过热时自动降频保护，温度恢复后自动恢复频率
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func

from app import db
from models import (
    ThermalProtectionConfig, ThermalEvent, ThermalEventType,
    HostingSite, HostingMiner, MinerTelemetry
)

logger = logging.getLogger(__name__)


class ThermalProtectionService:
    """热保护服务 - 监控温度并自动控制频率"""
    
    def __init__(self):
        self.throttled_miners: Dict[int, Dict] = {}
    
    def get_config(self, site_id: int) -> Optional[ThermalProtectionConfig]:
        """获取站点的热保护配置 (不论启用状态)"""
        return ThermalProtectionConfig.query.filter_by(
            site_id=site_id
        ).first()
    
    def get_enabled_config(self, site_id: int) -> Optional[ThermalProtectionConfig]:
        """获取站点启用的热保护配置 (用于实际温度检查)"""
        return ThermalProtectionConfig.query.filter_by(
            site_id=site_id,
            is_enabled=True
        ).first()
    
    def create_default_config(self, site_id: int) -> ThermalProtectionConfig:
        """为站点创建默认热保护配置"""
        config = ThermalProtectionConfig(
            site_id=site_id,
            config_name='默认热保护配置',
            warning_temp=70.0,
            throttle_temp=80.0,
            critical_temp=90.0,
            recovery_temp=65.0,
            throttle_frequency_percent=80,
            min_frequency_percent=50,
            cooldown_minutes=10,
            is_enabled=True,
            notify_on_warning=True,
            notify_on_throttle=True,
            notify_on_critical=True
        )
        db.session.add(config)
        db.session.commit()
        return config
    
    def update_config(self, config_id: int, data: Dict) -> Tuple[bool, str]:
        """更新热保护配置"""
        config = ThermalProtectionConfig.query.get(config_id)
        if not config:
            return False, "配置不存在"
        
        allowed_fields = [
            'config_name', 'warning_temp', 'throttle_temp', 'critical_temp',
            'recovery_temp', 'throttle_frequency_percent', 'min_frequency_percent',
            'cooldown_minutes', 'is_enabled', 'notify_on_warning',
            'notify_on_throttle', 'notify_on_critical', 'notification_email'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(config, field, data[field])
        
        try:
            db.session.commit()
            return True, "配置更新成功"
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新热保护配置失败: {e}")
            return False, str(e)
    
    def get_miner_temperature(self, miner_id: int) -> Optional[float]:
        """获取矿机当前温度"""
        telemetry = MinerTelemetry.query.filter_by(
            miner_id=miner_id
        ).order_by(MinerTelemetry.recorded_at.desc()).first()
        
        if telemetry and telemetry.temperature:
            return telemetry.temperature
        
        miner = HostingMiner.query.get(miner_id)
        if miner and miner.temperature_max:
            return miner.temperature_max
        
        return None
    
    def check_temperature(self, miner: HostingMiner, config: ThermalProtectionConfig) -> Optional[Dict]:
        """检查矿机温度并决定是否需要采取行动
        
        Returns:
            None if no action needed, or Dict with action details
        """
        temp = self.get_miner_temperature(miner.id)
        if temp is None:
            return None
        
        miner_state = self.throttled_miners.get(miner.id, {})
        is_throttled = miner_state.get('is_throttled', False)
        
        if temp >= config.critical_temp:
            return {
                'event_type': ThermalEventType.CRITICAL,
                'temperature': temp,
                'threshold': config.critical_temp,
                'action': 'disable',
                'message': f'温度过高 ({temp}°C >= {config.critical_temp}°C)，强制关机'
            }
        
        if temp >= config.throttle_temp and not is_throttled:
            return {
                'event_type': ThermalEventType.THROTTLE,
                'temperature': temp,
                'threshold': config.throttle_temp,
                'action': 'throttle',
                'frequency_percent': config.throttle_frequency_percent,
                'message': f'温度过高 ({temp}°C >= {config.throttle_temp}°C)，降低频率至 {config.throttle_frequency_percent}%'
            }
        
        if temp >= config.warning_temp and temp < config.throttle_temp:
            if not miner_state.get('warned', False):
                return {
                    'event_type': ThermalEventType.WARNING,
                    'temperature': temp,
                    'threshold': config.warning_temp,
                    'action': 'warn',
                    'message': f'温度预警 ({temp}°C >= {config.warning_temp}°C)'
                }
        
        if is_throttled and temp <= config.recovery_temp:
            cooldown_time = miner_state.get('throttle_time')
            if cooldown_time:
                elapsed = (datetime.utcnow() - cooldown_time).total_seconds() / 60
                if elapsed >= config.cooldown_minutes:
                    return {
                        'event_type': ThermalEventType.RECOVERY,
                        'temperature': temp,
                        'threshold': config.recovery_temp,
                        'action': 'recover',
                        'message': f'温度恢复 ({temp}°C <= {config.recovery_temp}°C)，恢复正常频率'
                    }
        
        return None
    
    def execute_thermal_action(self, miner: HostingMiner, action: Dict, config: ThermalProtectionConfig) -> Tuple[bool, str]:
        """执行热保护动作
        
        Returns:
            (success, message)
        """
        from edge_collector.cgminer_collector import CGMinerClient
        
        miner_id = miner.id
        action_type = action.get('action')
        event_type = action.get('event_type')
        temperature = action.get('temperature', 0)
        threshold = action.get('threshold', 0)
        
        event = ThermalEvent(
            site_id=miner.site_id,
            miner_id=miner_id,
            event_type=event_type,
            temperature=temperature,
            threshold=threshold
        )
        
        success = False
        message = action.get('message', '')
        
        try:
            if action_type == 'warn':
                success = True
                event.action_taken = 'warning_logged'
                self.throttled_miners[miner_id] = {
                    'warned': True,
                    'warn_time': datetime.utcnow()
                }
                
            elif action_type == 'throttle':
                if miner.ip_address:
                    client = CGMinerClient(miner.ip_address)
                    freq_percent = action.get('frequency_percent', 80)
                    
                    base_frequency = 600
                    target_freq = int(base_frequency * freq_percent / 100)
                    
                    ok, result = client.set_frequency(target_freq)
                    success = ok
                    event.action_taken = 'frequency_throttled'
                    event.frequency_before = base_frequency
                    event.frequency_after = target_freq
                    
                    if ok:
                        self.throttled_miners[miner_id] = {
                            'is_throttled': True,
                            'throttle_time': datetime.utcnow(),
                            'original_frequency': base_frequency,
                            'throttled_frequency': target_freq
                        }
                else:
                    success = False
                    message = "矿机无IP地址，无法执行降频"
                    
            elif action_type == 'disable':
                if miner.ip_address:
                    client = CGMinerClient(miner.ip_address)
                    ok, result = client.disable_mining()
                    success = ok
                    event.action_taken = 'mining_disabled'
                    
                    if ok:
                        miner.status = 'offline'
                        self.throttled_miners[miner_id] = {
                            'is_disabled': True,
                            'disable_time': datetime.utcnow()
                        }
                else:
                    success = False
                    message = "矿机无IP地址，无法关机"
                    
            elif action_type == 'recover':
                if miner.ip_address:
                    client = CGMinerClient(miner.ip_address)
                    
                    miner_state = self.throttled_miners.get(miner_id, {})
                    original_freq = miner_state.get('original_frequency', 600)
                    
                    ok, result = client.set_frequency(original_freq)
                    success = ok
                    event.action_taken = 'frequency_recovered'
                    event.frequency_before = miner_state.get('throttled_frequency')
                    event.frequency_after = original_freq
                    
                    if ok:
                        self.throttled_miners.pop(miner_id, None)
                        
                        prev_event = ThermalEvent.query.filter_by(
                            miner_id=miner_id,
                            event_type=ThermalEventType.THROTTLE,
                            resolved_at=None
                        ).order_by(ThermalEvent.created_at.desc()).first()
                        
                        if prev_event:
                            prev_event.resolved_at = datetime.utcnow()
                else:
                    success = False
                    message = "矿机无IP地址，无法恢复频率"
            
            event.success = success
            if not success:
                event.error_message = message
                
            db.session.add(event)
            db.session.commit()
            
            if success:
                self._send_notification(miner, config, action)
                event.notification_sent = True
                db.session.commit()
            
            return success, message
            
        except Exception as e:
            logger.error(f"执行热保护动作失败: {e}")
            event.success = False
            event.error_message = str(e)
            db.session.add(event)
            db.session.commit()
            return False, str(e)
    
    def _send_notification(self, miner: HostingMiner, config: ThermalProtectionConfig, action: Dict):
        """发送告警通知"""
        event_type = action.get('event_type')
        
        should_notify = False
        if event_type == ThermalEventType.WARNING and config.notify_on_warning:
            should_notify = True
        elif event_type == ThermalEventType.THROTTLE and config.notify_on_throttle:
            should_notify = True
        elif event_type == ThermalEventType.CRITICAL and config.notify_on_critical:
            should_notify = True
        
        if not should_notify:
            return
        
        logger.info(f"热保护告警: 矿机 {miner.serial_number} - {action.get('message')}")
    
    def check_site(self, site_id: int) -> Dict:
        """检查整个站点的矿机温度
        
        Returns:
            Dict with check results summary
        """
        config = self.get_enabled_config(site_id)
        if not config:
            return {'error': '热保护未启用或无配置', 'checked': 0, 'actions': 0}
        
        miners = HostingMiner.query.filter_by(
            site_id=site_id,
            status='active'
        ).all()
        
        results = {
            'checked': len(miners),
            'actions': 0,
            'warnings': 0,
            'throttles': 0,
            'criticals': 0,
            'recoveries': 0,
            'errors': []
        }
        
        for miner in miners:
            action = self.check_temperature(miner, config)
            if action:
                results['actions'] += 1
                success, msg = self.execute_thermal_action(miner, action, config)
                
                event_type = action.get('event_type')
                if event_type == ThermalEventType.WARNING:
                    results['warnings'] += 1
                elif event_type == ThermalEventType.THROTTLE:
                    results['throttles'] += 1
                elif event_type == ThermalEventType.CRITICAL:
                    results['criticals'] += 1
                elif event_type == ThermalEventType.RECOVERY:
                    results['recoveries'] += 1
                
                if not success:
                    results['errors'].append({
                        'miner_id': miner.id,
                        'serial': miner.serial_number,
                        'error': msg
                    })
        
        return results
    
    def get_thermal_events(self, site_id: int, limit: int = 50, 
                          event_type: str = None, miner_id: int = None) -> List[Dict]:
        """获取热保护事件历史"""
        query = ThermalEvent.query.filter_by(site_id=site_id)
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        if miner_id:
            query = query.filter_by(miner_id=miner_id)
        
        events = query.order_by(ThermalEvent.created_at.desc()).limit(limit).all()
        return [e.to_dict() for e in events]
    
    def get_thermal_stats(self, site_id: int) -> Dict:
        """获取热保护统计数据"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        today_events = db.session.query(
            ThermalEvent.event_type,
            func.count(ThermalEvent.id).label('count')
        ).filter(
            ThermalEvent.site_id == site_id,
            ThermalEvent.created_at >= today
        ).group_by(ThermalEvent.event_type).all()
        
        today_stats = {e.event_type: e.count for e in today_events}
        
        throttled_count = len([
            m_id for m_id, state in self.throttled_miners.items()
            if state.get('is_throttled', False)
        ])
        
        high_temp_miners = HostingMiner.query.filter(
            HostingMiner.site_id == site_id,
            HostingMiner.temperature_max >= 70,
            HostingMiner.status == 'active'
        ).count()
        
        return {
            'today_warnings': today_stats.get(ThermalEventType.WARNING, 0),
            'today_throttles': today_stats.get(ThermalEventType.THROTTLE, 0),
            'today_criticals': today_stats.get(ThermalEventType.CRITICAL, 0),
            'today_recoveries': today_stats.get(ThermalEventType.RECOVERY, 0),
            'currently_throttled': throttled_count,
            'high_temp_miners': high_temp_miners
        }


thermal_protection_service = ThermalProtectionService()
