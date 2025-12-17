# Phase 3 - Reliability & Performance Documentation
# 阶段3 - 可靠性与性能文档

**Generated**: 2025-12-12  
**Repository**: HashInsight Enterprise - BTC Mining Farm Management Platform

---

## 1. Overview / 概述

This document records reliability patterns, performance optimizations, and operational considerations for the CGMiner/Collector subsystem.

---

## 2. Connection Management / 连接管理

### 2.1 CGMiner TCP Connections

**Current Approach**: New socket per request (no pooling)

| Aspect | Implementation | Rationale |
|--------|---------------|-----------|
| Connection Reuse | ❌ Not implemented | CGMiner doesn't support persistent connections |
| Timeout | 5 seconds default | Balance between reliability and quick failure detection |
| Max Retries | 3 attempts | Handles transient network issues |
| Backoff | Exponential + Jitter | Prevents thundering herd |

**Exponential Backoff Formula**:
```python
wait_time = RETRY_BACKOFF_BASE * (2 ** attempt)  # 0.5s, 1s, 2s
wait_time += wait_time * 0.1 * random_jitter     # Add 0-10% jitter
```

### 2.2 Database Connections

**Current Approach**: SQLAlchemy connection pool

```python
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,    # Recycle connections every 5 minutes
    "pool_pre_ping": True,  # Verify connection before use
}
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `pool_recycle` | 300s | Avoid stale connections |
| `pool_pre_ping` | True | Detect broken connections |
| `pool_size` | 5 (default) | Concurrent connections |
| `max_overflow` | 10 (default) | Burst capacity |

### 2.3 Redis Connections

**Current Approach**: Single connection with retry

```python
# cache_manager.py
REDIS_RETRY_ON_ERROR = [ConnectionError, TimeoutError]
REDIS_RETRY_COUNT = 3
```

---

## 3. Caching Strategy / 缓存策略

### 3.1 Stale-While-Revalidate (SWR) Pattern

Used for expensive API calls (CoinGecko, CoinWarz):

```python
def get_btc_price():
    cached = cache.get('btc_price')
    if cached:
        return cached  # Return stale data immediately
    
    # Revalidate in background
    if should_revalidate():
        background_refresh()
    
    return cached or fetch_fresh()
```

### 3.2 Cache TTL Configuration

| Cache Key | TTL | Invalidation |
|-----------|-----|--------------|
| `btc_price` | 60s | Time-based |
| `btc_difficulty` | 300s | Time-based |
| `telemetry:live:{site_id}` | 60s | Time-based |
| `telemetry:summary:{site_id}` | 30s | Time-based |
| `miner_models` | 3600s | Time-based |
| `user_session:{id}` | 86400s | Logout event |

### 3.3 Cache Stampede Prevention

When cache expires, multiple workers might try to refresh simultaneously. Mitigations:

1. **Probabilistic Early Expiry**: Refresh slightly before TTL
2. **Lock-based Refresh**: Only one worker refreshes
3. **Background Refresh**: Async refresh before expiry

```python
def get_with_stampede_protection(key, ttl, refresh_fn):
    data, expires_at = cache.get_with_meta(key)
    
    # Probabilistic early refresh (last 10% of TTL)
    remaining = expires_at - time.time()
    if remaining < ttl * 0.1 and random.random() < 0.3:
        try:
            fresh_data = refresh_fn()
            cache.set(key, fresh_data, ttl)
            return fresh_data
        except:
            pass  # Return stale on error
    
    return data
```

---

## 4. Polling & Collection / 轮询与采集

### 4.1 APScheduler Configuration

```python
# services/cgminer_scheduler.py
scheduler = BackgroundScheduler()
scheduler.add_job(
    collect_all_miners_telemetry,
    'interval',
    seconds=60,
    max_instances=1,  # Prevent overlap
    coalesce=True,    # Skip if previous still running
    misfire_grace_time=30
)
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `interval` | 60s | Collection frequency |
| `max_instances` | 1 | Prevent concurrent runs |
| `coalesce` | True | Skip missed jobs |
| `misfire_grace_time` | 30s | Accept delayed execution |

### 4.2 Thread Pool for Miner Polling

