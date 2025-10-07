"""
告警配置和阈值管理
"""
import os

class AlertThresholds:
    P95_TTR_WARNING = int(os.getenv('ALERT_P95_TTR_WARNING', '5000'))
    P95_TTR_CRITICAL = int(os.getenv('ALERT_P95_TTR_CRITICAL', '10000'))
    
    SUCCESS_RATE_WARNING = float(os.getenv('ALERT_SUCCESS_RATE_WARNING', '99.9'))
    SUCCESS_RATE_CRITICAL = float(os.getenv('ALERT_SUCCESS_RATE_CRITICAL', '99.0'))
    
    CACHE_HIT_RATE_WARNING = float(os.getenv('ALERT_CACHE_HIT_RATE_WARNING', '80'))
    CACHE_HIT_RATE_CRITICAL = float(os.getenv('ALERT_CACHE_HIT_RATE_CRITICAL', '50'))

class AlertSeverity:
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'
