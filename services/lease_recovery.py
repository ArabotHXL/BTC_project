"""
Lease Recovery Scheduler Service
租约恢复调度器服务

Scheduled job for:
- Recovering expired leases on MinerCommand records (every 60 seconds)
"""

import atexit
import logging
import os
import socket
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class LeaseRecoveryScheduler:
    """
    Background scheduler for lease recovery
    Uses APScheduler with SchedulerLock for single-instance execution
    
    Recovers expired leases on MinerCommand records that are in 'dispatched' status
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._scheduler = None
            cls._instance._app = None
            cls._instance._is_running = False
            cls._instance.lock_key = "lease_recovery_scheduler_lock"
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
                worker_info = f"Lease Recovery Scheduler - PID {self.process_id} @ {self.hostname}"
                
                acquired = SchedulerLock.acquire_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id,
                    hostname=self.hostname,
                    timeout_seconds=lock_timeout,
                    worker_info=worker_info
                )
                
                if acquired:
                    logger.info(f"🔒 Lease recovery scheduler acquired lock: {worker_info}")
                else:
                    logger.info("⏳ Lease recovery scheduler lock held by another worker, skipping startup")
                
                return acquired
                
        except Exception as e:
            logger.error(f"Failed to acquire lease recovery scheduler lock: {e}", exc_info=True)
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
                    logger.info("🔓 Lease recovery scheduler released lock")
                    
        except Exception as e:
            logger.error(f"Failed to release lease recovery scheduler lock: {e}")
    
    def init_app(self, app):
        """Initialize scheduler with Flask app context"""
        self._app = app
        
        if not self._acquire_scheduler_lock():
            logger.info("Lease recovery scheduler not started (no lock)")
            return False
        
        logger.info(f"Lease recovery scheduler acquired lock (PID={os.getpid()})")
        
        self._scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 300
            }
        )
        
        self._scheduler.add_job(
            self._recover_expired_leases_job,
            IntervalTrigger(seconds=60),
            id='lease_recovery_job',
            name='Recover expired leases (every 60 seconds)',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._heartbeat_job,
            IntervalTrigger(seconds=60),
            id='lease_recovery_heartbeat',
            name='Scheduler heartbeat',
            replace_existing=True
        )
        
        self._scheduler.start()
        self._is_running = True
        atexit.register(self.stop)
        logger.info("Lease recovery scheduler started successfully with 2 jobs")
        
        return True
    
    def _recover_expired_leases_job(self):
        """Main job: Recover expired leases on dispatched MinerCommands"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                recovered = self._recover_expired_leases()
                if recovered > 0:
                    logger.info(f"[LeaseRecoveryScheduler] Recovered {recovered} expired leases")
                else:
                    logger.debug("[LeaseRecoveryScheduler] No expired leases to recover")
            except Exception as e:
                logger.error(f"[LeaseRecoveryScheduler] Lease recovery failed: {e}", exc_info=True)
    
    def _recover_expired_leases(self) -> int:
        """
        Recover expired leases on MinerCommand records
        
        Returns:
            int: Number of leases recovered
        """
        from api.collector_api import MinerCommand
        from db import db
        
        recovered_count = 0
        
        # Find all dispatched commands with expired leases
        expired_leases = MinerCommand.query.filter(
            MinerCommand.status == 'dispatched',
            MinerCommand.lease_until < datetime.utcnow(),
            MinerCommand.lease_until.isnot(None),
            MinerCommand.lease_owner.isnot(None)
        ).all()
        
        if not expired_leases:
            return 0
        
        logger.debug(f"[LeaseRecoveryScheduler] Found {len(expired_leases)} expired leases")
        
        for command in expired_leases:
            try:
                if command.retry_count < command.max_retries:
                    self._retry_command(command, db)
                    recovered_count += 1
                else:
                    self._fail_command(command, db)
                    recovered_count += 1
            except Exception as e:
                logger.error(
                    f"[LeaseRecoveryScheduler] Failed to process command {command.id} "
                    f"(miner={command.miner_id}): {e}",
                    exc_info=True
                )
        
        return recovered_count
    
    def _retry_command(self, command, db):
        """Retry a command with exponential backoff"""
        from models_control_plane import AuditEvent
        
        # Increment retry count
        command.retry_count += 1
        
        # Calculate next attempt with exponential backoff
        # backoff = base_backoff * (2 ^ retry_count)
        backoff_seconds = command.retry_backoff_sec * (2 ** (command.retry_count - 1))
        command.next_attempt_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
        
        # Reset to pending status
        command.status = 'pending'
        
        # Clear lease
        command.lease_owner = None
        command.lease_until = None
        
        db.session.add(command)
        db.session.flush()
        
        # Create audit event
        audit_event = AuditEvent(
            site_id=command.site_id,
            actor_type='system',
            actor_id='lease_recovery_scheduler',
            event_type='command.lease_expired_retry',
            ref_type='miner_command',
            ref_id=str(command.id),
            payload_json={
                'miner_id': command.miner_id,
                'command_type': command.command_type,
                'retry_count': command.retry_count,
                'max_retries': command.max_retries,
                'next_attempt_at': command.next_attempt_at.isoformat(),
                'previous_lease_owner': command.lease_owner,
                'backoff_seconds': backoff_seconds
            }
        )
        
        audit_event.event_hash = audit_event.compute_hash()
        db.session.add(audit_event)
        db.session.commit()
        
        logger.info(
            f"[LeaseRecoveryScheduler] Lease expired, retrying command {command.id} "
            f"(miner={command.miner_id}, retry={command.retry_count}/{command.max_retries}, "
            f"next_attempt_in={backoff_seconds}s)"
        )
    
    def _fail_command(self, command, db):
        """Mark command as failed after max retries exceeded"""
        from models_control_plane import AuditEvent
        
        # Mark as failed
        command.status = 'failed'
        command.terminal_at = datetime.utcnow()
        
        # Clear lease
        command.lease_owner = None
        command.lease_until = None
        
        db.session.add(command)
        db.session.flush()
        
        # Create audit event
        audit_event = AuditEvent(
            site_id=command.site_id,
            actor_type='system',
            actor_id='lease_recovery_scheduler',
            event_type='command.lease_expired_failed',
            ref_type='miner_command',
            ref_id=str(command.id),
            payload_json={
                'miner_id': command.miner_id,
                'command_type': command.command_type,
                'retry_count': command.retry_count,
                'max_retries': command.max_retries,
                'terminal_at': command.terminal_at.isoformat(),
                'reason': 'Max retries exceeded due to lease expiration'
            }
        )
        
        audit_event.event_hash = audit_event.compute_hash()
        db.session.add(audit_event)
        db.session.commit()
        
        logger.warning(
            f"[LeaseRecoveryScheduler] Lease expired, command {command.id} failed after max retries "
            f"(miner={command.miner_id}, retries={command.retry_count}/{command.max_retries})"
        )
    
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
                    logger.debug("🔄 Lease recovery scheduler heartbeat refreshed")
                else:
                    logger.warning("⚠️ Heartbeat failed: lock lost, stopping scheduler")
                    self.stop()
                    
        except Exception as e:
            logger.error(f"Lease recovery scheduler heartbeat failed: {e}")
    
    def stop(self):
        """Stop scheduler and release lock"""
        if self._scheduler and self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Lease recovery scheduler stopped")
        
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


lease_recovery_scheduler = LeaseRecoveryScheduler()
