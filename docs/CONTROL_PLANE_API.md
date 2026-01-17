# Control Plane API Documentation

## Overview

The Control Plane API is an enterprise-grade system for managing command dispatch and execution across edge collectors in 100MW+ mining operations. It provides:

- **Zone-based Partitioning**: Multi-tenant isolation at the site/zone level
- **Attribute-Based Access Control (ABAC)**: Customers can only access their own devices and miners
- **Approval Workflows**: Risk-tiered command approval with dual-approval support for high-risk operations
- **Rate Limiting**: Prevents command flooding and resource exhaustion
- **HMAC Signature Verification**: Optional cryptographic integrity checks for command authenticity
- **Audit Trail**: SHA-256 blockchain-style immutable event logging
- **Lease-based Dispatch**: Atomic command assignment prevents duplicate execution
- **Idempotent ACKs**: Replay protection enables robust edge recovery

The API consists of two main components:

1. **Edge-Facing API** (`/api/edge/v1/*`): Used by on-premises edge collectors
2. **User-Facing API** (`/api/v1/*`): Used by cloud portal and admin interfaces

## Environment Variables

### Core Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_URL` | String | Required | Redis connection string for rate limiting and caching. Format: `redis://[user:password@]host:port/db` |
| `ENABLE_COMMAND_SIGNATURE` | Boolean | `false` | Enable HMAC-SHA256 signature verification for commands. When enabled, cloud signs each command and edge validates. |

### Example Configuration

```bash
# Development
export REDIS_URL="redis://localhost:6379/0"
export ENABLE_COMMAND_SIGNATURE="false"

# Production
export REDIS_URL="redis://redis-prod.example.com:6379/0"
export ENABLE_COMMAND_SIGNATURE="true"
```

## API Endpoints

### Edge Device Endpoints

These endpoints are called by on-premises edge collectors. Authentication is via Bearer token (device token).

#### POST /api/edge/v1/register

Register an edge device with the cloud control plane.

**Authentication**: None (initial registration)

**Request Body**:
```json
{
  "edge_id": "collector-site-01",
  "site_id": 123,
  "zone_id": 1
}
```

**Response** (200 OK):
```json
{
  "registered": true,
  "server_time": "2026-01-17T10:30:45.123Z",
  "polling_hints": {
    "interval_seconds": 30,
    "long_poll_timeout": 60
  }
}
```

**Error Responses**:
- `400 Bad Request`: Missing `edge_id` or `site_id`
- `403 Forbidden`: Device not pre-registered by admin

---

#### GET /api/edge/v1/commands/poll

Poll the cloud for pending commands to execute.

**Authentication**: Bearer token (device token)

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | Integer | 10 | Number of commands to fetch (max 50) |
| `zone_id` | Integer | - | Optional zone filter; must match device's bound zone |

**Request**:
```bash
GET /api/edge/v1/commands/poll?limit=10&zone_id=1
Authorization: Bearer <device_token>
```

**Response** (200 OK):
```json
{
  "commands": [
    {
      "command_id": "cmd-uuid-1",
      "miner_id": "miner-s21-01",
      "command_type": "REBOOT",
      "parameters": {
        "delay_seconds": 30
      },
      "priority": 100,
      "created_at": "2026-01-17T10:25:00Z",
      "expires_at": "2026-01-18T10:25:00Z",
      "ack_nonce": "nonce-uuid",
      "lease_expires_at": "2026-01-17T10:31:00Z",
      "retry_count": 0,
      "max_retries": 3,
      "cloud_signature": "sha256_hex_string",
      "sig_version": "v1",
      "signed_at": "2026-01-17T10:30:00Z"
    }
  ],
  "server_time": "2026-01-17T10:30:45.123Z",
  "dispatched_count": 1,
  "rate_limited_count": 0,
  "lease_duration_sec": 60
}
```

**Lease Management**:
- Each command is assigned a **60-second lease** to the polling device
- Device must ACK the command before lease expiration
- If lease expires without ACK, another device can claim the command
- Only the lease owner can ACK a command

**Rate Limiting**:
- Commands may be deferred if rate limits are exceeded
- Check `rate_limited_count` to determine deferred commands
- Retry polling after 30-60 seconds

**Error Responses**:
- `401 Unauthorized`: Invalid or revoked device token
- `403 Forbidden`: Device token bound to different zone than requested

