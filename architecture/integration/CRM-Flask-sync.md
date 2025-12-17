# CRM-Flask Hosting Integration Sync Documentation

## Overview

This document describes the bidirectional synchronization between the CRM module and the Hosting module. The integration enables mine owners to view customer mining operations directly in CRM, providing real-time visibility into customer assets and performance.

## Architecture

```
┌─────────────────┐    email match     ┌─────────────────┐
│  CRM Customer   │◄──────────────────►│   UserAccess    │
│  (customer.email)                    │  (user.email)   │
└─────────────────┘                    └────────┬────────┘
                                                │
                                                │ user_id FK
                                                ▼
                                       ┌─────────────────┐
                                       │   UserMiner     │
                                       │ (mining assets) │
                                       └─────────────────┘
```

## Data Flow

### CRM → Hosting (Read Operations)

The CRM can query hosting data for any customer with a matching email in UserAccess:

1. **Customer Stats**: Aggregate mining statistics (hashrate, power, revenue)
2. **Miner List**: Detailed list of customer's mining equipment
3. **Performance Data**: Real-time operational metrics

### Hosting → CRM (Sync Operations)

Hosting data can be synced back to CRM to update customer records:

1. **Miners Count**: Total number of miners owned
2. **Primary Model**: Most common miner model
3. **Revenue Estimates**: Calculated from hashrate and BTC price

## API Endpoints

### 1. Get Customer Hosting Stats

**Endpoint**: `GET /crm/api/customer/<customer_id>/hosting-stats`

**Description**: Retrieves comprehensive hosting statistics for a CRM customer.

**Request**:
```http
GET /crm/api/customer/123/hosting-stats
Authorization: Session-based
```

**Response Schema**:
```json
{
  "success": true,
  "data": {
    "has_hosting": true,
    "user_access_id": 456,
    "miners_count": 50,
    "total_hashrate": 5000.0,
    "total_power": 7500000,
    "total_power_mw": 7.5,
    "active_miners": 48,
    "offline_miners": 2,
    "maintenance_miners": 0,
    "estimated_daily_btc": 0.05,
    "estimated_daily_usd": 4750.0,
    "avg_efficiency": 15.0,
    "by_model": {
      "Antminer S19 XP": { "count": 30, "hashrate": 4200, "power": 4350000 },
      "Antminer S21": { "count": 20, "hashrate": 800, "power": 3150000 }
    },
    "by_status": { "active": 48, "offline": 2, "maintenance": 0, "sold": 0 },
    "electricity_cost_daily": 900.0,
    "net_profit_daily": 3850.0,
    "btc_price": 95000
  }
}
```

### 2. Get Customer Miners List

**Endpoint**: `GET /crm/api/customer/<customer_id>/hosting-miners`

**Description**: Returns detailed list of customer's mining equipment.

**Query Parameters**:
- `status` (optional): Filter by miner status (active, offline, maintenance, sold)

**Request**:
```http
GET /crm/api/customer/123/hosting-miners?status=active
Authorization: Session-based
```

