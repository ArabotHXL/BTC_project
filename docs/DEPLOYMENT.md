# HashInsight Enterprise - Deployment Guide

## Overview

HashInsight Enterprise supports multiple deployment modes:

| Mode | Environment | Status |
|------|-------------|--------|
| Replit | Cloud SaaS | **Primary (Current)** |
| Docker Compose | Private/On-Premise | Placeholder Ready |
| Kubernetes | Enterprise Scale | Future (P1) |

---

## 1. Replit Deployment (Current)

### Quick Start

The application runs as a single process on Replit with deferred background initialization.

```bash
# Start the application
python main.py
```

### Environment Variables (Required)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SESSION_SECRET` | Secure session key (32+ chars) | Yes |
| `REDIS_URL` | Redis connection (optional) | No |

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic health check |
| `/health/deep` | Database connectivity check |
| `/ready` | Readiness probe |
| `/alive` | Liveness probe |

### Fast Startup Mode

For optimal deployment performance:

```env
SKIP_DATABASE_HEALTH_CHECK=1
FAST_STARTUP=1
```

This defers heavy initialization to background threads, allowing the server to bind to port 5000 immediately.

---

## 2. Docker Compose Deployment (Private)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM recommended

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd hashinsight-enterprise

# 2. Configure environment
cp .env.example .env
# Edit .env with production values:
# - Generate secure SESSION_SECRET
# - Set production POSTGRES_PASSWORD

# 3. Start all services
docker-compose up -d

# 4. Check status
docker-compose ps
docker-compose logs -f web
```

### Services Architecture

```
┌─────────────────────────────────────────────────┐
│                   Load Balancer                  │
│                   (nginx/traefik)               │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│                 Web Service                      │
│            (Gunicorn, 4 workers)                │
│                 Port: 5000                      │
└─────────────────────┬───────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
┌─────────────┐ ┌──────────┐ ┌──────────┐
│  Scheduler  │ │  Worker  │ │  Worker  │
│ (APScheduler)│ │  (RQ)    │ │  (RQ)    │
└──────┬──────┘ └────┬─────┘ └────┬─────┘
       │             │            │
       └──────┬──────┴────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌─────────┐      ┌───────────┐
│ Redis   │      │ PostgreSQL│
│ :6379   │      │  :5432    │
└─────────┘      └───────────┘
```

### Production Hardening

#### 1. Secure Secrets

```bash
# Generate secure session secret
python -c "import secrets; print(secrets.token_hex(32))"

# Never use default passwords in production
POSTGRES_PASSWORD=<strong-random-password>
SESSION_SECRET=<generated-secret>
```

#### 2. Resource Limits

Add to docker-compose.yml:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

#### 3. Backup Strategy

```bash
# Database backup
docker-compose exec postgres pg_dump -U hashinsight hashinsight > backup.sql

# Restore
cat backup.sql | docker-compose exec -T postgres psql -U hashinsight hashinsight
```

---

## 3. Database Migrations

### Using Alembic

```bash
# View current revision
alembic current

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# For existing databases (first-time Alembic adoption)
alembic stamp head
```

### Migration Safety

- Always backup database before migrations
- Test migrations on staging first
- Use `alembic downgrade -1` to rollback if needed

---

## 4. Verification Scripts

### Audit Chain Verification

```bash
python scripts/verify_audit_chain.py --site-id 1 --days 30
# Expected output: PASS or FAIL with details
```

### Tenant Isolation Verification

```bash
python scripts/verify_tenant_isolation.py
# Expected output: All 403 responses = PASS
```

### Telemetry Idempotency Verification

```bash
python scripts/verify_telemetry_idempotency.py
# Expected output: No duplicate rows = PASS
```

---

## 5. Monitoring

### Key Metrics

| Metric | Endpoint | Description |
|--------|----------|-------------|
| Health | `/health` | Application health |
| Metrics | `/metrics` | Prometheus metrics |

### Log Locations

| Service | Location |
|---------|----------|
| Web | stdout / docker logs |
| Scheduler | stdout / docker logs |
| Worker | stdout / docker logs |

---

## 6. Troubleshooting

### Common Issues

#### Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres pg_isready -U hashinsight
```

#### Session Issues

```bash
# Verify SESSION_SECRET is set
echo $SESSION_SECRET

# Check Redis connection
docker-compose exec redis redis-cli ping
```

#### Slow Startup

```bash
# Enable fast startup mode
SKIP_DATABASE_HEALTH_CHECK=1
FAST_STARTUP=1
```

---

## 7. Future Enhancements (P1)

- [ ] Google/Microsoft OIDC integration
- [ ] mTLS/VPN configuration
- [ ] Kubernetes Helm charts
- [ ] Prometheus/Grafana monitoring stack
- [ ] Centralized logging (ELK/Loki)
- [ ] Automated backup to S3/GCS

---

## Support

For deployment issues, check:
1. Application logs: `docker-compose logs -f`
2. Health endpoints: `/health/deep`
3. Database connectivity: `/health`
