"""
HashInsight Enterprise - Mining Calculator Unit Tests
挖矿计算器单元测试
"""

import pytest
from analytics.roi_heatmap_generator import ROIHeatmapGenerator


class TestMiningCalculator:
    """挖矿计算器测试套件"""
    
    def setup_method(self):
        """测试初始化"""
        self.calculator = ROIHeatmapGenerator()
    
    def test_daily_profit_calculation(self):
        """测试每日收益计算"""
        result = self.calculator.calculate_daily_profit(
            hashrate_th=110,
            power_w=3250,
            electricity_cost=0.08,
            btc_price=60000,
            difficulty_multiplier=1.0,
            curtailment_ratio=1.0
        )
        
        assert 'daily_revenue' in result
        assert 'daily_cost' in result
        assert 'daily_profit' in result
        assert result['daily_revenue'] > 0
        assert result['daily_cost'] > 0
        assert isinstance(result['is_profitable'], bool)
    
    def test_curtailment_effect(self):
        """测试限电效果"""
        # 无限电
        full_power = self.calculator.calculate_daily_profit(
            110, 3250, 0.08, 60000, 1.0, 1.0
        )
        
        # 50%限电
        curtailed = self.calculator.calculate_daily_profit(
            110, 3250, 0.08, 60000, 1.0, 0.5
        )
        
        assert curtailed['daily_revenue'] < full_power['daily_revenue']
        assert curtailed['daily_cost'] < full_power['daily_cost']
        assert curtailed['effective_hashrate'] == 55  # 110 * 0.5
    
    def test_breakeven_price(self):
        """测试盈亏平衡价格"""
        result = self.calculator.calculate_daily_profit(
            110, 3250, 0.08, 30000, 1.0, 1.0
        )
        
        assert result['breakeven_price'] > 0
        assert result['breakeven_price'] < 100000
    
    def test_profit_margin(self):
        """测试利润率计算"""
        result = self.calculator.calculate_daily_profit(
            110, 3250, 0.08, 80000, 1.0, 1.0
        )
        
        assert 'profit_margin' in result
        assert result['profit_margin'] >= 0
        assert result['profit_margin'] <= 100
    
    def test_edge_cases(self):
        """测试边界情况"""
        # 零算力
        result = self.calculator.calculate_daily_profit(
            0, 3250, 0.08, 60000, 1.0, 1.0
        )
        assert result['daily_revenue'] == 0
        
        # 极低电价
        result = self.calculator.calculate_daily_profit(
            110, 3250, 0.01, 60000, 1.0, 1.0
        )
        assert result['daily_cost'] > 0
        assert result['daily_profit'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
