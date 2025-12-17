"""
SLO (Service Level Objective) 监控系统
追踪关键性能指标：P95 TTR、成功率、延迟分布
"""
import time
import logging
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timedelta
import statistics
from functools import wraps

from intelligence.monitoring.alert_config import AlertThresholds, AlertSeverity

logger = logging.getLogger(__name__)

class SLOMetrics:
    """SLO指标数据类"""
    def __init__(self):
        self.ttr_samples = deque(maxlen=1000)
        
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        
        self.latency_buckets = {
            '0-50ms': 0,
            '50-100ms': 0,
            '100-200ms': 0,
            '200-500ms': 0,
            '500ms+': 0
        }
        
        self.alerts = []
        
    def record_ttr(self, duration_ms: float):
        """记录重算时长"""
        self.ttr_samples.append(duration_ms)
        
        if duration_ms < 50:
            self.latency_buckets['0-50ms'] += 1
        elif duration_ms < 100:
            self.latency_buckets['50-100ms'] += 1
        elif duration_ms < 200:
            self.latency_buckets['100-200ms'] += 1
        elif duration_ms < 500:
            self.latency_buckets['200-500ms'] += 1
        else:
            self.latency_buckets['500ms+'] += 1
    
    def record_attempt(self, success: bool):
        """记录重算尝试结果"""
        self.total_attempts += 1
        if success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1
    
    def get_p95_ttr(self) -> Optional[float]:
        """计算P95 TTR"""
        if len(self.ttr_samples) < 10:
            return None
        sorted_samples = sorted(self.ttr_samples)
        p95_index = int(len(sorted_samples) * 0.95)
        return sorted_samples[p95_index]
    
    def get_success_rate(self) -> float:
        """计算成功率（%）"""
        if self.total_attempts == 0:
            return 100.0
        return (self.successful_attempts / self.total_attempts) * 100
    
    def check_slo_compliance(self) -> Dict:
        """检查SLO合规性（使用可配置阈值）"""
        p95 = self.get_p95_ttr()
        success_rate = self.get_success_rate()
        
        alerts = []
        
        if p95 is not None:
            if p95 > AlertThresholds.P95_TTR_CRITICAL:
                alerts.append({
                    'severity': AlertSeverity.CRITICAL,
                    'metric': 'p95_ttr',
                    'value': f'{p95:.0f}ms',
                    'threshold': f'{AlertThresholds.P95_TTR_CRITICAL}ms',
                    'message': f'P95 TTR ({p95:.0f}ms) exceeds CRITICAL threshold ({AlertThresholds.P95_TTR_CRITICAL}ms)'
                })
            elif p95 > AlertThresholds.P95_TTR_WARNING:
                alerts.append({
                    'severity': AlertSeverity.WARNING,
                    'metric': 'p95_ttr',
                    'value': f'{p95:.0f}ms',
                    'threshold': f'{AlertThresholds.P95_TTR_WARNING}ms',
                    'message': f'P95 TTR ({p95:.0f}ms) exceeds WARNING threshold ({AlertThresholds.P95_TTR_WARNING}ms)'
                })
        
        if success_rate < AlertThresholds.SUCCESS_RATE_CRITICAL:
            alerts.append({
                'severity': AlertSeverity.CRITICAL,
                'metric': 'success_rate',
                'value': f'{success_rate:.2f}%',
                'threshold': f'{AlertThresholds.SUCCESS_RATE_CRITICAL}%',
                'message': f'Success rate ({success_rate:.2f}%) below CRITICAL threshold ({AlertThresholds.SUCCESS_RATE_CRITICAL}%)'
            })
        elif success_rate < AlertThresholds.SUCCESS_RATE_WARNING:
            alerts.append({
                'severity': AlertSeverity.WARNING,
                'metric': 'success_rate',
                'value': f'{success_rate:.2f}%',
                'threshold': f'{AlertThresholds.SUCCESS_RATE_WARNING}%',
                'message': f'Success rate ({success_rate:.2f}%) below WARNING threshold ({AlertThresholds.SUCCESS_RATE_WARNING}%)'
            })
        
        self.alerts = alerts
        
        return {
            'compliant': len(alerts) == 0,
            'p95_ttr_ms': p95,
            'success_rate_pct': success_rate,
            'alerts': alerts,
            'thresholds': {
                'p95_ttr_warning_ms': AlertThresholds.P95_TTR_WARNING,
                'p95_ttr_critical_ms': AlertThresholds.P95_TTR_CRITICAL,
                'success_rate_warning_pct': AlertThresholds.SUCCESS_RATE_WARNING,
                'success_rate_critical_pct': AlertThresholds.SUCCESS_RATE_CRITICAL
            }
        }
    
    def get_summary(self) -> Dict:
        """获取SLO摘要"""
        p95 = self.get_p95_ttr()
        
        return {
            'p95_ttr_ms': p95,
            'p50_ttr_ms': statistics.median(self.ttr_samples) if self.ttr_samples else None,
            'avg_ttr_ms': statistics.mean(self.ttr_samples) if self.ttr_samples else None,
            'success_rate_pct': self.get_success_rate(),
            'total_attempts': self.total_attempts,
            'successful_attempts': self.successful_attempts,
            'failed_attempts': self.failed_attempts,
            'latency_distribution': self.latency_buckets.copy(),
            'sample_count': len(self.ttr_samples),
            'slo_compliance': self.check_slo_compliance()
        }

slo_metrics = SLOMetrics()

def track_recalculation(func):
    """装饰器：追踪重算性能"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            logger.error(f"Recalculation failed: {e}")
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            slo_metrics.record_ttr(duration_ms)
            slo_metrics.record_attempt(success)
            
            logger.info(f"Recalculation: {duration_ms:.0f}ms, success={success}")
    
    return wrapper
