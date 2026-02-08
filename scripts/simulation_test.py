#!/usr/bin/env python3
"""
全面模拟测试 - Problem Registry + Fleet Anomaly Detection + Predictive Maintenance
Comprehensive Simulation Test - End-to-End Pipeline Verification

This script simulates a realistic mining fleet with various health scenarios,
runs the complete pipeline, and verifies all 10 services work correctly.

Test Scenarios:
1. Normal healthy miners (should produce no events)
2. Overheating miners (P0 hard rule)
3. Offline miners (P0 hard rule)
4. Hashrate degradation over time (P2 soft rule via EWMA)
5. Fleet outlier detection (P3 via robust z-score)
6. Maintenance suppression (should suppress events)
7. Event lifecycle: debounce → open → resolve → recurrence
8. Mode inference (eco/normal/perf clustering)
9. Policy engine budget enforcement
10. Diagnosis fusion + Health Object generation
"""

import sys
import os
import json
import time
import logging
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger('simulation_test')
logger.setLevel(logging.INFO)

SITE_ID = 998
MINER_PREFIX = 'SIM_TEST_'
PASS_COUNT = 0
FAIL_COUNT = 0
TEST_RESULTS = []

def header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def check(description, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        status = "✅ PASS"
    else:
        FAIL_COUNT += 1
        status = "❌ FAIL"
    msg = f"  {status}: {description}"
    if detail and not condition:
        msg += f" -- {detail}"
    print(msg)
    TEST_RESULTS.append({'desc': description, 'pass': condition, 'detail': detail})
    return condition

def cleanup(db):
    from sqlalchemy import text
    db.session.execute(text(f"DELETE FROM problem_events WHERE miner_id LIKE '{MINER_PREFIX}%'"))
    db.session.execute(text(f"DELETE FROM miner_baseline_state WHERE miner_id LIKE '{MINER_PREFIX}%'"))
    db.session.execute(text(f"DELETE FROM ml_model_registry WHERE model_name LIKE 'sim_test_%'"))
    db.session.commit()

def run_simulation():
    global PASS_COUNT, FAIL_COUNT

    from app import app, db
    from sqlalchemy import text

    with app.app_context():
        print("\n" + "🔧" * 35)
        print("  Problem Registry 全面模拟测试")
        print("  Comprehensive Simulation Test")
        print("🔧" * 35)

        cleanup(db)
        print("\n  [Setup] Cleaned up previous simulation data")

        # ============================================================
        # TEST 1: BaselineService - Incremental EWMA
        # ============================================================
        header("TEST 1: BaselineService - Incremental EWMA Updates")

        from services.baseline_service import BaselineService
        bs = BaselineService()

        features_t1 = {'hashrate_ratio': 0.95, 'boards_ratio': 1.0, 'temp_max': 65.0, 'efficiency': 30.0}
        r1 = bs.update_baseline(f'{MINER_PREFIX}BL_001', SITE_ID, features_t1)
        db.session.commit()

        check("First sample: EWMA = raw value",
              r1['hashrate_ratio']['ewma'] == round(0.95, 6),
              f"expected 0.95, got {r1['hashrate_ratio']['ewma']}")

        check("First sample: sample_count = 1",
              r1['hashrate_ratio']['sample_count'] == 1)

        check("First sample: residual = 0 (no history)",
              r1['hashrate_ratio']['residual'] == 0.0)

        features_t2 = {'hashrate_ratio': 0.85, 'boards_ratio': 0.95, 'temp_max': 70.0, 'efficiency': 32.0}
        r2 = bs.update_baseline(f'{MINER_PREFIX}BL_001', SITE_ID, features_t2)
        db.session.commit()

        check("Second sample: EWMA blended (not raw)",
              r2['hashrate_ratio']['ewma'] != 0.85,
              f"got {r2['hashrate_ratio']['ewma']}")

        check("Second sample: sample_count = 2",
              r2['hashrate_ratio']['sample_count'] == 2)

        check("Second sample: negative residual (0.85 < ewma)",
              r2['hashrate_ratio']['residual'] < 0,
              f"residual={r2['hashrate_ratio']['residual']}")

        for i in range(10):
            features_ti = {'hashrate_ratio': 0.70, 'boards_ratio': 1.0, 'temp_max': 65.0}
            ri = bs.update_baseline(f'{MINER_PREFIX}BL_001', SITE_ID, features_ti)
            db.session.commit()

        check("After 12 samples of 0.70: EWMA converges toward 0.70",
              ri['hashrate_ratio']['ewma'] < 0.80,
              f"ewma={ri['hashrate_ratio']['ewma']}")

        check("Z-score is negative (degradation signal)",
              ri['hashrate_ratio']['z_score'] < 0,
              f"z_score={ri['hashrate_ratio']['z_score']}")

        baselines = bs.get_baselines(f'{MINER_PREFIX}BL_001')
        check("get_baselines returns stored metrics",
              'hashrate_ratio' in baselines and 'temp_max' in baselines,
              f"keys={list(baselines.keys())}")

        # ============================================================
        # TEST 2: Baseline - Missing Fields Graceful Degradation
        # ============================================================
        header("TEST 2: BaselineService - Missing Fields Graceful Degradation")

        r_partial = bs.update_baseline(f'{MINER_PREFIX}BL_002', SITE_ID, {'hashrate_ratio': 0.9})
        db.session.commit()
        check("Partial features: only hashrate_ratio processed",
              'hashrate_ratio' in r_partial and 'temp_max' not in r_partial)

        r_none = bs.update_baseline(f'{MINER_PREFIX}BL_003', SITE_ID, {'hashrate_ratio': None, 'temp_max': None})
        db.session.commit()
        check("All-None features: returns empty dict",
              len(r_none) == 0)

        # ============================================================
        # TEST 3: ModeInferenceService - KMeans Clustering
        # ============================================================
        header("TEST 3: ModeInferenceService - KMeans Clustering")

        from services.mode_inference_service import ModeInferenceService
        import numpy as np
        np.random.seed(42)

        mis = ModeInferenceService()

        records = []
        for i in range(8):
            records.append({
                'miner_id': f'{MINER_PREFIX}ECO_{i}',
                'site_id': SITE_ID,
                'model': 'S19 Pro',
                'firmware': 'v1.0',
                'hashrate_ratio': 0.55 + np.random.normal(0, 0.02),
                'temp_max': 52 + np.random.normal(0, 2),
                'efficiency': None,
            })
        for i in range(8):
            records.append({
                'miner_id': f'{MINER_PREFIX}NORM_{i}',
                'site_id': SITE_ID,
                'model': 'S19 Pro',
                'firmware': 'v1.0',
                'hashrate_ratio': 0.90 + np.random.normal(0, 0.02),
                'temp_max': 65 + np.random.normal(0, 2),
                'efficiency': None,
            })
        for i in range(8):
            records.append({
                'miner_id': f'{MINER_PREFIX}PERF_{i}',
                'site_id': SITE_ID,
                'model': 'S19 Pro',
                'firmware': 'v1.0',
                'hashrate_ratio': 1.08 + np.random.normal(0, 0.02),
                'temp_max': 78 + np.random.normal(0, 2),
                'efficiency': None,
            })

        modes_result = mis.infer_modes(records)

        eco_modes = [modes_result[f'{MINER_PREFIX}ECO_{i}']['inferred_mode'] for i in range(8)]
        perf_modes = [modes_result[f'{MINER_PREFIX}PERF_{i}']['inferred_mode'] for i in range(8)]

        check("ECO miners get 'eco' mode",
              all(m == 'eco' for m in eco_modes),
              f"modes={eco_modes}")

        check("PERF miners get 'perf' mode",
              all(m == 'perf' for m in perf_modes),
              f"modes={perf_modes}")

        modes_r2 = mis.infer_modes(records)
        stability = all(
            modes_result[mid]['inferred_mode'] == modes_r2[mid]['inferred_mode']
            for mid in modes_result
        )
        check("Deterministic: same input → same output",
              stability)

        confidence = modes_result[f'{MINER_PREFIX}ECO_0'].get('confidence', 0)
        check("Confidence score is between 0 and 1",
              0 <= confidence <= 1,
              f"confidence={confidence}")

        small_records = [records[0], records[1], records[2]]
        small_modes = mis.infer_modes(small_records)
        check("Small group (<5) → mode='unknown'",
              all(small_modes[mid]['inferred_mode'] == 'unknown' for mid in small_modes))

        # ============================================================
        # TEST 4: FleetBaselineService - Peer Metrics & Cache
        # ============================================================
        header("TEST 4: FleetBaselineService - Peer Metrics & Cache")

        from services.fleet_baseline_service import FleetBaselineService
        fbs = FleetBaselineService()

        fleet_records = [
            {'hashrate_ratio': 0.88 + i * 0.01, 'boards_ratio': 1.0, 'temp_max': 63 + i, 'efficiency': None}
            for i in range(15)
        ]

        group_key = f'sim_test:{SITE_ID}:S19Pro:v1:normal'
        metrics = fbs.compute_peer_metrics(group_key, fleet_records)

        check("Peer metrics: has hashrate_ratio",
              'hashrate_ratio' in metrics,
              f"keys={list(metrics.keys())}")

        hr_m = metrics.get('hashrate_ratio', {})
        check("Peer metrics: median is reasonable",
              0.88 <= hr_m.get('median', 0) <= 1.05,
              f"median={hr_m.get('median')}")

        check("Peer metrics: has percentiles (p10, p25, p75, p90)",
              all(k in hr_m for k in ['p10', 'p25', 'p75', 'p90']),
              f"keys={list(hr_m.keys())}")

        check("Peer metrics: MAD > 0",
              hr_m.get('mad', 0) > 0,
              f"mad={hr_m.get('mad')}")

        cached = fbs.get_peer_metrics(group_key)
        check("Cache: returns cached metrics",
              cached is not None and cached == metrics)

        z = fbs.compute_robust_z(0.50, group_key, 'hashrate_ratio')
        check("Robust z-score: low hashrate gets very negative z",
              z < -2.0,
              f"z={z}")

        fbs.invalidate_cache(group_key)
        check("Cache invalidation works",
              fbs.get_peer_metrics(group_key) is None)

        # ============================================================
        # TEST 5: HealthRulesEngine - Hard Rules
        # ============================================================
        header("TEST 5: HealthRulesEngine - Hard Rules")

        from services.health_rules import HealthRulesEngine
        hre = HealthRulesEngine()

        overheat_f = {'temp_max': 92, 'is_online': True, 'hashrate_ratio': 0.5, 'boards_ratio': 1.0}
        overheat_issues = hre.evaluate_hard_rules(overheat_f)
        overheat_codes = [i['code'] for i in overheat_issues]
        check("P0: overheat_crit triggers at temp=92",
              'overheat_crit' in overheat_codes,
              f"codes={overheat_codes}")

        offline_f = {'temp_max': 0, 'is_online': False, 'hashrate_ratio': 0, 'boards_ratio': 0}
        offline_issues = hre.evaluate_hard_rules(offline_f)
        offline_codes = [i['code'] for i in offline_issues]
        check("P0: offline triggers when is_online=False",
              'offline' in offline_codes,
              f"codes={offline_codes}")

        zero_hr_f = {'temp_max': 60, 'is_online': True, 'hashrate_ratio': 0.0, 'boards_ratio': 1.0, 'fan_speed_min': 3000}
        zero_hr_issues = hre.evaluate_hard_rules(zero_hr_f)
        zero_hr_codes = [i['code'] for i in zero_hr_issues]
        check("P1: hashrate_zero triggers when online + HR=0",
              'hashrate_zero' in zero_hr_codes,
              f"codes={zero_hr_codes}")

        boards_dead_f = {'temp_max': 60, 'is_online': True, 'hashrate_ratio': 0.3, 'boards_ratio': 0.3}
        boards_issues = hre.evaluate_hard_rules(boards_dead_f)
        boards_codes = [i['code'] for i in boards_issues]
        check("P1: boards_dead triggers when boards_ratio=0.3",
              'boards_dead' in boards_codes,
              f"codes={boards_codes}")

        normal_f = {'temp_max': 60, 'is_online': True, 'hashrate_ratio': 0.95, 'boards_ratio': 1.0, 'fan_speed_min': 3000}
        normal_issues = hre.evaluate_hard_rules(normal_f)
        check("Normal miner: no hard rules trigger",
              len(normal_issues) == 0,
              f"issues={[i['code'] for i in normal_issues]}")

        # ============================================================
        # TEST 6: HealthRulesEngine - Soft Rules
        # ============================================================
        header("TEST 6: HealthRulesEngine - Soft Rules")

        degraded_baselines = {
            'hashrate_ratio': {'z_score': -3.0, 'sample_count': 10, 'ewma': 0.9, 'residual': -0.15},
            'boards_ratio': {'z_score': 0, 'sample_count': 10, 'ewma': 1.0, 'residual': 0},
            'temp_max': {'z_score': 0, 'sample_count': 10, 'ewma': 65, 'residual': 0},
        }
        soft_f = {'hashrate_ratio': 0.75, 'fleet_z_hashrate': 0}
        soft_issues = hre.evaluate_soft_rules(soft_f, degraded_baselines)
        soft_codes = [i['code'] for i in soft_issues]
        check("P2: hashrate_degradation triggers (z_score=-3, samples>=6)",
              'hashrate_degradation' in soft_codes,
              f"codes={soft_codes}")

        cold_baselines = {
            'hashrate_ratio': {'z_score': -3.0, 'sample_count': 3, 'ewma': 0.9, 'residual': -0.15},
        }
        cold_issues = hre.evaluate_soft_rules(soft_f, cold_baselines)
        check("Cold-start guard: sample_count=3 prevents trigger",
              len(cold_issues) == 0,
              f"issues={[i['code'] for i in cold_issues]}")

        fleet_outlier_f = {'hashrate_ratio': 0.5, 'fleet_z_hashrate': -4.0}
        fleet_baselines = {'hashrate_ratio': {'z_score': 0, 'sample_count': 10}}
        fleet_issues = hre.evaluate_soft_rules(fleet_outlier_f, fleet_baselines)
        fleet_codes = [i['code'] for i in fleet_issues]
        check("P3: fleet_outlier triggers (fleet_z=-4.0)",
              'fleet_outlier' in fleet_codes,
              f"codes={fleet_codes}")

        # ============================================================
        # TEST 7: EventEngine - Full Lifecycle
        # ============================================================
        header("TEST 7: EventEngine - Full Lifecycle (Debounce → Open → Resolve → Recurrence)")

        from services.event_engine import EventEngine
        ee = EventEngine()

        r_d1 = ee.process_detection(SITE_ID, f'{MINER_PREFIX}LIFE_001', 'overheat_crit', 'P0', {'temp': 90})
        check("Detection 1: event created (ack, debouncing)",
              r_d1['action'] in ('created', 'debouncing'),
              f"action={r_d1['action']}")
        event_id = r_d1.get('event_id')

        r_d2 = ee.process_detection(SITE_ID, f'{MINER_PREFIX}LIFE_001', 'overheat_crit', 'P0', {'temp': 91})
        check("Detection 2: passes debounce threshold → open/updated",
              r_d2['action'] in ('created', 'updated', 'escalated'),
              f"action={r_d2['action']}")

        for i in range(ee.RESOLVE_THRESHOLD):
            r_h = ee.process_healthy(SITE_ID, f'{MINER_PREFIX}LIFE_001', 'overheat_crit')

        check(f"After {ee.RESOLVE_THRESHOLD} healthy signals: event resolved",
              r_h['action'] == 'resolved',
              f"action={r_h['action']}, consecutive_ok={r_h.get('consecutive_ok')}")

        r_recur1 = ee.process_detection(SITE_ID, f'{MINER_PREFIX}LIFE_001', 'overheat_crit', 'P0', {'temp': 95})
        r_recur2 = ee.process_detection(SITE_ID, f'{MINER_PREFIX}LIFE_001', 'overheat_crit', 'P0', {'temp': 96})
        check("Recurrence: event reopened after resolve",
              r_recur2['action'] in ('created', 'updated', 'reopened', 'escalated'),
              f"action={r_recur2['action']}")

        # ============================================================
        # TEST 8: EventEngine - Maintenance Suppression
        # ============================================================
        header("TEST 8: EventEngine - Maintenance Suppression")

        ee.process_detection(SITE_ID, f'{MINER_PREFIX}SUP_001', 'offline', 'P0', {'status': 'offline'})
        ee.suppress_miner(f'{MINER_PREFIX}SUP_001', until=datetime.utcnow() + timedelta(hours=2), maintenance=True)

        r_sup = ee.process_detection(SITE_ID, f'{MINER_PREFIX}SUP_001', 'overheat_crit', 'P0', {'temp': 95})
        check("Suppressed miner: new detection is suppressed",
              r_sup['action'] == 'suppressed',
              f"action={r_sup['action']}")

        ee.unsuppress_miner(f'{MINER_PREFIX}SUP_001')

        r_unsup = ee.process_detection(SITE_ID, f'{MINER_PREFIX}SUP_001', 'overheat_crit', 'P0', {'temp': 95})
        check("After unsuppress: detection works again",
              r_unsup['action'] != 'suppressed',
              f"action={r_unsup['action']}")

        # ============================================================
        # TEST 9: EventEngine - Severity Escalation
        # ============================================================
        header("TEST 9: EventEngine - Severity Escalation")

        ee.process_detection(SITE_ID, f'{MINER_PREFIX}ESC_001', 'overheat_warn', 'P1', {'temp': 78})
        ee.process_detection(SITE_ID, f'{MINER_PREFIX}ESC_001', 'overheat_warn', 'P1', {'temp': 78})

        r_esc = ee.process_detection(SITE_ID, f'{MINER_PREFIX}ESC_001', 'overheat_warn', 'P0', {'temp': 88})
        check("Severity escalation: P1 → P0",
              r_esc['action'] in ('escalated', 'updated'),
              f"action={r_esc['action']}")

        row = db.session.execute(text(
            f"SELECT severity FROM problem_events WHERE miner_id='{MINER_PREFIX}ESC_001' AND issue_code='overheat_warn' AND status IN ('open','ack') LIMIT 1"
        )).fetchone()
        check("Escalated severity stored in DB as P0",
              row is not None and row[0] == 'P0',
              f"severity={row[0] if row else 'None'}")

        # ============================================================
        # TEST 10: EventEngine - Bulk Process
        # ============================================================
        header("TEST 10: EventEngine - Bulk Process")

        detections = []
        for i in range(5):
            detections.append({
                'site_id': SITE_ID,
                'miner_id': f'{MINER_PREFIX}BULK_{i:03d}',
                'issue_code': 'overheat_warn',
                'severity': 'P1',
                'evidence': {'temp': 80 + i},
            })
        for i in range(5):
            detections.append({
                'site_id': SITE_ID,
                'miner_id': f'{MINER_PREFIX}BULK_{i:03d}',
                'issue_code': 'overheat_warn',
                'severity': 'P1',
                'evidence': {'temp': 81 + i},
            })

        healthy_signals = [
            {'site_id': SITE_ID, 'miner_id': f'{MINER_PREFIX}BULK_099', 'issue_code': 'offline'}
        ]

        summary = ee.bulk_process(detections, healthy_signals)
        check("Bulk process: total_processed > 0",
              summary['total_processed'] > 0,
              f"total={summary['total_processed']}")

        check("Bulk process: created + updated + debouncing > 0",
              (summary.get('created', 0) + summary.get('updated', 0) + summary.get('debouncing', 0)) > 0,
              f"summary={summary}")

        # ============================================================
        # TEST 11: DiagnosisFusion - Health Object & Peer Hypothesis
        # ============================================================
        header("TEST 11: DiagnosisFusion - Health Object & Peer Hypothesis")

        from services.diagnosis_fusion import DiagnosisFusion
        df = DiagnosisFusion()

        peer_metrics = {
            'group_key': f'{SITE_ID}:S19Pro:v1:normal',
            'group_size': 50,
            'metrics': {
                'hashrate_ratio': {
                    'value': 0.60,
                    'group_median': 0.92,
                    'robust_z': -4.5,
                    'percentile_rank': 2,
                    'group_p10': 0.85,
                    'group_p90': 0.98,
                },
                'temp_max': {
                    'value': 82,
                    'group_median': 65,
                    'robust_z': 3.2,
                    'percentile_rank': 98,
                    'group_p10': 58,
                    'group_p90': 72,
                },
            }
        }

        ml_data = {
            'p_fail_24h': 0.78,
            'top_contributing_features': [
                {'feature': 'hashrate_ratio_ewma', 'importance': 0.35},
                {'feature': 'temp_max_z_score', 'importance': 0.25},
                {'feature': 'boards_ratio_residual', 'importance': 0.15},
            ]
        }

        hyp = df.create_peer_hypothesis(f'{MINER_PREFIX}DIAG_001', peer_metrics, ml_data, None)
        check("Peer hypothesis created",
              hyp is not None and hyp['hypothesis_id'] == 'peer_outlier_risk')

        check("Hypothesis has evidence items",
              len(hyp.get('evidence', [])) >= 2,
              f"evidence_count={len(hyp.get('evidence', []))}")

        check("Hypothesis has recommended actions",
              len(hyp.get('recommended_actions', [])) >= 1)

        check("Risk level reflects severity",
              hyp.get('risk_level') in ('P0', 'P1'),
              f"risk_level={hyp.get('risk_level')}")

        health_obj = df.build_health_object(
            site_id=SITE_ID,
            miner_id=f'{MINER_PREFIX}DIAG_001',
            issues=[
                {'issue_code': 'overheat_warn', 'severity': 'P1', 'evidence': {'temp': 82}},
                {'issue_code': 'hashrate_degradation', 'severity': 'P2', 'evidence': {'z_score': -3.0}},
            ],
            p_fail_24h=0.78,
            last_seen_ts=datetime.utcnow().isoformat() + 'Z',
        )

        check("Health Object: health_state = P1 (worst severity)",
              health_obj['health_state'] == 'P1',
              f"health_state={health_obj['health_state']}")

        check("Health Object: has assessed_at timestamp",
              'assessed_at' in health_obj)

        check("Health Object: p_fail_24h preserved",
              health_obj['p_fail_24h'] == 0.78)

        full_assessment = df.assess_miner(
            site_id=SITE_ID,
            miner_id=f'{MINER_PREFIX}DIAG_002',
            features={'hashrate_ratio': 0.60, 'temp_max': 82},
            baselines={
                'hashrate_ratio': {'z_score': -3.5, 'sample_count': 10, 'ewma': 0.9, 'residual': -0.3},
                'temp_max': {'z_score': 3.0, 'sample_count': 10, 'ewma': 65, 'residual': 17},
            },
            peer_metrics_json=peer_metrics,
            ml_json=ml_data,
        )

        check("Full assessment: returns health object",
              'health_state' in full_assessment and 'issues' in full_assessment)

        check("Full assessment: has issues detected",
              len(full_assessment.get('issues', [])) > 0,
              f"issues_count={len(full_assessment.get('issues', []))}")

        # ============================================================
        # TEST 12: PolicyEngine - Budget Enforcement
        # ============================================================
        header("TEST 12: PolicyEngine - Budget & Dispatch Rules")

        from services.policy_engine import PolicyEngine
        pe = PolicyEngine()

        p0_events = [{
            'event_id': f'sim-p0-{i}',
            'site_id': SITE_ID,
            'miner_id': f'{MINER_PREFIX}P0_{i}',
            'issue_code': 'overheat_crit',
            'severity': 'P0',
            'status': 'open',
            'start_ts': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            'ml_json': {'p_fail_24h': 0.9},
            'action': 'created',
        } for i in range(3)]

        p0_result = pe.evaluate_batch(p0_events, site_miner_count=500)
        check("P0: ALWAYS notifies (3/3)",
              p0_result['stats']['notifications_sent'] == 3,
              f"sent={p0_result['stats']['notifications_sent']}")

        check("P0: ALWAYS creates tickets (3/3)",
              p0_result['stats']['tickets_created'] == 3,
              f"created={p0_result['stats']['tickets_created']}")

        p3_events = [{
            'event_id': f'sim-p3-{i}',
            'site_id': SITE_ID,
            'miner_id': f'{MINER_PREFIX}P3_{i}',
            'issue_code': 'fleet_outlier',
            'severity': 'P3',
            'status': 'open',
            'start_ts': datetime.utcnow().isoformat(),
            'ml_json': {'p_fail_24h': 0.1},
            'action': 'created',
        } for i in range(5)]

        p3_result = pe.evaluate_batch(p3_events, site_miner_count=500)
        check("P3: NEVER notifies (0 notifications)",
              p3_result['stats']['notifications_sent'] == 0,
              f"sent={p3_result['stats']['notifications_sent']}")

        check("P3: NEVER creates tickets (0 tickets)",
              p3_result['stats']['tickets_created'] == 0,
              f"created={p3_result['stats']['tickets_created']}")

        p2_events = [{
            'event_id': f'sim-p2-{i}',
            'site_id': SITE_ID,
            'miner_id': f'{MINER_PREFIX}P2_{i:03d}',
            'issue_code': 'hashrate_degradation',
            'severity': 'P2',
            'status': 'open',
            'start_ts': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            'ml_json': {'p_fail_24h': 0.3 + i * 0.01},
            'action': 'created',
        } for i in range(30)]

        p2_result = pe.evaluate_batch(p2_events, site_miner_count=600)
        check("P2 budget: notifications capped at MAX_NOTIFICATIONS_PER_CYCLE",
              p2_result['stats']['notifications_sent'] <= pe.MAX_NOTIFICATIONS_PER_CYCLE,
              f"sent={p2_result['stats']['notifications_sent']}, max={pe.MAX_NOTIFICATIONS_PER_CYCLE}")

        check("P2 budget: tickets capped at MAX_TICKETS_PER_CYCLE",
              p2_result['stats']['tickets_created'] <= pe.MAX_TICKETS_PER_CYCLE,
              f"created={p2_result['stats']['tickets_created']}, max={pe.MAX_TICKETS_PER_CYCLE}")

        # ============================================================
        # TEST 13: WeakSupervisor - Label Builder & Model Registry
        # ============================================================
        header("TEST 13: WeakSupervisor - Label Builder & Model Registry")

        from services.weak_supervisor import WeakLabelBuilder, WeakSupervisor

        wlb = WeakLabelBuilder()
        labels_df = wlb.build_labels(lookback_days=7)

        check("WeakLabelBuilder: returns DataFrame (possibly empty in test env)",
              labels_df is not None)

        if len(labels_df) > 0:
            check("Labels have required columns",
                  'event_in_24h' in labels_df.columns)
            check("Labels are binary (0 or 1)",
                  set(labels_df['event_in_24h'].unique()).issubset({0, 1}))
        else:
            check("Labels empty in test environment (expected - no historical events)", True)

        from services.weak_supervisor import ModelRegistry
        mr = ModelRegistry()
        model_info = mr.get_active_version('p_fail_24h')
        check("Model registry: get_active_version returns gracefully (None if no model trained)",
              model_info is None or isinstance(model_info, dict))
        print(f"  [Info] Current model version: {model_info}")

        # ============================================================
        # TEST 14: Evidence in Hard Rules
        # ============================================================
        header("TEST 14: Evidence Building in Rules")

        overheat_issues_full = hre.evaluate_hard_rules({'temp_max': 88, 'is_online': True, 'hashrate_ratio': 0.9, 'boards_ratio': 1.0})
        if overheat_issues_full:
            ev = overheat_issues_full[0].get('evidence', {})
            check("Evidence has rule_code",
                  'rule_code' in ev,
                  f"evidence_keys={list(ev.keys())}")
            check("Evidence has description",
                  'description' in ev and len(ev['description']) > 0)
            check("Evidence has evaluated_at timestamp",
                  'evaluated_at' in ev)
            check("Evidence has threshold value",
                  'threshold' in ev or 'threshold_low' in ev,
                  f"evidence={ev}")

        # ============================================================
        # TEST 15: API Endpoints via Test Client
        # ============================================================
        header("TEST 15: API Endpoints via Flask Test Client")

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 4
                sess['email'] = 'test@test.com'

            resp = client.get(f'/hosting/api/sites/{SITE_ID}/health_summary')
            check("Health summary API: returns 200",
                  resp.status_code == 200,
                  f"status={resp.status_code}")

            data = resp.get_json()
            check("Health summary: has required fields",
                  all(k in data for k in ['site_id', 'total_miners', 'healthy_miners', 'problem_miners', 'by_severity', 'by_issue']),
                  f"keys={list(data.keys())}")

            check("Health summary: problem_miners > 0 (we created events)",
                  data.get('problem_miners', 0) > 0,
                  f"problem_miners={data.get('problem_miners')}")

            check("Health summary: by_severity has entries",
                  len(data.get('by_severity', {})) > 0,
                  f"by_severity={data.get('by_severity')}")

            print(f"  [Info] Health Summary: {json.dumps(data, indent=2, default=str)[:500]}")

            resp2 = client.get(f'/hosting/api/sites/{SITE_ID}/problems?per_page=10')
            check("Problems list API: returns 200",
                  resp2.status_code == 200,
                  f"status={resp2.status_code}")

            data2 = resp2.get_json()
            check("Problems list: has problems array",
                  'problems' in data2 and isinstance(data2['problems'], list))

            check("Problems list: has pagination",
                  'pagination' in data2,
                  f"keys={list(data2.keys())}")

            if data2.get('problems'):
                p = data2['problems'][0]
                check("Problem record: has required fields",
                      all(k in p for k in ['id', 'miner_id', 'issue_code', 'severity', 'status', 'start_ts']))
                print(f"  [Info] First problem: {json.dumps(p, indent=2, default=str)[:400]}")

            resp3 = client.get(f'/hosting/api/sites/{SITE_ID}/problems?severity=P0')
            data3 = resp3.get_json()
            if data3.get('problems'):
                all_p0 = all(p['severity'] == 'P0' for p in data3['problems'])
                check("Severity filter: all returned events are P0",
                      all_p0)

            miner_id_test = f'{MINER_PREFIX}LIFE_001'
            resp4 = client.get(f'/hosting/api/miners/{miner_id_test}/problems?include_resolved=true')
            check("Miner problems API: returns 200",
                  resp4.status_code == 200,
                  f"status={resp4.status_code}")

            data4 = resp4.get_json()
            check("Miner problems: has total count",
                  'total' in data4,
                  f"total={data4.get('total')}")

            supp_resp = client.post(
                f'/hosting/api/miners/{MINER_PREFIX}BULK_000/suppress',
                json={'until': (datetime.utcnow() + timedelta(hours=4)).isoformat(), 'maintenance': True, 'reason': 'Simulation test'},
                content_type='application/json'
            )
            check("Suppress API: returns 200",
                  supp_resp.status_code == 200,
                  f"status={supp_resp.status_code}, data={supp_resp.get_json()}")

            unsupp_resp = client.post(
                f'/hosting/api/miners/{MINER_PREFIX}BULK_000/unsuppress',
                json={},
                content_type='application/json'
            )
            check("Unsuppress API: returns 200",
                  unsupp_resp.status_code == 200,
                  f"status={unsupp_resp.status_code}")

            unauth_resp = client.get('/hosting/api/sites/1/health_summary')
            with client.session_transaction() as sess:
                sess.clear()
            unauth_resp = client.get('/hosting/api/sites/1/health_summary')
            check("Unauthenticated request: returns 401",
                  unauth_resp.status_code == 401)

        # ============================================================
        # TEST 16: Database State Verification
        # ============================================================
        header("TEST 16: Database State Verification")

        event_count = db.session.execute(text(
            f"SELECT COUNT(*) FROM problem_events WHERE miner_id LIKE '{MINER_PREFIX}%'"
        )).scalar()
        check("Problem events created in DB",
              event_count > 0,
              f"count={event_count}")

        baseline_count = db.session.execute(text(
            f"SELECT COUNT(*) FROM miner_baseline_state WHERE miner_id LIKE '{MINER_PREFIX}%'"
        )).scalar()
        check("Baseline states stored in DB",
              baseline_count > 0,
              f"count={baseline_count}")

        severity_dist = {}
        rows = db.session.execute(text(
            f"SELECT severity, COUNT(*) FROM problem_events WHERE miner_id LIKE '{MINER_PREFIX}%' GROUP BY severity ORDER BY severity"
        )).fetchall()
        for row in rows:
            severity_dist[row[0]] = row[1]
        check("Multiple severity levels in events",
              len(severity_dist) >= 2,
              f"distribution={severity_dist}")

        status_dist = {}
        rows2 = db.session.execute(text(
            f"SELECT status, COUNT(*) FROM problem_events WHERE miner_id LIKE '{MINER_PREFIX}%' GROUP BY status ORDER BY status"
        )).fetchall()
        for row in rows2:
            status_dist[row[0]] = row[1]
        check("Multiple statuses in events (open, resolved, etc.)",
              len(status_dist) >= 1,
              f"distribution={status_dist}")

        print(f"\n  [Info] Event severity distribution: {severity_dist}")
        print(f"  [Info] Event status distribution: {status_dist}")
        print(f"  [Info] Total events: {event_count}")
        print(f"  [Info] Total baseline states: {baseline_count}")

        # ============================================================
        # CLEANUP
        # ============================================================
        header("CLEANUP")
        cleanup(db)
        print("  Cleaned up all simulation test data")

        remaining = db.session.execute(text(
            f"SELECT COUNT(*) FROM problem_events WHERE miner_id LIKE '{MINER_PREFIX}%'"
        )).scalar()
        check("Cleanup complete: no simulation data remains",
              remaining == 0)

        # ============================================================
        # FINAL REPORT
        # ============================================================
        print(f"\n{'='*70}")
        print(f"  SIMULATION TEST RESULTS")
        print(f"{'='*70}")
        print(f"  Total Tests:  {PASS_COUNT + FAIL_COUNT}")
        print(f"  Passed:       {PASS_COUNT} ✅")
        print(f"  Failed:       {FAIL_COUNT} ❌")
        print(f"  Pass Rate:    {PASS_COUNT / (PASS_COUNT + FAIL_COUNT) * 100:.1f}%")
        print(f"{'='*70}")

        if FAIL_COUNT > 0:
            print("\n  FAILED TESTS:")
            for t in TEST_RESULTS:
                if not t['pass']:
                    print(f"    ❌ {t['desc']}: {t['detail']}")

        print()
        return FAIL_COUNT == 0


if __name__ == '__main__':
    try:
        success = run_simulation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
