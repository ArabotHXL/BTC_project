"""
Telemetry Scheduler Service
遥测数据调度器服务

Scheduled jobs for:
- Partition cleanup (hourly)
- 5-minute rollup (every 5 minutes)
- Daily rollup (daily at 00:30 UTC)
- History cleanup (daily)
"""

import atexit
import logging
import os
import socket
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class TelemetrySchedulerService:
    """
    Background scheduler for telemetry data management
    Uses APScheduler with SchedulerLock for single-instance execution
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._scheduler = None
            cls._instance._app = None
            cls._instance._is_running = False
            cls._instance.lock_key = "telemetry_scheduler_lock"
            cls._instance.process_id = os.getpid()
            cls._instance.hostname = socket.gethostname()
        return cls._instance
    
    def _acquire_scheduler_lock(self):
        """Acquire database lock to prevent multiple scheduler instances"""
        if not self._app:
            logger.error("Flask app not set, cannot acquire scheduler lock")
            return False
        
        try:
            with self._app.app_context():
                from models import SchedulerLock, db
                
                lock_timeout = 300
                worker_info = f"Telemetry Scheduler - PID {self.process_id} @ {self.hostname}"
                
                acquired = SchedulerLock.acquire_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id,
                    hostname=self.hostname,
                    timeout_seconds=lock_timeout,
                    worker_info=worker_info
                )
                
                if acquired:
                    logger.info(f"🔒 Telemetry scheduler acquired lock: {worker_info}")
                else:
                    logger.info("⏳ Telemetry scheduler lock held by another worker, skipping startup")
                
                return acquired
                
        except Exception as e:
            logger.error(f"Failed to acquire telemetry scheduler lock: {e}", exc_info=True)
            return False
    
    def _release_scheduler_lock(self):
        """Release database lock"""
        if not self._app:
            return
        
        try:
            with self._app.app_context():
                from models import SchedulerLock
                
                released = SchedulerLock.release_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id
                )
                
                if released:
                    logger.info("🔓 Telemetry scheduler released lock")
                    
        except Exception as e:
            logger.error(f"Failed to release telemetry scheduler lock: {e}")
    
    def init_app(self, app):
        """Initialize scheduler with Flask app context"""
        self._app = app
        
        if not self._acquire_scheduler_lock():
            logger.info("Telemetry scheduler not started (no lock)")
            return False
        
        logger.info(f"Telemetry scheduler acquired lock (PID={os.getpid()})")
        
        self._scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 300
            }
        )
        
        self._scheduler.add_job(
            self._cleanup_raw_job,
            IntervalTrigger(hours=1),
            id='telemetry_cleanup_raw',
            name='Cleanup raw telemetry (hourly)',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._rollup_5min_job,
            IntervalTrigger(minutes=5),
            id='telemetry_rollup_5min',
            name='Rollup to 5-minute buckets',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._rollup_daily_job,
            CronTrigger(hour=0, minute=30),
            id='telemetry_rollup_daily',
            name='Rollup to daily aggregates',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._cleanup_history_job,
            CronTrigger(hour=1, minute=0),
            id='telemetry_cleanup_history',
            name='Cleanup old history (daily)',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._heartbeat_job,
            IntervalTrigger(seconds=60),
            id='telemetry_heartbeat',
            name='Scheduler heartbeat',
            replace_existing=True
        )
        
        self._scheduler.start()
        self._is_running = True
        atexit.register(self.stop)
        logger.info("Telemetry scheduler started successfully with 5 jobs")
        
        return True
    
    def _cleanup_raw_job(self):
        """Cleanup raw telemetry older than 24h"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                from services.telemetry_storage import TelemetryStorageManager
                deleted = TelemetryStorageManager.cleanup_old_raw_data()
                logger.info(f"[TelemetryScheduler] Raw cleanup completed: {deleted} records deleted")
            except Exception as e:
                logger.error(f"[TelemetryScheduler] Raw cleanup failed: {e}")
    
    def _rollup_5min_job(self):
        """Aggregate raw data into 5-minute buckets"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                from services.telemetry_storage import TelemetryStorageManager
                affected = TelemetryStorageManager.rollup_to_5min()
                if affected > 0:
                    logger.debug(f"[TelemetryScheduler] 5-min rollup: {affected} buckets")
            except Exception as e:
                logger.error(f"[TelemetryScheduler] 5-min rollup failed: {e}")
    
    def _rollup_daily_job(self):
        """Aggregate 5-minute history into daily summaries"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                from services.telemetry_storage import TelemetryStorageManager
                affected = TelemetryStorageManager.rollup_to_daily()
                logger.info(f"[TelemetryScheduler] Daily rollup completed: {affected} records")
            except Exception as e:
                logger.error(f"[TelemetryScheduler] Daily rollup failed: {e}")
    
    def _cleanup_history_job(self):
        """Cleanup 5-minute history older than 60 days"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                from services.telemetry_storage import TelemetryStorageManager
                deleted = TelemetryStorageManager.cleanup_old_history()
                logger.info(f"[TelemetryScheduler] History cleanup completed: {deleted} records deleted")
            except Exception as e:
                logger.error(f"[TelemetryScheduler] History cleanup failed: {e}")
    
    def _heartbeat_job(self):
        """Refresh scheduler lock to prevent expiration"""
        if not self._app:
            return
        
        try:
            with self._app.app_context():
                from models import SchedulerLock, db
                
                lock = SchedulerLock.get_active_lock(self.lock_key)
                if lock and lock.process_id == self.process_id:
                    lock.refresh_lock(timeout_seconds=300)
                    db.session.commit()
                    logger.debug("🔄 Telemetry scheduler heartbeat refreshed")
                else:
                    logger.warning("⚠️ Heartbeat failed: lock lost, stopping scheduler")
                    self.stop()
                    
        except Exception as e:
            logger.error(f"Telemetry scheduler heartbeat failed: {e}")
    
    def stop(self):
        """Stop scheduler and release lock"""
        if self._scheduler and self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Telemetry scheduler stopped")
        
        self._release_scheduler_lock()
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        if not self._scheduler:
            return {'running': False, 'jobs': []}
        
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': str(job.next_run_time) if job.next_run_time else None,
            })
        
        return {
            'running': self._scheduler.running,
            'jobs': jobs
        }


telemetry_scheduler = TelemetrySchedulerService()
