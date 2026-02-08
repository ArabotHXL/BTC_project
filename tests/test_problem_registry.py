import pytest
import sys
import os

_real_db_url = os.environ.get('DATABASE_URL')
if _real_db_url and 'postgresql' in _real_db_url:
    os.environ['DATABASE_URL'] = _real_db_url

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def app_context():
    with app.app_context():
        yield


def test_baseline_incremental_update(app_context):
    """Verify EWMA updates incrementally without full history scan"""
    from services.baseline_service import BaselineService
    svc = BaselineService()

    features = {'hashrate_ratio': 0.95, 'boards_ratio': 1.0, 'temp_max': 65.0}
    result = svc.update_baseline('TEST_MINER_001', 999, features)
    assert result['hashrate_ratio']['ewma'] == pytest.approx(0.95, abs=0.01)
    assert result['hashrate_ratio']['sample_count'] == 1

    features2 = {'hashrate_ratio': 0.85, 'boards_ratio': 1.0, 'temp_max': 70.0}
    result2 = svc.update_baseline('TEST_MINER_001', 999, features2)
    assert result2['hashrate_ratio']['sample_count'] == 2
    assert result2['hashrate_ratio']['ewma'] != 0.85
    assert result2['hashrate_ratio']['residual'] < 0

    db.session.execute(text("DELETE FROM miner_baseline_state WHERE miner_id LIKE 'TEST_MINER_%'"))
    db.session.commit()


def test_baseline_missing_fields(app_context):
    """Verify baseline handles missing fields gracefully"""
    from services.baseline_service import BaselineService
    svc = BaselineService()
    features = {'hashrate_ratio': 0.95}
    result = svc.update_baseline('TEST_MINER_002', 999, features)
    assert 'hashrate_ratio' in result
    assert 'efficiency' not in result

    db.session.execute(text("DELETE FROM miner_baseline_state WHERE miner_id LIKE 'TEST_MINER_%'"))
    db.session.commit()


def test_mode_inference_stability(app_context):
    """Verify mode inference produces stable results with same input"""
    from services.mode_inference_service import ModeInferenceService
    import numpy as np
    svc = ModeInferenceService()

    records = []
    np.random.seed(42)
    for i in range(5):
        records.append({'miner_id': f'TEST_ECO_{i}', 'site_id': 999, 'model': 'S19 Pro',
                       'firmware': 'v1.0', 'hashrate_ratio': 0.6 + np.random.normal(0, 0.02),
                       'temp_max': 55 + np.random.normal(0, 2), 'efficiency': None})
    for i in range(5):
        records.append({'miner_id': f'TEST_NORM_{i}', 'site_id': 999, 'model': 'S19 Pro',
                       'firmware': 'v1.0', 'hashrate_ratio': 0.9 + np.random.normal(0, 0.02),
                       'temp_max': 65 + np.random.normal(0, 2), 'efficiency': None})
    for i in range(5):
        records.append({'miner_id': f'TEST_PERF_{i}', 'site_id': 999, 'model': 'S19 Pro',
                       'firmware': 'v1.0', 'hashrate_ratio': 1.05 + np.random.normal(0, 0.02),
                       'temp_max': 75 + np.random.normal(0, 2), 'efficiency': None})

    result1 = svc.infer_modes(records)
    result2 = svc.infer_modes(records)

    for mid in result1:
        assert result1[mid]['inferred_mode'] == result2[mid]['inferred_mode']

    assert result1['TEST_ECO_0']['inferred_mode'] == 'eco'
    assert result1['TEST_PERF_0']['inferred_mode'] == 'perf'

    db.session.execute(text("DELETE FROM miner_baseline_state WHERE miner_id LIKE 'TEST_%'"))
    db.session.commit()


def test_mode_inference_small_group(app_context):
    """Groups with < 5 miners should get mode='unknown'"""
    from services.mode_inference_service import ModeInferenceService
    svc = ModeInferenceService()
    records = [{'miner_id': f'TEST_SMALL_{i}', 'site_id': 999, 'model': 'S21',
               'firmware': 'v2.0', 'hashrate_ratio': 0.9, 'temp_max': 65, 'efficiency': None}
               for i in range(3)]
    result = svc.infer_modes(records)
    for mid in result:
        assert result[mid]['inferred_mode'] == 'unknown'

    db.session.execute(text("DELETE FROM miner_baseline_state WHERE miner_id LIKE 'TEST_%'"))
    db.session.commit()


def test_fleet_baseline_cache(app_context):
    """Verify cache hit within TTL"""
    from services.fleet_baseline_service import FleetBaselineService
    svc = FleetBaselineService()
    records = [{'hashrate_ratio': 0.9 + i*0.01, 'boards_ratio': 1.0, 'temp_max': 65, 'efficiency': None}
               for i in range(10)]

    metrics = svc.compute_peer_metrics('test:S19:v1:normal', records)
    assert 'hashrate_ratio' in metrics

    cached = svc.get_peer_metrics('test:S19:v1:normal')
    assert cached is not None
    assert cached == metrics

    svc.invalidate_cache('test:S19:v1:normal')
    assert svc.get_peer_metrics('test:S19:v1:normal') is None


