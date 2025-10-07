"""
Intelligence Tasks for RQ Task Queue
====================================

This module contains intelligence-specific tasks for forecasting, optimization,
and anomaly detection.
"""

import logging
from datetime import datetime, date
from typing import List, Optional
from rq import get_current_job

from intelligence.forecast import forecast_user_revenue
from intelligence.optimizer import optimize_curtailment
from intelligence.anomaly import generate_anomaly_report
from intelligence.workers.distributed_lock import distributed_lock
from intelligence.workers.idempotency import idempotent

logger = logging.getLogger(__name__)


@distributed_lock("lock:forecast:{user_id}", timeout=300)
@idempotent("result:forecast:{user_id}", ttl=7200, include_all_args=True)
def forecast_refresh(user_id: int, days: int = 7) -> dict:
    """
    Refresh forecast data for a user using ARIMA models.
    Calls forecast_user_revenue() to generate revenue predictions.
    
    Args:
        user_id: User ID to generate forecast for
        days: Number of days to forecast (default 7)
        
    Returns:
        dict: {
            'user_id': int,
            'days': int,
            'forecast_data': dict,
            'status': str,
            'timestamp': datetime
        }
    """
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'manual'
    
    logger.info(f"[Job {job_id}] Starting forecast refresh for user_id={user_id}, days={days}")
    
    try:
        forecast_data = forecast_user_revenue(user_id, days=days)
        
        if forecast_data.get('saved_records', 0) == 0:
            logger.warning(f"[Job {job_id}] No forecast records saved for user_id={user_id}")
        
        result = {
            'user_id': user_id,
            'days': days,
            'forecast_data': forecast_data,
            'status': 'success',
            'timestamp': datetime.utcnow()
        }
        
        logger.info(f"[Job {job_id}] Forecast refresh completed for user_id={user_id}, "
                   f"saved_records={forecast_data.get('saved_records', 0)}")
        
        return result
        
    except Exception as e:
        logger.error(f"[Job {job_id}] Error in forecast refresh for user_id={user_id}: {str(e)}", exc_info=True)
        return {
            'user_id': user_id,
            'days': days,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow()
        }


@distributed_lock("lock:optimize:{user_id}:{schedule_date}", timeout=300)
@idempotent("result:optimize:{user_id}:{schedule_date}", ttl=3600, include_all_args=True)
def optimize_curtailment_task(
    user_id: int,
    schedule_date: date,
    electricity_prices: List[float],
    target_uptime: float = 0.85,
    min_uptime: float = 0.70
) -> dict:
    """
    Optimize power curtailment schedule for a user using linear programming.
    Calls optimize_curtailment() to generate the optimal schedule.
    
    Args:
        user_id: User ID
        schedule_date: Date for the schedule
        electricity_prices: List of 24 hourly electricity prices ($/kWh)
        target_uptime: Target uptime percentage (default 85%)
        min_uptime: Minimum uptime percentage (default 70%)
        
    Returns:
        dict: {
            'user_id': int,
            'schedule_date': date,
            'optimization_result': dict,
            'status': str,
            'timestamp': datetime
        }
    """
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'manual'
    
    logger.info(f"[Job {job_id}] Starting curtailment optimization for user_id={user_id}, date={schedule_date}")
    
    try:
        if len(electricity_prices) != 24:
            raise ValueError(f"Expected 24 hourly prices, got {len(electricity_prices)}")
        
        optimization_result = optimize_curtailment(
            user_id=user_id,
            schedule_date=schedule_date,
            electricity_prices=electricity_prices,
            target_uptime=target_uptime,
            min_uptime=min_uptime
        )
        
        result = {
            'user_id': user_id,
            'schedule_date': schedule_date.isoformat() if isinstance(schedule_date, date) else schedule_date,
            'optimization_result': optimization_result,
            'status': 'success',
            'timestamp': datetime.utcnow()
        }
        
        logger.info(f"[Job {job_id}] Curtailment optimization completed for user_id={user_id}, "
                   f"status={optimization_result.get('optimization_status')}, "
                   f"total_cost=${optimization_result.get('total_cost', 0):.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"[Job {job_id}] Error in curtailment optimization for user_id={user_id}: {str(e)}", exc_info=True)
        return {
            'user_id': user_id,
            'schedule_date': schedule_date.isoformat() if isinstance(schedule_date, date) else schedule_date,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow()
        }


@distributed_lock("lock:anomaly:{user_id}", timeout=300)
@idempotent("result:anomaly:{user_id}", ttl=3600, include_all_args=True)
def detect_anomalies_task(user_id: int, lookback_days: int = 30) -> dict:
    """
    Detect anomalies in user's mining operations.
    Calls generate_anomaly_report() to analyze hashrate, power, and ROI patterns.
    
    Args:
        user_id: User ID to analyze
        lookback_days: Number of days to look back (default 30)
        
    Returns:
        dict: {
            'user_id': int,
            'lookback_days': int,
            'anomaly_report': dict,
            'status': str,
            'timestamp': datetime
        }
    """
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'manual'
    
    logger.info(f"[Job {job_id}] Starting anomaly detection for user_id={user_id}, lookback={lookback_days} days")
    
    try:
        anomaly_report = generate_anomaly_report(user_id)
        
        total_anomalies = (
            len(anomaly_report.get('hashrate_anomalies', [])) +
            len(anomaly_report.get('power_anomalies', [])) +
            len(anomaly_report.get('roi_anomalies', []))
        )
        
        result = {
            'user_id': user_id,
            'lookback_days': lookback_days,
            'anomaly_report': anomaly_report,
            'total_anomalies': total_anomalies,
            'status': 'success',
            'timestamp': datetime.utcnow()
        }
        
        logger.info(f"[Job {job_id}] Anomaly detection completed for user_id={user_id}, "
                   f"total_anomalies={total_anomalies}")
        
        return result
        
    except Exception as e:
        logger.error(f"[Job {job_id}] Error in anomaly detection for user_id={user_id}: {str(e)}", exc_info=True)
        return {
            'user_id': user_id,
            'lookback_days': lookback_days,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow()
        }
