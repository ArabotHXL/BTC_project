#!/usr/bin/env python3
"""
SLO阈值配置测试
验证环境变量能正确配置告警阈值
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['ALERT_P95_TTR_WARNING'] = '3000'
os.environ['ALERT_P95_TTR_CRITICAL'] = '8000'
os.environ['ALERT_SUCCESS_RATE_WARNING'] = '95.0'
os.environ['ALERT_SUCCESS_RATE_CRITICAL'] = '90.0'

import importlib
from intelligence.monitoring import alert_config
importlib.reload(alert_config)
from intelligence.monitoring.alert_config import AlertThresholds

print("=== SLO Threshold Configuration Test ===\n")

print("1. Verifying threshold configuration from environment variables:")
assert AlertThresholds.P95_TTR_WARNING == 3000, f"Expected 3000, got {AlertThresholds.P95_TTR_WARNING}"
assert AlertThresholds.P95_TTR_CRITICAL == 8000, f"Expected 8000, got {AlertThresholds.P95_TTR_CRITICAL}"
assert AlertThresholds.SUCCESS_RATE_WARNING == 95.0, f"Expected 95.0, got {AlertThresholds.SUCCESS_RATE_WARNING}"
assert AlertThresholds.SUCCESS_RATE_CRITICAL == 90.0, f"Expected 90.0, got {AlertThresholds.SUCCESS_RATE_CRITICAL}"
print("✓ All thresholds correctly configured from environment variables")

from intelligence.monitoring.slo_tracker import SLOMetrics

print("\n2. Testing SLO metrics with custom thresholds:")
metrics = SLOMetrics()

for i in range(10):
    metrics.record_ttr(3500)
    metrics.record_attempt(True)

compliance = metrics.check_slo_compliance()

assert len(compliance['alerts']) == 1, f"Expected 1 alert, got {len(compliance['alerts'])}"
assert compliance['alerts'][0]['severity'] == 'warning', "Expected WARNING severity"
assert compliance['alerts'][0]['metric'] == 'p95_ttr', "Expected p95_ttr metric"
assert '3000ms' in compliance['alerts'][0]['threshold'], "Threshold should be 3000ms from env var"
print(f"✓ Alert generated: {compliance['alerts'][0]['message']}")

assert 'thresholds' in compliance, "Response should include thresholds"
assert compliance['thresholds']['p95_ttr_warning_ms'] == 3000
print(f"✓ Current thresholds: {compliance['thresholds']}")

print("\n✅ All SLO threshold tests passed!")
print("Environment variables correctly configure alert thresholds.")
