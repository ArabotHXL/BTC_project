# Problem Registry & Fleet Anomaly Detection System
# 问题注册表与矿机健康检测系统

---

## Table of Contents / 目录

1. [System Overview / 系统概述](#1-system-overview)
2. [Architecture / 架构设计](#2-architecture)
3. [Data Pipeline / 数据管线](#3-data-pipeline)
4. [Database Schema / 数据库结构](#4-database-schema)
5. [Service Components / 服务组件](#5-service-components)
   - 5.1 [BaselineService](#51-baselineservice)
   - 5.2 [ModeInferenceService](#52-modeinferenceservice)
   - 5.3 [FleetBaselineService](#53-fleetbaselineservice)
   - 5.4 [HealthRulesEngine](#54-healthrulesengine)
   - 5.5 [EventEngine](#55-eventengine)
   - 5.6 [DiagnosisFusion](#56-diagnosisfusion)
   - 5.7 [WeakSupervisor (Predictive Maintenance)](#57-weaksupervisor)
   - 5.8 [PolicyEngine](#58-policyengine)
6. [Health Rules Reference / 规则参考](#6-health-rules-reference)
7. [API Reference / API 接口文档](#7-api-reference)
8. [Event Lifecycle / 事件生命周期](#8-event-lifecycle)
9. [Testing / 测试覆盖](#9-testing)
10. [Configuration / 配置参数](#10-configuration)

---

## 1. System Overview

The Problem Registry is a centralized system for detecting, tracking, and resolving health issues across a fleet of Bitcoin mining machines. It combines real-time rule-based detection with statistical anomaly analysis and machine learning to provide:

- **Real-time health monitoring** — Hard rules catch critical failures immediately (overheating, offline, zero hashrate)
- **Trend-based anomaly detection** — EWMA baselines detect gradual degradation invisible to static thresholds
- **Fleet-level peer comparison** — Robust z-scores identify outliers relative to similar miners
- **Predictive maintenance** — XGBoost model predicts 24-hour failure probability
- **Intelligent event management** — Debounce, deduplication, cooldown, and maintenance suppression prevent alert fatigue
- **Budgeted notifications** — Policy engine caps notifications/tickets per cycle with severity-based prioritization

### 系统概述

问题注册表是一个集中化系统，用于检测、跟踪和解决比特币矿机群的健康问题。它结合了实时规则检测、统计异常分析和机器学习预测：

- **实时健康监控** — 硬规则立即捕获关键故障（过热、离线、零算力）
- **趋势异常检测** — EWMA 基线检测静态阈值无法发现的渐进劣化
- **矿场级对等比较** — 稳健 Z 分数识别相对于同型矿机的异常值
- **预测性维护** — XGBoost 模型预测 24 小时内故障概率
- **智能事件管理** — 去抖、去重、冷却期和维护静默防止告警疲劳
- **预算化通知** — 策略引擎按严重性优先级限制每周期通知/工单数量

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FeatureStoreJob (5min cron)               │
│  APScheduler → runs every 5 minutes                         │
└────┬────────────────────────────────────────────────────┬────┘
     │                                                    │
     ▼                                                    ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────────────┐
│ Telemetry   │───▶│  Feature     │───▶│  BaselineService     │
│ Live Data   │    │  Extraction  │    │  (EWMA per miner)    │
└─────────────┘    └──────┬───────┘    └──────────┬───────────┘
                          │                       │
                          ▼                       ▼
                   ┌──────────────┐    ┌──────────────────────┐
                   │ ModeInference│    │  FleetBaseline       │
                   │ (KMeans)     │    │  (Peer Z-Scores)     │
                   └──────┬───────┘    └──────────┬───────────┘
                          │                       │
                          └───────────┬───────────┘
                                      ▼
                          ┌──────────────────────┐
                          │  HealthRulesEngine    │
                          │  Hard Rules (P0/P1)   │
                          │  Soft Rules (P2/P3)   │
                          └──────────┬───────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │ EventEngine  │ │ Diagnosis    │ │ WeakSuper-   │
           │ (Lifecycle)  │ │ Fusion       │ │ visor (ML)   │
           └──────┬───────┘ └──────────────┘ └──────────────┘
                  │
                  ▼
           ┌──────────────┐
           │ PolicyEngine │
           │ (Budget &    │
           │  Dispatch)   │
           └──────┬───────┘
                  │
          ┌───────┴───────┐
          ▼               ▼
    Notifications      Tickets
```

### File Structure / 文件结构

```
services/
├── baseline_service.py          # EWMA per-miner baselines
├── mode_inference_service.py    # KMeans operational mode clustering
├── fleet_baseline_service.py    # Peer group statistics & robust z-scores
├── health_rules.py              # Hard/soft rules + FeatureStoreJob pipeline
├── event_engine.py              # Event lifecycle (debounce/resolve/suppress)
├── diagnosis_fusion.py          # Health object builder & peer hypothesis
├── weak_supervisor.py           # Predictive maintenance (XGBoost)
├── policy_engine.py             # Notification/ticket budget & dispatch

routes/
├── problem_registry_routes.py   # REST API endpoints (5 endpoints)

scripts/
├── simulation_test.py           # Comprehensive test (83 assertions)

tests/
├── test_problem_registry.py     # Unit tests
```

---

## 3. Data Pipeline

The **FeatureStoreJob** runs every 5 minutes via APScheduler and orchestrates the entire pipeline:

```
Step 1: Fetch Live Data
    └─▶ TelemetryService.get_live() → all miners from miner_telemetry_live

Step 2: Feature Extraction
    └─▶ BaselineService.extract_features() per record
        Features: hashrate_ratio, boards_ratio, temp_max, efficiency,
                  fan_speed_min, is_online

Step 3: Baseline Update
    └─▶ BaselineService.bulk_update() → EWMA + variance + residuals
        Stored in: miner_baseline_state table

Step 4: Mode Inference
    └─▶ ModeInferenceService.infer_modes() → eco/normal/perf
        Algorithm: KMeans (k=3) on hashrate_ratio × temp_max

Step 5: Fleet Baselines
    └─▶ FleetBaselineService.compute_all_groups()
        Groups: site_id:model:firmware:mode
        Metrics: median, MAD, percentiles (p10/p25/p75/p90)
    └─▶ compute_robust_z() per miner → fleet_z_hashrate

Step 6: Rule Evaluation
    └─▶ HealthRulesEngine.evaluate_all(features, baselines)
        Hard rules: immediate threshold checks → P0/P1
        Soft rules: baseline z-scores + fleet z-scores → P2/P3
    └─▶ Generate detections[] and healthy[] signals

Step 7: Event Processing
    └─▶ EventEngine.bulk_process(detections, healthy)
        Debounce → Open → Resolve → Recurrence lifecycle

Step 8: Policy Dispatch (triggered downstream)
    └─▶ PolicyEngine.evaluate_batch(events)
        Budget-capped notifications and ticket creation
```

### 数据管线说明

FeatureStoreJob 每 5 分钟通过 APScheduler 运行一次，协调整个管线：

1. **获取实时数据** — 从 `miner_telemetry_live` 表读取所有矿机数据
2. **特征提取** — 计算 hashrate_ratio, boards_ratio, temp_max, efficiency 等
3. **基线更新** — EWMA 指数加权移动平均更新，存储到 `miner_baseline_state`
4. **模式推断** — KMeans 聚类判断矿机运行模式（节能/正常/性能）
5. **矿场基线** — 按 site:model:firmware:mode 分组计算中位数、MAD、百分位
6. **规则评估** — 硬规则检查即时阈值，软规则检查基线偏差
7. **事件处理** — 去抖、打开、解决、复发的完整生命周期
8. **策略分发** — 预算限制下的通知和工单创建

---

## 4. Database Schema

### `problem_events` — Event tracking

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NO | `gen_random_uuid()` | Primary key |
| `site_id` | INTEGER | NO | — | Site identifier |
| `miner_id` | VARCHAR | NO | — | Miner identifier |
| `issue_code` | VARCHAR | NO | — | Rule code (e.g., `overheat_crit`) |
| `severity` | VARCHAR | NO | — | `P0` / `P1` / `P2` / `P3` |
| `status` | VARCHAR | NO | `'open'` | `open` / `ack` / `in_progress` / `resolved` |
| `start_ts` | TIMESTAMP | NO | `now()` | When event first detected |
| `last_seen_ts` | TIMESTAMP | NO | `now()` | Most recent detection |
| `resolved_ts` | TIMESTAMP | YES | — | When event was resolved |
| `recurrence_count` | INTEGER | NO | `0` | Times event reopened |
| `consecutive_ok` | INTEGER | NO | `0` | Healthy signal counter |
| `consecutive_fail` | INTEGER | NO | `0` | Failed signal counter |
| `dedup_key` | VARCHAR | NO | — | `{miner_id}:{issue_code}` |
| `evidence_json` | JSONB | YES | `'[]'` | Array of evidence snapshots |
| `actions_json` | JSONB | YES | `'[]'` | Dispatched actions log |
| `peer_metrics_json` | JSONB | YES | `'{}'` | Fleet comparison data |
| `ml_json` | JSONB | YES | `'{}'` | ML prediction data |
| `suppress_until` | TIMESTAMP | YES | — | Suppression expiry |
| `maintenance_flag` | BOOLEAN | NO | `false` | Under maintenance? |
| `created_at` | TIMESTAMP | NO | `now()` | Record creation time |
| `updated_at` | TIMESTAMP | NO | `now()` | Last update time |

### `miner_baseline_state` — EWMA baselines

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | serial | Primary key |
| `miner_id` | VARCHAR | NO | — | Miner identifier |
| `site_id` | INTEGER | NO | — | Site identifier |
| `metric_name` | VARCHAR | NO | — | Feature name (e.g., `hashrate_ratio`) |
| `ewma_value` | DOUBLE | NO | `0` | Current EWMA estimate |
| `ewma_variance` | DOUBLE | NO | `0` | EWMA variance estimate |
| `sample_count` | INTEGER | NO | `0` | Total observations |
| `last_raw_value` | DOUBLE | YES | — | Most recent raw value |
| `last_residual` | DOUBLE | YES | — | `raw - ewma` before update |
| `inferred_mode` | VARCHAR | YES | `'unknown'` | Operational mode |
| `mode_confidence` | DOUBLE | YES | `0` | Mode confidence score |
| `updated_at` | TIMESTAMP | NO | `now()` | Last update time |

### `ml_model_registry` — Model versioning

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | serial | Primary key |
| `model_name` | VARCHAR | NO | — | Model identifier (e.g., `p_fail_24h`) |
| `version` | VARCHAR | NO | — | Semantic version |
| `model_type` | VARCHAR | NO | — | Algorithm type (e.g., `xgboost`) |
| `metrics_json` | JSONB | YES | `'{}'` | Training metrics (AUC, F1, etc.) |
| `model_path` | VARCHAR | YES | — | Serialized model file path |
| `is_active` | BOOLEAN | NO | `false` | Currently deployed? |
| `trained_at` | TIMESTAMP | NO | `now()` | Training timestamp |
| `sample_count` | INTEGER | YES | `0` | Training samples used |
| `feature_names` | JSONB | YES | `'[]'` | Feature column names |
| `created_at` | TIMESTAMP | NO | `now()` | Record creation time |

---

## 5. Service Components

### 5.1 BaselineService

**File:** `services/baseline_service.py`

Maintains per-miner EWMA (Exponentially Weighted Moving Average) baselines that track normal operating ranges without requiring historical data scans.

**Key Design Decisions:**
- **Never scans history** — Incremental EWMA updates only from current observation
- **Alpha = 0.1** — Slow adaptation preserves long-term trend signal
- **Z-score** = `(raw - ewma) / sqrt(variance)` — Detects deviations from individual miner norm
- **Residual** = `raw - ewma_before_update` — Shows direction and magnitude of change

**Features tracked:**

| Feature | Source | Description |
|---------|--------|-------------|
| `hashrate_ratio` | `hashrate.value / hashrate.expected_ths` | Actual vs. expected hashrate |
| `boards_ratio` | `boards_healthy / boards_total` | Board health fraction |
| `temp_max` | `temperature.max` | Maximum chip temperature (°C) |
| `efficiency` | `power / hashrate.value` | W/TH power efficiency |

**API:**

```python
bs = BaselineService()

# Extract features from telemetry
features = bs.extract_features(live_record)

# Update single miner baseline
result = bs.update_baseline(miner_id, site_id, features)
# Returns: {metric: {ewma, variance, sample_count, residual, z_score}}

# Bulk update all miners
baselines_map = bs.bulk_update(live_records)

# Get stored baselines
baselines = bs.get_baselines(miner_id)
```

---

### 5.2 ModeInferenceService

**File:** `services/mode_inference_service.py`

Infers miner operational modes (eco/normal/performance) using KMeans clustering on `hashrate_ratio × temp_max`.

**Key Design Decisions:**
- **k=3 clusters** — Maps to eco (low HR, low temp), normal, performance (high HR, high temp)
- **Min group size = 5** — Groups smaller than 5 miners → `mode=unknown`
- **Deterministic** — Same input always produces same output (fixed random seed)
- **Confidence** = inverse distance to cluster center (normalized 0.3–1.0)

**API:**

```python
mis = ModeInferenceService()
results = mis.infer_modes(feature_records)
# Returns: {miner_id: {inferred_mode, confidence, group_key}}
# Modes: 'eco', 'normal', 'perf', 'unknown'
```

---

### 5.3 FleetBaselineService

**File:** `services/fleet_baseline_service.py`

Computes peer group statistics to detect outliers relative to miners of the same model, firmware, and operational mode.

**Key Design Decisions:**
- **Peer groups** = `site_id:model:firmware:inferred_mode`
- **Robust z-score** = `(value - median) / (MAD * 1.4826)` — Resistant to outliers unlike mean/stddev
- **In-memory cache** with 300-second TTL and thread-safe operations
- **MAD floor** = 0.001 — Prevents division by zero for uniform groups

**Metrics computed per group:**

| Metric | Description |
|--------|-------------|
| `median` | 50th percentile |
| `mad` | Median Absolute Deviation |
| `p10, p25, p75, p90` | Percentile values |
| `count` | Group size |
| `min, max` | Range |

**API:**

```python
fbs = FleetBaselineService()

# Compute metrics for all groups
fbs.compute_all_groups(all_features)

# Get cached peer metrics
metrics = fbs.get_peer_metrics(group_key)

# Compute robust z-score for a single value
z = fbs.compute_robust_z(value, group_key, metric_name)

# Build peer metrics JSON for event enrichment
peer_json = fbs.build_peer_metrics_json(features, group_key)

# Invalidate cache
fbs.invalidate_cache(group_key)
```

---

### 5.4 HealthRulesEngine

**File:** `services/health_rules.py`

Evaluates predefined health rules against miner features and baselines. Rules are divided into two categories:

| Category | Severity | Input | Detection Speed |
|----------|----------|-------|-----------------|
| **Hard Rules** | P0, P1 | Raw features only | Immediate |
| **Soft Rules** | P2, P3 | Features + baselines | Requires history |

**Cold-start guard:** Soft rules require `sample_count >= 6` to prevent false positives on newly tracked miners.

See [Section 6: Health Rules Reference](#6-health-rules-reference) for the complete rule catalog.

**API:**

```python
hre = HealthRulesEngine()

# Evaluate hard rules (instant threshold checks)
hard_issues = hre.evaluate_hard_rules(features)

# Evaluate soft rules (baseline-dependent)
soft_issues = hre.evaluate_soft_rules(features, baselines)

# Evaluate all rules
all_issues = hre.evaluate_all(features, baselines)
# Returns: [{code, severity, evidence}]
```

---

### 5.5 EventEngine

**File:** `services/event_engine.py`

Manages the complete lifecycle of problem events with built-in protections against alert fatigue.

**Key Design Decisions:**
- **Debounce N=2** — Issue must be detected 2 consecutive times before opening an event
- **Resolve M=3** — Issue must be absent 3 consecutive times before resolving
- **Cooldown 24h** — After resolution, same issue won't reopen for 24 hours (increments `recurrence_count` instead)
- **Dedup key** = `{miner_id}:{issue_code}` — One active event per miner per issue type
- **Severity escalation** — If a new detection has higher severity, the event is upgraded

**Event States:**

```
                 ┌──── suppress ────┐
                 ▼                  │
[detected] ──▶ debounce ──▶ open ──┤──▶ resolved ──▶ (cooldown) ──▶ recurrence
                  (N=2)       │    │      (M=3)        (24h)
                              │    │
                              └────┘
                          severity escalation
```

**API:**

```python
ee = EventEngine()

# Process a single detection
result = ee.process_detection(site_id, miner_id, issue_code, severity, evidence)
# Returns: {action: created|updated|debouncing|suppressed|escalated, event_id}

# Process a healthy signal
result = ee.process_healthy(site_id, miner_id, issue_code)
# Returns: {action: resolved|counting, consecutive_ok}

# Bulk process
summary = ee.bulk_process(detections_list, healthy_list)
# Returns: {total_processed, created, updated, resolved, suppressed, ...}

# Maintenance suppression
ee.suppress_miner(miner_id, until=datetime, maintenance=True)
ee.unsuppress_miner(miner_id)
```

---

### 5.6 DiagnosisFusion

**File:** `services/diagnosis_fusion.py`

Stateless service that integrates fleet-level peer analysis, ML predictions, and rule-based detections into unified health assessments.

**Two main outputs:**

#### Health Object

```json
{
  "site_id": 1,
  "miner_id": "S19PRO-12345",
  "health_state": "P1",
  "issues": [
    {"issue_code": "overheat_warn", "severity": "P1", "evidence": {...}},
    {"issue_code": "hashrate_degradation", "severity": "P2", "evidence": {...}}
  ],
  "p_fail_24h": 0.78,
  "assessed_at": "2026-02-08T12:00:00Z"
}
```

#### Peer Hypothesis

```json
{
  "hypothesis_id": "peer_outlier_risk",
  "risk_level": "P1",
  "evidence": [
    {"metric": "hashrate_ratio", "value": 0.60, "group_median": 0.92, "robust_z": -4.5},
    {"metric": "temp_max", "value": 82, "group_median": 65, "robust_z": 3.2}
  ],
  "recommended_actions": ["inspect_boards", "check_cooling"],
  "ml_context": {"p_fail_24h": 0.78, "top_features": [...]}
}
```

**API:**

```python
df = DiagnosisFusion()

# Build health object
health = df.build_health_object(site_id, miner_id, issues, p_fail_24h, last_seen_ts)

# Create peer hypothesis
hypothesis = df.create_peer_hypothesis(miner_id, peer_metrics_json, ml_json, baselines)

# Full assessment (rules + peer + ML combined)
assessment = df.assess_miner(site_id, miner_id, features, baselines, peer_metrics_json, ml_json)
```

---

### 5.7 WeakSupervisor

**File:** `services/weak_supervisor.py`

Predictive maintenance system using weakly-supervised learning to predict 24-hour failure probability.

**Architecture:**

```
WeakLabelBuilder → Build feature+label dataset (no time leakage)
    ↓
ModelRegistry → Version control for trained models
    ↓
WeakSupervisor → Train XGBoost model → Predict p_fail_24h
```

**Key Design Decisions:**
- **Weak labels** — Derived from operational signals (problem events, offline periods) rather than manual annotation
- **No time leakage** — Features come from baseline state at time T, labels from events in T to T+24h
- **XGBoost classifier** — Binary classification (will fail in 24h: yes/no)
- **Model registry** — Version control with `is_active` flag for zero-downtime model updates

**Feature set (10 features):**

| Feature | Source |
|---------|--------|
| `hashrate_ratio_ewma` | BaselineService |
| `hashrate_ratio_var` | BaselineService |
| `boards_ratio_ewma` | BaselineService |
| `boards_ratio_var` | BaselineService |
| `temp_max_ewma` | BaselineService |
| `temp_max_var` | BaselineService |
| `efficiency_ewma` | BaselineService |
| `efficiency_var` | BaselineService |
| `sample_count` | BaselineService |
| `mode_encoded` | ModeInferenceService |

**API:**

```python
ws = WeakSupervisor()

# Train a new model
result = ws.train()
# Returns: {model_name, version, metrics: {auc, f1, accuracy, ...}}

# Predict for a batch of miners
predictions = ws.predict(features_list)
# Returns: {miner_id: {p_fail_24h, risk_level, top_features}}

# Build ML JSON for event enrichment
ml_json = ws.build_ml_json(miner_id, prediction_result)
```

---

### 5.8 PolicyEngine

**File:** `services/policy_engine.py`

Controls notification and ticket dispatch with per-cycle budget limits and severity-based prioritization.

**Dispatch Rules:**

| Severity | Notification | Ticket | Condition |
|----------|-------------|--------|-----------|
| **P0** | ALWAYS | ALWAYS | Immediate dispatch, no budget consumed |
| **P1** | ALWAYS | ALWAYS | Immediate dispatch, no budget consumed |
| **P2** | TopK by score | If `p_fail_24h > 0.5` AND duration > 30min | Subject to budget limits |
| **P3** | NEVER | NEVER | Log only |

**Budget Limits (per cycle):**

| Resource | Limit |
|----------|-------|
| Notifications | 20 per cycle |
| Tickets | 5 per cycle |

**Scoring formula for P2 prioritization:**

```
score = severity_weight × 0.4 + p_fail_24h × 0.3 + duration_hours × 0.2 + recurrence × 0.1
```

**API:**

```python
pe = PolicyEngine()

# Evaluate a batch of events
result = pe.evaluate_batch(events, site_miner_count=500)
# Returns: {
#   stats: {notifications_sent, tickets_created, suppressed, skipped},
#   actions: [{event_id, action_type, ...}]
# }
```

---

## 6. Health Rules Reference

### Hard Rules (P0 / P1) — Immediate Threshold Checks

| Code | Severity | Condition | Description |
|------|----------|-----------|-------------|
| `overheat_crit` | **P0** | `temp_max >= 85°C` | Critical overheating, immediate shutdown risk |
| `offline` | **P0** | `is_online == False` | Miner completely offline |
| `hashrate_zero` | **P1** | `hashrate_ratio <= 0.01 AND is_online == True` | Online but producing nothing |
| `boards_dead` | **P1** | `boards_ratio <= 0.5` | More than half of hash boards dead |
| `fan_zero` | **P1** | `fan_speed_min == 0 AND is_online == True` | Fan failure while running |
| `overheat_warn` | **P1** | `75 <= temp_max < 85°C` | Approaching critical temperature |

### Soft Rules (P2 / P3) — Baseline-Dependent Analysis

| Code | Severity | Condition | Cold-Start Guard |
|------|----------|-----------|-----------------|
| `hashrate_degradation` | **P2** | EWMA z-score < -2.0 | `sample_count >= 6` |
| `efficiency_degradation` | **P2** | EWMA z-score > 2.0 | `sample_count >= 6` |
| `temp_anomaly` | **P2** | EWMA z-score > 2.5 | No minimum |
| `fleet_outlier` | **P3** | Fleet robust z-score > 3.0 | No minimum |
| `boards_degrading` | **P3** | EWMA residual < -0.1 | `sample_count >= 6` |

### Evidence Structure

Every triggered rule generates an evidence object:

```json
{
  "rule_code": "overheat_crit",
  "description": "Temperature 92°C exceeds critical threshold 85°C",
  "temp_max": 92,
  "threshold": 85,
  "evaluated_at": "2026-02-08T12:00:00Z"
}
```

---

## 7. API Reference

All endpoints require session authentication. Unauthenticated requests return `401 Unauthorized`.

### GET `/hosting/api/sites/<site_id>/health_summary`

Returns an aggregated health overview for an entire site.

**Response:**

```json
{
  "site_id": 1,
  "total_miners": 800,
  "healthy_miners": 750,
  "problem_miners": 50,
  "by_severity": {
    "P0": 2,
    "P1": 8,
    "P2": 30,
    "P3": 10
  },
  "by_issue": {
    "overheat_crit": 2,
    "hashrate_degradation": 15,
    "offline": 5
  },
  "top_risks": [
    {
      "miner_id": "S19PRO-12345",
      "issue_code": "overheat_crit",
      "severity": "P0",
      "p_fail_24h": 0.92,
      "start_ts": "2026-02-08T10:00:00"
    }
  ],
  "last_scan_ts": "2026-02-08T12:00:00"
}
```

---

### GET `/hosting/api/sites/<site_id>/problems`

Returns paginated list of problem events with filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `severity` | string | — | Filter: `P0`, `P1`, `P2`, `P3` |
| `issue_code` | string | — | Filter by rule code |
| `status` | string | — | Filter: `open`, `ack`, `in_progress`, `resolved` |
| `model` | string | — | Filter by miner model |
| `firmware` | string | — | Filter by firmware version |
| `page` | integer | `1` | Page number |
| `per_page` | integer | `50` | Items per page (max 500) |

**Response:**

```json
{
  "problems": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "site_id": 1,
      "miner_id": "S19PRO-12345",
      "issue_code": "overheat_crit",
      "severity": "P0",
      "status": "open",
      "start_ts": "2026-02-08T10:00:00",
      "last_seen_ts": "2026-02-08T12:00:00",
      "recurrence_count": 0,
      "evidence_json": [...],
      "ml_json": {"p_fail_24h": 0.92}
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 120,
    "pages": 3
  }
}
```

---

### GET `/hosting/api/miners/<miner_id>/problems`

Returns all problems for a specific miner.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | `open` | Filter by status |
| `include_resolved` | boolean | `false` | Include resolved events |

**Response:**

```json
{
  "miner_id": "S19PRO-12345",
  "problems": [...],
  "total": 3
}
```

---

### POST `/hosting/api/miners/<miner_id>/suppress`

Set maintenance suppression for a miner. All new detections will be suppressed until the specified time.

**Request Body:**

```json
{
  "until": "2026-02-09T12:00:00",
  "maintenance": true,
  "reason": "Scheduled maintenance"
}
```

**Response:**

```json
{
  "success": true,
  "miner_id": "S19PRO-12345",
  "message": "Miner suppressed",
  "until": "2026-02-09T12:00:00",
  "maintenance": true,
  "reason": "Scheduled maintenance"
}
```

---

### POST `/hosting/api/miners/<miner_id>/unsuppress`

Remove maintenance suppression for a miner.

**Request Body:** `{}` (empty)

**Response:**

```json
{
  "success": true,
  "miner_id": "S19PRO-12345",
  "message": "Miner unsuppressed"
}
```

---

## 8. Event Lifecycle

### State Transitions

```
[Initial Detection]
    │
    ├─ Miner suppressed? ──▶ action: "suppressed" (no event created)
    │
    ├─ Existing open event?
    │   ├─ YES: Update last_seen_ts, increment consecutive_fail
    │   │       Higher severity? → Escalate
    │   │       Return action: "updated" or "escalated"
    │   │
    │   └─ NO: Recently resolved (within cooldown)?
    │           ├─ YES: Increment recurrence_count, return "cooldown"
    │           └─ NO: Create new event with consecutive_fail=1
    │                   consecutive_fail >= DEBOUNCE_THRESHOLD?
    │                   ├─ YES: status="open", action="created"
    │                   └─ NO: status="ack", action="debouncing"

[Healthy Signal]
    │
    ├─ No active event? ──▶ action: "no_event" (nothing to do)
    │
    └─ Active event found:
        Increment consecutive_ok, reset consecutive_fail
        consecutive_ok >= RESOLVE_THRESHOLD?
        ├─ YES: status="resolved", resolved_ts=now(), action="resolved"
        └─ NO: action="counting"
```

### Deduplication

Events are deduplicated by the key `{miner_id}:{issue_code}`. Only one active event (status != `resolved`) can exist per dedup key at any time. This prevents duplicate alerts for the same ongoing issue.

### Maintenance Suppression

When a miner is suppressed:
- All new detections for that miner return `action: "suppressed"`
- Existing open events remain unchanged (they are not auto-resolved)
- Suppression expires automatically at `suppress_until` timestamp
- Manual unsuppression removes suppression immediately

---

## 9. Testing

### Simulation Test (`scripts/simulation_test.py`)

A comprehensive end-to-end test covering all 10 services with **83 assertions across 16 test groups**.

| Test Group | Assertions | Description |
|------------|-----------|-------------|
| 1. BaselineService EWMA | 9 | Incremental updates, convergence, z-scores |
| 2. Baseline graceful degradation | 2 | Missing fields, all-None values |
| 3. ModeInference KMeans | 5 | eco/normal/perf clustering, determinism, confidence |
| 4. FleetBaseline peer metrics | 7 | Median, percentiles, MAD, cache, robust z-score |
| 5. Hard rules (P0/P1) | 5 | Overheat, offline, zero hashrate, dead boards, normal |
| 6. Soft rules (P2/P3) | 3 | Degradation, cold-start guard, fleet outlier |
| 7. Event lifecycle | 4 | Debounce → open → resolve → recurrence |
| 8. Maintenance suppression | 2 | Suppress + unsuppress |
| 9. Severity escalation | 2 | P1 → P0 upgrade verified in DB |
| 10. Bulk process | 2 | Batch event handling |
| 11. DiagnosisFusion | 9 | Health object, peer hypothesis, full assessment |
| 12. PolicyEngine budget | 6 | P0 always, P3 never, P2 budget cap |
| 13. WeakSupervisor | 4 | Label builder, model registry |
| 14. Evidence building | 4 | Rule code, description, timestamp, threshold |
| 15. API endpoints | 13 | Health summary, problems, filter, suppress, auth |
| 16. DB state verification | 5 | Event counts, severity distribution, cleanup |

**Run the test:**

```bash
python scripts/simulation_test.py
```

**Test isolation:** Uses `site_id=998` and `SIM_TEST_` prefix for all test miners. Automatically cleans up all test data after completion.

---

## 10. Configuration

### EventEngine Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DEBOUNCE_THRESHOLD` | `2` | Consecutive detections before opening event |
| `RESOLVE_THRESHOLD` | `3` | Consecutive healthy signals before resolving |
| `COOLDOWN_HOURS` | `24` | Hours before same issue can reopen |

### BaselineService Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ALPHA` | `0.1` | EWMA smoothing factor (lower = slower adaptation) |
| Tracked metrics | 4 | `hashrate_ratio`, `boards_ratio`, `temp_max`, `efficiency` |

### FleetBaselineService Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CACHE_TTL` | `300s` | Peer metrics cache lifetime |
| `MAD_FLOOR` | `0.001` | Minimum MAD to prevent division by zero |
| Grouping | — | `site_id:model:firmware:inferred_mode` |

### PolicyEngine Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_NOTIFICATIONS_PER_CYCLE` | `20` | Max notifications per evaluation cycle |
| `MAX_TICKETS_PER_CYCLE` | `5` | Max tickets per evaluation cycle |
| `P2_DURATION_GATE_MINUTES` | `30` | P2 events must be open this long for tickets |
| `P2_PFAIL_TICKET_THRESHOLD` | `0.5` | P2 events need `p_fail_24h > 0.5` for tickets |

### ModeInferenceService Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `K` | `3` | Number of clusters (eco/normal/perf) |
| `MIN_GROUP_SIZE` | `5` | Groups smaller than this → `mode=unknown` |
| Features used | 2 | `hashrate_ratio`, `temp_max` |

### WeakSupervisor Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Model type | XGBoost | Binary classifier |
| Features | 10 | See [Section 5.7](#57-weaksupervisor) |
| Label window | 24h | Predicts failure in next 24 hours |
| Lookback | 30 days | Default training data window |
