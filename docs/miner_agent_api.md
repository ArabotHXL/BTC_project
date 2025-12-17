# 🔌 Miner Agent API 接口规范

## 📋 文档信息

- **版本**: 1.0.0
- **日期**: 2025-10-13
- **Base URL**: `https://hashinsight.replit.app/agent/api`
- **协议**: HTTPS
- **认证**: JWT Bearer Token

---

## 📖 API 概览

### 端点分类

| 分类 | 前缀 | 描述 | 认证要求 |
|------|------|------|---------|
| **认证管理** | `/auth` | Agent 注册、Token 刷新 | 初始 Token |
| **心跳监控** | `/heartbeat` | 心跳上报、状态检查 | Agent Token |
| **遥测数据** | `/telemetry` | 矿机数据上报、查询 | Agent Token |
| **控制指令** | `/commands` | 指令下发、结果上报 | Agent Token |
| **配置管理** | `/config` | 配置获取、版本管理 | Agent Token |
| **事件告警** | `/events` | 事件上报、告警查询 | Agent Token |
| **管理接口** | `/admin` | Agent 管理、统计查询 | User Token |

### 认证机制

所有 API 请求（除注册接口外）必须在 Header 中携带 JWT Token:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 通用响应格式

**成功响应**:
```json
{
  "status": "success",
  "data": { ... },
  "timestamp": 1729872000
}
```

**错误响应**:
```json
{
  "status": "error",
  "error_code": "INVALID_TOKEN",
  "message": "Token has expired",
  "timestamp": 1729872000
}
```

### 错误码

| 错误码 | HTTP状态 | 说明 |
|--------|---------|------|
| `INVALID_TOKEN` | 401 | Token 无效或过期 |
| `UNAUTHORIZED` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `VALIDATION_ERROR` | 400 | 请求参数错误 |
| `RATE_LIMIT` | 429 | 请求频率超限 |
| `SERVER_ERROR` | 500 | 服务器内部错误 |

---

## 🔐 认证管理 API

### 1. Agent 注册验证

**端点**: `POST /auth/register`

**描述**: Agent 首次启动时，使用管理员预分配的 agent_id 和初始 Token 进行注册验证

**请求头**:
```http
Authorization: Bearer {initial_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "version": "1.0.0",
  "hostname": "mining-site-01",
  "os_info": "Ubuntu 20.04",
  "python_version": "3.8.10"
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "agent_name": "Site A Agent",
    "site_id": 123,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_expires_at": 1730476800,
    "config_version": "v1.0.0",
    "permissions": ["read", "control"]
  },
  "timestamp": 1729872000
}
```

**错误响应**:
```json
{
  "status": "error",
  "error_code": "AGENT_NOT_FOUND",
  "message": "Agent ID not found or already activated",
  "timestamp": 1729872000
}
```

---

### 2. Token 刷新

**端点**: `POST /auth/refresh`

**描述**: Agent Token 即将过期时，请求新的 Token

**请求头**:
```http
Authorization: Bearer {current_token}
```

