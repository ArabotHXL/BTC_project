"""
HashInsight Enterprise - Investor Dashboard
投资人工作台
"""

from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy import text, func
from db import db
from models import UserMiner


class InvestorDashboard:
    """投资人工作台"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def get_roi_overview(self) -> Dict:
        """ROI概览卡片"""
        miners = UserMiner.query.filter_by(user_id=self.user_id, status='active').all()
        
        total_investment = sum(m.actual_price * m.quantity for m in miners)
        daily_revenue = sum(self._calculate_daily_revenue(m) for m in miners)
        daily_cost = sum(self._calculate_daily_cost(m) for m in miners)
        daily_profit = daily_revenue - daily_cost
        
        return {
            'total_investment': total_investment,
            'daily_revenue': daily_revenue,
            'daily_cost': daily_cost,
            'daily_profit': daily_profit,
            'monthly_profit': daily_profit * 30,
            'annual_roi': (daily_profit * 365 / total_investment * 100) if total_investment > 0 else 0,
            'payback_days': total_investment / daily_profit if daily_profit > 0 else float('inf')
        }
    
    def get_cashflow_chart(self, days: int = 365) -> List[Dict]:
        """现金流图表数据"""
        # 模拟未来现金流
        overview = self.get_roi_overview()
        daily_profit = overview['daily_profit']
        
        cashflow = []
        cumulative = -overview['total_investment']  # 初始投资为负
        
        for day in range(days):
            cumulative += daily_profit
            cashflow.append({
                'day': day,
                'daily': daily_profit,
                'cumulative': cumulative,
                'is_breakeven': cumulative >= 0
            })
        
        return cashflow
    
    def _calculate_daily_revenue(self, miner: UserMiner) -> float:
        """计算单个矿机日收入"""
        btc_price = 60000  # 应从市场数据获取
        daily_btc = (miner.actual_hashrate / 500000) * 144 * 3.125  # 简化计算
        return daily_btc * btc_price * miner.quantity
    
    def _calculate_daily_cost(self, miner: UserMiner) -> float:
        """计算单个矿机日成本"""
        daily_kwh = (miner.actual_power * 24 / 1000) * miner.quantity
        return daily_kwh * miner.electricity_cost
