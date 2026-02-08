"""
Mode Inference Service — KMeans Clustering for Miner Operational Modes
矿机运行模式推理服务 — 基于KMeans聚类的生态/正常/性能模式推断

This service clusters miners within the same group (site + model + firmware) to infer whether
each is running in eco/normal/perf mode based on their operational characteristics.

Algorithm:
1. Group miners by (site_id, model, firmware) — peer groups
2. For each group with >= 5 miners, run KMeans(n_clusters=min(3, n_samples//3))
3. Features: hashrate_ratio (primary), temp_max, efficiency (if available)
4. After clustering, sort clusters by mean hashrate_ratio ascending → label as eco/normal/perf
5. If only 2 clusters: label eco/perf (skip normal)
6. If only 1 cluster or < 5 miners: all get mode='unknown'
7. Confidence = 1 - (distance_to_center / max_distance_in_cluster), clamped to [0.3, 1.0]
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from app import db

logger = logging.getLogger(__name__)


class ModeInferenceService:
    """KMeans clustering service for inferring miner operational modes."""
    
    @staticmethod
    def infer_modes(feature_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Infer operational modes for miners based on feature data.
        
        Args:
            feature_records: List of dicts with keys:
                - miner_id (str)
                - site_id (int)
                - model (str or None)
                - firmware (str or None)
                - hashrate_ratio (float or None)
                - temp_max (float or None)
                - efficiency (float or None)
        
        Returns:
            Dict of {miner_id: {
                'inferred_mode': str (eco/normal/perf/unknown),
                'mode_confidence': float (0.3-1.0),
                'group_key': str
            }}
        
        Side effect: Updates miner_baseline_state table with inferred_mode and mode_confidence
        """
        if not feature_records:
            logger.debug("No feature records provided for mode inference")
            return {}
        
        try:
            # Step 1: Group miners by (site_id, model, firmware)
            peer_groups = ModeInferenceService._group_by_peer_group(feature_records)
            logger.debug(f"Created {len(peer_groups)} peer groups")
            
            # Step 2: Process each group
            results = {}
            updates_for_db = []
            
            for group_key, group_records in peer_groups.items():
                # Skip groups too small
                if len(group_records) < 5:
                    logger.debug(f"Group {group_key} has {len(group_records)} miners < 5, assigning unknown")
                    for record in group_records:
                        miner_id = record['miner_id']
                        results[miner_id] = {
                            'inferred_mode': 'unknown',
                            'mode_confidence': 0.0,
                            'group_key': group_key,
                        }
                        updates_for_db.append((miner_id, 'unknown', 0.0))
                    continue
                
                # Cluster the group
                try:
                    clustered_records = ModeInferenceService._cluster_group(
                        group_records, 
                        features_to_use=['hashrate_ratio', 'temp_max', 'efficiency']
                    )
                    
                    for record in clustered_records:
                        miner_id = record['miner_id']
                        results[miner_id] = {
                            'inferred_mode': record['inferred_mode'],
                            'mode_confidence': record['mode_confidence'],
                            'group_key': group_key,
                        }
                        updates_for_db.append((miner_id, record['inferred_mode'], record['mode_confidence']))
                    
                except Exception as e:
                    logger.error(f"Error clustering group {group_key}: {e}")
                    # Fallback to unknown mode for this group
                    for record in group_records:
                        miner_id = record['miner_id']
                        results[miner_id] = {
                            'inferred_mode': 'unknown',
                            'mode_confidence': 0.0,
                            'group_key': group_key,
                        }
                        updates_for_db.append((miner_id, 'unknown', 0.0))
            
            # Step 3: Bulk update database
            if updates_for_db:
                ModeInferenceService._bulk_update_database(updates_for_db)
            
            logger.info(f"Mode inference completed: {len(results)} miners processed")
            return results
        
        except Exception as e:
            logger.error(f"Fatal error in infer_modes: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def _group_by_peer_group(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group records by (site_id, model, firmware).
        
        Args:
            records: List of feature records
        
        Returns:
            Dict of {group_key: [records]}
        """
        groups = {}
        
        for record in records:
            group_key = ModeInferenceService._build_group_key(
                site_id=record.get('site_id'),
                model=record.get('model'),
                firmware=record.get('firmware')
            )
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(record)
        
        return groups
    
    @staticmethod
    def _cluster_group(records: List[Dict[str, Any]], features_to_use: List[str]) -> List[Dict[str, Any]]:
        """Run KMeans clustering on a single peer group.
        
        Args:
            records: List of records in the group (length >= 5)
            features_to_use: List of feature names to use for clustering
        
        Returns:
            List of records with 'inferred_mode' and 'mode_confidence' added
        """
        if len(records) < 5:
            raise ValueError(f"Group too small: {len(records)} < 5")
        
        # Step 1: Extract feature matrix and handle NaN values
        feature_matrix = []
        valid_indices = []
        
        for i, record in enumerate(records):
            features = []
            has_valid_feature = False
            
            for feat_name in features_to_use:
                value = record.get(feat_name)
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    features.append(0.0)  # Default for missing feature
                else:
                    features.append(float(value))
                    has_valid_feature = True
            
            # Only include records with at least one valid feature
            if has_valid_feature:
                feature_matrix.append(features)
                valid_indices.append(i)
        
        if not feature_matrix:
            logger.warning("No valid features in group, assigning all to unknown")
            for record in records:
                record['inferred_mode'] = 'unknown'
                record['mode_confidence'] = 0.0
            return records
        
        feature_matrix = np.array(feature_matrix)
        
        # Step 2: Standardize features
        scaler = StandardScaler()
        try:
            scaled_features = scaler.fit_transform(feature_matrix)
        except Exception as e:
            logger.warning(f"StandardScaler failed: {e}, using raw features")
            scaled_features = feature_matrix
        
        # Step 3: Determine number of clusters
        n_samples = len(scaled_features)
        n_clusters = min(3, max(1, n_samples // 3))
        
        if n_clusters == 1:
            # Only 1 cluster: all miners are in the same mode
            logger.debug(f"Only 1 cluster for group with {n_samples} miners")
            for record in records:
                record['inferred_mode'] = 'unknown'
                record['mode_confidence'] = 0.0
            return records
        
        # Step 4: Run KMeans
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(scaled_features)
            distances = kmeans.transform(scaled_features)
        except Exception as e:
            logger.error(f"KMeans fit failed: {e}")
            for record in records:
                record['inferred_mode'] = 'unknown'
                record['mode_confidence'] = 0.0
            return records
        
        # Step 5: Label clusters by mean hashrate_ratio (ascending)
        # hashrate_ratio is features_to_use[0]
        cluster_hashrate_means = {}
        
        for cluster_idx in range(n_clusters):
            cluster_mask = labels == cluster_idx
            if np.any(cluster_mask):
                cluster_hashrates = feature_matrix[cluster_mask, 0]  # First feature is hashrate_ratio
                mean_hashrate = np.mean(cluster_hashrates[~np.isnan(cluster_hashrates)])
                if not np.isnan(mean_hashrate):
                    cluster_hashrate_means[cluster_idx] = mean_hashrate
                else:
                    cluster_hashrate_means[cluster_idx] = float('inf')  # Default to high value
        
        # Sort clusters by mean hashrate_ratio
        sorted_clusters = sorted(cluster_hashrate_means.items(), key=lambda x: x[1])
        
        # Assign mode labels
        mode_labels = {}
        if len(sorted_clusters) == 3:
            mode_labels[sorted_clusters[0][0]] = 'eco'
            mode_labels[sorted_clusters[1][0]] = 'normal'
            mode_labels[sorted_clusters[2][0]] = 'perf'
        elif len(sorted_clusters) == 2:
            mode_labels[sorted_clusters[0][0]] = 'eco'
            mode_labels[sorted_clusters[1][0]] = 'perf'
        else:
            # Single cluster (shouldn't reach here due to earlier check, but for safety)
            for idx in range(n_clusters):
                mode_labels[idx] = 'unknown'
        
        # Step 6: Assign modes and confidence to records
        for array_idx, record_idx in enumerate(valid_indices):
            cluster_idx = labels[array_idx]
            inferred_mode = mode_labels.get(cluster_idx, 'unknown')
            
            # Confidence calculation: 1 - (distance_to_center / max_distance_in_cluster)
            min_distance = distances[array_idx, cluster_idx]
            
            # Find max distance in this cluster
            cluster_mask = labels == cluster_idx
            cluster_distances = distances[cluster_mask, cluster_idx]
            max_distance = np.max(cluster_distances) if len(cluster_distances) > 0 else 1.0
            
            if max_distance > 0:
                confidence = 1.0 - (min_distance / max_distance)
            else:
                confidence = 1.0
            
            # Clamp confidence to [0.3, 1.0]
            confidence = max(0.3, min(1.0, confidence))
            
            records[record_idx]['inferred_mode'] = inferred_mode
            records[record_idx]['mode_confidence'] = float(round(confidence, 3))
        
        # Records not in valid_indices get 'unknown' mode
        invalid_indices = set(range(len(records))) - set(valid_indices)
        for record_idx in invalid_indices:
            records[record_idx]['inferred_mode'] = 'unknown'
            records[record_idx]['mode_confidence'] = 0.0
        
        return records
    
    @staticmethod
    def _build_group_key(site_id: Optional[int], model: Optional[str], firmware: Optional[str]) -> str:
        """Build a unique group key from site_id, model, and firmware.
        
        Args:
            site_id: Site ID
            model: Miner model
            firmware: Firmware version
        
        Returns:
            Formatted group key string
        """
        site_str = str(site_id) if site_id is not None else 'unknown'
        model_str = model if model else 'unknown'
        firmware_str = firmware if firmware else 'unknown'
        
        return f"{site_str}:{model_str}:{firmware_str}"
    
    @staticmethod
    def _bulk_update_database(updates: List[tuple]) -> bool:
        """Bulk update miner_baseline_state table with inferred modes and confidences.
        
        Args:
            updates: List of (miner_id, inferred_mode, mode_confidence) tuples
        
        Returns:
            True if successful, False otherwise
        """
        if not updates:
            return True
        
        try:
            # Build a temporary table with updates
            update_values = []
            for miner_id, inferred_mode, mode_confidence in updates:
                update_values.append({
                    'miner_id': miner_id,
                    'inferred_mode': inferred_mode,
                    'mode_confidence': mode_confidence,
                    'updated_at': datetime.utcnow(),
                })
            
            # Perform batch update using multiple UPDATE statements
            # For each unique miner_id across all metrics
            miner_ids = list(set(u[0] for u in updates))
            
            sql = text("""
                UPDATE miner_baseline_state
                SET inferred_mode = :inferred_mode,
                    mode_confidence = :mode_confidence,
                    updated_at = :updated_at
                WHERE miner_id = :miner_id
            """)
            
            for miner_id, inferred_mode, mode_confidence in updates:
                db.session.execute(sql, {
                    'miner_id': miner_id,
                    'inferred_mode': inferred_mode,
                    'mode_confidence': mode_confidence,
                    'updated_at': datetime.utcnow(),
                })
            
            db.session.commit()
            logger.info(f"Updated {len(updates)} miner mode inferences in database")
            return True
        
        except Exception as e:
            logger.error(f"Failed to bulk update database: {e}", exc_info=True)
            db.session.rollback()
            return False


# Module-level convenience functions

def infer_modes(feature_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Infer modes for a batch of miners.
    
    Args:
        feature_records: List of feature records
    
    Returns:
        Dict of {miner_id: mode inference results}
    """
    return ModeInferenceService.infer_modes(feature_records)