---

#### POST /api/edge/v1/commands/{command_id}/ack

Acknowledge command completion. Supports idempotent retries with replay protection.

**Authentication**: Bearer token (device token)

**Request Body**:
```json
{
  "status": "completed",
  "ack_nonce": "nonce-uuid",
  "result_code": 0,
  "result_message": "Command executed successfully",
  "execution_time_ms": 2500,
  "cloud_signature": "sha256_hex_string"
}
```

**Status Values**:
- `completed` or `succeeded`: Command executed successfully
- `failed`: Command execution failed; may trigger retry based on `max_retries`
- `expired`: Command TTL exceeded before execution
- Other custom statuses are preserved as-is

**Response** (200 OK - Success):
```json
{
  "acknowledged": true,
  "command_id": "cmd-uuid-1",
  "command_status": "completed",
  "final_status": "completed",
  "terminal_at": "2026-01-17T10:31:30Z"
}
```

**Response** (200 OK - Retry Scheduled):
```json
{
  "acknowledged": true,
  "command_id": "cmd-uuid-1",
  "command_status": "pending",
  "final_status": "pending_retry",
  "will_retry": true,
  "retry_count": 1,
  "max_retries": 3,
  "next_attempt_at": "2026-01-17T10:33:00Z"
}
```

**Idempotency**:
- ACKs are idempotent via `ack_nonce` and hash-based deduplication
- Duplicate ACKs return `replayed: true` and succeed silently
- Safe to retry on network failures

**Error Responses**:
- `404 Not Found`: Command does not exist
- `401 Unauthorized`: Invalid device token
- `403 Forbidden`: Command belongs to different site
- `409 Conflict`: Another device holds the lease
- `410 Gone`: Command has expired (TTL exceeded)

---

#### POST /api/edge/v1/telemetry/ingest

Ingest telemetry batch from edge collector (optional but recommended for monitoring).

**Authentication**: Bearer token (device token)

**Request Body**:
```json
{
  "telemetry": [
    {
      "asset_id": "miner-s21-01",
      "timestamp": "2026-01-17T10:30:45Z",
      "metrics": {
        "hashrate": 95500000000000,
        "power_watts": 3250,
        "chip_temp": 78,
        "pool": "stratum.mining.pool.com"
      }
    }
  ],
  "client_timestamp": "2026-01-17T10:30:43Z"
}
```

**Response** (200 OK):
```json
{
  "processed": 1,
  "received_at": "2026-01-17T10:30:45.123Z",
  "is_delayed": false
}
```

---

### User/Portal Endpoints

These endpoints are called by the cloud portal and admin interfaces. Authentication is via Flask session.

#### POST /api/v1/commands/propose

Propose a new command for execution. Automatically determines if approval is required.

**Authentication**: User session (Bearer token or Cookie)

**Request Body**:
```json
{
  "site_id": 123,
  "zone_id": 1,
  "command_type": "REBOOT",
  "payload": {
    "delay_seconds": 30
  },
  "target_ids": ["asset-id-1", "asset-id-2"],
  "ttl_seconds": 86400
}
```

**Risk Tiers** (automatically determined):
| Command Type | Risk Tier | Approval Required |
|--------------|-----------|-------------------|
| `REBOOT` | MEDIUM | Yes, if > 20 miners |
| `POWER_MODE` | MEDIUM | Yes, if > 20 miners |
| `CHANGE_POOL` | HIGH | Yes, always |
| `SET_FREQ` | MEDIUM | Yes, if > 20 miners |
| `THERMAL_POLICY` | LOW | Usually no |
| `LED` | LOW | Usually no |

**Response** (201 Created):
```json
{
  "success": true,
  "command_id": "cmd-uuid-1",
  "status": "PENDING_APPROVAL",
  "require_approval": true,
  "require_dual_approval": true,
  "steps_required": 2
}
```

**ABAC Enforcement**:
- Customers can only target their own miners (via `customer_id` filter)
- IP addresses in payload are rejected (cloud isolation)
- Failed ABAC checks return `403 Forbidden`

---

#### POST /api/v1/commands/{command_id}/approve

Approve a pending command. Supports multi-step approval workflows.

**Authentication**: User session

