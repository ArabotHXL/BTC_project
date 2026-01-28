# HashInsight Enterprise API 参考文档

本文档提供 HashInsight Enterprise 平台所有主要 API 端点的详细说明。

---

## 目录

1. [认证 API (Authentication)](#1-认证-api-authentication)
2. [CRM API](#2-crm-api)
3. [托管服务 API (Hosting)](#3-托管服务-api-hosting)
4. [AI 功能 API](#4-ai-功能-api)
5. [计算器 API (Calculator)](#5-计算器-api-calculator)
6. [遥测数据 API (Telemetry)](#6-遥测数据-api-telemetry)
7. [错误代码](#7-错误代码)

---

## 1. 认证 API (Authentication)

### 1.1 用户登录

用户通过邮箱/密码进行身份验证。

#### POST /login

**描述**: 处理用户登录请求

**请求参数** (Form Data):

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| email | string | 是 | 用户邮箱或用户名 |
| password | string | 是 | 用户密码 |

**请求示例**:
```
POST /login
Content-Type: application/x-www-form-urlencoded

email=user@example.com&password=yourpassword
```

**成功响应**: 重定向到对应的用户仪表板

**失败响应**: 返回登录页面并显示错误信息

**认证要求**: 无（公开端点）

---

### 1.2 用户登出

#### GET /logout

**描述**: 结束用户会话并登出

**认证要求**: 需要登录

**成功响应**: 重定向到首页

---

### 1.3 用户注册

#### POST /register

**描述**: 创建新用户账户

**请求参数** (Form Data):

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| email | string | 是 | 用户邮箱 |
| password | string | 是 | 用户密码（需符合密码策略） |
| name | string | 否 | 用户姓名 |

**成功响应**: 发送验证邮件，重定向到登录页面

---

### 1.4 邮箱验证

#### GET /verify-email/{token}

**描述**: 验证用户邮箱

**路径参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| token | string | 邮箱验证令牌 |

---

### 1.5 密码重置

#### POST /forgot-password

**描述**: 请求密码重置链接

**请求参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| email | string | 是 | 用户邮箱 |

#### POST /reset-password/{token}

**描述**: 使用令牌重置密码

**路径参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| token | string | 密码重置令牌 |

---

### 1.6 Web3 钱包认证

#### POST /api/wallet/nonce

**描述**: 生成钱包登录 nonce

**请求体**:
```json
{
  "wallet_address": "0x..."
}
```

**响应示例**:
```json
{
  "nonce": "random_nonce_string",
  "message": "Sign this message to login..."
}
```

#### POST /api/wallet/login

**描述**: 使用钱包签名登录

**请求体**:
```json
{
  "wallet_address": "0x...",
  "signature": "0x...",
  "nonce": "random_nonce_string"
}
```

---

## 2. CRM API

客户关系管理系统 API，支持多租户隔离。

### 2.1 客户管理

#### GET /crm/api/customers

**描述**: 获取客户列表（支持多租户隔离）

**认证要求**: 需要登录

**查询参数**:

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| per_page | int | 50 | 每页数量（最大100） |

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "客户A",
      "company": "ABC公司",
      "email": "customer@abc.com",
      "phone": "+86-138-0000-0000",
      "customer_type": "enterprise",
      "mining_capacity": 10.5,
      "join_date": "2025-01-15",
      "total_revenue": 50000.00,
      "status": "active",
      "electricity_cost": 0.05,
      "miners_count": 100
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 50
}
```

---

#### GET /crm/api/customer/{customer_id}

**描述**: 获取单个客户详情

**路径参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| customer_id | int | 客户ID |

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "客户A",
    "email": "customer@abc.com",
    "phone": "+86-138-0000-0000",
    "address": "北京市朝阳区",
    "status": "active",
    "tier": "enterprise",
    "join_date": "2025-01-15",
    "total_revenue": 50000.00,
    "mining_capacity": 10.5,
    "electricity_cost": 0.05,
    "contracts": [...],
    "notes": [...]
  }
}
```

---

#### POST /crm/api/customer

**描述**: 创建新客户

**认证要求**: 需要 CRM_CUSTOMER_MGMT 完全权限

**请求体**:
```json
{
  "name": "新客户",
  "email": "new@example.com",
  "phone": "+86-138-0000-0000",
  "company": "新公司"
}
```

**响应示例**:
```json
{
  "success": true,
  "customer_id": 123,
  "message": "客户创建成功"
}
```

---

### 2.2 交易管理

#### GET /crm/api/deals

**描述**: 获取交易列表

**认证要求**: 需要 CRM_TRANSACTION 权限

**查询参数**:

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| per_page | int | 50 | 每页数量 |

**响应示例**:
```json
{
  "success": true,
  "deals": [
    {
      "id": 1,
      "title": "矿机销售合同",
      "customer_id": 1,
      "customer_name": "客户A",
      "amount": 50000.00,
      "stage": "negotiation",
      "probability": 70,
      "expected_close": "2025-03-15"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 100,
    "pages": 2,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### 2.3 线索管理

#### GET /crm/api/leads

**描述**: 获取线索列表

**认证要求**: 需要登录

**查询参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| status | string | 筛选状态 (NEW/CONTACTED/QUALIFIED/NEGOTIATION/WON/LOST) |

**响应示例**:
```json
{
  "success": true,
  "leads": [
    {
      "id": 1,
      "name": "潜在客户",
      "email": "lead@example.com",
      "phone": "+86-138-0000-0000",
      "status": "NEW",
      "source": "website",
      "next_follow_up": "2025-02-01",
      "estimated_value": 100000.00
    }
  ]
}
```

---

### 2.4 客户分析

#### GET /crm/api/customer/{customer_id}/revenue-trend

**描述**: 获取客户收入趋势数据（过去12个月）

**响应示例**:
```json
{
  "success": true,
  "months": ["Jan 2025", "Feb 2025", ...],
  "miner_sales": [10000, 15000, ...],
  "hosting_fees": [5000, 6000, ...],
  "total_investment": 150000.00,
  "total_return": 172500.00,
  "roi_percent": 15.00,
  "breakeven_months": 18,
  "annual_projection": 120000.00
}
```

#### GET /crm/api/customer/{customer_id}/assets

**描述**: 获取客户矿机资产列表

**响应示例**:
```json
{
  "success": true,
  "assets": [
    {
      "id": 1,
      "model": "Antminer S21",
      "quantity": 10,
      "status": "active",
      "location": "Site A",
      "power_w": 35500,
      "hashrate_th": 2000
    }
  ],
  "total_power": 35500,
  "total_hashrate": 2000,
  "utilization_rate": 85.5
}
```

---

## 3. 托管服务 API (Hosting)

矿机托管服务相关 API。

### 3.1 总览数据

#### GET /hosting/api/overview

**描述**: 获取托管服务总览数据

**认证要求**: 需要 HOSTING_STATUS_MONITOR 权限

**响应示例**:
```json
{
  "success": true,
  "data": {
    "sites": {
      "total": 5,
      "online": 4,
      "offline": 1
    },
    "miners": {
      "total": 1000,
      "active": 950,
      "inactive": 50
    },
    "capacity": {
      "total_mw": 10.0,
      "used_mw": 8.5,
      "utilization_rate": 85.0
    },
    "alerts": {
      "recent_incidents": 3,
      "pending_tickets": 5
    }
  }
}
```

---

### 3.2 站点管理

#### GET /hosting/api/sites

**描述**: 获取托管站点列表

**认证要求**: 需要 HOSTING_SITE_MGMT 权限

**响应示例**:
```json
{
  "success": true,
  "sites": [
    {
      "id": 1,
      "name": "矿场A",
      "slug": "site-a",
      "location": "内蒙古",
      "status": "online",
      "capacity_mw": 5.0,
      "used_capacity_mw": 4.2,
      "device_count": 500,
      "active_devices": 480,
      "electricity_rate": 0.05
    }
  ]
}
```

#### POST /hosting/api/sites

**描述**: 创建新站点

**认证要求**: 需要 HOSTING_SITE_MGMT 完全权限

**请求体**:
```json
{
  "name": "新矿场",
  "slug": "new-site",
  "location": "四川",
  "capacity_mw": 10.0,
  "electricity_rate": 0.04,
  "operator_name": "运营商名称",
  "contact_email": "operator@example.com"
}
```

#### GET /hosting/api/sites/{site_id}

**描述**: 获取站点详情

#### PUT /hosting/api/sites/{site_id}

**描述**: 更新站点信息

---

### 3.3 矿机管理

#### GET /hosting/api/miners

**描述**: 获取矿机列表（支持分页和过滤）

**查询参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| site_id | int | 按站点筛选 |
| customer_id | int | 按客户筛选 |
| status | string | 按状态筛选 (active/inactive/maintenance) |
| model_id | int | 按型号筛选 |
| page | int | 页码 |
| per_page | int | 每页数量 |

**响应示例**:
```json
{
  "success": true,
  "miners": [
    {
      "id": 1,
      "sn": "MINER-001",
      "model": "Antminer S21",
      "site_id": 1,
      "site_name": "矿场A",
      "status": "active",
      "actual_hashrate": 195.5,
      "temperature_max": 75.2,
      "power_consumption": 3520,
      "last_seen": "2025-01-28T10:30:00Z",
      "alerts": {
        "has_alerts": false,
        "count": 0
      }
    }
  ],
  "pagination": {...}
}
```

#### POST /hosting/api/miners/create

**描述**: 创建新矿机记录

**请求体**:
```json
{
  "sn": "MINER-001",
  "model_id": 1,
  "site_id": 1,
  "customer_id": 1,
  "ip_address": "192.168.1.100",
  "location_slot": "A1-01"
}
```

#### POST /hosting/api/miners/batch

**描述**: 批量导入矿机

**请求体**:
```json
{
  "miners": [
    {"sn": "MINER-001", "model_id": 1, "site_id": 1},
    {"sn": "MINER-002", "model_id": 1, "site_id": 1}
  ]
}
```

---

### 3.4 矿机控制

#### POST /hosting/api/miners/{miner_id}/command

**描述**: 发送控制命令到矿机

**请求体**:
```json
{
  "command": "restart",
  "params": {}
}
```

**支持的命令**:
- `restart` - 重启矿机
- `shutdown` - 关机
- `start` - 启动
- `set_pool` - 设置矿池
- `set_fan` - 设置风扇速度

#### POST /hosting/api/miners/{miner_id}/start

**描述**: 启动矿机

#### POST /hosting/api/miners/{miner_id}/shutdown

**描述**: 关闭矿机

#### POST /hosting/api/miners/{miner_id}/restart

**描述**: 重启矿机

---

### 3.5 事件与告警

#### GET /hosting/api/incidents

**描述**: 获取最近事件/告警列表

**查询参数**:

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| limit | int | 10 | 返回数量 |

**响应示例**:
```json
{
  "success": true,
  "incidents": [
    {
      "id": 1,
      "title": "高温告警",
      "description": "矿机温度超过90°C",
      "severity": "critical",
      "status": "open",
      "site_id": 1,
      "created_at": "2025-01-28T10:00:00Z"
    }
  ]
}
```

#### POST /hosting/api/monitoring/incidents

**描述**: 创建新事件

---

### 3.6 限电管理

#### POST /hosting/api/curtailment/calculate

**描述**: 计算限电方案

**请求体**:
```json
{
  "site_id": 1,
  "target_reduction_pct": 20,
  "strategy": "efficiency_first"
}
```

#### POST /hosting/api/curtailment/execute

**描述**: 执行限电方案

#### POST /hosting/api/curtailment/cancel

**描述**: 取消限电

#### GET /hosting/api/curtailment/strategies

**描述**: 获取限电策略列表

#### GET /hosting/api/curtailment/history

**描述**: 获取限电历史记录

---

### 3.7 电力监控

#### GET /hosting/api/power/overview

**描述**: 获取电力总览数据

#### GET /hosting/api/power/consumption

**描述**: 获取电力消耗数据

#### GET /hosting/api/power/rates

**描述**: 获取电价信息

#### PUT /hosting/api/power/rates/{site_id}

**描述**: 更新站点电价

---

### 3.8 客户端 API

#### GET /hosting/api/client/dashboard

**描述**: 获取客户仪表板数据

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_miners": 50,
    "active_miners": 48,
    "total_hashrate": 10000,
    "total_power": 175000,
    "daily_revenue": 0.05,
    "monthly_revenue": 1.5
  }
}
```

#### GET /hosting/api/client/miners

**描述**: 获取客户拥有的矿机列表

#### GET /hosting/api/client/usage

**描述**: 获取客户使用记录

---

## 4. AI 功能 API

AI 辅助功能 API，提供告警诊断、工单生成和限电建议。

### 4.1 告警诊断

#### POST /api/v1/ai/diagnose/alert

**描述**: 诊断单个告警，生成 Top3 根因假设

**认证要求**: 需要用户登录

**请求体**:
```json
{
  "site_id": 1,
  "miner_id": "MINER-001",
  "alert_type": "high_temperature",
  "alert_id": "ALT-12345"
}
```

**请求参数说明**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| site_id | int | 是 | 站点ID |
| miner_id | string | 是 | 矿机ID |
| alert_type | string | 是 | 告警类型 |
| alert_id | string | 否 | 告警ID |

**响应示例**:
```json
{
  "success": true,
  "diagnosis": {
    "alert_id": "ALT-12345",
    "miner_id": "MINER-001",
    "site_id": 1,
    "alert_type": "high_temperature",
    "diagnosed_at": "2025-01-28T10:30:00Z",
    "summary": "矿机温度异常可能由散热系统故障引起",
    "summary_zh": "矿机温度异常可能由散热系统故障引起",
    "data_sources": ["telemetry", "historical_data"],
    "hypotheses": [
      {
        "rank": 1,
        "cause": "风扇故障",
        "probability": 0.65,
        "evidence": ["风扇转速下降50%", "温度持续上升"],
        "recommended_action": "检查并更换风扇"
      },
      {
        "rank": 2,
        "cause": "散热片积尘",
        "probability": 0.25,
        "evidence": ["运行时间超过6个月"],
        "recommended_action": "清洁散热片"
      }
    ]
  }
}
```

---

#### POST /api/v1/ai/diagnose/batch

**描述**: 批量诊断多台矿机告警

**请求体**:
```json
{
  "site_id": 1,
  "alert_type": "high_temperature",
  "miner_ids": ["MINER-001", "MINER-002", "MINER-003"]
}
```

**响应示例**:
```json
{
  "success": true,
  "diagnoses": {
    "MINER-001": {...},
    "MINER-002": {...},
    "MINER-003": {...}
  },
  "count": 3
}
```

---

### 4.2 工单草稿生成

#### POST /api/v1/ai/ticket/draft

**描述**: 生成工单草稿，将"写工单"从10-20分钟压缩到1-2分钟

**请求体**:
```json
{
  "site_id": 1,
  "miner_ids": ["MINER-001", "MINER-002"],
  "alert_type": "high_temperature",
  "diagnosis": {...},
  "site_info": {...},
  "miner_info": {...}
}
```

**请求参数说明**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| site_id | int | 是 | 站点ID |
| miner_ids | array | 是 | 受影响矿机ID列表 |
| alert_type | string | 是 | 告警类型 |
| diagnosis | object | 否 | 诊断结果（如果已有） |
| site_info | object | 否 | 站点信息 |
| miner_info | object | 否 | 矿机信息 |

**响应示例**:
```json
{
  "success": true,
  "ticket_draft": {
    "title": "[矿场A] 2台矿机高温告警处理",
    "priority": "high",
    "category": "hardware",
    "description": "...",
    "affected_miners": ["MINER-001", "MINER-002"],
    "root_cause_analysis": "...",
    "recommended_actions": ["..."],
    "estimated_resolution_time": "2小时"
  }
}
```

---

### 4.3 限电计划生成

#### POST /api/v1/ai/curtailment/plan

**描述**: 生成智能限电计划，包含关停顺序和收益损失预估

**请求体**:
```json
{
  "site_id": 1,
  "target_reduction_kw": 500,
  "target_power_kw": 4000,
  "target_reduction_pct": 20,
  "electricity_price": 0.05,
  "btc_price": 45000,
  "strategy": "efficiency_first",
  "max_miners_to_curtail": 50,
  "exclude_miner_ids": ["MINER-VIP-001"]
}
```

**策略选项**:

| 策略 | 描述 |
|------|------|
| efficiency_first | 效率优先 - 先关效率最差的矿机 |
| power_first | 功率优先 - 先关功率最大的矿机 |
| revenue_first | 收益优先 - 先关利润最低的矿机 |
| temperature_first | 温度优先 - 先关温度最高的矿机 |

**响应示例**:
```json
{
  "success": true,
  "curtailment_plan": {
    "site_id": 1,
    "target_reduction_kw": 500,
    "actual_reduction_kw": 498,
    "miners_to_curtail": [
      {
        "miner_id": "MINER-100",
        "model": "Antminer S19",
        "power_kw": 3.25,
        "efficiency_jth": 34.5,
        "daily_profit_loss": 5.20
      }
    ],
    "total_miners_affected": 15,
    "estimated_daily_revenue_loss": 78.00,
    "estimated_daily_cost_savings": 120.00,
    "net_impact": 42.00,
    "risk_points": ["部分矿机长时间关机可能影响寿命"]
  }
}
```

---

#### GET /api/v1/ai/curtailment/strategies

**描述**: 获取可用的限电策略列表

**响应示例**:
```json
{
  "strategies": [
    {
      "id": "efficiency_first",
      "name": "Efficiency First",
      "name_zh": "效率优先",
      "description": "Shut down miners with worst efficiency first",
      "description_zh": "优先关停效率最差的矿机"
    }
  ]
}
```

---

## 5. 计算器 API (Calculator)

BTC 挖矿收益计算相关 API。

### 5.1 单机计算

#### POST /calculate

**描述**: 计算挖矿收益

**请求体** (支持 JSON 和 Form Data):
```json
{
  "hashrate": 200,
  "hashrate_unit": "TH/s",
  "power-consumption": 3550,
  "electricity-cost": 0.05,
  "btc-price-input": 45000,
  "use_real_time_data": true,
  "miner-model": "Antminer S21",
  "miner-count": 10,
  "curtailment": 0
}
```

**请求参数说明**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| hashrate | float | 是 | 算力 |
| hashrate_unit | string | 否 | 算力单位 (TH/s, PH/s, EH/s) |
| power-consumption | float | 是 | 功耗 (W) |
| electricity-cost | float | 是 | 电费 ($/kWh) |
| btc-price-input | float | 否 | BTC价格（如果不使用实时数据） |
| use_real_time_data | bool | 否 | 是否使用实时数据 |
| miner-model | string | 否 | 矿机型号 |
| miner-count | int | 否 | 矿机数量 |
| curtailment | float | 否 | 限电比例 (%) |

**响应示例**:
```json
{
  "success": true,
  "timestamp": "2025-01-28T10:30:00Z",
  "btc_mined": {
    "daily": 0.00025,
    "monthly": 0.0075,
    "yearly": 0.09125
  },
  "revenue": {
    "daily": 11.25,
    "monthly": 337.50,
    "yearly": 4106.25
  },
  "client_electricity_cost": {
    "daily": 4.26,
    "monthly": 127.80,
    "yearly": 1554.90
  },
  "client_profit": {
    "daily": 6.99,
    "monthly": 209.70,
    "yearly": 2551.35
  },
  "network_data": {
    "btc_price": 45000,
    "network_difficulty": 75000000000000,
    "network_hashrate": 550,
    "block_reward": 3.125
  },
  "break_even": {
    "btc_price": 18500,
    "electricity_cost": 0.12
  },
  "roi": {
    "client": {
      "payback_period_months": 18
    }
  }
}
```

---

### 5.2 批量计算

#### POST /api/batch-calculate

**描述**: 批量计算多台矿机收益

**认证要求**: 需要登录 + ANALYTICS_BATCH_CALC 权限

**请求体**:
```json
{
  "miners": [
    {
      "model": "Antminer S21",
      "quantity": 100,
      "power_consumption": 3550,
      "electricity_cost": 0.05,
      "hashrate": 200,
      "decay_rate": 0,
      "machine_price": 3200
    },
    {
      "model": "WhatsMiner M53S",
      "quantity": 50,
      "power_consumption": 6554,
      "electricity_cost": 0.05
    }
  ],
  "settings": {}
}
```

**响应示例**:
```json
{
  "success": true,
  "results": [
    {
      "model": "Antminer S21",
      "quantity": 100,
      "daily_profit": 699.00,
      "daily_revenue": 1125.00,
      "daily_cost": 426.00,
      "monthly_profit": 20970.00,
      "roi_days": 480,
      "hash_rate": 20000
    }
  ],
  "summary": {
    "total_miners": 150,
    "total_daily_profit": 950.00,
    "total_monthly_profit": 28500.00,
    "unique_groups": 2,
    "average_roi_days": 520
  }
}
```

---

### 5.3 数据导出

#### POST /api/export/batch-csv

**描述**: 导出批量计算结果为 CSV

**认证要求**: 需要 REPORT_EXCEL 权限

**请求体**:
```json
{
  "results": [...]
}
```

**响应**: CSV 文件下载

#### POST /api/export/batch-excel

**描述**: 导出批量计算结果为 Excel

---

### 5.4 市场数据

#### GET /api/get_btc_price

**描述**: 获取当前 BTC 价格

**响应示例**:
```json
{
  "price": 45000.00,
  "source": "coingecko",
  "updated_at": "2025-01-28T10:30:00Z"
}
```

#### GET /api/get_network_stats

**描述**: 获取比特币网络统计数据

**响应示例**:
```json
{
  "difficulty": 75000000000000,
  "hashrate": 550,
  "block_reward": 3.125,
  "blocks_per_day": 144
}
```

---

## 6. 遥测数据 API (Telemetry)

统一遥测数据 API，提供单一数据真相。

### 6.1 实时数据

#### GET /api/v1/telemetry/live

**描述**: 获取矿机当前状态（来自实时层）

**查询参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| site_id | int | 按站点筛选 |
| miner_id | string | 按矿机筛选 |
| online | bool | 筛选在线状态 |
| limit | int | 最大返回数量（默认1000，最大5000） |

**响应示例**:
```json
{
  "miners": [
    {
      "miner_id": "MINER-001",
      "site_id": 1,
      "hashrate_5m": 195.5,
      "temperature_chip": 72.5,
      "temperature_board": 65.0,
      "power_consumption": 3520,
      "fan_speed": [5500, 5480, 5520],
      "pool_url": "stratum+tcp://pool.example.com:3333",
      "reject_rate": 0.02,
      "efficiency": 18.0,
      "online": true,
      "last_seen": "2025-01-28T10:29:55Z"
    }
  ],
  "count": 1,
  "_meta": {
    "source": "miner_telemetry_live",
    "updated_at": "2025-01-28T10:30:00Z",
    "unit_definitions": {
      "hashrate": "TH/s (5-minute average)",
      "temperature": "Celsius",
      "power": "Watts",
      "efficiency": "Joules per TH",
      "reject_rate": "Ratio (0-1)"
    }
  }
}
```

---

### 6.2 历史数据

#### GET /api/v1/telemetry/history

**描述**: 获取历史遥测数据

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| site_id | int | 是 | 站点ID |
| miner_id | string | 否 | 矿机ID |
| start | datetime | 是 | 开始时间 (ISO格式) |
| end | datetime | 是 | 结束时间 (ISO格式) |
| resolution | string | 否 | 数据分辨率 (5min/hourly/daily/auto) |

**响应示例**:
```json
{
  "site_id": 1,
  "start": "2025-01-27T00:00:00Z",
  "end": "2025-01-28T00:00:00Z",
  "resolution": "hourly",
  "data": [
    {
      "timestamp": "2025-01-27T00:00:00Z",
      "avg_hashrate": 195.2,
      "avg_temperature": 71.5,
      "avg_power": 3500,
      "online_count": 950,
      "total_count": 1000
    }
  ],
  "_meta": {
    "source": "miner_telemetry_hourly",
    "points": 24
  }
}
```

---

### 6.3 站点汇总

#### GET /api/v1/telemetry/site-summary

**描述**: 获取站点级别汇总数据

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| site_id | int | 是 | 站点ID |

**响应示例**:
```json
{
  "site_id": 1,
  "site_name": "矿场A",
  "total_miners": 1000,
  "online_miners": 950,
  "offline_miners": 50,
  "total_hashrate": 195000,
  "total_power": 3500000,
  "avg_temperature": 72.5,
  "avg_efficiency": 17.95,
  "uptime_rate": 0.95,
  "_meta": {
    "source": "miner_telemetry_live",
    "updated_at": "2025-01-28T10:30:00Z"
  }
}
```

---

### 6.4 单机详情

#### GET /api/v1/telemetry/miner/{miner_id}

**描述**: 获取单台矿机详细遥测数据

**路径参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| miner_id | string | 矿机ID |

**查询参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| include_history | bool | 是否包含24小时历史数据 |

**响应示例**:
```json
{
  "miner": {
    "miner_id": "MINER-001",
    "site_id": 1,
    "hashrate_5m": 195.5,
    "temperature_chip": 72.5,
    "power_consumption": 3520
  },
  "history_24h": {...},
  "_meta": {
    "source": "miner_telemetry_live",
    "updated_at": "2025-01-28T10:30:00Z"
  }
}
```

---

## 7. 错误代码

### HTTP 状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 - 需要登录 |
| 402 | 需要升级订阅计划 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "success": false,
  "error": "error_code",
  "message": "错误描述信息"
}
```

### 常见错误代码

| 错误代码 | 描述 |
|----------|------|
| authentication_required | 需要登录 |
| permission_denied | 权限不足 |
| resource_not_found | 资源不存在 |
| invalid_request | 请求参数无效 |
| upgrade_required | 需要升级订阅计划 |
| rate_limit_exceeded | 请求频率超限 |
| calculation_failed | 计算失败 |
| database_error | 数据库错误 |

---

## 附录

### A. 认证说明

大部分 API 需要用户认证。认证方式：

1. **Session 认证**: 通过 `/login` 端点登录后，使用 cookie 中的 session 进行认证
2. **JWT 认证**: 部分 API 支持 Bearer Token 认证

### B. 权限模块

系统使用 RBAC (基于角色的访问控制) 管理权限：

| 模块 | 描述 |
|------|------|
| HOSTING_STATUS_MONITOR | 托管状态监控 |
| HOSTING_SITE_MGMT | 站点管理 |
| CRM_CUSTOMER_VIEW | 客户查看 |
| CRM_CUSTOMER_MGMT | 客户管理 |
| CRM_TRANSACTION | 交易管理 |
| ANALYTICS_BATCH_CALC | 批量计算 |
| REPORT_EXCEL | Excel 报表导出 |
| REPORT_PDF | PDF 报表导出 |

### C. 速率限制

- 未登录用户: 10次/小时
- 登录用户: 根据订阅计划不同

---

*文档版本: 1.0*
*最后更新: 2025年1月28日*
