import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from db import db
from models import UserAccess, UserMiner, NetworkSnapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_user_mining_data(user_id: int) -> Optional[Dict]:
    """
    Get user's mining configuration and current metrics
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with user's mining data or None if user not found
    """
    try:
        user = db.session.query(UserAccess).filter_by(id=user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return None
        
        miners = db.session.query(UserMiner).filter_by(
            user_id=user_id, 
            status='active'
        ).all()
        
        if not miners:
            logger.warning(f"No active miners found for user {user_id}")
            return None
        
        total_hashrate = sum(m.calculate_total_hashrate() for m in miners)
        total_power = sum(m.calculate_total_power() for m in miners)
        avg_electricity_cost = np.mean([m.electricity_cost for m in miners])
        total_investment = sum(m.actual_price * m.quantity for m in miners)
        
        latest_network = db.session.query(NetworkSnapshot).order_by(
            NetworkSnapshot.recorded_at.desc()
        ).first()
        
        if not latest_network:
            logger.error("No network snapshot data available")
            return None
        
        return {
            'user_id': user_id,
            'total_hashrate': total_hashrate,
            'total_power': total_power,
            'electricity_cost': avg_electricity_cost,
            'total_investment': total_investment,
            'miner_count': len(miners),
            'miners': miners,
            'btc_price': latest_network.btc_price,
            'network_difficulty': latest_network.network_difficulty,
            'network_hashrate': latest_network.network_hashrate,
            'block_reward': latest_network.block_reward,
            'snapshot_time': latest_network.recorded_at
        }
        
    except Exception as e:
        logger.error(f"Error getting user mining data: {e}")
        return None


def _calculate_daily_revenue(hashrate_th: float, btc_price: float, 
                            network_difficulty: float, block_reward: float = 3.125) -> float:
    """
    Calculate daily mining revenue in USD
    
    Args:
        hashrate_th: Mining hashrate in TH/s
        btc_price: Bitcoin price in USD
        network_difficulty: Network difficulty
        block_reward: Block reward in BTC
        
    Returns:
        Daily revenue in USD
    """
    try:
        blocks_per_day = 144
        hashrate_hash_per_sec = hashrate_th * 1e12
        
        actual_difficulty = network_difficulty
        if network_difficulty < 1e6:
            actual_difficulty = network_difficulty * 1e12
        
        btc_per_day = (hashrate_hash_per_sec / (actual_difficulty * (2**32) / 600)) * blocks_per_day * block_reward
        daily_revenue_usd = btc_per_day * btc_price
        
        return daily_revenue_usd
    except Exception as e:
        logger.error(f"Error calculating daily revenue: {e}")
        return 0.0


def _calculate_daily_cost(power_watts: float, electricity_cost: float) -> float:
    """
    Calculate daily electricity cost in USD
    
    Args:
        power_watts: Power consumption in watts
        electricity_cost: Electricity cost in USD per kWh
        
    Returns:
        Daily cost in USD
    """
    try:
        daily_kwh = (power_watts / 1000) * 24
        daily_cost = daily_kwh * electricity_cost
        return daily_cost
    except Exception as e:
        logger.error(f"Error calculating daily cost: {e}")
        return 0.0


def calculate_roi_factors(user_id: int) -> Optional[Dict]:
    """
    Calculate ROI contribution analysis to explain what factors affect profitability
    
    Decomposes ROI into factors:
    - BTC price impact
    - Difficulty impact
    - Offline rate impact (hashrate efficiency)
    - Electricity cost impact
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with factor breakdown or None if error
    """
    try:
        logger.info(f"Calculating ROI factors for user {user_id}")
        
        user_data = _get_user_mining_data(user_id)
        if not user_data:
            return None
        
        hashrate = user_data['total_hashrate']
        power = user_data['total_power']
        electricity_cost = user_data['electricity_cost']
        btc_price = user_data['btc_price']
        difficulty = user_data['network_difficulty']
        block_reward = user_data['block_reward']
        investment = user_data['total_investment']
        
        base_daily_revenue = _calculate_daily_revenue(
            hashrate, btc_price, difficulty, block_reward
        )
        base_daily_cost = _calculate_daily_cost(power, electricity_cost)
        base_daily_profit = base_daily_revenue - base_daily_cost
        base_annual_profit = base_daily_profit * 365
        base_roi = (base_annual_profit / investment * 100) if investment > 0 else 0
        
        btc_price_sensitivity = 0.10
        btc_price_up = btc_price * (1 + btc_price_sensitivity)
        btc_price_down = btc_price * (1 - btc_price_sensitivity)
        
        revenue_up = _calculate_daily_revenue(hashrate, btc_price_up, difficulty, block_reward)
        revenue_down = _calculate_daily_revenue(hashrate, btc_price_down, difficulty, block_reward)
        
        profit_up = (revenue_up - base_daily_cost) * 365
        profit_down = (revenue_down - base_daily_cost) * 365
        
        roi_up = (profit_up / investment * 100) if investment > 0 else 0
        roi_down = (profit_down / investment * 100) if investment > 0 else 0
        
        btc_price_impact = ((roi_up - roi_down) / 2) / btc_price_sensitivity
        
        difficulty_sensitivity = 0.10
        difficulty_up = difficulty * (1 + difficulty_sensitivity)
        difficulty_down = difficulty * (1 - difficulty_sensitivity)
        
        revenue_diff_up = _calculate_daily_revenue(hashrate, btc_price, difficulty_up, block_reward)
        revenue_diff_down = _calculate_daily_revenue(hashrate, btc_price, difficulty_down, block_reward)
        
        profit_diff_up = (revenue_diff_up - base_daily_cost) * 365
        profit_diff_down = (revenue_diff_down - base_daily_cost) * 365
        
        roi_diff_up = (profit_diff_up / investment * 100) if investment > 0 else 0
        roi_diff_down = (profit_diff_down / investment * 100) if investment > 0 else 0
        
        difficulty_impact = ((roi_diff_down - roi_diff_up) / 2) / difficulty_sensitivity
        
        offline_sensitivity = 0.05
        hashrate_down = hashrate * (1 - offline_sensitivity)
        
        revenue_offline = _calculate_daily_revenue(hashrate_down, btc_price, difficulty, block_reward)
        profit_offline = (revenue_offline - base_daily_cost) * 365
        roi_offline = (profit_offline / investment * 100) if investment > 0 else 0
        
        offline_impact = (base_roi - roi_offline) / offline_sensitivity
        
        elec_sensitivity = 0.10
        elec_up = electricity_cost * (1 + elec_sensitivity)
        
        cost_up = _calculate_daily_cost(power, elec_up)
        profit_elec = (base_daily_revenue - cost_up) * 365
        roi_elec = (profit_elec / investment * 100) if investment > 0 else 0
        
        electricity_impact = (base_roi - roi_elec) / elec_sensitivity
        
        total_impact = abs(btc_price_impact) + abs(difficulty_impact) + abs(offline_impact) + abs(electricity_impact)
        
        if total_impact > 0:
            btc_price_contribution = (abs(btc_price_impact) / total_impact) * 100
            difficulty_contribution = (abs(difficulty_impact) / total_impact) * 100
            offline_contribution = (abs(offline_impact) / total_impact) * 100
            electricity_contribution = (abs(electricity_impact) / total_impact) * 100
        else:
            btc_price_contribution = difficulty_contribution = offline_contribution = electricity_contribution = 0
        
        result = {
            'user_id': user_id,
            'current_metrics': {
                'btc_price': btc_price,
                'network_difficulty': difficulty,
                'total_hashrate_th': hashrate,
                'electricity_cost': electricity_cost,
                'daily_revenue_usd': base_daily_revenue,
                'daily_cost_usd': base_daily_cost,
                'daily_profit_usd': base_daily_profit,
                'annual_roi_percent': base_roi,
                'investment_usd': investment
            },
            'factor_impacts': {
                'btc_price': {
                    'impact_per_10pct_change': btc_price_impact,
                    'contribution_percent': btc_price_contribution,
                    'description': f'10% BTC price change affects ROI by {btc_price_impact:.2f}%'
                },
                'difficulty': {
                    'impact_per_10pct_change': difficulty_impact,
                    'contribution_percent': difficulty_contribution,
                    'description': f'10% difficulty increase reduces ROI by {abs(difficulty_impact):.2f}%'
                },
                'offline_rate': {
                    'impact_per_5pct_offline': offline_impact,
                    'contribution_percent': offline_contribution,
                    'description': f'5% offline time reduces ROI by {offline_impact:.2f}%'
                },
                'electricity_cost': {
                    'impact_per_10pct_change': electricity_impact,
                    'contribution_percent': electricity_contribution,
                    'description': f'10% electricity cost increase reduces ROI by {abs(electricity_impact):.2f}%'
                }
            },
            'calculated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"ROI factors calculated successfully for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating ROI factors for user {user_id}: {e}")
        return None


def explain_roi_change(user_id: int, days_back: int = 30) -> Optional[Dict]:
    """
    Compare current ROI vs ROI from days_back and attribute changes to specific factors
    
    Args:
        user_id: User ID
        days_back: Number of days to look back (default: 30)
        
    Returns:
        Dictionary with ROI change explanation or None if error
    """
    try:
        logger.info(f"Explaining ROI change for user {user_id} over last {days_back} days")
        
        user_data = _get_user_mining_data(user_id)
        if not user_data:
            return None
        
        current_snapshot = db.session.query(NetworkSnapshot).order_by(
            NetworkSnapshot.recorded_at.desc()
        ).first()
        
        past_date = datetime.utcnow() - timedelta(days=days_back)
        historical_snapshot = db.session.query(NetworkSnapshot).filter(
            NetworkSnapshot.recorded_at <= past_date
        ).order_by(NetworkSnapshot.recorded_at.desc()).first()
        
        if not historical_snapshot:
            logger.warning(f"No historical data available for {days_back} days ago")
            return {
                'user_id': user_id,
                'error': f'No historical data available for {days_back} days ago',
                'current_roi': None,
                'historical_roi': None
            }
        
        hashrate = user_data['total_hashrate']
        power = user_data['total_power']
        electricity_cost = user_data['electricity_cost']
        investment = user_data['total_investment']
        
        current_revenue = _calculate_daily_revenue(
            hashrate, current_snapshot.btc_price, 
            current_snapshot.network_difficulty, current_snapshot.block_reward
        )
        current_cost = _calculate_daily_cost(power, electricity_cost)
        current_profit = (current_revenue - current_cost) * 365
        current_roi = (current_profit / investment * 100) if investment > 0 else 0
        
        historical_revenue = _calculate_daily_revenue(
            hashrate, historical_snapshot.btc_price,
            historical_snapshot.network_difficulty, historical_snapshot.block_reward
        )
        historical_cost = _calculate_daily_cost(power, electricity_cost)
        historical_profit = (historical_revenue - historical_cost) * 365
        historical_roi = (historical_profit / investment * 100) if investment > 0 else 0
        
        roi_change = current_roi - historical_roi
        roi_change_percent = (roi_change / abs(historical_roi) * 100) if historical_roi != 0 else 0
        
        btc_price_change = current_snapshot.btc_price - historical_snapshot.btc_price
        btc_price_change_pct = (btc_price_change / historical_snapshot.btc_price * 100)
        
        difficulty_change = current_snapshot.network_difficulty - historical_snapshot.network_difficulty
        difficulty_change_pct = (difficulty_change / historical_snapshot.network_difficulty * 100)
        
        revenue_if_same_price = _calculate_daily_revenue(
            hashrate, historical_snapshot.btc_price,
            current_snapshot.network_difficulty, current_snapshot.block_reward
        )
        profit_if_same_price = (revenue_if_same_price - current_cost) * 365
        roi_if_same_price = (profit_if_same_price / investment * 100) if investment > 0 else 0
        
        btc_price_contribution = current_roi - roi_if_same_price
        
        revenue_if_same_diff = _calculate_daily_revenue(
            hashrate, current_snapshot.btc_price,
            historical_snapshot.network_difficulty, current_snapshot.block_reward
        )
        profit_if_same_diff = (revenue_if_same_diff - current_cost) * 365
        roi_if_same_diff = (profit_if_same_diff / investment * 100) if investment > 0 else 0
        
        difficulty_contribution = roi_if_same_diff - current_roi
        
        residual = roi_change - (btc_price_contribution + difficulty_contribution)
        
        total_abs_contribution = (abs(btc_price_contribution) + 
                                  abs(difficulty_contribution) + 
                                  abs(residual))
        
        if total_abs_contribution > 0:
            btc_price_weight = (abs(btc_price_contribution) / total_abs_contribution) * 100
            difficulty_weight = (abs(difficulty_contribution) / total_abs_contribution) * 100
            other_weight = (abs(residual) / total_abs_contribution) * 100
        else:
            btc_price_weight = difficulty_weight = other_weight = 0
        
        main_drivers = []
        if abs(btc_price_contribution) > 0.5:
            direction = "increased" if btc_price_contribution > 0 else "decreased"
            main_drivers.append({
                'factor': 'BTC Price',
                'impact': btc_price_contribution,
                'weight': btc_price_weight,
                'description': f'BTC price {direction} by {abs(btc_price_change_pct):.1f}%, contributing {btc_price_contribution:+.2f}% to ROI'
            })
        
        if abs(difficulty_contribution) > 0.5:
            direction = "increased" if difficulty_change_pct > 0 else "decreased"
            main_drivers.append({
                'factor': 'Network Difficulty',
                'impact': -abs(difficulty_contribution) if difficulty_change_pct > 0 else abs(difficulty_contribution),
                'weight': difficulty_weight,
                'description': f'Difficulty {direction} by {abs(difficulty_change_pct):.1f}%, contributing {difficulty_contribution:+.2f}% to ROI'
            })
        
        main_drivers.sort(key=lambda x: abs(x['impact']), reverse=True)
        
        result = {
            'user_id': user_id,
            'time_period': {
                'days_back': days_back,
                'historical_date': historical_snapshot.recorded_at.isoformat(),
                'current_date': current_snapshot.recorded_at.isoformat()
            },
            'roi_comparison': {
                'historical_roi': historical_roi,
                'current_roi': current_roi,
                'roi_change': roi_change,
                'roi_change_percent': roi_change_percent,
                'trend': 'improved' if roi_change > 0 else 'declined' if roi_change < 0 else 'stable'
            },
            'market_changes': {
                'btc_price': {
                    'historical': historical_snapshot.btc_price,
                    'current': current_snapshot.btc_price,
                    'change_usd': btc_price_change,
                    'change_percent': btc_price_change_pct
                },
                'difficulty': {
                    'historical': historical_snapshot.network_difficulty,
                    'current': current_snapshot.network_difficulty,
                    'change': difficulty_change,
                    'change_percent': difficulty_change_pct
                }
            },
            'attribution': {
                'btc_price_contribution': btc_price_contribution,
                'difficulty_contribution': difficulty_contribution,
                'other_factors': residual,
                'total_change': roi_change
            },
            'main_drivers': main_drivers,
            'summary': _generate_roi_change_summary(
                roi_change, main_drivers, days_back
            )
        }
        
        logger.info(f"ROI change analysis completed for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error explaining ROI change for user {user_id}: {e}")
        return None


def _generate_roi_change_summary(roi_change: float, main_drivers: List[Dict], days_back: int) -> str:
    """Generate a human-readable summary of ROI change"""
    if roi_change > 0:
        trend = f"improved by {roi_change:.2f}%"
    elif roi_change < 0:
        trend = f"declined by {abs(roi_change):.2f}%"
    else:
        trend = "remained stable"
    
    summary = f"Your ROI has {trend} over the past {days_back} days. "
    
    if main_drivers:
        top_driver = main_drivers[0]
        summary += f"The primary factor was {top_driver['description']}. "
        
        if len(main_drivers) > 1:
            summary += f"Additionally, {main_drivers[1]['description']}."
    
    return summary


def get_optimization_recommendations(user_id: int) -> Optional[Dict]:
    """
    Analyze current operations and identify improvement opportunities
    
    Returns actionable recommendations with projected impact
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with optimization recommendations or None if error
    """
    try:
        logger.info(f"Generating optimization recommendations for user {user_id}")
        
        user_data = _get_user_mining_data(user_id)
        if not user_data:
            return None
        
        factors = calculate_roi_factors(user_id)
        if not factors:
            return None
        
        current_roi = factors['current_metrics']['annual_roi_percent']
        daily_profit = factors['current_metrics']['daily_profit_usd']
        
        recommendations = []
        
        hashrate = user_data['total_hashrate']
        power = user_data['total_power']
        electricity_cost = user_data['electricity_cost']
        btc_price = user_data['btc_price']
        difficulty = user_data['network_difficulty']
        block_reward = user_data['block_reward']
        investment = user_data['total_investment']
        
        offline_improvements = [
            {'reduction': 0.05, 'label': '5%'},
            {'reduction': 0.10, 'label': '10%'},
            {'reduction': 0.15, 'label': '15%'}
        ]
        
        for improvement in offline_improvements:
            improved_hashrate = hashrate * (1 + improvement['reduction'])
            improved_revenue = _calculate_daily_revenue(
                improved_hashrate, btc_price, difficulty, block_reward
            )
            improved_cost = _calculate_daily_cost(power, electricity_cost)
            improved_profit = (improved_revenue - improved_cost) * 365
            improved_roi = (improved_profit / investment * 100) if investment > 0 else 0
            
            roi_gain = improved_roi - current_roi
            
            if roi_gain > 0.5:
                recommendations.append({
                    'category': 'Uptime Optimization',
                    'priority': 'high' if roi_gain > 3 else 'medium',
                    'action': f'Reduce offline time by {improvement["label"]}',
                    'projected_impact': {
                        'roi_increase_percent': roi_gain,
                        'additional_annual_profit_usd': improved_profit - (daily_profit * 365),
                        'payback_improvement_days': None
                    },
                    'implementation_difficulty': 'medium',
                    'description': f'Improving uptime to {100 - improvement["reduction"]*100:.0f}% availability would increase ROI by {roi_gain:.2f}%',
                    'specific_actions': [
                        'Implement proactive monitoring systems',
                        'Schedule preventive maintenance',
                        'Optimize cooling systems to prevent thermal shutdowns',
                        'Set up automated restart procedures'
                    ]
                })
        
        cost_reductions = [
            {'reduction': 0.10, 'label': '10%'},
            {'reduction': 0.20, 'label': '20%'}
        ]
        
        for reduction in cost_reductions:
            reduced_cost = electricity_cost * (1 - reduction['reduction'])
            improved_daily_cost = _calculate_daily_cost(power, reduced_cost)
            improved_daily_revenue = _calculate_daily_revenue(
                hashrate, btc_price, difficulty, block_reward
            )
            improved_profit = (improved_daily_revenue - improved_daily_cost) * 365
            improved_roi = (improved_profit / investment * 100) if investment > 0 else 0
            
            roi_gain = improved_roi - current_roi
            
            if roi_gain > 0.5:
                recommendations.append({
                    'category': 'Cost Reduction',
                    'priority': 'high' if roi_gain > 5 else 'medium',
                    'action': f'Negotiate {reduction["label"]} electricity cost reduction',
                    'projected_impact': {
                        'roi_increase_percent': roi_gain,
                        'additional_annual_profit_usd': improved_profit - (daily_profit * 365),
                        'annual_savings_usd': (electricity_cost - reduced_cost) * (power / 1000) * 24 * 365
                    },
                    'implementation_difficulty': 'hard',
                    'description': f'Reducing electricity cost by {reduction["label"]} would increase ROI by {roi_gain:.2f}%',
                    'specific_actions': [
                        'Negotiate bulk rate discounts with energy providers',
                        'Consider relocating to lower-cost energy markets',
                        'Explore renewable energy partnerships',
                        'Implement demand response programs'
                    ]
                })
        
        efficiency = power / hashrate if hashrate > 0 else 0
        
        efficiency_improvements = [
            {'improvement': 0.10, 'label': '10%'},
            {'improvement': 0.15, 'label': '15%'}
        ]
        
        for improvement in efficiency_improvements:
            improved_power = power * (1 - improvement['improvement'])
            improved_cost = _calculate_daily_cost(improved_power, electricity_cost)
            improved_revenue = _calculate_daily_revenue(
                hashrate, btc_price, difficulty, block_reward
            )
            improved_profit = (improved_revenue - improved_cost) * 365
            improved_roi = (improved_profit / investment * 100) if investment > 0 else 0
            
            roi_gain = improved_roi - current_roi
            
            if roi_gain > 0.5:
                recommendations.append({
                    'category': 'Hardware Efficiency',
                    'priority': 'medium',
                    'action': f'Upgrade to {improvement["label"]} more efficient hardware',
                    'projected_impact': {
                        'roi_increase_percent': roi_gain,
                        'additional_annual_profit_usd': improved_profit - (daily_profit * 365),
                        'power_savings_watts': power - improved_power
                    },
                    'implementation_difficulty': 'hard',
                    'description': f'Upgrading to more efficient miners ({improvement["label"]} better W/TH) would increase ROI by {roi_gain:.2f}%',
                    'specific_actions': [
                        'Research latest generation ASIC miners',
                        'Calculate hardware upgrade ROI and payback period',
                        'Consider selling older equipment',
                        'Plan phased upgrade strategy'
                    ]
                })
        
        recommendations.sort(key=lambda x: x['projected_impact']['roi_increase_percent'], reverse=True)
        
        for i, rec in enumerate(recommendations[:5]):
            rec['rank'] = i + 1
        
        result = {
            'user_id': user_id,
            'current_performance': {
                'annual_roi_percent': current_roi,
                'daily_profit_usd': daily_profit,
                'efficiency_w_per_th': efficiency
            },
            'recommendations': recommendations[:5],
            'summary': _generate_recommendations_summary(recommendations[:3], current_roi),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {e}")
        return None


def _generate_recommendations_summary(recommendations: List[Dict], current_roi: float) -> str:
    """Generate a human-readable summary of recommendations"""
    if not recommendations:
        return f"Your mining operation is performing well with {current_roi:.1f}% annual ROI. Continue monitoring market conditions."
    
    top_rec = recommendations[0]
    potential_roi = current_roi + top_rec['projected_impact']['roi_increase_percent']
    
    summary = f"Your current ROI is {current_roi:.1f}%. "
    summary += f"The top recommendation is to {top_rec['action'].lower()}, "
    summary += f"which could increase your ROI to {potential_roi:.1f}% "
    summary += f"(+{top_rec['projected_impact']['roi_increase_percent']:.1f}%). "
    
    if len(recommendations) > 1:
        summary += f"Additionally, {recommendations[1]['action'].lower()} "
        summary += f"could add another {recommendations[1]['projected_impact']['roi_increase_percent']:.1f}% to ROI."
    
    return summary


def generate_roi_report(user_id: int) -> Optional[Dict]:
    """
    Generate comprehensive ROI explanation report
    
    Combines factor analysis, change attribution, and recommendations
    into a single comprehensive report
    
    Args:
        user_id: User ID
        
    Returns:
        Comprehensive ROI report dictionary or None if error
    """
    try:
        logger.info(f"Generating comprehensive ROI report for user {user_id}")
        
        factors = calculate_roi_factors(user_id)
        roi_change_30d = explain_roi_change(user_id, days_back=30)
        roi_change_90d = explain_roi_change(user_id, days_back=90)
        recommendations = get_optimization_recommendations(user_id)
        
        if not factors:
            logger.error(f"Failed to generate factor analysis for user {user_id}")
            return None
        
        report = {
            'user_id': user_id,
            'report_type': 'comprehensive_roi_analysis',
            'generated_at': datetime.utcnow().isoformat(),
            'executive_summary': _generate_executive_summary(
                factors, roi_change_30d, recommendations
            ),
            'current_performance': factors['current_metrics'],
            'factor_analysis': factors['factor_impacts'],
            'historical_comparison': {
                '30_days': roi_change_30d if roi_change_30d else {'error': 'Data not available'},
                '90_days': roi_change_90d if roi_change_90d else {'error': 'Data not available'}
            },
            'optimization_opportunities': recommendations if recommendations else {
                'error': 'Recommendations not available'
            },
            'risk_factors': _identify_risk_factors(factors),
            'market_sensitivity': _calculate_market_sensitivity(factors),
            'next_steps': _generate_next_steps(recommendations, roi_change_30d)
        }
        
        logger.info(f"Comprehensive ROI report generated successfully for user {user_id}")
        return report
        
    except Exception as e:
        logger.error(f"Error generating ROI report for user {user_id}: {e}")
        return None


def _generate_executive_summary(factors: Dict, roi_change: Optional[Dict], 
                                recommendations: Optional[Dict]) -> str:
    """Generate executive summary for the ROI report"""
    current_roi = factors['current_metrics']['annual_roi_percent']
    daily_profit = factors['current_metrics']['daily_profit_usd']
    
    summary = f"Your mining operation currently generates {current_roi:.1f}% annual ROI "
    summary += f"with ${daily_profit:.2f} daily profit. "
    
    if roi_change and 'roi_comparison' in roi_change:
        trend = roi_change['roi_comparison']['trend']
        roi_delta = roi_change['roi_comparison']['roi_change']
        
        if trend == 'improved':
            summary += f"Performance has improved by {roi_delta:.1f}% over the past 30 days. "
        elif trend == 'declined':
            summary += f"Performance has declined by {abs(roi_delta):.1f}% over the past 30 days. "
        
        if roi_change.get('main_drivers'):
            top_driver = roi_change['main_drivers'][0]
            summary += f"{top_driver['description']}. "
    
    if recommendations and recommendations.get('recommendations'):
        top_rec = recommendations['recommendations'][0]
        summary += f"The top optimization opportunity is to {top_rec['action'].lower()}, "
        summary += f"potentially increasing ROI by {top_rec['projected_impact']['roi_increase_percent']:.1f}%."
    
    return summary


def _identify_risk_factors(factors: Dict) -> List[Dict]:
    """Identify risk factors based on sensitivity analysis"""
    risks = []
    
    btc_impact = abs(factors['factor_impacts']['btc_price']['impact_per_10pct_change'])
    if btc_impact > 10:
        risks.append({
            'factor': 'BTC Price Volatility',
            'severity': 'high',
            'description': f'High sensitivity to BTC price changes ({btc_impact:.1f}% ROI impact per 10% price change)',
            'mitigation': 'Consider hedging strategies or diversification'
        })
    
    diff_impact = abs(factors['factor_impacts']['difficulty']['impact_per_10pct_change'])
    if diff_impact > 5:
        risks.append({
            'factor': 'Network Difficulty Growth',
            'severity': 'medium',
            'description': f'Significant exposure to difficulty increases ({diff_impact:.1f}% ROI impact per 10% difficulty change)',
            'mitigation': 'Plan for regular hardware upgrades to maintain competitiveness'
        })
    
    offline_impact = abs(factors['factor_impacts']['offline_rate']['impact_per_5pct_offline'])
    if offline_impact > 3:
        risks.append({
            'factor': 'Operational Uptime',
            'severity': 'medium',
            'description': f'Downtime has material impact on ROI ({offline_impact:.1f}% per 5% offline time)',
            'mitigation': 'Invest in monitoring, redundancy, and preventive maintenance'
        })
    
    return risks


def _calculate_market_sensitivity(factors: Dict) -> Dict:
    """Calculate overall market sensitivity metrics"""
    btc_sensitivity = factors['factor_impacts']['btc_price']['contribution_percent']
    diff_sensitivity = factors['factor_impacts']['difficulty']['contribution_percent']
    
    if btc_sensitivity > 50:
        market_exposure = 'high'
    elif btc_sensitivity > 30:
        market_exposure = 'moderate'
    else:
        market_exposure = 'low'
    
    return {
        'btc_price_sensitivity': btc_sensitivity,
        'difficulty_sensitivity': diff_sensitivity,
        'market_exposure_level': market_exposure,
        'diversification_score': 100 - btc_sensitivity,
        'description': f'Your operation has {market_exposure} market exposure with {btc_sensitivity:.1f}% sensitivity to BTC price'
    }


def _generate_next_steps(recommendations: Optional[Dict], roi_change: Optional[Dict]) -> List[str]:
    """Generate actionable next steps"""
    next_steps = []
    
    if recommendations and recommendations.get('recommendations'):
        top_rec = recommendations['recommendations'][0]
        next_steps.append(f"Priority 1: {top_rec['action']}")
        next_steps.extend(top_rec.get('specific_actions', [])[:2])
    
    if roi_change and roi_change.get('roi_comparison', {}).get('trend') == 'declined':
        next_steps.append("Monitor market conditions closely and review cost structure")
    
    next_steps.append("Continue tracking daily performance metrics")
    next_steps.append("Review this ROI analysis monthly to identify trends early")
    
    return next_steps[:5]
