"""
Market Intel Storage (default: SQLite)

This module avoids tight coupling to your main SQLAlchemy models.
- If you want to move to SQLAlchemy later, keep the same interface and swap backend.

Env:
- MARKET_INTEL_SQLITE_PATH: path to sqlite file (default: ./market_intel.db)
"""

from __future__ import annotations

import os
import json
import time
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB_PATH = os.environ.get("MARKET_INTEL_SQLITE_PATH", "market_intel.db").strip() or "market_intel.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_bookmarks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_key TEXT NOT NULL,
  news_id TEXT NOT NULL,
  title TEXT,
  url TEXT,
  source TEXT,
  published_at INTEGER,
  created_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_market_bookmarks_user_news
  ON market_bookmarks(user_key, news_id);

CREATE TABLE IF NOT EXISTS market_alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_key TEXT NOT NULL,
  name TEXT NOT NULL,
  keywords TEXT,
  tags TEXT,
  min_score REAL DEFAULT 0.0,
  created_at INTEGER NOT NULL
);
"""

def _conn(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    c = sqlite3.connect(db_path, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    c = _conn(db_path)
    try:
        c.executescript(_SCHEMA)
        c.commit()
    finally:
        c.close()

def list_bookmarks(user_key: str, limit: int = 200, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    c = _conn(db_path)
    try:
        cur = c.execute(
            "SELECT news_id, title, url, source, published_at, created_at FROM market_bookmarks WHERE user_key=? ORDER BY created_at DESC LIMIT ?",
            (user_key, limit),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        c.close()

def add_bookmark(user_key: str, item: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> None:
    c = _conn(db_path)
    try:
        c.execute(
            "INSERT OR IGNORE INTO market_bookmarks(user_key, news_id, title, url, source, published_at, created_at) VALUES(?,?,?,?,?,?,?)",
            (
                user_key,
                item.get("id"),
                item.get("title"),
                item.get("url"),
                item.get("source"),
                int(item.get("published_at") or 0),
                int(time.time()),
            ),
        )
        c.commit()
    finally:
        c.close()

def remove_bookmark(user_key: str, news_id: str, db_path: str = DEFAULT_DB_PATH) -> None:
    c = _conn(db_path)
    try:
        c.execute("DELETE FROM market_bookmarks WHERE user_key=? AND news_id=?", (user_key, news_id))
        c.commit()
    finally:
        c.close()

def list_alerts(user_key: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    c = _conn(db_path)
    try:
        cur = c.execute(
            "SELECT id, name, keywords, tags, min_score, created_at FROM market_alerts WHERE user_key=? ORDER BY created_at DESC",
            (user_key,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        # normalize json fields
        for r in rows:
            r["keywords"] = json.loads(r["keywords"]) if r.get("keywords") else []
            r["tags"] = json.loads(r["tags"]) if r.get("tags") else []
        return rows
    finally:
        c.close()

def add_alert(user_key: str, name: str, keywords: List[str], tags: List[str], min_score: float = 0.0, db_path: str = DEFAULT_DB_PATH) -> int:
    c = _conn(db_path)
    try:
        cur = c.execute(
            "INSERT INTO market_alerts(user_key, name, keywords, tags, min_score, created_at) VALUES(?,?,?,?,?,?)",
            (
                user_key,
                name,
                json.dumps([k.strip().lower() for k in keywords if k.strip()]),
                json.dumps([t.strip().lower() for t in tags if t.strip()]),
                float(min_score or 0.0),
                int(time.time()),
            ),
        )
        c.commit()
        return int(cur.lastrowid)
    finally:
        c.close()

def delete_alert(user_key: str, alert_id: int, db_path: str = DEFAULT_DB_PATH) -> None:
    c = _conn(db_path)
    try:
        c.execute("DELETE FROM market_alerts WHERE user_key=? AND id=?", (user_key, int(alert_id)))
        c.commit()
    finally:
        c.close()

def match_alert(alert: Dict[str, Any], item: Dict[str, Any]) -> bool:
    # score filter
    if float(item.get("score") or 0.0) < float(alert.get("min_score") or 0.0):
        return False
    # tag filter
    alert_tags = set([t.lower() for t in (alert.get("tags") or [])])
    item_tags = set([t.lower() for t in (item.get("tags") or [])])
    if alert_tags and not (alert_tags & item_tags):
        return False
    # keyword filter
    kws = [k.lower() for k in (alert.get("keywords") or []) if k]
    if kws:
        text = ((item.get("title") or "") + " " + (item.get("summary") or "")).lower()
        if not any(k in text for k in kws):
            return False
    return True

def eval_alerts(alerts: List[Dict[str, Any]], items: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    matches: Dict[int, List[Dict[str, Any]]] = {}
    for a in alerts:
        aid = int(a["id"])
        for it in items:
            if match_alert(a, it):
                matches.setdefault(aid, []).append(it)
    return matches