**请求体**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_expires_at": 1730476800
  },
  "timestamp": 1729872000
}
```

---

### 3. 验证 Token 有效性

**端点**: `GET /auth/verify`

**描述**: 验证当前 Token 是否有效

**请求头**:
```http
Authorization: Bearer {token}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "valid": true,
    "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "expires_at": 1730476800,
    "permissions": ["read", "control"]
  },
  "timestamp": 1729872000
}
```

---

## 💓 心跳监控 API

### 1. 上报心跳

**端点**: `POST /heartbeat`

**描述**: Agent 定期发送心跳，汇报自身状态

**请求频率**: 每 30 秒一次

**请求头**:
```http
Authorization: Bearer {agent_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": 1729872000,
  "status": "online",
  "version": "1.0.0",
  "stats": {
    "cpu_usage": 15.2,
    "memory_usage": 42.8,
    "disk_usage": 68.5,
    "uptime_seconds": 86400,
    "network_latency_ms": 25
  },
  "miners": {
    "total": 50,
    "online": 48,
    "offline": 2,
    "error": 0
  }
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "received": true,
    "server_time": 1729872001,
    
    "commands": [
      {
        "command_id": "cmd-12345",
        "command_type": "reboot_miner",
        "target_ip": "192.168.1.100",
        "params": {
          "delay_seconds": 30
        },
        "priority": 5
      }
    ],
    
    "config_update": {
      "has_update": false,
      "current_version": "v1.0.0",
      "latest_version": "v1.0.0"
    },
    
    "token_refresh": {
      "should_refresh": false,
      "expires_in_seconds": 518400
    }
  },
  "timestamp": 1729872001
}
```

**字段说明**:
- `commands`: 待执行的控制指令列表
- `config_update`: 配置更新通知
- `token_refresh`: Token 刷新建议

---

## 📡 遥测数据 API

### 1. 上报遥测数据

**端点**: `POST /telemetry`

**描述**: Agent 上报矿机遥测数据

**请求频率**: 每 60 秒一次（可配置）

**请求头**:
```http
Authorization: Bearer {agent_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": 1729872000,
  "batch_size": 2,
  "miners": [
    {
      "ip_address": "192.168.1.100",
      "mac_address": "00:1A:2B:3C:4D:5E",
      "serial_number": "S19-12345",
      "miner_type": "Antminer S19 Pro",
      "status": "running",
      
      "hashrate": {
        "realtime_th": 110.5,
        "avg_5s": 110.2,
        "avg_1m": 109.8,
        "avg_5m": 110.1,
        "avg_15m": 110.0
      },
      
      "temperature": {
        "avg": 68.3,
        "max": 72.1,
        "min": 65.2,
        "board1": 67.5,
        "board2": 68.8,
        "board3": 68.6
      },
      
      "fan": {
        "avg_speed": 4500,
        "max_speed": 4800,
        "fan1": 4450,
        "fan2": 4500,
        "fan3": 4550,
        "fan4": 4500
      },
      
      "power": {
        "consumption_w": 3250,
        "voltage_v": 220.5,
        "current_a": 14.7
      },
      
      "pool": {
        "url": "stratum+tcp://pool.example.com:3333",
        "worker": "worker001",
        "status": "connected"
      },
      
      "shares": {
        "accepted": 12543,
        "rejected": 23,
        "hardware_errors": 0,
        "reject_rate": 0.18
      },
      
      "uptime_seconds": 86400,
      "frequency_mhz": 550
    },
    {
      "ip_address": "192.168.1.101",
      "status": "offline",
      "last_seen": 1729871700
    }
  ]
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "received_count": 2,
    "processed_count": 2,
    "failed_count": 0,
    "errors": []
  },
  "timestamp": 1729872001
}
```

---

### 2. 批量上报（离线缓冲数据）

**端点**: `POST /telemetry/batch`

**描述**: Agent 重新连接后，批量上报缓冲的历史数据

**请求头**:
```http
Authorization: Bearer {agent_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "offline_period": {
    "start": 1729868400,
    "end": 1729872000
  },
  "batches": [
    {
      "timestamp": 1729868460,
      "miners": [ ... ]
    },
    {
      "timestamp": 1729868520,
      "miners": [ ... ]
    }
  ]
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "total_batches": 60,
    "processed_batches": 60,
    "total_records": 3000,
    "processed_records": 3000,
    "processing_time_ms": 1250
  },
  "timestamp": 1729872001
}
```

---

### 3. 查询实时数据

**端点**: `GET /telemetry/realtime`

**描述**: 查询指定 Agent 的最新遥测数据

**请求参数**:
```
?agent_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890
&limit=50
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "last_update": 1729872000,
    "miners": [
      {
        "ip_address": "192.168.1.100",
        "status": "running",
        "hashrate_th": 110.5,
        "temperature_avg": 68.3,
        "power_w": 3250,
        "uptime_seconds": 86400
      }
    ]
  },
  "timestamp": 1729872001
}
```

---

## 🎮 控制指令 API

### 1. 创建控制指令（管理员）

**端点**: `POST /commands/create`

**描述**: 管理员创建控制指令，下发给 Agent

**请求头**:
```http
Authorization: Bearer {user_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "command_type": "reboot_miner",
  "target_ip": "192.168.1.100",
  "params": {
    "delay_seconds": 30,
    "reason": "scheduled_maintenance"
  },
  "priority": 5,
  "timeout_seconds": 300
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "command_id": "cmd-12345",
    "status": "pending",
    "created_at": 1729872000,
    "estimated_execution": 1729872030
  },
  "timestamp": 1729872001
}
```

---

### 2. Agent 获取待执行指令

**端点**: `GET /commands/pending`

**描述**: Agent 轮询获取待执行的控制指令

**请求参数**:
```
?agent_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "commands": [
      {
        "command_id": "cmd-12345",
        "command_type": "reboot_miner",
        "target_ip": "192.168.1.100",
        "params": {
          "delay_seconds": 30,
          "reason": "scheduled_maintenance"
        },
        "priority": 5,
        "timeout_seconds": 300,
        "created_at": 1729872000
      }
    ],
    "count": 1
  },
  "timestamp": 1729872001
}
```

**注意**: 心跳响应中也包含待执行指令，Agent 可选择：
- 主动轮询此接口（实时性高）
- 仅依赖心跳返回（节省请求）

---

### 3. 上报指令执行结果

**端点**: `POST /commands/{command_id}/result`

**描述**: Agent 执行指令后，上报执行结果

**请求头**:
```http
Authorization: Bearer {agent_token}
Content-Type: application/json
```

**请求体 - 成功**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "command_id": "cmd-12345",
  "status": "success",
  "executed_at": 1729872030,
  "completed_at": 1729872075,
  "result": {
    "message": "Miner rebooted successfully",
    "reboot_time_seconds": 45,
    "post_reboot_status": "running",
    "post_reboot_hashrate": 110.2
  }
}
```

