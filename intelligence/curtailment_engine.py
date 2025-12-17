"""
限电策略引擎 Power Curtailment Strategy Engine
==============================================

智能矿机选择算法，用于在电网限电时自动选择关闭哪些矿机
Intelligent miner selection algorithms for automatic shutdown during power curtailment

实现4种策略:
Implements 4 strategies:
1. 性能优先 Performance Priority - 关闭低性能矿机
2. 客户优先 Customer Priority - 保护VIP客户
3. 公平分配 Fair Distribution - 按比例分配
4. 自定义规则 Custom Rules - 灵活配置

Author: HashInsight Intelligence Team
Created: 2025-11-11
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from collections import defaultdict

from sqlalchemy import func, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app import db
from models import (
    HostingMiner, MinerPerformanceScore, MinerModel, UserAccess,
    CurtailmentStrategy, StrategyType
)

logger = logging.getLogger(__name__)


def get_miners_with_performance(site_id: int) -> List[Dict]:
    """
    查询站点所有矿机及其最新性能评分
    Query all miners at a site with their latest performance scores
    
    Args:
        site_id: 站点ID Site ID
        
    Returns:
        List of dicts containing miner data:
        [
            {
                'miner_id': int,
                'serial_number': str,
                'customer_id': int,
                'customer_name': str,
                'customer_tier': str,  # 'VIP', 'Enterprise', 'Standard'
                'model_name': str,
                'performance_score': float,
                'actual_power': float,  # in watts
                'actual_hashrate': float,  # in TH/s
                'status': str,
                'install_date': datetime,
                'last_maintenance': datetime,
                'uptime_ratio': float
            },
            ...
        ]
    """
    try:
        logger.info(f"查询站点 {site_id} 的矿机及性能评分 Querying miners with performance for site {site_id}")
        
        # 子查询：获取每个矿机的最新性能评分
        # Subquery: Get latest performance score for each miner
        latest_scores_subq = db.session.query(  # type: ignore[misc]
            MinerPerformanceScore.miner_id,  # type: ignore[misc]
            func.max(MinerPerformanceScore.calculated_at).label('latest_calculated_at')  # type: ignore[misc]
        ).group_by(MinerPerformanceScore.miner_id).subquery()  # type: ignore[misc]
        
        # 主查询：JOIN所有相关表
        # Main query: JOIN all relevant tables
        query = db.session.query(  # type: ignore[misc]
            HostingMiner.id.label('miner_id'),  # type: ignore[misc]
            HostingMiner.serial_number,  # type: ignore[misc]
            HostingMiner.customer_id,  # type: ignore[misc]
            UserAccess.name.label('customer_name'),  # type: ignore[misc]
            UserAccess.subscription_plan.label('customer_tier'),  # type: ignore[misc]
            MinerModel.model_name,  # type: ignore[misc]
            MinerPerformanceScore.performance_score,  # type: ignore[misc]
            HostingMiner.actual_power,  # type: ignore[misc]
            HostingMiner.actual_hashrate,  # type: ignore[misc]
            HostingMiner.status,  # type: ignore[misc]
            HostingMiner.install_date,  # type: ignore[misc]
            HostingMiner.last_maintenance,  # type: ignore[misc]
            MinerPerformanceScore.uptime_ratio  # type: ignore[misc]
        ).join(  # type: ignore[misc]
            UserAccess,  # type: ignore[misc]
            HostingMiner.customer_id == UserAccess.id  # type: ignore[misc]
        ).join(  # type: ignore[misc]
            MinerModel,  # type: ignore[misc]
            HostingMiner.miner_model_id == MinerModel.id  # type: ignore[misc]
        ).outerjoin(  # type: ignore[misc]
            latest_scores_subq,  # type: ignore[misc]
            HostingMiner.id == latest_scores_subq.c.miner_id  # type: ignore[misc]
        ).outerjoin(  # type: ignore[misc]
            MinerPerformanceScore,  # type: ignore[misc]
            (MinerPerformanceScore.miner_id == HostingMiner.id) &  # type: ignore[misc]
            (MinerPerformanceScore.calculated_at == latest_scores_subq.c.latest_calculated_at)  # type: ignore[misc]
        ).filter(  # type: ignore[misc]
            HostingMiner.site_id == site_id  # type: ignore[misc]
        ).all()  # type: ignore[misc]
        
        miners_data = []
        for row in query:
            # 将subscription_plan映射到customer_tier
            # Map subscription_plan to customer_tier
            tier_mapping = {
                'pro': 'VIP',
                'basic': 'Enterprise',
                'free': 'Standard'
            }
            customer_tier = tier_mapping.get(row.customer_tier, 'Standard')
            
            miners_data.append({
                'miner_id': row.miner_id,
                'serial_number': row.serial_number,
                'customer_id': row.customer_id,
                'customer_name': row.customer_name,
                'customer_tier': customer_tier,
                'model_name': row.model_name,
                'performance_score': float(row.performance_score) if row.performance_score else 0.0,
                'actual_power': float(row.actual_power),
                'actual_hashrate': float(row.actual_hashrate),
                'status': row.status,
                'install_date': row.install_date,
                'last_maintenance': row.last_maintenance,
                'uptime_ratio': float(row.uptime_ratio) if row.uptime_ratio else 0.0
            })
        
        logger.info(f"找到 {len(miners_data)} 个矿机 Found {len(miners_data)} miners")
        
        return miners_data
        
    except SQLAlchemyError as e:
        logger.error(f"查询矿机数据失败 Failed to query miner data: {e}")
        db.session.rollback()
        return []
    except Exception as e:
        logger.error(f"获取矿机性能数据时发生错误 Error in get_miners_with_performance: {e}")
        return []


def performance_priority_strategy(miners: List[Dict], target_power_kw: float) -> List[int]:
    """
    策略1：性能优先 Strategy 1: Performance Priority
    
    从性能评分最低的矿机开始关闭，直到达到目标功率削减
    Shut down miners starting from lowest performance score until target power reduction is achieved
    
    算法逻辑 Algorithm:
    1. 按performance_score升序排列 Sort by performance_score ascending
    2. 累加功率直到达到目标 Accumulate power until target is reached
    3. 优先关闭评分为0的矿机（无数据或离线） Prioritize miners with score 0 (no data/offline)
    
    Args:
        miners: 矿机列表 List of miner dicts
        target_power_kw: 目标削减功率(kW) Target power reduction in kW
        
    Returns:
        List of miner IDs to shut down
    """
    try:
        logger.info(f"执行性能优先策略 Executing performance priority strategy")
        logger.info(f"目标削减功率：{target_power_kw} kW Target power reduction: {target_power_kw} kW")
        
        if not miners:
            logger.warning("无可用矿机 No miners available")
            return []
        
        # 按性能评分升序排序（评分越低越先关闭）
        # Sort by performance score ascending (lower score = shut down first)
        sorted_miners = sorted(miners, key=lambda m: m['performance_score'])
        
        selected_miners = []
        accumulated_power = 0.0
        target_power_w = target_power_kw * 1000  # 转换为瓦特 Convert to watts
        
        for miner in sorted_miners:
            if accumulated_power >= target_power_w:
                break
            
            selected_miners.append(miner['miner_id'])
            accumulated_power += miner['actual_power']
            
            logger.debug(
                f"选择关闭矿机 Selected miner: ID={miner['miner_id']}, "
                f"Score={miner['performance_score']:.2f}, "
                f"Power={miner['actual_power']}W, "
                f"累计功率 Accumulated={accumulated_power/1000:.2f}kW"
            )
        
        logger.info(
            f"性能优先策略完成 Performance priority strategy completed: "
            f"选择了 {len(selected_miners)} 个矿机，累计削减 {accumulated_power/1000:.2f}kW "
            f"Selected {len(selected_miners)} miners, total reduction {accumulated_power/1000:.2f}kW"
        )
        
        return selected_miners
        
    except Exception as e:
        logger.error(f"性能优先策略执行失败 Performance priority strategy failed: {e}")
        return []


def customer_priority_strategy(
    miners: List[Dict], 
    target_power_kw: float, 
    vip_protection: bool = True
) -> List[int]:
    """
    策略2：客户优先级混合 Strategy 2: Customer Priority
    
    保护VIP客户，优先关闭普通客户的低性能矿机
    Protect VIP customers, prioritize shutting down Standard customers' low-performance miners
    
    算法逻辑 Algorithm:
    1. 第一轮：只选择非VIP客户(Standard/Enterprise)的低性能矿机
       Round 1: Select only non-VIP (Standard/Enterprise) customers' low-performance miners
    2. 第二轮：如果功率不足，再从VIP客户中选择低性能矿机
       Round 2: If power insufficient, select from VIP customers' low-performance miners
    
    客户等级优先级 Customer tier priority:
    - Standard: 最先关闭 Shut down first
    - Enterprise: 其次 Second priority
    - VIP: 最后保护 Last to shut down (protected if vip_protection=True)
    
    Args:
        miners: 矿机列表 List of miner dicts
        target_power_kw: 目标削减功率(kW) Target power reduction in kW
        vip_protection: 是否启用VIP保护 Whether to enable VIP protection
        
    Returns:
        List of miner IDs to shut down
    """
    try:
        logger.info(f"执行客户优先级策略 Executing customer priority strategy")
        logger.info(f"VIP保护：{'启用' if vip_protection else '禁用'} VIP protection: {'enabled' if vip_protection else 'disabled'}")
        logger.info(f"目标削减功率：{target_power_kw} kW Target power reduction: {target_power_kw} kW")
        
        if not miners:
            logger.warning("无可用矿机 No miners available")
            return []
        
        # 按客户等级和性能评分分组
        # Group by customer tier and performance score
        tier_priority = {
            'Standard': 1,
            'Enterprise': 2,
            'VIP': 3
        }
        
        # 排序：先按客户等级优先级，再按性能评分
        # Sort: first by tier priority, then by performance score
        sorted_miners = sorted(
            miners, 
            key=lambda m: (tier_priority.get(m['customer_tier'], 1), m['performance_score'])
        )
        
        selected_miners = []
        accumulated_power = 0.0
        target_power_w = target_power_kw * 1000
        
        # 第一轮：只选择非VIP客户的矿机（如果启用VIP保护）
        # Round 1: Select only non-VIP customers' miners (if VIP protection enabled)
        if vip_protection:
            logger.info("第一轮：选择非VIP客户的矿机 Round 1: Selecting non-VIP customers' miners")
            for miner in sorted_miners:
                if accumulated_power >= target_power_w:
                    break
                
                if miner['customer_tier'] != 'VIP':
                    selected_miners.append(miner['miner_id'])
                    accumulated_power += miner['actual_power']
                    
                    logger.debug(
                        f"选择关闭矿机 Selected miner: ID={miner['miner_id']}, "
                        f"Customer={miner['customer_name']} ({miner['customer_tier']}), "
                        f"Score={miner['performance_score']:.2f}, "
                        f"累计功率 Accumulated={accumulated_power/1000:.2f}kW"
                    )
        
        # 第二轮：如果功率不足，从VIP客户中选择
        # Round 2: If power insufficient, select from VIP customers
        if accumulated_power < target_power_w:
            if vip_protection:
                logger.warning(
                    f"第一轮功率不足({accumulated_power/1000:.2f}kW < {target_power_kw}kW)，"
                    f"进入第二轮选择VIP客户矿机 "
                    f"Round 1 insufficient ({accumulated_power/1000:.2f}kW < {target_power_kw}kW), "
                    f"proceeding to Round 2: selecting VIP customers' miners"
                )
            
            for miner in sorted_miners:
                if accumulated_power >= target_power_w:
                    break
                
                if miner['miner_id'] not in selected_miners:
                    selected_miners.append(miner['miner_id'])
                    accumulated_power += miner['actual_power']
                    
                    logger.debug(
                        f"选择关闭矿机 Selected miner: ID={miner['miner_id']}, "
                        f"Customer={miner['customer_name']} ({miner['customer_tier']}), "
                        f"Score={miner['performance_score']:.2f}, "
                        f"累计功率 Accumulated={accumulated_power/1000:.2f}kW"
                    )
        
        logger.info(
            f"客户优先级策略完成 Customer priority strategy completed: "
            f"选择了 {len(selected_miners)} 个矿机，累计削减 {accumulated_power/1000:.2f}kW "
            f"Selected {len(selected_miners)} miners, total reduction {accumulated_power/1000:.2f}kW"
        )
        
        return selected_miners
        
    except Exception as e:
        logger.error(f"客户优先级策略执行失败 Customer priority strategy failed: {e}")
        return []


def fair_distribution_strategy(miners: List[Dict], target_power_kw: float) -> List[int]:
    """
    策略3：公平分配 Strategy 3: Fair Distribution
    
    按客户拥有矿机数量比例分配关机数量
    Distribute shutdowns proportionally based on number of miners owned by each customer
    
    算法逻辑 Algorithm:
    1. 统计每个客户的矿机数量和总功率
       Count number of miners and total power for each customer
    2. 按比例计算每个客户需要关闭的矿机数量
       Calculate proportional number of miners to shut down per customer
    3. 在每个客户内部按性能评分选择关闭对象
       Within each customer, select miners by performance score
    
    Args:
        miners: 矿机列表 List of miner dicts
        target_power_kw: 目标削减功率(kW) Target power reduction in kW
        
    Returns:
        List of miner IDs to shut down
    """
    try:
        logger.info(f"执行公平分配策略 Executing fair distribution strategy")
        logger.info(f"目标削减功率：{target_power_kw} kW Target power reduction: {target_power_kw} kW")
        
        if not miners:
            logger.warning("无可用矿机 No miners available")
            return []
        
        # 按客户分组
        # Group by customer
        customer_miners = defaultdict(list)
        for miner in miners:
            customer_miners[miner['customer_id']].append(miner)
        
        total_miners_count = len(miners)
        target_power_w = target_power_kw * 1000
        
        # 计算总功率
        # Calculate total power
        total_power = sum(m['actual_power'] for m in miners)
        
        logger.info(
            f"站点总矿机数：{total_miners_count}，总功率：{total_power/1000:.2f}kW "
            f"Total miners: {total_miners_count}, Total power: {total_power/1000:.2f}kW"
        )
        logger.info(f"客户数量：{len(customer_miners)} Number of customers: {len(customer_miners)}")
        
        selected_miners = []
        accumulated_power = 0.0
        
        # 按每个客户的功率占比分配削减目标
        # Allocate reduction target proportionally by each customer's power share
        for customer_id, customer_miner_list in customer_miners.items():
            if accumulated_power >= target_power_w:
                break
            
            # 计算该客户的总功率和占比
            # Calculate total power and share for this customer
            customer_total_power = sum(m['actual_power'] for m in customer_miner_list)
            customer_power_ratio = customer_total_power / total_power
            
            # 该客户应承担的削减功率
            # Power reduction allocated to this customer
            customer_target_power = target_power_w * customer_power_ratio
            
            logger.debug(
                f"客户 Customer {customer_id} ({customer_miner_list[0]['customer_name']}): "
                f"{len(customer_miner_list)} 个矿机, "
                f"总功率 Total power {customer_total_power/1000:.2f}kW ({customer_power_ratio*100:.1f}%), "
                f"分配削减目标 Allocated target {customer_target_power/1000:.2f}kW"
            )
            
            # 在该客户内部按性能评分排序
            # Sort within customer by performance score
            sorted_customer_miners = sorted(customer_miner_list, key=lambda m: m['performance_score'])
            
            customer_accumulated = 0.0
            for miner in sorted_customer_miners:
                if customer_accumulated >= customer_target_power:
                    break
                
                if accumulated_power >= target_power_w:
                    break
                
                selected_miners.append(miner['miner_id'])
                customer_accumulated += miner['actual_power']
                accumulated_power += miner['actual_power']
                
                logger.debug(
                    f"  选择矿机 Selected miner: ID={miner['miner_id']}, "
                    f"Score={miner['performance_score']:.2f}, "
                    f"客户累计 Customer accumulated={customer_accumulated/1000:.2f}kW"
                )
        
        logger.info(
            f"公平分配策略完成 Fair distribution strategy completed: "
            f"选择了 {len(selected_miners)} 个矿机，累计削减 {accumulated_power/1000:.2f}kW "
            f"Selected {len(selected_miners)} miners, total reduction {accumulated_power/1000:.2f}kW"
        )
        
        return selected_miners
        
    except Exception as e:
        logger.error(f"公平分配策略执行失败 Fair distribution strategy failed: {e}")
        return []


def custom_rules_strategy(
    miners: List[Dict], 
    target_power_kw: float, 
    rules_config: Optional[Dict] = None
) -> List[int]:
    """
    策略4：自定义规则引擎 Strategy 4: Custom Rules Engine
    
    支持灵活的规则配置，可组合多种筛选条件
    Supports flexible rule configuration with multiple filter conditions
    
    可用规则 Available rules:
    - min_uptime_threshold: 最低在线时间阈值 Minimum uptime threshold (0.0-1.0)
    - exclude_recent_maintenance_days: 排除最近N天维护过的矿机 Exclude miners maintained in last N days
    - temperature_priority: 优先关闭高温矿机 Prioritize high-temperature miners
    - max_performance_threshold: 最大性能阈值，只关闭低于此阈值的矿机 Max performance threshold
    - customer_tier_filter: 客户等级过滤 Customer tier filter list
    
    Args:
        miners: 矿机列表 List of miner dicts
        target_power_kw: 目标削减功率(kW) Target power reduction in kW
        rules_config: 规则配置字典 Rules configuration dict
        
    Returns:
        List of miner IDs to shut down
        
    Example rules_config:
        {
            'min_uptime_threshold': 0.8,
            'exclude_recent_maintenance_days': 7,
            'temperature_priority': True,
            'max_performance_threshold': 50.0,
            'customer_tier_filter': ['Standard', 'Enterprise']
        }
    """
    try:
        logger.info(f"执行自定义规则策略 Executing custom rules strategy")
        logger.info(f"目标削减功率：{target_power_kw} kW Target power reduction: {target_power_kw} kW")
        
        if not miners:
            logger.warning("无可用矿机 No miners available")
            return []
        
        if rules_config is None:
            rules_config = {}
        
        logger.info(f"规则配置 Rules config: {rules_config}")
        
        # 应用规则过滤矿机
        # Apply rules to filter miners
        eligible_miners = miners.copy()
        
        # 规则1：最低在线时间阈值
        # Rule 1: Minimum uptime threshold
        if 'min_uptime_threshold' in rules_config:
            min_uptime = rules_config['min_uptime_threshold']
            before_count = len(eligible_miners)
            eligible_miners = [m for m in eligible_miners if m['uptime_ratio'] >= min_uptime]
            logger.info(
                f"应用在线时间阈值规则 Applied uptime threshold rule (>={min_uptime}): "
                f"{before_count} -> {len(eligible_miners)} 个矿机 miners"
            )
        
        # 规则2：排除最近维护过的矿机
        # Rule 2: Exclude recently maintained miners
        if 'exclude_recent_maintenance_days' in rules_config:
            days = rules_config['exclude_recent_maintenance_days']
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            before_count = len(eligible_miners)
            eligible_miners = [
                m for m in eligible_miners 
                if m['last_maintenance'] is None or m['last_maintenance'] < cutoff_date
            ]
            logger.info(
                f"应用排除近期维护规则 Applied recent maintenance exclusion rule ({days} days): "
                f"{before_count} -> {len(eligible_miners)} 个矿机 miners"
            )
        
        # 规则3：最大性能阈值（只关闭低性能矿机）
        # Rule 3: Maximum performance threshold (only shut down low-performance miners)
        if 'max_performance_threshold' in rules_config:
            max_perf = rules_config['max_performance_threshold']
            before_count = len(eligible_miners)
            eligible_miners = [m for m in eligible_miners if m['performance_score'] <= max_perf]
            logger.info(
                f"应用性能阈值规则 Applied performance threshold rule (<={max_perf}): "
                f"{before_count} -> {len(eligible_miners)} 个矿机 miners"
            )
        
        # 规则4：客户等级过滤
        # Rule 4: Customer tier filter
        if 'customer_tier_filter' in rules_config:
            tier_filter = rules_config['customer_tier_filter']
            before_count = len(eligible_miners)
            eligible_miners = [m for m in eligible_miners if m['customer_tier'] in tier_filter]
            logger.info(
                f"应用客户等级过滤规则 Applied customer tier filter rule ({tier_filter}): "
                f"{before_count} -> {len(eligible_miners)} 个矿机 miners"
            )
        
        if not eligible_miners:
            logger.warning("应用规则后无符合条件的矿机 No eligible miners after applying rules")
            return []
        
        # 排序：根据是否启用温度优先
        # Sort: based on whether temperature priority is enabled
        if rules_config.get('temperature_priority', False):
            logger.info("启用温度优先排序 Temperature priority sorting enabled")
            # 按性能评分排序（温度数据在遥测中，这里用性能评分代替）
            # Sort by performance score (temperature data is in telemetry, using performance score as proxy)
            sorted_miners = sorted(eligible_miners, key=lambda m: m['performance_score'])
        else:
            # 默认按性能评分排序
            # Default sort by performance score
            sorted_miners = sorted(eligible_miners, key=lambda m: m['performance_score'])
        
        # 选择矿机直到达到目标功率
        # Select miners until target power is reached
        selected_miners = []
        accumulated_power = 0.0
        target_power_w = target_power_kw * 1000
        
        for miner in sorted_miners:
            if accumulated_power >= target_power_w:
                break
            
            selected_miners.append(miner['miner_id'])
            accumulated_power += miner['actual_power']
            
            logger.debug(
                f"选择关闭矿机 Selected miner: ID={miner['miner_id']}, "
                f"Score={miner['performance_score']:.2f}, "
                f"Uptime={miner['uptime_ratio']:.2f}, "
                f"累计功率 Accumulated={accumulated_power/1000:.2f}kW"
            )
        
        logger.info(
            f"自定义规则策略完成 Custom rules strategy completed: "
            f"选择了 {len(selected_miners)} 个矿机，累计削减 {accumulated_power/1000:.2f}kW "
            f"Selected {len(selected_miners)} miners, total reduction {accumulated_power/1000:.2f}kW"
        )
        
        return selected_miners
        
    except Exception as e:
        logger.error(f"自定义规则策略执行失败 Custom rules strategy failed: {e}")
        return []


def calculate_economic_impact(
    selected_miners: List[Dict], 
    duration_hours: int = 24,
    btc_price: float = 40000.0,
    electricity_rate: float = 0.08
) -> Dict:
    """
    计算关机的经济影响 Calculate economic impact of shutting down miners
    
    考虑因素 Factors considered:
    - 节省的电费 Electricity cost saved
    - 损失的BTC挖矿收益 BTC mining revenue lost
    - 净节省/损失 Net savings/loss
    
    Args:
        selected_miners: 被选中关闭的矿机列表 List of selected miners to shut down
        duration_hours: 关机时长（小时）Shutdown duration in hours
        btc_price: BTC价格（美元）BTC price in USD
        electricity_rate: 电价（美元/kWh）Electricity rate in $/kWh
        
    Returns:
        Dict containing:
        {
            'power_saved_kwh': float,  # 节省电量(kWh)
            'cost_saved_usd': float,  # 节省电费(USD)
            'revenue_lost_usd': float,  # 损失收益(USD)
            'net_savings_usd': float,  # 净节省(USD, 可为负)
            'affected_customers_count': int,  # 受影响客户数
            'miners_shutdown_count': int  # 关机矿机数
        }
    """
    try:
        logger.info(f"计算经济影响 Calculating economic impact for {len(selected_miners)} miners")
        
        if not selected_miners:
            return {
                'power_saved_kwh': 0.0,
                'cost_saved_usd': 0.0,
                'revenue_lost_usd': 0.0,
                'net_savings_usd': 0.0,
                'affected_customers_count': 0,
                'miners_shutdown_count': 0
            }
        
        # 计算总功率（kW）
        # Calculate total power (kW)
        total_power_kw = sum(m['actual_power'] for m in selected_miners) / 1000
        
        # 计算节省的电量（kWh）
        # Calculate power saved (kWh)
        power_saved_kwh = total_power_kw * duration_hours
        
        # 计算节省的电费（USD）
        # Calculate electricity cost saved (USD)
        cost_saved_usd = power_saved_kwh * electricity_rate
        
        # 计算总算力（TH/s）
        # Calculate total hashrate (TH/s)
        total_hashrate_ths = sum(m['actual_hashrate'] for m in selected_miners)
        
        # 简化的BTC收益计算（实际应考虑难度、区块奖励等）
        # Simplified BTC revenue calculation (should consider difficulty, block reward, etc.)
        # 假设：1 TH/s 每天产出约 0.00001 BTC (这是一个粗略估计)
        # Assumption: 1 TH/s produces ~0.00001 BTC per day (rough estimate)
        btc_per_ths_per_day = 0.00001
        btc_per_ths_per_hour = btc_per_ths_per_day / 24
        
        btc_lost = total_hashrate_ths * btc_per_ths_per_hour * duration_hours
        revenue_lost_usd = btc_lost * btc_price
        
        # 计算净节省（正值表示节省，负值表示损失）
        # Calculate net savings (positive = savings, negative = loss)
        net_savings_usd = cost_saved_usd - revenue_lost_usd
        
        # 统计受影响的客户数量
        # Count affected customers
        affected_customers = set(m['customer_id'] for m in selected_miners)
        affected_customers_count = len(affected_customers)
        
        result = {
            'power_saved_kwh': round(power_saved_kwh, 2),
            'cost_saved_usd': round(cost_saved_usd, 2),
            'revenue_lost_usd': round(revenue_lost_usd, 2),
            'net_savings_usd': round(net_savings_usd, 2),
            'affected_customers_count': affected_customers_count,
            'miners_shutdown_count': len(selected_miners),
            'btc_lost': round(btc_lost, 6)
        }
        
        logger.info(
            f"经济影响分析 Economic impact analysis: "
            f"节省电量 Power saved={power_saved_kwh:.2f}kWh, "
            f"节省电费 Cost saved=${cost_saved_usd:.2f}, "
            f"损失收益 Revenue lost=${revenue_lost_usd:.2f}, "
            f"净节省 Net savings=${net_savings_usd:.2f}, "
            f"BTC损失 BTC lost={btc_lost:.6f}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"计算经济影响失败 Failed to calculate economic impact: {e}")
        return {
            'power_saved_kwh': 0.0,
            'cost_saved_usd': 0.0,
            'revenue_lost_usd': 0.0,
            'net_savings_usd': 0.0,
            'affected_customers_count': 0,
            'miners_shutdown_count': 0,
            'error': str(e)
        }


def calculate_curtailment_plan(
    site_id: int, 
    strategy_id: int, 
    target_power_reduction_kw: float,
    btc_price: Optional[float] = None,
    electricity_rate: Optional[float] = None,
    duration_hours: int = 24
) -> Dict:
    """
    主函数：根据策略计算限电方案
    Main function: Calculate curtailment plan based on strategy
    
    工作流程 Workflow:
    1. 查询站点矿机及性能数据 Query site miners and performance data
    2. 读取策略配置 Read strategy configuration
    3. 根据策略类型调用相应算法 Call appropriate algorithm based on strategy type
    4. 计算经济影响 Calculate economic impact
    5. 返回完整方案 Return complete plan
    
    Args:
        site_id: 站点ID Site ID
        strategy_id: 策略ID Strategy ID
        target_power_reduction_kw: 目标削减功率(kW) Target power reduction in kW
        btc_price: BTC价格（可选，默认从数据库获取）BTC price (optional)
        electricity_rate: 电价（可选，默认从站点获取）Electricity rate (optional)
        duration_hours: 预计关机时长（小时）Expected shutdown duration in hours
        
    Returns:
        Dict containing:
        {
            'success': bool,
            'strategy_name': str,
            'strategy_type': str,
            'selected_miners': List[Dict],  # 被选中关闭的矿机详细信息
            'total_power_saved_kw': float,  # 实际削减功率
            'affected_customers': List[Dict],  # 受影响客户列表
            'economic_impact': Dict,  # 经济影响分析
            'execution_time': str,  # 执行时间
            'warnings': List[str]  # 警告信息
        }
    """
    try:
        logger.info(
            f"开始计算限电方案 Starting curtailment plan calculation: "
            f"site_id={site_id}, strategy_id={strategy_id}, "
            f"target={target_power_reduction_kw}kW"
        )
        
        start_time = datetime.utcnow()
        warnings = []
        
        # 1. 查询策略配置
        # 1. Query strategy configuration
        strategy = CurtailmentStrategy.query.get(strategy_id)
        if not strategy:
            logger.error(f"策略不存在 Strategy not found: {strategy_id}")
            return {
                'success': False,
                'error': f'Strategy {strategy_id} not found',
                'selected_miners': [],
                'total_power_saved_kw': 0.0,
                'affected_customers': [],
                'economic_impact': {}
            }
        
        if strategy.site_id != site_id:
            logger.error(f"策略不属于该站点 Strategy does not belong to site: {strategy_id} != {site_id}")
            return {
                'success': False,
                'error': f'Strategy {strategy_id} does not belong to site {site_id}',
                'selected_miners': [],
                'total_power_saved_kw': 0.0,
                'affected_customers': [],
                'economic_impact': {}
            }
        
        if not strategy.is_active:
            logger.warning(f"策略未激活 Strategy is not active: {strategy_id}")
            warnings.append(f"Strategy {strategy.name} is not active")
        
        logger.info(f"使用策略 Using strategy: {strategy.name} ({strategy.strategy_type.value})")
        
        # 2. 获取站点矿机数据
        # 2. Get site miner data
        miners = get_miners_with_performance(site_id)
        
        if not miners:
            logger.error(f"站点无可用矿机 No miners available at site: {site_id}")
            return {
                'success': False,
                'error': f'No miners available at site {site_id}',
                'selected_miners': [],
                'total_power_saved_kw': 0.0,
                'affected_customers': [],
                'economic_impact': {}
            }
        
        # 检查目标功率是否合理
        # Check if target power is reasonable
        total_site_power_kw = sum(m['actual_power'] for m in miners) / 1000
        if target_power_reduction_kw > total_site_power_kw:
            logger.warning(
                f"目标削减功率({target_power_reduction_kw}kW)超过站点总功率({total_site_power_kw:.2f}kW) "
                f"Target power reduction ({target_power_reduction_kw}kW) exceeds total site power ({total_site_power_kw:.2f}kW)"
            )
            warnings.append(
                f"Target reduction {target_power_reduction_kw}kW exceeds total site power {total_site_power_kw:.2f}kW"
            )
        
        # 3. 根据策略类型调用相应算法
        # 3. Call appropriate algorithm based on strategy type
        selected_miner_ids = []
        
        if strategy.strategy_type == StrategyType.PERFORMANCE_PRIORITY:
            selected_miner_ids = performance_priority_strategy(miners, target_power_reduction_kw)
            
        elif strategy.strategy_type == StrategyType.CUSTOMER_PRIORITY:
            vip_protection = strategy.vip_customer_protection
            selected_miner_ids = customer_priority_strategy(
                miners, target_power_reduction_kw, vip_protection
            )
            
        elif strategy.strategy_type == StrategyType.FAIR_DISTRIBUTION:
            selected_miner_ids = fair_distribution_strategy(miners, target_power_reduction_kw)
            
        elif strategy.strategy_type == StrategyType.CUSTOM:
            # 构建自定义规则配置
            # Build custom rules configuration
            rules_config = {
                'min_uptime_threshold': float(strategy.min_uptime_threshold)
            }
            selected_miner_ids = custom_rules_strategy(miners, target_power_reduction_kw, rules_config)
            
        else:
            logger.error(f"未知策略类型 Unknown strategy type: {strategy.strategy_type}")
            return {
                'success': False,
                'error': f'Unknown strategy type: {strategy.strategy_type}',
                'selected_miners': [],
                'total_power_saved_kw': 0.0,
                'affected_customers': [],
                'economic_impact': {}
            }
        
        # 4. 获取被选中矿机的详细信息
        # 4. Get detailed info for selected miners
        selected_miners = [m for m in miners if m['miner_id'] in selected_miner_ids]
        
        if not selected_miners:
            logger.warning("未选中任何矿机 No miners selected")
            warnings.append("No miners were selected by the strategy")
        
        # 5. 计算实际削减功率
        # 5. Calculate actual power reduction
        total_power_saved_kw = sum(m['actual_power'] for m in selected_miners) / 1000
        
        # 6. 统计受影响客户
        # 6. Count affected customers
        affected_customer_ids = set(m['customer_id'] for m in selected_miners)
        affected_customers = []
        customer_miner_counts = defaultdict(int)
        customer_power_reduction = defaultdict(float)
        
        for miner in selected_miners:
            customer_miner_counts[miner['customer_id']] += 1
            customer_power_reduction[miner['customer_id']] += miner['actual_power'] / 1000
        
        for customer_id in affected_customer_ids:
            customer_miners = [m for m in selected_miners if m['customer_id'] == customer_id]
            if customer_miners:
                affected_customers.append({
                    'customer_id': customer_id,
                    'customer_name': customer_miners[0]['customer_name'],
                    'customer_tier': customer_miners[0]['customer_tier'],
                    'miners_affected': customer_miner_counts[customer_id],
                    'power_reduction_kw': round(customer_power_reduction[customer_id], 2)
                })
        
        # 7. 计算经济影响
        # 7. Calculate economic impact
        # 如果未提供BTC价格或电价，使用默认值
        # If BTC price or electricity rate not provided, use defaults
        if btc_price is None:
            btc_price = 40000.0  # 默认BTC价格 Default BTC price
            warnings.append(f"Using default BTC price: ${btc_price}")
        
        if electricity_rate is None:
            electricity_rate = 0.08  # 默认电价 $0.08/kWh
            warnings.append(f"Using default electricity rate: ${electricity_rate}/kWh")
        
        economic_impact = calculate_economic_impact(
            selected_miners, 
            duration_hours=duration_hours,
            btc_price=btc_price,
            electricity_rate=electricity_rate
        )
        
        # 8. 构建返回结果
        # 8. Build return result
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        result = {
            'success': True,
            'strategy_id': strategy.id,
            'strategy_name': strategy.name,
            'strategy_type': strategy.strategy_type.value,
            'site_id': site_id,
            'target_power_reduction_kw': target_power_reduction_kw,
            'total_power_saved_kw': round(total_power_saved_kw, 2),
            'selected_miners': selected_miners,
            'selected_miner_count': len(selected_miners),
            'affected_customers': affected_customers,
            'affected_customers_count': len(affected_customers),
            'economic_impact': economic_impact,
            'execution_time_seconds': round(execution_time, 3),
            'calculated_at': datetime.utcnow().isoformat(),
            'duration_hours': duration_hours,
            'warnings': warnings
        }
        
        logger.info(
            f"限电方案计算完成 Curtailment plan calculation completed: "
            f"选择了 {len(selected_miners)} 个矿机，"
            f"削减功率 {total_power_saved_kw:.2f}kW，"
            f"影响 {len(affected_customers)} 个客户，"
            f"耗时 {execution_time:.3f}秒 "
            f"Selected {len(selected_miners)} miners, "
            f"power reduction {total_power_saved_kw:.2f}kW, "
            f"affected {len(affected_customers)} customers, "
            f"execution time {execution_time:.3f}s"
        )
        
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"数据库错误 Database error in calculate_curtailment_plan: {e}")
        db.session.rollback()
        return {
            'success': False,
            'error': f'Database error: {str(e)}',
            'selected_miners': [],
            'total_power_saved_kw': 0.0,
            'affected_customers': [],
            'economic_impact': {}
        }
    except Exception as e:
        logger.error(f"计算限电方案失败 Failed to calculate curtailment plan: {e}")
        return {
            'success': False,
            'error': str(e),
            'selected_miners': [],
            'total_power_saved_kw': 0.0,
            'affected_customers': [],
            'economic_impact': {}
        }
