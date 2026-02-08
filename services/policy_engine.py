"""
Policy Engine - Budgeted Notification and Ticket Dispatch

Controls which problem events trigger notifications and tickets, preventing alert spam
while ensuring critical issues are always surfaced.

Policy Rules:
- P0: ALWAYS push notification + ALWAYS create ticket immediately
- P1: ALWAYS push notification + auto-create ticket
- P2: Notify if in TopK (worst K miners by p_fail_24h) OR event open > 30 min
       Ticket if p_fail_24h > 0.5 AND event open > 30 min
- P3: Never notify, never create ticket (dashboard only)

Budget per site per 5-minute cycle:
- Max notifications: 20 (P0/P1 always count, P2 fills remaining slots)
- Max tickets: 5 (P0/P1 always count, P2 fills remaining slots)
- TopK for P2: K = max(3, floor(site_miner_count * 0.05))
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Budgeted notification and ticket dispatch engine"""

    MAX_NOTIFICATIONS_PER_CYCLE = 20
    MAX_TICKETS_PER_CYCLE = 5
    P2_DURATION_GATE_MINUTES = 30
    P2_PFAIL_TICKET_THRESHOLD = 0.5

    SEVERITY_PRIORITY = {
        "P0": 1,
        "P1": 2,
        "P2": 3,
        "P3": 4,
    }

    def __init__(self):
        """Initialize the Policy Engine"""
        pass

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def evaluate_batch(self, events: List[Dict], site_miner_count: int = 0) -> Dict:
        """
        Evaluate a batch of problem events and determine which ones get notifications/tickets.

        Args:
            events: List of event dicts with keys:
                - event_id, site_id, miner_id, issue_code, severity, status
                - start_ts (datetime or ISO string)
                - ml_json (dict with p_fail_24h)
                - action (from EventEngine: 'created', 'updated', 'escalated', etc.)
            site_miner_count: Total miner count for the site (for TopK calculation)

        Returns:
            {
                'notifications': [
                    {'event_id': uuid, 'miner_id': str, 'issue_code': str, 'severity': str,
                     'reason': str, 'priority': int}
                ],
                'tickets': [
                    {'event_id': uuid, 'miner_id': str, 'issue_code': str, 'severity': str,
                     'reason': str, 'priority': int, 'subject': str, 'description': str}
                ],
                'stats': {
                    'total_events': int,
                    'notifications_sent': int,
                    'tickets_created': int,
                    'p2_budget_remaining': int,
                    'p2_suppressed': int
                }
            }
        """
        try:
            logger.info(f"Evaluating batch of {len(events)} events")

            # Filter events - only process created, updated, escalated
            valid_actions = {"created", "updated", "escalated"}
            valid_events = [e for e in events if e.get("action") in valid_actions]

            logger.debug(f"Filtered to {len(valid_events)} valid events")

            if not valid_events:
                return self._empty_result()

            # Evaluate each event against policy rules
            evaluated = []
            for event in valid_events:
                result = self._evaluate_single(event, site_miner_count)
                evaluated.append(
                    {
                        "event": event,
                        "notify": result["notify"],
                        "ticket": result["ticket"],
                        "reason": result["reason"],
                    }
                )

            # Apply budget constraints
            budgeted_result = self._apply_budget(evaluated)

            # Build notifications list
            notifications = []
            for item in budgeted_result["notifications"]:
                event = item["event"]
                notifications.append(
                    {
                        "event_id": event.get("event_id"),
                        "site_id": event.get("site_id"),
                        "miner_id": event.get("miner_id"),
                        "issue_code": event.get("issue_code"),
                        "severity": event.get("severity"),
                        "reason": item["reason"],
                        "priority": self.SEVERITY_PRIORITY.get(event.get("severity"), 99),
                    }
                )

            # Build tickets list
            tickets = []
            for item in budgeted_result["tickets"]:
                event = item["event"]
                subject = self._build_ticket_subject(event)
                description = self._build_ticket_description(event)

                tickets.append(
                    {
                        "event_id": event.get("event_id"),
                        "site_id": event.get("site_id"),
                        "miner_id": event.get("miner_id"),
                        "issue_code": event.get("issue_code"),
                        "severity": event.get("severity"),
                        "reason": item["reason"],
                        "priority": self.SEVERITY_PRIORITY.get(event.get("severity"), 99),
                        "subject": subject,
                        "description": description,
                    }
                )

            # Dispatch to outbox/persistence layer
            if notifications:
                self.dispatch_notifications(notifications)

            if tickets:
                self.dispatch_tickets(tickets)

            # Build stats
            p2_events = [e for e in evaluated if e["event"].get("severity") == "P2"]
            p2_allowed = max(
                0,
                self.MAX_TICKETS_PER_CYCLE
                - sum(
                    1
                    for e in evaluated
                    if e["event"].get("severity") in {"P0", "P1"} and e["ticket"]
                ),
            )
            p2_suppressed = len(
                [e for e in p2_events if not e["ticket"]]
            )

            return {
                "notifications": notifications,
                "tickets": tickets,
                "stats": {
                    "total_events": len(valid_events),
                    "notifications_sent": len(notifications),
                    "tickets_created": len(tickets),
                    "p2_budget_remaining": max(
                        0,
                        p2_allowed
                        - len([t for t in tickets if t["severity"] == "P2"]),
                    ),
                    "p2_suppressed": p2_suppressed,
                },
            }

        except Exception as e:
            logger.exception(f"Error in evaluate_batch: {e}")
            return self._empty_result()

    def _evaluate_single(self, event: Dict, site_miner_count: int) -> Dict:
        """
        Evaluate a single event against policy rules.

        Returns:
            {'notify': bool, 'ticket': bool, 'reason': str}
        """
        try:
            severity = event.get("severity", "P3")
            start_ts = event.get("start_ts")
            ml_json = event.get("ml_json", {})

            # Handle ml_json as string or dict
            if isinstance(ml_json, str):
                try:
                    ml_json = json.loads(ml_json)
                except Exception:
                    ml_json = {}

            p_fail_24h = ml_json.get("p_fail_24h", 0) if ml_json else 0

            # Calculate duration open
            duration_minutes = self._get_duration_minutes(start_ts)

            # Policy evaluation
            if severity == "P0":
                return {
                    "notify": True,
                    "ticket": True,
                    "reason": "P0 - Critical, always notify and ticket",
                }

            elif severity == "P1":
                return {
                    "notify": True,
                    "ticket": True,
                    "reason": "P1 - High, always notify and ticket",
                }

            elif severity == "P2":
                notify = False
                ticket = False
                reason = "P2 - "

                # Check TopK
                if self._is_in_topk(event, site_miner_count):
                    notify = True
                    reason += "in TopK miners"

                # Check duration gate
                elif duration_minutes > self.P2_DURATION_GATE_MINUTES:
                    notify = True
                    reason += f"open > {self.P2_DURATION_GATE_MINUTES} min"

                # Ticket only if p_fail_24h > threshold AND duration > gate
                if (
                    p_fail_24h > self.P2_PFAIL_TICKET_THRESHOLD
                    and duration_minutes > self.P2_DURATION_GATE_MINUTES
                ):
                    ticket = True
                    if not notify:
                        reason = f"P2 - p_fail={p_fail_24h:.2f} & duration > {self.P2_DURATION_GATE_MINUTES} min"
                    else:
                        reason += (
                            f", creating ticket (p_fail={p_fail_24h:.2f})"
                        )

                if not notify and not ticket:
                    reason = (
                        "P2 - below thresholds (no TopK, <30 min, or low p_fail)"
                    )

                return {
                    "notify": notify,
                    "ticket": ticket,
                    "reason": reason,
                }

            else:  # P3 or unknown
                return {
                    "notify": False,
                    "ticket": False,
                    "reason": f"{severity} - Never notify or ticket",
                }

        except Exception as e:
            logger.exception(f"Error evaluating single event: {e}")
            return {
                "notify": False,
                "ticket": False,
                "reason": f"Error during evaluation: {str(e)}",
            }

    def _apply_budget(self, evaluated: List[Dict]) -> Dict:
        """
        Apply budget constraints. P0/P1 always pass. P2 sorted by p_fail_24h desc.

        Returns:
            {'notifications': [items], 'tickets': [items]}
        """
        try:
            # Separate by severity
            p0_p1 = [
                e
                for e in evaluated
                if e["event"].get("severity") in {"P0", "P1"}
            ]
            p2_items = [e for e in evaluated if e["event"].get("severity") == "P2"]

            notifications = []
            tickets = []

            # P0/P1 always get through
            for item in p0_p1:
                if item["notify"]:
                    notifications.append(item)
                if item["ticket"]:
                    tickets.append(item)

            # P2 - sort by p_fail_24h descending and fill remaining budget
            p2_sorted = self._sort_p2_by_pfail(p2_items)

            # Apply notification budget (P2 fills remaining slots)
            notif_budget_remaining = self.MAX_NOTIFICATIONS_PER_CYCLE - len(
                notifications
            )
            for item in p2_sorted:
                if item["notify"] and notif_budget_remaining > 0:
                    notifications.append(item)
                    notif_budget_remaining -= 1

            # Apply ticket budget (P2 fills remaining slots)
            ticket_budget_remaining = self.MAX_TICKETS_PER_CYCLE - len(tickets)
            for item in p2_sorted:
                if item["ticket"] and ticket_budget_remaining > 0:
                    tickets.append(item)
                    ticket_budget_remaining -= 1

            return {
                "notifications": notifications,
                "tickets": tickets,
            }

        except Exception as e:
            logger.exception(f"Error applying budget: {e}")
            return {
                "notifications": [e for e in evaluated if e["notify"]],
                "tickets": [e for e in evaluated if e["ticket"]],
            }

    def dispatch_notifications(self, notifications: List[Dict]):
        """
        Dispatch notifications via event_outbox table or logging.

        Tries to insert into event_outbox with type='notification'.
        If table doesn't exist, logs at WARNING level.
        """
        try:
            if not notifications:
                return

            logger.info(f"Dispatching {len(notifications)} notifications")

            # Check if event_outbox table exists
            if not self._table_exists("event_outbox"):
                logger.warning(
                    f"event_outbox table not found. "
                    f"Logging {len(notifications)} notifications instead."
                )
                for notif in notifications:
                    logger.warning(
                        f"NOTIFICATION: {notif.get('severity')} "
                        f"{notif.get('issue_code')} on miner "
                        f"{notif.get('miner_id')} - {notif.get('reason')}"
                    )
                return

            # Insert into event_outbox
            for notif in notifications:
                try:
                    payload = {
                        "event_id": str(notif.get("event_id")),
                        "miner_id": notif.get("miner_id"),
                        "issue_code": notif.get("issue_code"),
                        "severity": notif.get("severity"),
                        "reason": notif.get("reason"),
                        "priority": notif.get("priority"),
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                    insert_query = text(
                        """
                        INSERT INTO event_outbox (type, payload, created_at)
                        VALUES ('notification', :payload, :now)
                    """
                    )

                    db.session.execute(
                        insert_query,
                        {
                            "payload": json.dumps(payload),
                            "now": datetime.utcnow(),
                        },
                    )

                except Exception as e:
                    logger.error(
                        f"Error inserting notification "
                        f"{notif.get('event_id')}: {e}"
                    )

            db.session.commit()
            logger.info(
                f"Successfully dispatched {len(notifications)} notifications"
            )

        except Exception as e:
            logger.exception(f"Error in dispatch_notifications: {e}")
            db.session.rollback()
            # Fallback to logging
            for notif in notifications:
                logger.warning(
                    f"NOTIFICATION: {notif.get('severity')} "
                    f"{notif.get('issue_code')} on miner {notif.get('miner_id')}"
                )

    def dispatch_tickets(self, tickets: List[Dict]):
        """
        Dispatch tickets. Try HostingTicket model, then event_outbox, then logging.
        """
        try:
            if not tickets:
                return

            logger.info(f"Dispatching {len(tickets)} tickets")

            # Try to create HostingTicket records
            hosting_ticket_available = self._try_create_hosting_tickets(tickets)

            if not hosting_ticket_available:
                # Try event_outbox table
                if self._table_exists("event_outbox"):
                    self._insert_tickets_to_outbox(tickets)
                else:
                    # Fallback to logging
                    logger.warning(
                        f"No ticket dispatch mechanism available. "
                        f"Logging {len(tickets)} tickets instead."
                    )
                    for ticket in tickets:
                        logger.warning(
                            f"TICKET: {ticket.get('subject')} - "
                            f"{ticket.get('description')}"
                        )

        except Exception as e:
            logger.exception(f"Error in dispatch_tickets: {e}")

    def _try_create_hosting_tickets(self, tickets: List[Dict]) -> bool:
        """Try to create HostingTicket records. Returns True if successful."""
        try:
            # Try to import HostingTicket model dynamically
            try:
                from models_hosting import HostingTicket

                hosting_ticket_model = HostingTicket
            except ImportError:
                logger.debug(
                    "HostingTicket model not found, "
                    "skipping direct creation"
                )
                return False

            created_count = 0
            for ticket in tickets:
                try:
                    record = hosting_ticket_model(
                        event_id=str(ticket.get("event_id")),
                        miner_id=ticket.get("miner_id"),
                        issue_code=ticket.get("issue_code"),
                        severity=ticket.get("severity"),
                        subject=ticket.get("subject"),
                        description=ticket.get("description"),
                        status="open",
                        created_at=datetime.utcnow(),
                    )
                    db.session.add(record)
                    created_count += 1

                except Exception as e:
                    logger.error(
                        f"Error creating HostingTicket for "
                        f"{ticket.get('event_id')}: {e}"
                    )

            if created_count > 0:
                db.session.commit()
                logger.info(f"Created {created_count} HostingTicket records")
                return True

            return False

        except Exception as e:
            logger.warning(f"HostingTicket creation not available: {e}")
            db.session.rollback()
            return False

    def _insert_tickets_to_outbox(self, tickets: List[Dict]):
        """Insert tickets into event_outbox table"""
        try:
            for ticket in tickets:
                payload = {
                    "event_id": str(ticket.get("event_id")),
                    "miner_id": ticket.get("miner_id"),
                    "issue_code": ticket.get("issue_code"),
                    "severity": ticket.get("severity"),
                    "subject": ticket.get("subject"),
                    "description": ticket.get("description"),
                    "reason": ticket.get("reason"),
                    "priority": ticket.get("priority"),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                insert_query = text(
                    """
                    INSERT INTO event_outbox (type, payload, created_at)
                    VALUES ('ticket', :payload, :now)
                """
                )

                db.session.execute(
                    insert_query,
                    {
                        "payload": json.dumps(payload),
                        "now": datetime.utcnow(),
                    },
                )

            db.session.commit()
            logger.info(f"Inserted {len(tickets)} tickets into event_outbox")

        except Exception as e:
            logger.error(f"Error inserting tickets to outbox: {e}")
            db.session.rollback()

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        try:
            query = text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
            """
            )
            result = db.session.execute(query, {"table_name": table_name})
            return result.scalar() or False

        except Exception as e:
            logger.warning(
                f"Error checking if table {table_name} exists: {e}"
            )
            return False

    def get_site_summary(self, site_id: int) -> Dict:
        """
        Get notification/ticket summary for a site.
        Returns counts of recent notifications and tickets in last hour.
        """
        try:
            logger.info(f"Getting summary for site {site_id}")

            now = datetime.utcnow()
            one_hour_ago = now - timedelta(hours=1)

            # Try to get from event_outbox
            if self._table_exists("event_outbox"):
                notif_query = text(
                    """
                    SELECT COUNT(*) FROM event_outbox
                    WHERE type = 'notification'
                    AND created_at >= :one_hour_ago
                """
                )

                ticket_query = text(
                    """
                    SELECT COUNT(*) FROM event_outbox
                    WHERE type = 'ticket'
                    AND created_at >= :one_hour_ago
                """
                )

                notif_count = (
                    db.session.execute(
                        notif_query, {"one_hour_ago": one_hour_ago}
                    ).scalar()
                    or 0
                )
                ticket_count = (
                    db.session.execute(
                        ticket_query, {"one_hour_ago": one_hour_ago}
                    ).scalar()
                    or 0
                )
            else:
                notif_count = 0
                ticket_count = 0

            return {
                "site_id": site_id,
                "notifications_last_hour": notif_count,
                "tickets_last_hour": ticket_count,
                "timestamp": now.isoformat(),
            }

        except Exception as e:
            logger.exception(f"Error getting site summary: {e}")
            return {
                "site_id": site_id,
                "notifications_last_hour": 0,
                "tickets_last_hour": 0,
                "error": str(e),
            }

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _is_in_topk(self, event: Dict, site_miner_count: int) -> bool:
        """
        Check if event's miner is in TopK worst miners by p_fail_24h.
        TopK = max(3, floor(site_miner_count * 0.05))
        """
        try:
            if site_miner_count <= 0:
                logger.debug(
                    "site_miner_count not provided, TopK check skipped"
                )
                return False

            k = max(3, int(site_miner_count * 0.05))

            # Query top K miners by p_fail_24h for this site
            site_id = event.get("site_id")
            if not site_id:
                return False

            query = text(
                """
                SELECT miner_id, (ml_json ->> 'p_fail_24h')::float as p_fail
                FROM problem_events
                WHERE site_id = :site_id
                AND severity = 'P2'
                AND status IN ('open', 'ack', 'in_progress')
                AND ml_json IS NOT NULL
                ORDER BY (ml_json ->> 'p_fail_24h')::float DESC
                LIMIT :k
            """
            )

            result = db.session.execute(query, {"site_id": site_id, "k": k})
            top_miners = [row[0] for row in result]

            is_topk = event.get("miner_id") in top_miners
            logger.debug(
                f"TopK check: miner {event.get('miner_id')} "
                f"in_topk={is_topk} (k={k})"
            )

            return is_topk

        except Exception as e:
            logger.warning(f"Error checking TopK: {e}")
            return False

    def _sort_p2_by_pfail(self, p2_items: List[Dict]) -> List[Dict]:
        """Sort P2 items by p_fail_24h descending"""
        try:

            def get_pfail(item):
                ml_json = item["event"].get("ml_json", {})
                if isinstance(ml_json, str):
                    try:
                        ml_json = json.loads(ml_json)
                    except Exception:
                        ml_json = {}
                return ml_json.get("p_fail_24h", 0)

            return sorted(p2_items, key=get_pfail, reverse=True)

        except Exception as e:
            logger.warning(f"Error sorting P2 items: {e}")
            return p2_items

    def _get_duration_minutes(self, start_ts: Any) -> int:
        """Calculate minutes since event start. Returns 0 if invalid."""
        try:
            if not start_ts:
                return 0

            # Handle string timestamps
            if isinstance(start_ts, str):
                # Try ISO format
                try:
                    start_dt = datetime.fromisoformat(
                        start_ts.replace("Z", "+00:00")
                    )
                except Exception:
                    # Try other formats
                    try:
                        start_dt = datetime.fromisoformat(start_ts)
                    except Exception:
                        logger.warning(f"Could not parse start_ts: {start_ts}")
                        return 0
            else:
                start_dt = start_ts

            now = datetime.utcnow()
            delta = now - start_dt
            return int(delta.total_seconds() / 60)

        except Exception as e:
            logger.warning(f"Error calculating duration: {e}")
            return 0

    def _build_ticket_subject(self, event: Dict) -> str:
        """Build ticket subject line"""
        return (
            f"[{event.get('severity')}] {event.get('issue_code')} - "
            f"Miner {event.get('miner_id')}"
        )

    def _build_ticket_description(self, event: Dict) -> str:
        """Build ticket description"""
        ml_json = event.get("ml_json", {})
        if isinstance(ml_json, str):
            try:
                ml_json = json.loads(ml_json)
            except Exception:
                ml_json = {}

        p_fail = ml_json.get("p_fail_24h", "N/A") if ml_json else "N/A"

        return (
            f"Automated ticket for {event.get('issue_code')} on "
            f"miner {event.get('miner_id')}.\n"
            f"Severity: {event.get('severity')}\n"
            f"First detected: {event.get('start_ts', 'unknown')}\n"
            f"p_fail_24h: {p_fail}"
        )

    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "notifications": [],
            "tickets": [],
            "stats": {
                "total_events": 0,
                "notifications_sent": 0,
                "tickets_created": 0,
                "p2_budget_remaining": self.MAX_NOTIFICATIONS_PER_CYCLE,
                "p2_suppressed": 0,
            },
        }
