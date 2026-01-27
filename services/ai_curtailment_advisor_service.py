"""
AI Curtailment Advisor Service
AI 限电建议服务

功能:
- 接入电价/策略/矿机效率曲线 + 预测模块输出
- 输出建议削减比例、优先关停顺序、预计节省与收益损失、风险点
- 把"凭经验拍脑袋"变成"可解释的策略建议"

验收口径：AI 不需要 100% 正确，但要做到：可复核、有证据、能节省时间
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from db import db
from services.telemetry_service import TelemetryService

logger = logging.getLogger(__name__)


@dataclass
class MinerEfficiency:
    """矿机效率数据"""
    miner_id: str
    model: str
    hashrate_ths: float
    power_w: float
    efficiency_jth: float
    temperature_c: float
    uptime_hours: float
    revenue_per_hour: float
    cost_per_hour: float
    profit_per_hour: float


@dataclass
class CurtailmentTarget:
    """限电目标"""
    miner_id: str
    model: str
    priority: int
    reason: str
    reason_zh: str
    hashrate_ths: float
    power_w: float
    efficiency_jth: float
    savings_per_hour: float
    revenue_loss_per_hour: float


@dataclass
class RiskPoint:
    """风险点"""
    risk: str
    risk_zh: str
    severity: str
    mitigation: str
    mitigation_zh: str


@dataclass
class CurtailmentPlan:
    """限电计划"""
    site_id: int
    generated_at: str
    
    current_power_kw: float
    target_power_kw: float
    reduction_kw: float
    reduction_pct: float
    
    electricity_price: float
    btc_price: float
    
    miners_to_curtail: List[CurtailmentTarget]
    miners_to_keep: List[str]
    
    total_hashrate_loss_ths: float
    total_power_saved_kw: float
    
    hourly_cost_savings: float
    hourly_revenue_loss: float
    net_hourly_impact: float
    
    recovery_time_minutes: int
    
    risk_points: List[RiskPoint]
    
    strategy: str
    strategy_zh: str
    
    data_sources: List[str]


class AICurtailmentAdvisorService:
    """AI 限电建议服务
    
    输入：电价/策略/矿机效率曲线 + 预测模块输出
    输出：建议削减比例、优先关停顺序、预计节省与收益损失、风险点
    """
    
    STRATEGY_EFFICIENCY_FIRST = 'efficiency_first'
    STRATEGY_POWER_FIRST = 'power_first'
    STRATEGY_REVENUE_FIRST = 'revenue_first'
    STRATEGY_TEMPERATURE_FIRST = 'temperature_first'
    
    DEFAULT_BTC_PRICE = 95000
    DEFAULT_NETWORK_DIFFICULTY = 75e12
    DEFAULT_BLOCK_REWARD = 3.125
    
    RECOVERY_TIME_PER_MINER_MINUTES = 3
    
    def __init__(self):
        self.telemetry_service = TelemetryService()
    
    def generate_curtailment_plan(
        self,
        site_id: int,
        target_reduction_kw: Optional[float] = None,
        target_power_kw: Optional[float] = None,
        target_reduction_pct: Optional[float] = None,
        electricity_price: float = 0.05,
        btc_price: Optional[float] = None,
        strategy: str = STRATEGY_EFFICIENCY_FIRST,
        max_miners_to_curtail: Optional[int] = None,
        exclude_miner_ids: Optional[List[str]] = None,
    ) -> CurtailmentPlan:
        """生成限电计划
        
        Args:
            site_id: 站点ID
            target_reduction_kw: 目标削减功率 (kW)
            target_power_kw: 目标总功率 (kW)
            target_reduction_pct: 目标削减百分比
            electricity_price: 电价 ($/kWh)
            btc_price: BTC价格 (可选，默认使用当前价格)
            strategy: 关停策略
            max_miners_to_curtail: 最大关停矿机数
            exclude_miner_ids: 排除的矿机ID列表
        
        Returns:
            CurtailmentPlan 限电计划
        """
        now = datetime.utcnow()
        
        btc_price = btc_price or self._get_btc_price()
        
        miners = self._get_miner_efficiencies(site_id, btc_price, electricity_price)
        
        if exclude_miner_ids:
            miners = [m for m in miners if m.miner_id not in exclude_miner_ids]
        
        current_power_kw = sum(m.power_w for m in miners) / 1000
        
        if target_power_kw is not None:
            reduction_kw = max(0, current_power_kw - target_power_kw)
        elif target_reduction_pct is not None:
            reduction_kw = current_power_kw * (target_reduction_pct / 100)
        elif target_reduction_kw is not None:
            reduction_kw = target_reduction_kw
        else:
            reduction_kw = current_power_kw * 0.2
        
        reduction_pct = (reduction_kw / current_power_kw * 100) if current_power_kw > 0 else 0
        
        sorted_miners = self._sort_miners_by_strategy(miners, strategy)
        
        miners_to_curtail = []
        curtailed_power = 0
        
        for miner in sorted_miners:
            if curtailed_power >= reduction_kw * 1000:
                break
            
            if max_miners_to_curtail and len(miners_to_curtail) >= max_miners_to_curtail:
                break
            
            priority = len(miners_to_curtail) + 1
            reason, reason_zh = self._get_curtailment_reason(miner, strategy)
            
            miners_to_curtail.append(CurtailmentTarget(
                miner_id=miner.miner_id,
                model=miner.model,
                priority=priority,
                reason=reason,
                reason_zh=reason_zh,
                hashrate_ths=miner.hashrate_ths,
                power_w=miner.power_w,
                efficiency_jth=miner.efficiency_jth,
                savings_per_hour=miner.cost_per_hour,
                revenue_loss_per_hour=miner.revenue_per_hour,
            ))
            
            curtailed_power += miner.power_w
        
        curtailed_ids = {t.miner_id for t in miners_to_curtail}
        miners_to_keep = [m.miner_id for m in miners if m.miner_id not in curtailed_ids]
        
        total_hashrate_loss = sum(t.hashrate_ths for t in miners_to_curtail)
        total_power_saved = sum(t.power_w for t in miners_to_curtail) / 1000
        hourly_cost_savings = sum(t.savings_per_hour for t in miners_to_curtail)
        hourly_revenue_loss = sum(t.revenue_loss_per_hour for t in miners_to_curtail)
        net_hourly_impact = hourly_cost_savings - hourly_revenue_loss
        
        recovery_time = len(miners_to_curtail) * self.RECOVERY_TIME_PER_MINER_MINUTES
        
        risk_points = self._assess_risks(
            miners_to_curtail=miners_to_curtail,
            current_power_kw=current_power_kw,
            reduction_pct=reduction_pct,
            strategy=strategy,
        )
        
        strategy_name, strategy_name_zh = self._get_strategy_name(strategy)
        
        return CurtailmentPlan(
            site_id=site_id,
            generated_at=now.isoformat(),
            current_power_kw=round(current_power_kw, 2),
            target_power_kw=round(current_power_kw - reduction_kw, 2),
            reduction_kw=round(reduction_kw, 2),
            reduction_pct=round(reduction_pct, 1),
            electricity_price=electricity_price,
            btc_price=btc_price,
            miners_to_curtail=miners_to_curtail,
            miners_to_keep=miners_to_keep,
            total_hashrate_loss_ths=round(total_hashrate_loss, 2),
            total_power_saved_kw=round(total_power_saved, 2),
            hourly_cost_savings=round(hourly_cost_savings, 2),
            hourly_revenue_loss=round(hourly_revenue_loss, 2),
            net_hourly_impact=round(net_hourly_impact, 2),
            recovery_time_minutes=recovery_time,
            risk_points=risk_points,
            strategy=strategy,
            strategy_zh=strategy_name_zh,
            data_sources=['miner_telemetry_live', 'btc_price_api', 'electricity_price'],
        )
    
    def _get_miner_efficiencies(
        self,
        site_id: int,
        btc_price: float,
        electricity_price: float,
    ) -> List[MinerEfficiency]:
        """获取矿机效率数据"""
        miners = self.telemetry_service.get_live(site_id=site_id, online_only=True)
        
        efficiencies = []
        for miner in miners:
            miner_id = miner.get('miner_id', '')
            model = miner.get('hardware', {}).get('model', 'Unknown')
            hashrate_ths = miner.get('hashrate', {}).get('value', 0)
            power_w = miner.get('power', {}).get('value', 0) or 3000
            temperature_c = miner.get('temperature', {}).get('avg', 0) or 65
            uptime_seconds = miner.get('uptime_seconds', 0) or 0
            
            if hashrate_ths <= 0:
                hashrate_ths = miner.get('hashrate', {}).get('expected_ths', 100)
            
            efficiency_jth = (power_w / hashrate_ths) if hashrate_ths > 0 else 999
            
            daily_btc = self._calculate_daily_btc(hashrate_ths)
            revenue_per_hour = (daily_btc * btc_price) / 24
            cost_per_hour = (power_w / 1000) * electricity_price
            profit_per_hour = revenue_per_hour - cost_per_hour
            
            efficiencies.append(MinerEfficiency(
                miner_id=miner_id,
                model=model,
                hashrate_ths=hashrate_ths,
                power_w=power_w,
                efficiency_jth=round(efficiency_jth, 2),
                temperature_c=temperature_c,
                uptime_hours=uptime_seconds / 3600,
                revenue_per_hour=round(revenue_per_hour, 4),
                cost_per_hour=round(cost_per_hour, 4),
                profit_per_hour=round(profit_per_hour, 4),
            ))
        
        return efficiencies
    
    def _calculate_daily_btc(self, hashrate_ths: float) -> float:
        """计算日均BTC产出"""
        hashrate_hs = hashrate_ths * 1e12
        difficulty = self.DEFAULT_NETWORK_DIFFICULTY
        block_reward = self.DEFAULT_BLOCK_REWARD
        
        daily_btc = (hashrate_hs * 86400 * block_reward) / (difficulty * 2**32)
        return daily_btc
    
    def _sort_miners_by_strategy(
        self,
        miners: List[MinerEfficiency],
        strategy: str,
    ) -> List[MinerEfficiency]:
        """按策略排序矿机（优先关停的在前）"""
        if strategy == self.STRATEGY_EFFICIENCY_FIRST:
            return sorted(miners, key=lambda m: m.efficiency_jth, reverse=True)
        
        elif strategy == self.STRATEGY_POWER_FIRST:
            return sorted(miners, key=lambda m: m.power_w, reverse=True)
        
        elif strategy == self.STRATEGY_REVENUE_FIRST:
            return sorted(miners, key=lambda m: m.profit_per_hour)
        
        elif strategy == self.STRATEGY_TEMPERATURE_FIRST:
            return sorted(miners, key=lambda m: m.temperature_c, reverse=True)
        
        else:
            return sorted(miners, key=lambda m: m.efficiency_jth, reverse=True)
    
    def _get_curtailment_reason(
        self,
        miner: MinerEfficiency,
        strategy: str,
    ) -> tuple:
        """获取关停原因"""
        if strategy == self.STRATEGY_EFFICIENCY_FIRST:
            return (
                f"Low efficiency ({miner.efficiency_jth} J/TH)",
                f"效率较低（{miner.efficiency_jth} J/TH）"
            )
        elif strategy == self.STRATEGY_POWER_FIRST:
            return (
                f"High power consumption ({miner.power_w/1000:.1f} kW)",
                f"功耗较高（{miner.power_w/1000:.1f} kW）"
            )
        elif strategy == self.STRATEGY_REVENUE_FIRST:
            return (
                f"Low profit margin (${miner.profit_per_hour:.2f}/hr)",
                f"利润较低（${miner.profit_per_hour:.2f}/小时）"
            )
        elif strategy == self.STRATEGY_TEMPERATURE_FIRST:
            return (
                f"High temperature ({miner.temperature_c}°C)",
                f"温度较高（{miner.temperature_c}°C）"
            )
        else:
            return ("Selected for curtailment", "被选中限电")
    
    def _get_strategy_name(self, strategy: str) -> tuple:
        """获取策略名称"""
        names = {
            self.STRATEGY_EFFICIENCY_FIRST: ('Efficiency First', '效率优先'),
            self.STRATEGY_POWER_FIRST: ('Power First', '功率优先'),
            self.STRATEGY_REVENUE_FIRST: ('Revenue First', '收益优先'),
            self.STRATEGY_TEMPERATURE_FIRST: ('Temperature First', '温度优先'),
        }
        return names.get(strategy, ('Custom', '自定义'))
    
    def _assess_risks(
        self,
        miners_to_curtail: List[CurtailmentTarget],
        current_power_kw: float,
        reduction_pct: float,
        strategy: str,
    ) -> List[RiskPoint]:
        """评估风险点"""
        risks = []
        
        if reduction_pct > 50:
            risks.append(RiskPoint(
                risk=f"Large reduction ({reduction_pct:.0f}%) may impact site revenue significantly",
                risk_zh=f"削减幅度较大（{reduction_pct:.0f}%），可能显著影响站点收益",
                severity='high',
                mitigation='Consider phased curtailment approach',
                mitigation_zh='考虑分阶段限电方案',
            ))
        
        recovery_time = len(miners_to_curtail) * self.RECOVERY_TIME_PER_MINER_MINUTES
        if recovery_time > 30:
            risks.append(RiskPoint(
                risk=f"Recovery time ~{recovery_time} minutes may delay full hashrate restoration",
                risk_zh=f"恢复时间约 {recovery_time} 分钟，可能延迟算力恢复",
                severity='medium',
                mitigation='Schedule curtailment during low-price windows',
                mitigation_zh='在低电价时段安排限电',
            ))
        
        high_temp_miners = [t for t in miners_to_curtail if t.efficiency_jth > 40]
        if high_temp_miners and strategy != self.STRATEGY_TEMPERATURE_FIRST:
            risks.append(RiskPoint(
                risk=f"{len(high_temp_miners)} miners with poor efficiency selected - may indicate hardware issues",
                risk_zh=f"选中 {len(high_temp_miners)} 台效率较差的矿机 - 可能存在硬件问题",
                severity='low',
                mitigation='Review these miners for potential maintenance needs',
                mitigation_zh='检查这些矿机是否需要维护',
            ))
        
        if not miners_to_curtail:
            risks.append(RiskPoint(
                risk="No miners selected for curtailment - target may be too low",
                risk_zh="未选中任何矿机 - 目标可能设置过低",
                severity='info',
                mitigation='Adjust target reduction or check miner availability',
                mitigation_zh='调整削减目标或检查矿机可用性',
            ))
        
        return risks
    
    def _get_btc_price(self) -> float:
        """获取当前BTC价格"""
        try:
            from services.btc_price_service import get_btc_price
            price = get_btc_price()
            return price if price else self.DEFAULT_BTC_PRICE
        except:
            return self.DEFAULT_BTC_PRICE
    
    def to_dict(self, plan: CurtailmentPlan) -> Dict:
        """Convert CurtailmentPlan to dict for API response"""
        return {
            'site_id': plan.site_id,
            'generated_at': plan.generated_at,
            'power': {
                'current_kw': plan.current_power_kw,
                'target_kw': plan.target_power_kw,
                'reduction_kw': plan.reduction_kw,
                'reduction_pct': plan.reduction_pct,
            },
            'pricing': {
                'electricity_price': plan.electricity_price,
                'btc_price': plan.btc_price,
            },
            'miners_to_curtail': [
                {
                    'miner_id': t.miner_id,
                    'model': t.model,
                    'priority': t.priority,
                    'reason': t.reason,
                    'reason_zh': t.reason_zh,
                    'hashrate_ths': t.hashrate_ths,
                    'power_w': t.power_w,
                    'efficiency_jth': t.efficiency_jth,
                    'savings_per_hour': t.savings_per_hour,
                    'revenue_loss_per_hour': t.revenue_loss_per_hour,
                }
                for t in plan.miners_to_curtail
            ],
            'miners_to_keep': plan.miners_to_keep,
            'impact': {
                'total_hashrate_loss_ths': plan.total_hashrate_loss_ths,
                'total_power_saved_kw': plan.total_power_saved_kw,
                'hourly_cost_savings': plan.hourly_cost_savings,
                'hourly_revenue_loss': plan.hourly_revenue_loss,
                'net_hourly_impact': plan.net_hourly_impact,
            },
            'recovery_time_minutes': plan.recovery_time_minutes,
            'risk_points': [
                {
                    'risk': r.risk,
                    'risk_zh': r.risk_zh,
                    'severity': r.severity,
                    'mitigation': r.mitigation,
                    'mitigation_zh': r.mitigation_zh,
                }
                for r in plan.risk_points
            ],
            'strategy': plan.strategy,
            'strategy_zh': plan.strategy_zh,
            'data_sources': plan.data_sources,
        }


curtailment_advisor_service = AICurtailmentAdvisorService()
