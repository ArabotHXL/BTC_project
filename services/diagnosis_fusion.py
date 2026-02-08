"""
Diagnosis Fusion Service - 诊断融合服务

Integrates fleet-level peer anomaly detection with ML failure prediction
and existing AI alert diagnosis.

Provides:
1. Peer hypothesis generation from fleet metrics
2. Unified Health Object for each miner
3. Enriched diagnosis with fleet/ML context

This is a stateless service - all data comes from parameters.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class DiagnosisFusion:
    """
    Fusion service integrating:
    - Peer outlier detection (from FleetBaselineService)
    - ML failure prediction (p_fail_24h from ML model)
    - Existing AI alert diagnosis (from AIAlertDiagnosisService)

    All methods are stateless; data flows from parameters to outputs.
    """

    def __init__(self):
        """Initialize stateless fusion service."""
        pass

    def create_peer_hypothesis(
        self,
        miner_id: str,
        peer_metrics_json: Optional[Dict[str, Any]],
        ml_json: Optional[Dict[str, Any]],
        baselines: Optional[Dict[str, Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """
        Create a peer_outlier_or_risk hypothesis from fleet and ML data.

        Args:
            miner_id: Miner identifier
            peer_metrics_json: Output from FleetBaselineService.build_peer_metrics_json()
                {
                    'group_key': str,
                    'group_size': int,
                    'metrics': {
                        'hashrate_ratio': {
                            'value': float,
                            'group_median': float,
                            'robust_z': float,
                            'percentile_rank': float,
                            'group_p10': float,
                            'group_p90': float,
                        },
                        ...
                    }
                }
            ml_json: ML prediction results
                {
                    'p_fail_24h': float,
                    'top_contributing_features': [{'feature': str, 'importance': float}, ...]
                }
            baselines: Miner's baseline state from BaselineService.get_baselines()

        Returns:
            Hypothesis dict matching RootCauseHypothesis structure, or None if no data.
            {
                'hypothesis_id': 'peer_outlier_risk',
                'cause': str,
                'cause_zh': str,
                'confidence': float,
                'risk_level': str,
                'evidence': [evidence dicts],
                'recommended_actions': [action dicts]
            }
        """
        if not peer_metrics_json and not ml_json:
            logger.debug(f"No peer or ML data for {miner_id}, skipping hypothesis")
            return None

        # Calculate confidence scores
        peer_confidence = self._calculate_peer_confidence(peer_metrics_json)
        ml_confidence = self._calculate_ml_confidence(ml_json)
        combined_confidence = max(peer_confidence, ml_confidence)

        if combined_confidence == 0.0:
            logger.debug(f"Zero confidence for {miner_id}, skipping hypothesis")
            return None

        # Build evidence list
        evidence = self._build_peer_evidence(peer_metrics_json, ml_json, baselines)

        # Determine risk level
        risk_level = self._determine_risk_level(peer_metrics_json, ml_json)

        # Build recommended actions
        recommended_actions = self._build_peer_actions(peer_metrics_json, ml_json)

        logger.info(
            f"Created peer hypothesis for {miner_id}: "
            f"confidence={combined_confidence:.3f}, risk_level={risk_level}, "
            f"evidence_items={len(evidence)}, actions={len(recommended_actions)}"
        )

        return {
            'hypothesis_id': 'peer_outlier_risk',
            'cause': 'Fleet-relative anomaly and/or elevated failure risk',
            'cause_zh': '相对于同组矿机异常，且/或故障风险升高',
            'confidence': round(combined_confidence, 3),
            'risk_level': risk_level,
            'evidence': evidence,
            'recommended_actions': recommended_actions,
        }

    def build_health_object(
        self,
        site_id: int,
        miner_id: str,
        issues: List[Dict[str, Any]],
        p_fail_24h: Optional[float],
        last_seen_ts: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build unified Health Object for a miner.

        Args:
            site_id: Site identifier
            miner_id: Miner identifier
            issues: List of issue dicts with keys:
                issue_code, severity, evidence, recommended_actions, confidence
            p_fail_24h: Predicted failure probability (0-1)
            last_seen_ts: ISO format timestamp of last miner contact

        Returns:
            Health Object dict:
            {
                'site_id': int,
                'miner_id': str,
                'health_state': 'P0'|'P1'|'P2'|'P3'|'OK',
                'issues': [issue dicts],
                'p_fail_24h': float,
                'last_seen_ts': str,
                'assessed_at': str
            }
        """
        # Determine worst health state from issues and ML prediction
        health_state = self._determine_health_state(issues, p_fail_24h)

        # ISO format timestamp
        now = datetime.utcnow().isoformat() + 'Z'

        health_object = {
            'site_id': site_id,
            'miner_id': miner_id,
            'health_state': health_state,
            'issues': issues,
            'p_fail_24h': p_fail_24h if p_fail_24h is not None else 0.0,
            'last_seen_ts': last_seen_ts or now,
            'assessed_at': now,
        }

        logger.info(
            f"Built health object for {miner_id}: "
            f"health_state={health_state}, issues={len(issues)}, "
            f"p_fail_24h={p_fail_24h}"
        )

        return health_object

    def enrich_diagnosis(
        self,
        diagnosis_result: Any,
        peer_metrics_json: Optional[Dict[str, Any]],
        ml_json: Optional[Dict[str, Any]],
        baselines: Optional[Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Enrich diagnosis result with peer hypothesis.

        Takes an existing diagnosis result (from AIAlertDiagnosisService) and enriches
        it with fleet/ML evidence. Does NOT modify the original hypotheses —
        only APPENDS a new hypothesis.

        Args:
            diagnosis_result: DiagnosisResult from AIAlertDiagnosisService.diagnose_alert()
            peer_metrics_json: Fleet peer metrics
            ml_json: ML prediction data
            baselines: Miner's baseline state

        Returns:
            Dict with enriched diagnosis:
            {
                'miner_id': str,
                'site_id': int,
                'alert_type': str,
                'hypotheses': [...],  # original + new peer hypothesis
                'diagnosed_at': str,
                'summary': str,
                'summary_zh': str,
                'data_sources': [...],
                ...
            }
        """
        # Create peer hypothesis
        peer_hypothesis = self.create_peer_hypothesis(
            miner_id=diagnosis_result.miner_id,
            peer_metrics_json=peer_metrics_json,
            ml_json=ml_json,
            baselines=baselines,
        )

        # Convert DiagnosisResult to dict (handle dataclass attributes)
        result_dict = {
            'alert_id': diagnosis_result.alert_id,
            'miner_id': diagnosis_result.miner_id,
            'site_id': diagnosis_result.site_id,
            'alert_type': diagnosis_result.alert_type,
            'diagnosed_at': diagnosis_result.diagnosed_at,
            'summary': diagnosis_result.summary,
            'summary_zh': diagnosis_result.summary_zh,
            'data_sources': diagnosis_result.data_sources,
            'hypotheses': [self._hypothesis_to_dict(h) for h in diagnosis_result.hypotheses],
        }

        # Append peer hypothesis if created
        if peer_hypothesis:
            result_dict['hypotheses'].append(peer_hypothesis)
            logger.info(
                f"Enriched diagnosis for {diagnosis_result.miner_id} "
                f"with peer hypothesis (total hypotheses: {len(result_dict['hypotheses'])})"
            )

        return result_dict

    def assess_miner(
        self,
        site_id: int,
        miner_id: str,
        features: Optional[Dict[str, float]],
        baselines: Optional[Dict[str, Dict[str, Any]]],
        peer_metrics_json: Optional[Dict[str, Any]],
        ml_json: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Full assessment: evaluate rules + build health object + create peer hypothesis.

        Main entry point called by batch assessment jobs.

        Args:
            site_id: Site identifier
            miner_id: Miner identifier
            features: Current miner features
                {'hashrate_ratio': float, 'boards_ratio': float, 'temp_max': float, 'efficiency': float}
            baselines: Miner's baseline state from BaselineService.get_baselines()
            peer_metrics_json: Fleet peer metrics from FleetBaselineService
            ml_json: ML prediction data with p_fail_24h and top_contributing_features

        Returns:
            Health Object dict with all issues and assessments
        """
        logger.debug(
            f"Assessing miner {miner_id} at site {site_id} "
            f"(has_features={features is not None}, has_baselines={baselines is not None}, "
            f"has_peer={peer_metrics_json is not None}, has_ml={ml_json is not None})"
        )

        # Extract issues from various sources
        issues = []
        p_fail_24h = ml_json.get('p_fail_24h', 0.0) if ml_json else 0.0

        # Add baseline anomaly issues
        if features and baselines:
            baseline_issues = self._build_baseline_issues(miner_id, features, baselines)
            issues.extend(baseline_issues)
            logger.debug(f"Added {len(baseline_issues)} baseline issues for {miner_id}")

        # Add peer outlier issues
        if peer_metrics_json and peer_metrics_json.get('metrics'):
            peer_issues = self._build_peer_issues(miner_id, peer_metrics_json)
            issues.extend(peer_issues)
            logger.debug(f"Added {len(peer_issues)} peer issues for {miner_id}")

        # Add ML prediction issue if p_fail_24h is elevated
        if p_fail_24h and p_fail_24h > 0.2:
            ml_issues = self._build_ml_issues(miner_id, p_fail_24h, ml_json)
            issues.extend(ml_issues)
            logger.debug(f"Added {len(ml_issues)} ML issues for {miner_id}")

        # Get last seen timestamp (use current time as fallback)
        last_seen_ts = datetime.utcnow().isoformat() + 'Z'

        # Build and return health object
        health_object = self.build_health_object(
            site_id=site_id,
            miner_id=miner_id,
            issues=issues,
            p_fail_24h=p_fail_24h,
            last_seen_ts=last_seen_ts,
        )

        logger.info(
            f"Assessment complete for {miner_id}: health_state={health_object['health_state']}, "
            f"p_fail_24h={p_fail_24h}, issues={len(issues)}"
        )

        return health_object

    # ============================================================================
    # Private helper methods
    # ============================================================================

    def _calculate_peer_confidence(self, peer_metrics_json: Optional[Dict]) -> float:
        """
        Calculate confidence from peer outlier data.

        Confidence = min(1.0, max_abs_robust_z / 5.0)
        Higher z-score = higher confidence, capped at 1.0.

        Args:
            peer_metrics_json: Fleet metrics from FleetBaselineService

        Returns:
            Confidence score 0-1
        """
        if not peer_metrics_json or not peer_metrics_json.get('metrics'):
            return 0.0

        max_abs_z = 0.0
        for metric_data in peer_metrics_json['metrics'].values():
            robust_z = abs(metric_data.get('robust_z', 0.0))
            max_abs_z = max(max_abs_z, robust_z)

        if max_abs_z == 0.0:
            return 0.0

        confidence = min(1.0, max_abs_z / 5.0)
        return round(confidence, 3)

    def _calculate_ml_confidence(self, ml_json: Optional[Dict]) -> float:
        """
        Calculate confidence from ML prediction.

        ML confidence = p_fail_24h (already a probability 0-1).

        Args:
            ml_json: ML prediction data

        Returns:
            Confidence score 0-1
        """
        if not ml_json:
            return 0.0

        p_fail = ml_json.get('p_fail_24h', 0.0)
        return round(float(p_fail), 3) if p_fail else 0.0

    def _determine_risk_level(
        self,
        peer_metrics_json: Optional[Dict],
        ml_json: Optional[Dict],
    ) -> str:
        """
        Determine risk level from peer and ML data.

        Risk mapping:
        - P0: any metric with |robust_z| > 5
        - P1: any metric with |robust_z| > 3 or p_fail_24h > 0.8
        - P2: any metric with |robust_z| > 2 or p_fail_24h > 0.5
        - P3: everything else

        Args:
            peer_metrics_json: Fleet metrics
            ml_json: ML data

        Returns:
            Risk level string: 'P0', 'P1', 'P2', 'P3'
        """
        max_abs_z = 0.0
        if peer_metrics_json and peer_metrics_json.get('metrics'):
            for metric_data in peer_metrics_json['metrics'].values():
                robust_z = abs(metric_data.get('robust_z', 0.0))
                max_abs_z = max(max_abs_z, robust_z)

        p_fail = ml_json.get('p_fail_24h', 0.0) if ml_json else 0.0

        # P0: |z| > 5
        if max_abs_z > 5:
            return 'P0'

        # P1: |z| > 3 or p_fail > 0.8
        if max_abs_z > 3 or p_fail > 0.8:
            return 'P1'

        # P2: |z| > 2 or p_fail > 0.5
        if max_abs_z > 2 or p_fail > 0.5:
            return 'P2'

        # P3: everything else
        return 'P3'

    def _build_peer_evidence(
        self,
        peer_metrics_json: Optional[Dict],
        ml_json: Optional[Dict],
        baselines: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """
        Build evidence list from peer metrics and ML data.

        Includes fleet position, percentile rank, and ML feature contributions.

        Returns:
            List of evidence dicts with keys:
            metric, description, description_zh, value, threshold, assessment
        """
        evidence = []

        # Add peer metrics evidence
        if peer_metrics_json and peer_metrics_json.get('metrics'):
            for metric_name, metric_data in peer_metrics_json['metrics'].items():
                robust_z = metric_data.get('robust_z', 0.0)

                # Only include metrics with notable deviation
                if abs(robust_z) >= 1.0:
                    percentile = metric_data.get('percentile_rank', 0.0)
                    value = metric_data.get('value', 0.0)
                    median = metric_data.get('group_median', 0.0)
                    p10 = metric_data.get('group_p10', 0.0)
                    p90 = metric_data.get('group_p90', 0.0)

                    evidence.append({
                        'metric': f'peer_{metric_name}',
                        'description': (
                            f'{metric_name}: {value:.3f} (percentile {percentile:.0f}, z={robust_z:.2f}), '
                            f'peer range [{p10:.3f}-{p90:.3f}], median {median:.3f}'
                        ),
                        'description_zh': (
                            f'{metric_name}: {value:.3f}（第{percentile:.0f}百分位，z={robust_z:.2f}），'
                            f'同组范围[{p10:.3f}-{p90:.3f}]，中位数{median:.3f}'
                        ),
                        'value': value,
                        'threshold': median,
                        'assessment': 'peer_outlier' if abs(robust_z) > 2 else 'peer_deviation',
                    })

        # Add ML prediction evidence
        if ml_json and ml_json.get('p_fail_24h'):
            p_fail = ml_json['p_fail_24h']
            evidence.append({
                'metric': 'p_fail_24h',
                'description': f'24h failure probability: {p_fail:.3f}',
                'description_zh': f'24小时故障概率：{p_fail:.3f}',
                'value': p_fail,
                'threshold': 0.5,
                'assessment': 'high_risk' if p_fail > 0.5 else 'elevated_risk',
            })

            # Add top contributing features
            if ml_json.get('top_contributing_features'):
                top_features = ml_json['top_contributing_features'][:3]
                features_str = ', '.join(
                    [f"{f['feature']}({f['importance']:.2f})" for f in top_features]
                )
                evidence.append({
                    'metric': 'ml_top_features',
                    'description': f'Top failure contributing factors: {features_str}',
                    'description_zh': f'故障主要贡献因素：{features_str}',
                    'value': len(top_features),
                    'threshold': None,
                    'assessment': 'ml_insight',
                })

        return evidence

    def _build_peer_actions(
        self,
        peer_metrics_json: Optional[Dict],
        ml_json: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """
        Build recommended actions based on issue type.

        Actions vary based on:
        - Hashrate outlier: check hardware vs peers
        - Temperature outlier: inspect cooling system
        - High p_fail_24h: schedule preventive maintenance
        - General: monitor closely

        Returns:
            List of action dicts with keys:
            action, action_zh, priority, reason, reason_zh
        """
        actions = []

        # Analyze peer metrics to determine action type
        if peer_metrics_json and peer_metrics_json.get('metrics'):
            metrics = peer_metrics_json['metrics']

            # Check for hashrate outlier
            if 'hashrate_ratio' in metrics:
                hr_data = metrics['hashrate_ratio']
                if abs(hr_data.get('robust_z', 0.0)) > 2:
                    actions.append({
                        'action': 'Check miner hardware, compare with peers',
                        'action_zh': '检查矿机硬件，与同组矿机对比',
                        'priority': 1,
                        'reason': 'Significant hashrate deviation from peer group',
                        'reason_zh': '算力与同组矿机有显著偏差',
                    })

            # Check for temperature outlier
            if 'temp_max' in metrics:
                temp_data = metrics['temp_max']
                if abs(temp_data.get('robust_z', 0.0)) > 2:
                    actions.append({
                        'action': 'Inspect cooling system, check ambient temperature',
                        'action_zh': '检查散热系统，检查环境温度',
                        'priority': 1,
                        'reason': 'Temperature elevated compared to peers',
                        'reason_zh': '温度相比同组矿机较高',
                    })

        # ML-based action
        if ml_json and ml_json.get('p_fail_24h', 0.0) > 0.5:
            actions.append({
                'action': 'Schedule preventive maintenance',
                'action_zh': '安排预防性维护',
                'priority': 1,
                'reason': 'High failure prediction score',
                'reason_zh': '故障风险评分较高',
            })

        # Default action if no specific issues
        if not actions:
            actions.append({
                'action': 'Monitor closely, review in next cycle',
                'action_zh': '密切监控，下一周期评估',
                'priority': 2,
                'reason': 'General monitoring recommendation',
                'reason_zh': '常规监控建议',
            })

        return actions

    def _determine_health_state(
        self,
        issues: List[Dict],
        p_fail_24h: Optional[float],
    ) -> str:
        """
        Determine worst health state from issues and ML prediction.

        Health state is the worst (highest severity) among all issues,
        or 'OK' if no issues and low failure risk.

        Returns:
            'P0', 'P1', 'P2', 'P3', or 'OK'
        """
        # No issues and low failure risk -> OK
        if not issues and (not p_fail_24h or p_fail_24h <= 0.2):
            return 'OK'

        # Find worst severity from issues
        worst_severity = 'P3'
        for issue in issues:
            severity = issue.get('severity', 'P3')
            if self._severity_rank(severity) > self._severity_rank(worst_severity):
                worst_severity = severity

        # Check ML prediction
        if p_fail_24h and p_fail_24h > 0.8:
            worst_severity = 'P1'
        elif p_fail_24h and p_fail_24h > 0.5:
            if self._severity_rank('P2') > self._severity_rank(worst_severity):
                worst_severity = 'P2'

        return worst_severity

    def _severity_rank(self, severity: str) -> int:
        """
        Map severity level to numeric rank.

        Higher rank = worse severity.
        """
        rank_map = {'OK': 0, 'P3': 1, 'P2': 2, 'P1': 3, 'P0': 4}
        return rank_map.get(severity, 1)

    def _build_baseline_issues(
        self,
        miner_id: str,
        features: Dict[str, float],
        baselines: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Build issues from baseline anomalies.

        Analyzes per-miner baseline z-scores to identify deviations
        from the miner's own historical pattern.

        Returns:
            List of issue dicts
        """
        issues = []

        for metric_name, baseline_data in baselines.items():
            z_score = baseline_data.get('z_score', 0.0)

            # Skip if no significant deviation
            if abs(z_score) < 1.5:
                continue

            # Determine severity based on z-score magnitude
            if abs(z_score) > 3:
                severity = 'P1'
            elif abs(z_score) > 2:
                severity = 'P2'
            else:
                severity = 'P3'

            # Build issue
            issues.append({
                'issue_code': f'baseline_{metric_name}',
                'severity': severity,
                'evidence': [
                    {
                        'metric': metric_name,
                        'description': f'{metric_name}: z_score={z_score:.2f}',
                        'description_zh': f'{metric_name}：z_score={z_score:.2f}',
                        'value': features.get(metric_name, 0.0),
                        'assessment': 'baseline_anomaly',
                    }
                ],
                'recommended_actions': [
                    {
                        'action': 'Review miner metrics in detail',
                        'action_zh': '详细审查矿机指标',
                        'priority': 2,
                        'reason': 'Baseline deviation detected',
                        'reason_zh': '检测到基线偏差',
                    }
                ],
                'confidence': min(1.0, abs(z_score) / 5.0),
            })

        return issues

    def _build_peer_issues(
        self,
        miner_id: str,
        peer_metrics_json: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Build issues from peer outliers.

        Analyzes fleet-level metrics to identify miners that deviate
        significantly from their peer group.

        Returns:
            List of issue dicts
        """
        issues = []

        for metric_name, metric_data in peer_metrics_json.get('metrics', {}).items():
            robust_z = metric_data.get('robust_z', 0.0)

            # Skip if no significant deviation
            if abs(robust_z) < 1.5:
                continue

            # Determine severity based on z-score magnitude
            if abs(robust_z) > 5:
                severity = 'P0'
            elif abs(robust_z) > 3:
                severity = 'P1'
            elif abs(robust_z) > 2:
                severity = 'P2'
            else:
                severity = 'P3'

            # Determine action based on metric type
            action = 'Monitor closely, review in next cycle'
            action_zh = '密切监控，下一周期评估'

            if 'hashrate' in metric_name:
                action = 'Check miner hardware, compare with peers'
                action_zh = '检查矿机硬件，与同组矿机对比'
            elif 'temp' in metric_name:
                action = 'Inspect cooling system, check ambient temperature'
                action_zh = '检查散热系统，检查环境温度'

            # Build issue
            issues.append({
                'issue_code': f'peer_{metric_name}',
                'severity': severity,
                'evidence': [
                    {
                        'metric': metric_name,
                        'description': (
                            f'{metric_name}: z={robust_z:.2f}, '
                            f'percentile={metric_data.get("percentile_rank", 0):.0f}'
                        ),
                        'description_zh': (
                            f'{metric_name}：z={robust_z:.2f}，'
                            f'百分位={metric_data.get("percentile_rank", 0):.0f}'
                        ),
                        'value': metric_data.get('value', 0.0),
                        'threshold': metric_data.get('group_median', 0.0),
                        'assessment': 'peer_outlier',
                    }
                ],
                'recommended_actions': [
                    {
                        'action': action,
                        'action_zh': action_zh,
                        'priority': 1 if abs(robust_z) > 3 else 2,
                        'reason': f'Peer outlier: z={robust_z:.2f}',
                        'reason_zh': f'同组异常：z={robust_z:.2f}',
                    }
                ],
                'confidence': min(1.0, abs(robust_z) / 5.0),
            })

        return issues

    def _build_ml_issues(
        self,
        miner_id: str,
        p_fail_24h: float,
        ml_json: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Build issues from ML failure prediction.

        ML model predicts 24-hour failure probability; issues are created
        for elevated risk scores.

        Returns:
            List of issue dicts
        """
        issues = []

        # Determine severity from p_fail_24h
        if p_fail_24h > 0.8:
            severity = 'P1'
        elif p_fail_24h > 0.5:
            severity = 'P2'
        else:
            severity = 'P3'

        # Build issue
        issues.append({
            'issue_code': 'ml_failure_risk',
            'severity': severity,
            'evidence': [
                {
                    'metric': 'p_fail_24h',
                    'description': f'24h failure probability: {p_fail_24h:.3f}',
                    'description_zh': f'24小时故障概率：{p_fail_24h:.3f}',
                    'value': p_fail_24h,
                    'threshold': 0.5,
                    'assessment': 'ml_prediction',
                }
            ],
            'recommended_actions': [
                {
                    'action': 'Schedule preventive maintenance',
                    'action_zh': '安排预防性维护',
                    'priority': 1,
                    'reason': 'Elevated failure risk from ML model',
                    'reason_zh': 'ML模型预测故障风险较高',
                }
            ],
            'confidence': p_fail_24h,
        })

        return issues

    def _hypothesis_to_dict(self, hypothesis: Any) -> Dict[str, Any]:
        """
        Convert RootCauseHypothesis dataclass to dict.

        Handles conversion of nested Evidence and SuggestedAction dataclasses
        to dict format for JSON serialization.

        Args:
            hypothesis: RootCauseHypothesis instance

        Returns:
            Dict representation of hypothesis
        """
        # Convert evidence list
        evidence_list = []
        for ev in hypothesis.evidence:
            evidence_dict = {
                'metric': ev.metric,
                'description': ev.description,
                'description_zh': ev.description_zh,
                'value': ev.value,
                'threshold': ev.threshold,
            }
            # Add optional fields if present
            if hasattr(ev, 'deviation_pct') and ev.deviation_pct is not None:
                evidence_dict['deviation_pct'] = ev.deviation_pct
            if hasattr(ev, 'timestamp') and ev.timestamp is not None:
                evidence_dict['timestamp'] = ev.timestamp
            if hasattr(ev, 'assessment') and ev.assessment is not None:
                evidence_dict['assessment'] = ev.assessment
            evidence_list.append(evidence_dict)

        # Convert suggested_actions list
        actions_list = []
        for action in hypothesis.suggested_actions:
            action_dict = {
                'action': action.action,
                'action_zh': action.action_zh,
                'priority': action.priority,
                'reason': action.reason,
                'reason_zh': action.reason_zh,
            }
            # Add optional fields if present
            if hasattr(action, 'command_type') and action.command_type is not None:
                action_dict['command_type'] = action.command_type
            if hasattr(action, 'parameters') and action.parameters is not None:
                action_dict['parameters'] = action.parameters
            actions_list.append(action_dict)

        return {
            'hypothesis_id': hypothesis.hypothesis_id,
            'cause': hypothesis.cause,
            'cause_zh': hypothesis.cause_zh,
            'confidence': hypothesis.confidence,
            'risk_level': hypothesis.risk_level,
            'evidence': evidence_list,
            'suggested_actions': actions_list,
        }
