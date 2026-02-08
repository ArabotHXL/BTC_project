"""
Health Rules Engine & FeatureStore Batch Job
健康规则引擎与特征存储批处理任务

Part 1: Rules taxonomy (hard rules P0/P1, soft rules P2/P3)
Part 2: HealthRulesEngine — evaluates rules and builds evidence
Part 3: FeatureStoreJob — 5-minute batch pipeline orchestrating
        feature extraction, baseline updates, mode inference,
        fleet baselines, rule evaluation, and event processing
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from services.baseline_service import BaselineService
from services.mode_inference_service import ModeInferenceService
from services.fleet_baseline_service import FleetBaselineService
from services.event_engine import EventEngine

logger = logging.getLogger(__name__)

HARD_RULES = [
    {
        'code': 'overheat_crit',
        'severity': 'P0',
        'condition': lambda f: f.get('temp_max', 0) >= 85,
    },
    {
        'code': 'offline',
        'severity': 'P0',
        'condition': lambda f: f.get('is_online') is False,
    },
    {
        'code': 'hashrate_zero',
        'severity': 'P1',
        'condition': lambda f: f.get('hashrate_ratio', 1) <= 0.01 and f.get('is_online') is True,
    },
    {
        'code': 'boards_dead',
        'severity': 'P1',
        'condition': lambda f: f.get('boards_ratio', 1) <= 0.5,
    },
    {
        'code': 'fan_zero',
        'severity': 'P1',
        'condition': lambda f: f.get('fan_speed_min', 1) == 0 and f.get('is_online') is True,
    },
    {
        'code': 'overheat_warn',
        'severity': 'P1',
        'condition': lambda f: 75 <= f.get('temp_max', 0) < 85,
    },
]

SOFT_RULES = [
    {
        'code': 'hashrate_degradation',
        'severity': 'P2',
        'condition': lambda f, b: (
            b.get('hashrate_ratio', {}).get('z_score', 0) < -2.0
            and b.get('hashrate_ratio', {}).get('sample_count', 0) >= 6
        ),
    },
    {
        'code': 'efficiency_degradation',
        'severity': 'P2',
        'condition': lambda f, b: (
            b.get('efficiency', {}).get('z_score', 0) > 2.0
            and b.get('efficiency', {}).get('sample_count', 0) >= 6
        ),
    },
    {
        'code': 'temp_anomaly',
        'severity': 'P2',
        'condition': lambda f, b: b.get('temp_max', {}).get('z_score', 0) > 2.5,
    },
    {
        'code': 'fleet_outlier',
        'severity': 'P3',
        'condition': lambda f, b: abs(f.get('fleet_z_hashrate', 0)) > 3.0,
    },
    {
        'code': 'boards_degrading',
        'severity': 'P3',
        'condition': lambda f, b: (
            b.get('boards_ratio', {}).get('residual', 0) < -0.1
            and b.get('boards_ratio', {}).get('sample_count', 0) >= 6
        ),
    },
]

ALL_ISSUE_CODES = [r['code'] for r in HARD_RULES] + [r['code'] for r in SOFT_RULES]


class HealthRulesEngine:
    """Evaluates hard and soft health rules against miner features and baselines."""

    def evaluate_hard_rules(self, features: dict) -> List[dict]:
        triggered = []
        for rule in HARD_RULES:
            try:
                if rule['condition'](features):
                    evidence = self.build_evidence(rule['code'], features)
                    triggered.append({
                        'code': rule['code'],
                        'severity': rule['severity'],
                        'evidence': evidence,
                    })
            except Exception as e:
                logger.warning(f"Error evaluating hard rule {rule['code']}: {e}")
        return triggered

    def evaluate_soft_rules(self, features: dict, baselines: dict) -> List[dict]:
        triggered = []
        for rule in SOFT_RULES:
            try:
                if rule['condition'](features, baselines):
                    evidence = self.build_evidence(rule['code'], features, baselines)
                    triggered.append({
                        'code': rule['code'],
                        'severity': rule['severity'],
                        'evidence': evidence,
                    })
            except Exception as e:
                logger.warning(f"Error evaluating soft rule {rule['code']}: {e}")
        return triggered

    def evaluate_all(self, features: dict, baselines: dict) -> List[dict]:
        hard = self.evaluate_hard_rules(features)
        soft = self.evaluate_soft_rules(features, baselines)
        return hard + soft

    def build_evidence(self, rule_code: str, features: dict, baselines: dict = None) -> dict:
        evidence: Dict[str, Any] = {
            'rule_code': rule_code,
            'evaluated_at': datetime.utcnow().isoformat(),
        }

        if rule_code == 'overheat_crit':
            evidence['temp_max'] = features.get('temp_max')
            evidence['threshold'] = 85
            evidence['description'] = 'Critical overheating: temp_max >= 85°C'

        elif rule_code == 'offline':
            evidence['is_online'] = features.get('is_online')
            evidence['description'] = 'Miner is offline'

        elif rule_code == 'hashrate_zero':
            evidence['hashrate_ratio'] = features.get('hashrate_ratio')
            evidence['is_online'] = features.get('is_online')
            evidence['threshold'] = 0.01
            evidence['description'] = 'Hashrate near zero while online'

        elif rule_code == 'boards_dead':
            evidence['boards_ratio'] = features.get('boards_ratio')
            evidence['threshold'] = 0.5
            evidence['description'] = 'More than half of boards are dead'

        elif rule_code == 'fan_zero':
            evidence['fan_speed_min'] = features.get('fan_speed_min')
            evidence['is_online'] = features.get('is_online')
            evidence['description'] = 'Fan speed is zero while online'

        elif rule_code == 'overheat_warn':
            evidence['temp_max'] = features.get('temp_max')
            evidence['threshold_low'] = 75
            evidence['threshold_high'] = 85
            evidence['description'] = 'Warning: temp_max between 75°C and 85°C'

        elif rule_code == 'hashrate_degradation' and baselines:
            bl = baselines.get('hashrate_ratio', {})
            evidence['hashrate_ratio'] = features.get('hashrate_ratio')
            evidence['ewma'] = bl.get('ewma')
            evidence['z_score'] = bl.get('z_score')
            evidence['residual'] = bl.get('residual')
            evidence['sample_count'] = bl.get('sample_count')
            evidence['threshold_z'] = -2.0
            evidence['description'] = 'Hashrate degradation detected via EWMA z-score'

        elif rule_code == 'efficiency_degradation' and baselines:
            bl = baselines.get('efficiency', {})
            evidence['efficiency'] = features.get('efficiency')
            evidence['ewma'] = bl.get('ewma')
            evidence['z_score'] = bl.get('z_score')
            evidence['residual'] = bl.get('residual')
            evidence['sample_count'] = bl.get('sample_count')
            evidence['threshold_z'] = 2.0
            evidence['description'] = 'Efficiency degradation detected via EWMA z-score'

        elif rule_code == 'temp_anomaly' and baselines:
            bl = baselines.get('temp_max', {})
            evidence['temp_max'] = features.get('temp_max')
            evidence['ewma'] = bl.get('ewma')
            evidence['z_score'] = bl.get('z_score')
            evidence['residual'] = bl.get('residual')
            evidence['threshold_z'] = 2.5
            evidence['description'] = 'Temperature anomaly detected via EWMA z-score'

        elif rule_code == 'fleet_outlier':
            evidence['fleet_z_hashrate'] = features.get('fleet_z_hashrate')
            evidence['hashrate_ratio'] = features.get('hashrate_ratio')
            evidence['threshold_z'] = 3.0
            evidence['description'] = 'Fleet-level outlier: robust z-score > 3.0'

        elif rule_code == 'boards_degrading' and baselines:
            bl = baselines.get('boards_ratio', {})
            evidence['boards_ratio'] = features.get('boards_ratio')
            evidence['ewma'] = bl.get('ewma')
            evidence['residual'] = bl.get('residual')
            evidence['z_score'] = bl.get('z_score')
            evidence['sample_count'] = bl.get('sample_count')
            evidence['threshold_residual'] = -0.1
            evidence['description'] = 'Boards degradation trend detected'

        else:
            evidence['description'] = f'Rule {rule_code} triggered'

        return evidence


class FeatureStoreJob:
    """5-minute batch processing pipeline.

    Orchestrates: feature extraction → baseline update → mode inference →
    fleet baselines → rule evaluation → event processing.
    """

    def __init__(self, app):
        self.app = app
        self.baseline_service = BaselineService()
        self.mode_service = ModeInferenceService()
        self.fleet_service = FleetBaselineService()
        self.rules_engine = HealthRulesEngine()
        self.event_engine = EventEngine()

    def run(self):
        """Main entry point called by APScheduler every 5 minutes."""
        try:
            with self.app.app_context():
                return self._run_pipeline()
        except Exception as e:
            logger.error(f"FeatureStoreJob fatal error: {e}", exc_info=True)
            return {'error': str(e)}

    def _run_pipeline(self):
        start_time = datetime.utcnow()
        logger.info("FeatureStoreJob started")

        live_records = self._fetch_live_data()
        if not live_records:
            logger.info("FeatureStoreJob: no live records, skipping")
            return {'skipped': True, 'reason': 'no_live_records'}

        logger.info(f"Step 1: Fetched {len(live_records)} live records")

        all_features = []
        for record in live_records:
            features = self.baseline_service.extract_features(record)
            features['miner_id'] = record.get('miner_id')
            features['site_id'] = record.get('site_id')
            features['model'] = record.get('hardware', {}).get('model')
            features['firmware'] = record.get('hardware', {}).get('firmware')
            features['is_online'] = record.get('online', False)

            fan_speed_min = self._extract_fan_speed_min(record)
            if fan_speed_min is not None:
                features['fan_speed_min'] = fan_speed_min

            all_features.append(features)

        logger.info(f"Step 2: Extracted features for {len(all_features)} miners")

        baselines_map = self.baseline_service.bulk_update(live_records)
        logger.info(f"Step 3: Updated baselines for {len(baselines_map)} miners")

        mode_results = self.mode_service.infer_modes(all_features)
        for f in all_features:
            mid = f['miner_id']
            if mid in mode_results:
                f['inferred_mode'] = mode_results[mid]['inferred_mode']
            else:
                f['inferred_mode'] = 'unknown'
        logger.info(f"Step 4: Inferred modes for {len(mode_results)} miners")

        fleet_metrics = self.fleet_service.compute_all_groups(all_features)
        for f in all_features:
            group_key = self._build_group_key(f)
            hr = f.get('hashrate_ratio')
            if hr is not None:
                z = self.fleet_service.compute_robust_z(hr, group_key, 'hashrate_ratio')
            else:
                z = 0.0
            f['fleet_z_hashrate'] = z
        logger.info(f"Step 5: Computed fleet baselines for {len(fleet_metrics)} groups")

        detections = []
        healthy = []
        for f in all_features:
            mid = f['miner_id']
            sid = f['site_id']
            miner_baselines = baselines_map.get(mid, {})

            issues = self.rules_engine.evaluate_all(f, miner_baselines)

            if issues:
                triggered_codes = set()
                for issue in issues:
                    triggered_codes.add(issue['code'])
                    group_key = self._build_group_key(f)
                    peer_json = self.fleet_service.build_peer_metrics_json(f, group_key)
                    detections.append({
                        'site_id': sid,
                        'miner_id': mid,
                        'issue_code': issue['code'],
                        'severity': issue['severity'],
                        'evidence': issue['evidence'],
                        'peer_metrics': peer_json,
                    })
                for code in ALL_ISSUE_CODES:
                    if code not in triggered_codes:
                        healthy.append({
                            'site_id': sid,
                            'miner_id': mid,
                            'issue_code': code,
                        })
            else:
                for code in ALL_ISSUE_CODES:
                    healthy.append({
                        'site_id': sid,
                        'miner_id': mid,
                        'issue_code': code,
                    })

        logger.info(
            f"Step 6: Generated {len(detections)} detections, "
            f"{len(healthy)} healthy signals"
        )

        result = self.event_engine.bulk_process(detections, healthy)
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"FeatureStore batch complete in {elapsed:.1f}s: {result}"
        )
        return result

    def _fetch_live_data(self) -> list:
        from services.telemetry_service import TelemetryService
        try:
            return TelemetryService.get_live()
        except Exception as e:
            logger.error(f"Failed to fetch live data: {e}", exc_info=True)
            return []

    def _build_group_key(self, features: dict) -> str:
        site = features.get('site_id', 0)
        model = features.get('model') or 'unknown'
        firmware = features.get('firmware') or 'unknown'
        mode = features.get('inferred_mode') or 'unknown'
        return f"{site}:{model}:{firmware}:{mode}"

    @staticmethod
    def _extract_fan_speed_min(record: dict) -> Optional[int]:
        try:
            fan_speeds = record.get('fan_speeds')
            if fan_speeds is None and 'hardware' in record:
                fan_speeds = record['hardware'].get('fan_speeds')
            if fan_speeds and isinstance(fan_speeds, (list, tuple)):
                numeric = [int(s) for s in fan_speeds if s is not None]
                if numeric:
                    return min(numeric)
        except (TypeError, ValueError):
            pass
        return None
