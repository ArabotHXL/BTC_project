"""
Per-Miner EWMA Baseline Service
增量式指数加权移动平均(EWMA)基线服务

This service maintains per-miner baselines using EWMA algorithm for:
- hashrate_ratio: current hashrate / expected hashrate
- boards_ratio: healthy boards / total boards
- temp_max: maximum temperature
- efficiency: power consumption / hashrate

Key Design:
- Incremental updates: NEVER scans full history, uses only latest live data
- Single transaction per batch for consistency
- Graceful degradation: skips metrics if fields unavailable
- Raw SQL with INSERT ON CONFLICT for performance
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from math import sqrt
from sqlalchemy import text

from app import db

logger = logging.getLogger(__name__)

# EWMA configuration
EWMA_SPAN = 12  # 1 hour at 5min intervals
EWMA_ALPHA = 2 / (EWMA_SPAN + 1)  # ≈ 0.1538


class BaselineService:
    """Per-miner EWMA incremental baseline service"""
    
    @staticmethod
    def extract_features(live_record: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Extract raw features from a live telemetry record.
        
        Args:
            live_record: Dict from TelemetryService.get_live() with structure:
                {
                    'miner_id': str,
                    'site_id': int,
                    'hashrate': {'value': float, 'expected_ths': float},
                    'temperature': {'avg': float, 'max': float},
                    'hardware': {'boards_healthy': int, 'boards_total': int, ...},
                    'power': float or None,
                    ...
                }
        
        Returns:
            Dict with keys: hashrate_ratio, boards_ratio, temp_max, efficiency
            Values are float or None if unavailable.
        """
        features = {
            'hashrate_ratio': None,
            'boards_ratio': None,
            'temp_max': None,
            'efficiency': None,
        }
        
        try:
            # Extract hashrate_ratio: hashrate.value / hashrate.expected_ths
            if 'hashrate' in live_record and isinstance(live_record['hashrate'], dict):
                hashrate_value = live_record['hashrate'].get('value')
                hashrate_expected = live_record['hashrate'].get('expected_ths')
                if hashrate_value is not None and hashrate_expected is not None:
                    if hashrate_expected > 0:
                        features['hashrate_ratio'] = float(hashrate_value) / float(hashrate_expected)
                    # else: gracefully skip if expected is 0 or negative
            
            # Extract boards_ratio: boards_healthy / boards_total
            if 'hardware' in live_record and isinstance(live_record['hardware'], dict):
                boards_healthy = live_record['hardware'].get('boards_healthy')
                boards_total = live_record['hardware'].get('boards_total')
                if boards_healthy is not None and boards_total is not None:
                    if int(boards_total) > 0:
                        features['boards_ratio'] = float(boards_healthy) / float(boards_total)
                    # else: gracefully skip if total is 0
            
            # Extract temp_max: temperature.max
            if 'temperature' in live_record and isinstance(live_record['temperature'], dict):
                temp_max = live_record['temperature'].get('max')
                if temp_max is not None:
                    features['temp_max'] = float(temp_max)
            
            # Extract efficiency: power / hashrate_value
            # Skip if power doesn't exist or hashrate is missing/zero
            power = live_record.get('power')
            if power is not None:
                hashrate_value = None
                if 'hashrate' in live_record and isinstance(live_record['hashrate'], dict):
                    hashrate_value = live_record['hashrate'].get('value')
                
                if hashrate_value is not None and float(hashrate_value) > 0:
                    features['efficiency'] = float(power) / float(hashrate_value)
                # else: gracefully skip if hashrate missing or zero
        
        except (TypeError, ValueError, KeyError) as e:
            logger.warning(f"Error extracting features from live_record: {e}")
        
        return features
    
    @staticmethod
    def update_baseline(miner_id: str, site_id: int, features: Dict[str, Optional[float]]) -> Dict[str, Dict[str, Any]]:
        """Update baselines for a miner using EWMA algorithm.
        
        For each metric in features, performs an upsert (INSERT ON CONFLICT UPDATE)
        with EWMA calculation.
        
        Args:
            miner_id: Miner identifier
            site_id: Site identifier
            features: Dict of {metric_name: raw_value} where raw_value is float or None
        
        Returns:
            Dict of {metric_name: {'ewma': float, 'residual': float, 'z_score': float, 'sample_count': int}}
            Skips metrics with None values.
        """
        results = {}
        
        # Process each metric
        for metric_name, raw_value in features.items():
            if raw_value is None:
                continue
            
            try:
                # Fetch current baseline state
                current_state = BaselineService._get_baseline_state(miner_id, metric_name)
                
                if current_state is None:
                    # First sample: initialize
                    ewma_value = raw_value
                    ewma_variance = 0.0
                    sample_count = 1
                    residual = 0.0
                else:
                    # EWMA update
                    sample_count = current_state['sample_count'] + 1
                    ewma_old = current_state['ewma_value']
                    variance_old = current_state['ewma_variance']
                    
                    # ewma_new = alpha * raw + (1 - alpha) * ewma_old
                    ewma_value = EWMA_ALPHA * raw_value + (1 - EWMA_ALPHA) * ewma_old
                    
                    # residual = raw - ewma_new
                    residual = raw_value - ewma_value
                    
                    # variance_new = alpha * (raw - ewma_new)^2 + (1 - alpha) * variance_old
                    ewma_variance = EWMA_ALPHA * (residual ** 2) + (1 - EWMA_ALPHA) * variance_old
                
                # Compute z_score
                z_score = 0.0
                if ewma_variance > 0:
                    z_score = residual / sqrt(ewma_variance)
                
                # Upsert into database
                BaselineService._upsert_baseline(
                    miner_id=miner_id,
                    site_id=site_id,
                    metric_name=metric_name,
                    raw_value=raw_value,
                    ewma_value=ewma_value,
                    ewma_variance=ewma_variance,
                    residual=residual,
                    sample_count=sample_count
                )
                
                results[metric_name] = {
                    'ewma': round(ewma_value, 6),
                    'residual': round(residual, 6),
                    'z_score': round(z_score, 6),
                    'sample_count': sample_count,
                }
                
            except Exception as e:
                logger.error(f"Error updating baseline for {miner_id}/{metric_name}: {e}")
        
        return results
    
    @staticmethod
    def get_baselines(miner_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch all baseline states for a miner.
        
        Args:
            miner_id: Miner identifier
        
        Returns:
            Dict of {metric_name: {ewma, variance, sample_count, updated_at, residual, mode, mode_confidence}}
        """
        result = {}
        
        try:
            sql = text("""
                SELECT 
                    metric_name, ewma_value, ewma_variance, sample_count,
                    last_raw_value, last_residual, inferred_mode, mode_confidence,
                    updated_at
                FROM miner_baseline_state
                WHERE miner_id = :miner_id
                ORDER BY updated_at DESC
            """)
            
            rows = db.session.execute(sql, {'miner_id': miner_id})
            
            for row in rows:
                metric_name = row.metric_name
                result[metric_name] = {
                    'ewma': float(row.ewma_value) if row.ewma_value is not None else None,
                    'variance': float(row.ewma_variance) if row.ewma_variance is not None else None,
                    'sample_count': row.sample_count,
                    'last_raw_value': float(row.last_raw_value) if row.last_raw_value is not None else None,
                    'last_residual': float(row.last_residual) if row.last_residual is not None else None,
                    'inferred_mode': row.inferred_mode,
                    'mode_confidence': float(row.mode_confidence) if row.mode_confidence is not None else None,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                }
            
            logger.debug(f"Retrieved {len(result)} baseline metrics for miner {miner_id}")
        
        except Exception as e:
            logger.error(f"Error fetching baselines for {miner_id}: {e}")
        
        return result
    
    @staticmethod
    def bulk_update(live_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Process a batch of live records in a single transaction.
        
        Args:
            live_records: List of live records from TelemetryService.get_live()
        
        Returns:
            Dict of {miner_id: {metric_name: baseline_info}}
        """
        results = {}
        
        if not live_records:
            return results
        
        try:
            # Start transaction
            for live_record in live_records:
                try:
                    miner_id = live_record.get('miner_id')
                    site_id = live_record.get('site_id')
                    
                    if not miner_id or not site_id:
                        logger.warning(f"Skipping record missing miner_id or site_id: {live_record}")
                        continue
                    
                    # Extract features
                    features = BaselineService.extract_features(live_record)
                    
                    # Update baselines
                    baseline_results = BaselineService.update_baseline(miner_id, site_id, features)
                    
                    if baseline_results:
                        results[miner_id] = baseline_results
                    
                except Exception as e:
                    logger.error(f"Error processing record for miner {live_record.get('miner_id')}: {e}")
            
            # Commit transaction
            db.session.commit()
            logger.info(f"Bulk update completed: {len(results)} miners processed")
        
        except Exception as e:
            logger.error(f"Bulk update transaction failed: {e}")
            db.session.rollback()
        
        return results
    
    # ========================================================================
    # Private helper methods
    # ========================================================================
    
    @staticmethod
    def _get_baseline_state(miner_id: str, metric_name: str) -> Optional[Dict[str, Any]]:
        """Fetch current baseline state for a metric.
        
        Args:
            miner_id: Miner identifier
            metric_name: Name of metric (hashrate_ratio, boards_ratio, temp_max, efficiency)
        
        Returns:
            Dict with ewma_value, ewma_variance, sample_count or None if not found
        """
        try:
            sql = text("""
                SELECT ewma_value, ewma_variance, sample_count
                FROM miner_baseline_state
                WHERE miner_id = :miner_id AND metric_name = :metric_name
                LIMIT 1
            """)
            
            row = db.session.execute(
                sql,
                {'miner_id': miner_id, 'metric_name': metric_name}
            ).fetchone()
            
            if row:
                return {
                    'ewma_value': float(row.ewma_value),
                    'ewma_variance': float(row.ewma_variance),
                    'sample_count': int(row.sample_count),
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Error fetching baseline state for {miner_id}/{metric_name}: {e}")
            return None
    
    @staticmethod
    def _upsert_baseline(
        miner_id: str,
        site_id: int,
        metric_name: str,
        raw_value: float,
        ewma_value: float,
        ewma_variance: float,
        residual: float,
        sample_count: int
    ) -> bool:
        """Upsert baseline state using INSERT ON CONFLICT UPDATE.
        
        Uses unique index on (miner_id, metric_name) for conflict detection.
        
        Args:
            miner_id: Miner identifier
            site_id: Site identifier
            metric_name: Metric name
            raw_value: Raw measurement value
            ewma_value: Updated EWMA value
            ewma_variance: Updated EWMA variance
            residual: Residual (raw - ewma)
            sample_count: Updated sample count
        
        Returns:
            True if successful, False otherwise
        """
        try:
            sql = text("""
                INSERT INTO miner_baseline_state (
                    miner_id, site_id, metric_name,
                    ewma_value, ewma_variance, sample_count,
                    last_raw_value, last_residual,
                    updated_at
                )
                VALUES (
                    :miner_id, :site_id, :metric_name,
                    :ewma_value, :ewma_variance, :sample_count,
                    :raw_value, :residual,
                    :updated_at
                )
                ON CONFLICT (miner_id, metric_name)
                DO UPDATE SET
                    ewma_value = EXCLUDED.ewma_value,
                    ewma_variance = EXCLUDED.ewma_variance,
                    sample_count = EXCLUDED.sample_count,
                    last_raw_value = EXCLUDED.last_raw_value,
                    last_residual = EXCLUDED.last_residual,
                    updated_at = EXCLUDED.updated_at
            """)
            
            db.session.execute(
                sql,
                {
                    'miner_id': miner_id,
                    'site_id': site_id,
                    'metric_name': metric_name,
                    'ewma_value': ewma_value,
                    'ewma_variance': ewma_variance,
                    'sample_count': sample_count,
                    'raw_value': raw_value,
                    'residual': residual,
                    'updated_at': datetime.utcnow(),
                }
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error upserting baseline for {miner_id}/{metric_name}: {e}")
            return False


# Export singleton methods for module-level usage
def extract_features(live_record: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Module-level function to extract features."""
    return BaselineService.extract_features(live_record)


def update_baseline(miner_id: str, site_id: int, features: Dict[str, Optional[float]]) -> Dict[str, Dict[str, Any]]:
    """Module-level function to update baseline."""
    return BaselineService.update_baseline(miner_id, site_id, features)


def get_baselines(miner_id: str) -> Dict[str, Dict[str, Any]]:
    """Module-level function to get baselines."""
    return BaselineService.get_baselines(miner_id)


def bulk_update(live_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Module-level function to bulk update baselines."""
    return BaselineService.bulk_update(live_records)
