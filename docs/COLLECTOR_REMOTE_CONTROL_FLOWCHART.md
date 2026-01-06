# Collector & Remote Control System Architecture

> Last Updated: January 2026

This document describes the complete data flow for miner telemetry collection and remote control operations in HashInsight Enterprise.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Complete Flow Chart](#complete-flow-chart)
3. [User Control Command Flow](#user-control-command-flow)
4. [Telemetry Collection Flow](#telemetry-collection-flow)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Database Tables Reference](#database-tables-reference)
7. [Command Types & States](#command-types--states)

---

## System Overview

The system consists of two main data flows:

1. **Telemetry Collection** (Miner → Cloud): Edge collectors gather real-time data from miners and upload to cloud
2. **Remote Control** (User → Miner): Users send commands through web UI, which are executed on miners via edge collectors

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HASHINSIGHT ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐   │
│   │   User   │────▶│   Web UI     │────▶│  Cloud API   │────▶│ Database │   │
│   │          │◀────│              │◀────│              │◀────│          │   │
│   └──────────┘     └──────────────┘     └──────────────┘     └──────────┘   │
│                                                │                             │
│                                                │ Commands (Poll)             │
│                                                ▼                             │
│                                         ┌──────────────┐                     │
│                                         │    Edge      │                     │
│                                         │  Collector   │                     │
│                                         └──────┬───────┘                     │
│                                                │                             │
│                                                │ CGMiner API (4028)          │
│                                                ▼                             │
│                                         ┌──────────────┐                     │
│                                         │   Miners     │                     │
│                                         │ (ASIC Fleet) │                     │
│                                         └──────────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Flow Chart

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              USER CONTROL FLOW                                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────┐
                                    │   Web UI     │
                                    │ (User Login) │
                                    └──────┬───────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                              │
                    ▼                                              ▼
        ┌───────────────────────┐                    ┌────────────────────────┐
        │ View Miner Status     │                    │ Send Control Command   │
        │ (Read Telemetry)      │                    │ (REBOOT/POOL/FREQ)     │
        └───────────┬───────────┘                    └───────────┬────────────┘
                    │                                             │
                    ▼                                             ▼
┌───────────────────────────────────────┐    ┌─────────────────────────────────────────────┐
│      TELEMETRY READ ENDPOINTS          │    │        REMOTE CONTROL ENDPOINTS             │
├───────────────────────────────────────┤    ├─────────────────────────────────────────────┤
│ GET /hosting/miners                   │    │ POST /api/sites/<id>/commands               │
│ GET /api/collector/live/<site_id>     │    │   → Creates RemoteCommand                   │
│ GET /hosting/site/<id>/dashboard      │    │   → Non-admin batch: PENDING_APPROVAL       │
└───────────────────┬───────────────────┘    │   → Admin/normal: QUEUED                    │
                    │                         └─────────────────────┬───────────────────────┘
                    │                                               │
                    ▼                                               ▼
        ┌───────────────────────┐                    ┌─────────────────────────┐
        │ Database Tables       │                    │ If require_approval     │
        │ (Read)                │                    │ = True                  │
        └───────────────────────┘                    └───────────┬─────────────┘
                    │                                             │
     ┌──────────────┼──────────────┐              ┌───────────────┴───────────────┐
     ▼              ▼              ▼              │                               │
┌─────────┐  ┌───────────────┐  ┌──────────┐     ▼                               ▼
│ hosting │  │MinerTelemetry │  │  Miner   │  ┌────────────────┐     ┌────────────────────┐
│ _miners │  │    Live       │  │Telemetry │  │ Admin Approval │     │ Auto-Approved      │
│         │  │               │  │ History  │  │ Required       │     │ (QUEUED directly)  │
└─────────┘  └───────────────┘  └──────────┘  └───────┬────────┘     └─────────┬──────────┘
                                                       │                        │
                                                       ▼                        │
                                           ┌─────────────────────────┐          │
                                           │ POST /api/commands/     │          │
                                           │ <id>/approve            │          │
                                           │ (Admin approves)        │          │
                                           └───────────┬─────────────┘          │
                                                       │                        │
                                                       ▼                        │
                                           ┌─────────────────────────┐          │
                                           │ command_dispatcher.py   │◀─────────┘
                                           │ dispatch_remote_command │
                                           └───────────┬─────────────┘
                                                       │
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            COMMAND QUEUE (Database)                                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌─────────────────────┐         ┌───────────────────┐  │
│  │   remote_commands   │ ──1:N──▶│ remote_command_     │         │  miner_commands   │  │
│  │                     │         │     results         │         │   (Edge Queue)    │  │
│  │ • id (UUID)         │         │ • command_id        │         │ • miner_id        │  │
│  │ • command_type      │         │ • miner_id          │         │ • command_type    │  │
│  │ • status (enum)     │         │ • result_status     │         │ • status=pending  │  │
│  │ • target_ids[]      │         │ • result_message    │         │ • expires_at      │  │
│  │ • require_approval  │         │                     │         │ • remote_cmd_id   │  │
│  └─────────────────────┘         └─────────────────────┘         └─────────┬─────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                       EDGE COLLECTOR (On-Premise at Mining Farm)                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                    COMMAND POLLING LOOP (Two API Paths Available)                │   │
│   │                                                                                  │   │
│   │   PATH A: Collector API                     PATH B: Control Plane API           │   │
│   │   ─────────────────────────                 ──────────────────────────           │   │
│   │   GET /api/collector/commands/pending       GET /api/edge/v1/commands/poll       │   │
│   │   Headers:                                  Headers:                             │   │
│   │   • X-Collector-Key: <api_key>              • Authorization: Bearer <token>      │   │
│   │   • X-Site-ID: <site_id>                                                         │   │
│   │                                                                                  │   │
│   │   POST /api/collector/commands/<id>/result  POST /api/edge/v1/commands/<id>/ack  │   │
│   │                                                                                  │   │
│   │   ┌─────────────────┐                                                            │   │
│   │   │ CommandExecutor │◀─────── Poll pending commands                              │   │
│   │   │ • fetch_pending │                                                            │   │
│   │   │ • execute_cmd   │──────── Report result                                      │   │
│   │   │ • report_result │                                                            │   │
│   │   └────────┬────────┘                                                            │   │
│   │            │                                                                     │   │
│   │            ▼                                                                     │   │
│   │   ┌─────────────────┐                                                            │   │
│   │   │  CGMiner API    │   Execute: enable/disable/restart/set_pool/set_fan         │   │
│   │   │  (Port 4028)    │◀──────────────────────────────────────────────────────     │   │
│   │   └────────┬────────┘                                                            │   │
│   │            │                                                                     │   │
│   └────────────┼─────────────────────────────────────────────────────────────────────┘   │
│                │                                                                          │
│                ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                    TELEMETRY COLLECTION LOOP                                     │   │
│   │                                                                                  │   │
│   │   ┌─────────────────┐      Query: summary, stats, pools, devs                    │   │
│   │   │ EdgeCollector   │◀─────────────────────────────────────────────────────────  │   │
│   │   │ • collect_all   │                    CGMiner API (4028)                      │   │
│   │   │ • parse_data    │                                                            │   │
│   │   │ • compress_gzip │──────────────────────────────────────────────────────────▶ │   │
│   │   │ • upload        │      POST /api/collector/upload                            │   │
│   │   └─────────────────┘      Headers:                                              │   │
│   │                            • X-Collector-Key: <hashed_api_key>                   │   │
│   │                            • X-Site-ID: <site_id>                                │   │
│   │                            • Content-Encoding: gzip                              │   │
│   │                            • Content-Type: application/octet-stream              │   │
│   │                                                                                  │   │
│   └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                    OFFLINE CACHE (Network Resilience)                            │   │
│   │   • SQLite: ./cache/offline_cache.db                                             │   │
│   │   • Auto-retry pending uploads when network recovers                             │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          CLOUD API - DATA STORAGE                                        │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   POST /api/collector/upload                                                             │
│   ├── Verify X-Collector-Key header (SHA-256 hash lookup in collector_keys)              │
│   ├── Decompress gzip data                                                               │
│   ├── Auto-create HostingMiner if not exists (find_or_create_hosting_miner)              │
│   └── Store to multiple tables:                                                          │
│                                                                                          │
│       ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐     │
│       │ MinerTelemetryLive  │    │ MinerTelemetryHist- │    │  TelemetryRaw24h    │     │
│       │                     │    │        ory          │    │                     │     │
│       ├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤     │
│       │ • Current status    │    │ • Time-series data  │    │ • High-resolution   │     │
│       │ • Upsert on each    │    │ • For charts        │    │ • 24-hour retention │     │
│       │   upload            │    │ • Appends each      │    │ • All raw samples   │     │
│       │ • Unique: site_id + │    │   upload            │    │                     │     │
│       │   miner_id          │    │                     │    │                     │     │
│       └─────────────────────┘    └─────────────────────┘    └─────────────────────┘     │
│                                                                                          │
│       ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐     │
│       │ MinerBoardTelemetry │    │   HostingMiner      │    │ CollectorUploadLog  │     │
│       │                     │    │                     │    │                     │     │
│       ├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤     │
│       │ • Board-level       │    │ • Master miner      │    │ • Audit trail       │     │
│       │   health data       │    │   record sync       │    │ • Upload stats      │     │
│       │ • Per-board temps,  │    │ • Auto-provision    │    │ • miner_count       │     │
│       │   hashrate, health  │    │   new miners        │    │ • online/offline    │     │
│       └─────────────────────┘    └─────────────────────┘    └─────────────────────┘     │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## User Control Command Flow

### Step-by-Step Flow

```
User Action                    API Endpoint                      Database Table
───────────────────────────────────────────────────────────────────────────────

1. Login                       POST /login                       user_access
                                                                 ↓
2. Select Site                 GET /hosting/sites                hosting_sites
                                                                 ↓
3. View Miners                 GET /hosting/miners               hosting_miners
                               GET /api/collector/live/<id>      MinerTelemetryLive
                                                                 ↓
4. Send Command                POST /api/sites/<id>/commands     remote_commands
   (e.g., REBOOT)                                                remote_command_results
                                                                 ↓
5. Status Check:               
   • require_approval=True     → Status: PENDING_APPROVAL
   • require_approval=False    → Status: QUEUED
                                                                 ↓
6. If Approval Required        POST /api/commands/<id>/approve   remote_commands
   (Admin action)              (dispatches to miner_commands)    miner_commands
                                                                 ↓
7. Edge Polls                  GET /api/collector/commands/      miner_commands
                               pending                           (status: sent)
                               OR
                               GET /api/edge/v1/commands/poll
                                                                 ↓
8. Execute on Miner            CGMiner API (port 4028)           -
                                                                 ↓
9. Report Result               POST /api/collector/commands/     miner_commands
                               <id>/result                       (status: completed/failed)
                               OR                                remote_command_results
                               POST /api/edge/v1/commands/
                               <id>/ack
```

---

## Telemetry Collection Flow

### Step-by-Step Flow

```
Edge Collector Action          API Endpoint                      Database Table
───────────────────────────────────────────────────────────────────────────────

1. Query Miners                CGMiner API (port 4028)           -
   • summary → hashrate, shares, uptime
   • stats   → temperature, fans, frequency
   • pools   → pool URL, worker name
   • devs    → device info

                                                                 ↓
2. Parse Data                  (internal)                        -
   • MinerDataParser.parse_antminer()
   • parse_board_health() - board-level data
   • parse_power_consumption()
                                                                 ↓
3. Compress (gzip)             (internal)                        -
   • JSON serialize array of MinerData
   • gzip.compress()
                                                                 ↓
4. Upload                      POST /api/collector/upload        
                               Headers:                          
                               • X-Collector-Key: <api_key>      collector_keys (lookup)
                               • X-Site-ID: <site_id>            
                               • Content-Encoding: gzip          
                               • Content-Type: application/      
                                 octet-stream                    
                                                                 ↓
5. Server Processing           (api/collector_api.py)            
   • Verify collector key      collector_keys
   • Find or create miner      hosting_miners (auto-provision)
   • Store live telemetry      MinerTelemetryLive (upsert)
   • Store history             MinerTelemetryHistory (append)
   • Store raw data            TelemetryRaw24h (append)
   • Store board health        MinerBoardTelemetry (append)
   • Log upload                CollectorUploadLog (append)
                                                                 ↓
6. Offline Cache               (if network down)                 
   • Save to SQLite            ./cache/offline_cache.db
   • Auto-retry when online    (local to edge device)
```

---

## API Endpoints Reference

### Collector API (`/api/collector/`)

| Endpoint | Method | Auth Header | Description | Tables Written |
|----------|--------|-------------|-------------|----------------|
| `/upload` | POST | X-Collector-Key, X-Site-ID | Upload telemetry data | `MinerTelemetryLive`, `MinerTelemetryHistory`, `TelemetryRaw24h`, `MinerBoardTelemetry`, `hosting_miners`, `CollectorUploadLog` |
| `/commands/pending` | GET | X-Collector-Key, X-Site-ID | Poll for pending commands | - (reads `miner_commands`) |
| `/commands/<id>/result` | POST | X-Collector-Key, X-Site-ID | Report command result | `miner_commands`, `remote_command_results` |
| `/commands` | POST | Admin Auth | Create miner command | `miner_commands` |
| `/commands/batch` | POST | Admin Auth | Batch create commands | `miner_commands` |
| `/live/<site_id>` | GET | Admin Auth | Get live telemetry | - (reads `MinerTelemetryLive`) |
| `/keys` | GET/POST | Admin Auth | Manage collector API keys | `collector_keys` |

### Control Plane API (`/api/edge/v1/` and `/api/v1/`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/edge/v1/commands/poll` | GET | Bearer Token | Edge device polls for commands |
| `/api/edge/v1/commands/<id>/ack` | POST | Bearer Token | Edge acknowledges command result |
| `/api/v1/commands/propose` | POST | Session Auth | Propose new command (dual-approval) |
| `/api/v1/commands/<id>/approve` | POST | Session Auth | Approve pending command |
| `/api/v1/commands/<id>/deny` | POST | Session Auth | Deny pending command |

### Remote Control API (`/api/`)

| Endpoint | Method | Auth | RBAC Permission | Description |
|----------|--------|------|-----------------|-------------|
| `/api/sites/<id>/commands` | POST | Session | REMOTE_CONTROL_REQUEST (FULL) | Create remote command |
| `/api/sites/<id>/commands` | GET | Session | REMOTE_CONTROL_AUDIT | List site commands |
| `/api/commands/<id>` | GET | Session | REMOTE_CONTROL_AUDIT | Get command details |
| `/api/commands/<id>/cancel` | POST | Session | REMOTE_CONTROL_REQUEST (FULL) | Cancel pending command |
| `/api/commands/<id>/approve` | POST | Session | REMOTE_CONTROL_EXECUTE (FULL) | Approve and dispatch command |

### Hosting API (`/hosting/`)

| Endpoint | Method | Description | Tables Read |
|----------|--------|-------------|-------------|
| `/hosting/miners` | GET | List all miners | `hosting_miners`, `MinerTelemetryLive` |
| `/hosting/site/<id>/dashboard` | GET | Site dashboard | `hosting_sites`, `hosting_miners` |
| `/hosting/status/<slug>` | GET | Public status page | `hosting_sites` |

---

## Database Tables Reference

### Telemetry Tables

| Table | Class Name | Purpose | Retention | Write Frequency |
|-------|------------|---------|-----------|-----------------|
| `miner_telemetry_live` | `MinerTelemetryLive` | Current miner status | Overwrites (upsert) | Every upload (~30s) |
| `miner_telemetry_history` | `MinerTelemetryHistory` | Time-series for charts | Indefinite (appends) | Every upload |
| `telemetry_raw_24h` | `TelemetryRaw24h` | High-resolution raw data | 24 hours | Every upload |
| `miner_board_telemetry` | `MinerBoardTelemetry` | Board-level health | Indefinite | Every upload |

### Command Tables

| Table | Class Name | Purpose | Key Fields |
|-------|------------|---------|------------|
| `remote_commands` | `RemoteCommand` | High-level command queue | id (UUID), command_type, status, target_ids[], require_approval |
| `remote_command_results` | `RemoteCommandResult` | Per-miner results | command_id, miner_id, result_status, result_message |
| `miner_commands` | `MinerCommand` | Edge-facing queue | miner_id, command_type, status, expires_at, remote_command_id |

### Authentication Tables

| Table | Class Name | Purpose |
|-------|------------|---------|
| `collector_keys` | `CollectorKey` | Edge collector API keys (SHA-256 hashed) |
| `edge_devices` | `EdgeDevice` | Registered edge devices with Bearer tokens |
| `user_access` | `UserAccess` | User authentication & RBAC |

---

## Command Types & States

### Supported Command Types (CommandType Enum)

| Command | Description | Payload Example |
|---------|-------------|-----------------|
| `REBOOT` | Restart miner | `{"mode": "soft"}` or `{"mode": "hard"}` |
| `POWER_MODE` | Set power mode | `{"mode": "high"}`, `{"mode": "normal"}`, `{"mode": "eco"}` |
| `CHANGE_POOL` | Switch mining pool | `{"pool_url": "...", "worker_name": "...", "password": "..."}` |
| `SET_FREQ` | Adjust frequency | `{"frequency_mhz": 500, "profile": "stock"}` |
| `THERMAL_POLICY` | Configure cooling | `{"fan_mode": "auto", "fan_speed_pct": 80, "temp_warning_c": 75}` |
| `LED` | Toggle LED | `{"state": "on"}` or `{"state": "off"}` |

### Command Status Lifecycle (CommandStatus Enum)

```
                           ┌───────────────────┐
                           │  User Creates     │
                           │  Command          │
                           └─────────┬─────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │     PENDING       │
                           └─────────┬─────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         │                         ▼
┌─────────────────────┐              │               ┌─────────────────┐
│ require_approval    │              │               │ Auto-approved   │
│ = true              │              │               │ (admin/small)   │
└──────────┬──────────┘              │               └────────┬────────┘
           │                         │                        │
           ▼                         │                        │
┌─────────────────────┐              │                        │
│ PENDING_APPROVAL    │              │                        │
└──────────┬──────────┘              │                        │
           │ (admin approves)        │                        │
           ▼                         │                        │
           └─────────────────────────┼────────────────────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │     QUEUED        │ ←── dispatch_remote_command()
                           └─────────┬─────────┘     creates MinerCommand entries
                                     │
                                     │ (Edge polls & executes)
                                     ▼
                           ┌───────────────────┐
                           │     RUNNING       │
                           └─────────┬─────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   SUCCEEDED   │          │    FAILED     │          │   EXPIRED     │
└───────────────┘          └───────────────┘          └───────────────┘

                    User can also:
                    ┌───────────────┐
                    │  CANCELLED    │ ←── POST /api/commands/<id>/cancel
                    └───────────────┘     (only if PENDING/PENDING_APPROVAL/QUEUED)
```

### Per-Miner Result Status (ResultStatus Enum)

| Status | Description |
|--------|-------------|
| `PENDING` | Waiting to be executed |
| `RUNNING` | Currently executing on miner |
| `SUCCEEDED` | Command completed successfully |
| `FAILED` | Command execution failed |
| `SKIPPED` | Command was cancelled before execution |

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `edge_collector/cgminer_collector.py` | Edge collector main module (runs on-premise) |
| `edge_collector/cgminer_client.py` | CGMiner API client |
| `edge_collector/command_runner.py` | Command execution on edge |
| `api/collector_api.py` | Cloud collector endpoints (`/api/collector/*`) |
| `api/remote_control_api.py` | Remote command endpoints (`/api/sites/*/commands`) |
| `api/control_plane_api.py` | Control plane & edge device endpoints (`/api/edge/v1/*`) |
| `models_remote_control.py` | Command database models (RemoteCommand, RemoteCommandResult) |
| `services/command_dispatcher.py` | Command dispatch service |
| `services/telemetry_storage.py` | Telemetry storage layer (TelemetryRaw24h) |

---

## Related Documentation

- [System Architecture](../SYSTEM_ARCHITECTURE_COMPLETE.md)
- [Security Compliance](../SECURITY_COMPLIANCE_EVIDENCE_INDEX_EN.md)
- [Operations Manual](../OPERATIONS_MANUAL_EN.md)
