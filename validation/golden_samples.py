"""
HashInsight Enterprise - Golden Samples Validator
黄金样本验证器
"""

import logging
from typing import List, Dict
from analytics.roi_heatmap_generator import ROIHeatmapGenerator

logger = logging.getLogger(__name__)


class GoldenSamplesValidator:
    """黄金样本验证器"""
    
    # 20组标准配置
    GOLDEN_SAMPLES = [
        {
            'name': 'Antminer S19 Pro',
            'hashrate': 110,
            'power': 3250,
            'electricity_cost': 0.08,
            'btc_price': 60000,
            'expected_daily_revenue': 19.2,  # USD
            'expected_daily_cost': 6.24,
            'expected_daily_profit': 12.96,
            'tolerance': 0.001  # 0.1%
        },
        {
            'name': 'Antminer S21',
            'hashrate': 200,
            'power': 3550,
            'electricity_cost': 0.08,
            'btc_price': 60000,
            'expected_daily_revenue': 34.9,
            'expected_daily_cost': 6.82,
            'expected_daily_profit': 28.08,
            'tolerance': 0.001
        },
        {
            'name': 'WhatsMiner M53S',
            'hashrate': 226,
            'power': 6554,
            'electricity_cost': 0.08,
            'btc_price': 60000,
            'expected_daily_revenue': 39.4,
            'expected_daily_cost': 12.58,
            'expected_daily_profit': 26.82,
            'tolerance': 0.001
        },
        # 添加更多标准配置...
    ]
    
    def __init__(self):
        """初始化验证器"""
        self.calculator = ROIHeatmapGenerator()
        self.results = []
    
    def validate_all(self) -> Dict:
        """验证所有黄金样本"""
        passed = 0
        failed = 0
        deviations = []
        
        for sample in self.GOLDEN_SAMPLES:
            result = self._validate_sample(sample)
            self.results.append(result)
            
            if result['passed']:
                passed += 1
            else:
                failed += 1
                deviations.append(result)
        
        return {
            'total': len(self.GOLDEN_SAMPLES),
            'passed': passed,
            'failed': failed,
            'pass_rate': (passed / len(self.GOLDEN_SAMPLES)) * 100,
            'deviations': deviations
        }
    
    def _validate_sample(self, sample: Dict) -> Dict:
        """验证单个样本"""
        calculated = self.calculator.calculate_daily_profit(
            hashrate_th=sample['hashrate'],
            power_w=sample['power'],
            electricity_cost=sample['electricity_cost'],
            btc_price=sample['btc_price']
        )
        
        # 计算偏差
        revenue_deviation = abs(
            calculated['daily_revenue'] - sample['expected_daily_revenue']
        ) / sample['expected_daily_revenue']
        
        cost_deviation = abs(
            calculated['daily_cost'] - sample['expected_daily_cost']
        ) / sample['expected_daily_cost']
        
        profit_deviation = abs(
            calculated['daily_profit'] - sample['expected_daily_profit']
        ) / sample['expected_daily_profit']
        
        max_deviation = max(revenue_deviation, cost_deviation, profit_deviation)
        passed = max_deviation <= sample['tolerance']
        
        return {
            'name': sample['name'],
            'passed': passed,
            'calculated': calculated,
            'expected': {
                'revenue': sample['expected_daily_revenue'],
                'cost': sample['expected_daily_cost'],
                'profit': sample['expected_daily_profit']
            },
            'deviations': {
                'revenue': revenue_deviation * 100,  # 百分比
                'cost': cost_deviation * 100,
                'profit': profit_deviation * 100,
                'max': max_deviation * 100
            }
        }
    
    def generate_report(self) -> str:
        """生成验证报告"""
        summary = self.validate_all()
        
        report = f"""
=== Golden Samples Validation Report ===

Total Samples: {summary['total']}
Passed: {summary['passed']}
Failed: {summary['failed']}
Pass Rate: {summary['pass_rate']:.2f}%

"""
        
        if summary['deviations']:
            report += "\nDeviations (exceeding 0.1% tolerance):\n"
            for dev in summary['deviations']:
                report += f"\n{dev['name']}:\n"
                report += f"  Revenue Deviation: {dev['deviations']['revenue']:.3f}%\n"
                report += f"  Cost Deviation: {dev['deviations']['cost']:.3f}%\n"
                report += f"  Profit Deviation: {dev['deviations']['profit']:.3f}%\n"
        
        return report