**Request Body**:
```json
{
  "reason": "Verified by operations team",
  "step": 1
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "command_status": "QUEUED",
  "approvals_count": 2,
  "steps_required": 2
}
```

**Approval Flow**:
1. User proposes command → status = `PENDING_APPROVAL`
2. Approver 1 approves → status stays `PENDING_APPROVAL`, `approvals_count` increments
3. Approver 2 approves → status transitions to `QUEUED`
4. Edge polls and executes

---

#### POST /api/v1/commands/{command_id}/deny

Reject a pending command.

**Authentication**: User session

**Request Body**:
```json
{
  "reason": "Not approved by operations"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "command_status": "CANCELLED"
}
```

---

#### POST /api/v1/commands/{command_id}/rollback

Create a rollback command to undo a previously executed command.

**Authentication**: User session

**Request Body**:
```json
{
  "reason": "Incorrect settings applied"
}
```

**Constraints**:
- Only commands in terminal states (`COMPLETED`, `SUCCEEDED`, `FAILED`, `PARTIAL`) can be rolled back
- Rollback command is created as `PENDING_APPROVAL` with same risk tier as original
- Targets are automatically set to the original command's targets

**Response** (201 Created):
```json
{
  "success": true,
  "rollback_command_id": "rollback-uuid-1",
  "original_command_id": "cmd-uuid-1",
  "status": "PENDING_APPROVAL",
  "approval_required": {...},
  "message": "Rollback command created. Approval required before execution."
}
```

---

#### GET /api/v1/commands/{command_id}

Get details of a specific command.

**Authentication**: User session

**Response** (200 OK):
```json
{
  "command": {
    "id": "cmd-uuid-1",
    "site_id": 123,
    "command_type": "REBOOT",
    "status": "COMPLETED",
    "target_ids": ["asset-id-1", "asset-id-2"],
    "created_at": "2026-01-17T10:00:00Z",
    "completed_at": "2026-01-17T10:15:00Z",
    "results": [
      {
        "asset_id": "asset-id-1",
        "status": "SUCCEEDED",
        "execution_time_ms": 2500
      },
      {
        "asset_id": "asset-id-2",
        "status": "SUCCEEDED",
        "execution_time_ms": 2300
      }
    ]
  },
  "approvals": [
    {
      "approver_user_id": 42,
      "decision": "APPROVE",
      "reason": "Verified",
      "step": 1,
      "approved_at": "2026-01-17T10:02:00Z"
    }
  ]
}
```

---

#### GET /api/v1/commands

List commands with optional filtering.

**Authentication**: User session

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `site_id` | Integer | Filter by site |
| `zone_id` | Integer | Filter by zone |
| `status` | String | Filter by status (PENDING_APPROVAL, QUEUED, RUNNING, COMPLETED, etc.) |
| `limit` | Integer | Results per page (default 50, max 200) |
| `offset` | Integer | Pagination offset (default 0) |

**Response** (200 OK):
```json
{
  "commands": [
    {
      "id": "cmd-uuid-1",
      "site_id": 123,
      "command_type": "REBOOT",
      "status": "COMPLETED",
      "target_count": 2,
      "created_at": "2026-01-17T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

#### POST /api/v1/price-plans/upload

Upload a price plan (CSV or JSON) for billing calculations.

**Authentication**: User session

**Multipart Form**:
- `site_id` (required): Site to associate plan with
- `plan_name` (optional): Plan identifier (default: "Default Plan")
- `effective_from` (optional): Start date for plan version
- `missing_data_policy` (optional): How to handle missing rates (carry_forward | interpolate)
- `file`: CSV or JSON file

**CSV Format**:
```csv
hour,rate_per_kw
0,0.045
1,0.042
...
23,0.048
```

**JSON Format**:
```json
{
  "rates": [
    {"hour": 0, "rate_per_kw": 0.045},
    {"hour": 1, "rate_per_kw": 0.042}
  ]
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "plan_id": 456,
  "version_number": 1,
  "file_hash": "sha256_hex",
  "effective_from": "2026-01-17",
  "rows_imported": 24
}
```

---

#### GET /api/v1/price-plans/{plan_id}/versions

Retrieve all versions of a price plan (audit trail).

**Authentication**: User session

**Response** (200 OK):
```json
{
  "plan_id": 456,
  "plan_name": "Default Plan",
  "versions": [
    {
      "version_number": 2,
      "effective_from": "2026-01-15",
      "created_at": "2026-01-17T10:30:00Z",
      "file_hash": "sha256_hex_v2",
      "rows": 24
    },
    {
      "version_number": 1,
      "effective_from": "2026-01-01",
      "created_at": "2026-01-10T09:00:00Z",
      "file_hash": "sha256_hex_v1",
      "rows": 24
    }
  ]
}
```

---

### Monitoring Endpoint

#### GET /metrics

Prometheus metrics endpoint for monitoring and alerting.

**Authentication**: None (metrics are typically internal)

**Response** (200 OK, text/plain):
```
# HELP miner_commands_dispatched_total Total commands dispatched to edges
# TYPE miner_commands_dispatched_total counter
miner_commands_dispatched_total{site_id="123",command_type="REBOOT"} 150.0

