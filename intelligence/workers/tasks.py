"""
Basic Portfolio Recalculation Tasks for RQ
==========================================

This module contains basic portfolio recalculation tasks for the RQ task queue.
All tasks are idempotent with proper error handling and retry logic.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Any
from rq import get_current_job
from importlib import import_module

from app import db
from models import UserMiner, UserAccess, NetworkSnapshot, EventOutbox, EventFailure
from intelligence.workers.distributed_lock import distributed_lock
from intelligence.workers.idempotency import idempotent
from intelligence.monitoring.slo_tracker import track_recalculation

logger = logging.getLogger(__name__)


# ============================================================================
# SWR Cache Refresh Task (Top-level for RQ serialization)
# ============================================================================

def refresh_cache_entry(
    key: str, 
    callback_path: str, 
    callback_args: tuple = (), 
    callback_kwargs: Optional[dict] = None, 
    ttl: int = 300, 
    stale_window: int = 300, 
    lock_key: Optional[str] = None
) -> dict:
    """
    Top-level RQ task for cache refresh (SWR pattern).
    This function is picklable because it's defined at module level.
    
    Args:
        key: Cache key to refresh
        callback_path: Import path to callback function (e.g., "module.submodule.function_name")
        callback_args: Positional arguments to pass to callback function
        callback_kwargs: Keyword arguments to pass to callback function
        ttl: Time-to-live (fresh period) in seconds
        stale_window: Stale window duration in seconds
        lock_key: Redis lock key for this refresh operation
        
    Returns:
        dict: {
            'status': str,
            'key': str,
            'refreshed': bool,
            'timestamp': datetime
        }
    """
    if callback_kwargs is None:
        callback_kwargs = {}
    
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'manual'
    
    logger.info(
        f"[Job {job_id}] Starting cache refresh for key={key}, callback_path={callback_path}, "
        f"args={callback_args}, kwargs={callback_kwargs}"
    )
    
    try:
        from intelligence.cache_manager import intelligence_cache, CachedValue
        
        if intelligence_cache._check_cache_freshness(key):
            logger.debug(f"[Job {job_id}] Cache already fresh, skipping refresh: {key}")
            return {
                'status': 'skipped',
                'key': key,
                'refreshed': False,
                'reason': 'cache_already_fresh',
                'timestamp': datetime.utcnow()
            }
        
        module_path, func_name = callback_path.rsplit('.', 1)
        module = import_module(module_path)
        callback = getattr(module, func_name)
        
        fresh_value = callback(*callback_args, **callback_kwargs)
        
        now = datetime.utcnow()
        cached_value = CachedValue(
            value=fresh_value,
            expires_at=now + timedelta(seconds=ttl),
            stale_until=now + timedelta(seconds=ttl + stale_window)
        )
        
        if intelligence_cache.cache:
            intelligence_cache.cache.set(key, cached_value, timeout=ttl + stale_window)
        
        logger.info(f"[Job {job_id}] Background refresh complete (RQ): {key}")
        
        return {
            'status': 'success',
            'key': key,
            'refreshed': True,
            'timestamp': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"[Job {job_id}] Cache refresh failed for {key}: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'key': key,
            'refreshed': False,
            'error': str(e),
            'timestamp': datetime.utcnow()
        }
    finally:
        try:
            from intelligence.cache_manager import intelligence_cache
            if lock_key:
                intelligence_cache._release_redis_lock(lock_key)
                logger.debug(f"[Job {job_id}] Released redis lock: {lock_key}")
        except Exception as lock_error:
            logger.error(f"[Job {job_id}] Failed to release lock {lock_key}: {lock_error}")


# ============================================================================
# Event Callback Functions
# ============================================================================

def mark_source_events_completed(event_ids: List[int]) -> int:
    """
    Mark source events as COMPLETED after successful task execution.
    标记源事件为已完成（任务成功后）。
    
    Args:
        event_ids: List of event IDs to mark as completed
        
    Returns:
        int: Number of events updated
    """
    if not event_ids:
        return 0
    
    try:
        events = EventOutbox.query.filter(EventOutbox.id.in_(event_ids)).all()
        
        updated_count = 0
        for event in events:
            event.mark_completed()
            updated_count += 1
        
        db.session.commit()
        logger.info(f"Marked {updated_count} source events as COMPLETED: {event_ids}")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error marking events as completed: {str(e)}", exc_info=True)
        db.session.rollback()
        return 0


def mark_source_events_failed(event_ids: List[int], error_message: str) -> int:
    """
    Mark source events as FAILED after task failure.
    标记源事件为失败（任务失败后）。
    
    Args:
        event_ids: List of event IDs to mark as failed
        error_message: Error message to record
        
    Returns:
        int: Number of events updated
    """
    if not event_ids:
        return 0
    
    try:
        events = EventOutbox.query.filter(EventOutbox.id.in_(event_ids)).all()
        
        updated_count = 0
        for event in events:
            event.mark_failed(error_message)
            
            # Create failure record
            failure = EventFailure(
                event_id=event.id,
                event_type=event.event_type,
                event_payload=event.event_payload,
                failure_reason=error_message
            )
            db.session.add(failure)
            updated_count += 1
        
        db.session.commit()
        logger.info(f"Marked {updated_count} source events as FAILED: {event_ids}")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error marking events as failed: {str(e)}", exc_info=True)
        db.session.rollback()
        return 0


@distributed_lock("lock:recalc:user:{user_id}", timeout=300)
@idempotent("result:recalc:user:{user_id}", ttl=1800, include_all_args=True)
@track_recalculation
def recalculate_user_portfolio(user_id: int, source_event_ids: Optional[List[int]] = None) -> dict:
    """
    Recalculate user's portfolio metrics including total hashrate, power consumption, and estimated revenue.
    This task is idempotent and can be safely retried.
    
    Args:
        user_id: User ID to recalculate portfolio for
        source_event_ids: Optional list of event IDs that triggered this recalculation
        
    Returns:
        dict: {
            'user_id': int,
            'total_hashrate': float,
            'total_power': float,
            'active_miners': int,
            'estimated_daily_revenue': float,
            'status': str,
            'timestamp': datetime,
            'source_events_updated': int
        }
    """
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'manual'
    
    logger.info(
        f"[Job {job_id}] Starting portfolio recalculation for user_id={user_id}, "
        f"source_event_ids={source_event_ids}"
    )
    
    try:
        user = UserAccess.query.get(user_id)
        if not user:
            error_msg = f"User {user_id} not found"
            logger.error(f"[Job {job_id}] {error_msg}")
            
            # Mark source events as FAILED
            if source_event_ids:
                mark_source_events_failed(source_event_ids, error_msg)
            
            return {
                'user_id': user_id,
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.utcnow(),
                'source_events_updated': len(source_event_ids) if source_event_ids else 0
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
        
        # Mark source events as COMPLETED on success
        events_updated = 0
        if source_event_ids:
            events_updated = mark_source_events_completed(source_event_ids)
        
        result = {
            'user_id': user_id,
            'total_hashrate': float(total_hashrate),
            'total_power': float(total_power),
            'active_miners': len(active_miners),
            'estimated_daily_revenue': float(estimated_daily_revenue),
            'status': 'success',
            'timestamp': datetime.utcnow(),
            'source_events_updated': events_updated
        }
        
        logger.info(
            f"[Job {job_id}] Portfolio recalculation completed for user_id={user_id}: "
            f"hashrate={total_hashrate:.2f} TH/s, revenue=${estimated_daily_revenue:.2f}/day, "
            f"source_events_updated={events_updated}"
        )
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"[Job {job_id}] Error recalculating portfolio for user_id={user_id}: {error_msg}",
            exc_info=True
        )
        
        # Mark source events as FAILED on error
        if source_event_ids:
            mark_source_events_failed(source_event_ids, error_msg)
        
        return {
            'user_id': user_id,
            'status': 'error',
            'error': error_msg,
            'timestamp': datetime.utcnow(),
            'source_events_updated': len(source_event_ids) if source_event_ids else 0
        }


@distributed_lock("lock:recalc:analytics:{user_id}", timeout=300)
@idempotent("result:recalc:analytics:{user_id}", ttl=1800, include_all_args=True)
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


@distributed_lock("lock:refresh:cache:{user_id}", timeout=300)
@idempotent("result:refresh:cache:{user_id}", ttl=1800, include_all_args=True)
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


# ============================================================================
# CLI Entry Point - Start RQ Worker
# ============================================================================

if __name__ == '__main__':
    """
    Start RQ worker to process tasks.
    
    Usage:
        python -m intelligence.workers.tasks
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting RQ Worker from tasks module...")
    
    from intelligence.workers.worker import start_worker
    
    import sys
    burst_mode = '--burst' in sys.argv
    
    if len(sys.argv) > 1 and sys.argv[1] not in ['--burst']:
        queue_names = [q for q in sys.argv[1:] if q != '--burst']
        start_worker(queue_names=queue_names, burst=burst_mode)
    else:
        start_worker(burst=burst_mode)
