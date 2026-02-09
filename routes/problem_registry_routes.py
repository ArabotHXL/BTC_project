"""
HashInsight Enterprise - Problem Registry Routes
Problem event tracking and health summary API endpoints

Provides REST API for querying problem events, health summaries, and managing event suppression.
All endpoints require authentication via session.
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from app import db
from sqlalchemy import text
from services.event_engine import EventEngine

logger = logging.getLogger(__name__)

problem_registry_bp = Blueprint('problem_registry', __name__)


def check_auth():
    """Helper function to check user authentication."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id



# =========================================================================
# Endpoint 1: GET /hosting/api/sites/<int:site_id>/health_summary
# =========================================================================

@problem_registry_bp.route('/hosting/api/sites/<int:site_id>/health_summary', methods=['GET'])
def health_summary(site_id):
    """
    Returns a health summary for a site.

    Query parameters: None

    Returns:
        {
            "site_id": 1,
            "total_miners": 800,
            "healthy_miners": 750,
            "problem_miners": 50,
            "by_severity": {"P0": 2, "P1": 8, "P2": 30, "P3": 10},
            "by_issue": {"overheat_crit": 2, "hashrate_degradation": 15, ...},
            "top_risks": [
                {
                    "miner_id": "S19PRO-12345",
                    "issue_code": "overheat_crit",
                    "severity": "P0",
                    "p_fail_24h": 0.92,
                    "start_ts": "2026-02-08T10:00:00"
                }
            ],
            "last_scan_ts": "2026-02-08T12:00:00"
        }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Get total miners for this site from miner_telemetry_live
        total_miners_result = db.session.execute(
            text("""
                SELECT COUNT(DISTINCT miner_id) as total
                FROM miner_telemetry_live
                WHERE site_id = :site_id
            """),
            {'site_id': site_id}
        )
        total_miners_row = total_miners_result.fetchone()
        total_miners = total_miners_row[0] if total_miners_row else 0

        # Count miners with active problems
        problem_miners_result = db.session.execute(
            text("""
                SELECT COUNT(DISTINCT miner_id) as total
                FROM problem_events
                WHERE site_id = :site_id
                  AND status IN ('open', 'ack', 'in_progress')
            """),
            {'site_id': site_id}
        )
        problem_miners_row = problem_miners_result.fetchone()
        problem_miners = problem_miners_row[0] if problem_miners_row else 0

        healthy_miners = total_miners - problem_miners

        # Count by severity
        severity_result = db.session.execute(
            text("""
                SELECT severity, COUNT(*) as count
                FROM problem_events
                WHERE site_id = :site_id
                  AND status IN ('open', 'ack', 'in_progress')
                GROUP BY severity
            """),
            {'site_id': site_id}
        )
        by_severity = {}
        for row in severity_result:
            by_severity[row[0]] = row[1]

        # Count by issue_code
        issue_result = db.session.execute(
            text("""
                SELECT issue_code, COUNT(*) as count
                FROM problem_events
                WHERE site_id = :site_id
                  AND status IN ('open', 'ack', 'in_progress')
                GROUP BY issue_code
            """),
            {'site_id': site_id}
        )
        by_issue = {}
        for row in issue_result:
            by_issue[row[0]] = row[1]

        # Get top 10 risks sorted by severity (P0 first) then by p_fail_24h
        risks_result = db.session.execute(
            text("""
                SELECT miner_id, issue_code, severity,
                       COALESCE((ml_json->>'p_fail_24h')::float, 0) as p_fail_24h,
                       start_ts
                FROM problem_events
                WHERE site_id = :site_id
                  AND status IN ('open', 'ack', 'in_progress')
                ORDER BY
                    CASE severity
                        WHEN 'P0' THEN 0
                        WHEN 'P1' THEN 1
                        WHEN 'P2' THEN 2
                        WHEN 'P3' THEN 3
                    END ASC,
                    p_fail_24h DESC,
                    start_ts DESC
                LIMIT 10
            """),
            {'site_id': site_id}
        )

        top_risks = []
        for row in risks_result:
            top_risks.append({
                'miner_id': row[0],
                'issue_code': row[1],
                'severity': row[2],
                'p_fail_24h': float(row[3]) if row[3] else 0.0,
                'start_ts': row[4].isoformat() if row[4] else None
            })

        # Get last scan timestamp (most recent last_seen_ts from active events)
        last_scan_result = db.session.execute(
            text("""
                SELECT MAX(last_seen_ts) as last_scan_ts
                FROM problem_events
                WHERE site_id = :site_id
                  AND status IN ('open', 'ack', 'in_progress')
            """),
            {'site_id': site_id}
        )
        last_scan_row = last_scan_result.fetchone()
        last_scan_ts = last_scan_row[0] if last_scan_row and last_scan_row[0] else None

        return jsonify({
            'site_id': site_id,
            'total_miners': total_miners,
            'healthy_miners': healthy_miners,
            'problem_miners': problem_miners,
            'by_severity': by_severity,
            'by_issue': by_issue,
            'top_risks': top_risks,
            'last_scan_ts': last_scan_ts.isoformat() if last_scan_ts else None
        }), 200

    except Exception as e:
        logger.error(f"Error in health_summary for site {site_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =========================================================================
# Endpoint 2: GET /hosting/api/sites/<int:site_id>/problems
# =========================================================================

@problem_registry_bp.route('/hosting/api/sites/<int:site_id>/problems', methods=['GET'])
def get_problems(site_id):
    """
    Returns paginated list of problem events with filtering.

    Query parameters:
        severity: Filter by severity (P0, P1, P2, P3)
        issue_code: Filter by issue code
        status: Filter by status (open, ack, in_progress, resolved)
        model: Filter by miner model
        firmware: Filter by firmware version
        page: Page number (default 1)
        per_page: Items per page (default 50, max 500)

    Returns:
        {
            "problems": [...],
            "pagination": {
                "page": 1,
                "per_page": 50,
                "total": 120,
                "pages": 3
            }
        }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Get query parameters
        severity = request.args.get('severity', None)
        issue_code = request.args.get('issue_code', None)
        status = request.args.get('status', None)
        model = request.args.get('model', None)
        firmware = request.args.get('firmware', None)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # Validate pagination parameters
        page = max(1, page)
        per_page = max(1, min(per_page, 500))  # Cap at 500 per page

        # Build WHERE clause
        where_clauses = ["pe.site_id = :site_id"]
        params = {'site_id': site_id}

        if severity:
            where_clauses.append("pe.severity = :severity")
            params['severity'] = severity

        if issue_code:
            where_clauses.append("pe.issue_code = :issue_code")
            params['issue_code'] = issue_code

        if status:
            where_clauses.append("pe.status = :status")
            params['status'] = status

        # Build JOIN for model/firmware filtering
        join_clause = ""
        if model or firmware:
            join_clause = """
                LEFT JOIN miner_telemetry_live mtl ON pe.miner_id = mtl.miner_id
            """
            if model:
                where_clauses.append("mtl.miner_model = :model")
                params['model'] = model

            if firmware:
                where_clauses.append("mtl.firmware_version = :firmware")
                params['firmware'] = firmware

        where_clause_str = " AND ".join(where_clauses)

        # Count total
        count_query = f"""
            SELECT COUNT(*) as total
            FROM problem_events pe
            {join_clause}
            WHERE {where_clause_str}
        """
        count_result = db.session.execute(text(count_query), params)
        total = count_result.fetchone()[0]

        # Calculate pagination
        pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page

        # Fetch data
        data_query = f"""
            SELECT
                pe.id, pe.site_id, pe.miner_id, pe.issue_code, pe.severity,
                pe.status, pe.start_ts, pe.last_seen_ts, pe.recurrence_count,
                pe.evidence_json, pe.peer_metrics_json, pe.ml_json, pe.maintenance_flag
            FROM problem_events pe
            {join_clause}
            WHERE {where_clause_str}
            ORDER BY
                CASE pe.severity
                    WHEN 'P0' THEN 0
                    WHEN 'P1' THEN 1
                    WHEN 'P2' THEN 2
                    WHEN 'P3' THEN 3
                END ASC,
                COALESCE((pe.ml_json->>'p_fail_24h')::float, 0) DESC,
                pe.last_seen_ts DESC
            LIMIT :limit OFFSET :offset
        """
        params['limit'] = per_page
        params['offset'] = offset

        result = db.session.execute(text(data_query), params)
        rows = result.fetchall()

        problems = []
        for row in rows:
            # Parse JSON fields
            evidence_json = None
            peer_metrics_json = None
            ml_json = None

            try:
                evidence_json = json.loads(row[9]) if row[9] else None
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                peer_metrics_json = json.loads(row[10]) if row[10] else None
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                ml_json = json.loads(row[11]) if row[11] else None
            except (json.JSONDecodeError, TypeError):
                pass

            problems.append({
                'id': str(row[0]),
                'site_id': row[1],
                'miner_id': row[2],
                'issue_code': row[3],
                'severity': row[4],
                'status': row[5],
                'start_ts': row[6].isoformat() if row[6] else None,
                'last_seen_ts': row[7].isoformat() if row[7] else None,
                'recurrence_count': row[8],
                'evidence_json': evidence_json,
                'peer_metrics_json': peer_metrics_json,
                'ml_json': ml_json,
                'maintenance_flag': row[12]
            })

        return jsonify({
            'problems': problems,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': pages
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in get_problems for site {site_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =========================================================================
# Endpoint 3: GET /hosting/api/miners/<miner_id>/problems
# =========================================================================

@problem_registry_bp.route('/hosting/api/miners/<miner_id>/problems', methods=['GET'])
def get_miner_problems(miner_id):
    """
    Returns all problems for a specific miner.

    Query parameters:
        status: Filter by status (default 'open' - can be 'open', 'ack', 'in_progress', 'resolved')
        include_resolved: Include resolved events (default false)

    Returns:
        {
            "miner_id": "S19PRO-12345",
            "problems": [...],
            "total": 3
        }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Get query parameters
        include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'

        # Build WHERE clause
        where_clause = "miner_id = :miner_id"
        params = {'miner_id': miner_id}

        if include_resolved:
            where_clause += " AND status IN ('open', 'ack', 'in_progress', 'resolved')"
        else:
            where_clause += " AND status IN ('open', 'ack', 'in_progress')"

        # Fetch all problems for this miner
        query = f"""
            SELECT
                id, site_id, miner_id, issue_code, severity,
                status, start_ts, last_seen_ts, recurrence_count,
                evidence_json, peer_metrics_json, ml_json, maintenance_flag
            FROM problem_events
            WHERE {where_clause}
            ORDER BY
                CASE severity
                    WHEN 'P0' THEN 0
                    WHEN 'P1' THEN 1
                    WHEN 'P2' THEN 2
                    WHEN 'P3' THEN 3
                END ASC,
                last_seen_ts DESC
        """

        result = db.session.execute(text(query), params)
        rows = result.fetchall()

        problems = []
        for row in rows:
            # Parse JSON fields
            evidence_json = None
            peer_metrics_json = None
            ml_json = None

            try:
                evidence_json = json.loads(row[9]) if row[9] else None
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                peer_metrics_json = json.loads(row[10]) if row[10] else None
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                ml_json = json.loads(row[11]) if row[11] else None
            except (json.JSONDecodeError, TypeError):
                pass

            problems.append({
                'id': str(row[0]),
                'site_id': row[1],
                'miner_id': row[2],
                'issue_code': row[3],
                'severity': row[4],
                'status': row[5],
                'start_ts': row[6].isoformat() if row[6] else None,
                'last_seen_ts': row[7].isoformat() if row[7] else None,
                'recurrence_count': row[8],
                'evidence_json': evidence_json,
                'peer_metrics_json': peer_metrics_json,
                'ml_json': ml_json,
                'maintenance_flag': row[12]
            })

        return jsonify({
            'miner_id': miner_id,
            'problems': problems,
            'total': len(problems)
        }), 200

    except Exception as e:
        logger.error(f"Error in get_miner_problems for miner {miner_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =========================================================================
# Endpoint 4: POST /hosting/api/miners/<miner_id>/suppress
# =========================================================================

@problem_registry_bp.route('/hosting/api/miners/<miner_id>/suppress', methods=['POST'])
def suppress_miner(miner_id):
    """
    Set maintenance suppression for a miner.

    Body: {
        "until": "2026-02-09T12:00:00",  # Optional ISO format datetime
        "maintenance": true,               # Optional, default false
        "reason": "Scheduled maintenance"  # Optional reason
    }

    Returns:
        {
            "success": true,
            "miner_id": "S19PRO-12345",
            "message": "...",
            "until": "2026-02-09T12:00:00",
            "maintenance": true,
            "reason": "..."
        }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json() or {}

        until_str = data.get('until', None)
        maintenance = data.get('maintenance', False)
        reason = data.get('reason', '')

        # Parse until datetime if provided
        until = None
        if until_str:
            try:
                # Handle ISO format with or without Z
                until = datetime.fromisoformat(until_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return jsonify({'error': 'Invalid datetime format for "until". Use ISO format (e.g., 2026-02-09T12:00:00)'}), 400

        # Call EventEngine
        engine = EventEngine()
        result = engine.suppress_miner(miner_id, until=until, maintenance=maintenance)

        if result.get('success'):
            return jsonify({
                'success': True,
                'miner_id': miner_id,
                'message': result.get('message', ''),
                'until': until.isoformat() if until else None,
                'maintenance': maintenance,
                'reason': reason
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('message', 'Failed to suppress miner')
            }), 400

    except Exception as e:
        logger.error(f"Error in suppress_miner for {miner_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =========================================================================
# Endpoint 5: POST /hosting/api/miners/<miner_id>/unsuppress
# =========================================================================

@problem_registry_bp.route('/hosting/api/miners/<miner_id>/unsuppress', methods=['POST'])
def unsuppress_miner(miner_id):
    """
    Remove maintenance suppression for a miner.

    Body: {} (empty)

    Returns:
        {
            "success": true,
            "miner_id": "S19PRO-12345",
            "message": "..."
        }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Call EventEngine
        engine = EventEngine()
        result = engine.unsuppress_miner(miner_id)

        if result.get('success'):
            return jsonify({
                'success': True,
                'miner_id': miner_id,
                'message': result.get('message', '')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('message', 'Failed to unsuppress miner')
            }), 400

    except Exception as e:
        logger.error(f"Error in unsuppress_miner for {miner_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
