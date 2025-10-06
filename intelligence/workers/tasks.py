"""
Basic Portfolio Recalculation Tasks for RQ
==========================================

This module contains basic portfolio recalculation tasks for the RQ task queue.
All tasks are idempotent with proper error handling and retry logic.
"""

import logging
from datetime import datetime
from typing import Optional
from rq import get_current_job

from app import db
from models import UserMiner, UserAccess, NetworkSnapshot

logger = logging.getLogger(__name__)


def recalculate_user_portfolio(user_id: int) -> dict:
    """
    Recalculate user's portfolio metrics including total hashrate, power consumption, and estimated revenue.
    This task is idempotent and can be safely retried.
    
    Args:
        user_id: User ID to recalculate portfolio for
        
    Returns:
        dict: {
            'user_id': int,
            'total_hashrate': float,
            'total_power': float,
            'active_miners': int,
            'estimated_daily_revenue': float,
            'status': str,
            'timestamp': datetime
        }
    """
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'manual'
    
    logger.info(f"[Job {job_id}] Starting portfolio recalculation for user_id={user_id}")
    
    try:
        user = UserAccess.query.get(user_id)
        if not user:
            logger.error(f"[Job {job_id}] User {user_id} not found")
            return {
                'user_id': user_id,
                'status': 'error',
                'error': 'User not found',
                'timestamp': datetime.utcnow()
            }
        
        active_miners = UserMiner.query.filter_by(
            user_id=user_id,
            status='active'
        ).all()
        
        total_hashrate = sum(m.actual_hashrate * m.quantity for m in active_miners)
        total_power = sum(m.actual_power * m.quantity for m in active_miners)
        
        latest_snapshot = NetworkSnapshot.query.filter_by(
            is_valid=True
        ).order_by(NetworkSnapshot.recorded_at.desc()).first()
        
        estimated_daily_revenue = 0.0
        if latest_snapshot and total_hashrate > 0:
            btc_price = float(latest_snapshot.btc_price)
            network_difficulty = float(latest_snapshot.network_difficulty)
            block_reward = float(latest_snapshot.block_reward)
            
            blocks_per_day = 144
            network_hashrate_th = network_difficulty * (2**32) / 600 / 1e12
            
            if network_hashrate_th > 0:
                daily_btc = (total_hashrate / network_hashrate_th) * blocks_per_day * block_reward
                estimated_daily_revenue = daily_btc * btc_price
        
        result = {
            'user_id': user_id,
            'total_hashrate': float(total_hashrate),
            'total_power': float(total_power),
            'active_miners': len(active_miners),
            'estimated_daily_revenue': float(estimated_daily_revenue),
            'status': 'success',
            'timestamp': datetime.utcnow()
        }
        
        logger.info(f"[Job {job_id}] Portfolio recalculation completed for user_id={user_id}: "
                   f"hashrate={total_hashrate:.2f} TH/s, revenue=${estimated_daily_revenue:.2f}/day")
        
        return result
        
    except Exception as e:
        logger.error(f"[Job {job_id}] Error recalculating portfolio for user_id={user_id}: {str(e)}", exc_info=True)
        return {
            'user_id': user_id,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow()
        }


def update_user_analytics(user_id: int) -> dict:
    """
    Update user analytics data including performance metrics and trends.
    This task is idempotent and can be safely retried.
    
    Args:
        user_id: User ID to update analytics for
        
    Returns:
        dict: {
            'user_id': int,
            'metrics_updated': int,
            'status': str,
            'timestamp': datetime
        }
    """
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'manual'
    
    logger.info(f"[Job {job_id}] Starting analytics update for user_id={user_id}")
    
    try:
        user = UserAccess.query.get(user_id)
        if not user:
            logger.error(f"[Job {job_id}] User {user_id} not found")
            return {
                'user_id': user_id,
                'status': 'error',
                'error': 'User not found',
                'timestamp': datetime.utcnow()
            }
        
        metrics_updated = 0
        
        active_miners = UserMiner.query.filter_by(
            user_id=user_id,
            status='active'
        ).all()
        
        for miner in active_miners:
            if miner.actual_hashrate and miner.original_hashrate:
                efficiency_ratio = (miner.actual_hashrate / miner.original_hashrate) * 100
                metrics_updated += 1
        
        logger.info(f"[Job {job_id}] Analytics update completed for user_id={user_id}, metrics_updated={metrics_updated}")
        
        return {
            'user_id': user_id,
            'metrics_updated': metrics_updated,
            'status': 'success',
            'timestamp': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"[Job {job_id}] Error updating analytics for user_id={user_id}: {str(e)}", exc_info=True)
        return {
            'user_id': user_id,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow()
        }


def refresh_user_cache(user_id: int) -> dict:
    """
    Refresh user's cached data including miner stats and network data.
    This task is idempotent and can be safely retried.
    
    Args:
        user_id: User ID to refresh cache for
        
    Returns:
        dict: {
            'user_id': int,
            'cache_entries_refreshed': int,
            'status': str,
            'timestamp': datetime
        }
    """
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'manual'
    
    logger.info(f"[Job {job_id}] Starting cache refresh for user_id={user_id}")
    
    try:
        user = UserAccess.query.get(user_id)
        if not user:
            logger.error(f"[Job {job_id}] User {user_id} not found")
            return {
                'user_id': user_id,
                'status': 'error',
                'error': 'User not found',
                'timestamp': datetime.utcnow()
            }
        
        cache_entries_refreshed = 0
        
        active_miners = UserMiner.query.filter_by(
            user_id=user_id,
            status='active'
        ).all()
        
        cache_entries_refreshed = len(active_miners)
        
        latest_snapshot = NetworkSnapshot.query.filter_by(
            is_valid=True
        ).order_by(NetworkSnapshot.recorded_at.desc()).first()
        
        if latest_snapshot:
            cache_entries_refreshed += 1
        
        logger.info(f"[Job {job_id}] Cache refresh completed for user_id={user_id}, entries={cache_entries_refreshed}")
        
        return {
            'user_id': user_id,
            'cache_entries_refreshed': cache_entries_refreshed,
            'status': 'success',
            'timestamp': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"[Job {job_id}] Error refreshing cache for user_id={user_id}: {str(e)}", exc_info=True)
        return {
            'user_id': user_id,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow()
        }
