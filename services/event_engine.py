"""
Problem Event Lifecycle Manager
Handles dedup, debounce, cooldown, resolve, recurrence, and maintenance suppression

Key Features:
- Deduplication by dedup_key (site_id:miner_id:issue_code)
- Debounce: Events only transition to 'open' after consecutive_fail >= threshold
- Resolution: Auto-resolve when consecutive_ok >= threshold
- Recurrence: Reopen resolved events within cooldown period
- Cooldown: Prevent duplicate events within cooldown window
- Maintenance Suppression: Suppress events based on miner status
- Severity Escalation: Upgrade severity for new detections
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app import db
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class EventEngine:
    """Problem Event Lifecycle Manager"""

    # Configuration with defaults
    DEBOUNCE_THRESHOLD = 2  # consecutive fails before opening event
    RESOLVE_THRESHOLD = 3  # consecutive OKs before resolving event
    COOLDOWN_HOURS = 24  # hours to prevent duplicate events after resolve

    # Severity levels (ordered from low to high)
    SEVERITY_ORDER = ["P3", "P2", "P1", "P0"]

    def __init__(self):
        """Initialize the Event Engine"""
        self.debounce_threshold = self.DEBOUNCE_THRESHOLD
        self.resolve_threshold = self.RESOLVE_THRESHOLD
        self.cooldown_hours = self.COOLDOWN_HOURS

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def process_detection(
        self,
        site_id: int,
        miner_id: str,
        issue_code: str,
        severity: str,
        evidence: Dict[str, Any],
        peer_metrics: Optional[Dict[str, Any]] = None,
        ml_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a problem detection for a miner.

        Handles the full lifecycle with debounce logic:
        - Events start in 'ack' status (acknowledged but not confirmed)
        - Transition to 'open' when consecutive_fail >= debounce_threshold (default 2)
        - Updates evidence/metrics/ML data on each detection
        
        Steps:
        1. Check maintenance suppression
        2. Check cooldown from previous resolution
        3. Find or create event
        4. Apply debounce logic (ack -> open transition)
        5. Apply severity escalation
        6. Check recurrence if previously resolved

        Args:
            site_id: Site ID
            miner_id: Miner ID
            issue_code: Issue code (e.g., 'HIGH_TEMP', 'OFFLINE')
            severity: Severity level (P0, P1, P2, P3)
            evidence: Evidence dict for this detection
            peer_metrics: Optional peer metrics data
            ml_data: Optional ML analysis data

        Returns:
            {
                'action': 'created'|'updated'|'debouncing'|'suppressed'|'escalated'|'reopened',
                'event_id': <uuid>,
                'status': <event_status>,  (ack|open|resolved|suppressed)
                'consecutive_fail': <count>,
                'message': <description>
            }
        """
        try:
            dedup_key = self._make_dedup_key(site_id, miner_id, issue_code)

            # Step 1: Check maintenance suppression
            if self._is_miner_suppressed(miner_id):
                logger.info(f"Event suppressed (maintenance): {dedup_key}")
                return {
                    "action": "suppressed",
                    "event_id": None,
                    "status": "suppressed",
                    "message": f"Miner {miner_id} is under maintenance suppression",
                }

            # Step 2: Check cooldown from previous resolution
            resolved_event = self._get_resolved_event_within_cooldown(dedup_key)
            if resolved_event and not self._should_reopen_recurring(resolved_event):
                logger.info(f"Event blocked by cooldown: {dedup_key}")
                return {
                    "action": "suppressed",
                    "event_id": resolved_event["id"],
                    "status": "resolved",
                    "message": f"Event within cooldown period ({self.cooldown_hours}h)",
                }

            # Step 3: Find existing active event
            active_event = self._get_active_event(dedup_key)

            if active_event:
                # Update existing event
                return self._update_event(
                    active_event,
                    severity,
                    evidence,
                    peer_metrics,
                    ml_data,
                    resolved_event,
                )
            else:
                # Check if this is a recurrence (event existed but was resolved)
                if resolved_event and self._should_reopen_recurring(resolved_event):
                    return self._reopen_recurring_event(
                        resolved_event,
                        severity,
                        evidence,
                        peer_metrics,
                        ml_data,
                    )
                else:
                    # Create new event
                    return self._create_event(
                        site_id, miner_id, issue_code, severity, evidence, peer_metrics, ml_data
                    )

        except Exception as e:
            logger.error(f"Error processing detection for {site_id}:{miner_id}:{issue_code}: {e}")
            return {
                "action": "error",
                "event_id": None,
                "status": None,
                "message": str(e),
            }

    def process_healthy(
        self, site_id: int, miner_id: str, issue_code: str
    ) -> Dict[str, Any]:
        """
        Process a healthy signal for a miner/issue combination.

        Increments consecutive_ok counter. When consecutive_ok >= resolve_threshold,
        resolves the event.

        Args:
            site_id: Site ID
            miner_id: Miner ID
            issue_code: Issue code

        Returns:
            {
                'action': 'resolving'|'resolved'|'no_active_event',
                'event_id': <uuid>,
                'consecutive_ok': <count>,
                'message': <description>
            }
        """
        try:
            dedup_key = self._make_dedup_key(site_id, miner_id, issue_code)

            # Find active event
            active_event = self._get_active_event(dedup_key)
            if not active_event:
                logger.debug(f"No active event found for healthy signal: {dedup_key}")
                return {
                    "action": "no_active_event",
                    "event_id": None,
                    "consecutive_ok": 0,
                    "message": f"No active event for {dedup_key}",
                }

            event_id = active_event["id"]

            # Increment consecutive_ok and reset consecutive_fail
            query = text(
                """
                UPDATE problem_events
                SET consecutive_ok = consecutive_ok + 1,
                    consecutive_fail = 0,
                    last_seen_ts = :now,
                    updated_at = :now
                WHERE id = :event_id
                RETURNING consecutive_ok, status
                """
            )

            result = db.session.execute(query, {"event_id": str(event_id), "now": datetime.utcnow()})
            row = result.fetchone()
            db.session.commit()

            if not row:
                logger.warning(f"Event not found after update: {event_id}")
                return {
                    "action": "no_active_event",
                    "event_id": str(event_id),
                    "consecutive_ok": 0,
                    "message": "Event not found",
                }

            consecutive_ok, current_status = row

            # Check if we should resolve
            if consecutive_ok >= self.resolve_threshold:
                # Resolve the event
                resolve_query = text(
                    """
                    UPDATE problem_events
                    SET status = 'resolved',
                        resolved_ts = :now,
                        updated_at = :now
                    WHERE id = :event_id
                    """
                )
                db.session.execute(resolve_query, {"event_id": str(event_id), "now": datetime.utcnow()})
                db.session.commit()

                logger.info(
                    f"Event resolved: {dedup_key} (consecutive_ok={consecutive_ok})"
                )
                return {
                    "action": "resolved",
                    "event_id": str(event_id),
                    "consecutive_ok": consecutive_ok,
                    "message": f"Event resolved after {consecutive_ok} consecutive healthy signals",
                }
            else:
                logger.info(
                    f"Event resolving (consecutive_ok={consecutive_ok}): {dedup_key}"
                )
                return {
                    "action": "resolving",
                    "event_id": str(event_id),
                    "consecutive_ok": consecutive_ok,
                    "message": f"Incrementing resolution counter ({consecutive_ok}/{self.resolve_threshold})",
                }

        except Exception as e:
            logger.error(f"Error processing healthy signal: {e}")
            return {
                "action": "error",
                "event_id": None,
                "consecutive_ok": 0,
                "message": str(e),
            }

    def bulk_process(
        self, detections: List[Dict[str, Any]], healthy: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Bulk process multiple detections and healthy signals.

        Args:
            detections: List of detection dicts with keys:
                {site_id, miner_id, issue_code, severity, evidence, [peer_metrics], [ml_data]}
            healthy: List of healthy dicts with keys:
                {site_id, miner_id, issue_code}

        Returns:
            Summary dict:
            {
                'created': int,
                'updated': int,
                'escalated': int,
                'reopened': int,
                'resolving': int,
                'resolved': int,
                'debouncing': int,
                'suppressed': int,
                'errors': int,
                'total_processed': int
            }
        """
        summary = {
            "created": 0,
            "updated": 0,
            "escalated": 0,
            "reopened": 0,
            "resolving": 0,
            "resolved": 0,
            "debouncing": 0,
            "suppressed": 0,
            "errors": 0,
            "total_processed": 0,
        }

        logger.info(f"Bulk processing: {len(detections)} detections, {len(healthy)} healthy signals")

        # Process detections
        for detection in detections:
            try:
                result = self.process_detection(
                    site_id=detection["site_id"],
                    miner_id=detection["miner_id"],
                    issue_code=detection["issue_code"],
                    severity=detection["severity"],
                    evidence=detection.get("evidence", {}),
                    peer_metrics=detection.get("peer_metrics"),
                    ml_data=detection.get("ml_data"),
                )

                action = result.get("action", "error")
                if action in summary:
                    summary[action] += 1
                summary["total_processed"] += 1
            except Exception as e:
                logger.error(f"Error processing detection {detection}: {e}")
                summary["errors"] += 1
                summary["total_processed"] += 1

        # Process healthy signals
        for healthy_signal in healthy:
            try:
                result = self.process_healthy(
                    site_id=healthy_signal["site_id"],
                    miner_id=healthy_signal["miner_id"],
                    issue_code=healthy_signal["issue_code"],
                )

                action = result.get("action", "error")
                if action == "resolving":
                    summary["resolving"] += 1
                elif action == "resolved":
                    summary["resolved"] += 1
                elif action == "no_active_event":
                    pass  # Don't count as error
                else:
                    summary["errors"] += 1
                summary["total_processed"] += 1
            except Exception as e:
                logger.error(f"Error processing healthy signal {healthy_signal}: {e}")
                summary["errors"] += 1
                summary["total_processed"] += 1

        logger.info(f"Bulk processing complete: {summary}")
        return summary

    def suppress_miner(
        self, miner_id: str, until: Optional[datetime] = None, maintenance: bool = False
    ) -> Dict[str, Any]:
        """
        Set maintenance suppression for a miner.

        Args:
            miner_id: Miner ID
            until: Optional datetime until which to suppress. If None and maintenance=True,
                   suppresses indefinitely.
            maintenance: Whether to set maintenance_flag

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            if until is None and not maintenance:
                until = datetime.utcnow() + timedelta(hours=24)

            # Update all events for this miner
            query = text(
                """
                UPDATE problem_events
                SET suppress_until = :until,
                    maintenance_flag = :maintenance,
                    updated_at = :now
                WHERE miner_id = :miner_id
                """
            )

            db.session.execute(
                query,
                {
                    "miner_id": miner_id,
                    "until": until,
                    "maintenance": maintenance,
                    "now": datetime.utcnow(),
                },
            )
            db.session.commit()

            logger.info(f"Miner {miner_id} suppressed: until={until}, maintenance={maintenance}")
            return {
                "success": True,
                "message": f"Miner {miner_id} suppressed successfully",
            }
        except Exception as e:
            logger.error(f"Error suppressing miner {miner_id}: {e}")
            return {
                "success": False,
                "message": str(e),
            }

    def unsuppress_miner(self, miner_id: str) -> Dict[str, Any]:
        """
        Remove maintenance suppression for a miner.

        Args:
            miner_id: Miner ID

        Returns:
            {'success': bool, 'message': str}
        """
        try:
            query = text(
                """
                UPDATE problem_events
                SET suppress_until = NULL,
                    maintenance_flag = FALSE,
                    updated_at = :now
                WHERE miner_id = :miner_id
                """
            )

            db.session.execute(query, {"miner_id": miner_id, "now": datetime.utcnow()})
            db.session.commit()

            logger.info(f"Miner {miner_id} unsuppressed")
            return {
                "success": True,
                "message": f"Miner {miner_id} unsuppressed successfully",
            }
        except Exception as e:
            logger.error(f"Error unsuppressing miner {miner_id}: {e}")
            return {
                "success": False,
                "message": str(e),
            }

    def get_active_events(
        self, site_id: Optional[int] = None, miner_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query active events with optional filters.

        Args:
            site_id: Optional site ID filter
            miner_id: Optional miner ID filter

        Returns:
            List of event dicts
        """
        try:
            query = """
                SELECT id, site_id, miner_id, issue_code, severity, status,
                       start_ts, last_seen_ts, resolved_ts, recurrence_count,
                       consecutive_ok, consecutive_fail, dedup_key,
                       suppress_until, maintenance_flag,
                       created_at, updated_at
                FROM problem_events
                WHERE status IN ('open', 'ack', 'in_progress')
            """
            params = {}

            if site_id is not None:
                query += " AND site_id = :site_id"
                params["site_id"] = site_id

            if miner_id is not None:
                query += " AND miner_id = :miner_id"
                params["miner_id"] = miner_id

            query += " ORDER BY last_seen_ts DESC"

            result = db.session.execute(text(query), params)
            rows = result.fetchall()

            events = []
            for row in rows:
                events.append(
                    {
                        "id": row[0],
                        "site_id": row[1],
                        "miner_id": row[2],
                        "issue_code": row[3],
                        "severity": row[4],
                        "status": row[5],
                        "start_ts": row[6],
                        "last_seen_ts": row[7],
                        "resolved_ts": row[8],
                        "recurrence_count": row[9],
                        "consecutive_ok": row[10],
                        "consecutive_fail": row[11],
                        "dedup_key": row[12],
                        "suppress_until": row[13],
                        "maintenance_flag": row[14],
                        "created_at": row[15],
                        "updated_at": row[16],
                    }
                )

            logger.debug(f"Retrieved {len(events)} active events")
            return events

        except Exception as e:
            logger.error(f"Error querying active events: {e}")
            return []

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _make_dedup_key(self, site_id: int, miner_id: str, issue_code: str) -> str:
        """Generate dedup key"""
        return f"{site_id}:{miner_id}:{issue_code}"

    def _is_miner_suppressed(self, miner_id: str) -> bool:
        """Check if miner is under maintenance suppression"""
        try:
            query = text(
                """
                SELECT COUNT(*) as cnt
                FROM problem_events
                WHERE miner_id = :miner_id
                AND (
                    maintenance_flag = TRUE
                    OR (suppress_until IS NOT NULL AND suppress_until > :now)
                )
                LIMIT 1
                """
            )

            result = db.session.execute(query, {"miner_id": miner_id, "now": datetime.utcnow()})
            row = result.fetchone()
            return row[0] > 0 if row else False

        except Exception as e:
            logger.error(f"Error checking miner suppression: {e}")
            return False

    def _get_active_event(self, dedup_key: str) -> Optional[Dict[str, Any]]:
        """Get active (open/ack/in_progress) event for dedup_key"""
        try:
            query = text(
                """
                SELECT id, site_id, miner_id, issue_code, severity, status,
                       start_ts, last_seen_ts, resolved_ts, recurrence_count,
                       consecutive_ok, consecutive_fail,
                       evidence_json, actions_json, peer_metrics_json, ml_json,
                       suppress_until, maintenance_flag
                FROM problem_events
                WHERE dedup_key = :dedup_key
                AND status IN ('open', 'ack', 'in_progress')
                LIMIT 1
                """
            )

            result = db.session.execute(query, {"dedup_key": dedup_key})
            row = result.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "site_id": row[1],
                "miner_id": row[2],
                "issue_code": row[3],
                "severity": row[4],
                "status": row[5],
                "start_ts": row[6],
                "last_seen_ts": row[7],
                "resolved_ts": row[8],
                "recurrence_count": row[9],
                "consecutive_ok": row[10],
                "consecutive_fail": row[11],
                "evidence_json": row[12],
                "actions_json": row[13],
                "peer_metrics_json": row[14],
                "ml_json": row[15],
                "suppress_until": row[16],
                "maintenance_flag": row[17],
            }

        except Exception as e:
            logger.error(f"Error getting active event: {e}")
            return None

    def _get_resolved_event_within_cooldown(self, dedup_key: str) -> Optional[Dict[str, Any]]:
        """Get resolved event within cooldown period"""
        try:
            query = text(
                """
                SELECT id, site_id, miner_id, issue_code, severity, status,
                       start_ts, last_seen_ts, resolved_ts, recurrence_count,
                       consecutive_ok, consecutive_fail
                FROM problem_events
                WHERE dedup_key = :dedup_key
                AND status = 'resolved'
                AND resolved_ts IS NOT NULL
                AND resolved_ts > :cooldown_start
                ORDER BY resolved_ts DESC
                LIMIT 1
                """
            )

            cooldown_start = datetime.utcnow() - timedelta(hours=self.cooldown_hours)
            result = db.session.execute(
                query, {"dedup_key": dedup_key, "cooldown_start": cooldown_start}
            )
            row = result.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "site_id": row[1],
                "miner_id": row[2],
                "issue_code": row[3],
                "severity": row[4],
                "status": row[5],
                "start_ts": row[6],
                "last_seen_ts": row[7],
                "resolved_ts": row[8],
                "recurrence_count": row[9],
                "consecutive_ok": row[10],
                "consecutive_fail": row[11],
            }

        except Exception as e:
            logger.error(f"Error getting resolved event: {e}")
            return None

    def _should_reopen_recurring(self, resolved_event: Dict[str, Any]) -> bool:
        """Check if a resolved event should be reopened as recurrence"""
        try:
            if not resolved_event.get("resolved_ts"):
                return False

            time_since_resolved = datetime.utcnow() - resolved_event["resolved_ts"]
            cooldown_duration = timedelta(hours=self.cooldown_hours)

            return time_since_resolved < cooldown_duration

        except Exception as e:
            logger.error(f"Error checking recurrence: {e}")
            return False

    def _is_severity_higher(self, new_severity: str, existing_severity: str) -> bool:
        """Check if new severity is higher than existing"""
        try:
            new_idx = self.SEVERITY_ORDER.index(new_severity) if new_severity in self.SEVERITY_ORDER else -1
            existing_idx = (
                self.SEVERITY_ORDER.index(existing_severity)
                if existing_severity in self.SEVERITY_ORDER
                else -1
            )
            return new_idx > existing_idx
        except Exception as e:
            logger.error(f"Error comparing severities: {e}")
            return False

    def _append_evidence(self, existing_evidence: Optional[str], new_evidence: Dict[str, Any]) -> str:
        """Append new evidence to existing evidence array"""
        try:
            if not existing_evidence:
                evidence_list = []
            else:
                try:
                    evidence_list = json.loads(existing_evidence) if isinstance(existing_evidence, str) else existing_evidence or []
                except:
                    evidence_list = []

            if not isinstance(evidence_list, list):
                evidence_list = [evidence_list]

            # Add timestamp to evidence if not present
            if isinstance(new_evidence, dict) and "timestamp" not in new_evidence:
                new_evidence["timestamp"] = datetime.utcnow().isoformat()

            evidence_list.append(new_evidence)

            # Keep only last 100 entries to prevent unbounded growth
            if len(evidence_list) > 100:
                evidence_list = evidence_list[-100:]

            return json.dumps(evidence_list)

        except Exception as e:
            logger.error(f"Error appending evidence: {e}")
            return json.dumps([new_evidence])

    def _create_event(
        self,
        site_id: int,
        miner_id: str,
        issue_code: str,
        severity: str,
        evidence: Dict[str, Any],
        peer_metrics: Optional[Dict[str, Any]],
        ml_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create a new event"""
        try:
            event_id = str(uuid.uuid4())
            dedup_key = self._make_dedup_key(site_id, miner_id, issue_code)
            now = datetime.utcnow()

            # Events start with consecutive_fail = 1, status depends on debounce
            consecutive_fail = 1
            # Use 'ack' status until debounce threshold is reached
            status = "open" if consecutive_fail >= self.debounce_threshold else "ack"

            # Prepare JSON fields
            evidence_json = self._append_evidence(None, evidence)
            peer_metrics_json = json.dumps(peer_metrics) if peer_metrics else None
            ml_json = json.dumps(ml_data) if ml_data else None

            query = text(
                """
                INSERT INTO problem_events (
                    id, site_id, miner_id, issue_code, severity, status,
                    start_ts, last_seen_ts, resolved_ts, recurrence_count,
                    consecutive_ok, consecutive_fail, dedup_key,
                    evidence_json, actions_json, peer_metrics_json, ml_json,
                    suppress_until, maintenance_flag, created_at, updated_at
                ) VALUES (
                    :id, :site_id, :miner_id, :issue_code, :severity, :status,
                    :now, :now, NULL, 0,
                    0, :consecutive_fail, :dedup_key,
                    :evidence_json, NULL, :peer_metrics_json, :ml_json,
                    NULL, FALSE, :now, :now
                )
                """
            )

            db.session.execute(
                query,
                {
                    "id": event_id,
                    "site_id": site_id,
                    "miner_id": miner_id,
                    "issue_code": issue_code,
                    "severity": severity,
                    "status": status,
                    "now": now,
                    "consecutive_fail": consecutive_fail,
                    "dedup_key": dedup_key,
                    "evidence_json": evidence_json,
                    "peer_metrics_json": peer_metrics_json,
                    "ml_json": ml_json,
                },
            )
            db.session.commit()

            logger.info(
                f"Event created: {dedup_key} (status={status}, consecutive_fail={consecutive_fail})"
            )

            # When status is 'ack', it means we're debouncing (not yet 'open')
            action = "created" if status == "open" else "debouncing"
            return {
                "action": action,
                "event_id": event_id,
                "status": status,
                "consecutive_fail": consecutive_fail,
                "message": f"Event {action} (consecutive_fail={consecutive_fail}/{self.debounce_threshold})",
            }

        except IntegrityError as e:
            db.session.rollback()
            # Race condition: another process created the event
            logger.warning(f"Race condition on event creation (dedup_key={dedup_key}): {e}")
            # Retry by fetching and updating
            active_event = self._get_active_event(dedup_key)
            if active_event:
                return self._update_event(
                    active_event, severity, evidence, peer_metrics, ml_data, None
                )
            else:
                # Should not happen, but handle gracefully
                return {
                    "action": "error",
                    "event_id": None,
                    "status": None,
                    "message": "Race condition on event creation (resolved on retry)",
                }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating event: {e}")
            return {
                "action": "error",
                "event_id": None,
                "status": None,
                "message": str(e),
            }

    def _update_event(
        self,
        event: Dict[str, Any],
        severity: str,
        evidence: Dict[str, Any],
        peer_metrics: Optional[Dict[str, Any]],
        ml_data: Optional[Dict[str, Any]],
        resolved_event: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Update an existing event"""
        try:
            event_id = event["id"]
            consecutive_fail = event.get("consecutive_fail", 0) + 1
            now = datetime.utcnow()

            # Append evidence
            evidence_json = self._append_evidence(event.get("evidence_json"), evidence)

            # Update peer metrics and ML data (ensure they're JSON strings)
            if peer_metrics:
                peer_metrics_json = json.dumps(peer_metrics)
            elif event.get("peer_metrics_json"):
                # Already a JSON string or dict - ensure it's a string
                existing = event.get("peer_metrics_json")
                peer_metrics_json = existing if isinstance(existing, str) else json.dumps(existing)
            else:
                peer_metrics_json = None
                
            if ml_data:
                ml_json = json.dumps(ml_data)
            elif event.get("ml_json"):
                # Already a JSON string or dict - ensure it's a string
                existing = event.get("ml_json")
                ml_json = existing if isinstance(existing, str) else json.dumps(existing)
            else:
                ml_json = None

            # Check for severity escalation
            should_escalate = self._is_severity_higher(severity, event.get("severity", "P3"))

            # Determine new status - transition from 'ack' to 'open' when debounce threshold is reached
            new_status = event.get("status")
            if new_status == "ack" and consecutive_fail >= self.debounce_threshold:
                new_status = "open"

            # Build update query
            update_parts = [
                "consecutive_fail = :consecutive_fail",
                "consecutive_ok = 0",
                "last_seen_ts = :now",
                "updated_at = :now",
                "evidence_json = :evidence_json",
                "peer_metrics_json = :peer_metrics_json",
                "ml_json = :ml_json",
                "status = :status",
            ]

            if should_escalate:
                update_parts.append("severity = :severity")

            query = text(
                f"""
                UPDATE problem_events
                SET {', '.join(update_parts)}
                WHERE id = :event_id
                """
            )

            params = {
                "event_id": str(event_id),
                "consecutive_fail": consecutive_fail,
                "now": now,
                "evidence_json": evidence_json,
                "peer_metrics_json": peer_metrics_json,
                "ml_json": ml_json,
                "status": new_status,
            }

            if should_escalate:
                params["severity"] = severity

            db.session.execute(query, params)
            db.session.commit()

            action = "updated"
            if should_escalate:
                action = "escalated"
            elif new_status == "open" and event.get("status") == "pending_open":
                action = "updated"  # Transitioned from pending to open

            logger.info(
                f"Event {action}: {event.get('dedup_key')} "
                f"(consecutive_fail={consecutive_fail}, status={new_status})"
            )

            return {
                "action": action,
                "event_id": str(event_id),
                "status": new_status,
                "consecutive_fail": consecutive_fail,
                "message": f"Event {action} (consecutive_fail={consecutive_fail})",
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating event: {e}")
            return {
                "action": "error",
                "event_id": str(event.get("id")),
                "status": None,
                "message": str(e),
            }

    def _reopen_recurring_event(
        self,
        resolved_event: Dict[str, Any],
        severity: str,
        evidence: Dict[str, Any],
        peer_metrics: Optional[Dict[str, Any]],
        ml_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Reopen a resolved event as a recurrence"""
        try:
            event_id = resolved_event["id"]
            now = datetime.utcnow()
            recurrence_count = (resolved_event.get("recurrence_count", 0) or 0) + 1

            # Append evidence (fresh, no previous for recurrence)
            evidence_json = self._append_evidence(None, evidence)

            # Prepare JSON fields (ensure they're JSON strings)
            peer_metrics_json = json.dumps(peer_metrics) if peer_metrics else None
            ml_json = json.dumps(ml_data) if ml_data else None

            # Check for severity escalation
            should_escalate = self._is_severity_higher(severity, resolved_event.get("severity", "P3"))

            query = text(
                """
                UPDATE problem_events
                SET status = 'open',
                    recurrence_count = :recurrence_count,
                    consecutive_ok = 0,
                    consecutive_fail = 1,
                    resolved_ts = NULL,
                    evidence_json = :evidence_json,
                    peer_metrics_json = :peer_metrics_json,
                    ml_json = :ml_json,
                    last_seen_ts = :now,
                    updated_at = :now
                """
                + (" , severity = :severity" if should_escalate else "")
                + """
                WHERE id = :event_id
                """
            )

            params = {
                "event_id": str(event_id),
                "recurrence_count": recurrence_count,
                "evidence_json": evidence_json,
                "peer_metrics_json": peer_metrics_json,
                "ml_json": ml_json,
                "now": now,
            }

            if should_escalate:
                params["severity"] = severity

            db.session.execute(query, params)
            db.session.commit()

            logger.info(
                f"Event reopened (recurrence={recurrence_count}): {resolved_event.get('dedup_key')}"
            )

            return {
                "action": "reopened",
                "event_id": str(event_id),
                "status": "open",
                "recurrence_count": recurrence_count,
                "message": f"Event reopened as recurrence #{recurrence_count}",
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error reopening event: {e}")
            return {
                "action": "error",
                "event_id": str(resolved_event.get("id")),
                "status": None,
                "message": str(e),
            }


# =========================================================================
# Module-level instance for convenient import
# =========================================================================
event_engine = EventEngine()