# HELP miner_commands_acked_total Total command acknowledgments received
# TYPE miner_commands_acked_total counter
miner_commands_acked_total{site_id="123",command_type="REBOOT",outcome="succeeded"} 145.0
miner_commands_acked_total{site_id="123",command_type="REBOOT",outcome="failed"} 5.0

# HELP miner_commands_failed_total Failed commands by error code
# TYPE miner_commands_failed_total counter
miner_commands_failed_total{site_id="123",command_type="REBOOT",error_code="TIMEOUT"} 3.0
miner_commands_failed_total{site_id="123",command_type="REBOOT",error_code="INVALID_PARAM"} 2.0

# HELP rule_evaluations_total Rule evaluations (automation/control)
# TYPE rule_evaluations_total counter
rule_evaluations_total{site_id="123",rule_type="THERMAL_PROTECTION"} 8640.0

# HELP telemetry_ingest_lag_seconds Delay between edge timestamp and cloud receipt
# TYPE telemetry_ingest_lag_seconds gauge
telemetry_ingest_lag_seconds{site_id="123"} 5.2

# HELP command_dispatch_duration_seconds Command dispatch latency histogram
# TYPE command_dispatch_duration_seconds histogram
command_dispatch_duration_seconds_bucket{site_id="123",le="0.01"} 95.0
command_dispatch_duration_seconds_bucket{site_id="123",le="0.1"} 148.0
command_dispatch_duration_seconds_bucket{site_id="123",le="+Inf"} 150.0

# HELP active_leases Active command leases
# TYPE active_leases gauge
active_leases{site_id="123"} 12.0
```

**Key Metrics**:
- **Dispatch Rate**: Monitor `miner_commands_dispatched_total` to detect command volume spikes
- **Success Rate**: Calculate `acked_succeeded / dispatched` for reliability
- **Error Codes**: Track `miner_commands_failed_total` by error code for debugging
- **Telemetry Lag**: Watch `telemetry_ingest_lag_seconds` for network issues
- **Active Leases**: Monitor for stuck leases indicating edge hangs

---

## Error Codes Table

| Error Code | HTTP | Description | Recovery |
|------------|------|-------------|----------|
| `COMMAND_NOT_FOUND` | 404 | Command does not exist in database | Verify command_id; may have been deleted |
| `ACCESS_DENIED` | 403 | Device not authorized for this site/zone | Check device token binding; verify site_id matches |
| `ACK_NOT_LEASE_OWNER` | 409 | Different device holds the lease for this command | Wait for lease to expire; another device is executing |
| `ACK_REPLAYED` | 200 | ACK already processed (idempotent success) | Normal; safe to ignore on retry |
| `COMMAND_EXPIRED` | 410 | Command TTL exceeded before execution | Command is stale; request new command from cloud |
| `RATE_LIMITED` | 429 | Rate limit exceeded for command type | Backoff 30-60 seconds; check `rate_limited_count` in response |
| `SIGNATURE_INVALID` | 401 | HMAC signature mismatch (if `ENABLE_COMMAND_SIGNATURE=true`) | Verify device token and payload integrity |
| `DEVICE_TOKEN_INVALID` | 401 | Device token is invalid or revoked | Re-register device via `/api/edge/v1/register` |
| `ZONE_ACCESS_DENIED` | 403 | Device bound to different zone than requested | Device zone_id immutable; contact admin to migrate |

---

## curl Examples

### Device Registration

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "edge_id": "collector-site-01",
    "site_id": 123,
    "zone_id": 1
  }' \
  https://app.example.com/api/edge/v1/register
```

