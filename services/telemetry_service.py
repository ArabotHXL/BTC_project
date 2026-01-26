"""
Unified Telemetry Service
统一遥测数据服务 - 单一数据真相

This service provides a single source of truth for telemetry data:
- Write path: collector → raw_24h → live & history (via background jobs)
- Read path: unified API for all consumers (UI, alerts, reports)

Data Layers:
- telemetry_raw_24h: Raw data, 24h retention
- miner_telemetry_live: Current snapshot, one record per miner
- telemetry_history_5min: 5-minute aggregates, 90 day retention
- telemetry_daily: Daily aggregates, 365 day retention
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from flask import current_app
from sqlalchemy import text, func
from db import db

logger = logging.getLogger(__name__)


class TelemetryLayer:
    RAW_24H = 'telemetry_raw_24h'
    LIVE = 'miner_telemetry_live'
    HISTORY_5MIN = 'telemetry_history_5min'
    DAILY = 'telemetry_daily'


class TelemetryService:
    """Unified Telemetry Service - Single Source of Truth"""
    
    @staticmethod
    def write_raw(site_id: int, miner_id: str, data: dict) -> bool:
        """Write raw telemetry data (collector entry point)
        
        This is the ONLY write entry point for external systems.
        Background jobs handle live/history updates.
        """
        try:
            sql = text("""
                INSERT INTO telemetry_raw_24h 
                (ts, site_id, miner_id, status, hashrate_ths, temperature_c, power_w, fan_rpm, reject_rate, pool_url)
                VALUES (:ts, :site_id, :miner_id, :status, :hashrate_ths, :temperature_c, :power_w, :fan_rpm, :reject_rate, :pool_url)
            """)
            
            db.session.execute(sql, {
                'ts': data.get('ts', datetime.utcnow()),
                'site_id': site_id,
                'miner_id': miner_id,
                'status': data.get('status', 'online'),
                'hashrate_ths': data.get('hashrate_ths'),
                'temperature_c': data.get('temperature_c'),
                'power_w': data.get('power_w'),
                'fan_rpm': data.get('fan_rpm'),
                'reject_rate': data.get('reject_rate'),
                'pool_url': data.get('pool_url'),
            })
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to write raw telemetry: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_live(site_id: Optional[int] = None, miner_id: Optional[str] = None, 
                 online_only: bool = False, limit: int = 1000) -> List[Dict]:
        """Get current miner status from live layer
        
        Returns standardized format with metadata.
        """
        conditions = []
        params = {'limit': limit}
        
        if site_id:
            conditions.append("site_id = :site_id")
            params['site_id'] = site_id
        if miner_id:
            conditions.append("miner_id = :miner_id")
            params['miner_id'] = miner_id
        if online_only:
            conditions.append("online = true")
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        sql = text(f"""
            SELECT 
                miner_id, site_id, online, last_seen,
                hashrate_ghs, hashrate_5s_ghs, hashrate_expected_ghs,
                temperature_avg, temperature_max, temperature_min,
                fan_speeds, frequency_avg,
                accepted_shares, rejected_shares, hardware_errors,
                uptime_seconds, power_consumption, efficiency,
                pool_url, worker_name, model, firmware_version,
                error_message, boards_healthy, boards_total,
                pool_latency_ms, overall_health, updated_at
            FROM miner_telemetry_live
            {where_clause}
            ORDER BY updated_at DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = db.session.execute(sql, params)
        rows = result.fetchall()
        
        miners = []
        for row in rows:
            hashrate_ths = (row.hashrate_ghs or 0) / 1000  # Convert GH/s to TH/s
            reject_rate = 0
            if row.accepted_shares and (row.accepted_shares + (row.rejected_shares or 0)) > 0:
                reject_rate = (row.rejected_shares or 0) / (row.accepted_shares + (row.rejected_shares or 0))
            
            miners.append({
                'miner_id': row.miner_id,
                'site_id': row.site_id,
                'online': row.online,
                'last_seen': row.last_seen.isoformat() if row.last_seen else None,
                'hashrate': {
                    'value': round(hashrate_ths, 2),
                    'unit': 'TH/s',
                    'source': '5min_avg',
                    'instant_ths': round((row.hashrate_5s_ghs or 0) / 1000, 2),
                    'expected_ths': round((row.hashrate_expected_ghs or 0) / 1000, 2),
                },
                'temperature': {
                    'avg': row.temperature_avg,
                    'max': row.temperature_max,
                    'min': row.temperature_min,
                    'unit': 'C',
                },
                'power': {
                    'value': row.power_consumption,
                    'unit': 'W',
                },
                'efficiency': {
                    'value': row.efficiency,
                    'unit': 'J/TH',
                },
                'shares': {
                    'accepted': row.accepted_shares,
                    'rejected': row.rejected_shares,
                    'reject_rate': round(reject_rate, 4),
                },
                'uptime_seconds': row.uptime_seconds,
                'pool': {
                    'url': row.pool_url,
                    'worker': row.worker_name,
                    'latency_ms': row.pool_latency_ms,
                },
                'hardware': {
                    'model': row.model,
                    'firmware': row.firmware_version,
                    'boards_healthy': row.boards_healthy,
                    'boards_total': row.boards_total,
                    'errors': row.hardware_errors,
                },
                'health': row.overall_health,
                'error_message': row.error_message,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            })
        
        return miners
    
    @staticmethod
    def get_history(site_id: int, start: datetime, end: datetime,
                    miner_id: Optional[str] = None,
                    resolution: str = '5min') -> Dict:
        """Get historical telemetry data
        
        Args:
            site_id: Site ID
            start: Start time
            end: End time
            miner_id: Optional miner filter
            resolution: '5min', 'hourly', 'daily'
        
        Returns standardized format with metadata.
        """
        duration = end - start
        
        if resolution == 'daily' or duration.days > 60:
            table = 'telemetry_daily'
            time_col = 'day'
            source = 'telemetry_daily'
        elif resolution == 'hourly':
            table = 'telemetry_history_5min'
            time_col = 'bucket_ts'
            source = 'telemetry_history_5min (hourly aggregated)'
        else:
            table = 'telemetry_history_5min'
            time_col = 'bucket_ts'
            source = 'telemetry_history_5min'
        
        conditions = [f"{time_col} >= :start", f"{time_col} <= :end", "site_id = :site_id"]
        params = {'start': start, 'end': end, 'site_id': site_id}
        
        if miner_id:
            conditions.append("miner_id = :miner_id")
            params['miner_id'] = miner_id
        
        where_clause = ' AND '.join(conditions)
        
        if resolution == 'hourly' and table == 'telemetry_history_5min':
            sql = text(f"""
                SELECT 
                    miner_id,
                    date_trunc('hour', bucket_ts) AS ts,
                    AVG(avg_hashrate_ths) AS hashrate_ths,
                    MAX(max_hashrate_ths) AS max_hashrate_ths,
                    AVG(avg_temp_c) AS temp_c,
                    MAX(max_temp_c) AS max_temp_c,
                    AVG(avg_power_w) AS power_w,
                    AVG(online_ratio) AS online_ratio,
                    SUM(samples) AS samples
                FROM {table}
                WHERE {where_clause}
                GROUP BY miner_id, date_trunc('hour', bucket_ts)
                ORDER BY miner_id, ts
            """)
        else:
            hashrate_col = 'avg_hashrate_ths'
            temp_col = 'avg_temp_c'
            power_col = 'avg_power_w' if table == 'telemetry_history_5min' else 'avg_power_w'
            
            sql = text(f"""
                SELECT 
                    miner_id,
                    {time_col} AS ts,
                    {hashrate_col} AS hashrate_ths,
                    max_hashrate_ths,
                    min_hashrate_ths,
                    {temp_col} AS temp_c,
                    max_temp_c,
                    {power_col} AS power_w,
                    online_ratio,
                    samples
                FROM {table}
                WHERE {where_clause}
                ORDER BY miner_id, {time_col}
            """)
        
        result = db.session.execute(sql, params)
        rows = result.fetchall()
        
        series_map = {}
        for row in rows:
            mid = row.miner_id
            if mid not in series_map:
                series_map[mid] = []
            
            series_map[mid].append({
                'ts': row.ts.isoformat() if hasattr(row.ts, 'isoformat') else str(row.ts),
                'hashrate_ths': round(row.hashrate_ths or 0, 2),
                'max_hashrate_ths': round(row.max_hashrate_ths or 0, 2) if hasattr(row, 'max_hashrate_ths') else None,
                'min_hashrate_ths': round(row.min_hashrate_ths or 0, 2) if hasattr(row, 'min_hashrate_ths') else None,
                'temp_c': round(row.temp_c or 0, 1),
                'max_temp_c': round(row.max_temp_c or 0, 1) if hasattr(row, 'max_temp_c') else None,
                'power_w': round(row.power_w or 0, 0),
                'online_ratio': round(row.online_ratio or 0, 3),
                'samples': row.samples if hasattr(row, 'samples') else None,
            })
        
        return {
            'series': [{'miner_id': mid, 'data': data} for mid, data in series_map.items()],
            '_meta': {
                'source': source,
                'resolution': resolution,
                'start': start.isoformat(),
                'end': end.isoformat(),
                'site_id': site_id,
            }
        }
    
    @staticmethod
    def get_site_summary(site_id: int) -> Dict:
        """Get site-level summary from live data"""
        sql = text("""
            SELECT 
                COUNT(*) AS total_miners,
                COUNT(CASE WHEN online = true THEN 1 END) AS online_miners,
                SUM(hashrate_ghs) / 1000 AS total_hashrate_ths,
                AVG(temperature_avg) AS avg_temperature,
                MAX(temperature_max) AS max_temperature,
                SUM(power_consumption) AS total_power_w,
                AVG(efficiency) AS avg_efficiency,
                SUM(accepted_shares) AS total_accepted,
                SUM(rejected_shares) AS total_rejected
            FROM miner_telemetry_live
            WHERE site_id = :site_id
        """)
        
        result = db.session.execute(sql, {'site_id': site_id})
        row = result.fetchone()
        
        if not row:
            return {'error': 'No data found'}
        
        total_shares = (row.total_accepted or 0) + (row.total_rejected or 0)
        reject_rate = (row.total_rejected or 0) / total_shares if total_shares > 0 else 0
        
        return {
            'site_id': site_id,
            'miners': {
                'total': row.total_miners or 0,
                'online': row.online_miners or 0,
                'offline': (row.total_miners or 0) - (row.online_miners or 0),
                'online_rate': round((row.online_miners or 0) / (row.total_miners or 1), 3),
            },
            'hashrate': {
                'total_ths': round(row.total_hashrate_ths or 0, 2),
                'unit': 'TH/s',
            },
            'temperature': {
                'avg': round(row.avg_temperature or 0, 1),
                'max': round(row.max_temperature or 0, 1),
                'unit': 'C',
            },
            'power': {
                'total_w': round(row.total_power_w or 0, 0),
                'total_kw': round((row.total_power_w or 0) / 1000, 2),
                'unit': 'W',
            },
            'efficiency': {
                'avg': round(row.avg_efficiency or 0, 1),
                'unit': 'J/TH',
            },
            'shares': {
                'accepted': row.total_accepted or 0,
                'rejected': row.total_rejected or 0,
                'reject_rate': round(reject_rate, 4),
            },
            '_meta': {
                'source': 'miner_telemetry_live',
                'updated_at': datetime.utcnow().isoformat(),
            }
        }
    
    @staticmethod
    def update_live_from_raw():
        """Background job: Update live table from raw data
        
        Should be called every minute by APScheduler.
        """
        try:
            sql = text("""
                WITH latest_raw AS (
                    SELECT DISTINCT ON (miner_id)
                        site_id, miner_id, ts, status, hashrate_ths, 
                        temperature_c, power_w, fan_rpm, reject_rate, pool_url
                    FROM telemetry_raw_24h
                    WHERE ts >= NOW() - INTERVAL '5 minutes'
                    ORDER BY miner_id, ts DESC
                )
                INSERT INTO miner_telemetry_live (
                    miner_id, site_id, online, last_seen, 
                    hashrate_ghs, temperature_avg, power_consumption, updated_at
                )
                SELECT 
                    miner_id, site_id, 
                    (status = 'online') AS online,
                    ts AS last_seen,
                    hashrate_ths * 1000 AS hashrate_ghs,
                    temperature_c AS temperature_avg,
                    power_w AS power_consumption,
                    NOW() AS updated_at
                FROM latest_raw
                ON CONFLICT (miner_id) DO UPDATE SET
                    online = EXCLUDED.online,
                    last_seen = EXCLUDED.last_seen,
                    hashrate_ghs = EXCLUDED.hashrate_ghs,
                    temperature_avg = EXCLUDED.temperature_avg,
                    power_consumption = EXCLUDED.power_consumption,
                    updated_at = EXCLUDED.updated_at
            """)
            
            db.session.execute(sql)
            db.session.commit()
            logger.debug("Updated live telemetry from raw data")
            return True
        except Exception as e:
            logger.error(f"Failed to update live telemetry: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def aggregate_to_5min():
        """Background job: Aggregate raw data to 5-min buckets
        
        Should be called every 5 minutes by APScheduler.
        """
        try:
            sql = text("""
                INSERT INTO telemetry_history_5min (
                    bucket_ts, site_id, miner_id,
                    avg_hashrate_ths, max_hashrate_ths, min_hashrate_ths,
                    avg_temp_c, max_temp_c, avg_power_w, avg_fan_rpm,
                    online_ratio, samples, created_at
                )
                SELECT 
                    date_trunc('minute', ts) - (EXTRACT(MINUTE FROM ts)::INT % 5) * INTERVAL '1 minute' AS bucket_ts,
                    site_id, miner_id,
                    AVG(hashrate_ths) AS avg_hashrate_ths,
                    MAX(hashrate_ths) AS max_hashrate_ths,
                    MIN(hashrate_ths) AS min_hashrate_ths,
                    AVG(temperature_c) AS avg_temp_c,
                    MAX(temperature_c) AS max_temp_c,
                    AVG(power_w) AS avg_power_w,
                    AVG(fan_rpm) AS avg_fan_rpm,
                    COUNT(CASE WHEN status = 'online' THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) AS online_ratio,
                    COUNT(*) AS samples,
                    NOW() AS created_at
                FROM telemetry_raw_24h
                WHERE ts >= NOW() - INTERVAL '10 minutes'
                  AND ts < NOW() - INTERVAL '5 minutes'
                GROUP BY bucket_ts, site_id, miner_id
                ON CONFLICT (bucket_ts, site_id, miner_id) DO NOTHING
            """)
            
            db.session.execute(sql)
            db.session.commit()
            logger.debug("Aggregated telemetry to 5-min buckets")
            return True
        except Exception as e:
            logger.error(f"Failed to aggregate telemetry: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def cleanup_old_data():
        """Background job: Clean up old data based on retention policy
        
        Should be called daily by APScheduler.
        """
        try:
            db.session.execute(text(
                "DELETE FROM telemetry_raw_24h WHERE ts < NOW() - INTERVAL '24 hours'"
            ))
            
            db.session.execute(text(
                "DELETE FROM telemetry_history_5min WHERE bucket_ts < NOW() - INTERVAL '90 days'"
            ))
            
            db.session.execute(text(
                "DELETE FROM telemetry_daily WHERE day < NOW() - INTERVAL '365 days'"
            ))
            
            db.session.commit()
            logger.info("Cleaned up old telemetry data")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup telemetry: {e}")
            db.session.rollback()
            return False


telemetry_service = TelemetryService()