**请求体 - 失败**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "command_id": "cmd-12345",
  "status": "failed",
  "executed_at": 1729872030,
  "error": {
    "error_code": "CONNECTION_TIMEOUT",
    "message": "Failed to connect to miner at 192.168.1.100:4028",
    "details": "Timeout after 5 seconds"
  }
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "command_id": "cmd-12345",
    "result_recorded": true
  },
  "timestamp": 1729872076
}
```

---

### 4. 查询指令状态

**端点**: `GET /commands/{command_id}`

**描述**: 查询指定指令的执行状态

**响应**:
```json
{
  "status": "success",
  "data": {
    "command_id": "cmd-12345",
    "command_type": "reboot_miner",
    "target_ip": "192.168.1.100",
    "status": "completed",
    "created_at": 1729872000,
    "executed_at": 1729872030,
    "completed_at": 1729872075,
    "result": {
      "message": "Miner rebooted successfully",
      "reboot_time_seconds": 45
    }
  },
  "timestamp": 1729872100
}
```

---

## ⚙️ 配置管理 API

### 1. 获取最新配置

**端点**: `GET /config/latest`

**描述**: Agent 获取最新的配置文件

**请求参数**:
```
?agent_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890
&current_version=v1.0.0
```

**响应 - 有更新**:
```json
{
  "status": "success",
  "data": {
    "has_update": true,
    "current_version": "v1.0.0",
    "latest_version": "v1.1.0",
    "config": {
      "version": "v1.1.0",
      "collection_interval": 60,
      "heartbeat_interval": 30,
      "cgminer_api_timeout": 5,
      "retry_policy": {
        "max_retries": 3,
        "backoff_seconds": [5, 15, 30]
      },
      "buffer_config": {
        "max_buffer_size": 10000,
        "max_buffer_hours": 24
      },
      "features": {
        "enable_auto_discovery": false,
        "enable_remote_control": true,
        "enable_auto_reboot": false
      }
    },
    "change_summary": "Increased heartbeat interval to 30s"
  },
  "timestamp": 1729872001
}
```

**响应 - 无更新**:
```json
{
  "status": "success",
  "data": {
    "has_update": false,
    "current_version": "v1.0.0",
    "latest_version": "v1.0.0"
  },
  "timestamp": 1729872001
}
```

---

### 2. 确认配置应用

**端点**: `POST /config/confirm`

**描述**: Agent 应用新配置后，上报确认

**请求体**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "version": "v1.1.0",
  "applied_at": 1729872100,
  "restart_required": true,
  "restarted_at": 1729872105
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "confirmed": true
  },
  "timestamp": 1729872106
}
```

---

## 🚨 事件告警 API

### 1. 上报事件

**端点**: `POST /events`

**描述**: Agent 上报重要事件和告警

**请求头**:
```http
Authorization: Bearer {agent_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "events": [
    {
      "event_type": "miner_offline",
      "severity": "error",
      "title": "Miner 192.168.1.100 offline",
      "message": "Miner stopped responding to CGMiner API requests",
      "related_miner_ip": "192.168.1.100",
      "timestamp": 1729872000,
      "details": {
        "last_seen": 1729871940,
        "offline_duration_seconds": 60,
        "last_hashrate": 110.5
      }
    },
    {
      "event_type": "high_temperature",
      "severity": "warning",
      "title": "High temperature detected on 192.168.1.105",
      "message": "Average temperature reached 75°C, exceeding threshold",
      "related_miner_ip": "192.168.1.105",
      "timestamp": 1729872030,
      "details": {
        "temperature_avg": 75.2,
        "temperature_max": 78.5,
        "threshold": 72.0
      }
    }
  ]
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "events_received": 2,
    "events_created": 2
  },
  "timestamp": 1729872031
}
```

