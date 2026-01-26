"""
Unified Telemetry API
统一遥测数据 API - 单一数据真相

This API provides a single source of truth for telemetry queries.
All UI components should use these endpoints for consistent data.

Endpoints:
    GET /api/v1/telemetry/live - Current miner status (from live layer)
    GET /api/v1/telemetry/history - Historical data (from history layers)
    GET /api/v1/telemetry/site-summary - Site-level aggregation
"""

import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, g, session

from db import db
from models import UserAccess
from services.telemetry_service import telemetry_service

logger = logging.getLogger(__name__)

telemetry_bp = Blueprint('telemetry_api', __name__)


def require_user_auth(f):
    """Require user authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id or not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        g.user = user
        g.user_id = user.id
        g.user_role = user.role or 'user'
        return f(*args, **kwargs)
    return decorated


@telemetry_bp.route('/api/v1/telemetry/live', methods=['GET'])
@require_user_auth
def get_live_telemetry():
    """Get current miner status from live layer
    
    Query Parameters:
        site_id (int, optional): Filter by site
        miner_id (string, optional): Filter by miner
        online (bool, optional): Filter by online status
        limit (int, optional): Max results (default 1000)
    
    Returns standardized format with metadata.
    """
    site_id = request.args.get('site_id', type=int)
    miner_id = request.args.get('miner_id')
    online_only = request.args.get('online', '').lower() == 'true'
    limit = min(request.args.get('limit', 1000, type=int), 5000)
    
    miners = telemetry_service.get_live(
        site_id=site_id,
        miner_id=miner_id,
        online_only=online_only,
        limit=limit
    )
    
    return jsonify({
        'miners': miners,
        'count': len(miners),
        '_meta': {
            'source': 'miner_telemetry_live',
            'updated_at': datetime.utcnow().isoformat(),
            'unit_definitions': {
                'hashrate': 'TH/s (5-minute average)',
                'temperature': 'Celsius',
                'power': 'Watts',
                'efficiency': 'Joules per TH',
                'reject_rate': 'Ratio (0-1)',
            }
        }
    })


@telemetry_bp.route('/api/v1/telemetry/history', methods=['GET'])
@require_user_auth
def get_history_telemetry():
    """Get historical telemetry data
    
    Query Parameters:
        site_id (int, required): Site ID
        miner_id (string, optional): Filter by miner
        start (datetime, required): Start time (ISO format)
        end (datetime, required): End time (ISO format)
        resolution (string): '5min' | 'hourly' | 'daily' (default: auto)
    
    Returns standardized format with metadata.
    """
    site_id = request.args.get('site_id', type=int)
    miner_id = request.args.get('miner_id')
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    resolution = request.args.get('resolution', 'auto')
    
    if not site_id:
        return jsonify({'error': 'site_id is required'}), 400
    
    if not start_str or not end_str:
        return jsonify({'error': 'start and end are required'}), 400
    
    try:
        start = datetime.fromisoformat(start_str.replace('Z', '+00:00').replace('+00:00', ''))
        end = datetime.fromisoformat(end_str.replace('Z', '+00:00').replace('+00:00', ''))
    except ValueError:
        return jsonify({'error': 'Invalid datetime format. Use ISO format.'}), 400
    
    duration = end - start
    if resolution == 'auto':
        if duration.days > 30:
            resolution = 'daily'
        elif duration.days > 2:
            resolution = 'hourly'
        else:
            resolution = '5min'
    
    result = telemetry_service.get_history(
        site_id=site_id,
        start=start,
        end=end,
        miner_id=miner_id,
        resolution=resolution
    )
    
    return jsonify(result)


@telemetry_bp.route('/api/v1/telemetry/site-summary', methods=['GET'])
@require_user_auth
def get_site_summary():
    """Get site-level summary from live data
    
    Query Parameters:
        site_id (int, required): Site ID
    
    Returns aggregated metrics for the site.
    """
    site_id = request.args.get('site_id', type=int)
    
    if not site_id:
        return jsonify({'error': 'site_id is required'}), 400
    
    result = telemetry_service.get_site_summary(site_id)
    
    return jsonify(result)


@telemetry_bp.route('/api/v1/telemetry/miner/<miner_id>', methods=['GET'])
@require_user_auth
def get_miner_telemetry(miner_id):
    """Get detailed telemetry for a specific miner
    
    Path Parameters:
        miner_id (string): Miner ID
    
    Query Parameters:
        include_history (bool): Include 24h history
    
    Returns current status and optional history.
    """
    include_history = request.args.get('include_history', '').lower() == 'true'
    
    miners = telemetry_service.get_live(miner_id=miner_id)
    
    if not miners:
        return jsonify({'error': 'Miner not found'}), 404
    
    miner = miners[0]
    
    response = {
        'miner': miner,
        '_meta': {
            'source': 'miner_telemetry_live',
            'updated_at': datetime.utcnow().isoformat(),
        }
    }
    
    if include_history:
        end = datetime.utcnow()
        start = end - timedelta(hours=24)
        history = telemetry_service.get_history(
            site_id=miner['site_id'],
            start=start,
            end=end,
            miner_id=miner_id,
            resolution='5min'
        )
        response['history_24h'] = history
    
    return jsonify(response)


def register_telemetry_routes(app):
    """Register the telemetry blueprint with the Flask app"""
    app.register_blueprint(telemetry_bp)
    logger.info("Unified Telemetry API registered")
