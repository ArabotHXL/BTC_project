"""
Weakly-Supervised Predictive Maintenance Service with XGBoost

Builds weak labels from operational signals and trains an XGBoost model
to predict p_fail_24h (probability of failure within 24 hours).

Key Components:
- WeakLabelBuilder: Constructs binary labels from P0/P1 events and features from baselines
- ModelRegistry: Manages model persistence (joblib) and metadata (database)
- WeakSupervisor: Orchestrates training and prediction workflows
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
from sqlalchemy import text

from app import db

logger = logging.getLogger(__name__)

# Feature names for training
FEATURE_NAMES = [
    'hashrate_ratio_ewma', 'hashrate_ratio_var',
    'boards_ratio_ewma', 'boards_ratio_var',
    'temp_max_ewma', 'temp_max_var',
    'efficiency_ewma', 'efficiency_var',
    'sample_count', 'mode_encoded'
]

# Mode encoding mapping
MODE_ENCODING = {
    'eco': 0,
    'normal': 1,
    'perf': 2,
    'unknown': -1,
    None: -1
}


class WeakLabelBuilder:
    """Build weakly-supervised labels from operational signals."""

    def build_labels(self, lookback_days: int = 30) -> pd.DataFrame:
        """
        Build feature+label dataset from historical data.

        CRITICAL: No time leakage!
        - Features come from current miner_baseline_state
        - Labels come from problem_events in the lookback window
        - For each miner: if it had any P0/P1 event in the last 24h → label=1, else label=0

        Args:
            lookback_days: Number of days to look back for labels

        Returns:
            DataFrame with columns:
            miner_id, site_id, hashrate_ratio_ewma, hashrate_ratio_var,
            boards_ratio_ewma, boards_ratio_var, temp_max_ewma, temp_max_var,
            efficiency_ewma, efficiency_var, mode_encoded, sample_count, event_in_24h
        """
        try:
            logger.info(f"Building weak labels with {lookback_days} day lookback")

            # Fetch current baseline state as features
            features_df = self._build_features()
            if features_df.empty:
                logger.warning("No baseline features available")
                return pd.DataFrame()

            # Fetch P0/P1 events in lookback window as labels
            labels_df = self._build_labels_from_events(lookback_days)

            # Merge on miner_id
            if labels_df.empty:
                # No events in lookback window - all miners get label=0
                features_df['event_in_24h'] = 0
            else:
                # Left join to preserve all miners from features
                merged = features_df.merge(
                    labels_df[['miner_id', 'event_in_24h']],
                    on='miner_id',
                    how='left'
                )
                merged['event_in_24h'] = merged['event_in_24h'].fillna(0).astype(int)
                features_df = merged

            # Reorder columns to match expected schema
            column_order = ['miner_id', 'site_id'] + FEATURE_NAMES + ['event_in_24h']
            features_df = features_df[[col for col in column_order if col in features_df.columns]]

            positive_count = int(features_df['event_in_24h'].sum()) if 'event_in_24h' in features_df.columns else 0
            logger.info(f"Built labels: {len(features_df)} miners, {positive_count} positive")
            return features_df

        except Exception as e:
            logger.error(f"Error building labels: {e}")
            return pd.DataFrame()

    def _build_features(self) -> pd.DataFrame:
        """
        Fetch current baseline state and pivot into features.

        Returns:
            DataFrame with columns:
            miner_id, site_id, hashrate_ratio_ewma, hashrate_ratio_var, ..., sample_count, mode_encoded
        """
        try:
            # Fetch latest baseline state for each miner, pivoted by metric_name
            sql = text("""
                SELECT
                    miner_id,
                    site_id,
                    metric_name,
                    ewma_value,
                    ewma_variance,
                    sample_count,
                    inferred_mode
                FROM miner_baseline_state
                ORDER BY updated_at DESC
            """)

            rows = db.session.execute(sql).fetchall()

            if not rows:
                logger.warning("No baseline data available")
                return pd.DataFrame()

            # Convert to list of dicts
            data = []
            for row in rows:
                data.append({
                    'miner_id': row[0],
                    'site_id': row[1],
                    'metric_name': row[2],
                    'ewma_value': float(row[3]) if row[3] is not None else 0.0,
                    'ewma_variance': float(row[4]) if row[4] is not None else 0.0,
                    'sample_count': int(row[5]) if row[5] is not None else 0,
                    'inferred_mode': row[6],
                })

            df = pd.DataFrame(data)

            # Get the latest sample_count and inferred_mode per miner
            # (these are the same across all metrics for a miner)
            miner_meta = df.groupby('miner_id').agg({
                'site_id': 'first',
                'sample_count': 'first',
                'inferred_mode': 'first'
            }).reset_index()

            # Pivot metrics into columns
            pivot_df = df.pivot_table(
                index='miner_id',
                columns='metric_name',
                values=['ewma_value', 'ewma_variance'],
                aggfunc='first'
            )

            # Flatten column names (e.g., ('ewma_value', 'hashrate_ratio') -> ewma_value_hashrate_ratio)
            pivot_df.columns = [f"{value}_{metric}" for value, metric in pivot_df.columns]
            pivot_df = pivot_df.reset_index()

            # Merge with miner metadata
            result = pivot_df.merge(miner_meta, on='miner_id', how='left')

            # Encode mode
            result['mode_encoded'] = result['inferred_mode'].map(MODE_ENCODING).fillna(-1).astype(int)

            # Ensure all features exist (fill missing with 0)
            for feat in FEATURE_NAMES:
                if feat not in result.columns and feat != 'mode_encoded':
                    result[feat] = 0.0

            # Select only the columns we need
            columns_to_keep = ['miner_id', 'site_id'] + FEATURE_NAMES
            result = result[[col for col in columns_to_keep if col in result.columns]]

            logger.debug(f"Built features: {len(result)} miners")
            return result

        except Exception as e:
            logger.error(f"Error building features: {e}")
            return pd.DataFrame()

    def _build_labels_from_events(self, lookback_days: int) -> pd.DataFrame:
        """
        Fetch P0/P1 events in the last lookback_days and mark miners with events.

        Args:
            lookback_days: Number of days to look back

        Returns:
            DataFrame with columns: miner_id, event_in_24h
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=lookback_days)

            sql = text("""
                SELECT DISTINCT
                    miner_id,
                    1 as event_in_24h
                FROM problem_events
                WHERE severity IN ('P0', 'P1')
                  AND last_seen_ts >= :cutoff_time
            """)

            rows = db.session.execute(sql, {'cutoff_time': cutoff_time}).fetchall()

            if not rows:
                logger.info(f"No P0/P1 events in last {lookback_days} days")
                return pd.DataFrame()

            labels = pd.DataFrame([{'miner_id': row[0], 'event_in_24h': row[1]} for row in rows])
            logger.debug(f"Found {len(labels)} miners with P0/P1 events")
            return labels

        except Exception as e:
            logger.error(f"Error building labels from events: {e}")
            return pd.DataFrame()