---

### 2. 查询事件历史

**端点**: `GET /events`

**描述**: 查询事件历史记录

**请求参数**:
```
?agent_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890
&severity=error
&status=open
&limit=50
&offset=0
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "events": [
      {
        "id": 12345,
        "event_type": "miner_offline",
        "severity": "error",
        "title": "Miner 192.168.1.100 offline",
        "status": "open",
        "created_at": 1729872000
      }
    ],
    "total": 15,
    "limit": 50,
    "offset": 0
  },
  "timestamp": 1729872100
}
```

---

## 👨‍💼 管理接口 API

### 1. 创建 Agent

**端点**: `POST /admin/agents/create`

**描述**: 管理员创建新的 Agent 记录

**请求头**:
```http
Authorization: Bearer {user_token}
Content-Type: application/json
```

**请求体**:
```json
{
  "agent_name": "Site A Agent",
  "site_id": 123,
  "permissions": ["read", "control"],
  "collection_interval": 60,
  "heartbeat_interval": 30,
  "notes": "Main agent for Site A"
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "agent_name": "Site A Agent",
    "initial_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "status": "pending",
    "created_at": 1729872000
  },
  "timestamp": 1729872001
}
```

**重要**: `initial_token` 仅在创建时返回一次，用于 Agent 首次注册

---

### 2. Agent 列表

**端点**: `GET /admin/agents`

**描述**: 获取所有 Agent 列表

**请求参数**:
```
?status=active
&site_id=123
&limit=50
&offset=0
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "agents": [
      {
        "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "agent_name": "Site A Agent",
        "site_id": 123,
        "site_name": "Beijing Data Center",
        "status": "active",
        "version": "1.0.0",
        "last_seen_at": 1729871970,
        "total_miners": 50,
        "active_miners": 48,
        "created_at": 1729800000
      }
    ],
    "total": 10,
    "limit": 50,
    "offset": 0
  },
  "timestamp": 1729872001
}
```

---

### 3. Agent 详情

**端点**: `GET /admin/agents/{agent_id}`

**描述**: 获取指定 Agent 的详细信息

**响应**:
```json
{
  "status": "success",
  "data": {
    "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "agent_name": "Site A Agent",
    "site_id": 123,
    "status": "active",
    "version": "1.0.0",
    "permissions": ["read", "control"],
    "config_version": "v1.0.0",
    
    "stats": {
      "total_miners": 50,
      "active_miners": 48,
      "offline_miners": 2,
      "total_uptime_seconds": 864000,
      "connection_count": 28800
    },
    
    "last_heartbeat": {
      "timestamp": 1729871970,
      "cpu_usage": 15.2,
      "memory_usage": 42.8,
      "disk_usage": 68.5
    },
    
    "recent_events": {
      "critical": 0,
      "error": 2,
      "warning": 5,
      "info": 10
    },
    
    "created_at": 1729800000,
    "last_seen_at": 1729871970
  },
  "timestamp": 1729872001
}
```

---

### 4. 更新 Agent 配置

**端点**: `PUT /admin/agents/{agent_id}/config`

**描述**: 更新 Agent 配置

**请求体**:
```json
{
  "agent_name": "Site A Main Agent",
  "collection_interval": 120,
  "permissions": ["read", "control", "config"],
  "notes": "Updated collection interval"
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "updated": true,
    "config_version": "v1.1.0"
  },
  "timestamp": 1729872001
}
```

---

### 5. 禁用/启用 Agent

**端点**: `POST /admin/agents/{agent_id}/toggle`

**描述**: 禁用或启用 Agent

**请求体**:
```json
{
  "action": "disable",
  "reason": "Maintenance"
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "disabled",
    "updated_at": 1729872001
  },
  "timestamp": 1729872001
}
```

---

### 6. Agent 统计汇总

**端点**: `GET /admin/stats/summary`

**描述**: 获取所有 Agent 的统计汇总