```python
# services/cgminer_collector.py
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = [
        executor.submit(poll_single_miner, miner)
        for miner in miners
    ]
    # Wait with timeout
    for future in as_completed(futures, timeout=300):
        try:
            result = future.result(timeout=10)
        except TimeoutError:
            log_timeout()
```

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `max_workers` | 20 | Balance parallelism vs. resource usage |
| `timeout` | 300s | Total collection timeout |
| `future timeout` | 10s | Per-miner timeout |

### 4.3 Jitter for Edge Collectors

Edge collectors should add jitter to prevent synchronized requests:

```python
# edge_collector/main.py
COLLECTION_INTERVAL = 60
JITTER_RANGE = 10  # seconds

while True:
    collect_and_upload()
    
    # Add jitter to prevent synchronization
    sleep_time = COLLECTION_INTERVAL + random.uniform(-JITTER_RANGE, JITTER_RANGE)
    time.sleep(sleep_time)
```

---

## 5. Error Handling / 错误处理

### 5.1 Error Classification

| Error Type | Action | Retry |
|------------|--------|-------|
| `timeout` | Mark offline, retry later | Yes |
| `connection` | Mark offline, alert if persistent | Yes |
| `dns` | Log error, check config | No |
| `parse` | Log warning, skip data point | No |
| `auth` | Reject request, log | No |

### 5.2 Circuit Breaker Pattern

For external API calls (CoinGecko, etc.):

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failures = 0
        self.last_failure = None
        self.state = 'closed'  # closed, open, half-open
    
    def call(self, fn):
        if self.state == 'open':
            if time.time() - self.last_failure > self.recovery_timeout:
                self.state = 'half-open'
            else:
                raise CircuitOpenError()
        
        try:
            result = fn()
            if self.state == 'half-open':
                self.state = 'closed'
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.failure_threshold:
                self.state = 'open'
            raise
```

---

## 6. Metrics & Observability / 指标与可观测性

### 6.1 Current Metrics (Database-based)

| Table/Field | Metric Type | Description |
|-------------|-------------|-------------|
| `CollectorUploadLog.processing_time_ms` | Histogram | Upload processing time |
| `MinerTelemetryLive.updated_at` | Gauge | Last update timestamp |
| `MinerCommand.status` | Counter | Command outcomes |
| `MinerTelemetryLive.online` | Gauge | Online miner count |

### 6.2 Recommended Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Collection metrics
miner_poll_total = Counter(
    'miner_poll_total',
    'Total miner polling attempts',
    ['site_id', 'status']  # status: success, timeout, error
)

miner_poll_latency = Histogram(
    'miner_poll_latency_seconds',
    'Miner polling latency',
    ['site_id'],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

# Upload metrics
collector_upload_total = Counter(
    'collector_upload_total',
    'Total collector uploads',
    ['site_id', 'status']  # status: success, error, rate_limited
)

collector_upload_size = Histogram(
    'collector_upload_size_bytes',
    'Upload payload size',
    buckets=[1000, 10000, 100000, 1000000, 10000000]
)

# Rate limiting
rate_limit_hits = Counter(
    'rate_limit_hits_total',
    'Rate limit exceeded events',
    ['key_prefix']
)

# Health
miners_online = Gauge(
    'miners_online_total',
    'Currently online miners',
    ['site_id']
)
```

### 6.3 Logging Standards

```python
import logging

# Structured logging format
logging.basicConfig(
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    level=logging.INFO
)

# Key log points
logger.info("Telemetry upload", extra={
    'site_id': site_id,
    'miner_count': count,
    'processing_ms': latency
})

logger.warning("Miner offline", extra={
    'miner_id': miner_id,
    'last_seen': last_seen,
    'consecutive_failures': failures
})

logger.error("Collection failed", extra={
    'site_id': site_id,
    'error_type': error_type,
    'error_message': str(e)
})
```

---

## 7. Resilience Patterns / 弹性模式

### 7.1 Graceful Degradation

| Component | Degraded Mode |
|-----------|--------------|
| Redis unavailable | Fall back to in-memory cache |
| External API down | Use cached/stale data |
| Single miner timeout | Continue with other miners |
| Database slow | Reduce batch sizes |