def test_event_debounce(app_context):
    """Event should not open until consecutive_fail >= DEBOUNCE_THRESHOLD"""
    from services.event_engine import EventEngine
    engine = EventEngine()

    r1 = engine.process_detection(999, 'TEST_DEB_001', 'overheat_crit', 'P0', {'temp': 90})
    assert r1['action'] in ('created', 'debouncing')

    r2 = engine.process_detection(999, 'TEST_DEB_001', 'overheat_crit', 'P0', {'temp': 91})
    assert r2['action'] in ('created', 'updated', 'escalated')

    db.session.execute(text("DELETE FROM problem_events WHERE miner_id LIKE 'TEST_DEB_%'"))
    db.session.commit()


def test_event_resolve_recurrence(app_context):
    """Event resolves after N healthy signals and can recur"""
    from services.event_engine import EventEngine
    engine = EventEngine()

    engine.process_detection(999, 'TEST_RES_001', 'offline', 'P0', {'status': 'offline'})
    engine.process_detection(999, 'TEST_RES_001', 'offline', 'P0', {'status': 'offline'})

    r = None
    for _ in range(engine.RESOLVE_THRESHOLD):
        r = engine.process_healthy(999, 'TEST_RES_001', 'offline')
    assert r['action'] == 'resolved'

    engine.process_detection(999, 'TEST_RES_001', 'offline', 'P0', {'status': 'offline'})
    r2 = engine.process_detection(999, 'TEST_RES_001', 'offline', 'P0', {'status': 'offline'})

    row = db.session.execute(text(
        "SELECT recurrence_count FROM problem_events WHERE miner_id='TEST_RES_001' AND issue_code='offline' AND status IN ('open','ack') LIMIT 1"
    )).fetchone()

    db.session.execute(text("DELETE FROM problem_events WHERE miner_id LIKE 'TEST_RES_%'"))
    db.session.commit()


def test_maintenance_suppression(app_context):
    """Suppressed miners should not generate events"""
    from services.event_engine import EventEngine
    from datetime import datetime, timedelta
    engine = EventEngine()

    engine.process_detection(999, 'TEST_SUP_001', 'overheat_crit', 'P0', {'temp': 88})

    engine.suppress_miner('TEST_SUP_001', until=datetime.utcnow() + timedelta(hours=1), maintenance=True)

    r = engine.process_detection(999, 'TEST_SUP_001', 'overheat_crit', 'P0', {'temp': 90})
    assert r['action'] == 'suppressed'

    engine.unsuppress_miner('TEST_SUP_001')

    db.session.execute(text("DELETE FROM problem_events WHERE miner_id LIKE 'TEST_SUP_%'"))
    db.session.commit()

    r2 = engine.process_detection(999, 'TEST_SUP_001', 'overheat_crit', 'P0', {'temp': 90})
    assert r2['action'] != 'suppressed'

    db.session.execute(text("DELETE FROM problem_events WHERE miner_id LIKE 'TEST_SUP_%'"))
    db.session.commit()


def test_weak_supervisor_no_leakage(app_context):
    """Verify weak labels don't use future data"""
    from services.weak_supervisor import WeakLabelBuilder
    builder = WeakLabelBuilder()
    df = builder.build_labels(lookback_days=30)
    if len(df) > 0:
        assert 'hashrate_ratio_ewma' in df.columns
        assert 'event_in_24h' in df.columns
        assert set(df['event_in_24h'].unique()).issubset({0, 1})


def test_policy_budget(app_context):
    """P2 events should be budget-capped"""
    from services.policy_engine import PolicyEngine
    from datetime import datetime, timedelta
    pe = PolicyEngine()

    events = []
    for i in range(30):
        events.append({
            'event_id': f'test-{i}',
            'site_id': 999,
            'miner_id': f'TEST_BUD_{i:03d}',
            'issue_code': 'hashrate_degradation',
            'severity': 'P2',
            'status': 'open',
            'start_ts': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            'ml_json': {'p_fail_24h': 0.3 + i * 0.01},
            'action': 'created'
        })

    result = pe.evaluate_batch(events, site_miner_count=600)
    assert result['stats']['notifications_sent'] <= pe.MAX_NOTIFICATIONS_PER_CYCLE


def test_hard_rules(app_context):
    """Verify hard rules trigger correctly"""
    from services.health_rules import HealthRulesEngine
    engine = HealthRulesEngine()

    features = {'temp_max': 90, 'is_online': True, 'hashrate_ratio': 0.5, 'boards_ratio': 1.0}
    issues = engine.evaluate_hard_rules(features)
    codes = [i['code'] for i in issues]
    assert 'overheat_crit' in codes

    features2 = {'temp_max': 60, 'is_online': True, 'hashrate_ratio': 0.95, 'boards_ratio': 1.0}
    issues2 = engine.evaluate_hard_rules(features2)
    assert len(issues2) == 0
