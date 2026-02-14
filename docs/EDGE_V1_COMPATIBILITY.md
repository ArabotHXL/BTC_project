# Edge v1 Protocol Compatibility Matrix

## Overview

The Edge v1 protocol provides a unified, versioned API surface for edge collectors (Raspberry Pi, on-prem gateways) to interact with the HashInsight Cloud platform. It consolidates telemetry ingestion and command dispatch into two endpoint groups under `/api/edge/v1/`.

### Design Goals

- **Single versioned prefix** — all edge-facing routes live under `/api/edge/v1/`
- **Dual auth** — supports both `EdgeDevice` tokens and legacy `CollectorKey` tokens
- **Format flexibility** — accepts plain lists, envelope v1, and legacy dict payloads
- **Gzip support** — transparent decompression of `Content-Encoding: gzip` bodies
- **Encrypted payload rejection** — returns `422` for `payload_enc` fields to enforce plaintext-only ingestion at the v1 layer

---

## Authentication Methods

| Method | Header | Token Source | Zone Binding |
|---|---|---|---|
| EdgeDevice token | `Authorization: Bearer <token>` | `edge_devices.device_token` or `token_hash` | Yes — bound to `(site_id, zone_id)` |
| CollectorKey token | `Authorization: Bearer <token>` or `X-Collector-Key: <token>` | `collector_keys.key_hash` | No — `zone_id` is `NULL` |

Both methods are handled by the `require_edge_auth` decorator. The decorator sets `g.auth_method` to either `'edge_device'` or `'collector_key'`.

### Token Lookup Order

1. Extract `Bearer` token from `Authorization` header
2. Hash with SHA-256, look up in `edge_devices.token_hash`
3. Fall back to plaintext match on `edge_devices.device_token`
4. If no EdgeDevice match, try `collector_keys.key_hash`
5. If still no match, check `X-Collector-Key` header
6. Return `401` if all lookups fail

---

## Telemetry Endpoints

### POST `/api/edge/v1/telemetry/ingest`

Primary telemetry ingestion endpoint.

| Feature | Supported | Notes |
|---|---|---|
| Plain list format | ✅ | `[{"worker_id":"...","hashrate_rt":85.3}]` |
| Telemetry envelope v1 | ✅ | `{"format":"telemetry_envelope.v1","collected_at":"...","miners":[...]}` |
| Legacy dict format | ✅ | `{"device_id":"...","timestamp":"...","miners":[...]}` |
| Gzip compression | ✅ | `Content-Encoding: gzip` header triggers automatic decompression |
| `payload_enc` rejection | ✅ | Returns `422 Unprocessable Entity` — encrypted payloads not accepted on v1 |
| Batch alias | ✅ | `/api/edge/v1/telemetry/batch` routes to the same handler |

### Input Format Details

#### 1. Plain List

```json
[
  {
    "worker_id": "miner-001",
    "hashrate_rt": 85.3,
    "temperature": 62,
    "fan_speeds": [5200, 5100]
  }
]
```

#### 2. Telemetry Envelope v1

```json
{
  "format": "telemetry_envelope.v1",
  "collected_at": "2026-02-14T12:00:00Z",
  "edge_version": "0.9.1",
  "miners": [
    {
      "worker_id": "miner-001",
      "hashrate_rt": 85.3,
      "temperature": 62
    }
  ]
}
```

#### 3. Legacy Dict

```json
{
  "device_id": "collector-pi-01",
  "timestamp": "2026-02-14T12:00:00Z",
  "miners": [
    {
      "worker_id": "miner-001",
      "hashrate_rt": 85.3,
      "temperature": 62
    }
  ]
}
```

### Response Format

```json
{
  "status": "ok",
  "received": 5,
  "processed": 5,
  "online": 4,
  "offline": 1,
  "inserted": 2,
  "updated": 3,
  "errors": []
}
```

---

## Commands Endpoints

### GET `/api/edge/v1/commands/poll`

Polls for pending commands assigned to the authenticated device/site.