### Poll for Commands

```bash
# Basic poll (default limit=10)
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  https://app.example.com/api/edge/v1/commands/poll

# Poll with custom limit
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  "https://app.example.com/api/edge/v1/commands/poll?limit=25&zone_id=1"
```

### Acknowledge Command Success

```bash
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "ack_nonce": "550e8400-e29b-41d4-a716-446655440000",
    "result_code": 0,
    "result_message": "Command executed successfully",
    "execution_time_ms": 2500
  }' \
  https://app.example.com/api/edge/v1/commands/cmd-uuid-1/ack
```

### Acknowledge Command Failure (with Retry)

```bash
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "status": "failed",
    "ack_nonce": "550e8400-e29b-41d4-a716-446655440000",
    "result_code": "MINER_UNREACHABLE",
    "result_message": "Unable to connect to miner IP address",
    "execution_time_ms": 5000
  }' \
  https://app.example.com/api/edge/v1/commands/cmd-uuid-1/ack
```

### Ingest Telemetry

```bash
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "telemetry": [
      {
        "asset_id": "miner-s21-01",
        "timestamp": "2026-01-17T10:30:45Z",
        "metrics": {
          "hashrate": 95500000000000,
          "power_watts": 3250,
          "chip_temp": 78
        }
      }
    ],
    "client_timestamp": "2026-01-17T10:30:43Z"
  }' \
  https://app.example.com/api/edge/v1/telemetry/ingest
```

### Propose Command (User/Portal)

```bash
curl -X POST \
  -H "Authorization: Bearer user_session_token" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": 123,
    "zone_id": 1,
    "command_type": "REBOOT",
    "payload": {"delay_seconds": 30},
    "target_ids": ["asset-id-1", "asset-id-2"],
    "ttl_seconds": 86400
  }' \
  https://app.example.com/api/v1/commands/propose
```

### Approve Command

```bash
curl -X POST \
  -H "Authorization: Bearer user_session_token" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Verified by operations team",
    "step": 1
  }' \
  https://app.example.com/api/v1/commands/cmd-uuid-1/approve
```

### Get Command Status

```bash
curl -H "Authorization: Bearer user_session_token" \
  https://app.example.com/api/v1/commands/cmd-uuid-1
```

### List Commands

```bash
# List all COMPLETED commands for a site
curl -H "Authorization: Bearer user_session_token" \
  "https://app.example.com/api/v1/commands?site_id=123&status=COMPLETED&limit=50"
```

### Upload Price Plan

```bash
curl -X POST \
  -H "Authorization: Bearer user_session_token" \
  -F "site_id=123" \
  -F "plan_name=Q1-2026-Rates" \
  -F "effective_from=2026-01-01" \
  -F "file=@rates.csv" \
  https://app.example.com/api/v1/price-plans/upload
```

### Get Prometheus Metrics

```bash
curl https://app.example.com/metrics | grep miner_commands

# Filter for specific site
curl https://app.example.com/metrics | grep 'site_id="123"'
```

---

## Troubleshooting

### Issue: Commands Not Being Dispatched

**Symptoms**: 
- Edge polls but receives empty `commands` array
- `dispatched_count` is 0

**Diagnosis**:
1. Check if command exists in database: `SELECT * FROM miner_command WHERE status='pending' LIMIT 5;`
2. Verify lease is not held by another device: `SELECT lease_owner, lease_until FROM miner_command WHERE status='dispatched';`
3. Check command expiration: `SELECT expires_at, NOW() FROM miner_command WHERE id='cmd-uuid-1';`

**Solutions**:
- **Rate Limited**: Check `rate_limited_count` in response. Wait 30-60s and retry.
- **Lease Stuck**: If `lease_until` is old and device is unresponsive, manually release lease:
  ```sql
  UPDATE miner_command SET status='pending', lease_owner=NULL, lease_until=NULL 
  WHERE status='dispatched' AND lease_until < NOW() - INTERVAL '5 minutes';
  ```
- **Command Expired**: Create a new command with fresh TTL.

---

### Issue: ACK Failures with "NOT_LEASE_OWNER"

**Symptoms**:
- Edge receives command with `ack_nonce`
- ACK returns `409 Conflict` with `ACK_NOT_LEASE_OWNER`

