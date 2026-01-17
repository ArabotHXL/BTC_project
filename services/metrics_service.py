"""
Prometheus Metrics Service for Control Plane

This module provides metrics collection and export for the control plane,
including command dispatch tracking, rule evaluations, telemetry lag monitoring,
and lease management.
"""

import logging
from flask import Blueprint, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    REGISTRY,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# Metric Definitions
# ==============================================================================

# Commands Dispatched - total commands sent to edge collectors
commands_dispatched_total = Counter(
    'commands_dispatched_total',
    'Total number of commands dispatched to edge collectors',
    labelnames=['site_id', 'command_type']
)

# Commands Acknowledged - commands that were acknowledged with success/failure status
commands_acked_total = Counter(
    'commands_acked_total',
    'Total number of commands acknowledged by edge collectors',
    labelnames=['site_id', 'command_type', 'status']  # status: succeeded/failed
)

# Commands Failed - commands that failed with specific error codes
commands_failed_total = Counter(
    'commands_failed_total',
    'Total number of commands that failed with specific error codes',
    labelnames=['site_id', 'command_type', 'error_code']
)

# Rule Evaluations - automation/control rules that were evaluated
rule_evals_total = Counter(
    'rule_evals_total',
    'Total number of rule evaluations',
    labelnames=['rule_id', 'triggered']  # triggered: true/false
)

# Telemetry Ingest Lag - delay in seconds between event generation and ingestion
telemetry_ingest_lag_seconds = Gauge(
    'telemetry_ingest_lag_seconds',
    'Telemetry ingestion lag in seconds',
    labelnames=['site_id']
)

# Command Dispatch Duration - time taken to dispatch commands (histogram for percentiles)
command_dispatch_duration_seconds = Histogram(
    'command_dispatch_duration_seconds',
    'Time taken to dispatch commands in seconds',
    labelnames=['command_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

# Active Leases - current count of active equipment leases per site
active_leases = Gauge(
    'active_leases',
    'Number of active equipment leases',
    labelnames=['site_id']
)

# ==============================================================================
# Helper Functions
# ==============================================================================


def inc_commands_dispatched(site_id, command_type):
    """
    Increment the total commands dispatched counter.
    
    Args:
        site_id: Identifier of the hosting site
        command_type: Type of command (e.g., 'REBOOT', 'POWER_MODE', etc.)
    """
    try:
        commands_dispatched_total.labels(site_id=str(site_id), command_type=str(command_type)).inc()
        logger.debug(f"Incremented commands_dispatched for site {site_id}, type {command_type}")
    except Exception as e:
        logger.error(f"Error incrementing commands_dispatched: {e}")


def inc_commands_acked(site_id, command_type, status):
    """
    Increment the commands acknowledged counter.
    
    Args:
        site_id: Identifier of the hosting site
        command_type: Type of command
        status: Command acknowledgment status ('succeeded' or 'failed')
    """
    try:
        valid_statuses = ['succeeded', 'failed']
        if status not in valid_statuses:
            logger.warning(f"Invalid status '{status}'. Using 'failed' instead.")
            status = 'failed'
        
        commands_acked_total.labels(
            site_id=str(site_id),
            command_type=str(command_type),
            status=status
        ).inc()
        logger.debug(f"Incremented commands_acked for site {site_id}, type {command_type}, status {status}")
    except Exception as e:
        logger.error(f"Error incrementing commands_acked: {e}")


def inc_commands_failed(site_id, command_type, error_code):
    """
    Increment the failed commands counter with specific error code.
    
    Args:
        site_id: Identifier of the hosting site
        command_type: Type of command that failed
        error_code: Error code indicating the failure reason
    """
    try:
        commands_failed_total.labels(
            site_id=str(site_id),
            command_type=str(command_type),
            error_code=str(error_code)
        ).inc()
        logger.debug(f"Incremented commands_failed for site {site_id}, type {command_type}, error {error_code}")
    except Exception as e:
        logger.error(f"Error incrementing commands_failed: {e}")


def inc_rule_evals(rule_id, triggered):
    """
    Increment the rule evaluation counter.
    
    Args:
        rule_id: Identifier of the rule being evaluated
        triggered: Boolean indicating if the rule was triggered (True/False)
    """
    try:
        triggered_str = 'true' if triggered else 'false'
        rule_evals_total.labels(rule_id=str(rule_id), triggered=triggered_str).inc()
        logger.debug(f"Incremented rule_evals for rule {rule_id}, triggered {triggered_str}")
    except Exception as e:
        logger.error(f"Error incrementing rule_evals: {e}")


def set_telemetry_lag(site_id, lag_seconds):
    """
    Set the telemetry ingestion lag gauge.
    
    Args:
        site_id: Identifier of the hosting site
        lag_seconds: Lag time in seconds (float)
    """
    try:
        telemetry_ingest_lag_seconds.labels(site_id=str(site_id)).set(float(lag_seconds))
        logger.debug(f"Set telemetry_ingest_lag for site {site_id} to {lag_seconds}s")
    except Exception as e:
        logger.error(f"Error setting telemetry_ingest_lag: {e}")


def observe_dispatch_duration(command_type, duration_seconds):
    """
    Record a command dispatch duration observation.
    
    Args:
        command_type: Type of command being dispatched
        duration_seconds: Duration of dispatch in seconds (float)
    """
    try:
        command_dispatch_duration_seconds.labels(command_type=str(command_type)).observe(float(duration_seconds))
        logger.debug(f"Observed dispatch duration for {command_type}: {duration_seconds}s")
    except Exception as e:
        logger.error(f"Error observing dispatch_duration: {e}")


def set_active_leases(site_id, count):
    """
    Set the active leases gauge for a site.
    
    Args:
        site_id: Identifier of the hosting site
        count: Current count of active leases (integer)
    """
    try:
        active_leases.labels(site_id=str(site_id)).set(int(count))
        logger.debug(f"Set active_leases for site {site_id} to {count}")
    except Exception as e:
        logger.error(f"Error setting active_leases: {e}")


# ==============================================================================
# Flask Blueprint for Metrics Export
# ==============================================================================

metrics_bp = Blueprint('metrics', __name__, url_prefix='')


@metrics_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Expose Prometheus metrics endpoint.
    
    Returns:
        Response: Metrics in Prometheus text format
    """
    try:
        metrics_output = generate_latest(REGISTRY)
        return Response(metrics_output, mimetype='text/plain; charset=utf-8')
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response('Error generating metrics', status=500, mimetype='text/plain')


# ==============================================================================
# Initialization
# ==============================================================================

def init_metrics(app):
    """
    Initialize the metrics blueprint with the Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(metrics_bp)
    logger.info("Metrics service initialized and blueprint registered")
