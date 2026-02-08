"""
Fleet-level peer group baseline service.

Computes fleet-level statistics for peer groups of miners to detect outliers
relative to their peers (not just relative to their own history).

Peer groups are defined by: site_id:model:firmware[:inferred_mode]
Statistics: median, MAD (median absolute deviation), p10, p25, p75, p90, robust z-scores
"""

import logging
import time
import threading
import numpy as np
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Consistency constant for normal distribution (MAD to sigma conversion)
MAD_CONSISTENCY_CONSTANT = 1.4826

# Cache TTL in seconds
CACHE_TTL_SECONDS = 300


class FleetBaselineService:
    """
    Fleet-level peer group baseline service.
    
    Computes fleet-level statistics for peer groups of miners to detect outliers
    relative to their peers (not just relative to their own history).
    
    Features:
    - Peer groups defined by: site_id:model:firmware[:inferred_mode]
    - In-memory cache with 300-second TTL
    - Thread-safe cache operations
    - Robust z-score calculation using MAD
    - Percentile-based metrics
    """
    
    def __init__(self):
        """Initialize the service with empty cache and lock."""
        self._cache = {}
        self._cache_lock = threading.Lock()
        logger.info("FleetBaselineService initialized")
    
    def _get_group_key(self, site_id: int, model: str, firmware: str, 
                       inferred_mode: Optional[str] = None) -> str:
        """
        Build peer group key.
        
        If inferred_mode is 'unknown' or missing, omit it from the key.
        Otherwise: site_id:model:firmware:inferred_mode
        
        Args:
            site_id: Site ID
            model: Miner model
            firmware: Firmware version
            inferred_mode: Operating mode (normal, low-power, etc.)
            
        Returns:
            Peer group key string
        """
        if inferred_mode and inferred_mode != 'unknown':
            return f"{site_id}:{model}:{firmware}:{inferred_mode}"
        return f"{site_id}:{model}:{firmware}"
    
    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """
        Check if cache entry is still valid (within TTL).
        
        Args:
            cache_entry: Cache entry dict
            
        Returns:
            True if entry is within TTL, False otherwise
        """
        computed_at = cache_entry.get('computed_at', 0)
        elapsed = time.time() - computed_at
        return elapsed < CACHE_TTL_SECONDS
    
    def _compute_mad(self, values: np.ndarray) -> float:
        """
        Compute Median Absolute Deviation.
        
        MAD = median(|x_i - median(x)|)
        
        Args:
            values: Array of numeric values
            
        Returns:
            MAD value
        """
        if len(values) == 0:
            return 0.0
        median = np.median(values)
        deviations = np.abs(values - median)
        mad = np.median(deviations)
        return float(mad)
    
    def _compute_percentiles(self, values: np.ndarray) -> Dict[str, float]:
        """
        Compute percentiles (p10, p25, p50/median, p75, p90).
        
        Args:
            values: Array of numeric values
            
        Returns:
            Dict with percentile values
        """
        if len(values) == 0:
            return {}
        
        return {
            'p10': float(np.percentile(values, 10)),
            'p25': float(np.percentile(values, 25)),
            'median': float(np.percentile(values, 50)),
            'p75': float(np.percentile(values, 75)),
            'p90': float(np.percentile(values, 90)),
        }
    
    def compute_peer_metrics(self, group_key: str, feature_records: List[dict]) -> dict:
        """
        Compute peer group statistics for all metrics.
        
        Computes: median, MAD, p10, p25, p75, p90, count for each metric.
        Stores results in cache with TTL.
        
        Args:
            group_key: Peer group identifier (site:model:firmware[:mode])
            feature_records: List of miner feature dicts
            
        Returns:
            {metric_name: {median, mad, p10, p25, p75, p90, count}}
        """
        metrics_to_compute = ['hashrate_ratio', 'boards_ratio', 'temp_max', 'efficiency']
        result = {}
        values_by_metric = {}
        
        for metric_name in metrics_to_compute:
            # Extract valid values for this metric
            values = []
            for record in feature_records:
                value = record.get(metric_name)
                if value is not None and isinstance(value, (int, float)) and not np.isnan(value):
                    values.append(float(value))
            
            if not values:
                logger.debug(f"No valid values for metric {metric_name} in group {group_key}")
                continue
            
            values_array = np.array(values)
            values_by_metric[metric_name] = values
            median = float(np.median(values_array))
            mad = self._compute_mad(values_array)
            percentiles = self._compute_percentiles(values_array)
            
            result[metric_name] = {
                'median': median,
                'mad': mad,
                'p10': percentiles.get('p10', 0.0),
                'p25': percentiles.get('p25', 0.0),
                'p75': percentiles.get('p75', 0.0),
                'p90': percentiles.get('p90', 0.0),
                'count': len(values),
            }
        
        # Cache the result with raw values for percentile rank calculation
        cache_entry = {
            'metrics': result,
            'values': values_by_metric,
            'computed_at': time.time(),
        }
        
        with self._cache_lock:
            self._cache[group_key] = cache_entry
        
        total_values = sum(m['count'] for m in result.values())
        logger.info(f"Computed peer metrics for group {group_key}: "
                   f"{len(result)} metrics, {total_values} total values")
        
        return result
    
    def get_peer_metrics(self, group_key: str) -> Optional[dict]:
        """
        Get cached peer metrics if still valid.
        
        Returns the metrics dict without the raw values or cache metadata.
        
        Args:
            group_key: Peer group identifier
            
        Returns:
            Metrics dict or None if not cached or expired
        """
        with self._cache_lock:
            cache_entry = self._cache.get(group_key)
        
        if cache_entry is None:
            return None
        
        if not self._is_cache_valid(cache_entry):
            with self._cache_lock:
                if group_key in self._cache:
                    del self._cache[group_key]
            return None
        
        return cache_entry['metrics']
    
    def compute_robust_z(self, value: float, group_key: str, metric_name: str) -> float:
        """
        Compute robust z-score for a single value.
        
        robust_z = (value - median) / (mad * 1.4826)
        Returns 0 if no cached data or mad=0.
        
        Args:
            value: The miner's metric value
            group_key: Peer group identifier
            metric_name: Metric name (e.g., 'hashrate_ratio')
            
        Returns:
            Robust z-score
        """
        metrics = self.get_peer_metrics(group_key)
        
        if metrics is None or metric_name not in metrics:
            return 0.0
        
        metric_stats = metrics[metric_name]
        median = metric_stats.get('median', 0.0)
        mad = metric_stats.get('mad', 0.0)
        
        if mad == 0:
            return 0.0
        
        z_score = (value - median) / (mad * MAD_CONSISTENCY_CONSTANT)
        return float(z_score)
    
    def _compute_percentile_rank(self, value: float, values: List[float]) -> float:
        """
        Compute percentile rank: percentage of group members with value <= this value.
        
        Args:
            value: The miner's value
            values: All values in the group for this metric
            
        Returns:
            Percentile rank (0-100)
        """
        if not values:
            return 0.0
        
        count_lte = sum(1 for v in values if v <= value)
        percentile = (count_lte / len(values)) * 100
        return float(percentile)
    
    def build_peer_metrics_json(self, miner_features: dict, group_key: str) -> dict:
        """
        Build peer metrics JSON for storage in problem_events.
        
        Builds a JSON structure with the miner's metrics relative to peer group stats.
        
        Args:
            miner_features: Single miner's feature dict with metric values
            group_key: Peer group identifier
            
        Returns:
            {
                "group_key": "...",
                "group_size": 200,
                "metrics": {
                    "hashrate_ratio": {
                        "value": 0.85,
                        "group_median": 0.95,
                        "robust_z": -2.1,
                        "percentile_rank": 8.5,
                        "group_p10": 0.88,
                        "group_p90": 0.98
                    }
                }
            }
        """
        with self._cache_lock:
            cache_entry = self._cache.get(group_key)
        
        if cache_entry is None or not self._is_cache_valid(cache_entry):
            logger.warning(f"No valid cached metrics for group {group_key}")
            return {
                'group_key': group_key,
                'group_size': 0,
                'metrics': {},
            }
        
        metrics = cache_entry['metrics']
        values_by_metric = cache_entry.get('values', {})
        
        # Build the output
        output_metrics = {}
        
        for metric_name, metric_stats in metrics.items():
            value = miner_features.get(metric_name)
            
            if value is None or (isinstance(value, float) and np.isnan(value)):
                continue
            
            value = float(value)
            robust_z = self.compute_robust_z(value, group_key, metric_name)
            
            # Calculate percentile rank using cached values
            percentile_rank = 0.0
            if metric_name in values_by_metric:
                percentile_rank = self._compute_percentile_rank(value, values_by_metric[metric_name])
            
            output_metrics[metric_name] = {
                'value': value,
                'group_median': metric_stats.get('median', 0.0),
                'robust_z': round(robust_z, 2),
                'percentile_rank': round(percentile_rank, 1),
                'group_p10': metric_stats.get('p10', 0.0),
                'group_p90': metric_stats.get('p90', 0.0),
            }
        
        # Get group size from first metric (all metrics in same group have same count)
        group_size = 0
        if metrics:
            first_metric = next(iter(metrics.values()))
            group_size = first_metric.get('count', 0)
        
        return {
            'group_key': group_key,
            'group_size': group_size,
            'metrics': output_metrics,
        }
    
    def invalidate_cache(self, group_key: Optional[str] = None) -> None:
        """
        Invalidate cache for a specific group or all groups.
        
        Args:
            group_key: Specific group to invalidate, or None to clear all
        """
        with self._cache_lock:
            if group_key is None:
                self._cache.clear()
                logger.info("Cleared all cached peer metrics")
            else:
                if group_key in self._cache:
                    del self._cache[group_key]
                    logger.debug(f"Invalidated cache for group {group_key}")
    
    def compute_all_groups(self, all_features: List[dict]) -> dict:
        """
        Compute stats for all groups in the feature set.
        
        Groups records by (site_id, model, firmware, inferred_mode) and
        computes statistics for each group, caching results.
        
        Args:
            all_features: List of miner feature dicts with keys:
                         miner_id, site_id, model, firmware, inferred_mode,
                         hashrate_ratio, boards_ratio, temp_max, efficiency
        
        Returns:
            {group_key: {metrics dict}}
        """
        if not all_features:
            logger.debug("No features provided to compute_all_groups")
            return {}
        
        # Group records by peer group
        groups = {}
        
        for record in all_features:
            site_id = record.get('site_id')
            model = record.get('model')
            firmware = record.get('firmware')
            inferred_mode = record.get('inferred_mode')
            
            if not all([site_id, model, firmware]):
                logger.warning(f"Skipping record with missing site_id, model, or firmware: {record}")
                continue
            
            group_key = self._get_group_key(site_id, model, firmware, inferred_mode)
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(record)
        
        # Compute metrics for each group
        result = {}
        
        for group_key, records in groups.items():
            metrics = self.compute_peer_metrics(group_key, records)
            result[group_key] = metrics
        
        logger.info(f"Computed metrics for {len(result)} peer groups, "
                   f"total {len(all_features)} miner records")
        
        return result


# Global service instance
fleet_baseline_service = FleetBaselineService()
