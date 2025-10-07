"""
Intelligence Layer Event Aggregation Scheduler
事件聚合调度器

Implements event aggregation by user_id to reduce redundant portfolio recalculations.
实现按user_id的事件聚合，减少重复的投资组合重算。

Features:
- Polls EventOutbox for PENDING events
- Groups events by user_id (debounce window)
- Dispatches single portfolio recalculation task per user
- Updates event status: PENDING → PROCESSING → COMPLETED
- Uses SchedulerLock to prevent multiple instances
"""

import logging
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from collections import defaultdict
from itertools import groupby
import os
import socket

from app import db
from models import EventOutbox, EventFailure, EventStatus, SchedulerLock
from intelligence.events.contracts import EventTypes, AggregateTypes
from intelligence.workers.worker import enqueue_task
from intelligence.workers.tasks import recalculate_user_portfolio

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Constants
# ============================================================================

SCHEDULER_LOCK_KEY = "event_scheduler_lock"
LOCK_TIMEOUT_SECONDS = 120  # 2 minutes lock timeout
DEBOUNCE_WINDOW_SECONDS = 5  # Events created within 5 seconds are aggregated
MAX_EVENTS_PER_BATCH = 100  # Maximum events to process in one run
TASK_TIMEOUT_SECONDS = 300  # 5 minutes timeout for recalculation tasks


# ============================================================================
# Helper Functions
# ============================================================================

def extract_user_id_from_payload(payload: Dict[str, Any]) -> Optional[int]:
    """
    Extract user_id from event payload.
    从事件载荷中提取user_id。
    
    Checks multiple possible field names:
    - owner_id (for miner events)
    - user_id (for portfolio/user events)
    
    Args:
        payload: Event payload dictionary
        
    Returns:
        int: User ID if found, None otherwise
    """
    if not payload or not isinstance(payload, dict):
        return None
    
    # Check common user_id fields
    user_id = payload.get('user_id') or payload.get('owner_id')
    
    if user_id is not None:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id value in payload: {user_id}")
            return None
    
    return None


def aggregate_events_by_user(events: List[EventOutbox]) -> Dict[int, List[EventOutbox]]:
    """
    Group events by user_id.
    按user_id分组事件。
    
    Args:
        events: List of EventOutbox objects
        
    Returns:
        dict: {user_id: [event1, event2, ...]}
    """
    events_by_user = defaultdict(list)
    
    for event in events:
        user_id = extract_user_id_from_payload(event.event_payload)
        
        if user_id is not None:
            events_by_user[user_id].append(event)
        else:
            logger.warning(
                f"Event {event.id} ({event.event_type}) has no user_id in payload, skipping aggregation"
            )
    
    return dict(events_by_user)


def dispatch_user_recalc_task(user_id: int, event_ids: List[int]) -> bool:
    """
    Dispatch portfolio recalculation task for a user.
    为用户发送投资组合重算任务。
    
    Args:
        user_id: User ID to recalculate
        event_ids: List of event IDs that triggered this recalculation
        
    Returns:
        bool: True if task was enqueued successfully, False otherwise
    """
    try:
        logger.info(
            f"Dispatching portfolio recalculation for user_id={user_id}, "
            f"aggregating {len(event_ids)} events: {event_ids}"
        )
        
        # Enqueue task to intelligence queue with timeout and source_event_ids
        job = enqueue_task(
            'intelligence',
            recalculate_user_portfolio,
            user_id=user_id,
            source_event_ids=event_ids,
            timeout=TASK_TIMEOUT_SECONDS
        )
        
        if job:
            logger.info(
                f"Successfully enqueued recalculation task {job.id} for user_id={user_id} "
                f"with source_event_ids={event_ids}"
            )
            return True
        else:
            logger.error(f"Failed to enqueue task for user_id={user_id}")
            return False
            
    except Exception as e:
        logger.error(
            f"Error dispatching recalc task for user_id={user_id}: {str(e)}\n"
            f"{traceback.format_exc()}"
        )
        return False


def mark_events_processing(event_ids: List[int]) -> int:
    """
    Mark events as PROCESSING.
    标记事件为处理中。
    
    Args:
        event_ids: List of event IDs to mark
        
    Returns:
        int: Number of events updated
    """
    try:
        events = EventOutbox.query.filter(EventOutbox.id.in_(event_ids)).all()
        
        updated_count = 0
        for event in events:
            event.mark_processing()
            updated_count += 1
        
        db.session.commit()
        logger.info(f"Marked {updated_count} events as PROCESSING")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error marking events as processing: {str(e)}")
        db.session.rollback()
        return 0


