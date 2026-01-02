"""
Power Aggregation Scheduler Service
电力聚合调度器服务

Scheduled jobs for:
- Hourly energy aggregation (every hour)
- Daily energy aggregation (daily at 01:00 UTC)
- Monthly energy aggregation (monthly on 1st at 02:00 UTC)
"""

import atexit
import logging
import os
import socket
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func

logger = logging.getLogger(__name__)

CARBON_EMISSION_FACTORS = {
    'hydro': 0.024,
    'solar': 0.048,
    'wind': 0.011,
    'nuclear': 0.012,
    'natural_gas': 0.41,
    'coal': 0.82,
    'grid': 0.42
}


class PowerAggregationScheduler:
    """
    Background scheduler for power/energy data aggregation
    Uses APScheduler with SchedulerLock for single-instance execution
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._scheduler = None
            cls._instance._app = None
            cls._instance._is_running = False
            cls._instance.lock_key = "power_aggregation_scheduler_lock"
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
                from app import db
                from models import SchedulerLock
                
                lock_timeout = 300
                worker_info = f"Power Aggregation Scheduler - PID {self.process_id} @ {self.hostname}"
                
                acquired = SchedulerLock.acquire_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id,
                    hostname=self.hostname,
                    timeout_seconds=lock_timeout,
                    worker_info=worker_info
                )
                
                if acquired:
                    logger.info(f"🔒 Power aggregation scheduler acquired lock: {worker_info}")
                else:
                    logger.info("⏳ Power aggregation scheduler lock held by another worker, skipping startup")
                
                return acquired
                
        except Exception as e:
            logger.error(f"Failed to acquire power aggregation scheduler lock: {e}", exc_info=True)
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
                    logger.info("🔓 Power aggregation scheduler released lock")
                    
        except Exception as e:
            logger.error(f"Failed to release power aggregation scheduler lock: {e}")
    
    def init_app(self, app):
        """Initialize scheduler with Flask app context"""
        self._app = app
        
        if not self._acquire_scheduler_lock():
            logger.info("Power aggregation scheduler not started (no lock)")
            return False
        
        logger.info(f"Power aggregation scheduler acquired lock (PID={os.getpid()})")
        
        self._scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 300
            }
        )
        
        self._scheduler.add_job(
            self._aggregate_hourly,
            IntervalTrigger(hours=1),
            id='power_aggregate_hourly',
            name='Aggregate hourly site energy',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._aggregate_daily,
            CronTrigger(hour=1, minute=0),
            id='power_aggregate_daily',
            name='Aggregate daily site energy',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._aggregate_monthly,
            CronTrigger(day=1, hour=2, minute=0),
            id='power_aggregate_monthly',
            name='Aggregate monthly site energy',
            replace_existing=True
        )
        
        self._scheduler.add_job(
            self._heartbeat_job,
            IntervalTrigger(seconds=60),
            id='power_aggregation_heartbeat',
            name='Scheduler heartbeat',
            replace_existing=True
        )
        
        self._scheduler.start()
        self._is_running = True
        atexit.register(self.shutdown)
        logger.info("Power aggregation scheduler started successfully with 4 jobs")
        
        return True
    
    def _get_carbon_factor(self, energy_source: str | None) -> float:
        """Get carbon emission factor for energy source"""
        if energy_source and energy_source.lower() in CARBON_EMISSION_FACTORS:
            return CARBON_EMISSION_FACTORS[energy_source.lower()]
        return CARBON_EMISSION_FACTORS['grid']
    
    def _aggregate_hourly(self):
        """Aggregate telemetry data into hourly site energy records"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                from app import db
                from models import (
                    HostingSite, HostingMiner, MinerTelemetry, 
                    SiteEnergyHourly
                )
                
                now = datetime.utcnow()
                hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                hour_end = hour_start + timedelta(hours=1)
                
                sites = HostingSite.query.all()
                aggregated_count = 0
                
                for site in sites:
                    miner_ids = [m.id for m in site.miners]
                    if not miner_ids:
                        continue
                    
                    telemetry_data = MinerTelemetry.query.filter(
                        MinerTelemetry.miner_id.in_(miner_ids),
                        MinerTelemetry.recorded_at >= hour_start,
                        MinerTelemetry.recorded_at < hour_end
                    ).all()
                    
                    if not telemetry_data:
                        continue
                    
                    power_readings = [t.power_consumption for t in telemetry_data if t.power_consumption]
                    if not power_readings:
                        continue
                    
                    avg_kw = sum(power_readings) / len(power_readings) / 1000.0
                    peak_kw = max(power_readings) / 1000.0
                    kwh = avg_kw * 1.0
                    
                    electricity_rate = getattr(site, 'electricity_rate', 0.0) or 0.0
                    cost_usd = kwh * electricity_rate
                    
                    electricity_source = getattr(site, 'electricity_source', None)
                    carbon_factor = self._get_carbon_factor(electricity_source)
                    co2_kg = kwh * carbon_factor
                    
                    miner_count = len(set(t.miner_id for t in telemetry_data))
                    
                    existing = SiteEnergyHourly.query.filter_by(
                        site_id=site.id,
                        hour_ts=hour_start
                    ).first()
                    
                    if existing:
                        existing.kwh = kwh
                        existing.avg_kw = avg_kw
                        existing.peak_kw = peak_kw
                        existing.cost_usd = cost_usd
                        existing.co2_kg = co2_kg
                        existing.miner_count = miner_count
                    else:
                        record = SiteEnergyHourly(
                            site_id=site.id,
                            hour_ts=hour_start,
                            kwh=kwh,
                            avg_kw=avg_kw,
                            peak_kw=peak_kw,
                            cost_usd=cost_usd,
                            co2_kg=co2_kg,
                            miner_count=miner_count
                        )
                        db.session.add(record)
                    
                    aggregated_count += 1
                
                db.session.commit()
                logger.info(f"[PowerAggregation] Hourly aggregation completed: {aggregated_count} sites")
                
            except Exception as e:
                logger.error(f"[PowerAggregation] Hourly aggregation failed: {e}", exc_info=True)
                db.session.rollback()
    
    def _aggregate_daily(self):
        """Aggregate hourly data into daily site energy records"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                from app import db
                from models import HostingSite, SiteEnergyHourly, SiteEnergyDaily
                
                yesterday = (datetime.utcnow() - timedelta(days=1)).date()
                day_start = datetime.combine(yesterday, datetime.min.time())
                day_end = day_start + timedelta(days=1)
                
                sites = HostingSite.query.all()
                aggregated_count = 0
                
                for site in sites:
                    hourly_data = SiteEnergyHourly.query.filter(
                        SiteEnergyHourly.site_id == site.id,
                        SiteEnergyHourly.hour_ts >= day_start,
                        SiteEnergyHourly.hour_ts < day_end
                    ).all()
                    
                    if not hourly_data:
                        continue
                    
                    total_kwh = sum(h.kwh for h in hourly_data)
                    total_cost = sum(h.cost_usd for h in hourly_data)
                    peak_kw = max(h.peak_kw for h in hourly_data)
                    total_co2 = sum(h.co2_kg for h in hourly_data)
                    max_miners = max(h.miner_count for h in hourly_data)
                    
                    avg_price = total_cost / total_kwh if total_kwh > 0 else 0.0
                    
                    existing = SiteEnergyDaily.query.filter_by(
                        site_id=site.id,
                        date=yesterday
                    ).first()
                    
                    if existing:
                        existing.kwh = total_kwh
                        existing.cost_usd = total_cost
                        existing.peak_kw = peak_kw
                        existing.co2_kg = total_co2
                        existing.avg_price_per_kwh = avg_price
                        existing.miner_count = max_miners
                    else:
                        record = SiteEnergyDaily(
                            site_id=site.id,
                            date=yesterday,
                            kwh=total_kwh,
                            cost_usd=total_cost,
                            peak_kw=peak_kw,
                            co2_kg=total_co2,
                            avg_price_per_kwh=avg_price,
                            miner_count=max_miners
                        )
                        db.session.add(record)
                    
                    aggregated_count += 1
                
                db.session.commit()
                logger.info(f"[PowerAggregation] Daily aggregation completed: {aggregated_count} sites")
                
            except Exception as e:
                logger.error(f"[PowerAggregation] Daily aggregation failed: {e}", exc_info=True)
                db.session.rollback()
    
    def _aggregate_monthly(self):
        """Aggregate daily data into monthly site energy records"""
        if not self._app:
            return
        
        with self._app.app_context():
            try:
                from app import db
                from models import HostingSite, SiteEnergyDaily, SiteEnergyMonthly
                
                today = datetime.utcnow().date()
                first_of_this_month = today.replace(day=1)
                last_month_end = first_of_this_month - timedelta(days=1)
                last_month_start = last_month_end.replace(day=1)
                
                sites = HostingSite.query.all()
                aggregated_count = 0
                
                for site in sites:
                    daily_data = SiteEnergyDaily.query.filter(
                        SiteEnergyDaily.site_id == site.id,
                        SiteEnergyDaily.date >= last_month_start,
                        SiteEnergyDaily.date <= last_month_end
                    ).all()
                    
                    if not daily_data:
                        continue
                    
                    total_kwh = sum(d.kwh for d in daily_data)
                    total_cost = sum(d.cost_usd for d in daily_data)
                    peak_kw = max(d.peak_kw for d in daily_data)
                    total_co2 = sum(d.co2_kg for d in daily_data)
                    
                    avg_price = total_cost / total_kwh if total_kwh > 0 else 0.0
                    
                    existing = SiteEnergyMonthly.query.filter_by(
                        site_id=site.id,
                        month=last_month_start
                    ).first()
                    
                    if existing:
                        existing.kwh = total_kwh
                        existing.cost_usd = total_cost
                        existing.peak_kw = peak_kw
                        existing.co2_kg = total_co2
                        existing.avg_price_per_kwh = avg_price
                    else:
                        record = SiteEnergyMonthly(
                            site_id=site.id,
                            month=last_month_start,
                            kwh=total_kwh,
                            cost_usd=total_cost,
                            peak_kw=peak_kw,
                            co2_kg=total_co2,
                            avg_price_per_kwh=avg_price
                        )
                        db.session.add(record)
                    
                    aggregated_count += 1
                
                db.session.commit()
                logger.info(f"[PowerAggregation] Monthly aggregation completed: {aggregated_count} sites")
                
            except Exception as e:
                logger.error(f"[PowerAggregation] Monthly aggregation failed: {e}", exc_info=True)
                db.session.rollback()
    
    def _heartbeat_job(self):
        """Refresh scheduler lock to prevent expiration"""
        if not self._app:
            return
        
        try:
            with self._app.app_context():
                from app import db
                from models import SchedulerLock
                
                lock_timeout = 300
                worker_info = f"Power Aggregation Scheduler - PID {self.process_id} @ {self.hostname}"
                
                acquired = SchedulerLock.acquire_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id,
                    hostname=self.hostname,
                    timeout_seconds=lock_timeout,
                    worker_info=worker_info
                )
                
                if acquired:
                    logger.debug("🔄 Power aggregation scheduler heartbeat refreshed")
                else:
                    logger.warning("⚠️ Heartbeat failed: lock lost, stopping scheduler")
                    self.shutdown()
                    
        except Exception as e:
            logger.error(f"Power aggregation scheduler heartbeat failed: {e}")
    
    def shutdown(self):
        """Stop scheduler and release lock"""
        if self._scheduler and self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Power aggregation scheduler stopped")
        
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


power_aggregation_scheduler = PowerAggregationScheduler()