**Diagnosis**:
1. Verify edge still holds lease: `SELECT lease_owner, lease_until FROM miner_command WHERE id='cmd-uuid-1';`
2. Check current time: `SELECT NOW();`
3. Verify it's the same edge: `SELECT lease_owner FROM miner_command; SELECT edge_device_id FROM edge_device WHERE device_token='...';`

**Solutions**:
- **Lease Expired**: Re-poll before sending ACK. Cloud extended lease timeout to 60s.
- **Different Device**: Multiple devices polling same command. Ensure only one active poller per site.
- **Clock Skew**: Sync system clocks between edge and cloud (NTP).

---

### Issue: Rate Limiting / Command Queue Buildup

**Symptoms**:
- `rate_limited_count > 0` in poll responses
- Command execution is slower than expected

**Diagnosis**:
1. Check Redis rate limiter state:
   ```bash
   redis-cli GET "rate_limit:site:123:REBOOT:window:$(date +%s | head -c 6)"
   ```
2. Monitor Prometheus metrics: `miner_commands_dispatched_total` vs `miner_commands_acked_total`
3. Calculate backlog: `SELECT COUNT(*) FROM miner_command WHERE status IN ('pending', 'dispatched');`

**Solutions**:
- **High Volume**: Increase edge polling frequency and `limit` parameter (up to 50).
- **Slow Execution**: Check edge device logs for slow command execution. Increase `max_retries` to reduce failures.
- **Queue Pressure**: Reduce TTL on non-critical commands or prioritize high-priority commands.
- **Tune Rate Limits**: Adjust `check_rate_limit()` in `services/rate_limiter.py` based on edge capacity.

---

### Issue: HMAC Signature Validation Failures

**Symptoms**:
- Enabled `ENABLE_COMMAND_SIGNATURE=true`
- Edge receives command with `cloud_signature` but cannot verify

**Diagnosis**:
1. Verify signature is enabled: `echo $ENABLE_COMMAND_SIGNATURE`
2. Check device token is consistent:
   ```bash
   # Edge should use same token for auth and signature verification
   AUTH_HEADER="Authorization: Bearer $DEVICE_TOKEN"
   # Signature payload includes: command_id:command_type:timestamp
   ```
3. Compare hashes:
   ```python
   import hmac, hashlib
   payload = "cmd-uuid-1:REBOOT:2026-01-17T10:30:45.123Z"
   expected = hmac.new(device_token.encode(), payload.encode(), hashlib.sha256).hexdigest()
   actual = cloud_signature
   print(f"Match: {expected == actual}")
   ```

**Solutions**:
- **Token Mismatch**: Ensure edge uses device_token from registration, not device ID.
- **Timestamp Skew**: Sync clocks (NTP). Signature includes ISO timestamp; > 5s drift causes failures.
- **Case Sensitivity**: Command type and UUID must match exactly.
- **Disable Temporarily**: Set `ENABLE_COMMAND_SIGNATURE=false` for debugging, then re-enable.

---

### Issue: Zone Access Denied on Poll

**Symptoms**:
- Edge poll returns `403 Forbidden: Zone access denied - device bound to different zone`

**Diagnosis**:
1. Check device zone binding: `SELECT zone_id FROM edge_device WHERE id='device-uuid';`
2. Verify request zone matches:
   ```bash
   curl "https://app.example.com/api/edge/v1/commands/poll?zone_id=2"
   # Device bound to zone 1, but requested zone 2
   ```

**Solutions**:
- **Remove Zone Filter**: Don't pass `zone_id` in query; device's bound zone is used automatically.
- **Re-register Device**: If zone changed, re-register device:
  ```bash
  curl -X POST -d '{"edge_id":"...", "site_id":123, "zone_id":1}' .../api/edge/v1/register
  ```
- **Multi-Zone Setup**: Each edge device is bound to one zone. For multi-zone operation, deploy multiple edge instances (one per zone).

---

### Issue: Commands Stuck in PENDING_APPROVAL

**Symptoms**:
- Command proposed 1+ hour ago still in `PENDING_APPROVAL`
- `approvals` array shows no entries or incomplete approvals

