# Skills Framework API Guide / 技能框架 API 指南

## Overview / 概述

The Skills Framework is a unified capability plugin system for HashInsight Enterprise. It provides standardized tool interfaces for AI closed-loop automation and human operators, with built-in RBAC, audit trail, rate limiting, and feature flags.

技能框架是 HashInsight Enterprise 的统一能力插件系统。它为 AI 闭环自动化和人工操作员提供标准化的工具接口，内置 RBAC 权限控制、审计追踪、限流和功能开关。

---

## Table of Contents / 目录

1. [Authentication / 认证](#authentication)
2. [API Endpoints / API 接口](#api-endpoints)
3. [Available Skills / 可用技能](#available-skills)
   - [telemetry_snapshot / 遥测快照](#1-telemetry_snapshot--遥测快照)
   - [alert_triage / 告警聚合分级](#2-alert_triage--告警聚合分级)
   - [rca_quick_diagnose / 快速根因诊断](#3-rca_quick_diagnose--快速根因诊断)
   - [ticket_draft / 工单草拟](#4-ticket_draft--工单草拟)
   - [curtailment_dry_run / 限电预演](#5-curtailment_dry_run--限电预演)
4. [RBAC Permissions / 权限矩阵](#rbac-permissions)
5. [Response Format / 响应格式](#response-format)
6. [Error Codes / 错误码](#error-codes)
7. [Feature Flags / 功能开关](#feature-flags)
8. [Rate Limiting / 限流](#rate-limiting)

---

## Authentication

All Skills API endpoints require authentication. Three methods are supported:

所有技能 API 接口都需要认证。支持以下三种方式：

### 1. API Key (Header)

```bash
curl -H "X-API-Key: YOUR_API_KEY" https://your-domain/api/skills
```

### 2. Session Cookie (Browser Login)

After logging in through the web UI, session cookies are sent automatically.

通过 Web UI 登录后，会话 Cookie 自动发送。

### 3. Internal Auth Middleware (g.auth)

Used by internal services and the AI closed-loop system.

内部服务和 AI 闭环系统使用的内部认证中间件。

---

## API Endpoints

### `GET /api/skills` — List Available Skills / 列出可用技能

Returns all skills the current user has permission to run, filtered by role.

返回当前用户有权限运行的所有技能（按角色过滤）。

**Request:**
```bash
curl -H "X-API-Key: YOUR_API_KEY" https://your-domain/api/skills
```

**Response:**
```json
{
  "ok": true,
  "count": 5,
  "skills": [
    {
      "id": "telemetry_snapshot",
      "name": "Telemetry Snapshot",
      "name_zh": "遥测快照",
      "desc": "Fetch live telemetry and recent history for a miner...",
      "desc_zh": "获取矿机实时遥测和近期历史数据...",
      "required_permissions": ["skills:run:telemetry"],
      "input_schema": { ... },
      "output_fields": ["current", "window_stats", "anomalies"],
      "version": "1.0",
      "tags": ["telemetry", "snapshot", "P0"]
    }
  ]
}
```

---

### `GET /api/skills/<skill_id>` — Get Skill Spec / 获取技能详情

Returns the full specification of a single skill, including its input schema.

返回单个技能的完整规格说明，包含输入参数模式。

**Request:**
```bash
curl -H "X-API-Key: YOUR_API_KEY" https://your-domain/api/skills/telemetry_snapshot
```

**Response:**
```json
{
  "ok": true,
  "skill": {
    "id": "telemetry_snapshot",
    "name": "Telemetry Snapshot",
    "name_zh": "遥测快照",
    "input_schema": {
      "required": ["miner_id"],
      "properties": {
        "miner_id": { "type": "string" },
        "site_id": { "type": "integer" },
        "window_min": { "type": "integer", "default": 10 }
      }
    },
    ...
  }
}
```

---

### `POST /api/skills/<skill_id>/run` — Execute a Skill / 执行技能

Runs a skill with the provided input parameters. Returns results with audit trail.

使用提供的输入参数运行技能。返回结果及审计追踪信息。

**Request:**
```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"miner_id": "miner-001", "window_min": 10}' \
  https://your-domain/api/skills/telemetry_snapshot/run
```

**Response:** See [Response Format](#response-format).

---

## Available Skills

### 1. `telemetry_snapshot` / 遥测快照

Fetches live telemetry and recent history for a specific miner, computes window statistics (min/max/avg for hashrate, temperature, power), and flags anomalies.

获取指定矿机的实时遥测和近期历史数据，计算窗口统计（算力/温度/功耗的最小值/最大值/平均值），并标记异常。

**Permission:** `skills:run:telemetry`

**Input Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `miner_id` | string | Yes | — | Miner identifier / 矿机标识 |
| `site_id` | integer | No | from session | Mining site ID / 矿场 ID |
| `window_min` | integer | No | `10` | History window in minutes / 历史窗口（分钟）|

**Example:**
```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "miner_id": "miner-001",
    "site_id": 1,
    "window_min": 15
  }' \
  https://your-domain/api/skills/telemetry_snapshot/run
```

**Output Fields:**

| Field | Description |
|-------|-------------|
| `current` | Latest live telemetry reading (hashrate, temp, power, fan speeds) / 最新实时遥测数据 |
| `window_stats` | Aggregated stats over the time window: hashrate_ths, temperature_c, power_w (each with min/max/avg) / 时间窗口聚合统计 |
| `anomalies` | Detected anomalies: `high_temperature` (>75°C) or `hashrate_drop` (>20% below avg) / 检测到的异常 |

**Example Response:**
```json
{
  "ok": true,
  "skill_id": "telemetry_snapshot",
  "audit_id": "12345",
  "elapsed_ms": 62,
  "data": {
    "miner_id": "miner-001",
    "site_id": 1,
    "current": {
      "hashrate": {"value": 95.2, "expected_ths": 100},
      "temperature": {"avg": 65, "max": 72},
      "power": {"value": 3250}
    },
    "window_stats": {
      "hashrate_ths": {"min": 90.1, "max": 98.5, "avg": 94.8},
      "temperature_c": {"min": 60, "max": 72, "avg": 65.3},
      "power_w": {"min": 3100, "max": 3300, "avg": 3200},
      "samples": 3,
      "window_minutes": 15
    },
    "anomalies": []
  },
  "warnings": [],
  "evidence_refs": [
    {"type": "telemetry_live", "id": "miner-001", "source": "miner_telemetry_live"},
    {"type": "telemetry_history", "id": "1:miner-001", "source": "telemetry_history_5min"}
  ],
  "error": null
}
```

---

### 2. `alert_triage` / 告警聚合分级

Aggregates and clusters recent alerts by miner, alert type, and time bucket, sorted by severity. Falls back to live telemetry scanning if the alert database is unavailable.

按矿机、告警类型和时间窗口聚合近期告警，按严重度排序。如果告警数据库不可用，自动回退到实时遥测扫描。

**Permission:** `skills:run:alerts`

**Input Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `site_id` | integer | Yes | — | Mining site ID / 矿场 ID |
| `since_min` | integer | No | `30` | Look back window in minutes / 回溯窗口（分钟）|
| `severity_floor` | string | No | `"P3"` | Minimum severity to include: `critical`/`P1`, `warning`/`P2`, `info`/`P3` / 最低严重度过滤 |

**Example:**
```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": 1,
    "since_min": 60,
    "severity_floor": "P2"
  }' \
  https://your-domain/api/skills/alert_triage/run
```

**Output Fields:**

| Field | Description |
|-------|-------------|
| `total_clusters` | Number of alert clusters found / 告警聚合组数 |
| `clusters` | Array of clusters, each with: `cluster_id`, `alert_type`, `severity`, `count`, `affected_miners`, `top_signals`, `time_bucket` / 告警聚合组列表 |

**Example Response:**
```json
{
  "ok": true,
  "skill_id": "alert_triage",
  "audit_id": "12346",
  "received_at": "2026-02-14T22:00:00Z",
  "elapsed_ms": 85,
  "data": {
    "site_id": 1,
    "since_min": 60,
    "severity_floor": "P2",
    "total_clusters": 2,
    "clusters": [
      {
        "cluster_id": "a1b2c3d4e5f6",
        "alert_type": "temperature_high",
        "severity": "critical",
        "count": 3,
        "affected_miners": ["miner-005", "miner-012", "miner-018"],
        "top_signals": ["temp_max=87°C", "temp_max=82°C"],
        "time_bucket": "1739548800"
      },
      {
        "cluster_id": "f6e5d4c3b2a1",
        "alert_type": "hashrate_low",
        "severity": "warning",
        "count": 1,
        "affected_miners": ["miner-042"],
        "top_signals": ["hashrate=12 TH/s vs expected=100 TH/s"],
        "time_bucket": "live"
      }
    ]
  }
}
```

---

### 3. `rca_quick_diagnose` / 快速根因诊断

Runs health rules against live telemetry to identify the most likely root cause category and suggests next diagnostic checks. Categories: Thermal, Hardware, Network, Pool, Power, Unknown.

对实时遥测运行健康规则，识别最可能的根因类别并建议下一步诊断检查。类别：散热、硬件、网络、矿池、电力、未知。

**Permission:** `skills:run:diagnose`

**Input Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `miner_id` | string | Yes | — | Miner identifier / 矿机标识 |
| `site_id` | integer | No | from session | Mining site ID / 矿场 ID |
| `incident_hint` | string | No | `""` | Optional description of the observed issue / 可选的问题描述 |

**Example:**
```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "miner_id": "miner-005",
    "site_id": 1,
    "incident_hint": "hashrate dropped suddenly"
  }' \
  https://your-domain/api/skills/rca_quick_diagnose/run
```

**Output Fields:**

| Field | Description |
|-------|-------------|
| `root_cause` | Most likely category: `Thermal`, `Hardware`, `Network`, `Pool`, `Power`, `Unknown` / 最可能的根因类别 |
| `confidence` | Confidence score 0.0–1.0 / 置信度 |
| `category_scores` | Weighted scores per category / 各类别加权分数 |
| `triggered_rules` | List of rules that fired, with severity and evidence / 触发的规则列表 |
| `evidence` | Telemetry features used for diagnosis / 用于诊断的遥测特征 |
| `next_checks` | Recommended follow-up actions / 建议的后续检查步骤 |

**Example Response:**
```json
{
  "ok": true,
  "skill_id": "rca_quick_diagnose",
  "audit_id": "12347",
  "received_at": "2026-02-14T22:01:00Z",
  "elapsed_ms": 120,
  "data": {
    "miner_id": "miner-005",
    "root_cause": "Thermal",
    "confidence": 0.67,
    "category_scores": {"Thermal": 1.0, "Hardware": 0.3},
    "triggered_rules": [
      {"code": "overheat_crit", "severity": "P0", "evidence": {"temp_max": 88}},
      {"code": "boards_degrading", "severity": "P2", "evidence": {"boards_ratio": 0.75}}
    ],
    "evidence": {
      "features": {
        "temp_max": 88, "temp_avg": 78, "hashrate_ratio": 0.65,
        "is_online": true, "boards_ratio": 0.75, "fan_speed_min": 4200,
        "hardware_errors": 12
      },
      "incident_hint": "hashrate dropped suddenly"
    },
    "next_checks": [
      "Check ambient temperature and cooling system",
      "Inspect fans and heat sinks for dust buildup",
      "Verify airflow direction and obstructions"
    ]
  }
}
```

---

### 4. `ticket_draft` / 工单草拟

Generates a structured maintenance ticket draft for a miner issue, optionally including a live telemetry snapshot. Uses the AI ticket drafting service when available, with a template fallback.

为矿机问题生成结构化维护工单草稿，可选包含实时遥测快照。优先使用 AI 工单起草服务，不可用时使用模板回退。

**Permission:** `skills:run:ticket`

**Input Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `miner_id` | string | Yes | — | Miner identifier / 矿机标识 |
| `issue` | string | Yes | — | Issue description (e.g., "hashrate_drop", "overheating") / 问题描述 |
| `site_id` | integer | No | from session | Mining site ID / 矿场 ID |
| `include_snapshot` | boolean | No | `true` | Attach live telemetry snapshot / 是否附加实时遥测快照 |

**Example:**
```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "miner_id": "miner-005",
    "issue": "overheating",
    "site_id": 1,
    "include_snapshot": true
  }' \
  https://your-domain/api/skills/ticket_draft/run
```

**Output Fields:**

| Field | Description |
|-------|-------------|
| `title` | Generated ticket title / 工单标题 |
| `description` | Problem description and context / 问题描述和上下文 |
| `priority` | Priority level: P0–P3 / 优先级 |
| `tags` | Auto-assigned tags / 自动标签 |
| `recommended_parts` | Suggested replacement parts or actions / 建议更换部件或操作 |
| `full_draft` | Complete ticket object (includes troubleshooting steps, bilingual titles, etc.) / 完整工单对象 |
| `snapshot` | Live telemetry data at time of drafting (if `include_snapshot=true`) / 起草时的实时遥测数据 |

**Example Response:**
```json
{
  "ok": true,
  "skill_id": "ticket_draft",
  "audit_id": "12348",
  "received_at": "2026-02-14T22:02:00Z",
  "elapsed_ms": 210,
  "data": {
    "miner_id": "miner-005",
    "site_id": 1,
    "issue": "overheating",
    "title": "[overheating] Miner miner-005 - Requires Attention",
    "description": "Issue reported: overheating\nAffected miner: miner-005\nSite: 1",
    "priority": "P2",
    "tags": ["auto-generated", "overheating"],
    "recommended_parts": [],
    "full_draft": {
      "title": "[overheating] Miner miner-005 - Requires Attention",
      "title_zh": "[overheating] 矿机 miner-005 - 需要关注",
      "troubleshooting_steps": [
        "Check miner status and connectivity",
        "Review recent logs",
        "Contact on-site technician if needed"
      ],
      "generated_at": "2026-02-14T22:00:00"
    },
    "snapshot": null
  }
}
```

---

### 5. `curtailment_dry_run` / 限电预演

Simulates a power curtailment plan without executing any control actions. This is strictly read-only — no miners are stopped, no database writes occur. Useful for planning and impact assessment.

模拟限电计划但不执行任何控制操作。严格只读——不停止矿机，不写入数据库。适用于规划和影响评估。

**Permission:** `skills:run:curtailment`

**Input Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `site_id` | integer | Yes | — | Mining site ID / 矿场 ID |
| `target_kw_reduction` | number | No | — | Target power reduction in kW / 目标减少功率（千瓦）|
| `curtailment_pct` | number | No | `10` | Alternative: reduce by percentage of total power / 替代：按总功率百分比减少 |
| `strategy` | string | No | `"shutdown"` | Strategy name (e.g., "shutdown", "throttle") / 策略名称 |
| `step_size` | integer | No | `50` | Miners per execution step / 每步执行的矿机数 |
| `constraints` | object | No | `null` | Additional constraints / 附加约束 |

> Note: Provide either `target_kw_reduction` OR `curtailment_pct`. If neither is given, defaults to 10% curtailment.
>
> 注意：提供 `target_kw_reduction` 或 `curtailment_pct` 之一。如果两者都没有提供，默认减少 10%。

**Example:**
```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": 1,
    "target_kw_reduction": 500,
    "strategy": "shutdown",
    "step_size": 20
  }' \
  https://your-domain/api/skills/curtailment_dry_run/run
```

**Output Fields:**

| Field | Description |
|-------|-------------|
| `dry_run` | Always `true` — confirms no actions were taken / 始终为 `true`，确认未执行操作 |
| `strategy` | Strategy used / 使用的策略 |
| `target_kw_reduction` | Target kW requested / 请求的目标减少千瓦 |
| `total_power_reduction_kw` | Actual simulated reduction / 实际模拟减少量 |
| `total_hashrate_loss_ths` | Estimated hashrate loss / 估计的算力损失 |
| `total_miners_affected` | Number of miners that would be affected / 受影响的矿机数 |
| `steps` | Execution steps with miners, estimated kW, and hashrate impact per batch / 执行步骤，含每批矿机、预估功率和算力影响 |
| `economic_impact` | Economic impact analysis (when available from curtailment engine) / 经济影响分析 |

**Example Response:**
```json
{
  "ok": true,
  "skill_id": "curtailment_dry_run",
  "audit_id": "12349",
  "received_at": "2026-02-14T22:03:00Z",
  "elapsed_ms": 340,
  "data": {
    "site_id": 1,
    "dry_run": true,
    "strategy": "shutdown",
    "target_kw_reduction": 500,
    "curtailment_pct": null,
    "total_power_reduction_kw": 520.5,
    "total_hashrate_loss_ths": 4800.2,
    "total_miners_affected": 150,
    "steps": [
      {
        "step": 1,
        "miners": ["miner-101", "miner-102", "..."],
        "miner_count": 20,
        "estimated_kw": 68.4,
        "estimated_hash_loss_ths": 640.0
      },
      {
        "step": 2,
        "miners": ["miner-121", "miner-122", "..."],
        "miner_count": 20,
        "estimated_kw": 65.2,
        "estimated_hash_loss_ths": 610.0
      }
    ],
    "economic_impact": null
  },
  "warnings": [
    "This is a dry-run simulation. No control actions were triggered."
  ]
}
```

---

## RBAC Permissions

Skills visibility and execution are controlled by the central RBAC permission matrix. Each role sees only the skills they can run.

技能的可见性和执行由中央 RBAC 权限矩阵控制。每个角色只能看到和运行其有权限的技能。

| Role / 角色 | telemetry_snapshot | alert_triage | rca_quick_diagnose | ticket_draft | curtailment_dry_run |
|---|:---:|:---:|:---:|:---:|:---:|
| **Owner** | Yes | Yes | Yes | Yes | Yes |
| **Admin** | Yes | Yes | Yes | Yes | Yes |
| **Mining Site Owner** | Yes | Yes | Yes | Yes | Yes |
| **Operator** | Yes | Yes | Yes | Yes | No |
| **Client** | Yes | No | No | No | No |
| **Guest** | No | No | No | No | No |

**Permission strings:**

| Permission | Controls |
|---|---|
| `skills:read` | Can list skills (required for all non-guest roles) |
| `skills:run:telemetry` | Can run `telemetry_snapshot` |
| `skills:run:alerts` | Can run `alert_triage` |
| `skills:run:diagnose` | Can run `rca_quick_diagnose` |
| `skills:run:ticket` | Can run `ticket_draft` |
| `skills:run:curtailment` | Can run `curtailment_dry_run` |

---

## Response Format

All skill execution responses follow a unified JSON structure:

所有技能执行响应遵循统一的 JSON 结构：

```json
{
  "ok": true,
  "skill_id": "telemetry_snapshot",
  "audit_id": "12345",
  "received_at": "2026-02-14T22:00:00Z",
  "elapsed_ms": 62,
  "data": { ... },
  "warnings": ["optional warning messages"],
  "evidence_refs": [
    {"type": "telemetry_live", "id": "miner-001", "source": "miner_telemetry_live"}
  ],
  "error": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | `true` if execution succeeded / 执行是否成功 |
| `skill_id` | string | ID of the executed skill / 执行的技能 ID |
| `audit_id` | string | Unique audit trail ID for this execution / 此次执行的审计追踪 ID |
| `received_at` | string | ISO 8601 timestamp when request was received / 请求接收时间 |
| `elapsed_ms` | integer | Execution time in milliseconds / 执行耗时（毫秒）|
| `data` | object | Skill-specific result data / 技能特定的结果数据 |
| `warnings` | array | Non-fatal warning messages / 非致命警告信息 |
| `evidence_refs` | array | References to data sources used / 使用的数据源引用 |
| `error` | object\|null | Error details if `ok` is `false` / 错误详情（如失败）|

---

## Error Codes

When a request fails, `ok` is `false` and the `error` object contains:

请求失败时，`ok` 为 `false`，`error` 对象包含：

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Input validation failed",
    "details": {"errors": ["Missing required field: miner_id"]}
  }
}
```

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_REQUIRED` | 401 | No valid authentication provided / 未提供有效认证 |
| `FORBIDDEN` | 403 | User lacks required permission for this skill / 用户缺少此技能所需的权限 |
| `INVALID_INPUT` | 400 | Input validation failed (missing/wrong type fields) / 输入验证失败 |
| `NOT_FOUND` | 404 | Skill ID does not exist / 技能 ID 不存在 |
| `RATE_LIMITED` | 429 | Too many requests (30 requests/minute) / 请求过于频繁 |
| `UPSTREAM_FAILED` | 502 | Upstream service (telemetry, AI) unavailable / 上游服务不可用 |
| `FEATURE_DISABLED` | 503 | Skills system or specific skill is disabled / 技能系统或特定技能已禁用 |
| `INTERNAL_ERROR` | 500 | Unexpected server error / 服务器内部错误 |

---

## Feature Flags

### Global Kill Switch / 全局开关

Set environment variable `SKILLS_ENABLED=false` to disable the entire skills system. All `/run` requests will return `503 FEATURE_DISABLED`.

设置环境变量 `SKILLS_ENABLED=false` 禁用整个技能系统。

### Skill Allowlist / 技能白名单

Set `SKILLS_ALLOWLIST` in app config to restrict which skills can be executed:

在应用配置中设置 `SKILLS_ALLOWLIST` 限制可执行的技能：

```python
app.config['SKILLS_ALLOWLIST'] = ['telemetry_snapshot', 'alert_triage']
```

When set, only listed skills can be run. Skills not in the list return `503 FEATURE_DISABLED`. When `None` (default), all registered skills are available.

设置后只有列表中的技能可以运行。未列出的技能返回 `503`。默认值 `None` 表示所有注册的技能均可用。

---

## Rate Limiting

The `/api/skills/<skill_id>/run` endpoint is rate-limited to **30 requests per minute** per client.

`/run` 接口限流为每客户端 **每分钟 30 次请求**。

When exceeded, returns:

超限时返回：

```json
{
  "ok": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests"
  }
}
```

HTTP Status: `429`

---

## Workflow Examples / 工作流示例

### Example 1: Diagnose a Miner Issue / 诊断矿机问题

A typical troubleshooting workflow chains multiple skills:

典型的故障排查工作流串联多个技能：

```bash
# Step 1: Get current telemetry / 第一步：获取当前遥测
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"miner_id": "miner-005", "site_id": 1}' \
  https://your-domain/api/skills/telemetry_snapshot/run

# Step 2: Diagnose root cause / 第二步：诊断根因
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"miner_id": "miner-005", "incident_hint": "hashrate dropped 50%"}' \
  https://your-domain/api/skills/rca_quick_diagnose/run

# Step 3: Draft a maintenance ticket / 第三步：起草维护工单
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"miner_id": "miner-005", "issue": "hashrate_drop"}' \
  https://your-domain/api/skills/ticket_draft/run
```

### Example 2: Plan a Power Curtailment / 规划限电

```bash
# Step 1: Check site alerts / 第一步：检查矿场告警
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"site_id": 1, "since_min": 60}' \
  https://your-domain/api/skills/alert_triage/run

# Step 2: Simulate 500kW curtailment / 第二步：模拟减少 500kW
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"site_id": 1, "target_kw_reduction": 500, "strategy": "shutdown", "step_size": 25}' \
  https://your-domain/api/skills/curtailment_dry_run/run
```

### Example 3: AI Closed-Loop Automation / AI 闭环自动化

The AI system uses the same API endpoints internally to perform automated operations:

AI 系统内部使用相同的 API 接口执行自动化操作：

1. `telemetry_snapshot` → Detect anomaly / 检测异常
2. `rca_quick_diagnose` → Identify root cause / 识别根因
3. `ticket_draft` → Generate maintenance ticket / 生成维护工单
4. `curtailment_dry_run` → Simulate mitigation plan / 模拟缓解方案
5. Control Plane → Execute approved actions / 执行已批准的操作

Each step generates an `audit_id` for full traceability.

每一步都会生成 `audit_id` 实现完整追溯。

---

## Audit Trail / 审计追踪

Every skill execution is recorded in the Control Plane audit log with:

每次技能执行都记录在控制平面审计日志中，包含：

- `event_type`: `skill_run`
- `actor_id`: User ID or API key name
- `ref_type`: `skill`
- `ref_id`: Skill ID (e.g., `telemetry_snapshot`)
- `payload`: Redacted input, status, elapsed time, evidence references

Sensitive fields in the input (passwords, tokens, keys) are automatically redacted before logging.

输入中的敏感字段（密码、令牌、密钥）在记录前会自动脱敏。
