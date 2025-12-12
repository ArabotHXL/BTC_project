# Phase 0 - Repository Discovery Report
# 阶段0 - 仓库发现报告

**Generated**: 2025-12-12  
**Repository**: HashInsight Enterprise - BTC Mining Farm Management Platform

---

## 1. Backend Entrypoints / 后端入口

| File | Role | Description |
|------|------|-------------|
| `main.py` | WSGI Entry | Flask application import point for Gunicorn |
| `app.py` | Application Instance | Direct Flask instantiation (NOT a factory pattern), 7700+ lines with routes inline |
| `gunicorn.conf.py` | WSGI Config | Gunicorn server configuration (workers, timeouts) |
| `gunicorn_fast.conf.py` | Fast Config | Optimized Gunicorn config for high-performance |

**Start Command**: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`

**Note**: `app.py` directly instantiates Flask and registers blueprints inline. It is NOT an application factory pattern.

---

## 2. CGMiner/Collector Modules / CGMiner采集模块

### 2.1 Core Collector Services

| File | Purpose | Status |
|------|---------|--------|
| `services/cgminer_scheduler.py` | APScheduler-based periodic collection | **Active** |
| `services/cgminer_collector.py` | Parallel miner polling with thread pool | **Active** |
| `tools/test_cgminer.py` | CGMinerTester class for TCP communication | **Active** |
| `edge_collector/cgminer_client.py` | Enhanced TCP client with retry/backoff | **Active** |
| `edge_collector/cgminer_collector.py` | Edge-side batch collection | **Active** |
| `edge_collector/parsers.py` | Response parsing utilities | **Active** |

### 2.2 CGMiner TCP Client Implementation

**Location**: `edge_collector/cgminer_client.py`

```python
class CGMinerClient:
    DEFAULT_PORT = 4028
    DEFAULT_TIMEOUT = 5.0
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 0.5  # Exponential backoff: 500ms, 1s, 2s
    
    # Supported commands: summary, stats, pools, devs, version
    # Features: Auto-retry, connection timeout, JSON parsing
```

**Capabilities**:
- TCP socket connection to port 4028
- JSON command format: `{"command": "summary", "parameter": ""}`
- Null-byte termination handling
- Exponential retry backoff (0.5s, 1s, 2s)
- Custom exceptions: `CGMinerError` with error types (timeout, connection, parse)

### 2.3 Alternative Client (Simpler)

**Location**: `tools/test_cgminer.py`

```python
class CGMinerTester:
    # Simpler implementation used by cgminer_collector.py
    # Methods: send_command(), test_connection(), get_telemetry_data()
```

---

## 3. Routes/Endpoints for Miners / 矿机相关路由

### 3.1 Collector API Blueprint

**File**: `api/collector_api.py`  
**Prefix**: `/api/collector`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/collector/upload` | POST | Upload batch telemetry data (gzip supported) |
| `/api/collector/status` | GET | Collector status check |
| `/api/collector/live/<site_id>` | GET | Get live telemetry for a site |
| `/api/collector/summary/<site_id>` | GET | Get site summary statistics |
| `/api/collector/stats` | GET | Overall collection statistics |
| `/api/collector/alerts` | GET | Active alert list |
| `/api/collector/keys` | GET/POST | Manage collector API keys |
| `/api/collector/keys/<key_id>` | DELETE | Revoke collector key |
| `/api/collector/commands` | POST | Create miner control command |
| `/api/collector/commands/batch` | POST | Create batch commands |
| `/api/collector/commands/pending` | GET | Fetch pending commands for edge |
| `/api/collector/commands/<id>/result` | POST | Report command execution result |
| `/api/collector/commands/<id>` | DELETE | Cancel pending command |
| `/api/collector/commands/history` | GET | Command execution history |
| `/api/collector/commands/stats` | GET | Command statistics |
| `/api/collector/miners/<id>/status` | GET | Single miner status |

### 3.2 Hosting API