**Diagnosis**:
1. Check approval requirement: `SELECT * FROM command_approval WHERE command_id='cmd-uuid-1';`
2. Get approval policy:
   ```sql
   SELECT * FROM approval_policy WHERE site_id=123 AND command_type='REBOOT';
   ```
3. Count approvals vs required:
   ```sql
   SELECT COUNT(*) FROM command_approval 
   WHERE command_id='cmd-uuid-1' AND decision='APPROVE';
   ```

**Solutions**:
- **Missing Approvers**: Contact site admins to provide approvals.
- **Wrong Approver Role**: Check if approver has correct role; some policies require specific roles.
- **Expired Policy**: If approval policy changed, old commands may reference outdated requirements. Create new command.
- **Override (Admin Only)**: Manually update status:
  ```sql
  UPDATE remote_command SET status='QUEUED' WHERE id='cmd-uuid-1';
  ```

---

### Monitoring Rate Limit Status

To check current rate limit usage:

```bash
# Get Redis client connection
redis-cli

# Check limits for a specific site and command type
KEYS "rate_limit:site:123:REBOOT:*"
GET "rate_limit:site:123:REBOOT:window:$(date +%s | head -c 6)"

# Check all rate limits
KEYS "rate_limit:*"

# Monitor real-time (watch every 1 second)
MONITOR | grep rate_limit
```

To read rate limits from application:

```python
from services.rate_limiter import check_rate_limit

allowed, rate_info = check_rate_limit(site_id=123, command_type='REBOOT')
print(f"Allowed: {allowed}")
print(f"Limit: {rate_info.get('limit')}")
print(f"Current Count: {rate_info.get('current_count')}")
print(f"Reset At: {rate_info.get('reset_at')}")
```

---

### Verifying HMAC Signatures

To manually verify a signature received from cloud:

```python
import hmac
import hashlib
from datetime import datetime

# Received from cloud in command
cloud_signature = "a1b2c3d4e5f6..."
sig_version = "v1"
signed_at = "2026-01-17T10:30:45Z"
command_id = "cmd-uuid-1"
command_type = "REBOOT"

# Your device token (known to edge)
device_token = "edge-token-secret-key"

# Reconstruct the payload that was signed
signature_payload = f"{command_id}:{command_type}:{signed_at}"

# Compute HMAC-SHA256
computed = hmac.new(
    device_token.encode('utf-8'),
    signature_payload.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# Verify
if computed == cloud_signature:
    print("✓ Signature valid")
else:
    print("✗ Signature mismatch")
    print(f"Expected: {computed}")
    print(f"Received: {cloud_signature}")
```

---

### Debugging Audit Trail

Commands and approvals are logged in the immutable audit trail for compliance:

```sql
-- View audit events for a specific command
SELECT event_type, actor_type, actor_id, event_hash, prev_hash, payload_json, created_at
FROM audit_event
WHERE ref_type='command' AND ref_id='cmd-uuid-1'
ORDER BY created_at ASC;

-- Verify audit chain integrity
SELECT id, event_hash, prev_hash, 
  CASE WHEN event_hash = SHA2(CONCAT(prev_hash, ':', payload_json), 256) 
    THEN 'VALID' ELSE 'INVALID' END as chain_status
FROM audit_event
ORDER BY id DESC
LIMIT 100;

-- Find all commands approved by a user
SELECT DISTINCT ref_id, event_type, created_at
FROM audit_event
WHERE actor_type='user' AND actor_id=42 AND event_type LIKE 'command.%'
ORDER BY created_at DESC;
```

---

## Integration Checklist

Before deploying Control Plane API to production:

- [ ] Set `REDIS_URL` to production Redis instance
- [ ] Configure `ENABLE_COMMAND_SIGNATURE=true` for secure command verification
- [ ] Deploy edge collectors with device tokens pre-provisioned
- [ ] Test command poll → dispatch → ACK flow end-to-end
- [ ] Set up Prometheus scraping of `/metrics` endpoint
- [ ] Configure alerting for `rate_limited_count > 0` (5-min average)
- [ ] Configure alerting for failed commands: `miner_commands_failed_total > threshold`
- [ ] Verify audit trail: `SELECT COUNT(*) FROM audit_event;`
- [ ] Load test with expected command volume (e.g., 1000 commands/minute)
- [ ] Document zone-to-edge device mapping for your deployment
- [ ] Train operators on approval workflow and command monitoring

