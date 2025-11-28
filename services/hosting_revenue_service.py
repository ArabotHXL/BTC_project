"""
HashInsight Enterprise - 托管收益预测服务
Hosting Revenue Prediction Service

功能:
- 实时矿机收益预测
- 基于实时数据的盈利分析
- 按矿机/站点聚合收益
- 24小时滚动预测

版本: 1.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from decimal import Decimal

from db import db

logger = logging.getLogger(__name__)


@dataclass
class MinerRevenueMetrics:
    miner_id: int
    serial_number: str
    model_name: str
    
    hashrate_th: float
    power_w: float
    efficiency_jth: float
    electricity_rate: float
    
    daily_btc: float
    daily_usd: float
    daily_power_cost: float
    daily_net_profit: float
    
    hourly_btc: float
    hourly_usd: float
    hourly_net_profit: float
    
    roi_days: float
    profit_margin: float
    
    btc_price: float
    difficulty: float
    block_reward: float
    
    efficiency_grade: str
    health_score: int
    is_profitable: bool
    
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')


@dataclass 
class SiteRevenueMetrics:
    site_id: int
    site_name: str
    
    total_miners: int
    online_miners: int
    
    total_hashrate_th: float
    total_power_mw: float
    
    daily_btc_total: float
    daily_usd_total: float
    daily_power_cost_total: float
    daily_net_profit_total: float
    
    monthly_btc_estimate: float
    monthly_usd_estimate: float
    
    avg_efficiency_jth: float
    avg_profit_margin: float
    
    profitable_miners: int
    unprofitable_miners: int
    
    electricity_rate: float
    utilization_rate: float
    
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')


class HostingRevenueService:
    
    SECONDS_PER_DAY = 86400
    SECONDS_PER_HOUR = 3600
    TH_TO_H = 1e12
    WATT_TO_MW = 1e-6
    
    def __init__(self):
        self._btc_price: float = 95000.0
        self._difficulty: float = 102.29e12
        self._block_reward: float = 3.125
        self._network_hashrate: float = 750e18
        self._data_source: str = "default"
        self._last_update: Optional[datetime] = None
        
        logger.info("HostingRevenueService initialized")
    
    def update_market_data(
        self, 
        btc_price: Optional[float] = None,
        difficulty: Optional[float] = None,
        block_reward: Optional[float] = None,
        network_hashrate: Optional[float] = None,
        source: str = "api"
    ):
        if btc_price is not None:
            self._btc_price = btc_price
        if difficulty is not None:
            self._difficulty = difficulty
        if block_reward is not None:
            self._block_reward = block_reward
        if network_hashrate is not None:
            self._network_hashrate = network_hashrate
        
        self._data_source = source
        self._last_update = datetime.utcnow()
        
        logger.info(f"市场数据更新 - BTC: ${self._btc_price:.2f}, 难度: {self._difficulty:.2e}")
    
    def _fetch_market_data(self) -> Dict[str, Any]:
        try:
            from market_analytics import get_cached_market_data
            
            market_data = get_cached_market_data()
            if market_data:
                self.update_market_data(
                    btc_price=market_data.get('btc_price', self._btc_price),
                    difficulty=market_data.get('difficulty', self._difficulty),
                    block_reward=market_data.get('block_reward', self._block_reward),
                    network_hashrate=market_data.get('network_hashrate', self._network_hashrate),
                    source=market_data.get('source', 'api')
                )
        except Exception as e:
            logger.warning(f"无法获取实时市场数据，使用默认值: {e}")
        
        return {
            'btc_price': self._btc_price,
            'difficulty': self._difficulty,
            'block_reward': self._block_reward,
            'network_hashrate': self._network_hashrate,
            'source': self._data_source,
            'last_update': self._last_update.isoformat() if self._last_update else None
        }
    
    def calculate_daily_btc(self, hashrate_th: float) -> float:
        if self._difficulty <= 0:
            return 0.0
        
        hashrate_h = hashrate_th * self.TH_TO_H
        
        blocks_per_day = self.SECONDS_PER_DAY / 600
        
        pool_share = hashrate_h / self._network_hashrate if self._network_hashrate > 0 else 0
        
        daily_btc = pool_share * blocks_per_day * self._block_reward
        
        return daily_btc
    
    def calculate_daily_power_cost(self, power_w: float, electricity_rate: float) -> float:
        daily_kwh = (power_w / 1000) * 24
        return daily_kwh * electricity_rate
    
    def calculate_efficiency(self, hashrate_th: float, power_w: float) -> float:
        if hashrate_th <= 0:
            return float('inf')
        return power_w / hashrate_th
    
    def get_efficiency_grade(self, efficiency_jth: float, model_name: str = "") -> str:
        model_baselines = {
            'S21': 17.5, 'S21 Pro': 15.0, 'S21 XP': 13.5,
            'S19': 30.0, 'S19 Pro': 29.5, 'S19j Pro': 28.0, 'S19 XP': 21.5,
            'M50': 26.0, 'M50S': 24.0, 'M50S++': 22.0,
            'M60': 18.5, 'M60S': 17.0,
        }
        
        baseline = None
        for model_key, base in model_baselines.items():
            if model_key.lower() in model_name.lower():
                baseline = base
                break
        
        if baseline is None:
            if efficiency_jth < 20:
                return 'A'
            elif efficiency_jth < 25:
                return 'B'
            elif efficiency_jth < 30:
                return 'C'
            elif efficiency_jth < 40:
                return 'D'
            else:
                return 'F'
        
        ratio = efficiency_jth / baseline
        
        if ratio <= 1.0:
            return 'A'
        elif ratio <= 1.1:
            return 'B'
        elif ratio <= 1.25:
            return 'C'
        elif ratio <= 1.5:
            return 'D'
        else:
            return 'F'
    
    def calculate_miner_revenue(
        self,
        miner_id: int,
        serial_number: str,
        model_name: str,
        hashrate_th: float,
        power_w: float,
        electricity_rate: float,
        health_score: int = 100,
        equipment_cost: float = 0.0
    ) -> MinerRevenueMetrics:
        self._fetch_market_data()
        
        efficiency_jth = self.calculate_efficiency(hashrate_th, power_w)
        
        daily_btc = self.calculate_daily_btc(hashrate_th)
        daily_usd = daily_btc * self._btc_price
        daily_power_cost = self.calculate_daily_power_cost(power_w, electricity_rate)
        daily_net_profit = daily_usd - daily_power_cost
        
        hourly_btc = daily_btc / 24
        hourly_usd = daily_usd / 24
        hourly_net_profit = daily_net_profit / 24
        
        if equipment_cost > 0 and daily_net_profit > 0:
            roi_days = equipment_cost / daily_net_profit
        else:
            roi_days = -1
        
        if daily_usd > 0:
            profit_margin = (daily_net_profit / daily_usd) * 100
        else:
            profit_margin = 0.0
        
        efficiency_grade = self.get_efficiency_grade(efficiency_jth, model_name)
        is_profitable = daily_net_profit > 0
        
        return MinerRevenueMetrics(
            miner_id=miner_id,
            serial_number=serial_number,
            model_name=model_name,
            hashrate_th=hashrate_th,
            power_w=power_w,
            efficiency_jth=efficiency_jth,
            electricity_rate=electricity_rate,
            daily_btc=daily_btc,
            daily_usd=daily_usd,
            daily_power_cost=daily_power_cost,
            daily_net_profit=daily_net_profit,
            hourly_btc=hourly_btc,
            hourly_usd=hourly_usd,
            hourly_net_profit=hourly_net_profit,
            roi_days=roi_days,
            profit_margin=profit_margin,
            btc_price=self._btc_price,
            difficulty=self._difficulty,
            block_reward=self._block_reward,
            efficiency_grade=efficiency_grade,
            health_score=health_score,
            is_profitable=is_profitable
        )
    
    def calculate_site_revenue(self, site_id: int) -> Optional[SiteRevenueMetrics]:
        try:
            from models import HostingMiner, HostingSite
            
            site = HostingSite.query.get(site_id)
            if not site:
                logger.warning(f"站点不存在: {site_id}")
                return None
            
            miners = HostingMiner.query.filter_by(site_id=site_id).all()
            
            if not miners:
                return SiteRevenueMetrics(
                    site_id=site_id,
                    site_name=site.name,
                    total_miners=0,
                    online_miners=0,
                    total_hashrate_th=0,
                    total_power_mw=0,
                    daily_btc_total=0,
                    daily_usd_total=0,
                    daily_power_cost_total=0,
                    daily_net_profit_total=0,
                    monthly_btc_estimate=0,
                    monthly_usd_estimate=0,
                    avg_efficiency_jth=0,
                    avg_profit_margin=0,
                    profitable_miners=0,
                    unprofitable_miners=0,
                    electricity_rate=site.electricity_rate,
                    utilization_rate=site.utilization_rate if hasattr(site, 'utilization_rate') else 0
                )
            
            total_miners = len(miners)
            online_miners = sum(1 for m in miners if m.status == 'active' or getattr(m, 'cgminer_online', False))
            
            total_hashrate = 0.0
            total_power = 0.0
            daily_btc_total = 0.0
            daily_usd_total = 0.0
            daily_power_cost_total = 0.0
            profitable_count = 0
            unprofitable_count = 0
            efficiency_sum = 0.0
            profit_margin_sum = 0.0
            
            electricity_rate = site.electricity_rate
            
            for miner in miners:
                hashrate = miner.actual_hashrate or 0
                power = miner.actual_power or 0
                model_name = miner.miner_model.model_name if miner.miner_model else ""
                
                if hashrate <= 0 or power <= 0:
                    continue
                
                metrics = self.calculate_miner_revenue(
                    miner_id=miner.id,
                    serial_number=miner.serial_number,
                    model_name=model_name,
                    hashrate_th=hashrate,
                    power_w=power,
                    electricity_rate=electricity_rate,
                    health_score=miner.health_score or 100
                )
                
                total_hashrate += hashrate
                total_power += power
                daily_btc_total += metrics.daily_btc
                daily_usd_total += metrics.daily_usd
                daily_power_cost_total += metrics.daily_power_cost
                efficiency_sum += metrics.efficiency_jth
                profit_margin_sum += metrics.profit_margin
                
                if metrics.is_profitable:
                    profitable_count += 1
                else:
                    unprofitable_count += 1
            
            daily_net_profit_total = daily_usd_total - daily_power_cost_total
            
            valid_miners = profitable_count + unprofitable_count
            avg_efficiency = efficiency_sum / valid_miners if valid_miners > 0 else 0
            avg_profit_margin = profit_margin_sum / valid_miners if valid_miners > 0 else 0
            
            monthly_btc = daily_btc_total * 30
            monthly_usd = daily_usd_total * 30
            
            utilization = 0
            if hasattr(site, 'utilization_rate'):
                utilization = site.utilization_rate
            elif hasattr(site, 'capacity_mw') and site.capacity_mw > 0:
                utilization = (total_power * self.WATT_TO_MW / site.capacity_mw) * 100
            
            return SiteRevenueMetrics(
                site_id=site_id,
                site_name=site.name,
                total_miners=total_miners,
                online_miners=online_miners,
                total_hashrate_th=total_hashrate,
                total_power_mw=total_power * self.WATT_TO_MW,
                daily_btc_total=daily_btc_total,
                daily_usd_total=daily_usd_total,
                daily_power_cost_total=daily_power_cost_total,
                daily_net_profit_total=daily_net_profit_total,
                monthly_btc_estimate=monthly_btc,
                monthly_usd_estimate=monthly_usd,
                avg_efficiency_jth=avg_efficiency,
                avg_profit_margin=avg_profit_margin,
                profitable_miners=profitable_count,
                unprofitable_miners=unprofitable_count,
                electricity_rate=electricity_rate,
                utilization_rate=utilization
            )
            
        except Exception as e:
            logger.error(f"计算站点收益失败: {e}")
            return None
    
    def get_all_miners_revenue(
        self, 
        site_id: Optional[int] = None,
        sort_by: str = "daily_net_profit",
        sort_desc: bool = True,
        limit: int = 100
    ) -> List[MinerRevenueMetrics]:
        try:
            from models import HostingMiner, HostingSite
            
            query = HostingMiner.query
            if site_id:
                query = query.filter_by(site_id=site_id)
            
            miners = query.limit(limit).all()
            
            results = []
            
            for miner in miners:
                site = HostingSite.query.get(miner.site_id)
                electricity_rate = site.electricity_rate if site else 0.06
                
                hashrate = miner.actual_hashrate or 0
                power = miner.actual_power or 0
                model_name = miner.miner_model.model_name if miner.miner_model else ""
                
                if hashrate <= 0 or power <= 0:
                    continue
                
                metrics = self.calculate_miner_revenue(
                    miner_id=miner.id,
                    serial_number=miner.serial_number,
                    model_name=model_name,
                    hashrate_th=hashrate,
                    power_w=power,
                    electricity_rate=electricity_rate,
                    health_score=miner.health_score or 100
                )
                
                results.append(metrics)
            
            if sort_by and hasattr(MinerRevenueMetrics, sort_by):
                results.sort(
                    key=lambda x: getattr(x, sort_by, 0),
                    reverse=sort_desc
                )
            
            return results
            
        except Exception as e:
            logger.error(f"获取矿机收益列表失败: {e}")
            return []
    
    def get_revenue_summary(self, site_id: Optional[int] = None) -> Dict[str, Any]:
        self._fetch_market_data()
        
        if site_id:
            site_metrics = self.calculate_site_revenue(site_id)
            if site_metrics:
                return {
                    'type': 'site',
                    'site': asdict(site_metrics),
                    'market_data': {
                        'btc_price': self._btc_price,
                        'difficulty': self._difficulty,
                        'block_reward': self._block_reward,
                        'source': self._data_source,
                        'last_update': self._last_update.isoformat() if self._last_update else None
                    }
                }
        
        try:
            from models import HostingSite
            
            sites = HostingSite.query.all()
            site_summaries = []
            
            total_hashrate = 0.0
            total_power_mw = 0.0
            total_daily_btc = 0.0
            total_daily_usd = 0.0
            total_daily_cost = 0.0
            total_miners = 0
            online_miners = 0
            
            for site in sites:
                metrics = self.calculate_site_revenue(site.id)
                if metrics:
                    site_summaries.append(asdict(metrics))
                    total_hashrate += metrics.total_hashrate_th
                    total_power_mw += metrics.total_power_mw
                    total_daily_btc += metrics.daily_btc_total
                    total_daily_usd += metrics.daily_usd_total
                    total_daily_cost += metrics.daily_power_cost_total
                    total_miners += metrics.total_miners
                    online_miners += metrics.online_miners
            
            return {
                'type': 'global',
                'summary': {
                    'total_sites': len(sites),
                    'total_miners': total_miners,
                    'online_miners': online_miners,
                    'online_rate': (online_miners / total_miners * 100) if total_miners > 0 else 0,
                    'total_hashrate_th': total_hashrate,
                    'total_hashrate_ph': total_hashrate / 1000,
                    'total_power_mw': total_power_mw,
                    'daily_btc_total': total_daily_btc,
                    'daily_usd_total': total_daily_usd,
                    'daily_power_cost_total': total_daily_cost,
                    'daily_net_profit_total': total_daily_usd - total_daily_cost,
                    'monthly_btc_estimate': total_daily_btc * 30,
                    'monthly_usd_estimate': total_daily_usd * 30
                },
                'sites': site_summaries,
                'market_data': {
                    'btc_price': self._btc_price,
                    'difficulty': self._difficulty,
                    'block_reward': self._block_reward,
                    'source': self._data_source,
                    'last_update': self._last_update.isoformat() if self._last_update else None
                }
            }
            
        except Exception as e:
            logger.error(f"获取收益汇总失败: {e}")
            return {
                'type': 'error',
                'error': str(e),
                'market_data': {
                    'btc_price': self._btc_price,
                    'difficulty': self._difficulty,
                    'block_reward': self._block_reward,
                    'source': self._data_source
                }
            }
    
    def project_24h_revenue(
        self, 
        miner_id: int,
        historical_hours: int = 6
    ) -> Dict[str, Any]:
        try:
            from models import HostingMiner, MinerTelemetry
            
            miner = HostingMiner.query.get(miner_id)
            if not miner:
                return {'error': 'Miner not found'}
            
            since = datetime.utcnow() - timedelta(hours=historical_hours)
            telemetry = MinerTelemetry.query.filter(
                MinerTelemetry.miner_id == miner_id,
                MinerTelemetry.timestamp >= since
            ).order_by(MinerTelemetry.timestamp.desc()).all()
            
            if not telemetry:
                current = self.calculate_miner_revenue(
                    miner_id=miner.id,
                    serial_number=miner.serial_number,
                    model_name=miner.miner_model.model_name if miner.miner_model else "",
                    hashrate_th=miner.actual_hashrate or 0,
                    power_w=miner.actual_power or 0,
                    electricity_rate=0.06,
                    health_score=miner.health_score or 100
                )
                return {
                    'miner_id': miner_id,
                    'projection_type': 'static',
                    'projected_24h_btc': current.daily_btc,
                    'projected_24h_usd': current.daily_usd,
                    'projected_24h_cost': current.daily_power_cost,
                    'projected_24h_profit': current.daily_net_profit,
                    'confidence': 'low',
                    'data_points': 0
                }
            
            avg_hashrate = sum(t.hashrate for t in telemetry if t.hashrate) / len(telemetry)
            avg_power = sum(t.power_consumption for t in telemetry if t.power_consumption) / len(telemetry)
            
            uptime_ratio = sum(1 for t in telemetry if t.online) / len(telemetry)
            
            projected = self.calculate_miner_revenue(
                miner_id=miner.id,
                serial_number=miner.serial_number,
                model_name=miner.miner_model.model_name if miner.miner_model else "",
                hashrate_th=avg_hashrate * uptime_ratio,
                power_w=avg_power * uptime_ratio,
                electricity_rate=0.06,
                health_score=miner.health_score or 100
            )
            
            confidence = 'high' if len(telemetry) >= historical_hours * 6 else 'medium' if len(telemetry) >= 10 else 'low'
            
            return {
                'miner_id': miner_id,
                'projection_type': 'dynamic',
                'projected_24h_btc': projected.daily_btc,
                'projected_24h_usd': projected.daily_usd,
                'projected_24h_cost': projected.daily_power_cost,
                'projected_24h_profit': projected.daily_net_profit,
                'confidence': confidence,
                'data_points': len(telemetry),
                'avg_hashrate_th': avg_hashrate,
                'avg_power_w': avg_power,
                'uptime_ratio': uptime_ratio
            }
            
        except Exception as e:
            logger.error(f"24小时收益预测失败: {e}")
            return {'error': str(e)}


_revenue_service: Optional[HostingRevenueService] = None

def get_revenue_service() -> HostingRevenueService:
    global _revenue_service
    if _revenue_service is None:
        _revenue_service = HostingRevenueService()
    return _revenue_service
