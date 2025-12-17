"""
HashInsight Enterprise - 矿机评估服务
Miner Evaluation Service

功能:
- 效率评估 (hashrate/watt vs 型号基准)
- 健康评估 (温度/运行时间/错误率/风扇)
- 收益评估 (实际 vs 预期收益偏差)
- 综合评级 (A/B/C/D/F)

版本: 1.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from db import db

logger = logging.getLogger(__name__)


class EvaluationGrade(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class EfficiencyScore:
    score: float
    grade: str
    actual_jth: float
    baseline_jth: float
    efficiency_ratio: float
    comparison: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class HealthScore:
    score: float
    grade: str
    status: str
    
    temperature_score: float
    temperature_status: str
    temp_avg: float
    temp_max: float
    
    uptime_score: float
    uptime_hours: int
    uptime_status: str
    
    error_score: float
    hardware_errors: int
    reject_rate: float
    error_status: str
    
    fan_score: float
    fan_avg: int
    fan_status: str
    
    alerts: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return asdict(self)


@dataclass
class RevenueScore:
    score: float
    grade: str
    
    expected_daily_usd: float
    actual_daily_usd: float
    variance_pct: float
    variance_usd: float
    
    is_underperforming: bool
    performance_status: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class MinerEvaluation:
    miner_id: int
    serial_number: str
    model_name: str
    
    efficiency: EfficiencyScore
    health: HealthScore
    revenue: RevenueScore
    
    composite_score: float
    composite_grade: str
    
    rank: int
    percentile: float
    
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    
    def to_dict(self):
        return {
            'miner_id': self.miner_id,
            'serial_number': self.serial_number,
            'model_name': self.model_name,
            'efficiency': self.efficiency.to_dict(),
            'health': self.health.to_dict(),
            'revenue': self.revenue.to_dict(),
            'composite_score': self.composite_score,
            'composite_grade': self.composite_grade,
            'rank': self.rank,
            'percentile': self.percentile,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp
        }


class MinerEvaluationService:
    
    MODEL_EFFICIENCY_BASELINES = {
        'Antminer S21 XP': 13.5,
        'Antminer S21 Pro': 15.0,
        'Antminer S21': 17.5,
        'Antminer S19 XP': 21.5,
        'Antminer S19j Pro': 28.0,
        'Antminer S19 Pro': 29.5,
        'Antminer S19': 30.0,
        'Antminer T21': 19.0,
        'Antminer T19': 37.5,
        
        'Whatsminer M60S': 17.0,
        'Whatsminer M60': 18.5,
        'Whatsminer M50S++': 22.0,
        'Whatsminer M50S': 24.0,
        'Whatsminer M50': 26.0,
        'Whatsminer M30S++': 31.0,
        'Whatsminer M30S+': 34.0,
        'Whatsminer M30S': 38.0,
        
        'Avalon A1466': 21.5,
        'Avalon A1366': 25.0,
        'Avalon A1266': 28.0,
        'Avalon A1166 Pro': 30.0,
        
        'S21 XP': 13.5,
        'S21 Pro': 15.0,
        'S21': 17.5,
        'S19 XP': 21.5,
        'S19j Pro': 28.0,
        'S19 Pro': 29.5,
        'S19': 30.0,
        'T21': 19.0,
        'T19': 37.5,
        
        'M60S': 17.0,
        'M60': 18.5,
        'M50S++': 22.0,
        'M50S': 24.0,
        'M50': 26.0,
        'M30S++': 31.0,
        'M30S+': 34.0,
        'M30S': 38.0,
    }
    
    TEMP_THRESHOLDS = {
        'excellent': 65,
        'good': 75,
        'warning': 85,
        'critical': 95
    }
    
    FAN_THRESHOLDS = {
        'excellent': (4000, 6000),
        'good': (3000, 7000),
        'warning': (2000, 8000),
        'min': 1000
    }
    
    WEIGHTS = {
        'efficiency': 0.35,
        'health': 0.35,
        'revenue': 0.30
    }
    
    def __init__(self):
        logger.info("MinerEvaluationService initialized")
    
    def get_efficiency_baseline(self, model_name: str) -> float:
        for key, baseline in self.MODEL_EFFICIENCY_BASELINES.items():
            if key.lower() in model_name.lower() or model_name.lower() in key.lower():
                return baseline
        
        return 30.0
    
    def evaluate_efficiency(
        self,
        hashrate_th: float,
        power_w: float,
        model_name: str
    ) -> EfficiencyScore:
        if hashrate_th <= 0:
            return EfficiencyScore(
                score=0,
                grade='F',
                actual_jth=float('inf'),
                baseline_jth=0,
                efficiency_ratio=float('inf'),
                comparison="无法计算 - 零算力"
            )
        
        actual_jth = power_w / hashrate_th
        baseline_jth = self.get_efficiency_baseline(model_name)
        efficiency_ratio = actual_jth / baseline_jth
        
        if efficiency_ratio <= 0.95:
            score = 100
            grade = 'A'
            comparison = f"优于基准 {(1-efficiency_ratio)*100:.1f}%"
        elif efficiency_ratio <= 1.0:
            score = 95
            grade = 'A'
            comparison = f"接近基准"
        elif efficiency_ratio <= 1.1:
            score = 85
            grade = 'B'
            comparison = f"略低于基准 {(efficiency_ratio-1)*100:.1f}%"
        elif efficiency_ratio <= 1.25:
            score = 70
            grade = 'C'
            comparison = f"低于基准 {(efficiency_ratio-1)*100:.1f}%"
        elif efficiency_ratio <= 1.5:
            score = 50
            grade = 'D'
            comparison = f"显著低于基准 {(efficiency_ratio-1)*100:.1f}%"
        else:
            score = 25
            grade = 'F'
            comparison = f"严重低于基准 {(efficiency_ratio-1)*100:.1f}%"
        
        return EfficiencyScore(
            score=score,
            grade=grade,
            actual_jth=round(actual_jth, 2),
            baseline_jth=baseline_jth,
            efficiency_ratio=round(efficiency_ratio, 3),
            comparison=comparison
        )
    
    def evaluate_health(
        self,
        temp_avg: float = 0,
        temp_max: float = 0,
        fan_avg: int = 0,
        hardware_errors: int = 0,
        reject_rate: float = 0,
        uptime_seconds: int = 0,
        is_online: bool = True
    ) -> HealthScore:
        alerts = []
        
        if not is_online:
            return HealthScore(
                score=0,
                grade='F',
                status='offline',
                temperature_score=0,
                temperature_status='unknown',
                temp_avg=temp_avg,
                temp_max=temp_max,
                uptime_score=0,
                uptime_hours=0,
                uptime_status='offline',
                error_score=0,
                hardware_errors=hardware_errors,
                reject_rate=reject_rate,
                error_status='unknown',
                fan_score=0,
                fan_avg=fan_avg,
                fan_status='unknown',
                alerts=['设备离线']
            )
        
        if temp_max <= 0:
            temp_score = 70
            temp_status = 'unknown'
        elif temp_max <= self.TEMP_THRESHOLDS['excellent']:
            temp_score = 100
            temp_status = 'excellent'
        elif temp_max <= self.TEMP_THRESHOLDS['good']:
            temp_score = 85
            temp_status = 'good'
        elif temp_max <= self.TEMP_THRESHOLDS['warning']:
            temp_score = 60
            temp_status = 'warning'
            alerts.append(f'温度偏高: {temp_max}°C')
        elif temp_max <= self.TEMP_THRESHOLDS['critical']:
            temp_score = 30
            temp_status = 'critical'
            alerts.append(f'温度危险: {temp_max}°C')
        else:
            temp_score = 10
            temp_status = 'critical'
            alerts.append(f'温度严重过高: {temp_max}°C')
        
        uptime_hours = uptime_seconds // 3600
        if uptime_hours >= 720:
            uptime_score = 100
            uptime_status = 'excellent'
        elif uptime_hours >= 168:
            uptime_score = 90
            uptime_status = 'good'
        elif uptime_hours >= 24:
            uptime_score = 75
            uptime_status = 'normal'
        elif uptime_hours >= 1:
            uptime_score = 50
            uptime_status = 'recent_restart'
            alerts.append(f'近期重启 (运行{uptime_hours}小时)')
        else:
            uptime_score = 30
            uptime_status = 'just_started'
        
        error_score = 100
        error_status = 'excellent'
        
        if reject_rate > 5:
            error_score -= 40
            error_status = 'critical'
            alerts.append(f'拒绝率过高: {reject_rate:.1f}%')
        elif reject_rate > 2:
            error_score -= 20
            error_status = 'warning'
            alerts.append(f'拒绝率偏高: {reject_rate:.1f}%')
        elif reject_rate > 0.5:
            error_score -= 10
            error_status = 'normal'
        
        if hardware_errors > 100:
            error_score -= 30
            if error_status != 'critical':
                error_status = 'warning'
            alerts.append(f'硬件错误多: {hardware_errors}')
        elif hardware_errors > 20:
            error_score -= 15
        elif hardware_errors > 5:
            error_score -= 5
        
        error_score = max(0, error_score)
        
        if fan_avg <= 0:
            fan_score = 70
            fan_status = 'unknown'
        elif fan_avg < self.FAN_THRESHOLDS['min']:
            fan_score = 20
            fan_status = 'critical'
            alerts.append(f'风扇转速异常低: {fan_avg} RPM')
        elif self.FAN_THRESHOLDS['excellent'][0] <= fan_avg <= self.FAN_THRESHOLDS['excellent'][1]:
            fan_score = 100
            fan_status = 'excellent'
        elif self.FAN_THRESHOLDS['good'][0] <= fan_avg <= self.FAN_THRESHOLDS['good'][1]:
            fan_score = 85
            fan_status = 'good'
        elif self.FAN_THRESHOLDS['warning'][0] <= fan_avg <= self.FAN_THRESHOLDS['warning'][1]:
            fan_score = 60
            fan_status = 'warning'
        else:
            fan_score = 40
            fan_status = 'abnormal'
            alerts.append(f'风扇转速异常: {fan_avg} RPM')
        
        total_score = (temp_score * 0.35 + uptime_score * 0.15 + 
                      error_score * 0.30 + fan_score * 0.20)
        
        if total_score >= 90:
            grade = 'A'
            status = 'healthy'
        elif total_score >= 75:
            grade = 'B'
            status = 'healthy'
        elif total_score >= 60:
            grade = 'C'
            status = 'warning'
        elif total_score >= 40:
            grade = 'D'
            status = 'warning'
        else:
            grade = 'F'
            status = 'critical'
        
        return HealthScore(
            score=round(total_score, 1),
            grade=grade,
            status=status,
            temperature_score=temp_score,
            temperature_status=temp_status,
            temp_avg=temp_avg,
            temp_max=temp_max,
            uptime_score=uptime_score,
            uptime_hours=uptime_hours,
            uptime_status=uptime_status,
            error_score=error_score,
            hardware_errors=hardware_errors,
            reject_rate=reject_rate,
            error_status=error_status,
            fan_score=fan_score,
            fan_avg=fan_avg,
            fan_status=fan_status,
            alerts=alerts
        )
    
    def evaluate_revenue(
        self,
        expected_daily_usd: float,
        actual_hashrate_th: float,
        rated_hashrate_th: float,
        power_ratio: float = 1.0
    ) -> RevenueScore:
        if rated_hashrate_th <= 0 or expected_daily_usd <= 0:
            return RevenueScore(
                score=0,
                grade='F',
                expected_daily_usd=0,
                actual_daily_usd=0,
                variance_pct=0,
                variance_usd=0,
                is_underperforming=True,
                performance_status='无法计算'
            )
        
        performance_ratio = (actual_hashrate_th / rated_hashrate_th) * power_ratio
        actual_daily_usd = expected_daily_usd * performance_ratio
        
        variance_pct = (performance_ratio - 1) * 100
        variance_usd = actual_daily_usd - expected_daily_usd
        
        if performance_ratio >= 1.0:
            score = 100
            grade = 'A'
            performance_status = f'超出预期 {variance_pct:.1f}%'
            is_underperforming = False
        elif performance_ratio >= 0.95:
            score = 90
            grade = 'A'
            performance_status = '接近预期'
            is_underperforming = False
        elif performance_ratio >= 0.85:
            score = 75
            grade = 'B'
            performance_status = f'略低于预期 {abs(variance_pct):.1f}%'
            is_underperforming = True
        elif performance_ratio >= 0.70:
            score = 55
            grade = 'C'
            performance_status = f'低于预期 {abs(variance_pct):.1f}%'
            is_underperforming = True
        elif performance_ratio >= 0.50:
            score = 35
            grade = 'D'
            performance_status = f'显著低于预期 {abs(variance_pct):.1f}%'
            is_underperforming = True
        else:
            score = 15
            grade = 'F'
            performance_status = f'严重低于预期 {abs(variance_pct):.1f}%'
            is_underperforming = True
        
        return RevenueScore(
            score=score,
            grade=grade,
            expected_daily_usd=round(expected_daily_usd, 2),
            actual_daily_usd=round(actual_daily_usd, 2),
            variance_pct=round(variance_pct, 1),
            variance_usd=round(variance_usd, 2),
            is_underperforming=is_underperforming,
            performance_status=performance_status
        )
    
    def generate_recommendations(
        self,
        efficiency: EfficiencyScore,
        health: HealthScore,
        revenue: RevenueScore
    ) -> List[str]:
        recommendations = []
        
        if efficiency.grade in ['D', 'F']:
            if efficiency.efficiency_ratio > 1.3:
                recommendations.append("检查矿机固件版本，可能需要更新")
                recommendations.append("清洁散热系统，可能积灰影响效率")
        
        for alert in health.alerts:
            if '温度' in alert:
                recommendations.append("检查风扇和散热系统")
                recommendations.append("确认环境温度是否过高")
                break
        
        if health.fan_status in ['critical', 'abnormal']:
            recommendations.append("检查风扇是否正常工作")
        
        if health.error_status in ['critical', 'warning']:
            if health.reject_rate > 2:
                recommendations.append("检查网络连接稳定性")
                recommendations.append("确认矿池配置是否正确")
            if health.hardware_errors > 20:
                recommendations.append("检查电源供应是否稳定")
                recommendations.append("可能需要更换算力板")
        
        if revenue.is_underperforming and revenue.variance_pct < -15:
            recommendations.append("矿机表现显著低于预期，建议全面检查")
        
        if efficiency.grade in ['A', 'B'] and health.grade in ['A', 'B']:
            if not recommendations:
                recommendations.append("矿机状态良好，继续保持当前配置")
        
        return recommendations[:5]
    
    def evaluate_miner(
        self,
        miner_id: int,
        serial_number: str,
        model_name: str,
        actual_hashrate_th: float,
        rated_hashrate_th: float,
        actual_power_w: float,
        rated_power_w: float,
        electricity_rate: float,
        temp_avg: float = 0,
        temp_max: float = 0,
        fan_avg: int = 0,
        hardware_errors: int = 0,
        reject_rate: float = 0,
        uptime_seconds: int = 0,
        is_online: bool = True,
        expected_daily_usd: float = 0
    ) -> MinerEvaluation:
        efficiency = self.evaluate_efficiency(
            hashrate_th=actual_hashrate_th,
            power_w=actual_power_w,
            model_name=model_name
        )
        
        health = self.evaluate_health(
            temp_avg=temp_avg,
            temp_max=temp_max,
            fan_avg=fan_avg,
            hardware_errors=hardware_errors,
            reject_rate=reject_rate,
            uptime_seconds=uptime_seconds,
            is_online=is_online
        )
        
        power_ratio = actual_power_w / rated_power_w if rated_power_w > 0 else 1.0
        revenue = self.evaluate_revenue(
            expected_daily_usd=expected_daily_usd,
            actual_hashrate_th=actual_hashrate_th,
            rated_hashrate_th=rated_hashrate_th,
            power_ratio=min(1.0, power_ratio)
        )
        
        composite_score = (
            efficiency.score * self.WEIGHTS['efficiency'] +
            health.score * self.WEIGHTS['health'] +
            revenue.score * self.WEIGHTS['revenue']
        )
        
        if composite_score >= 90:
            composite_grade = 'A'
        elif composite_score >= 75:
            composite_grade = 'B'
        elif composite_score >= 60:
            composite_grade = 'C'
        elif composite_score >= 40:
            composite_grade = 'D'
        else:
            composite_grade = 'F'
        
        recommendations = self.generate_recommendations(efficiency, health, revenue)
        
        return MinerEvaluation(
            miner_id=miner_id,
            serial_number=serial_number,
            model_name=model_name,
            efficiency=efficiency,
            health=health,
            revenue=revenue,
            composite_score=round(composite_score, 1),
            composite_grade=composite_grade,
            rank=0,
            percentile=0,
            recommendations=recommendations
        )
    
    def evaluate_site_miners(self, site_id: int) -> List[MinerEvaluation]:
        try:
            from models import HostingMiner, HostingSite, MinerModel
            from services.hosting_revenue_service import get_revenue_service
            
            site = HostingSite.query.get(site_id)
            if not site:
                logger.warning(f"站点不存在: {site_id}")
                return []
            
            miners = HostingMiner.query.filter_by(site_id=site_id).all()
            revenue_service = get_revenue_service()
            
            evaluations = []
            
            for miner in miners:
                model = miner.miner_model
                model_name = model.model_name if model else "Unknown"
                rated_hashrate = model.hashrate if model else miner.actual_hashrate
                rated_power = model.power_consumption if model else miner.actual_power
                
                revenue_metrics = revenue_service.calculate_miner_revenue(
                    miner_id=miner.id,
                    serial_number=miner.serial_number,
                    model_name=model_name,
                    hashrate_th=rated_hashrate,
                    power_w=rated_power,
                    electricity_rate=site.electricity_rate,
                    health_score=miner.health_score or 100
                )
                
                evaluation = self.evaluate_miner(
                    miner_id=miner.id,
                    serial_number=miner.serial_number,
                    model_name=model_name,
                    actual_hashrate_th=miner.actual_hashrate or 0,
                    rated_hashrate_th=rated_hashrate,
                    actual_power_w=miner.actual_power or 0,
                    rated_power_w=rated_power,
                    electricity_rate=site.electricity_rate,
                    temp_avg=miner.temperature_avg or 0,
                    temp_max=miner.temperature_max or 0,
                    fan_avg=miner.fan_avg or 0,
                    hardware_errors=miner.hardware_errors or 0,
                    reject_rate=miner.reject_rate or 0,
                    uptime_seconds=miner.uptime_seconds or 0,
                    is_online=miner.status == 'active' or miner.cgminer_online,
                    expected_daily_usd=revenue_metrics.daily_usd
                )
                
                evaluations.append(evaluation)
            
            evaluations.sort(key=lambda e: e.composite_score, reverse=True)
            
            total = len(evaluations)
            for i, evaluation in enumerate(evaluations):
                evaluation.rank = i + 1
                evaluation.percentile = round((total - i) / total * 100, 1) if total > 0 else 0
            
            return evaluations
            
        except Exception as e:
            logger.error(f"评估站点矿机失败: {e}")
            return []
    
    def get_site_evaluation_summary(self, site_id: int) -> Dict[str, Any]:
        evaluations = self.evaluate_site_miners(site_id)
        
        if not evaluations:
            return {
                'site_id': site_id,
                'total_miners': 0,
                'grade_distribution': {},
                'avg_scores': {},
                'top_performers': [],
                'needs_attention': []
            }
        
        grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        efficiency_sum = health_sum = revenue_sum = composite_sum = 0
        
        for e in evaluations:
            grade_counts[e.composite_grade] += 1
            efficiency_sum += e.efficiency.score
            health_sum += e.health.score
            revenue_sum += e.revenue.score
            composite_sum += e.composite_score
        
        total = len(evaluations)
        
        return {
            'site_id': site_id,
            'total_miners': total,
            'grade_distribution': grade_counts,
            'grade_percentages': {
                grade: round(count / total * 100, 1)
                for grade, count in grade_counts.items()
            },
            'avg_scores': {
                'efficiency': round(efficiency_sum / total, 1),
                'health': round(health_sum / total, 1),
                'revenue': round(revenue_sum / total, 1),
                'composite': round(composite_sum / total, 1)
            },
            'top_performers': [e.to_dict() for e in evaluations[:5]],
            'needs_attention': [
                e.to_dict() for e in evaluations 
                if e.composite_grade in ['D', 'F']
            ][:10]
        }


_evaluation_service: Optional[MinerEvaluationService] = None

def get_evaluation_service() -> MinerEvaluationService:
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = MinerEvaluationService()
    return _evaluation_service
