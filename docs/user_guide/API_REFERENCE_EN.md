# HashInsight Enterprise API Reference

This document provides detailed descriptions of all major API endpoints for the HashInsight Enterprise platform.

---

## Table of Contents

1. [Authentication API](#1-authentication-api)
2. [CRM API](#2-crm-api)
3. [Hosting Service API](#3-hosting-service-api)
4. [AI Features API](#4-ai-features-api)
5. [Calculator API](#5-calculator-api)
6. [Telemetry Data API](#6-telemetry-data-api)
7. [Error Codes](#7-error-codes)

---

## 1. Authentication API

### 1.1 User Login

Users authenticate via email/password.

#### POST /login

**Description**: Process user login request

**Request Parameters** (Form Data):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| email | string | Yes | User email or username |
| password | string | Yes | User password |

**Request Example**:
```
POST /login
Content-Type: application/x-www-form-urlencoded

email=user@example.com&password=yourpassword
```

**Success Response**: Redirect to corresponding user dashboard

**Failure Response**: Return to login page with error message

**Authentication Required**: None (public endpoint)

---

### 1.2 User Logout

#### GET /logout

**Description**: End user session and logout

**Authentication Required**: Must be logged in

**Success Response**: Redirect to homepage

---

### 1.3 User Registration

#### POST /register

**Description**: Create new user account

**Request Parameters** (Form Data):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| email | string | Yes | User email |
| password | string | Yes | User password (must comply with password policy) |
| name | string | No | User name |

**Success Response**: Send verification email, redirect to login page

---

### 1.4 Email Verification

#### GET /verify-email/{token}

**Description**: Verify user email

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| token | string | Email verification token |

---

### 1.5 Password Reset

#### POST /forgot-password

**Description**: Request password reset link

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| email | string | Yes | User email |

#### POST /reset-password/{token}

**Description**: Reset password using token

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| token | string | Password reset token |

---

### 1.6 Web3 Wallet Authentication

#### POST /api/wallet/nonce

**Description**: Generate wallet login nonce

**Request Body**:
```json
{
  "wallet_address": "0x..."
}
```

**Response Example**:
```json
{
  "nonce": "random_nonce_string",
  "message": "Sign this message to login..."
}
```

#### POST /api/wallet/login

**Description**: Login using wallet signature

**Request Body**:
```json
{
  "wallet_address": "0x...",
  "signature": "0x...",
  "nonce": "random_nonce_string"
}
```

---

## 2. CRM API

Customer Relationship Management system API with multi-tenant isolation support.

### 2.1 Customer Management

#### GET /crm/api/customers

**Description**: Get customer list (supports multi-tenant isolation)

**Authentication Required**: Must be logged in

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| per_page | int | 50 | Items per page (max 100) |

**Response Example**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Customer A",
      "company": "ABC Company",
      "email": "customer@abc.com",
      "phone": "+1-555-0000-0000",
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

**Description**: Get single customer details

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| customer_id | int | Customer ID |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Customer A",
    "email": "customer@abc.com",
    "phone": "+1-555-0000-0000",
    "address": "123 Main Street",
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

**Description**: Create new customer

**Authentication Required**: Requires CRM_CUSTOMER_MGMT full permission

**Request Body**:
```json
{
  "name": "New Customer",
  "email": "new@example.com",
  "phone": "+1-555-0000-0000",
  "company": "New Company"
}
```

**Response Example**:
```json
{
  "success": true,
  "customer_id": 123,
  "message": "Customer created successfully"
}
```

---

### 2.2 Deal Management

#### GET /crm/api/deals

**Description**: Get deal list

**Authentication Required**: Requires CRM_TRANSACTION permission

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| per_page | int | 50 | Items per page |

**Response Example**:
```json
{
  "success": true,
  "deals": [
    {
      "id": 1,
      "title": "Miner Sales Contract",
      "customer_id": 1,
      "customer_name": "Customer A",
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

### 2.3 Lead Management

#### GET /crm/api/leads

**Description**: Get lead list

**Authentication Required**: Must be logged in

**Query Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status (NEW/CONTACTED/QUALIFIED/NEGOTIATION/WON/LOST) |

**Response Example**:
```json
{
  "success": true,
  "leads": [
    {
      "id": 1,
      "name": "Potential Customer",
      "email": "lead@example.com",
      "phone": "+1-555-0000-0000",
      "status": "NEW",
      "source": "website",
      "next_follow_up": "2025-02-01",
      "estimated_value": 100000.00
    }
  ]
}
```

---

### 2.4 Customer Analytics

#### GET /crm/api/customer/{customer_id}/revenue-trend

**Description**: Get customer revenue trend data (past 12 months)

**Response Example**:
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

**Description**: Get customer miner asset list

**Response Example**:
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

## 3. Hosting Service API

Miner hosting service related APIs.

### 3.1 Overview Data

#### GET /hosting/api/overview

**Description**: Get hosting service overview data

**Authentication Required**: Requires HOSTING_STATUS_MONITOR permission

**Response Example**:
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

### 3.2 Site Management

#### GET /hosting/api/sites

**Description**: Get hosting site list

**Authentication Required**: Requires HOSTING_SITE_MGMT permission

**Response Example**:
```json
{
  "success": true,
  "sites": [
    {
      "id": 1,
      "name": "Mining Farm A",
      "slug": "site-a",
      "location": "Texas",
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

**Description**: Create new site

**Authentication Required**: Requires HOSTING_SITE_MGMT full permission

**Request Body**:
```json
{
  "name": "New Mining Farm",
  "slug": "new-site",
  "location": "Wyoming",
  "capacity_mw": 10.0,
  "electricity_rate": 0.04,
  "operator_name": "Operator Name",
  "contact_email": "operator@example.com"
}
```

#### GET /hosting/api/sites/{site_id}

**Description**: Get site details

#### PUT /hosting/api/sites/{site_id}

**Description**: Update site information

---

### 3.3 Miner Management

#### GET /hosting/api/miners

**Description**: Get miner list (supports pagination and filtering)

**Query Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| site_id | int | Filter by site |
| customer_id | int | Filter by customer |
| status | string | Filter by status (active/inactive/maintenance) |
| model_id | int | Filter by model |
| page | int | Page number |
| per_page | int | Items per page |

**Response Example**:
```json
{
  "success": true,
  "miners": [
    {
      "id": 1,
      "sn": "MINER-001",
      "model": "Antminer S21",
      "site_id": 1,
      "site_name": "Mining Farm A",
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

**Description**: Create new miner record

**Request Body**:
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

**Description**: Batch import miners

**Request Body**:
```json
{
  "miners": [
    {"sn": "MINER-001", "model_id": 1, "site_id": 1},
    {"sn": "MINER-002", "model_id": 1, "site_id": 1}
  ]
}
```

---

### 3.4 Miner Control

#### POST /hosting/api/miners/{miner_id}/command

**Description**: Send control command to miner

**Request Body**:
```json
{
  "command": "restart",
  "params": {}
}
```

**Supported Commands**:
- `restart` - Restart miner
- `shutdown` - Shut down
- `start` - Start up
- `set_pool` - Set mining pool
- `set_fan` - Set fan speed

#### POST /hosting/api/miners/{miner_id}/start

**Description**: Start miner

#### POST /hosting/api/miners/{miner_id}/shutdown

**Description**: Shut down miner

#### POST /hosting/api/miners/{miner_id}/restart

**Description**: Restart miner

---

### 3.5 Events and Alerts

#### GET /hosting/api/incidents

**Description**: Get recent event/alert list

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Number to return |

**Response Example**:
```json
{
  "success": true,
  "incidents": [
    {
      "id": 1,
      "title": "High Temperature Alert",
      "description": "Miner temperature exceeded 90°C",
      "severity": "critical",
      "status": "open",
      "site_id": 1,
      "created_at": "2025-01-28T10:00:00Z"
    }
  ]
}
```

#### POST /hosting/api/monitoring/incidents

**Description**: Create new incident

---

### 3.6 Curtailment Management

#### POST /hosting/api/curtailment/calculate

**Description**: Calculate curtailment plan

**Request Body**:
```json
{
  "site_id": 1,
  "target_reduction_pct": 20,
  "strategy": "efficiency_first"
}
```

#### POST /hosting/api/curtailment/execute

**Description**: Execute curtailment plan

#### POST /hosting/api/curtailment/cancel

**Description**: Cancel curtailment

#### GET /hosting/api/curtailment/strategies

**Description**: Get curtailment strategy list

#### GET /hosting/api/curtailment/history

**Description**: Get curtailment history records

---

### 3.7 Power Monitoring

#### GET /hosting/api/power/overview

**Description**: Get power overview data

#### GET /hosting/api/power/consumption

**Description**: Get power consumption data

#### GET /hosting/api/power/rates

**Description**: Get electricity rate information

#### PUT /hosting/api/power/rates/{site_id}

**Description**: Update site electricity rate

---

### 3.8 Client API

#### GET /hosting/api/client/dashboard

**Description**: Get client dashboard data

**Response Example**:
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

**Description**: Get client's miner list

#### GET /hosting/api/client/usage

**Description**: Get client usage records

---

## 4. AI Features API

AI-assisted features API providing alert diagnostics, ticket generation, and curtailment suggestions.

### 4.1 Alert Diagnosis

#### POST /api/v1/ai/diagnose/alert

**Description**: Diagnose single alert, generate Top 3 root cause hypotheses

**Authentication Required**: Must be logged in

**Request Body**:
```json
{
  "site_id": 1,
  "miner_id": "MINER-001",
  "alert_type": "high_temperature",
  "alert_id": "ALT-12345"
}
```

**Request Parameter Description**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| site_id | int | Yes | Site ID |
| miner_id | string | Yes | Miner ID |
| alert_type | string | Yes | Alert type |
| alert_id | string | No | Alert ID |

**Response Example**:
```json
{
  "success": true,
  "diagnosis": {
    "alert_id": "ALT-12345",
    "miner_id": "MINER-001",
    "site_id": 1,
    "alert_type": "high_temperature",
    "diagnosed_at": "2025-01-28T10:30:00Z",
    "summary": "Miner temperature abnormality may be caused by cooling system failure",
    "summary_zh": "矿机温度异常可能由散热系统故障引起",
    "data_sources": ["telemetry", "historical_data"],
    "hypotheses": [
      {
        "rank": 1,
        "cause": "Fan failure",
        "probability": 0.65,
        "evidence": ["Fan speed dropped 50%", "Temperature continuously rising"],
        "recommended_action": "Check and replace fan"
      },
      {
        "rank": 2,
        "cause": "Heatsink dust accumulation",
        "probability": 0.25,
        "evidence": ["Operating time exceeds 6 months"],
        "recommended_action": "Clean heatsink"
      }
    ]
  }
}
```

---

#### POST /api/v1/ai/diagnose/batch

**Description**: Batch diagnose multiple miner alerts

**Request Body**:
```json
{
  "site_id": 1,
  "alert_type": "high_temperature",
  "miner_ids": ["MINER-001", "MINER-002", "MINER-003"]
}
```

**Response Example**:
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

### 4.2 Ticket Draft Generation

#### POST /api/v1/ai/ticket/draft

**Description**: Generate ticket draft, reducing "write ticket" from 10-20 minutes to 1-2 minutes

**Request Body**:
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

**Request Parameter Description**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| site_id | int | Yes | Site ID |
| miner_ids | array | Yes | Affected miner ID list |
| alert_type | string | Yes | Alert type |
| diagnosis | object | No | Diagnosis result (if available) |
| site_info | object | No | Site information |
| miner_info | object | No | Miner information |

**Response Example**:
```json
{
  "success": true,
  "ticket_draft": {
    "title": "[Mining Farm A] High Temperature Alert for 2 Miners",
    "priority": "high",
    "category": "hardware",
    "description": "...",
    "affected_miners": ["MINER-001", "MINER-002"],
    "root_cause_analysis": "...",
    "recommended_actions": ["..."],
    "estimated_resolution_time": "2 hours"
  }
}
```

---

### 4.3 Curtailment Plan Generation

#### POST /api/v1/ai/curtailment/plan

**Description**: Generate intelligent curtailment plan, including shutdown order and revenue loss estimation

**Request Body**:
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

**Strategy Options**:

| Strategy | Description |
|----------|-------------|
| efficiency_first | Efficiency first - shut down least efficient miners first |
| power_first | Power first - shut down highest power miners first |
| revenue_first | Revenue first - shut down lowest profit miners first |
| temperature_first | Temperature first - shut down highest temperature miners first |

**Response Example**:
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
    "risk_points": ["Prolonged shutdown of some miners may affect lifespan"]
  }
}
```

---

#### GET /api/v1/ai/curtailment/strategies

**Description**: Get available curtailment strategy list

**Response Example**:
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

## 5. Calculator API

BTC mining revenue calculation related APIs.

### 5.1 Single Miner Calculation

#### POST /calculate

**Description**: Calculate mining revenue

**Request Body** (supports JSON and Form Data):
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

**Request Parameter Description**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| hashrate | float | Yes | Hashrate |
| hashrate_unit | string | No | Hashrate unit (TH/s, PH/s, EH/s) |
| power-consumption | float | Yes | Power consumption (W) |
| electricity-cost | float | Yes | Electricity cost ($/kWh) |
| btc-price-input | float | No | BTC price (if not using real-time data) |
| use_real_time_data | bool | No | Whether to use real-time data |
| miner-model | string | No | Miner model |
| miner-count | int | No | Number of miners |
| curtailment | float | No | Curtailment ratio (%) |

**Response Example**:
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

### 5.2 Batch Calculation

#### POST /api/batch-calculate

**Description**: Batch calculate revenue for multiple miners

**Authentication Required**: Must be logged in + ANALYTICS_BATCH_CALC permission

**Request Body**:
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

**Response Example**:
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

### 5.3 Data Export

#### POST /api/export/batch-csv

**Description**: Export batch calculation results as CSV

**Authentication Required**: Requires REPORT_EXCEL permission

**Request Body**:
```json
{
  "results": [...]
}
```

**Response**: CSV file download

#### POST /api/export/batch-excel

**Description**: Export batch calculation results as Excel

---

### 5.4 Market Data

#### GET /api/get_btc_price

**Description**: Get current BTC price

**Response Example**:
```json
{
  "price": 45000.00,
  "source": "coingecko",
  "updated_at": "2025-01-28T10:30:00Z"
}
```

#### GET /api/get_network_stats

**Description**: Get Bitcoin network statistics

**Response Example**:
```json
{
  "difficulty": 75000000000000,
  "hashrate": 550,
  "block_reward": 3.125,
  "blocks_per_day": 144
}
```

---

## 6. Telemetry Data API

Unified telemetry data API providing single source of truth.

### 6.1 Real-time Data

#### GET /api/v1/telemetry/live

**Description**: Get miner current status (from real-time layer)

**Query Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| site_id | int | Filter by site |
| miner_id | string | Filter by miner |
| online | bool | Filter by online status |
| limit | int | Maximum return count (default 1000, max 5000) |

**Response Example**:
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

### 6.2 Historical Data

#### GET /api/v1/telemetry/history

**Description**: Get historical telemetry data

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| site_id | int | Yes | Site ID |
| miner_id | string | No | Miner ID |
| start | datetime | Yes | Start time (ISO format) |
| end | datetime | Yes | End time (ISO format) |
| resolution | string | No | Data resolution (5min/hourly/daily/auto) |

**Response Example**:
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

### 6.3 Site Summary

#### GET /api/v1/telemetry/site-summary

**Description**: Get site-level summary data

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| site_id | int | Yes | Site ID |

**Response Example**:
```json
{
  "site_id": 1,
  "site_name": "Mining Farm A",
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

### 6.4 Single Miner Details

#### GET /api/v1/telemetry/miner/{miner_id}

**Description**: Get detailed telemetry data for single miner

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| miner_id | string | Miner ID |

**Query Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| include_history | bool | Whether to include 24-hour historical data |

**Response Example**:
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

## 7. Error Codes

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad request parameters |
| 401 | Unauthorized - login required |
| 402 | Subscription upgrade required |
| 403 | Permission denied |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### Error Response Format

```json
{
  "success": false,
  "error": "error_code",
  "message": "Error description message"
}
```

### Common Error Codes

| Error Code | Description |
|------------|-------------|
| authentication_required | Login required |
| permission_denied | Permission denied |
| resource_not_found | Resource not found |
| invalid_request | Invalid request parameters |
| upgrade_required | Subscription upgrade required |
| rate_limit_exceeded | Rate limit exceeded |
| calculation_failed | Calculation failed |
| database_error | Database error |

---

## Appendix

### A. Authentication Notes

Most APIs require user authentication. Authentication methods:

1. **Session Authentication**: After logging in via `/login` endpoint, use session cookie for authentication
2. **JWT Authentication**: Some APIs support Bearer Token authentication

### B. Permission Modules

System uses RBAC (Role-Based Access Control) to manage permissions:

| Module | Description |
|--------|-------------|
| HOSTING_STATUS_MONITOR | Hosting status monitoring |
| HOSTING_SITE_MGMT | Site management |
| CRM_CUSTOMER_VIEW | Customer viewing |
| CRM_CUSTOMER_MGMT | Customer management |
| CRM_TRANSACTION | Deal management |
| ANALYTICS_BATCH_CALC | Batch calculation |
| REPORT_EXCEL | Excel report export |
| REPORT_PDF | PDF report export |

### C. Rate Limiting

- Unauthenticated users: 10 requests/hour
- Authenticated users: Varies by subscription plan

---

*Document Version: 1.0*
*Last Updated: January 28, 2025*