def mark_events_completed(event_ids: List[int]) -> int:
    """
    Mark events as COMPLETED.
    标记事件为已完成。
    
    Args:
        event_ids: List of event IDs to mark
        
    Returns:
        int: Number of events updated
    """
    try:
        events = EventOutbox.query.filter(EventOutbox.id.in_(event_ids)).all()
        
        updated_count = 0
        for event in events:
            event.mark_completed()
            updated_count += 1
        
        db.session.commit()
        logger.info(f"Marked {updated_count} events as COMPLETED")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error marking events as completed: {str(e)}")
        db.session.rollback()
        return 0


def mark_events_failed(event_ids: List[int], error_message: str) -> int:
    """
    Mark events as FAILED and create failure records.
    标记事件为失败并创建失败记录。
    
    Args:
        event_ids: List of event IDs to mark
        error_message: Error message to record
        
    Returns:
        int: Number of events updated
    """
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
        logger.info(f"Marked {updated_count} events as FAILED")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error marking events as failed: {str(e)}")
        db.session.rollback()
        return 0


# ============================================================================
# Scheduler Lock Management
# ============================================================================

def acquire_scheduler_lock() -> Optional[SchedulerLock]:
    """
    Acquire scheduler lock to ensure single instance execution.
    获取调度器锁以确保单实例执行。
    
    Returns:
        SchedulerLock: Lock object if acquired, None otherwise
    """
    try:
        process_id = os.getpid()
        hostname = socket.gethostname()
        
        # Clean up expired locks first
        SchedulerLock.cleanup_expired_locks()
        db.session.commit()
        
        # Try to get existing lock
        existing_lock = SchedulerLock.query.filter_by(lock_key=SCHEDULER_LOCK_KEY).first()
        
        if existing_lock:
            if existing_lock.is_expired():
                # Lock expired, take it over
                logger.info(f"Taking over expired lock from PID={existing_lock.process_id}")
                existing_lock.process_id = process_id
                existing_lock.hostname = hostname
                existing_lock.refresh_lock(LOCK_TIMEOUT_SECONDS)
                db.session.commit()
                return existing_lock
            else:
                # Lock held by another process
                logger.debug(
                    f"Lock held by PID={existing_lock.process_id}@{existing_lock.hostname}, "
                    f"expires at {existing_lock.expires_at}"
                )
                return None
        else:
            # No existing lock, create new one
            expires_at = datetime.utcnow() + timedelta(seconds=LOCK_TIMEOUT_SECONDS)
            new_lock = SchedulerLock(
                lock_key=SCHEDULER_LOCK_KEY,
                process_id=process_id,
                hostname=hostname,
                expires_at=expires_at
            )
            db.session.add(new_lock)
            db.session.commit()
            logger.info(f"Acquired new scheduler lock: PID={process_id}@{hostname}")
            return new_lock
            
    except Exception as e:
        logger.error(f"Error acquiring scheduler lock: {str(e)}")
        db.session.rollback()
        return None


def release_scheduler_lock(lock: SchedulerLock):
    """
    Release scheduler lock.
    释放调度器锁。
    
    Args:
        lock: Lock object to release
    """
    try:
        if lock:
            db.session.delete(lock)
            db.session.commit()
            logger.info(f"Released scheduler lock: PID={lock.process_id}")
    except Exception as e:
        logger.error(f"Error releasing scheduler lock: {str(e)}")
        db.session.rollback()


# ============================================================================
# Main Aggregation Function
# ============================================================================