**Prefix**: `/api/hosting` and `/hosting`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sites` | GET | List hosting sites |
| `/api/miners` | GET/POST | Miner CRUD operations |
| `/api/miners/<id>/telemetry` | GET | Get miner telemetry |
| `/api/thermal/config` | GET/PUT | Thermal protection configuration |
| `/api/thermal/check` | POST | Trigger thermal check |

### 3.3 Client Portal API

**Prefix**: `/api/client`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/client/dashboard` | GET | Client dashboard data |
| `/api/client/miner-distribution` | GET | Miner status distribution |
| `/api/client/miners` | GET | Client's miner list |

---

## 4. Database Models / 数据库模型

### 4.1 Core Telemetry Models (api/collector_api.py)

| Model | Table | Purpose |
|-------|-------|---------|
| `MinerTelemetryLive` | `miner_telemetry_live` | Real-time miner status snapshot |
| `MinerTelemetryHistory` | `miner_telemetry_history` | Time-series telemetry data |
| `CollectorKey` | `collector_keys` | API key authentication for collectors |
| `CollectorUploadLog` | `collector_upload_logs` | Upload audit trail |
| `MinerCommand` | `miner_commands` | Cloud-to-edge command queue |

### 4.2 Hosting Models (models_hosting.py)

| Model | Table | Purpose |
|-------|-------|---------|
| `HostingSite` | `hosting_sites` | Mining facility/datacenter |
| `HostingMiner` | `hosting_miners` | Miner inventory with IP/model/status |
| `UserMiner` | `user_miners` | Client-miner ownership mapping |
| `ThermalProtectionConfig` | `thermal_protection_config` | Temperature thresholds |
| `ThermalEvent` | `thermal_events` | Thermal protection event log |

### 4.3 Key Indexes

```sql
-- Telemetry Live
CREATE UNIQUE INDEX uq_site_miner ON miner_telemetry_live(site_id, miner_id);
CREATE INDEX ix_telemetry_live_site_online ON miner_telemetry_live(site_id, online);

-- Telemetry History
CREATE INDEX ix_telemetry_history_miner_time ON miner_telemetry_history(miner_id, timestamp);
CREATE INDEX ix_telemetry_history_site_time ON miner_telemetry_history(site_id, timestamp);
```

### 4.4 Tenant Scoping

- `site_id` FK on all telemetry tables for multi-site isolation
- `HostingSite` has `owner_id` linking to user for ownership
- RBAC enforced at route level via decorators

---

## 5. Caching Layer / 缓存层

### 5.1 Redis Configuration

**File**: `cache_manager.py`, `cache_config.yaml`

```python
# Cache patterns:
- Stale-While-Revalidate (SWR) for API responses
- Redis for session storage and task queues
- TTL-based cache invalidation (60-300s typical)
```

### 5.2 Flask-Caching Integration

```python
from flask_caching import Cache
cache = Cache(config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': os.environ.get('REDIS_URL')})
```

---

## 6. Runtime Topology / 运行时拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                     REPLIT PLATFORM                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────┐    ┌─────────────────────┐         │
│  │   Gunicorn WSGI     │    │   APScheduler       │         │
│  │   (Port 5000)       │    │   Background Jobs   │         │
│  │   - Flask App       │    │   - CGMiner Collect │         │
│  │   - API Routes      │    │   - Thermal Check   │         │
│  │   - Web UI          │    │   - Curtailment     │         │
│  └─────────┬───────────┘    └─────────┬───────────┘         │
│            │                          │                      │
│            ▼                          ▼                      │
│  ┌─────────────────────────────────────────────────┐        │
│  │              PostgreSQL (Neon)                   │        │
│  │   - User data       - Miner inventory            │        │
│  │   - Telemetry Live  - Telemetry History          │        │
│  │   - Command Queue   - Audit Logs                 │        │
│  └─────────────────────────────────────────────────┘        │
│            │                                                 │
│            ▼                                                 │
│  ┌─────────────────────────────────────────────────┐        │
│  │              Redis (Optional)                    │        │
│  │   - Cache           - Session                    │        │
│  │   - Task Queue      - Rate Limiting              │        │
│  └─────────────────────────────────────────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ HTTPS (Internet)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    MINING FARM (On-Premise)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────┐    ┌─────────────────────┐         │
│  │   Edge Collector    │    │   Antminer S19      │         │
│  │   (Python Agent)    │◄──►│   CGMiner :4028     │         │
│  │   - Batch Collect   │    └─────────────────────┘         │
│  │   - Command Execute │    ┌─────────────────────┐         │
│  │   - E2EE Decrypt    │◄──►│   Antminer S21      │         │
│  └─────────┬───────────┘    │   CGMiner :4028     │         │
│            │                └─────────────────────┘         │
│            │ POST /api/collector/telemetry                   │
│            ▼                                                 │
│  ┌─────────────────────────────────────────────────┐        │
│  │   Cloud API (Replit)                             │        │
│  └─────────────────────────────────────────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. External Dependencies / 外部依赖

