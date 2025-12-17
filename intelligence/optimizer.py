"""
Power Curtailment Optimization Module
=====================================

Uses PuLP linear programming to optimize miner on/off schedules
to minimize electricity costs while maintaining target uptime.

Author: HashInsight Intelligence Team
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
import time

import pulp
from sqlalchemy import and_

from db import db
from models import UserMiner, OpsSchedule

logger = logging.getLogger(__name__)


def optimize_curtailment(
    user_id: int, 
    schedule_date: date, 
    electricity_prices: List[float],
    target_uptime: float = 0.85,
    min_uptime: float = 0.70
) -> Dict:
    """
    Optimize power curtailment schedule using PuLP linear programming.
    
    Args:
        user_id: User ID
        schedule_date: Date for the schedule
        electricity_prices: List of 24 hourly electricity prices ($/kWh)
        target_uptime: Target uptime percentage (default 85%)
        min_uptime: Minimum uptime percentage (default 70%)
    
    Returns:
        dict: {
            'schedule': List of 24 hourly decisions (miners online/offline),
            'total_cost': Total electricity cost ($),
            'total_power': Total power consumption (kWh),
            'uptime_achieved': Actual uptime percentage,
            'optimization_status': 'optimal' | 'feasible' | 'infeasible',
            'computation_time_ms': Computation time in milliseconds
        }
    """
    start_time = time.time()
    
    try:
        if len(electricity_prices) != 24:
            raise ValueError(f"Expected 24 hourly prices, got {len(electricity_prices)}")
        
        miners = UserMiner.get_user_miners(user_id, status='active')
        
        if not miners:
            logger.warning(f"No active miners found for user_id={user_id}")
            return {
                'schedule': [{'hour': h, 'miners_online': 0, 'miners_offline': 0, 'power_kw': 0} for h in range(24)],
                'total_cost': 0,
                'total_power': 0,
                'uptime_achieved': 0,
                'optimization_status': 'no_miners',
                'computation_time_ms': 0
            }
        
        total_miners = sum(miner.quantity for miner in miners)
        total_power_per_miner = sum(miner.actual_power * miner.quantity for miner in miners) / total_miners if total_miners > 0 else 0
        total_power_kw = total_power_per_miner / 1000
        
        logger.info(f"Optimizing for user_id={user_id}, date={schedule_date}, total_miners={total_miners}, power_per_unit={total_power_kw:.2f}kW")
        
        prob = pulp.LpProblem("Power_Curtailment_Optimization", pulp.LpMinimize)
        
        x = pulp.LpVariable.dicts("miners_online", range(24), lowBound=0, upBound=total_miners, cat='Integer')
        
        prob += pulp.lpSum([
            x[h] * total_power_kw * electricity_prices[h] for h in range(24)
        ]), "Total_Electricity_Cost"
        
        min_hours_online = int(24 * min_uptime)
        prob += pulp.lpSum([x[h] for h in range(24)]) >= min_hours_online * total_miners, "Minimum_Uptime_Constraint"
        
        prob += pulp.lpSum([x[h] for h in range(24)]) >= 24 * total_miners * target_uptime, "Target_Uptime_Constraint"
        
        for h in range(23):
            prob += x[h+1] - x[h] >= -total_miners * 0.3, f"Smooth_Transition_Down_{h}"
            prob += x[h+1] - x[h] <= total_miners * 0.3, f"Smooth_Transition_Up_{h}"
        
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        status = pulp.LpStatus[prob.status]
        
        if status not in ['Optimal', 'Feasible']:
            logger.error(f"Optimization failed with status: {status}")
            return {
                'schedule': [{'hour': h, 'miners_online': total_miners, 'miners_offline': 0, 'power_kw': total_power_kw * total_miners} for h in range(24)],
                'total_cost': sum(electricity_prices) * total_power_kw * total_miners,
                'total_power': total_power_kw * total_miners * 24,
                'uptime_achieved': 1.0,
                'optimization_status': 'infeasible',
                'computation_time_ms': int((time.time() - start_time) * 1000)
            }
        
        schedule = []
        total_cost = 0
        total_power = 0
        miners_hours_online = 0
        
        for h in range(24):
            miners_online = int(x[h].varValue)
            miners_offline = total_miners - miners_online
            power_kw = miners_online * total_power_kw
            cost = power_kw * electricity_prices[h]
            
            schedule.append({
                'hour': h,
                'miners_online': miners_online,
                'miners_offline': miners_offline,
                'power_kw': power_kw,
                'electricity_price': electricity_prices[h],
                'cost': cost
            })
            
            total_cost += cost
            total_power += power_kw
            if miners_online > 0:
                miners_hours_online += miners_online
        
        uptime_achieved = miners_hours_online / (total_miners * 24) if total_miners > 0 else 0
        
        computation_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Optimization complete: cost=${total_cost:.2f}, uptime={uptime_achieved:.1%}, time={computation_time_ms}ms")
        
        return {
            'schedule': schedule,
            'total_cost': total_cost,
            'total_power': total_power,
            'uptime_achieved': uptime_achieved,
            'optimization_status': status.lower(),
            'computation_time_ms': computation_time_ms
        }
        
    except Exception as e:
        logger.error(f"Error in optimize_curtailment: {str(e)}", exc_info=True)
        raise


def calculate_curtailment_savings(
    schedule: List[Dict],
    electricity_prices: List[float],
    baseline_schedule: Optional[List[Dict]] = None
) -> Dict:
    """
    Calculate total savings from curtailment compared to baseline (always-on).
    
    Args:
        schedule: Optimized schedule from optimize_curtailment()
        electricity_prices: List of 24 hourly electricity prices
        baseline_schedule: Optional baseline schedule (default: all miners always on)
    
    Returns:
        dict: {
            'cost_saved_usd': Total cost saved ($),
            'power_saved_kwh': Total power saved (kWh),
            'curtailment_percentage': Percentage of power curtailed,
            'baseline_cost': Baseline cost ($),
            'optimized_cost': Optimized cost ($),
            'baseline_power': Baseline power (kWh),
            'optimized_power': Optimized power (kWh)
        }
    """
    try:
        if len(schedule) != 24:
            raise ValueError(f"Schedule must have 24 hours, got {len(schedule)}")
        
        if len(electricity_prices) != 24:
            raise ValueError(f"Expected 24 hourly prices, got {len(electricity_prices)}")
        
        optimized_cost = sum(hour['cost'] for hour in schedule)
        optimized_power = sum(hour['power_kw'] for hour in schedule)
        
        if baseline_schedule:
            baseline_cost = sum(hour['cost'] for hour in baseline_schedule)
            baseline_power = sum(hour['power_kw'] for hour in baseline_schedule)
        else:
            max_miners = max(hour['miners_online'] + hour['miners_offline'] for hour in schedule)
            max_power_kw = max(hour['miners_online'] + hour['miners_offline'] for hour in schedule) * (schedule[0]['power_kw'] / schedule[0]['miners_online'] if schedule[0]['miners_online'] > 0 else 0)
            
            baseline_cost = sum(max_power_kw * price for price in electricity_prices)
            baseline_power = max_power_kw * 24
        
        cost_saved = baseline_cost - optimized_cost
        power_saved = baseline_power - optimized_power
        curtailment_percentage = (power_saved / baseline_power * 100) if baseline_power > 0 else 0
        
        logger.info(f"Savings calculated: cost_saved=${cost_saved:.2f}, power_saved={power_saved:.2f}kWh, curtailment={curtailment_percentage:.1f}%")
        
        return {
            'cost_saved_usd': cost_saved,
            'power_saved_kwh': power_saved,
            'curtailment_percentage': curtailment_percentage,
            'baseline_cost': baseline_cost,
            'optimized_cost': optimized_cost,
            'baseline_power': baseline_power,
            'optimized_power': optimized_power
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_curtailment_savings: {str(e)}", exc_info=True)
        raise


def save_optimization_schedule(
    user_id: int,
    schedule_date: date,
    schedule: List[Dict],
    optimization_result: Dict,
    algorithm: str = 'PuLP'
) -> List[OpsSchedule]:
    """
    Save optimization schedule to OpsSchedule model.
    
    Args:
        user_id: User ID
        schedule_date: Date for the schedule
        schedule: Hourly schedule from optimize_curtailment()
        optimization_result: Full optimization result dict
        algorithm: Algorithm used (default: 'PuLP')
    
    Returns:
        List[OpsSchedule]: Saved schedule records
    """
    try:
        saved_records = []
        
        db.session.query(OpsSchedule).filter_by(
            user_id=user_id,
            schedule_date=schedule_date
        ).delete()
        
        for hour_data in schedule:
            hour = hour_data['hour']
            
            is_peak = electricity_prices_is_peak(hour_data['electricity_price'], schedule)
            
            curtailment_pct = (hour_data['miners_offline'] / (hour_data['miners_online'] + hour_data['miners_offline']) * 100) if (hour_data['miners_online'] + hour_data['miners_offline']) > 0 else 0
            
            ops_record = OpsSchedule(
                user_id=user_id,
                schedule_date=schedule_date,
                hour_of_day=hour,
                electricity_price=hour_data['electricity_price'],
                total_power_consumption_kw=hour_data['power_kw'],
                is_peak_hour=is_peak,
                miners_online=hour_data['miners_online'],
                miners_offline=hour_data['miners_offline'],
                curtailment_percentage=curtailment_pct,
                power_saved_kw=hour_data['miners_offline'] * (hour_data['power_kw'] / hour_data['miners_online']) if hour_data['miners_online'] > 0 else 0,
                cost_saved_usd=hour_data.get('cost_saved', 0),
                algorithm_used=algorithm,
                optimization_status=optimization_result.get('optimization_status', 'optimal'),
                computation_time_ms=optimization_result.get('computation_time_ms', 0)
            )
            
            db.session.add(ops_record)
            saved_records.append(ops_record)
        
        db.session.commit()
        
        logger.info(f"Saved {len(saved_records)} schedule records for user_id={user_id}, date={schedule_date}")
        
        return saved_records
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving optimization schedule: {str(e)}", exc_info=True)
        raise


def electricity_prices_is_peak(price: float, schedule: List[Dict]) -> bool:
    """Helper function to determine if a price is peak pricing."""
    all_prices = [hour['electricity_price'] for hour in schedule]
    avg_price = sum(all_prices) / len(all_prices)
    return price > avg_price * 1.2


def get_recommended_schedule(
    user_id: int,
    schedule_date: date,
    electricity_prices: Optional[List[float]] = None,
    force_recalculate: bool = False
) -> Dict:
    """
    Retrieve or calculate optimized schedule with caching.
    
    Args:
        user_id: User ID
        schedule_date: Date for the schedule
        electricity_prices: Optional hourly prices (required if not cached)
        force_recalculate: Force recalculation even if cached
    
    Returns:
        dict: {
            'schedule': List of 24 hourly records,
            'total_cost': Total cost,
            'total_power': Total power,
            'uptime_achieved': Uptime percentage,
            'is_cached': Whether result was from cache,
            'computation_time_ms': Computation time
        }
    """
    try:
        if not force_recalculate:
            cached_schedule = db.session.query(OpsSchedule).filter_by(
                user_id=user_id,
                schedule_date=schedule_date
            ).order_by(OpsSchedule.hour_of_day).all()
            
            if cached_schedule and len(cached_schedule) == 24:
                logger.info(f"Returning cached schedule for user_id={user_id}, date={schedule_date}")
                
                schedule = []
                total_cost = 0
                total_power = 0
                
                for record in cached_schedule:
                    hour_data = {
                        'hour': record.hour_of_day,
                        'miners_online': record.miners_online,
                        'miners_offline': record.miners_offline,
                        'power_kw': float(record.total_power_consumption_kw),
                        'electricity_price': float(record.electricity_price),
                        'cost': float(record.total_power_consumption_kw) * float(record.electricity_price),
                        'is_peak_hour': record.is_peak_hour
                    }
                    schedule.append(hour_data)
                    total_cost += hour_data['cost']
                    total_power += hour_data['power_kw']
                
                total_miners = max(r.miners_online + r.miners_offline for r in cached_schedule)
                miners_hours = sum(r.miners_online for r in cached_schedule)
                uptime = miners_hours / (total_miners * 24) if total_miners > 0 else 0
                
                return {
                    'schedule': schedule,
                    'total_cost': total_cost,
                    'total_power': total_power,
                    'uptime_achieved': uptime,
                    'is_cached': True,
                    'computation_time_ms': 0,
                    'optimization_status': cached_schedule[0].optimization_status
                }
        
        if not electricity_prices:
            raise ValueError("electricity_prices required for new schedule calculation")
        
        logger.info(f"Calculating new schedule for user_id={user_id}, date={schedule_date}")
        
        optimization_result = optimize_curtailment(user_id, schedule_date, electricity_prices)
        
        save_optimization_schedule(
            user_id=user_id,
            schedule_date=schedule_date,
            schedule=optimization_result['schedule'],
            optimization_result=optimization_result
        )
        
        optimization_result['is_cached'] = False
        
        return optimization_result
        
    except Exception as e:
        logger.error(f"Error in get_recommended_schedule: {str(e)}", exc_info=True)
        raise