### 7.2 Bulkhead Pattern

Isolate different workloads to prevent cascade failures:

```python
# Separate thread pools for different tasks
collection_pool = ThreadPoolExecutor(max_workers=20, thread_name_prefix='collect')
command_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix='command')
api_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix='api')
```

### 7.3 Timeout Hierarchy

```
Global Request Timeout: 300s (Gunicorn)
├── Database Query: 30s
├── Redis Operation: 5s
├── CGMiner Poll: 5s
│   ├── Connect: 2s
│   ├── Send: 1s
│   └── Receive: 2s
└── External API: 10s
```

---

## 8. Performance Optimizations / 性能优化

### 8.1 Database Query Optimization

**N+1 Query Fix** (Already implemented):

```python
# Before (N+1 queries)
for site in sites:
    miners = Miner.query.filter_by(site_id=site.id).count()

# After (Single query with aggregation)
stats = db.session.query(
    MinerTelemetryLive.site_id,
    func.count(MinerTelemetryLive.id).label('total'),
    func.sum(db.case((MinerTelemetryLive.online == True, 1), else_=0)).label('online')
).group_by(MinerTelemetryLive.site_id).all()
```

### 8.2 Batch Operations

```python
# Batch insert/update
if updates:
    db.session.bulk_update_mappings(MinerTelemetryLive, updates)
if inserts:
    db.session.bulk_insert_mappings(MinerTelemetryLive, inserts)
db.session.commit()  # Single commit
```

### 8.3 Compression

- Request: `Content-Encoding: gzip` for telemetry uploads
- Response: Flask-Compress for large responses

---

## 9. Capacity Planning / 容量规划

### 9.1 Current Limits

| Resource | Limit | Basis |
|----------|-------|-------|
| Miners per upload | 5,000 | Memory/processing time |
| Upload size | 10 MB | Memory/network |
| Rate limit | 60/min | Database write capacity |
| Concurrent collections | 1 | APScheduler config |
| Thread pool | 20 workers | Network I/O bound |

### 9.2 Scaling Considerations

| Scale Factor | Bottleneck | Mitigation |
|--------------|------------|------------|
| 10K miners | Database writes | Batch writes, partitioning |
| 50K miners | Collection time | More edge collectors |
| 100K miners | Database size | Time-series DB (TimescaleDB) |

---

## 10. Operational Runbook / 运维手册

### 10.1 Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /health` | Basic liveness | 200 OK |
| `GET /api/collector/stats` | Collection health | JSON with site stats |
| `GET /api/collector/status` | Collector status | Auth required |

### 10.2 Common Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| High `processing_time_ms` | Database slow | Check DB connections |
| All miners offline | Network issue | Check edge collector |
| Rate limit exceeded | Client bug | Review client code |
| Stale telemetry | Scheduler stopped | Restart application |

### 10.3 Maintenance Tasks

```bash
# Clean old telemetry history (recommended: cron job)
DELETE FROM miner_telemetry_history 
WHERE timestamp < NOW() - INTERVAL '30 days';

# Clean old upload logs
DELETE FROM collector_upload_logs 
WHERE upload_time < NOW() - INTERVAL '7 days';

# Clean expired commands
DELETE FROM miner_commands 
WHERE status IN ('expired', 'cancelled') 
AND created_at < NOW() - INTERVAL '30 days';
```

---

## 11. Summary / 总结

| Pattern | Status | Notes |
|---------|--------|-------|
| Connection Pooling | ✅ DB, ⚠️ No CGMiner pool | CGMiner doesn't support |
| Retry with Backoff | ✅ Implemented | Exponential + jitter |
| Cache Stampede | ⚠️ Partial | Recommend full SWR |
| Rate Limiting | ✅ Implemented | In-memory, upgrade to Redis |
| Circuit Breaker | ⚠️ Not implemented | Recommend for external APIs |
| Metrics Export | ⚠️ Database-based | Recommend Prometheus |
| Graceful Degradation | ✅ Partial | Cache fallbacks exist |

**Key Recommendations**:
1. Add Prometheus metrics export
2. Implement circuit breaker for external APIs
3. Upgrade to Redis-backed rate limiter for multi-worker
4. Add automated telemetry history cleanup