| Feature | Supported | Notes |
|---|---|---|
| Atomic lease dispatch | ✅ | `SELECT FOR UPDATE SKIP LOCKED` |
| Zone binding validation | ✅ | `?zone_id=` must match device zone |
| Rate limiting | ✅ | Per-site, per-command-type limits |
| HMAC signatures | ✅ | Optional, enabled via `ENABLE_COMMAND_SIGNATURE=true` |
| MinerCommand (single) | ✅ | `command_source: "miner"` |
| RemoteCommand (legacy) | ✅ | `command_source: "remote"` |
| CollectorKey auth | ✅ | Zone binding bypassed |

#### Query Parameters

| Param | Type | Default | Description |
|---|---|---|---|
| `zone_id` | int | — | Optional zone filter (validated against device binding) |
| `limit` | int | 10 | Max commands to return (capped at 50) |

### POST `/api/edge/v1/commands/{command_id}/ack`

Acknowledges command execution result.

| Feature | Supported | Notes |
|---|---|---|
| `status` field | ✅ | `SUCCESS`, `FAILED`, `ERROR`, `TIMEOUT` |
| `result` field | ✅ | Arbitrary JSON result object |
| `execution_time_ms` | ✅ | Standard field name |
| `duration_ms` alias | ✅ | Mapped to `execution_time_ms` for backward compatibility |
| `error_message` | ✅ | Error description when status is `FAILED` |
| Idempotent ACK | ✅ | Via `ack_nonce` / `dispatch_nonce` |
| RemoteCommand sync | ✅ | Auto-syncs parent RemoteCommand status |

#### Ack Payload

```json
{
  "status": "SUCCESS",
  "result": {"hashrate_after": 95.2},
  "execution_time_ms": 1500,
  "error_message": null
}
```

---

## Migration Guide: Legacy `collector_api` → Edge v1

### Telemetry Upload

| Legacy | Edge v1 |
|---|---|
| `POST /api/collector/upload` | `POST /api/edge/v1/telemetry/ingest` |
| `X-Collector-Key` header | `Authorization: Bearer <token>` (or `X-Collector-Key`) |
| Encrypted payloads (`payload_enc`) | Not supported — use plaintext JSON |
| No gzip support | `Content-Encoding: gzip` supported |

### Command Polling

| Legacy | Edge v1 |
|---|---|
| `GET /api/collector/commands` | `GET /api/edge/v1/commands/poll` |
| No lease mechanism | Atomic lease with `SELECT FOR UPDATE SKIP LOCKED` |
| No rate limiting | Per-site, per-type rate limiting |
| No signatures | Optional HMAC-SHA256 signatures |

### Command Acknowledgment

| Legacy | Edge v1 |
|---|---|
| `POST /api/collector/commands/<id>/ack` | `POST /api/edge/v1/commands/<id>/ack` |
| `execution_time_ms` only | `execution_time_ms` or `duration_ms` alias |
| No idempotency | Idempotent via `ack_nonce` |
| No parent sync | Auto-syncs RemoteCommand parent status |

### Configuration Change

In `collector_config_example.json`, set `api_url` to the base URL only:

```json
{
  "api_url": "https://calc.hashinsight.net"
}
```

The collector appends the endpoint path automatically. The v1 telemetry endpoint is `/api/edge/v1/telemetry/ingest`.

---

## Known Limitations

1. **No encrypted payload support** — `payload_enc` payloads are rejected with `422`. End-to-end encryption must be handled at the transport layer (TLS).
2. **Zone binding is device-only** — CollectorKey auth does not enforce zone isolation; the key is site-scoped.
3. **HMAC signatures are opt-in** — Requires `ENABLE_COMMAND_SIGNATURE=true` environment variable. Not enforced by default.
4. **Rate limits are in-memory** — Rate limiting state is not shared across multiple server instances. A Redis-backed rate limiter is recommended for multi-instance deployments.
5. **Lease expiry is fixed** — Command lease duration is 60 seconds, not configurable per-command.
6. **No WebSocket push** — Commands must be polled; there is no server-push mechanism for real-time command delivery.
7. **Legacy RemoteCommand coexistence** — Both `MinerCommand` and `RemoteCommand` objects are returned in poll results. The `command_source` field distinguishes them.