**响应**:
```json
{
  "status": "success",
  "data": {
    "total_agents": 10,
    "active_agents": 8,
    "offline_agents": 2,
    "total_miners": 500,
    "active_miners": 485,
    "offline_miners": 15,
    
    "total_hashrate_th": 55250.5,
    "avg_temperature_c": 67.8,
    "total_power_kw": 1625.0,
    
    "open_events": {
      "critical": 0,
      "error": 5,
      "warning": 12
    },
    
    "pending_commands": 3,
    
    "last_update": 1729872001
  },
  "timestamp": 1729872001
}
```

---

## 📊 数据聚合 API

### 1. 矿机性能趋势

**端点**: `GET /telemetry/trend`

**描述**: 获取矿机性能趋势数据

**请求参数**:
```
?agent_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890
&miner_ip=192.168.1.100
&metric=hashrate
&period=24h
&granularity=1h
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "metric": "hashrate",
    "unit": "TH/s",
    "period": "24h",
    "granularity": "1h",
    "data_points": [
      {
        "timestamp": 1729828800,
        "value": 110.2,
        "min": 109.5,
        "max": 111.0
      },
      {
        "timestamp": 1729832400,
        "value": 110.5,
        "min": 110.0,
        "max": 111.2
      }
    ]
  },
  "timestamp": 1729872001
}
```

---

## 🔄 API 限流策略

### 限流规则

| 端点类型 | 限制 | 时间窗口 | 超限响应 |
|---------|------|---------|---------|
| 心跳 | 100 次/Agent | 1 分钟 | 429 + Retry-After |
| 遥测数据 | 100 次/Agent | 1 分钟 | 429 + Retry-After |
| 控制指令 | 50 次/Agent | 1 分钟 | 429 + Retry-After |
| 管理接口 | 200 次/用户 | 1 分钟 | 429 + Retry-After |

### 限流响应

```json
{
  "status": "error",
  "error_code": "RATE_LIMIT",
  "message": "Rate limit exceeded: 100 requests per minute",
  "retry_after": 30,
  "timestamp": 1729872001
}
```

**响应头**:
```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1729872030
Retry-After: 30
```

---

## 🔒 安全最佳实践

### 1. Token 管理
- Token 有效期: 7 天
- 提前 1 天刷新 Token
- 旧 Token 在新 Token 生成后 1 小时内仍有效（平滑过渡）

### 2. HTTPS 强制
- 所有 API 必须通过 HTTPS 访问
- HTTP 请求自动重定向到 HTTPS

### 3. 请求签名（可选增强）
```python
# 使用 HMAC-SHA256 签名请求体
import hmac
import hashlib

signature = hmac.new(
    agent_secret.encode(),
    request_body.encode(),
    hashlib.sha256
).hexdigest()

headers = {
    'Authorization': f'Bearer {token}',
    'X-Signature': signature,
    'X-Timestamp': str(int(time.time()))
}
```

### 4. IP 白名单（可选）
- 配置 Agent 的允许 IP 范围
- 云端验证请求来源 IP

---

## 📝 使用示例

### Python Agent 示例

```python
import requests
import time

class AgentClient:
    def __init__(self, base_url, agent_id, token):
        self.base_url = base_url
        self.agent_id = agent_id
        self.token = token
    
    def send_heartbeat(self, stats):
        url = f"{self.base_url}/heartbeat"
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'agent_id': self.agent_id,
            'timestamp': int(time.time()),
            'status': 'online',
            'stats': stats
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('commands', [])
        else:
            raise Exception(f"Heartbeat failed: {response.text}")
    
    def send_telemetry(self, miners_data):
        url = f"{self.base_url}/telemetry"
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'agent_id': self.agent_id,
            'timestamp': int(time.time()),
            'miners': miners_data
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

# 使用示例
client = AgentClient(
    base_url='https://hashinsight.replit.app/agent/api',
    agent_id='a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    token='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
)

# 发送心跳
commands = client.send_heartbeat({
    'cpu_usage': 15.2,
    'memory_usage': 42.8,
    'disk_usage': 68.5
})

# 处理待执行指令
for cmd in commands:
    print(f"Received command: {cmd['command_type']}")
```

---

## 🧪 测试环境

### Staging API Base URL
```
https://hashinsight-staging.replit.app/agent/api
```

### 测试 Agent 凭证
```
Agent ID: test-agent-12345
Token: test_token_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📚 相关文档

- [架构设计](./miner_agent_architecture.md)
- [数据库设计](./miner_agent_database.md)
- [Agent 代码实现](../agent/miner_agent.py)
- [部署运维指南](./miner_agent_deployment.md)

---

**文档版本**: v1.0.0  
**最后更新**: 2025-10-13
