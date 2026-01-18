# Edge Collector Remote Control v1.1 - Cloud Specification

## Overview

This document specifies the Cloud-side implementation of Edge Collector Remote Control v1.1, designed for 20MW+ Bitcoin mining operations requiring atomic command dispatch, audit compliance, and high reliability.

## Table of Contents

1. [Command Protocol Contract](#command-protocol-contract)
2. [HMAC Signature Generation](#hmac-signature-generation)
3. [Command Dispatch Lease](#command-dispatch-lease)
4. [ACK Endpoint & Idempotency](#ack-endpoint--idempotency)
5. [Rate Limiting & Deduplication](#rate-limiting--deduplication)
6. [Command Type Standardization](#command-type-standardization)
7. [Safety Events Endpoint](#safety-events-endpoint)
8. [API Reference](#api-reference)
9. [Error Codes](#error-codes)
10. [Configuration](#configuration)

---

## Command Protocol Contract

### Poll Response Fields (Cloud → Collector)

Each command returned by `GET /api/edge/v1/commands/poll` includes:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command_id` | string | ✓ | Unique command identifier |
| `site_id` | integer | ✓ | Target site ID |
| `zone_id` | integer | ✓ | Zone partition ID |
| `miner_id` | integer | ✓* | Target miner ID (*null for multi-miner commands) |
| `command_type` | string | ✓ | Standardized command type (see below) |
| `params` | object | ✓ | Command parameters |
| `priority` | integer | ✓ | Execution priority (0=normal, higher=urgent) |
| `expires_at` | string | ✓ | Expiration timestamp (UTC ISO8601) |
| `dedupe_key` | string |   | Deduplication key for automation rules |
| `signed_at` | string | ✓ | Signature timestamp (UTC ISO8601) |
| `nonce` | string | ✓ | Unique nonce for replay protection |
| `signature` | string | ✓ | HMAC signature (hex-encoded) |
| `sig_version` | string | ✓ | `HMAC-SHA256-CANONICAL-JSON-V1` |
| `sig_encoding` | string | ✓ | `hex` |

### Example Poll Response

```json
{
  "commands": [
    {
      "command_id": "cmd_abc123",
      "site_id": 42,
      "zone_id": 5,
      "miner_id": 1001,
      "command_type": "MINER_RESTART",
      "params": {"reason": "scheduled_maintenance"},
      "priority": 0,
      "expires_at": "2026-01-18T12:00:00Z",
      "dedupe_key": "rule_001_miner_1001_restart",
      "signed_at": "2026-01-18T10:00:00Z",
      "nonce": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "signature": "a1b2c3d4e5f6...",
      "sig_version": "HMAC-SHA256-CANONICAL-JSON-V1",
      "sig_encoding": "hex"
    }
  ],
  "miner_command_count": 1,
  "remote_command_count": 0
}
```

---

## HMAC Signature Generation

### Canonical JSON Format

The Cloud generates signatures using a strict canonical JSON format:

```python
# Fixed field set (order matters for canonical form)
canonical_fields = {
    'command_id': str,
    'site_id': int,
    'zone_id': int,
    'miner_id': int | None,
    'command_type': str,
    'params': dict,
    'priority': int,
    'expires_at': str,  # UTC ISO8601
    'dedupe_key': str | None,
    'signed_at': str,   # UTC ISO8601
    'nonce': str
}

# Canonical JSON generation
canonical_json = json.dumps(
    canonical_fields,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False
)

# HMAC-SHA256 signature
signature = hmac.new(
    hmac_secret.encode('utf-8'),
    canonical_json.encode('utf-8'),
    hashlib.sha256
).hexdigest()
```

### EdgeDevice HMAC Secret

Each EdgeDevice stores its HMAC secret in the `hmac_secret` field:

```sql
ALTER TABLE edge_devices ADD COLUMN hmac_secret VARCHAR(64);
```

Secrets are 256-bit values stored as hex strings (64 characters).

---

## Command Dispatch Lease

### Atomic Lease Acquisition

Commands are dispatched using atomic lease acquisition to prevent duplicate execution:

```sql
SELECT * FROM miner_commands
WHERE site_id = :site_id
  AND status = 'pending'
  AND (lease_until IS NULL OR lease_until < NOW())
  AND expires_at > NOW()
ORDER BY priority DESC, created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT :limit;
```

### Lease Fields

| Field | Type | Description |
|-------|------|-------------|
| `lease_owner` | string | Collector device ID holding the lease |
| `lease_until` | timestamp | Lease expiration (default: now + 60 seconds) |
| `dispatched_at` | timestamp | When command was dispatched |

### Lease Recovery

Expired leases are automatically recovered by the `LeaseRecoveryScheduler`:

- Runs every 60 seconds
- Resets `status` to `pending` for expired leases
- Implements exponential backoff: `retry_backoff_sec * 2^retry_count`

---

## ACK Endpoint & Idempotency

### Endpoint

```
POST /api/edge/v1/commands/{command_id}/ack
```

### Request Body

```json
{
  "status": "succeeded",
  "result_code": 0,
  "message": "Command executed successfully",
  "executed_at": "2026-01-18T10:05:00Z",
  "before_snapshot": {...},
  "after_snapshot": {...},
  "nonce": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `succeeded` | Command completed successfully |
| `failed` | Command failed (will retry if retries remaining) |
| `deferred` | Command deferred for later execution |
| `rejected` | Command rejected by miner/device |

### Idempotency Rules

1. **Hash-based deduplication**: Each ACK computes `ack_hash = SHA256(command_id + status + result_code + message)`
2. **Replay detection**: If `ack_hash` matches previous ACK, returns `{"replayed": true}` without state change
3. **Terminal state protection**: Commands in terminal states (`succeeded`, `failed`, `expired`, `cancelled`) reject new ACKs

---

## Rate Limiting & Deduplication

### Rate Limit Configuration

| Command Type | Rate | Window |
|--------------|------|--------|
| `MINER_RESTART` | 5 | 300 seconds |
| `DEVICE_REBOOT` | 5 | 300 seconds |
| default | 20 | 60 seconds |

### Redis Sliding Window

```python
bucket_key = f"ratelimit:{site_id}:{command_type}"
current_count = redis.zcount(bucket_key, window_start, now)
if current_count >= limit:
    return (False, {"error": "RATE_LIMITED"})
```

### Deduplication Key

Automation rules generate dedupe keys:

```python
dedupe_key = sha256(f"{rule_id}:{miner_id}:{action_type}:{trigger_type}")[:32]
```

Partial unique index prevents duplicate active commands:

```sql
CREATE UNIQUE INDEX ix_miner_commands_dedupe_active
ON miner_commands(dedupe_key)
WHERE status IN ('pending', 'dispatched', 'running') AND dedupe_key IS NOT NULL;
```

---

## Command Type Standardization

### v1.1 Standard Command Types

| Command Type | Description | Legacy Aliases |
|--------------|-------------|----------------|
| `MINER_RESTART` | Restart miner software | `reboot`, `restart` |
| `DEVICE_REBOOT` | Full device reboot | `device_reboot` |
| `HASHING_ENABLE` | Enable hashing | `start`, `enable` |
| `HASHING_DISABLE` | Disable hashing | `stop`, `disable` |
| `POOL_SET` | Update pool configuration | `set_pool`, `pool_set` |
| `SET_FAN` | Adjust fan speed | `set_fan` |
| `SET_FREQUENCY` | Adjust hash frequency | `set_frequency` |
| `POWER_MODE` | Set power mode (LOW/NORMAL/HIGH) | `power_mode` |

### Backward Compatibility

Legacy command types are automatically mapped:

```python
COMMAND_TYPE_MAP = {
    'reboot': 'MINER_RESTART',
    'restart': 'MINER_RESTART',
    'device_reboot': 'DEVICE_REBOOT',
    'stop': 'HASHING_DISABLE',
    'start': 'HASHING_ENABLE',
    # ...
}
```

---

## Safety Events Endpoint

### Endpoint

```
POST /api/edge/v1/events/safety/batch
```

### Request Body

```json
{
  "events": [
    {
      "miner_id": 1001,
      "action": "THERMAL_SHUTDOWN",
      "reason": "Temperature exceeded 95C threshold",
      "temp_max": 98.5,
      "ts": "2026-01-18T10:30:00Z",
      "snapshot_json": {
        "hashrate": 100.5,
        "fan_speed": 100,
        "power_draw": 3200
      }
    }
  ]
}
```

### Response

```json
{
  "status": "success",
  "processed": 1,
  "failed": 0,
  "received_at": "2026-01-18T10:30:05Z"
}
```

### Safety Event Actions

| Action | Description |
|--------|-------------|
| `THERMAL_SHUTDOWN` | Emergency shutdown due to overheating |
| `EMERGENCY_STOP` | Manual emergency stop triggered |
| `POWER_LIMIT` | Power draw exceeded threshold |
| `FAN_FAILURE` | Fan failure detected |

---

## API Reference

### GET /api/edge/v1/commands/poll

Poll for pending commands.

**Query Parameters:**
- `limit` (int, default: 10): Maximum commands to return

**Headers:**
- `Authorization: Bearer <device_token>`

**Example:**
```bash
curl -H "Authorization: Bearer $DEVICE_TOKEN" \
     "https://cloud.example.com/api/edge/v1/commands/poll?limit=10"
```

### POST /api/edge/v1/commands/{command_id}/ack

Acknowledge command execution.

**Example:**
```bash
curl -X POST \
     -H "Authorization: Bearer $DEVICE_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"status":"succeeded","result_code":0}' \
     "https://cloud.example.com/api/edge/v1/commands/cmd_abc123/ack"
```

### POST /api/edge/v1/events/safety/batch

Submit batch of safety events.

**Example:**
```bash
curl -X POST \
     -H "Authorization: Bearer $DEVICE_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"events":[{"miner_id":1001,"action":"THERMAL_SHUTDOWN","reason":"Temp exceeded 95C","temp_max":98.5,"ts":"2026-01-18T10:30:00Z"}]}' \
     "https://cloud.example.com/api/edge/v1/events/safety/batch"
```

### GET /metrics

Prometheus metrics endpoint.

**Example:**
```bash
curl "https://cloud.example.com/metrics"
```

---

## Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `COMMAND_NOT_FOUND` | 404 | Command does not exist |
| `ACCESS_DENIED` | 403 | Device not authorized for this site |
| `ACK_NOT_LEASE_OWNER` | 409 | Device didn't acquire command lease |
| `ACK_REPLAYED` | 200 | ACK already processed (idempotent) |
| `COMMAND_EXPIRED` | 410 | Command TTL exceeded |
| `RATE_LIMITED` | 429 | Rate limit exceeded for command type |
| `SIGNATURE_INVALID` | 401 | HMAC signature verification failed |
| `NONCE_MISMATCH` | 401 | Nonce doesn't match dispatched value |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_COMMAND_SIGNATURE` | `false` | Enable HMAC signature verification |
| `REDIS_URL` | - | Redis URL for rate limiting |
| `COMMAND_LEASE_DURATION_SEC` | `60` | Lease timeout in seconds |
| `MAX_COMMAND_RETRIES` | `3` | Maximum retry attempts |
| `DEFAULT_RETRY_BACKOFF_SEC` | `30` | Base backoff duration |

### Default Rate Limits

| Command Type | Limit | Window (seconds) |
|--------------|-------|------------------|
| `MINER_RESTART` | 5 | 300 |
| `DEVICE_REBOOT` | 5 | 300 |
| `HASHING_DISABLE` | 10 | 300 |
| default | 20 | 60 |

---

## Database Migrations

| Migration | Description |
|-----------|-------------|
| `022_add_edge_device_hmac_secret.sql` | Add hmac_secret to edge_devices |
| `023_create_safety_events.sql` | Create safety_events table |

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `commands_dispatched_total` | Counter | Total commands dispatched |
| `commands_acked_total` | Counter | Total ACKs received |
| `commands_failed_total` | Counter | Failed commands by error code |
| `command_dispatch_duration_seconds` | Histogram | Dispatch latency |
| `active_leases` | Gauge | Current active leases per site |
| `telemetry_ingest_lag_seconds` | Gauge | Telemetry ingestion delay |
| `rule_evals_total` | Counter | Automation rule evaluations |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.1 | 2026-01-18 | Canonical JSON signatures, safety events, command standardization |
| v1.0 | 2026-01-17 | Initial atomic lease, rate limiting, dedupe |