def run_event_aggregation() -> Dict[str, Any]:
    """
    Main event aggregation function.
    主事件聚合函数。
    
    This function:
    1. Acquires scheduler lock
    2. Queries PENDING events
    3. Groups events by user_id
    4. Dispatches portfolio recalculation tasks
    5. Updates event status
    6. Releases scheduler lock
    
    Returns:
        dict: {
            'success': bool,
            'events_processed': int,
            'users_affected': int,
            'tasks_dispatched': int,
            'errors': list,
            'timestamp': datetime
        }
    """
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info("Starting event aggregation run")
    logger.info("=" * 60)
    
    result = {
        'success': False,
        'events_processed': 0,
        'users_affected': 0,
        'tasks_dispatched': 0,
        'errors': [],
        'timestamp': start_time
    }
    
    # Acquire lock
    lock = acquire_scheduler_lock()
    if not lock:
        logger.debug("Could not acquire lock, another instance is running")
        result['errors'].append("Lock acquisition failed")
        return result
    
    try:
        # Query PENDING events within debounce window
        cutoff_time = datetime.utcnow() - timedelta(seconds=DEBOUNCE_WINDOW_SECONDS)
        
        pending_events = EventOutbox.query.filter(
            EventOutbox.status == EventStatus.PENDING
        ).filter(
            EventOutbox.created_at <= cutoff_time
        ).order_by(
            EventOutbox.created_at.asc()
        ).limit(MAX_EVENTS_PER_BATCH).all()
        
        if not pending_events:
            logger.info("No pending events to process")
            result['success'] = True
            return result
        
        logger.info(f"Found {len(pending_events)} pending events to process")
        
        # Filter only miner-related events (can be extended to other types)
        miner_event_types = [
            EventTypes.MINER_ADDED,
            EventTypes.MINER_UPDATED,
            EventTypes.MINER_DELETED,
            EventTypes.MINER_STATUS_CHANGED,
            EventTypes.MINER_PERFORMANCE_UPDATED
        ]
        
        relevant_events = [
            e for e in pending_events 
            if e.event_type in miner_event_types
        ]
        
        if not relevant_events:
            logger.info("No miner-related events found, skipping aggregation")
            result['success'] = True
            return result
        
        logger.info(f"Processing {len(relevant_events)} miner-related events")
        
        # Group events by user_id
        events_by_user = aggregate_events_by_user(relevant_events)
        
        logger.info(f"Aggregated events for {len(events_by_user)} users")
        
        # Process each user's events
        for user_id, user_events in events_by_user.items():
            event_ids = [e.id for e in user_events]
            event_types = [e.event_type for e in user_events]
            
            logger.info(
                f"Processing user_id={user_id}: {len(user_events)} events "
                f"(types: {', '.join(set(event_types))})"
            )
            
            # Dispatch recalculation task
            success = dispatch_user_recalc_task(user_id, event_ids)
            
            if success:
                # Mark events as PROCESSING - task will mark as COMPLETED/FAILED when done
                mark_events_processing(event_ids)
                result['events_processed'] += len(user_events)
                result['users_affected'] += 1
                result['tasks_dispatched'] += 1
            else:
                # ✅ Correct: enqueue failure keeps events PENDING for retry
                # Infrastructure failures (Redis down, etc.) are temporary - don't mark as FAILED
                # Events remain PENDING and will be retried on next aggregator run
                error_msg = f"Failed to dispatch recalculation task for user_id={user_id}"
                logger.error(
                    f"❌ {error_msg} - Events {event_ids} remain PENDING for retry on next run"
                )
                result['errors'].append(error_msg)
                # Don't call mark_events_failed() - keep events PENDING for retry
                # Don't create EventFailure - this is infrastructure failure, not business logic failure
        
        result['success'] = True
        
        # Log summary
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"Event aggregation completed in {elapsed:.2f}s")
        logger.info(f"Events processed: {result['events_processed']}")
        logger.info(f"Users affected: {result['users_affected']}")
        logger.info(f"Tasks dispatched: {result['tasks_dispatched']}")
        if result['errors']:
            logger.warning(f"Errors encountered: {len(result['errors'])}")
        logger.info("=" * 60)
        
    except Exception as e:
        error_msg = f"Event aggregation error: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        result['errors'].append(error_msg)
        
    finally:
        # Always release lock
        release_scheduler_lock(lock)
    
    return result


# ============================================================================
# Scheduled Task Entry Point
# ============================================================================

def scheduled_event_aggregation():
    """
    Entry point for scheduled event aggregation task.
    计划任务的入口点。
    
    This function is designed to be called by RQ scheduler every 30 seconds.
    此函数设计为每30秒由RQ调度器调用。
    """
    try:
        result = run_event_aggregation()
        return result
    except Exception as e:
        logger.error(f"Scheduled aggregation failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow()
        }


# ============================================================================
# Manual Testing / CLI Entry Point
# ============================================================================

if __name__ == '__main__':
    """
    Manual testing entry point.
    手动测试入口点。
    
    Usage:
        python -m intelligence.workers.event_scheduler
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Running event aggregation manually...")
    result = run_event_aggregation()
    
    print("\n" + "=" * 60)
    print("AGGREGATION RESULT:")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Events processed: {result['events_processed']}")
    print(f"Users affected: {result['users_affected']}")
    print(f"Tasks dispatched: {result['tasks_dispatched']}")
    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"  - {error}")
    print("=" * 60)