**Response Schema**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1001,
      "name": "Farm A - Rack 1",
      "model": "Antminer S19 XP",
      "quantity": 10,
      "hashrate": 140,
      "total_hashrate": 1400,
      "power": 3050,
      "total_power": 30500,
      "status": "active",
      "location": "Texas DC-01",
      "electricity_cost": 0.045,
      "daily_electricity_cost": 32.94
    }
  ]
}
```

### 3. Sync Customer Hosting Data

**Endpoint**: `POST /crm/api/customer/<customer_id>/sync-hosting`

**Description**: Synchronizes hosting data to update CRM customer record fields.

**Request**:
```http
POST /crm/api/customer/123/sync-hosting
Authorization: Session-based
Content-Type: application/json
```

**Response Schema**:
```json
{
  "success": true,
  "message": "托管数据同步成功"
}
```

**Error Response** (no linked account):
```json
{
  "success": false,
  "error": "未找到关联的托管账户或无矿机数据"
}
```

### 4. Batch Sync All Customers

**Endpoint**: `POST /crm/api/sync-all-hosting`

**Description**: Synchronizes hosting data for all customers with linked accounts.

**Request**:
```http
POST /crm/api/sync-all-hosting
Authorization: Session-based
Content-Type: application/json
```

**Response Schema**:
```json
{
  "success": true,
  "data": {
    "total": 150,
    "synced": 45,
    "skipped": 105,
    "errors": 0
  },
  "message": "已同步 45 个客户的托管数据"
}
```

### 5. Sync Status Check (NEW)

**Endpoint**: `GET /crm/api/sync-status`

**Description**: Returns the current sync status between CRM and Hosting modules.

**Request**:
```http
GET /crm/api/sync-status
Authorization: Session-based
```

**Response Schema**:
```json
{
  "success": true,
  "data": {
    "total_customers": 150,
    "linked_customers": 45,
    "unlinked_customers": 105,
    "link_rate": 30.0,
    "last_sync": "2025-12-12T10:30:00Z",
    "sync_health": "healthy",
    "issues": []
  }
}
```

## Data Validation Schemas

### HostingStatsSchema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| has_hosting | boolean | Yes | Whether customer has hosting account |
| user_access_id | integer | No | Linked UserAccess ID |
| miners_count | integer | Yes | Total number of miners |
| total_hashrate | float | Yes | Total hashrate in TH/s |
| total_power | integer | Yes | Total power in Watts |
| active_miners | integer | Yes | Count of active miners |
| offline_miners | integer | Yes | Count of offline miners |
| estimated_daily_btc | float | Yes | Estimated daily BTC revenue |
| estimated_daily_usd | float | Yes | Estimated daily USD revenue |

### MinerDataSchema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | integer | Yes | Miner record ID |
| name | string | Yes | Custom name or model name |
| model | string | Yes | Miner model name |
| quantity | integer | Yes | Number of units |
| hashrate | float | Yes | Per-unit hashrate TH/s |
| total_hashrate | float | Yes | Quantity × hashrate |
| power | integer | Yes | Per-unit power in Watts |
| status | string | Yes | active/offline/maintenance/sold |

## Service Layer

### CRMHostingIntegrationService

Located at: `crm_services/hosting_integration.py`

**Methods**:

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_linked_user_access` | customer | UserAccess\|None | Find UserAccess by email match |
| `get_customer_hosting_stats` | customer_id | Dict | Aggregate hosting statistics |
| `get_customer_miners_list` | customer_id, status | List[Dict] | List miners with optional filter |
| `sync_customer_from_hosting` | customer_id | bool | Sync hosting data to CRM record |
| `sync_all_customers` | - | Dict | Batch sync all customers |
| `get_sync_status` | - | Dict | Get current sync health status |

## Error Handling

### Error Codes

| HTTP Code | Error Type | Description |
|-----------|------------|-------------|
| 401 | Not authenticated | Session expired or missing |
| 403 | Access denied | User lacks permission for resource |
| 404 | Not found | Customer or linked account not found |
| 500 | Internal error | Server-side processing error |

### Error Response Format

```json
{
  "success": false,
  "error": "Human-readable error message"
}
```

## Security

### Authentication
- All endpoints require session-based authentication
- User must be logged in (`user_id` in session)

### Authorization
- Tenant isolation via `verify_resource_access()` function
- Users can only access customers they created (unless admin/owner)
- RBAC integration with enterprise roles

## Monitoring

### Health Indicators

1. **Link Rate**: Percentage of customers with linked hosting accounts
2. **Sync Freshness**: Time since last batch sync
3. **Error Rate**: Failed sync operations over time

### Recommended Alerts

- Link rate drops below 20%
- Sync errors exceed 5% of operations
- Last batch sync older than 24 hours

## Best Practices

1. **Email Matching**: Ensure consistent email format between CRM and Hosting
2. **Regular Sync**: Run batch sync daily to keep data current
3. **Error Monitoring**: Review sync_all_hosting results for failures
4. **Data Validation**: Validate response schemas on client side
