# Deployment Guide

## Overview
This document outlines the deployment optimizations implemented to resolve deployment failures and ensure reliable deployments.

## Deployment Fixes Applied

### 1. Fast Health Check Endpoints
- **`/ready`** - Lightweight readiness probe for deployment health checks
- **`/alive`** - Minimal liveness probe (returns "OK")
- **`/status`** - Basic status endpoint for load balancer health checks

### 2. Application Startup Optimizations
- **Fast Startup Mode**: Database health checks are skipped by default (`SKIP_DATABASE_HEALTH_CHECK=1`)
- **Deferred Background Services**: Non-critical services start 5 seconds after core app initialization
- **Readiness Signals**: Core application creates readiness files at `/tmp/core_app_ready` and `/tmp/app_ready`

### 3. Gunicorn Configuration Optimizations
- **Worker Count**: Reduced to `cpu_count + 1` (max 3) for faster startup
- **Timeout Settings**: Increased to 180s for deployment compatibility
- **Worker Timeout**: Set to 60s for faster startup detection
- **Graceful Timeout**: Optimized to 45s for deployments

### 4. Deployment Health Monitoring
- **deployment_health.py**: Comprehensive health check script
- **Multiple Check Methods**: HTTP endpoints + file-based readiness signals
- **Wait Mode**: Script can wait for readiness with timeout

## Environment Variables

### Production Deployment
```bash
FAST_STARTUP=1                    # Enable fast startup mode
SKIP_DATABASE_HEALTH_CHECK=1      # Skip DB checks for faster startup
ENABLE_BACKGROUND_SERVICES=1      # Enable background services (delayed)
```

### Development
```bash
FAST_STARTUP=0                    # Full initialization
SKIP_DATABASE_HEALTH_CHECK=0      # Perform DB health checks
ENABLE_BACKGROUND_SERVICES=1      # Enable background services
```

## Health Check Endpoints

### `/ready` - Deployment Readiness
- **Purpose**: Quick deployment health check
- **Response**: JSON with status, app state, timestamp
- **Timeout**: Very fast response for deployment systems

### `/alive` - Liveness Probe
- **Purpose**: Minimal liveness check
- **Response**: Simple "OK" text
- **Use Case**: Load balancer health checks

### `/health` - Comprehensive Health
- **Purpose**: Full application health including database
- **Response**: Detailed JSON with all service states
- **Use Case**: Monitoring and debugging

## Deployment Flow

1. **Core Application Startup** (< 5 seconds)
   - Environment validation
   - Database connection (if enabled)
   - Flask app initialization
   - Readiness signal creation

2. **Health Check Response** (immediate)
   - `/ready` and `/alive` endpoints become available
   - Deployment system receives positive health checks

3. **Background Service Initialization** (after 5 seconds)
   - Analytics engine startup
   - Data collection services
   - Scheduled tasks

## Testing Deployment Health

### Basic Health Check
```bash
curl http://localhost:5000/alive
# Expected: "OK"
```

### Readiness Check
```bash
curl http://localhost:5000/ready
# Expected: {"status": "ready", "app": "running", "timestamp": "..."}
```

### Using Health Check Script
```bash
python3 deployment_health.py
# Expected: JSON response with deployment status

python3 deployment_health.py --wait
# Waits for readiness with timeout
```

### File-based Readiness
```bash
cat /tmp/app_ready
# Expected: "ready"

cat /tmp/core_app_ready  
# Expected: "ready"
```

## Troubleshooting

### Deployment Timeout
- Check `/ready` endpoint response time
- Verify readiness files exist in `/tmp/`
- Check Gunicorn worker logs for startup issues

### Health Check Failures
- Test individual endpoints (`/alive`, `/ready`, `/health`)
- Check application logs for startup errors
- Verify environment variables are set correctly

### Background Service Issues
- Background services are deferred and should not affect deployment
- Check logs for analytics engine startup after 5-second delay
- Services can be disabled with `ENABLE_BACKGROUND_SERVICES=0`

## Monitoring

The application provides comprehensive logging for deployment monitoring:
- Core app readiness signals
- Background service startup status
- Health check endpoint access logs
- Worker process management logs