"""
Automation Scheduler Service
自动化规则调度器服务

Scheduled jobs for:
- Checking automation rules and executing actions (every 2 minutes)
"""

import atexit
import hashlib
import logging
import os
import socket
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from models_control_plane import AuditEvent
from services.metrics_service import inc_rule_evals

logger = logging.getLogger(__name__)

METRIC_MAPPING = {
    'temp_max': 'temperature_max',
    'temp_avg': 'temperature_avg',
    'hashrate': 'hashrate_ghs',
    'power': 'power_consumption',
}

ACTION_TYPE_MAPPING = {
    'power_mode_low': ('power_mode', {'mode': 'low'}),
    'power_mode_normal': ('power_mode', {'mode': 'normal'}),
    'reboot': ('reboot', {}),
    'disable': ('disable', {}),
}


class AutomationSchedulerService:
    """
    Background scheduler for automation rule execution
    Uses APScheduler with SchedulerLock for single-instance execution
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._scheduler = None
            cls._instance._app = None
            cls._instance._is_running = False
            cls._instance.lock_key = "automation_scheduler_lock"
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
                worker_info = f"Automation Scheduler - PID {self.process_id} @ {self.hostname}"
                
                acquired = SchedulerLock.acquire_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id,
                    hostname=self.hostname,
                    timeout_seconds=lock_timeout,
                    worker_info=worker_info
                )
                
                if acquired:
                    logger.info(f"🔒 Automation scheduler acquired lock: {worker_info}")
                else:
                    logger.info("⏳ Automation scheduler lock held by another worker, skipping startup")
                
                return acquired
                
        except Exception as e:
            logger.error(f"Failed to acquire automation scheduler lock: {e}", exc_info=True)
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
                    logger.info("🔓 Automation scheduler released lock")
                    
        except Exception as e:
            logger.error(f"Failed to release automation scheduler lock: {e}")
    
    def init_app(self, app):
        """Initialize scheduler with Flask app context"""
        self._app = app
        
        if not self._acquire_scheduler_lock():
            logger.info("Automation scheduler not started (no lock)")
            return False
        
        logger.info(f"Automation scheduler acquired lock (PID={os.getpid()})")
        
        self._scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 300
            }
        )
        
        self._scheduler.add_job(
            self._check_automation_rules_job,
            IntervalTrigger(minutes=2),
            id='automation_rules_check',
            name='Check automation rules (every 2 minutes)',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._heartbeat_job,
            IntervalTrigger(seconds=60),
            id='automation_heartbeat',
            name='Scheduler heartbeat',
            replace_existing=True
        )
        
        self._scheduler.start()
        self._is_running = True
        atexit.register(self.stop)
        logger.info("Automation scheduler started successfully with 2 jobs")
        
        return True
    
    def _check_automation_rules_job(self):
        """Main job: Check all enabled automation rules and execute actions"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                from models import AutomationRule, AutomationRuleLog, AutomationRuleCooldown, HostingMiner
                from api.collector_api import MinerTelemetryLive, MinerCommand
                from db import db
                
                enabled_rules = AutomationRule.query.filter_by(is_enabled=True).order_by(AutomationRule.priority.desc()).all()
                
                if not enabled_rules:
                    logger.debug("[AutomationScheduler] No enabled automation rules found")
                    return
                
                logger.info(f"[AutomationScheduler] Checking {len(enabled_rules)} enabled rules")
                
                actions_taken = 0
                
                for rule in enabled_rules:
                    try:
                        actions_for_rule = self._process_rule(rule, db)
                        actions_taken += actions_for_rule
                        inc_rule_evals(rule.id, triggered=(actions_for_rule > 0))
                    except Exception as e:
                        logger.error(f"[AutomationScheduler] Error processing rule {rule.id} ({rule.name}): {e}", exc_info=True)
                        inc_rule_evals(rule.id, triggered=False)
                
                if actions_taken > 0:
                    logger.info(f"[AutomationScheduler] Completed: {actions_taken} actions taken")
                else:
                    logger.debug("[AutomationScheduler] Completed: no actions needed")
                    
            except Exception as e:
                logger.error(f"[AutomationScheduler] Rule check failed: {e}", exc_info=True)
    
    def _process_rule(self, rule, db) -> int:
        """Process a single automation rule and return count of actions taken"""
        from models import AutomationRuleLog, AutomationRuleCooldown, HostingMiner
        from api.collector_api import MinerTelemetryLive, MinerCommand
        
        actions_taken = 0
        
        telemetry_query = MinerTelemetryLive.query
        if rule.site_id:
            telemetry_query = telemetry_query.filter_by(site_id=rule.site_id)
        
        if rule.miner_ids and isinstance(rule.miner_ids, list) and len(rule.miner_ids) > 0:
            telemetry_query = telemetry_query.filter(MinerTelemetryLive.miner_id.in_(rule.miner_ids))
        
        telemetry_records = telemetry_query.filter_by(online=True).all()
        
        if not telemetry_records:
            return 0
        
        telemetry_field = METRIC_MAPPING.get(rule.trigger_metric, 'temperature_max')
        
        for telemetry in telemetry_records:
            try:
                actual_value = getattr(telemetry, telemetry_field, None)
                if actual_value is None:
                    continue
                
                if not self._check_threshold(actual_value, rule.trigger_operator, rule.trigger_value):
                    continue
                
                hosting_miner = HostingMiner.query.filter_by(
                    site_id=telemetry.site_id,
                    serial_number=telemetry.miner_id
                ).first()
                
                if not hosting_miner:
                    hosting_miner = HostingMiner.query.filter_by(
                        site_id=telemetry.site_id,
                        ip_address=telemetry.ip_address
                    ).first()
                
                if not hosting_miner:
                    logger.warning(f"[AutomationScheduler] Cannot find HostingMiner for telemetry miner_id={telemetry.miner_id}")
                    continue
                
                if self._is_in_cooldown(rule.id, hosting_miner.id):
                    logger.debug(f"[AutomationScheduler] Rule {rule.id} skipped for miner {hosting_miner.id}: in cooldown")
                    continue
                
                command = self._create_command(rule, telemetry, db)
                if command:
                    self._create_log(rule, hosting_miner, actual_value, command, db)
                    self._update_cooldown(rule, hosting_miner, db)
                    actions_taken += 1
                    logger.info(f"[AutomationScheduler] Rule '{rule.name}' triggered for miner {hosting_miner.id}: {telemetry_field}={actual_value} {rule.trigger_operator} {rule.trigger_value}")
                    
            except Exception as e:
                logger.error(f"[AutomationScheduler] Error processing telemetry for miner {telemetry.miner_id}: {e}")
        
        return actions_taken
    
    def _check_threshold(self, actual_value: float, operator: str, threshold: float) -> bool:
        """Check if actual value meets the threshold condition"""
        if operator == '>':
            return actual_value > threshold
        elif operator == '>=':
            return actual_value >= threshold
        elif operator == '<':
            return actual_value < threshold
        elif operator == '<=':
            return actual_value <= threshold
        elif operator == '==':
            return actual_value == threshold
        return False
    
    def _is_in_cooldown(self, rule_id: int, miner_id: int) -> bool:
        """Check if the rule-miner combination is still in cooldown period"""
        from models import AutomationRuleCooldown
        
        cooldown = AutomationRuleCooldown.query.filter_by(
            rule_id=rule_id,
            miner_id=miner_id
        ).first()
        
        if cooldown and cooldown.cooldown_until > datetime.utcnow():
            return True
        return False
    
    def _create_audit_event(self, site_id, event_type, rule_id, miner_id, payload=None):
        """Create an audit event for rule actions"""
        try:
            payload = payload or {}
            
            audit_event = AuditEvent(
                site_id=site_id,
                actor_type='system',
                actor_id='automation_scheduler',
                event_type=event_type,
                ref_type='automation_rule',
                ref_id=str(rule_id),
                payload_json=payload
            )
            
            audit_event.event_hash = audit_event.compute_hash()
            
            from db import db as database
            database.session.add(audit_event)
            database.session.commit()
            
            logger.debug(f"[AutomationScheduler] Audit event created: {event_type} for rule {rule_id}, miner {miner_id}")
        except Exception as e:
            logger.error(f"[AutomationScheduler] Failed to create audit event: {e}")
    
    def _create_command(self, rule, telemetry, db):
        """Create a MinerCommand record for the action with dedupe_key"""
        from api.collector_api import MinerCommand
        
        action_config = ACTION_TYPE_MAPPING.get(rule.action_type)
        if not action_config:
            logger.warning(f"[AutomationScheduler] Unknown action type: {rule.action_type}")
            return None
        
        command_type, default_params = action_config
        parameters = {**default_params, **(rule.action_parameters or {})}
        
        dedupe_key = hashlib.sha256(
            f"{rule.id}:{telemetry.miner_id}:{rule.action_type}:{rule.trigger_metric}".encode()
        ).hexdigest()[:32]
        
        existing_command = MinerCommand.query.filter_by(dedupe_key=dedupe_key).filter(
            MinerCommand.status.in_(['pending', 'dispatched', 'running'])
        ).first()
        
        if existing_command:
            self._create_audit_event(
                site_id=telemetry.site_id,
                event_type='rule.deduped',
                rule_id=rule.id,
                miner_id=telemetry.miner_id,
                payload={
                    'dedupe_key': dedupe_key,
                    'existing_command_id': existing_command.id,
                    'trigger_metric': rule.trigger_metric,
                    'action_type': rule.action_type
                }
            )
            logger.info(f"[AutomationScheduler] Duplicate command detected for rule {rule.id}, miner {telemetry.miner_id}: dedupe_key={dedupe_key}")
            return None
        
        command = MinerCommand(
            miner_id=telemetry.miner_id,
            site_id=telemetry.site_id,
            ip_address=telemetry.ip_address,
            command_type=command_type,
            parameters=parameters,
            status='pending',
            priority=rule.priority,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            retry_count=0,
            max_retries=3,
            dedupe_key=dedupe_key
        )
        
        db.session.add(command)
        db.session.commit()
        
        self._create_audit_event(
            site_id=telemetry.site_id,
            event_type='rule.command_created',
            rule_id=rule.id,
            miner_id=telemetry.miner_id,
            payload={
                'dedupe_key': dedupe_key,
                'command_id': command.id,
                'command_type': command_type,
                'trigger_metric': rule.trigger_metric,
                'action_type': rule.action_type
            }
        )
        
        return command
    
    def _create_log(self, rule, hosting_miner, actual_value: float, command, db):
        """Create an AutomationRuleLog record"""
        from models import AutomationRuleLog
        
        log = AutomationRuleLog(
            rule_id=rule.id,
            miner_id=hosting_miner.id,
            trigger_value_actual=actual_value,
            action_type=rule.action_type,
            action_status='pending',
            command_id=command.id
        )
        
        db.session.add(log)
        db.session.commit()
        
        return log
    
    def _update_cooldown(self, rule, hosting_miner, db):
        """Update or create AutomationRuleCooldown record"""
        from models import AutomationRuleCooldown
        
        cooldown = AutomationRuleCooldown.query.filter_by(
            rule_id=rule.id,
            miner_id=hosting_miner.id
        ).first()
        
        cooldown_until = datetime.utcnow() + timedelta(seconds=rule.cooldown_seconds)
        
        if cooldown:
            cooldown.last_triggered_at = datetime.utcnow()
            cooldown.cooldown_until = cooldown_until
        else:
            cooldown = AutomationRuleCooldown(
                rule_id=rule.id,
                miner_id=hosting_miner.id,
                last_triggered_at=datetime.utcnow(),
                cooldown_until=cooldown_until
            )
            db.session.add(cooldown)
        
        db.session.commit()
    
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
                    logger.debug("🔄 Automation scheduler heartbeat refreshed")
                else:
                    logger.warning("⚠️ Heartbeat failed: lock lost, stopping scheduler")
                    self.stop()
                    
        except Exception as e:
            logger.error(f"Automation scheduler heartbeat failed: {e}")
    
    def stop(self):
        """Stop scheduler and release lock"""
        if self._scheduler and self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Automation scheduler stopped")
        
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


automation_scheduler = AutomationSchedulerService()
