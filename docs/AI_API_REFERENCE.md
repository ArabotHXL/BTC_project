# AI 系统 API 参考文档

> AI System API Reference | AI 系统 API 完整参考

本文档详细描述系统中所有 AI 相关的 API 接口，包括闭环流程 API、AI 功能 API 和自动执行 API。

---

## 目录

- [1. 概述](#1-概述)
- [2. 认证与授权](#2-认证与授权)
- [3. AI 闭环流程 API](#3-ai-闭环流程-api-ai-closed-loop-api)
- [4. AI 功能 API](#4-ai-功能-api-ai-feature-api)
- [5. AI 自动执行 API](#5-ai-自动执行-api-ai-auto-execution-api)
- [6. 错误码参考](#6-错误码参考)
- [7. 数据模型](#7-数据模型)

---

## 1. 概述

系统 AI 功能围绕以下闭环流程设计：

```
告警(Detect) → 诊断(Diagnose) → 建议(Recommend) → 审批(Approve) → 执行(Act) → 审计(Audit) → 复盘(Learn)
```

**API 模块分层：**

| 模块 | 路径前缀 | 功能描述 |
|------|----------|----------|
| AI Closed-Loop API | `/api/v1/ai/recommendations` | 建议生命周期管理 |
| AI Feature API | `/api/v1/ai/diagnose`, `/api/v1/ai/ticket`, `/api/v1/ai/curtailment` | AI 诊断与建议功能 |
| AI Auto Execution API | `/api/v1/ai/auto` | 自动执行与规则管理 |

---

## 2. 认证与授权

### 2.1 认证方式

所有 AI API 均需要用户登录认证（Session 认证）。

**认证头 (Authentication Header):**
```
Cookie: session=<session_token>
```

### 2.2 角色权限

| 角色 (Role) | 权限描述 |
|-------------|----------|
| `user` | 基础访问：查看建议、诊断告警 |
| `operator` | 操作权限：审批/拒绝/执行建议 |
| `manager` | 管理权限：同 operator |
| `admin` | 管理员：管理自动审批规则 |

### 2.3 错误响应

**401 Unauthorized（未认证）:**
```json
{
  "error": "Authentication required"
}
```

**403 Forbidden（权限不足）:**
```json
{
  "error": "Operator access required"
}
```

---

## 3. AI 闭环流程 API (AI Closed-Loop API)

> 文件位置: `api/ai_closedloop_api.py`

管理 AI 建议的完整生命周期。

---

### 3.1 获取建议列表

**GET** `/api/v1/ai/recommendations`

获取 AI 建议列表，支持按站点、状态过滤。

**认证要求:** 登录用户

**Query 参数:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `site_id` | int | 否 | - | 按站点 ID 过滤 |
| `status` | string | 否 | - | 按状态过滤: `pending`, `approved`, `rejected`, `executing`, `completed`, `failed`, `expired` |
| `limit` | int | 否 | 50 | 返回数量上限 (最大 200) |

**请求示例:**
```http
GET /api/v1/ai/recommendations?site_id=1&status=pending&limit=20
```

**成功响应 (200 OK):**
```json
{
  "recommendations": [
    {
      "id": "uuid-recommendation-id",
      "site_id": 1,
      "trigger": {
        "type": "alert",
        "id": "alert-123",
        "data": null
      },
      "diagnosis": {
        "root_cause": "温度过高导致算力下降",
        "evidence": ["温度 85°C", "算力下降 15%"],
        "confidence": 0.85
      },
      "action": {
        "type": "adjust_fan",
        "params": {"speed": 100},
        "target_ids": ["miner-001", "miner-002"]
      },
      "risk": {
        "level": "low",
        "confidence": 0.85,
        "priority": 3
      },
      "expected_benefit": {
        "description": "恢复正常算力",
        "estimated_improvement_pct": 15
      },
      "status": "pending",
      "created_at": "2026-01-27T10:30:00Z"
    }
  ],
  "count": 1
}
```

---

### 3.2 创建建议

**POST** `/api/v1/ai/recommendations`

创建新的 AI 建议。

**认证要求:** 登录用户

**请求体 (Request Body):**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |
| `trigger_type` | string | **是** | 触发类型: `alert`, `anomaly`, `schedule`, `user_request` |
| `trigger_id` | string | 否 | 触发事件 ID |
| `trigger_data` | object | 否 | 触发上下文数据 |
| `diagnosis` | object | **是** | 诊断结果 (见下表) |
| `action_type` | string | **是** | 动作类型: `reboot`, `power_off`, `power_on`, `adjust_frequency`, `adjust_fan`, `switch_pool`, `curtail`, `restore`, `alert_only`, `manual_review` |
| `action_params` | object | 否 | 动作参数 |
| `target_ids` | array | 否 | 目标设备 ID 列表 |
| `risk_level` | string | 否 | 风险等级: `low`, `medium`, `high`, `critical` (默认 `medium`) |
| `confidence_score` | number | 否 | AI 置信度 (0-1) |
| `priority` | int | 否 | 优先级 (1-10, 1最高, 默认5) |
| `expected_benefit` | object | 否 | 预期收益 |

**diagnosis 对象结构:**
```json
{
  "root_cause": "string - 根因描述",
  "evidence": ["证据1", "证据2"],
  "confidence": 0.85
}
```

**请求示例:**
```json
{
  "site_id": 1,
  "trigger_type": "alert",
  "trigger_id": "alert-456",
  "diagnosis": {
    "root_cause": "风扇故障导致温度异常",
    "evidence": ["Fan1 转速 0 RPM", "芯片温度 92°C"],
    "confidence": 0.92
  },
  "action_type": "power_off",
  "target_ids": ["miner-003"],
  "risk_level": "high",
  "priority": 2
}
```

**成功响应 (201 Created):**
```json
{
  "success": true,
  "recommendation": {
    "id": "uuid-new-recommendation",
    "site_id": 1,
    "status": "pending",
    ...
  }
}
```

**错误响应 (400 Bad Request):**
```json
{
  "error": "site_id is required"
}
```

---

### 3.3 获取建议详情

**GET** `/api/v1/ai/recommendations/<recommendation_id>`

获取单个建议的完整详情，包含反馈记录。

**认证要求:** 登录用户

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `recommendation_id` | string | 建议 UUID |

**成功响应 (200 OK):**
```json
{
  "recommendation": {
    "id": "uuid-recommendation-id",
    "site_id": 1,
    "trigger": {
      "type": "alert",
      "id": "alert-123",
      "data": {"severity": "high", "timestamp": "..."}
    },
    "diagnosis": {...},
    "action": {...},
    "risk": {...},
    "status": "completed",
    "approval": {
      "required": true,
      "approved_by": 5,
      "approved_at": "2026-01-27T11:00:00Z",
      "reason": "确认需要关停"
    },
    "execution": {
      "command_id": "cmd-uuid",
      "started_at": "2026-01-27T11:01:00Z",
      "completed_at": "2026-01-27T11:02:00Z",
      "result": {"success": true}
    },
    "learning": {
      "effectiveness_score": 0.9,
      "feedback": {...}
    }
  },
  "feedback": [
    {
      "id": "feedback-uuid",
      "feedback_type": "user_review",
      "was_effective": true,
      "user_rating": 5,
      "user_comment": "问题已解决",
      "created_at": "2026-01-27T12:00:00Z"
    }
  ]
}
```

**错误响应 (404 Not Found):**
```json
{
  "error": "Recommendation not found"
}
```

---

### 3.4 审批建议

**POST** `/api/v1/ai/recommendations/<recommendation_id>/approve`

批准待处理的建议。

**认证要求:** 登录用户

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `reason` | string | 否 | 审批原因/备注 |

**请求示例:**
```json
{
  "reason": "经确认矿机确实过热，同意关停"
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "recommendation": {
    "id": "uuid-recommendation",
    "status": "approved",
    "approval": {
      "approved_by": 5,
      "approved_at": "2026-01-27T11:00:00Z",
      "reason": "经确认矿机确实过热，同意关停"
    },
    ...
  }
}
```

**错误响应 (400 Bad Request):**
```json
{
  "error": "Recommendation cannot be approved (status=completed)"
}
```

---

### 3.5 拒绝建议

**POST** `/api/v1/ai/recommendations/<recommendation_id>/reject`

拒绝待处理的建议。

**认证要求:** 登录用户

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `reason` | string | **是** | 拒绝原因 (必填) |

**请求示例:**
```json
{
  "reason": "误报，矿机状态正常"
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "recommendation": {
    "id": "uuid-recommendation",
    "status": "rejected",
    "rejection": {
      "rejected_by": 5,
      "rejected_at": "2026-01-27T11:00:00Z",
      "reason": "误报，矿机状态正常"
    },
    ...
  }
}
```

**错误响应 (400 Bad Request):**
```json
{
  "error": "reason is required"
}
```

---

### 3.6 执行建议

**POST** `/api/v1/ai/recommendations/<recommendation_id>/execute`

执行已批准的建议。将在 Control Plane 中创建命令并下发。

**认证要求:** 登录用户

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `recommendation_id` | string | 建议 UUID |

**成功响应 (200 OK):**
```json
{
  "success": true,
  "recommendation_id": "uuid-recommendation",
  "command_id": "cmd-uuid",
  "status": "executing"
}
```

**错误响应 (400 Bad Request):**
```json
{
  "error": "Recommendation must be approved before execution"
}
```

---

### 3.7 提交反馈

**POST** `/api/v1/ai/recommendations/<recommendation_id>/feedback`

为建议提交反馈，用于学习循环。

**认证要求:** 登录用户

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feedback_type` | string | **是** | 反馈类型: `execution_result`, `user_review`, `automated_check` |
| `was_effective` | bool | 否 | 是否有效 |
| `outcome_metrics` | object | 否 | 结果指标 |
| `user_rating` | int | 否 | 用户评分 (1-5) |
| `user_comment` | string | 否 | 用户评论 |
| `side_effects` | object | 否 | 副作用记录 |

**请求示例:**
```json
{
  "feedback_type": "user_review",
  "was_effective": true,
  "user_rating": 4,
  "user_comment": "问题已解决，但响应时间可以更快",
  "outcome_metrics": {
    "hashrate_recovered_pct": 95,
    "time_to_resolve_minutes": 15
  }
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "feedback": {
    "id": "feedback-uuid",
    "recommendation_id": "uuid-recommendation",
    "feedback_type": "user_review",
    "was_effective": true,
    "user_rating": 4,
    "created_at": "2026-01-27T12:00:00Z"
  }
}
```

---

### 3.8 获取学习统计

**GET** `/api/v1/ai/learning/stats`

获取站点的 AI 学习统计数据。

**认证要求:** 登录用户

**Query 参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |

**请求示例:**
```http
GET /api/v1/ai/learning/stats?site_id=1
```

**成功响应 (200 OK):**
```json
{
  "site_id": 1,
  "total_recommendations": 156,
  "approved_count": 120,
  "rejected_count": 15,
  "executed_count": 115,
  "success_rate": 0.92,
  "average_effectiveness": 0.87,
  "feedback_count": 98,
  "last_updated": "2026-01-27T12:00:00Z"
}
```

---

## 4. AI 功能 API (AI Feature API)

> 文件位置: `api/ai_feature_api.py`

提供三大高频场景的 AI 辅助功能：
1. **告警诊断** - 减少值班人员"看图猜原因"的时间
2. **工单草稿** - 把"写工单"从 10-20 分钟压到 1-2 分钟
3. **限电建议** - 把"凭经验拍脑袋"变成"可解释的策略建议"

---

### 4.1 告警诊断

**POST** `/api/v1/ai/diagnose/alert`

诊断单个告警，返回 Top3 根因假设、证据和建议动作。

**认证要求:** 登录用户

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |
| `miner_id` | string | **是** | 矿机 ID |
| `alert_type` | string | **是** | 告警类型 |
| `alert_id` | string | 否 | 告警 ID |

**请求示例:**
```json
{
  "site_id": 1,
  "miner_id": "miner-001",
  "alert_type": "hashrate_drop"
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "diagnosis": {
    "miner_id": "miner-001",
    "alert_type": "hashrate_drop",
    "hypotheses": [
      {
        "rank": 1,
        "cause": "芯片温度过高导致降频",
        "confidence": 0.85,
        "evidence": [
          "芯片温度 88°C，超过阈值 85°C",
          "功耗下降 12%"
        ],
        "suggested_action": {
          "type": "adjust_fan",
          "params": {"speed": 100},
          "description": "提高风扇转速至最大"
        }
      },
      {
        "rank": 2,
        "cause": "矿池连接不稳定",
        "confidence": 0.45,
        "evidence": [
          "过去 1 小时拒绝率 2.3%"
        ],
        "suggested_action": {
          "type": "switch_pool",
          "description": "切换到备用矿池"
        }
      },
      {
        "rank": 3,
        "cause": "算力板故障",
        "confidence": 0.30,
        "evidence": [
          "Board 2 芯片数异常"
        ],
        "suggested_action": {
          "type": "manual_review",
          "description": "人工检查算力板"
        }
      }
    ],
    "summary": "最可能原因：温度过高导致自动降频",
    "urgency": "medium",
    "diagnosed_at": "2026-01-27T10:30:00Z"
  }
}
```

---

### 4.2 批量告警诊断

**POST** `/api/v1/ai/diagnose/batch`

批量诊断多台矿机的告警。

**认证要求:** 登录用户

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |
| `alert_type` | string | **是** | 告警类型 |
| `miner_ids` | array | **是** | 矿机 ID 列表 (非空数组) |

**请求示例:**
```json
{
  "site_id": 1,
  "alert_type": "offline",
  "miner_ids": ["miner-001", "miner-002", "miner-003"]
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "diagnoses": {
    "miner-001": {
      "hypotheses": [...],
      "summary": "网络故障",
      "urgency": "high"
    },
    "miner-002": {
      "hypotheses": [...],
      "summary": "电源问题",
      "urgency": "high"
    },
    "miner-003": {
      "hypotheses": [...],
      "summary": "网络故障",
      "urgency": "high"
    }
  },
  "count": 3
}
```

**错误响应 (400 Bad Request):**
```json
{
  "error": "miner_ids must be a non-empty array"
}
```

---

### 4.3 生成工单草稿

**POST** `/api/v1/ai/ticket/draft`

根据告警和诊断结果自动生成工单草稿。

**认证要求:** 登录用户

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |
| `miner_ids` | array | **是** | 受影响矿机 ID 列表 |
| `alert_type` | string | **是** | 告警类型 |
| `diagnosis` | object | 否 | 已有诊断结果 (无则自动诊断) |
| `site_info` | object | 否 | 站点信息 |
| `miner_info` | object | 否 | 矿机信息 |

**请求示例:**
```json
{
  "site_id": 1,
  "miner_ids": ["miner-001", "miner-002"],
  "alert_type": "high_temperature"
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "ticket_draft": {
    "title": "[温度告警] 矿机过温 - 站点A 2台设备",
    "severity": "high",
    "category": "hardware_issue",
    "affected_devices": ["miner-001", "miner-002"],
    "description": {
      "summary": "2台矿机检测到温度异常告警",
      "symptoms": [
        "芯片温度超过 85°C 阈值",
        "算力下降约 15%"
      ],
      "diagnosis": "初步判断为散热系统异常或环境温度过高",
      "impact": "影响算力产出，存在硬件损坏风险"
    },
    "recommended_actions": [
      {
        "step": 1,
        "action": "检查风扇运转状态",
        "details": "确认所有风扇正常工作"
      },
      {
        "step": 2,
        "action": "检查环境温度",
        "details": "确认机房温度在正常范围内"
      },
      {
        "step": 3,
        "action": "清洁散热器",
        "details": "如有积尘需要清理"
      }
    ],
    "attachments_needed": [
      "矿机状态截图",
      "机房温度记录"
    ],
    "estimated_resolution_time": "2-4 小时",
    "generated_at": "2026-01-27T10:30:00Z"
  }
}
```

---

### 4.4 生成限电计划

**POST** `/api/v1/ai/curtailment/plan`

根据目标功率削减量生成优化的限电计划。

**认证要求:** 登录用户

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |
| `target_reduction_kw` | float | 否* | 目标削减功率 (kW) |
| `target_power_kw` | float | 否* | 目标总功率 (kW) |
| `target_reduction_pct` | float | 否* | 目标削减百分比 (默认 20%) |
| `electricity_price` | float | 否 | 电价 ($/kWh)，默认 0.05 |
| `btc_price` | float | 否 | BTC 价格 |
| `strategy` | string | 否 | 关停策略 (默认 `efficiency_first`) |
| `max_miners_to_curtail` | int | 否 | 最大关停矿机数 |
| `exclude_miner_ids` | array | 否 | 排除的矿机 ID 列表 |

> *注：`target_reduction_kw`、`target_power_kw`、`target_reduction_pct` 三选一

**策略选项 (strategy):**

| 策略 | 说明 |
|------|------|
| `efficiency_first` | 效率优先 - 优先关停效率最差 (J/TH 最高) 的矿机 |
| `power_first` | 功率优先 - 优先关停功耗最高的矿机 |
| `revenue_first` | 收益优先 - 优先关停利润最低的矿机 |
| `temperature_first` | 温度优先 - 优先关停运行温度最高的矿机 |

**请求示例:**
```json
{
  "site_id": 1,
  "target_reduction_kw": 500,
  "electricity_price": 0.06,
  "strategy": "efficiency_first",
  "exclude_miner_ids": ["vip-miner-001"]
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "curtailment_plan": {
    "site_id": 1,
    "strategy": "efficiency_first",
    "target": {
      "reduction_kw": 500,
      "reduction_pct": 18.5,
      "target_power_kw": 2200
    },
    "current_state": {
      "total_power_kw": 2700,
      "total_hashrate_th": 8500,
      "total_miners": 85
    },
    "curtailment_sequence": [
      {
        "order": 1,
        "miner_id": "miner-042",
        "model": "Antminer S19",
        "power_kw": 3.25,
        "hashrate_th": 95,
        "efficiency_jth": 34.2,
        "hourly_profit_usd": 0.15,
        "reason": "效率最差 (34.2 J/TH)"
      },
      {
        "order": 2,
        "miner_id": "miner-067",
        "model": "Antminer S19",
        "power_kw": 3.30,
        "hashrate_th": 98,
        "efficiency_jth": 33.7,
        "hourly_profit_usd": 0.18,
        "reason": "效率次差 (33.7 J/TH)"
      }
    ],
    "impact_summary": {
      "miners_to_curtail": 15,
      "total_power_reduction_kw": 502.5,
      "total_hashrate_loss_th": 1450,
      "estimated_revenue_loss_daily_usd": 85.2,
      "electricity_saved_daily_usd": 72.4,
      "net_impact_daily_usd": -12.8
    },
    "risks": [
      {
        "type": "revenue_impact",
        "severity": "medium",
        "description": "每日收益损失约 $85"
      }
    ],
    "execution_window": {
      "recommended_start": "2026-01-27T14:00:00Z",
      "estimated_duration_minutes": 30
    },
    "generated_at": "2026-01-27T10:30:00Z"
  }
}
```

---

### 4.5 获取限电策略列表

**GET** `/api/v1/ai/curtailment/strategies`

获取可用的限电策略选项。

**认证要求:** 登录用户

**成功响应 (200 OK):**
```json
{
  "strategies": [
    {
      "id": "efficiency_first",
      "name": "Efficiency First",
      "name_zh": "效率优先",
      "description": "Shut down miners with worst efficiency (highest J/TH) first",
      "description_zh": "优先关停效率最差（J/TH 最高）的矿机"
    },
    {
      "id": "power_first",
      "name": "Power First",
      "name_zh": "功率优先",
      "description": "Shut down highest power consuming miners first",
      "description_zh": "优先关停功耗最高的矿机"
    },
    {
      "id": "revenue_first",
      "name": "Revenue First",
      "name_zh": "收益优先",
      "description": "Shut down miners with lowest profit margin first",
      "description_zh": "优先关停利润最低的矿机"
    },
    {
      "id": "temperature_first",
      "name": "Temperature First",
      "name_zh": "温度优先",
      "description": "Shut down hottest running miners first",
      "description_zh": "优先关停运行温度最高的矿机"
    }
  ]
}
```

---

## 5. AI 自动执行 API (AI Auto Execution API)

> 文件位置: `api/ai_auto_execution_api.py`

管理 AI 建议的自动执行功能，包括风险评估、自动审批规则和批量执行。

---

### 5.1 风险评估

**POST** `/api/v1/ai/auto/assess-risk`

评估 AI 建议动作的风险等级。

**认证要求:** 登录用户

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action_type` | string | **是** | 动作类型: `power_off`, `curtail`, `reboot` 等 |
| `target_ids` | array | 否 | 目标设备 ID 列表 |
| `power_impact_kw` | float | 否 | 预估功率影响 (kW) |
| `revenue_impact_pct` | float | 否 | 预估收益影响百分比 |
| `confidence_score` | float | 否 | AI 置信度 (0-1)，默认 0.5 |
| `historical_success_rate` | float | 否 | 历史成功率，默认 0.9 |
| `time_of_day_risk` | float | 否 | 时段风险因子，默认 0.0 |

**请求示例:**
```json
{
  "action_type": "curtail",
  "target_ids": ["miner-001", "miner-002", "miner-003"],
  "power_impact_kw": 100,
  "revenue_impact_pct": 5,
  "confidence_score": 0.85
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "risk_assessment": {
    "level": "low",
    "score": 0.22,
    "factors": [
      {
        "factor": "action_type",
        "value": "curtail",
        "weight": 0.6,
        "description_en": "Action type 'curtail' risk weight",
        "description_zh": "操作类型 'curtail' 风险权重"
      },
      {
        "factor": "target_count",
        "value": 3,
        "weight": 0.1,
        "description_en": "3 devices affected",
        "description_zh": "影响 3 台设备"
      },
      {
        "factor": "power_impact",
        "value": 100,
        "weight": 0.1,
        "description_en": "100 kW power impact",
        "description_zh": "功率影响 100 kW"
      },
      {
        "factor": "revenue_impact",
        "value": 5.0,
        "weight": 0.1,
        "description_en": "5.0% revenue impact",
        "description_zh": "收益影响 5.0%"
      }
    ],
    "can_auto_execute": true,
    "require_approval": false,
    "approval_level": "operator"
  }
}
```

**风险等级阈值:**

| 等级 (Level) | 分数阈值 | 自动执行 |
|--------------|----------|----------|
| `low` | < 0.25 | 可自动执行 |
| `medium` | 0.25 - 0.50 | 需 operator 审批 |
| `high` | 0.50 - 0.75 | 需 manager 审批 |
| `critical` | >= 0.75 | 需 admin 审批 |

---

### 5.2 获取待审批建议

**GET** `/api/v1/ai/auto/recommendations`

获取待审批的 AI 建议列表。

**认证要求:** 登录用户

**Query 参数:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `site_id` | int | 否 | - | 按站点过滤 |
| `status` | string | 否 | `pending` | 状态过滤 (`pending`, `approved`, `all`) |
| `limit` | int | 否 | 50 | 返回数量上限 |

**成功响应 (200 OK):**
```json
{
  "success": true,
  "recommendations": [
    {
      "id": "uuid-1",
      "site_id": 1,
      "action": {
        "type": "curtail",
        "target_ids": ["miner-001", "miner-002"]
      },
      "risk": {
        "level": "medium",
        "priority": 3
      },
      "status": "pending",
      "created_at": "2026-01-27T10:30:00Z"
    }
  ],
  "count": 1
}
```

---

### 5.3 审批建议 (Auto API)

**POST** `/api/v1/ai/auto/recommendations/<rec_id>/approve`

审批待处理的建议。

**认证要求:** 登录用户 + operator 或更高角色

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `reason` | string | 否 | 审批原因 |

**成功响应 (200 OK):**
```json
{
  "success": true,
  "recommendation": {
    "id": "uuid-1",
    "status": "approved",
    ...
  }
}
```

---

### 5.4 拒绝建议 (Auto API)

**POST** `/api/v1/ai/auto/recommendations/<rec_id>/reject`

拒绝待处理的建议。

**认证要求:** 登录用户 + operator 或更高角色

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `reason` | string | **是** | 拒绝原因 (必填) |

**成功响应 (200 OK):**
```json
{
  "success": true,
  "recommendation": {
    "id": "uuid-1",
    "status": "rejected",
    ...
  }
}
```

---

### 5.5 执行建议 (Auto API)

**POST** `/api/v1/ai/auto/recommendations/<rec_id>/execute`

执行已审批的建议。

**认证要求:** 登录用户 + operator 或更高角色

**成功响应 (200 OK):**
```json
{
  "success": true,
  "recommendation_id": "uuid-1",
  "command_id": "cmd-uuid",
  "status": "executing"
}
```

---

### 5.6 获取自动审批规则

**GET** `/api/v1/ai/auto/rules`

获取站点的自动审批规则列表。

**认证要求:** 登录用户

**Query 参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |

**成功响应 (200 OK):**
```json
{
  "success": true,
  "rules": [
    {
      "id": 1,
      "site_id": 1,
      "name": "低风险自动审批",
      "description": "自动批准低风险的建议",
      "conditions": {
        "max_risk_level": "low",
        "min_confidence": 0.8,
        "allowed_actions": ["adjust_fan", "switch_pool"],
        "max_targets": 10
      },
      "is_active": true,
      "created_at": "2026-01-20T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

### 5.7 创建自动审批规则

**POST** `/api/v1/ai/auto/rules`

创建新的自动审批规则。

**认证要求:** 登录用户 + admin 角色

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |
| `name` | string | **是** | 规则名称 |
| `description` | string | 否 | 规则描述 |
| `conditions` | object | **是** | 自动审批条件 (见下表) |

**conditions 对象结构:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `max_risk_level` | string | 最高允许风险等级: `low`, `medium` |
| `min_confidence` | float | 最低 AI 置信度 (0-1) |
| `allowed_actions` | array | 允许的动作类型列表 |
| `max_targets` | int | 最大目标设备数 |

**请求示例:**
```json
{
  "site_id": 1,
  "name": "Fan调整自动批准",
  "description": "自动批准风扇调整类的低风险建议",
  "conditions": {
    "max_risk_level": "low",
    "min_confidence": 0.85,
    "allowed_actions": ["adjust_fan"],
    "max_targets": 20
  }
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "rule": {
    "id": 2,
    "site_id": 1,
    "name": "Fan调整自动批准",
    "is_active": true,
    ...
  }
}
```

---

### 5.8 更新自动审批规则

**PUT** `/api/v1/ai/auto/rules/<rule_id>`

更新现有的自动审批规则。

**认证要求:** 登录用户 + admin 角色

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 否 | 规则名称 |
| `description` | string | 否 | 规则描述 |
| `conditions` | object | 否 | 自动审批条件 |
| `is_active` | bool | 否 | 是否激活 |

**成功响应 (200 OK):**
```json
{
  "success": true,
  "rule": {
    "id": 2,
    "is_active": true,
    ...
  }
}
```

---

### 5.9 删除自动审批规则

**DELETE** `/api/v1/ai/auto/rules/<rule_id>`

删除 (停用) 自动审批规则。

**认证要求:** 登录用户 + admin 角色

**成功响应 (200 OK):**
```json
{
  "success": true,
  "message": "Rule deactivated"
}
```

**错误响应 (404 Not Found):**
```json
{
  "error": "Rule not found"
}
```

---

### 5.10 执行自动审批批次

**POST** `/api/v1/ai/auto/execute-approved`

批量执行所有已自动审批的建议。

**认证要求:** 登录用户 + operator 或更高角色

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | 否 | 限定到特定站点 |

**成功响应 (200 OK):**
```json
{
  "success": true,
  "results": [
    {
      "recommendation_id": "uuid-1",
      "success": true,
      "command_id": "cmd-uuid-1"
    },
    {
      "recommendation_id": "uuid-2",
      "success": false,
      "error": "Target device offline"
    }
  ],
  "executed_count": 1,
  "failed_count": 1
}
```

---

### 5.11 从限电计划创建建议

**POST** `/api/v1/ai/auto/curtailment/create`

将限电计划转换为 AI 建议。

**认证要求:** 登录用户 + operator 或更高角色

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `site_id` | int | **是** | 站点 ID |
| `curtailment_plan` | object | **是** | 限电计划 (来自 `/api/v1/ai/curtailment/plan` 的输出) |
| `trigger_type` | string | 否 | 触发类型，默认 `user_request` |
| `trigger_id` | string | 否 | 触发 ID |

**请求示例:**
```json
{
  "site_id": 1,
  "curtailment_plan": {
    "strategy": "efficiency_first",
    "curtailment_sequence": [...],
    "impact_summary": {...}
  },
  "trigger_type": "schedule"
}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "recommendation": {
    "id": "uuid-new",
    "status": "pending",
    "action": {
      "type": "curtail",
      "target_ids": ["miner-042", "miner-067", ...]
    },
    ...
  },
  "auto_approved": false,
  "auto_executed": false
}
```

如果满足自动审批规则:
```json
{
  "success": true,
  "recommendation": {
    "id": "uuid-new",
    "status": "approved",
    ...
  },
  "auto_approved": true,
  "auto_executed": false
}
```

---

## 6. 错误码参考

### HTTP 状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器内部错误 |

### 常见错误消息

| 错误消息 | 原因 | 解决方案 |
|----------|------|----------|
| `Authentication required` | 未登录 | 请先登录系统 |
| `User not found` | 用户不存在 | 检查用户账号 |
| `Operator access required` | 需要操作员权限 | 联系管理员升级权限 |
| `Admin access required` | 需要管理员权限 | 使用管理员账号 |
| `{field} is required` | 缺少必填字段 | 补充缺失的字段 |
| `Recommendation not found` | 建议不存在 | 检查建议 ID |
| `Recommendation cannot be approved` | 建议状态不允许审批 | 只能审批 pending 状态的建议 |
| `reason is required` | 拒绝时必须填写原因 | 提供拒绝原因 |
| `miner_ids must be a non-empty array` | 矿机 ID 列表为空 | 提供至少一个矿机 ID |

---

## 7. 数据模型

### 7.1 RecommendationStatus (建议状态)

| 状态 | 值 | 说明 |
|------|-----|------|
| 待处理 | `pending` | 等待审批 |
| 已批准 | `approved` | 已批准，等待执行 |
| 已拒绝 | `rejected` | 已被拒绝 |
| 执行中 | `executing` | 正在执行 |
| 已完成 | `completed` | 执行完成 |
| 失败 | `failed` | 执行失败 |
| 已过期 | `expired` | 建议已过期 |

### 7.2 RiskLevel (风险等级)

| 等级 | 值 | 说明 |
|------|-----|------|
| 低 | `low` | 低风险，可自动执行 |
| 中 | `medium` | 中等风险，需 operator 审批 |
| 高 | `high` | 高风险，需 manager 审批 |
| 危急 | `critical` | 危急风险，需 admin 审批 |

### 7.3 ActionType (动作类型)

| 动作 | 值 | 说明 |
|------|-----|------|
| 重启 | `reboot` | 重启矿机 |
| 关机 | `power_off` | 关闭矿机电源 |
| 开机 | `power_on` | 开启矿机电源 |
| 调频 | `adjust_frequency` | 调整运行频率 |
| 调风扇 | `adjust_fan` | 调整风扇转速 |
| 切矿池 | `switch_pool` | 切换矿池 |
| 限电 | `curtail` | 执行限电关停 |
| 恢复 | `restore` | 恢复正常运行 |
| 仅告警 | `alert_only` | 仅发出告警 |
| 人工检查 | `manual_review` | 需要人工检查 |

---

## 附录

### A. API 请求示例 (cURL)

**登录后获取建议列表:**
```bash
curl -X GET "http://localhost:5000/api/v1/ai/recommendations?site_id=1&status=pending" \
  -H "Cookie: session=<your_session_token>"
```

**创建告警诊断:**
```bash
curl -X POST "http://localhost:5000/api/v1/ai/diagnose/alert" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your_session_token>" \
  -d '{
    "site_id": 1,
    "miner_id": "miner-001",
    "alert_type": "hashrate_drop"
  }'
```

**生成限电计划:**
```bash
curl -X POST "http://localhost:5000/api/v1/ai/curtailment/plan" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your_session_token>" \
  -d '{
    "site_id": 1,
    "target_reduction_kw": 500,
    "strategy": "efficiency_first"
  }'
```

---

*文档版本: 1.0*
*最后更新: 2026-01-27*
