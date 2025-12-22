"""
4-Layer Telemetry Storage System
四层遥测存储系统

Layer 1: telemetry_raw_24h - Partitioned by hour, TTL 24h (DROP PARTITION)
Layer 2: miner_telemetry_live - Latest status per miner (existing)
Layer 3: telemetry_history_5min - 5-minute rollups, 60 days retention
Layer 4: telemetry_daily - Daily aggregates, long-term archive

Storage estimate for 6000 miners @ 30s polling:
- Raw 24h: ~17M rows/day, ~3-4 GiB (partitioned, auto-drop)
- History 5min: ~1.7M rows/day, ~300 MB, 60 days = 5-6 GiB
- Daily: 6K rows/day, ~1 MB, forever = <100 MB
- Total: ~9 GiB (within 10 GiB limit)
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from db import db

logger = logging.getLogger(__name__)


class TelemetryRaw24h(db.Model):
    """
    Layer 1: Raw telemetry data with 24-hour TTL
    Partitioned by hour for efficient DROP PARTITION cleanup
    """
    __tablename__ = 'telemetry_raw_24h'
    
    id = db.Column(db.BigInteger, primary_key=True)
    ts = db.Column(db.DateTime, nullable=False, index=True)
    site_id = db.Column(db.Integer, nullable=False)
    miner_id = db.Column(db.String(50), nullable=False)
    
    status = db.Column(db.String(20), default='online')
    hashrate_ths = db.Column(db.Float, default=0)
    temperature_c = db.Column(db.Float, default=0)
    power_w = db.Column(db.Float, default=0)
    fan_rpm = db.Column(db.Integer, default=0)
    reject_rate = db.Column(db.Float, default=0)
    pool_url = db.Column(db.String(200))
    
    __table_args__ = (
        db.Index('idx_raw_24h_site_miner_ts', 'site_id', 'miner_id', 'ts'),
        db.Index('idx_raw_24h_ts', 'ts'),
    )


class TelemetryHistory5min(db.Model):
    """
    Layer 3: 5-minute rollup aggregates
    60-day retention
    """
    __tablename__ = 'telemetry_history_5min'
    
    id = db.Column(db.BigInteger, primary_key=True)
    bucket_ts = db.Column(db.DateTime, nullable=False)
    site_id = db.Column(db.Integer, nullable=False)
    miner_id = db.Column(db.String(50), nullable=False)
    
    avg_hashrate_ths = db.Column(db.Float, default=0)
    max_hashrate_ths = db.Column(db.Float, default=0)
    min_hashrate_ths = db.Column(db.Float, default=0)
    avg_temp_c = db.Column(db.Float, default=0)
    max_temp_c = db.Column(db.Float, default=0)
    avg_power_w = db.Column(db.Float, default=0)
    avg_fan_rpm = db.Column(db.Float, default=0)
    online_ratio = db.Column(db.Float, default=1.0)
    samples = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_history_5min_site_miner_bucket', 'site_id', 'miner_id', 'bucket_ts'),
        db.Index('idx_history_5min_bucket', 'bucket_ts'),
        db.UniqueConstraint('site_id', 'miner_id', 'bucket_ts', name='uq_history_5min_bucket'),
    )


class TelemetryDaily(db.Model):
    """
    Layer 4: Daily aggregates for long-term archive
    """
    __tablename__ = 'telemetry_daily'
    
    id = db.Column(db.BigInteger, primary_key=True)
    day = db.Column(db.Date, nullable=False)
    site_id = db.Column(db.Integer, nullable=False)
    miner_id = db.Column(db.String(50), nullable=False)
    
    avg_hashrate_ths = db.Column(db.Float, default=0)
    max_hashrate_ths = db.Column(db.Float, default=0)
    min_hashrate_ths = db.Column(db.Float, default=0)
    avg_temp_c = db.Column(db.Float, default=0)
    max_temp_c = db.Column(db.Float, default=0)
    avg_power_w = db.Column(db.Float, default=0)
    total_power_kwh = db.Column(db.Float, default=0)
    online_ratio = db.Column(db.Float, default=1.0)
    uptime_hours = db.Column(db.Float, default=0)
    samples = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_daily_site_miner_day', 'site_id', 'miner_id', 'day'),
        db.Index('idx_daily_day', 'day'),
        db.UniqueConstraint('site_id', 'miner_id', 'day', name='uq_daily_miner'),
    )


class TelemetryStorageManager:
    """
    Manages partition creation, cleanup, and rollup operations
    """
    
    RAW_RETENTION_HOURS = 26  # Keep 26 hours to ensure full 24h window
    HISTORY_RETENTION_DAYS = 60
    
    @staticmethod
    def ensure_tables_exist():
        """Create tables if they don't exist (non-partitioned fallback)"""
        try:
            db.create_all()
            logger.info("Telemetry storage tables created/verified")
            return True
        except Exception as e:
            logger.error(f"Failed to create telemetry tables: {e}")
            return False
    
    @staticmethod
    def batch_insert_raw(records: list) -> int:
        """
        Batch insert raw telemetry records
        
        Args:
            records: List of dicts with keys matching TelemetryRaw24h columns
            
        Returns:
            Number of records inserted
        """
        if not records:
            return 0
        
        try:
            now = datetime.utcnow()
            inserts = []
            
            for r in records:
                inserts.append({
                    'ts': r.get('ts', now),
                    'site_id': r['site_id'],
                    'miner_id': r['miner_id'],
                    'status': 'online' if r.get('online', False) else 'offline',
                    'hashrate_ths': (r.get('hashrate_ghs', 0) or 0) / 1000,
                    'temperature_c': r.get('temperature_avg', 0) or 0,
                    'power_w': r.get('power_consumption', 0) or 0,
                    'fan_rpm': r.get('fan_speed_avg', 0) or 0,
                    'reject_rate': r.get('reject_rate', 0) or 0,
                    'pool_url': r.get('pool_url', '')[:200] if r.get('pool_url') else None,
                })
            
            db.session.bulk_insert_mappings(TelemetryRaw24h, inserts)
            db.session.commit()
            
            logger.debug(f"Inserted {len(inserts)} raw telemetry records")
            return len(inserts)
            
        except Exception as e:
            logger.error(f"Batch insert raw failed: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def cleanup_old_raw_data() -> int:
        """
        Delete raw data older than retention period
        For non-partitioned table, use DELETE (less efficient but works)
        
        Returns:
            Number of records deleted
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=TelemetryStorageManager.RAW_RETENTION_HOURS)
            
            result = db.session.execute(
                text("DELETE FROM telemetry_raw_24h WHERE ts < :cutoff"),
                {'cutoff': cutoff}
            )
            db.session.commit()
            
            deleted = result.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old raw telemetry records (before {cutoff})")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cleanup old raw data failed: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def rollup_to_5min() -> int:
        """
        Aggregate raw data into 5-minute buckets
        
        Returns:
            Number of buckets created/updated
        """
        try:
            now = datetime.utcnow()
            bucket_start = now.replace(second=0, microsecond=0)
            bucket_start = bucket_start.replace(minute=(bucket_start.minute // 5) * 5)
            bucket_end = bucket_start + timedelta(minutes=5)
            lookback = bucket_start - timedelta(minutes=10)
            
            sql = text("""
                INSERT INTO telemetry_history_5min 
                    (bucket_ts, site_id, miner_id, avg_hashrate_ths, max_hashrate_ths, min_hashrate_ths,
                     avg_temp_c, max_temp_c, avg_power_w, avg_fan_rpm, online_ratio, samples, created_at)
                SELECT 
                    date_trunc('hour', ts) + 
                        (EXTRACT(minute FROM ts)::int / 5 * INTERVAL '5 minutes') as bucket_ts,
                    site_id,
                    miner_id,
                    AVG(hashrate_ths) as avg_hashrate_ths,
                    MAX(hashrate_ths) as max_hashrate_ths,
                    MIN(hashrate_ths) as min_hashrate_ths,
                    AVG(temperature_c) as avg_temp_c,
                    MAX(temperature_c) as max_temp_c,
                    AVG(power_w) as avg_power_w,
                    AVG(fan_rpm) as avg_fan_rpm,
                    SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END)::float / COUNT(*) as online_ratio,
                    COUNT(*) as samples,
                    NOW() as created_at
                FROM telemetry_raw_24h
                WHERE ts >= :lookback AND ts < :bucket_end
                GROUP BY bucket_ts, site_id, miner_id
                ON CONFLICT (site_id, miner_id, bucket_ts) 
                DO UPDATE SET
                    avg_hashrate_ths = EXCLUDED.avg_hashrate_ths,
                    max_hashrate_ths = EXCLUDED.max_hashrate_ths,
                    min_hashrate_ths = EXCLUDED.min_hashrate_ths,
                    avg_temp_c = EXCLUDED.avg_temp_c,
                    max_temp_c = EXCLUDED.max_temp_c,
                    avg_power_w = EXCLUDED.avg_power_w,
                    avg_fan_rpm = EXCLUDED.avg_fan_rpm,
                    online_ratio = EXCLUDED.online_ratio,
                    samples = EXCLUDED.samples
            """)
            
            result = db.session.execute(sql, {'lookback': lookback, 'bucket_end': bucket_end})
            db.session.commit()
            
            affected = result.rowcount
            if affected > 0:
                logger.info(f"Rolled up {affected} 5-minute buckets")
            
            return affected
            
        except Exception as e:
            logger.error(f"Rollup to 5min failed: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def rollup_to_daily() -> int:
        """
        Aggregate 5-minute history into daily summaries
        
        Returns:
            Number of daily records created/updated
        """
        try:
            yesterday = (datetime.utcnow() - timedelta(days=1)).date()
            
            sql = text("""
                INSERT INTO telemetry_daily 
                    (day, site_id, miner_id, avg_hashrate_ths, max_hashrate_ths, min_hashrate_ths,
                     avg_temp_c, max_temp_c, avg_power_w, total_power_kwh, online_ratio, 
                     uptime_hours, samples, created_at)
                SELECT 
                    DATE(bucket_ts) as day,
                    site_id,
                    miner_id,
                    AVG(avg_hashrate_ths) as avg_hashrate_ths,
                    MAX(max_hashrate_ths) as max_hashrate_ths,
                    MIN(min_hashrate_ths) as min_hashrate_ths,
                    AVG(avg_temp_c) as avg_temp_c,
                    MAX(max_temp_c) as max_temp_c,
                    AVG(avg_power_w) as avg_power_w,
                    SUM(avg_power_w * 5 / 60 / 1000) as total_power_kwh,
                    AVG(online_ratio) as online_ratio,
                    SUM(online_ratio * 5 / 60) as uptime_hours,
                    SUM(samples) as samples,
                    NOW() as created_at
                FROM telemetry_history_5min
                WHERE DATE(bucket_ts) = :yesterday
                GROUP BY day, site_id, miner_id
                ON CONFLICT (site_id, miner_id, day) 
                DO UPDATE SET
                    avg_hashrate_ths = EXCLUDED.avg_hashrate_ths,
                    max_hashrate_ths = EXCLUDED.max_hashrate_ths,
                    min_hashrate_ths = EXCLUDED.min_hashrate_ths,
                    avg_temp_c = EXCLUDED.avg_temp_c,
                    max_temp_c = EXCLUDED.max_temp_c,
                    avg_power_w = EXCLUDED.avg_power_w,
                    total_power_kwh = EXCLUDED.total_power_kwh,
                    online_ratio = EXCLUDED.online_ratio,
                    uptime_hours = EXCLUDED.uptime_hours,
                    samples = EXCLUDED.samples
            """)
            
            result = db.session.execute(sql, {'yesterday': yesterday})
            db.session.commit()
            
            affected = result.rowcount
            if affected > 0:
                logger.info(f"Created {affected} daily aggregate records for {yesterday}")
            
            return affected
            
        except Exception as e:
            logger.error(f"Rollup to daily failed: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def cleanup_old_history() -> int:
        """
        Delete 5-minute history older than retention period
        
        Returns:
            Number of records deleted
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=TelemetryStorageManager.HISTORY_RETENTION_DAYS)
            
            result = db.session.execute(
                text("DELETE FROM telemetry_history_5min WHERE bucket_ts < :cutoff"),
                {'cutoff': cutoff}
            )
            db.session.commit()
            
            deleted = result.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old 5-minute history records")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cleanup old history failed: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_storage_stats() -> dict:
        """Get storage statistics for all telemetry tables"""
        try:
            stats = {}
            
            tables = [
                ('telemetry_raw_24h', 'ts'),
                ('telemetry_history_5min', 'bucket_ts'),
                ('telemetry_daily', 'day'),
                ('miner_telemetry_live', 'updated_at'),
                ('miner_telemetry_history', 'timestamp'),
            ]
            
            for table, time_col in tables:
                try:
                    count_result = db.session.execute(
                        text(f"SELECT COUNT(*) as cnt FROM {table}")
                    ).fetchone()
                    
                    oldest_result = db.session.execute(
                        text(f"SELECT MIN({time_col}) as oldest FROM {table}")
                    ).fetchone()
                    
                    newest_result = db.session.execute(
                        text(f"SELECT MAX({time_col}) as newest FROM {table}")
                    ).fetchone()
                    
                    size_result = db.session.execute(
                        text(f"SELECT pg_size_pretty(pg_total_relation_size('{table}')) as size")
                    ).fetchone()
                    
                    stats[table] = {
                        'count': count_result[0] if count_result else 0,
                        'oldest': str(oldest_result[0]) if oldest_result and oldest_result[0] else None,
                        'newest': str(newest_result[0]) if newest_result and newest_result[0] else None,
                        'size': size_result[0] if size_result else 'unknown',
                    }
                except Exception as e:
                    stats[table] = {'error': str(e)}
            
            total_size_result = db.session.execute(
                text("""
                    SELECT pg_size_pretty(SUM(pg_total_relation_size(tablename::regclass)))
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename LIKE 'telemetry%' OR tablename LIKE 'miner_telemetry%'
                """)
            ).fetchone()
            
            stats['total_telemetry_size'] = total_size_result[0] if total_size_result else 'unknown'
            
            return stats
            
        except Exception as e:
            logger.error(f"Get storage stats failed: {e}")
            return {'error': str(e)}
