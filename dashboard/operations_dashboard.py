"""
HashInsight Enterprise - Operations Dashboard
运维工作台
"""

from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy import text
from db import db
from models import UserMiner


class OperationsDashboard:
    """运维工作台"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def get_health_status(self) -> Dict:
        """矿机健康状态"""
        miners = UserMiner.query.filter_by(user_id=self.user_id).all()
        
        health_stats = {
            'total': len(miners),
            'active': sum(1 for m in miners if m.status == 'active'),
            'maintenance': sum(1 for m in miners if m.status == 'maintenance'),
            'offline': sum(1 for m in miners if m.status == 'offline'),
            'degraded': sum(1 for m in miners if self._is_degraded(m)),
            'critical': sum(1 for m in miners if self._is_critical(m))
        }
        
        return health_stats
    
    def get_alert_center(self) -> List[Dict]:
        """告警中心"""
        miners = UserMiner.query.filter_by(user_id=self.user_id).all()
        alerts = []
        
        for miner in miners:
            if self._is_critical(miner):
                alerts.append({
                    'severity': 'critical',
                    'miner_id': miner.id,
                    'miner_name': miner.custom_name or f"Miner #{miner.id}",
                    'message': 'Critical performance degradation detected',
                    'timestamp': datetime.utcnow()
                })
            elif self._is_degraded(miner):
                alerts.append({
                    'severity': 'warning',
                    'miner_id': miner.id,
                    'miner_name': miner.custom_name or f"Miner #{miner.id}",
                    'message': 'Performance degradation detected',
                    'timestamp': datetime.utcnow()
                })
        
        return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)
    
    def get_maintenance_plan(self) -> List[Dict]:
        """维护计划"""
        miners = UserMiner.query.filter_by(user_id=self.user_id).all()
        maintenance_plan = []
        
        for miner in miners:
            if miner.last_maintenance_date:
                days_since = (datetime.utcnow().date() - miner.last_maintenance_date).days
                if days_since > 90:
                    maintenance_plan.append({
                        'miner_id': miner.id,
                        'miner_name': miner.custom_name or f"Miner #{miner.id}",
                        'last_maintenance': miner.last_maintenance_date,
                        'days_overdue': days_since - 90,
                        'priority': 'high' if days_since > 180 else 'medium'
                    })
        
        return sorted(maintenance_plan, key=lambda x: x['days_overdue'], reverse=True)
    
    def _is_degraded(self, miner: UserMiner) -> bool:
        """检查是否性能降级"""
        if miner.original_hashrate and miner.actual_hashrate:
            degradation = (miner.original_hashrate - miner.actual_hashrate) / miner.original_hashrate
            return degradation > 0.1  # 10%降级
        return False
    
    def _is_critical(self, miner: UserMiner) -> bool:
        """检查是否严重故障"""
        if miner.original_hashrate and miner.actual_hashrate:
            degradation = (miner.original_hashrate - miner.actual_hashrate) / miner.original_hashrate
            return degradation > 0.3  # 30%降级
        return False