class ModelRegistry:
    """Manage ML model persistence and metadata."""

    MODEL_DIR = '/tmp/ml_models'

    def __init__(self):
        """Initialize model registry and create model directory."""
        os.makedirs(self.MODEL_DIR, exist_ok=True)
        logger.debug(f"Model directory initialized: {self.MODEL_DIR}")

    def save_model(
        self,
        model: xgb.XGBClassifier,
        model_name: str,
        version: str,
        metrics: Dict[str, Any],
        feature_names: List[str]
    ) -> bool:
        """
        Save model to disk and register in ml_model_registry table.

        Args:
            model: Trained XGBClassifier
            model_name: Name of the model (e.g., 'p_fail_24h')
            version: Version string
            metrics: Dict of training metrics
            feature_names: List of feature names used

        Returns:
            True if successful, False otherwise
        """
        try:
            # Save model to disk
            model_path = os.path.join(self.MODEL_DIR, f"{model_name}_{version}.joblib")
            joblib.dump(model, model_path)
            logger.info(f"Saved model to {model_path}")

            # Register in database
            # First, deactivate other versions
            deactivate_sql = text("""
                UPDATE ml_model_registry
                SET is_active = FALSE
                WHERE model_name = :model_name
            """)
            db.session.execute(deactivate_sql, {'model_name': model_name})

            # Insert new version
            insert_sql = text("""
                INSERT INTO ml_model_registry (
                    model_name, version, model_type, metrics_json,
                    model_path, is_active, trained_at, sample_count,
                    feature_names, created_at
                )
                VALUES (
                    :model_name, :version, :model_type, :metrics_json,
                    :model_path, :is_active, :trained_at, :sample_count,
                    :feature_names, :created_at
                )
            """)

            db.session.execute(insert_sql, {
                'model_name': model_name,
                'version': version,
                'model_type': 'xgboost',
                'metrics_json': json.dumps(metrics),
                'model_path': model_path,
                'is_active': True,
                'trained_at': datetime.utcnow(),
                'sample_count': metrics.get('sample_count', 0),
                'feature_names': json.dumps(feature_names),
                'created_at': datetime.utcnow(),
            })

            db.session.commit()
            logger.info(f"Registered model {model_name} v{version} in database")
            return True

        except Exception as e:
            logger.error(f"Error saving model: {e}")
            db.session.rollback()
            return False

    def load_active_model(self, model_name: str) -> Tuple[Optional[xgb.XGBClassifier], Optional[Dict[str, Any]]]:
        """
        Load the active model for a given model_name.

        Args:
            model_name: Name of the model to load

        Returns:
            Tuple of (model, metadata) or (None, None) if not found
        """
        try:
            # Fetch active model metadata from database
            sql = text("""
                SELECT model_path, version, metrics_json, feature_names
                FROM ml_model_registry
                WHERE model_name = :model_name AND is_active = TRUE
                LIMIT 1
            """)

            row = db.session.execute(sql, {'model_name': model_name}).fetchone()

            if not row:
                logger.info(f"No active model found for {model_name}")
                return None, None

            model_path, version, metrics_json, feature_names_json = row

            # Load model from disk
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return None, None

            model = joblib.load(model_path)
            metadata = {
                'version': version,
                'metrics': json.loads(metrics_json) if metrics_json else {},
                'feature_names': json.loads(feature_names_json) if feature_names_json else [],
            }

            logger.info(f"Loaded active model {model_name} v{version}")
            return model, metadata

        except Exception as e:
            logger.error(f"Error loading active model: {e}")
            return None, None

    def get_active_version(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for active model version.

        Args:
            model_name: Name of the model

        Returns:
            Dict with version, metrics, feature_names or None if not found
        """
        try:
            sql = text("""
                SELECT version, metrics_json, feature_names, trained_at
                FROM ml_model_registry
                WHERE model_name = :model_name AND is_active = TRUE
                LIMIT 1
            """)

            row = db.session.execute(sql, {'model_name': model_name}).fetchone()

            if not row:
                return None

            return {
                'version': row[0],
                'metrics': json.loads(row[1]) if row[1] else {},
                'feature_names': json.loads(row[2]) if row[2] else [],
                'trained_at': row[3].isoformat() if row[3] else None,
            }

        except Exception as e:
            logger.error(f"Error getting active version: {e}")
            return None


class WeakSupervisor:
    """Weakly-supervised predictive maintenance with XGBoost."""

    def __init__(self):
        """Initialize the weak supervisor."""
        self.label_builder = WeakLabelBuilder()
        self.registry = ModelRegistry()
        self.model_name = 'p_fail_24h'
        self.model: Optional[xgb.XGBClassifier] = None
        self.model_version: Optional[str] = None
        self.feature_names: List[str] = FEATURE_NAMES.copy()

    def train(self) -> Dict[str, Any]:
        """
        Train XGBoost model on weak labels.

        - Build labels from historical events and baseline features
        - If < 50 samples or < 5 positive labels, skip training (not enough data)
        - Train XGBClassifier with configured hyperparameters
        - Save model via registry
        - Return training metrics

        Returns:
            Dict with training metrics and status
        """
        try:
            logger.info("Starting model training")

            # Build labels
            df = self.label_builder.build_labels(lookback_days=30)

            if df.empty:
                logger.warning("No data available for training")
                return {
                    'status': 'insufficient_data',
                    'message': 'No baseline data available',
                    'sample_count': 0,
                    'positive_count': 0,
                }

            # Check minimum data requirements
            sample_count = len(df)
            positive_count = int(df['event_in_24h'].sum())

            if sample_count < 50 or positive_count < 5:
                logger.info(
                    f"Skipping training: {sample_count} samples, "
                    f"{positive_count} positive (need >=50 samples, >=5 positive)"
                )
                return {
                    'status': 'insufficient_data',
                    'message': f"Need >=50 samples and >=5 positive labels (got {sample_count}, {positive_count})",
                    'sample_count': sample_count,
                    'positive_count': positive_count,
                }

            # Prepare features and labels
            X = df[self.feature_names].copy()
            y = df['event_in_24h'].copy()

            # Handle missing values
            X = X.fillna(0)

            # Calculate scale_pos_weight to handle class imbalance
            neg_count = (y == 0).sum()
            pos_count = (y == 1).sum()
            scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0

            logger.info(f"Training data: {sample_count} samples, {pos_count} positive, scale_pos_weight={scale_pos_weight:.2f}")

            # Train XGBoost model
            params = {
                'n_estimators': 100,
                'max_depth': 4,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'scale_pos_weight': scale_pos_weight,
                'eval_metric': 'auc',
                'random_state': 42,
                'use_label_encoder': False,
            }

            self.model = xgb.XGBClassifier(**params)
            self.model.fit(X, y)

            logger.info("Model training completed")

            # Calculate training metrics
            try:
                from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

                y_pred_proba = self.model.predict_proba(X)[:, 1]
                y_pred = self.model.predict(X)

                auc = roc_auc_score(y, y_pred_proba)
                precision = precision_score(y, y_pred)
                recall = recall_score(y, y_pred)
                f1 = f1_score(y, y_pred)

                metrics = {
                    'sample_count': sample_count,
                    'positive_count': positive_count,
                    'negative_count': int(neg_count),
                    'auc': float(auc),
                    'precision': float(precision),
                    'recall': float(recall),
                    'f1': float(f1),
                    'scale_pos_weight': float(scale_pos_weight),
                }
            except Exception as e:
                logger.warning(f"Error calculating metrics: {e}")
                metrics = {
                    'sample_count': sample_count,
                    'positive_count': positive_count,
                    'negative_count': int(neg_count),
                    'auc': 0.0,
                    'precision': 0.0,
                    'recall': 0.0,
                    'f1': 0.0,
                    'scale_pos_weight': float(scale_pos_weight),
                }

            # Generate version string
            version = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            self.model_version = version

            # Save model
            success = self.registry.save_model(
                self.model,
                self.model_name,
                version,
                metrics,
                self.feature_names
            )

            if not success:
                logger.error("Failed to save model")
                return {
                    'status': 'save_failed',
                    'message': 'Failed to save model to registry',
                    **metrics,
                }

            logger.info(f"Model saved successfully: {self.model_name} v{version}")
            return {
                'status': 'success',
                'message': f"Model trained and saved: {version}",
                **metrics,
            }

        except Exception as e:
            logger.error(f"Error during training: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'sample_count': 0,
                'positive_count': 0,
            }

    def predict(self, features: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Predict p_fail_24h for a batch of miners.

        Input: list of feature dicts with keys matching training features
        Output: {miner_id: {'p_fail_24h': float, 'top_features': list, 'model_version': str}}

        If no active model exists, return p_fail_24h=0.0 for all (graceful degradation)

        Args:
            features: List of feature dicts, each with 'miner_id' and feature columns

        Returns:
            Dict of {miner_id: prediction_result}
        """
        try:
            if not features:
                return {}

            # Load active model if not already loaded
            if self.model is None:
                self.model, metadata = self.registry.load_active_model(self.model_name)
                if metadata:
                    self.model_version = metadata.get('version', 'unknown')
                    self.feature_names = metadata.get('feature_names', FEATURE_NAMES.copy())

            # Graceful degradation: no model available
            if self.model is None:
                logger.warning("No active model available, returning p_fail_24h=0.0 for all")
                results = {}
                for feature_dict in features:
                    miner_id = feature_dict.get('miner_id', 'unknown')
                    results[miner_id] = {
                        'p_fail_24h': 0.0,
                        'top_features': [],
                        'model_version': 'none',
                    }
                return results

            # Convert feature dicts to DataFrame
            df = pd.DataFrame(features)

            # Extract miner_ids
            miner_ids = df['miner_id'].tolist()

            # Select feature columns and fill missing values
            X = df[self.feature_names].copy()
            X = X.fillna(0)

            # Predict probabilities
            y_pred_proba = self.model.predict_proba(X)[:, 1]

            # Get feature importances
            feature_importances = dict(zip(self.feature_names, self.model.feature_importances_))
            top_3_features = sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)[:3]
            top_features = [{'name': name, 'importance': float(imp)} for name, imp in top_3_features]

            # Build results
            results = {}
            for miner_id, p_fail in zip(miner_ids, y_pred_proba):
                results[miner_id] = {
                    'p_fail_24h': float(p_fail),
                    'top_features': top_features,
                    'model_version': self.model_version or 'unknown',
                }

            logger.debug(f"Predicted for {len(results)} miners")
            return results

        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            # Graceful degradation: return 0.0 for all
            results = {}
            for feature_dict in features:
                miner_id = feature_dict.get('miner_id', 'unknown')
                results[miner_id] = {
                    'p_fail_24h': 0.0,
                    'top_features': [],
                    'model_version': 'error',
                }
            return results

    def build_ml_json(self, miner_id: str, prediction_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the ml_json object for storage in problem_events.

        Args:
            miner_id: Miner identifier
            prediction_result: Dict from predict() with p_fail_24h, top_features, model_version

        Returns:
            Dict with ml_json structure
        """
        return {
            'p_fail_24h': prediction_result.get('p_fail_24h', 0.0),
            'top_features': prediction_result.get('top_features', []),
            'model_version': prediction_result.get('model_version', 'none'),
            'predicted_at': datetime.utcnow().isoformat(),
        }
