#!/usr/bin/env python3
"""
SLO监控系统 - Service Level Objectives Monitoring System
SLO定义、追踪、错误预算管理

目标：
- 可用性SLO ≥99.95% (错误预算≤21.6分钟/月)
- 延迟SLO p95 ≤250ms  
- 错误率SLO ≤0.1%

Objectives:
- Availability SLO ≥99.95% (Error budget ≤21.6 min/month)
- Latency SLO p95 ≤250ms
- Error Rate SLO ≤0.1%
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SLOMetric:
    """SLO指标定义"""
    name: str
    target: float  # 目标值 (e.g., 99.95 for 99.95%)
    current: float = 0.0  # 当前值
    measurement_window_minutes: int = 30  # 测量窗口（分钟）
    
    def meets_target(self) -> bool:
        """检查是否满足目标"""
        return self.current >= self.target
    
    def compliance_percentage(self) -> float:
        """计算合规百分比"""
        if self.target == 0:
            return 100.0
        return min((self.current / self.target) * 100, 100.0)


@dataclass  
class ErrorBudget:
    """错误预算"""
    total_minutes: float  # 总预算时间（分钟）
    consumed_minutes: float = 0.0  # 已消耗时间（分钟）
    period: str = "monthly"  # 周期
    
    def remaining_minutes(self) -> float:
        """剩余预算（分钟）"""
        return max(self.total_minutes - self.consumed_minutes, 0.0)
    
    def remaining_percentage(self) -> float:
        """剩余预算百分比"""
        if self.total_minutes == 0:
            return 0.0
        return (self.remaining_minutes() / self.total_minutes) * 100
    
    def is_exhausted(self) -> bool:
        """预算是否耗尽"""
        return self.remaining_minutes() <= 0


class SLOManager:
    """SLO管理器"""
    
    def __init__(self, measurement_window_minutes: int = 30):
        """
        初始化SLO管理器
        
        Parameters:
        -----------
        measurement_window_minutes : int
            测量窗口时间（分钟）
        """
        self.measurement_window = measurement_window_minutes
        
        # 定义核心SLO
        self.slos = {
            'availability': SLOMetric(
                name='Availability',
                target=99.95,
                measurement_window_minutes=measurement_window_minutes
            ),
            'latency_p95': SLOMetric(
                name='Latency P95',
                target=250.0,  # 毫秒
                measurement_window_minutes=measurement_window_minutes
            ),
            'error_rate': SLOMetric(
                name='Error Rate',
                target=0.1,  # 0.1%
                measurement_window_minutes=measurement_window_minutes
            )
        }
        
        # 错误预算（99.95% = 21.6分钟/月）
        minutes_per_month = 30 * 24 * 60  # 43,200分钟
        error_budget_minutes = minutes_per_month * (1 - 0.9995)  # 21.6分钟
        
        self.error_budget = ErrorBudget(
            total_minutes=error_budget_minutes,
            period="monthly"
        )
        
        # 数据收集
        self.request_history = deque(maxlen=10000)
        self.uptime_history = deque(maxlen=1000)
        
        logger.info(f"SLO管理器已初始化 (测量窗口: {measurement_window_minutes}分钟)")
    
    def record_request(self, success: bool, response_time_ms: float, 
                      timestamp: Optional[datetime] = None):
        """
        记录请求
        
        Parameters:
        -----------
        success : bool
            请求是否成功
        response_time_ms : float
            响应时间（毫秒）
        timestamp : datetime
            时间戳
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.request_history.append({
            'timestamp': timestamp,
            'success': success,
            'response_time_ms': response_time_ms
        })
        
        # 更新错误预算（如果请求失败）
        if not success:
            # 假设每个失败请求消耗平均1秒的预算
            self.error_budget.consumed_minutes += 1.0 / 60.0
    
    def record_uptime(self, is_up: bool, timestamp: Optional[datetime] = None):
        """
        记录系统运行状态
        
        Parameters:
        -----------
        is_up : bool
            系统是否运行
        timestamp : datetime
            时间戳
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.uptime_history.append({
            'timestamp': timestamp,
            'is_up': is_up
        })
    
    def calculate_availability(self, window_minutes: Optional[int] = None) -> float:
        """
        计算可用性
        
        Parameters:
        -----------
        window_minutes : int
            测量窗口（分钟）
            
        Returns:
        --------
        float : 可用性百分比
        """
        window_minutes = window_minutes or self.measurement_window
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        recent_uptime = [
            record for record in self.uptime_history
            if record['timestamp'] >= cutoff_time
        ]
        
        if not recent_uptime:
            return 100.0
        
        up_count = sum(1 for record in recent_uptime if record['is_up'])
        total_count = len(recent_uptime)
        
        availability = (up_count / total_count) * 100
        self.slos['availability'].current = availability
        
        return availability
    
    def calculate_latency_p95(self, window_minutes: Optional[int] = None) -> float:
        """
        计算P95延迟
        
        Parameters:
        -----------
        window_minutes : int
            测量窗口（分钟）
            
        Returns:
        --------
        float : P95延迟（毫秒）
        """
        window_minutes = window_minutes or self.measurement_window
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        recent_requests = [
            record for record in self.request_history
            if record['timestamp'] >= cutoff_time
        ]
        
        if not recent_requests:
            return 0.0
        
        response_times = [req['response_time_ms'] for req in recent_requests]
        p95 = np.percentile(response_times, 95)
        
        self.slos['latency_p95'].current = p95
        
        return float(p95)
    
    def calculate_error_rate(self, window_minutes: Optional[int] = None) -> float:
        """
        计算错误率
        
        Parameters:
        -----------
        window_minutes : int
            测量窗口（分钟）
            
        Returns:
        --------
        float : 错误率百分比
        """
        window_minutes = window_minutes or self.measurement_window
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        recent_requests = [
            record for record in self.request_history
            if record['timestamp'] >= cutoff_time
        ]
        
        if not recent_requests:
            return 0.0
        
        error_count = sum(1 for req in recent_requests if not req['success'])
        total_count = len(recent_requests)
        
        error_rate = (error_count / total_count) * 100
        self.slos['error_rate'].current = error_rate
        
        return error_rate
    
    def get_slo_status(self) -> Dict:
        """
        获取所有SLO状态
        
        Returns:
        --------
        Dict : SLO状态报告
        """
        # 更新所有SLO
        self.calculate_availability()
        self.calculate_latency_p95()
        self.calculate_error_rate()
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'measurement_window_minutes': self.measurement_window,
            'slos': {},
            'error_budget': {
                'total_minutes': self.error_budget.total_minutes,
                'consumed_minutes': round(self.error_budget.consumed_minutes, 2),
                'remaining_minutes': round(self.error_budget.remaining_minutes(), 2),
                'remaining_percentage': round(self.error_budget.remaining_percentage(), 2),
                'is_exhausted': self.error_budget.is_exhausted(),
                'period': self.error_budget.period
            },
            'overall_compliance': True
        }
        
        for key, slo in self.slos.items():
            status['slos'][key] = {
                'name': slo.name,
                'target': slo.target,
                'current': round(slo.current, 2),
                'meets_target': slo.meets_target(),
                'compliance_percentage': round(slo.compliance_percentage(), 2)
            }
            
            if not slo.meets_target():
                status['overall_compliance'] = False
        
        return status
    
    def check_release_gate(self, min_error_budget_percentage: float = 20.0) -> Dict:
        """
        检查发布闸门（CI/CD集成）
        
        Parameters:
        -----------
        min_error_budget_percentage : float
            最小错误预算百分比（阻止发布的阈值）
            
        Returns:
        --------
        Dict : 发布闸门结果
        """
        status = self.get_slo_status()
        
        # 检查错误预算
        error_budget_ok = (
            status['error_budget']['remaining_percentage'] >= min_error_budget_percentage
        )
        
        # 检查所有SLO
        all_slos_ok = status['overall_compliance']
        
        can_release = error_budget_ok and all_slos_ok
        
        result = {
            'can_release': can_release,
            'timestamp': status['timestamp'],
            'error_budget_ok': error_budget_ok,
            'error_budget_remaining': status['error_budget']['remaining_percentage'],
            'min_required': min_error_budget_percentage,
            'slos_ok': all_slos_ok,
            'failed_slos': [
                key for key, slo_data in status['slos'].items()
                if not slo_data['meets_target']
            ],
            'recommendation': self._get_release_recommendation(
                can_release, error_budget_ok, all_slos_ok
            )
        }
        
        return result
    
    def _get_release_recommendation(self, can_release: bool, 
                                    error_budget_ok: bool, 
                                    slos_ok: bool) -> str:
        """生成发布建议"""
        if can_release:
            return "✅ 可以发布 - 所有SLO和错误预算均符合要求"
        
        reasons = []
        if not error_budget_ok:
            reasons.append("❌ 错误预算不足")
        if not slos_ok:
            reasons.append("❌ 部分SLO未达标")
        
        return f"🚫 不建议发布 - {'; '.join(reasons)}"
    
    def export_prometheus_metrics(self) -> Dict:
        """
        导出Prometheus指标
        
        Returns:
        --------
        Dict : Prometheus格式的指标
        """
        status = self.get_slo_status()
        
        metrics = {
            # SLO指标
            'slo_availability_target': self.slos['availability'].target,
            'slo_availability_current': self.slos['availability'].current,
            'slo_latency_p95_target_ms': self.slos['latency_p95'].target,
            'slo_latency_p95_current_ms': self.slos['latency_p95'].current,
            'slo_error_rate_target_percent': self.slos['error_rate'].target,
            'slo_error_rate_current_percent': self.slos['error_rate'].current,
            
            # 错误预算
            'error_budget_total_minutes': self.error_budget.total_minutes,
            'error_budget_consumed_minutes': self.error_budget.consumed_minutes,
            'error_budget_remaining_minutes': self.error_budget.remaining_minutes(),
            'error_budget_remaining_percentage': self.error_budget.remaining_percentage(),
            
            # 合规性
            'slo_compliance_overall': 1 if status['overall_compliance'] else 0,
            'slo_compliance_availability': 1 if self.slos['availability'].meets_target() else 0,
            'slo_compliance_latency': 1 if self.slos['latency_p95'].meets_target() else 0,
            'slo_compliance_error_rate': 1 if self.slos['error_rate'].meets_target() else 0
        }
        
        return metrics
    
    def generate_report(self, output_file: str = 'slo_report.json') -> Dict:
        """
        生成SLO报告
        
        Parameters:
        -----------
        output_file : str
            输出文件路径
            
        Returns:
        --------
        Dict : SLO报告
        """
        status = self.get_slo_status()
        release_gate = self.check_release_gate()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'slo_status': status,
            'release_gate_status': release_gate,
            'metrics': self.export_prometheus_metrics(),
            'recommendations': self._generate_recommendations()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✓ SLO报告已保存到: {output_file}")
        
        return report
    
    def _generate_recommendations(self) -> List[Dict]:
        """生成优化建议"""
        recommendations = []
        
        # 可用性建议
        if not self.slos['availability'].meets_target():
            recommendations.append({
                'slo': 'Availability',
                'issue': f"当前可用性 {self.slos['availability'].current:.2f}% 低于目标 {self.slos['availability'].target}%",
                'priority': 'Critical',
                'actions': [
                    '检查服务健康状态和依赖项',
                    '审查最近的部署和配置更改',
                    '启用自动故障转移机制',
                    '增加监控和告警覆盖率'
                ]
            })
        
        # 延迟建议
        if not self.slos['latency_p95'].meets_target():
            recommendations.append({
                'slo': 'Latency P95',
                'issue': f"当前P95延迟 {self.slos['latency_p95'].current:.2f}ms 高于目标 {self.slos['latency_p95'].target}ms",
                'priority': 'High',
                'actions': [
                    '启用响应压缩',
                    '优化数据库查询',
                    '实现缓存策略',
                    '考虑CDN加速'
                ]
            })
        
        # 错误率建议
        if not self.slos['error_rate'].meets_target():
            recommendations.append({
                'slo': 'Error Rate',
                'issue': f"当前错误率 {self.slos['error_rate'].current:.2f}% 高于目标 {self.slos['error_rate'].target}%",
                'priority': 'High',
                'actions': [
                    '分析错误日志定位问题',
                    '增强输入验证',
                    '实现熔断器模式',
                    '改进错误处理逻辑'
                ]
            })
        
        # 错误预算建议
        if self.error_budget.remaining_percentage() < 20:
            recommendations.append({
                'slo': 'Error Budget',
                'issue': f"错误预算仅剩 {self.error_budget.remaining_percentage():.1f}%",
                'priority': 'Critical',
                'actions': [
                    '暂停非关键性部署',
                    '集中处理影响SLO的问题',
                    '增加人工审核流程',
                    '启用紧急变更控制'
                ]
            })
        
        return recommendations
    
    def reset_error_budget(self):
        """重置错误预算（每月初调用）"""
        self.error_budget.consumed_minutes = 0.0
        logger.info("✓ 错误预算已重置")


# 全局SLO管理器实例
slo_manager = SLOManager(measurement_window_minutes=30)


if __name__ == '__main__':
    # 测试SLO管理器
    manager = SLOManager(measurement_window_minutes=30)
    
    # 模拟一些请求
    import random
    import time
    
    print("模拟请求数据...")
    for i in range(1000):
        success = random.random() > 0.001  # 99.9%成功率
        response_time = random.gauss(150, 50)  # 平均150ms，标准差50ms
        
        manager.record_request(success, response_time)
        manager.record_uptime(True)
    
    # 生成报告
    print("\n生成SLO报告...")
    report = manager.generate_report()
    
    # 打印状态
    print("\n=== SLO状态 ===")
    for key, slo_data in report['slo_status']['slos'].items():
        print(f"{slo_data['name']}: {slo_data['current']:.2f} "
              f"(目标: {slo_data['target']}) "
              f"{'✅' if slo_data['meets_target'] else '❌'}")
    
    print(f"\n错误预算剩余: {report['slo_status']['error_budget']['remaining_percentage']:.2f}%")
    
    # 检查发布闸门
    print("\n=== 发布闸门检查 ===")
    gate = manager.check_release_gate()
    print(gate['recommendation'])
    
    print(f"\n详细报告已保存到: slo_report.json")
