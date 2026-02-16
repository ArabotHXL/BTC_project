"""
Market Intel Routes (Blueprint)

UI:
- /analytics/market-intel

API:
- /api/market-intel/news
- /api/market-intel/trends
- /api/market-intel/bookmarks  (GET/POST/DELETE)
- /api/market-intel/alerts     (GET/POST/DELETE)
- /api/market-intel/alerts/matches
"""

from __future__ import annotations

import logging
from typing import List, Optional

from flask import Blueprint, jsonify, render_template, request, session

logger = logging.getLogger(__name__)

# Optional auth/RBAC imports (keep this module drop-in)
try:
    from auth import login_required  # type: ignore
except Exception:
    def login_required(fn):  # type: ignore
        return fn

try:
    from common.rbac import requires_module_access, Module, AccessLevel  # type: ignore
    _HAS_RBAC = True
except Exception:
    _HAS_RBAC = False
    def requires_module_access(*args, **kwargs):  # type: ignore
        def deco(fn):
            return fn
        return deco
    class Module:  # type: ignore
        ANALYTICS = "ANALYTICS"
        ANALYTICS_MARKET_INTEL = "ANALYTICS_MARKET_INTEL"
    class AccessLevel:  # type: ignore
        READ = "READ"

from services.market_intel_service import MarketIntelService
from services.market_intel_store import init_db, list_bookmarks, add_bookmark, remove_bookmark, list_alerts, add_alert, delete_alert, eval_alerts

market_intel_bp = Blueprint("market_intel", __name__)

_service = MarketIntelService()
_db_ready = False

def _user_key() -> str:
    # Prefer authenticated identity if available
    email = session.get("email") or session.get("user_email")
    if email:
        return str(email).lower()
    # fallback: per-session key
    anon = session.get("_anon_key")
    if not anon:
        import secrets
        anon = "anon_" + secrets.token_hex(8)
        session["_anon_key"] = anon
    return anon

@market_intel_bp.before_app_request
def _ensure_db():
    global _db_ready
    if not _db_ready:
        try:
            init_db()
            _db_ready = True
        except Exception as e:
            logger.warning("Market Intel sqlite init failed: %s", e)
            _db_ready = True  # avoid repeated attempts; API can still work without persistence

@market_intel_bp.route("/analytics/market-intel")
@login_required
@requires_module_access(getattr(Module, "ANALYTICS_MARKET_INTEL", getattr(Module, "ANALYTICS", "ANALYTICS")), getattr(AccessLevel, "READ", "READ"))
def market_intel_page():
    # Allow UI to know language
    current_lang = session.get("lang", "en")
    return render_template("market_intel.html", current_lang=current_lang)

# ---------------- API ----------------

def _parse_tags(v: str) -> List[str]:
    if not v:
        return []
    return [x.strip().lower() for x in v.split(",") if x.strip()]

@market_intel_bp.route("/api/market-intel/news")
@login_required
def api_news():
    window = int(request.args.get("window_hours", "24"))
    q = request.args.get("q", "")
    tags = _parse_tags(request.args.get("tags", ""))
    limit = int(request.args.get("limit", "200"))
    data = _service.get_news(window_hours=window, q=q, tags=tags, limit=limit)
    return jsonify(data)

@market_intel_bp.route("/api/market-intel/trends")
@login_required
def api_trends():
    window = int(request.args.get("window_hours", "24"))
    q = request.args.get("q", "")
    tags = _parse_tags(request.args.get("tags", ""))
    data = _service.get_trends(window_hours=window, q=q, tags=tags)
    return jsonify(data)

@market_intel_bp.route("/api/market-intel/bookmarks", methods=["GET", "POST", "DELETE"])
@login_required
def api_bookmarks():
    uk = _user_key()

    if request.method == "GET":
        return jsonify({"items": list_bookmarks(uk)})

    if request.method == "POST":
        payload = request.get_json(force=True, silent=True) or {}
        item = payload.get("item") or payload
        if not item.get("id"):
            return jsonify({"error": "missing item.id"}), 400
        add_bookmark(uk, item)
        return jsonify({"ok": True})

    # DELETE
    payload = request.get_json(force=True, silent=True) or {}
    news_id = payload.get("news_id") or payload.get("id")
    if not news_id:
        return jsonify({"error": "missing news_id"}), 400
    remove_bookmark(uk, str(news_id))
    return jsonify({"ok": True})

@market_intel_bp.route("/api/market-intel/alerts", methods=["GET", "POST", "DELETE"])
@login_required
def api_alerts():
    uk = _user_key()

    if request.method == "GET":
        return jsonify({"items": list_alerts(uk)})

    if request.method == "POST":
        payload = request.get_json(force=True, silent=True) or {}
        name = (payload.get("name") or "").strip() or "Alert"
        keywords = payload.get("keywords") or []
        tags = payload.get("tags") or []
        min_score = float(payload.get("min_score") or 0.0)
        aid = add_alert(uk, name, keywords, tags, min_score=min_score)
        return jsonify({"ok": True, "id": aid})

    # DELETE
    payload = request.get_json(force=True, silent=True) or {}
    aid = payload.get("id") or payload.get("alert_id")
    if not aid:
        return jsonify({"error": "missing id"}), 400
    delete_alert(uk, int(aid))
    return jsonify({"ok": True})

@market_intel_bp.route("/api/market-intel/alerts/matches")
@login_required
def api_alert_matches():
    uk = _user_key()
    window = int(request.args.get("window_hours", "24"))
    news = _service.get_news(window_hours=window, q="", tags=None, limit=500)
    alerts = list_alerts(uk)
    matches = eval_alerts(alerts, news["items"])
    return jsonify({"matches": matches, "generated_at": news["generated_at"]})