### 7.1 Python Libraries (Key)

| Library | Version | Purpose |
|---------|---------|---------|
| Flask | 3.x | Web framework |
| SQLAlchemy | 2.x | ORM |
| APScheduler | 3.x | Background job scheduling |
| psycopg2-binary | - | PostgreSQL adapter |
| redis | - | Redis client |
| cryptography | - | E2EE encryption/decryption |
| requests | - | HTTP client for external APIs |

### 7.2 External APIs

| API | Purpose | Fallback |
|-----|---------|----------|
| CoinGecko | BTC price/history | CoinWarz |
| Blockchain.info | Network difficulty | Mempool.space |
| Deribit/OKX/Binance | Options/futures data | Multi-source aggregation |

---

## 8. Summary Assessment / 总结评估

### Existing Capabilities ✅

1. **CGMiner TCP Client**: Two implementations exist (`CGMinerClient` and `CGMinerTester`)
2. **Scheduled Collection**: APScheduler-based with lock management
3. **Telemetry Storage**: PostgreSQL models with proper indexing
4. **Edge Collector**: Python agent for on-premise deployment
5. **Command Queue**: Bidirectional cloud-to-edge control
6. **Audit Logging**: `CollectorUploadLog` for upload tracking

### Gaps Identified ⚠️

1. **Input Validation**: Telemetry payload schema validation not enforced
2. **Rate Limiting**: No rate limiting on collector API endpoints
3. **Normalized Response**: CGMiner response normalization varies between clients
4. **CLI Probe Tool**: No standalone CLI tool matching the security review spec
5. **Metrics Export**: No Prometheus/OpenTelemetry instrumentation
6. **Connection Pooling**: New socket per request (no pooling)

### Recommendations for Phase 1-4

1. Unify CGMiner clients into a single hardened implementation
2. Add schema validation middleware for telemetry ingestion
3. Implement rate limiting per collector key
4. Add metrics counters for observability
5. Document E2E flow with Mermaid diagrams

---

## 9. CGMiner Connectivity Path (Actual) / CGMiner实际连接路径

### Current Cloud-Side Collection Path

```
CGMinerSchedulerService (services/cgminer_scheduler.py)
    │
    ├── APScheduler interval trigger (60s)
    │
    └── _collect_telemetry_job()
            │
            └── collect_all_miners_telemetry() (services/cgminer_collector.py)
                    │
                    ├── Query HostingMiner table for active miners
                    │
                    ├── ThreadPoolExecutor (20 workers)
                    │       │
                    │       └── poll_single_miner()
                    │               │
                    │               └── CGMinerTester (tools/test_cgminer.py)
                    │                       │
                    │                       └── TCP socket to <ip>:4028
                    │
                    └── update_miner_telemetry_data() → HostingMiner model
```

**Key Observation**: The cloud-side scheduler uses `CGMinerTester` (simpler implementation), NOT `CGMinerClient` from edge_collector. The hardened client with retry/backoff is only used by edge collectors.

### Edge Collector Path

```
Edge Collector Agent (edge_collector/main.py)
    │
    └── CGMinerClient (edge_collector/cgminer_client.py)
            │
            ├── Retry with exponential backoff
            ├── Custom exceptions (CGMinerError)
            │
            └── POST /api/collector/upload
                    │
                    └── MinerTelemetryLive, MinerTelemetryHistory (PostgreSQL)
```

**Recommendation**: Consider using `CGMinerClient` for cloud-side collection to benefit from retry/backoff, or create unified client module.
