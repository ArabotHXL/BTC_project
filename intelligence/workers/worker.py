"""
RQ Worker Configuration and Startup
===================================

This module configures Redis connection and RQ queues for the intelligence worker system.
Workers process tasks from different priority queues.
"""

import os
import logging
from redis import Redis
from rq import Queue, Worker

logger = logging.getLogger(__name__)


def get_redis_connection():
    """
    Get Redis connection from environment variable or use default localhost.
    
    Returns:
        Redis: Redis connection instance
    """
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    try:
        redis_conn = Redis.from_url(redis_url, decode_responses=True)
        redis_conn.ping()
        logger.info(f"Connected to Redis at {redis_url}")
        return redis_conn
    except Exception as e:
        logger.error(f"Failed to connect to Redis at {redis_url}: {str(e)}")
        logger.warning("Falling back to localhost Redis connection")
        try:
            redis_conn = Redis(host='localhost', port=6379, db=0, decode_responses=True)
            redis_conn.ping()
            logger.info("Connected to Redis at localhost:6379")
            return redis_conn
        except Exception as e2:
            logger.error(f"Failed to connect to localhost Redis: {str(e2)}")
            raise


def create_queues(redis_conn):
    """
    Create RQ queue instances with different priorities.
    
    Args:
        redis_conn: Redis connection instance
        
    Returns:
        dict: Dictionary of queue name to Queue instance
    """
    queues = {
        'high': Queue('high', connection=redis_conn),
        'intelligence': Queue('intelligence', connection=redis_conn),
        'default': Queue('default', connection=redis_conn),
        'low': Queue('low', connection=redis_conn),
    }
    
    logger.info(f"Created {len(queues)} RQ queues: {list(queues.keys())}")
    return queues


def start_worker(queue_names=None, burst=False):
    """
    Start RQ worker to process tasks from specified queues.
    
    Args:
        queue_names: List of queue names to listen to (default: ['high', 'intelligence', 'default', 'low'])
        burst: If True, worker will quit after all jobs are processed (default: False)
    """
    if queue_names is None:
        queue_names = ['high', 'intelligence', 'default', 'low']
    
    try:
        redis_conn = get_redis_connection()
        queues = create_queues(redis_conn)
        
        worker_queues = [queues[name] for name in queue_names if name in queues]
        
        if not worker_queues:
            raise ValueError(f"No valid queues found. Available: {list(queues.keys())}")
        
        logger.info(f"Starting RQ worker for queues: {queue_names}")
        
        worker = Worker(worker_queues, connection=redis_conn)
        
        if burst:
            logger.info("Worker starting in burst mode (will exit after processing all jobs)")
            worker.work(burst=True)
        else:
            logger.info("Worker starting in continuous mode")
            worker.work()
            
    except KeyboardInterrupt:
        logger.info("Worker stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Worker error: {str(e)}", exc_info=True)
        raise


def enqueue_task(queue_name, func, *args, timeout=None, **kwargs):
    """
    Enqueue a task to a specific queue with optional timeout.
    
    Args:
        queue_name: Name of the queue ('high', 'intelligence', 'default', 'low')
        func: Function to execute
        *args: Positional arguments for the function
        timeout: Job timeout in seconds (optional, e.g., 300, 600, 900)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Job: RQ Job instance
        
    Examples:
        # Basic portfolio tasks (default queue, 5 min timeout)
        enqueue_task('default', recalculate_user_portfolio, user_id=123, timeout=300)
        enqueue_task('default', update_user_analytics, user_id=123, timeout=300)
        enqueue_task('default', refresh_user_cache, user_id=123, timeout=180)
        
        # Intelligence tasks (intelligence queue, longer timeouts)
        enqueue_task('intelligence', forecast_refresh, user_id=123, days=7, timeout=600)
        enqueue_task('intelligence', optimize_curtailment_task, 
                     user_id=123, schedule_date=date.today(), 
                     electricity_prices=[0.12]*24, timeout=900)
        enqueue_task('intelligence', detect_anomalies_task, user_id=123, timeout=600)
    """
    try:
        redis_conn = get_redis_connection()
        queues = create_queues(redis_conn)
        
        if queue_name not in queues:
            raise ValueError(f"Invalid queue name: {queue_name}. Available: {list(queues.keys())}")
        
        queue = queues[queue_name]
        
        if timeout:
            job = queue.enqueue(func, *args, job_timeout=timeout, **kwargs)
            logger.info(f"Enqueued job {job.id} to queue '{queue_name}': {func.__name__} (timeout={timeout}s)")
        else:
            job = queue.enqueue(func, *args, **kwargs)
            logger.info(f"Enqueued job {job.id} to queue '{queue_name}': {func.__name__}")
        
        return job
        
    except Exception as e:
        logger.error(f"Failed to enqueue task: {str(e)}", exc_info=True)
        raise


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("RQ Worker System Starting...")
    logger.info("=" * 60)
    
    import sys
    
    burst_mode = '--burst' in sys.argv
    
    if len(sys.argv) > 1 and sys.argv[1] not in ['--burst']:
        queue_names = [q for q in sys.argv[1:] if q != '--burst']
        start_worker(queue_names=queue_names, burst=burst_mode)
    else:
        start_worker(burst=burst_mode)
