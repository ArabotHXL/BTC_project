"""
Gunicorn configuration for production deployment
Handles database connection issues gracefully during startup
"""

import os
import logging
import multiprocessing

# Basic configuration
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
workers = 1  # 🔧 单worker以解决session一致性问题（CSRF修复）
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 180  # Increased timeout for deployment compatibility
keepalive = 2

# Deployment-specific optimizations
worker_timeout = 60  # Worker timeout for faster startup detection

# Logging
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'btc_mining_calculator'

# Worker recycling
max_requests = 500
max_requests_jitter = 100
preload_app = True  # Preload for better memory usage

# Graceful shutdown
graceful_timeout = 45  # Optimized for deployments

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

def when_ready(server):
    """Called when the server is ready to serve requests"""
    server.log.info("BTC Mining Calculator server is ready. Worker pid: %s", os.getpid())
    # Signal deployment readiness
    try:
        with open('/tmp/app_ready', 'w') as f:
            f.write('ready')
        server.log.info("Deployment readiness signal created")
    except Exception as e:
        server.log.warning("Could not create readiness signal: %s", e)

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal"""
    worker.log.info("Worker received SIGINT or SIGQUIT signal")

def pre_fork(server, worker):
    """Called before worker processes are forked"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called after worker processes are forked"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal"""
    worker.log.info("Worker received SIGABRT signal")