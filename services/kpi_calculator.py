"""
KPI Calculator Service for Hosting OKR Dashboard

Calculates 9 key performance indicators:
O1: Energy Cost Optimization
  - KR1: Total electricity cost reduction
  - KR2: Cost per TH/s reduction
  - KR3: Peak hour usage ratio reduction
  - KR4: Curtailment execution accuracy
  - KR5: Uptime target achievement

O2: Reduce Broken Rate by Risk Control
  - KR6: High temperature events reduction
  - KR7: Critical board rate reduction
  - KR8: MTTR (Mean Time To Resolution) improvement
  - KR9: Unplanned offline hours reduction
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app import db

logger = logging.getLogger(__name__)


class KPICalculator:
    """KPI 计算器服务"""
    
    def __init__(self, site_id: int, start_date: datetime = None, end_date: datetime = None):
        self.site_id = site_id
        self.end_date = end_date or datetime.utcnow()
        self.start_date = start_date or (self.end_date - timedelta(days=7))
        
    def calculate_all_kpis(self, baseline_start: datetime = None, baseline_end: datetime = None) -> dict:
        """计算所有 KPI 指标
        
        Args:
            baseline_start: 基准期开始时间（用于对比）
            baseline_end: 基准期结束时间
        
        Returns:
            包含所有 KPI 的字典
        """
        if not baseline_start:
            baseline_start = self.start_date - timedelta(days=7)
        if not baseline_end:
            baseline_end = self.start_date
        
        return {
            'period': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat(),
                'baseline_start': baseline_start.isoformat(),
                'baseline_end': baseline_end.isoformat()
            },
            'o1_energy_optimization': {
                'kr1_total_cost': self._calculate_kr1_total_cost(baseline_start, baseline_end),
                'kr2_cost_per_th': self._calculate_kr2_cost_per_th(baseline_start, baseline_end),
                'kr3_peak_usage': self._calculate_kr3_peak_usage(baseline_start, baseline_end),
                'kr4_curtailment_accuracy': self._calculate_kr4_curtailment_accuracy(),
                'kr5_uptime': self._calculate_kr5_uptime()
            },
            'o2_risk_control': {
                'kr6_high_temp': self._calculate_kr6_high_temp(baseline_start, baseline_end),
                'kr7_critical_board': self._calculate_kr7_critical_board(baseline_start, baseline_end),
                'kr8_mttr': self._calculate_kr8_mttr(baseline_start, baseline_end),
                'kr9_unplanned_offline': self._calculate_kr9_unplanned_offline(baseline_start, baseline_end)
            },
            'calculated_at': datetime.utcnow().isoformat()
        }
    
    def _calculate_kr1_total_cost(self, baseline_start: datetime, baseline_end: datetime) -> dict:
        """KR1: 总电费下降
        
        Cost_USD = Σ(kWh * $/kWh)
        目标: -5% 到 -10%
        """
        try:
            from api.collector_api import MinerTelemetryHistory
            from models import HostingSite
            
            site = HostingSite.query.get(self.site_id)
            electricity_rate = site.electricity_rate if site and site.electricity_rate else 0.08
            
            current_kwh = self._get_total_kwh(self.start_date, self.end_date)
            baseline_kwh = self._get_total_kwh(baseline_start, baseline_end)
            
            current_cost = current_kwh * electricity_rate
            baseline_cost = baseline_kwh * electricity_rate
            
            change_pct = 0
            if baseline_cost > 0:
                change_pct = ((current_cost - baseline_cost) / baseline_cost) * 100
            
            target_min = -10
            target_max = -5
            status = 'good' if change_pct <= target_max else ('warning' if change_pct <= 0 else 'critical')
            
            return {
                'current_value': round(current_cost, 2),
                'baseline_value': round(baseline_cost, 2),
                'change_pct': round(change_pct, 2),
                'target_min': target_min,
                'target_max': target_max,
                'status': status,
                'unit': 'USD'
            }
        except Exception as e:
            logger.error(f"KR1 calculation error: {e}")
            return self._empty_kpi_result('USD')
    
    def _calculate_kr2_cost_per_th(self, baseline_start: datetime, baseline_end: datetime) -> dict:
        """KR2: 单位算力电费下降
        
        Cost_per_TH = Cost_USD / Σ(TH*s)
        目标: -5%
        """
        try:
            from models import HostingSite
            
            site = HostingSite.query.get(self.site_id)
            electricity_rate = site.electricity_rate if site and site.electricity_rate else 0.08
            
            current_kwh = self._get_total_kwh(self.start_date, self.end_date)
            current_th = self._get_total_hashrate_hours(self.start_date, self.end_date)
            baseline_kwh = self._get_total_kwh(baseline_start, baseline_end)
            baseline_th = self._get_total_hashrate_hours(baseline_start, baseline_end)
            
            current_cost_per_th = (current_kwh * electricity_rate / current_th) if current_th > 0 else 0
            baseline_cost_per_th = (baseline_kwh * electricity_rate / baseline_th) if baseline_th > 0 else 0
            
            change_pct = 0
            if baseline_cost_per_th > 0:
                change_pct = ((current_cost_per_th - baseline_cost_per_th) / baseline_cost_per_th) * 100
            
            target = -5
            status = 'good' if change_pct <= target else ('warning' if change_pct <= 0 else 'critical')
            
            return {
                'current_value': round(current_cost_per_th, 4),
                'baseline_value': round(baseline_cost_per_th, 4),
                'change_pct': round(change_pct, 2),
                'target': target,
                'status': status,
                'unit': 'USD/TH·h'
            }
        except Exception as e:
            logger.error(f"KR2 calculation error: {e}")
            return self._empty_kpi_result('USD/TH·h')
    
    def _calculate_kr3_peak_usage(self, baseline_start: datetime, baseline_end: datetime) -> dict:
        """KR3: 峰时段用电占比下降
        
        Peak_kWh% = Peak_kWh / Total_kWh
        目标: -10% 相对下降
        """
        try:
            current_peak_ratio = self._get_peak_usage_ratio(self.start_date, self.end_date)
            baseline_peak_ratio = self._get_peak_usage_ratio(baseline_start, baseline_end)
            
            change_pct = 0
            if baseline_peak_ratio > 0:
                change_pct = ((current_peak_ratio - baseline_peak_ratio) / baseline_peak_ratio) * 100
            
            target = -10
            status = 'good' if change_pct <= target else ('warning' if change_pct <= 0 else 'critical')
            
            return {
                'current_value': round(current_peak_ratio * 100, 2),
                'baseline_value': round(baseline_peak_ratio * 100, 2),
                'change_pct': round(change_pct, 2),
                'target': target,
                'status': status,
                'unit': '%'
            }
        except Exception as e:
            logger.error(f"KR3 calculation error: {e}")
            return self._empty_kpi_result('%')
    
    def _calculate_kr4_curtailment_accuracy(self) -> dict:
        """KR4: 限电执行精度
        
        Accuracy = 1 - |Actual_Reduction - Target_Reduction| / Target_Reduction
        目标: ≥95%
        """
        try:
            from models import CurtailmentExecution, ExecutionStatus
            
            executions = CurtailmentExecution.query.filter(
                CurtailmentExecution.site_id == self.site_id,
                CurtailmentExecution.executed_at >= self.start_date,
                CurtailmentExecution.executed_at <= self.end_date,
                CurtailmentExecution.status == ExecutionStatus.COMPLETED
            ).all()
            
            if not executions:
                return {
                    'current_value': 100,
                    'target': 95,
                    'status': 'good',
                    'unit': '%',
                    'sample_count': 0
                }
            
            accuracies = []
            for exe in executions:
                if exe.target_reduction_kw and exe.target_reduction_kw > 0:
                    actual = exe.actual_reduction_kw or 0
                    target = exe.target_reduction_kw
                    accuracy = max(0, 1 - abs(actual - target) / target)
                    accuracies.append(accuracy)
            
            avg_accuracy = sum(accuracies) / len(accuracies) * 100 if accuracies else 100
            
            target = 95
            status = 'good' if avg_accuracy >= target else ('warning' if avg_accuracy >= 90 else 'critical')
            
            return {
                'current_value': round(avg_accuracy, 2),
                'target': target,
                'status': status,
                'unit': '%',
                'sample_count': len(accuracies)
            }
        except Exception as e:
            logger.error(f"KR4 calculation error: {e}")
            return self._empty_kpi_result('%')
    
    def _calculate_kr5_uptime(self) -> dict:
        """KR5: Uptime 达标
        
        Uptime = Online_miner_hours / Total_miner_hours
        目标: ≥85%
        """
        try:
            from api.collector_api import MinerTelemetryHistory
            
            total_records = db.session.query(func.count(MinerTelemetryHistory.id)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= self.start_date,
                MinerTelemetryHistory.timestamp <= self.end_date
            ).scalar() or 0
            
            online_records = db.session.query(func.count(MinerTelemetryHistory.id)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= self.start_date,
                MinerTelemetryHistory.timestamp <= self.end_date,
                MinerTelemetryHistory.online == True
            ).scalar() or 0
            
            uptime = (online_records / total_records * 100) if total_records > 0 else 0
            
            target = 85
            status = 'good' if uptime >= target else ('warning' if uptime >= 75 else 'critical')
            
            return {
                'current_value': round(uptime, 2),
                'target': target,
                'status': status,
                'unit': '%',
                'online_records': online_records,
                'total_records': total_records
            }
        except Exception as e:
            logger.error(f"KR5 calculation error: {e}")
            return self._empty_kpi_result('%')
    
    def _calculate_kr6_high_temp(self, baseline_start: datetime, baseline_end: datetime) -> dict:
        """KR6: 高温事件下降
        
        HighTemp_Minutes (>75°C / >85°C)
        目标: -30%
        """
        try:
            from api.collector_api import MinerTelemetryHistory
            
            current_high_temp = db.session.query(func.count(MinerTelemetryHistory.id)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= self.start_date,
                MinerTelemetryHistory.timestamp <= self.end_date,
                MinerTelemetryHistory.temperature_max > 75
            ).scalar() or 0
            
            baseline_high_temp = db.session.query(func.count(MinerTelemetryHistory.id)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= baseline_start,
                MinerTelemetryHistory.timestamp <= baseline_end,
                MinerTelemetryHistory.temperature_max > 75
            ).scalar() or 0
            
            change_pct = 0
            if baseline_high_temp > 0:
                change_pct = ((current_high_temp - baseline_high_temp) / baseline_high_temp) * 100
            
            target = -30
            status = 'good' if change_pct <= target else ('warning' if change_pct <= 0 else 'critical')
            
            return {
                'current_value': current_high_temp,
                'baseline_value': baseline_high_temp,
                'change_pct': round(change_pct, 2),
                'target': target,
                'status': status,
                'unit': 'events'
            }
        except Exception as e:
            logger.error(f"KR6 calculation error: {e}")
            return self._empty_kpi_result('events')
    
    def _calculate_kr7_critical_board(self, baseline_start: datetime, baseline_end: datetime) -> dict:
        """KR7: 板卡 CRITICAL 率下降
        
        Critical_Board_Minutes% (temp>90°C 或 chips_ok/chips_total<95%)
        目标: -20%
        """
        try:
            from api.collector_api import MinerTelemetryHistory
            
            current_critical = db.session.query(func.count(MinerTelemetryHistory.id)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= self.start_date,
                MinerTelemetryHistory.timestamp <= self.end_date,
                or_(
                    MinerTelemetryHistory.temperature_max > 90,
                    and_(
                        MinerTelemetryHistory.boards_total > 0,
                        MinerTelemetryHistory.boards_healthy < MinerTelemetryHistory.boards_total * 0.95
                    )
                )
            ).scalar() or 0
            
            baseline_critical = db.session.query(func.count(MinerTelemetryHistory.id)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= baseline_start,
                MinerTelemetryHistory.timestamp <= baseline_end,
                or_(
                    MinerTelemetryHistory.temperature_max > 90,
                    and_(
                        MinerTelemetryHistory.boards_total > 0,
                        MinerTelemetryHistory.boards_healthy < MinerTelemetryHistory.boards_total * 0.95
                    )
                )
            ).scalar() or 0
            
            change_pct = 0
            if baseline_critical > 0:
                change_pct = ((current_critical - baseline_critical) / baseline_critical) * 100
            
            target = -20
            status = 'good' if change_pct <= target else ('warning' if change_pct <= 0 else 'critical')
            
            return {
                'current_value': current_critical,
                'baseline_value': baseline_critical,
                'change_pct': round(change_pct, 2),
                'target': target,
                'status': status,
                'unit': 'events'
            }
        except Exception as e:
            logger.error(f"KR7 calculation error: {e}")
            return self._empty_kpi_result('events')
    
    def _calculate_kr8_mttr(self, baseline_start: datetime, baseline_end: datetime) -> dict:
        """KR8: 异常处置时效提升
        
        MTTR = Avg(resolved_at - created_at)
        目标: -25%
        """
        try:
            from models import HostingTicket
            
            current_tickets = HostingTicket.query.filter(
                HostingTicket.site_id == self.site_id,
                HostingTicket.created_at >= self.start_date,
                HostingTicket.created_at <= self.end_date,
                HostingTicket.resolved_at.isnot(None)
            ).all()
            
            baseline_tickets = HostingTicket.query.filter(
                HostingTicket.site_id == self.site_id,
                HostingTicket.created_at >= baseline_start,
                HostingTicket.created_at <= baseline_end,
                HostingTicket.resolved_at.isnot(None)
            ).all()
            
            def avg_resolution_hours(tickets):
                if not tickets:
                    return 0
                total_hours = sum((t.resolved_at - t.created_at).total_seconds() / 3600 for t in tickets)
                return total_hours / len(tickets)
            
            current_mttr = avg_resolution_hours(current_tickets)
            baseline_mttr = avg_resolution_hours(baseline_tickets)
            
            change_pct = 0
            if baseline_mttr > 0:
                change_pct = ((current_mttr - baseline_mttr) / baseline_mttr) * 100
            
            target = -25
            status = 'good' if change_pct <= target else ('warning' if change_pct <= 0 else 'critical')
            
            return {
                'current_value': round(current_mttr, 2),
                'baseline_value': round(baseline_mttr, 2),
                'change_pct': round(change_pct, 2),
                'target': target,
                'status': status,
                'unit': 'hours',
                'sample_count': len(current_tickets)
            }
        except Exception as e:
            logger.error(f"KR8 calculation error: {e}")
            return self._empty_kpi_result('hours')
    
    def _calculate_kr9_unplanned_offline(self, baseline_start: datetime, baseline_end: datetime) -> dict:
        """KR9: 非计划离线减少
        
        Unplanned_Offline_Hours（非计划窗口的离线时长）
        目标: -15%
        """
        try:
            from api.collector_api import MinerTelemetryHistory
            
            current_offline = db.session.query(func.count(MinerTelemetryHistory.id)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= self.start_date,
                MinerTelemetryHistory.timestamp <= self.end_date,
                MinerTelemetryHistory.online == False
            ).scalar() or 0
            
            baseline_offline = db.session.query(func.count(MinerTelemetryHistory.id)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= baseline_start,
                MinerTelemetryHistory.timestamp <= baseline_end,
                MinerTelemetryHistory.online == False
            ).scalar() or 0
            
            current_hours = current_offline * 5 / 60
            baseline_hours = baseline_offline * 5 / 60
            
            change_pct = 0
            if baseline_hours > 0:
                change_pct = ((current_hours - baseline_hours) / baseline_hours) * 100
            
            target = -15
            status = 'good' if change_pct <= target else ('warning' if change_pct <= 0 else 'critical')
            
            return {
                'current_value': round(current_hours, 2),
                'baseline_value': round(baseline_hours, 2),
                'change_pct': round(change_pct, 2),
                'target': target,
                'status': status,
                'unit': 'hours'
            }
        except Exception as e:
            logger.error(f"KR9 calculation error: {e}")
            return self._empty_kpi_result('hours')
    
    def _get_total_kwh(self, start: datetime, end: datetime) -> float:
        """获取时间段内总用电量 (kWh)"""
        try:
            from api.collector_api import MinerTelemetryHistory
            
            total_power = db.session.query(func.sum(MinerTelemetryHistory.power_consumption)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= start,
                MinerTelemetryHistory.timestamp <= end
            ).scalar() or 0
            
            return total_power * 5 / 60 / 1000
        except Exception as e:
            logger.error(f"Total kWh calculation error: {e}")
            return 0
    
    def _get_total_hashrate_hours(self, start: datetime, end: datetime) -> float:
        """获取时间段内总算力小时 (TH·h)"""
        try:
            from api.collector_api import MinerTelemetryHistory
            
            total_hashrate = db.session.query(func.sum(MinerTelemetryHistory.hashrate_ghs)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= start,
                MinerTelemetryHistory.timestamp <= end
            ).scalar() or 0
            
            return total_hashrate / 1000 * 5 / 60
        except Exception as e:
            logger.error(f"Total hashrate hours calculation error: {e}")
            return 0
    
    def _get_peak_usage_ratio(self, start: datetime, end: datetime) -> float:
        """获取峰时段用电占比 (9:00-21:00 为峰时)"""
        try:
            from api.collector_api import MinerTelemetryHistory
            
            peak_power = db.session.query(func.sum(MinerTelemetryHistory.power_consumption)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= start,
                MinerTelemetryHistory.timestamp <= end,
                func.extract('hour', MinerTelemetryHistory.timestamp).between(9, 20)
            ).scalar() or 0
            
            total_power = db.session.query(func.sum(MinerTelemetryHistory.power_consumption)).filter(
                MinerTelemetryHistory.site_id == self.site_id,
                MinerTelemetryHistory.timestamp >= start,
                MinerTelemetryHistory.timestamp <= end
            ).scalar() or 0
            
            return peak_power / total_power if total_power > 0 else 0
        except Exception as e:
            logger.error(f"Peak usage ratio calculation error: {e}")
            return 0
    
    def _empty_kpi_result(self, unit: str) -> dict:
        """返回空的 KPI 结果"""
        return {
            'current_value': 0,
            'baseline_value': 0,
            'change_pct': 0,
            'target': 0,
            'status': 'unknown',
            'unit': unit
        }


def get_site_kpis(site_id: int, period_days: int = 7) -> dict:
    """获取站点 KPI 数据的便捷函数
    
    Args:
        site_id: 站点 ID
        period_days: 统计周期（天）
    
    Returns:
        KPI 数据字典
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    calculator = KPICalculator(site_id, start_date, end_date)
    return calculator.calculate_all_kpis()
