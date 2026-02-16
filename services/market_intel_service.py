"""
Market Intel Service
- Aggregates BTC/crypto news from multiple providers (RSS, Finnhub, GDELT)
- Normalizes into a single schema
- Deduplicates, tags, scores relevance, and clusters into story groups

Design goals:
- Server-side ingestion (avoid exposing API keys to browsers)
- Fast UI refresh (cache + TTL)
- Extensible providers (add more RSS feeds / APIs later)
"""

from __future__ import annotations

import os
import re
import time
import json
import hashlib
import logging
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# -----------------------------
# Helpers
# -----------------------------

STOPWORDS_EN = set("""
a an and are as at be by for from has have he her his i if in is it its of on or our that the their then there these they this to was were will with you your
""".split())

STOPWORDS_ZH = set("的 了 在 是 和 与 及 对 于 这 那 我 你 他 她 它 我们 你们 他们 她们 它们 以及 由于 通过 将".split())

def now_ts() -> int:
    return int(time.time())

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def safe_get(d: dict, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def normalize_title(title: str) -> str:
    t = (title or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", t)
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff\s\-_/.:]", "", t)
    return t

def tokenize_for_trends(text: str) -> List[str]:
    if not text:
        return []
    t = normalize_title(text)
    # Keep Chinese characters as tokens; split English by whitespace
    tokens: List[str] = []
    # Chinese tokens (single char) are noisy; keep 2+ char chunks
    zh_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", t)
    tokens.extend([z for z in zh_chunks if z not in STOPWORDS_ZH])

    # English tokens
    en = re.sub(r"[\u4e00-\u9fff]", " ", t)
    for w in en.split():
        if len(w) < 3:
            continue
        if w in STOPWORDS_EN:
            continue
        tokens.append(w)
    return tokens

# -----------------------------
# Schema
# -----------------------------

@dataclass
class NewsItem:
    id: str
    published_at: int
    source: str
    title: str
    summary: str
    url: str
    image: Optional[str] = None
    lang: Optional[str] = None
    entities: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    score: float = 0.0
    story_id: Optional[str] = None

# -----------------------------
# Providers
# -----------------------------

class RSSProvider:
    """
    Fetch RSS feeds. Uses feedparser if installed, otherwise a minimal XML parser.
    """
    def __init__(self, urls: List[str], timeout: int = 10):
        self.urls = urls
        self.timeout = timeout

    def fetch(self, window_hours: int = 24) -> List[NewsItem]:
        items: List[NewsItem] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        for feed_url in self.urls:
            try:
                items.extend(self._fetch_one(feed_url, cutoff))
            except Exception as e:
                logger.warning("RSS fetch failed for %s: %s", feed_url, e)
        return items

    def _fetch_one(self, feed_url: str, cutoff_dt: datetime) -> List[NewsItem]:
        resp = requests.get(feed_url, timeout=self.timeout, headers={"User-Agent": "HashInsight/MarketIntel"})
        resp.raise_for_status()
        content = resp.text

        # Try feedparser
        try:
            import feedparser  # type: ignore
            parsed = feedparser.parse(content)
            out: List[NewsItem] = []
            for e in parsed.entries or []:
                title = getattr(e, "title", "") or ""
                link = getattr(e, "link", "") or ""
                summary = getattr(e, "summary", "") or getattr(e, "description", "") or ""
                published_parsed = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
                if published_parsed:
                    published_at = int(time.mktime(published_parsed))
                else:
                    published_at = now_ts()
                dt = datetime.fromtimestamp(published_at, timezone.utc)
                if dt < cutoff_dt:
                    continue
                src = safe_get(getattr(e, "source", None) or {}, "title", default=None) or self._infer_source(feed_url)
                out.append(NewsItem(
                    id=sha1((src or "") + "|" + (link or "") + "|" + normalize_title(title)),
                    published_at=published_at,
                    source=src,
                    title=title.strip(),
                    summary=self._strip_html(summary),
                    url=link,
                    image=None,
                    lang=None
                ))
            return out
        except Exception:
            # Minimal XML parse fallback
            return self._xml_parse(content, feed_url, cutoff_dt)

    def _xml_parse(self, xml_text: str, feed_url: str, cutoff_dt: datetime) -> List[NewsItem]:
        import xml.etree.ElementTree as ET
        out: List[NewsItem] = []
        root = ET.fromstring(xml_text)
        # RSS2: channel/item
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            published_at = now_ts()
            if pub:
                try:
                    # common RFC822
                    from email.utils import parsedate_to_datetime
                    published_at = int(parsedate_to_datetime(pub).timestamp())
                except Exception:
                    pass
            dt = datetime.fromtimestamp(published_at, timezone.utc)
            if dt < cutoff_dt:
                continue
            src = self._infer_source(feed_url)
            out.append(NewsItem(
                id=sha1((src or "") + "|" + (link or "") + "|" + normalize_title(title)),
                published_at=published_at,
                source=src,
                title=title,
                summary=self._strip_html(desc),
                url=link,
                image=None,
                lang=None
            ))
        return out

    def _infer_source(self, url: str) -> str:
        # best-effort domain label
        m = re.search(r"https?://([^/]+)/", url)
        return (m.group(1) if m else "rss").replace("www.", "")

    def _strip_html(self, s: str) -> str:
        s = re.sub(r"<[^>]+>", " ", s or "")
        s = re.sub(r"\s+", " ", s).strip()
        return s


class FinnhubProvider:
    """
    Finnhub News API: /api/v1/news?category=crypto&token=...
    Requires FINNHUB_TOKEN.
    Docs: https://finnhub.io/docs/api
    """
    def __init__(self, token: str, timeout: int = 10):
        self.token = token
        self.timeout = timeout

    def fetch(self, window_hours: int = 24) -> List[NewsItem]:
        cutoff_ts = now_ts() - int(window_hours * 3600)
        url = "https://finnhub.io/api/v1/news"
        resp = requests.get(url, params={"category": "crypto", "token": self.token},
                            timeout=self.timeout, headers={"User-Agent": "HashInsight/MarketIntel"})
        resp.raise_for_status()
        data = resp.json() or []
        out: List[NewsItem] = []
        for x in data:
            published_at = int(x.get("datetime") or 0) or now_ts()
            if published_at < cutoff_ts:
                continue
            title = (x.get("headline") or "").strip()
            link = (x.get("url") or "").strip()
            out.append(NewsItem(
                id=sha1("finnhub|" + (link or "") + "|" + normalize_title(title)),
                published_at=published_at,
                source=(x.get("source") or "finnhub"),
                title=title,
                summary=(x.get("summary") or "").strip(),
                url=link,
                image=x.get("image"),
                lang=None
            ))
        return out


class GDELTProvider:
    """
    GDELT DOC 2.0 API (JSON)
    Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
    """
    def __init__(self, query: str = "bitcoin OR btc OR cryptocurrency", max_records: int = 50, timeout: int = 10):
        self.query = query
        self.max_records = max_records
        self.timeout = timeout

    def fetch(self, window_hours: int = 24) -> List[NewsItem]:
        # GDELT timespan uses things like "24h", "7d"
        timespan = f"{int(window_hours)}h" if window_hours <= 72 else f"{max(1, int(window_hours/24))}d"
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": self.query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": str(self.max_records),
            "sort": "hybridrel",
            "timespan": timespan,
        }
        resp = requests.get(url, params=params, timeout=self.timeout, headers={"User-Agent": "HashInsight/MarketIntel"})
        resp.raise_for_status()
        data = resp.json() or {}
        arts = data.get("articles") or []
        out: List[NewsItem] = []
        for a in arts:
            title = (a.get("title") or "").strip()
            link = (a.get("url") or "").strip()
            # GDELT seendate is like 20260114120000
            seendate = (a.get("seendate") or "").strip()
            published_at = now_ts()
            if seendate and len(seendate) >= 14:
                try:
                    dt = datetime.strptime(seendate[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                    published_at = int(dt.timestamp())
                except Exception:
                    pass
            out.append(NewsItem(
                id=sha1("gdelt|" + (link or "") + "|" + normalize_title(title)),
                published_at=published_at,
                source=(a.get("sourceCountry") or a.get("sourceCollection") or "gdelt"),
                title=title,
                summary=(a.get("excerpt") or "").strip(),
                url=link,
                image=(a.get("image") or None),
                lang=(a.get("language") or None)
            ))
        return out

# -----------------------------
# Tagging / Scoring / Clustering
# -----------------------------

TAG_RULES: Dict[str, List[str]] = {
    "btc": ["bitcoin", "btc", "satoshi", "lightning", "taproot"],
    "mining": ["miner", "mining", "hashrate", "difficulty", "asic", "antminer", "whatsminer", "pool", "stratum", "block reward", "halving"],
    "etf": ["etf", "blackrock", "fidelity", "ark", "approval", "spot etf"],
    "regulation": ["sec", "cftc", "regulation", "law", "ban", "sanction", "lawsuit", "compliance", "kyc", "aml"],
    "macro": ["inflation", "cpi", "rate", "fed", "yield", "dollar", "dxy", "recession", "liquidity"],
    "exchange": ["binance", "coinbase", "kraken", "okx", "bybit", "exchange", "listing", "delisting"],
    "hack": ["hack", "exploit", "breach", "stolen", "phishing", "drain", "rug pull"],
    "stablecoin": ["stablecoin", "usdt", "usdc", "tether", "circle", "peg"],
    "energy": ["energy", "power", "grid", "electric", "electricity", "demand response", "curtail", "tariff", "pipa", "ppa"],
}

# weights for relevance scoring
TAG_WEIGHTS = {
    "btc": 1.0,
    "mining": 0.8,
    "etf": 0.9,
    "regulation": 0.7,
    "macro": 0.5,
    "exchange": 0.4,
    "hack": 0.6,
    "stablecoin": 0.3,
    "energy": 0.4,
}

def tag_and_score(item: NewsItem) -> NewsItem:
    text = f"{item.title} {item.summary}".lower()
    tags: List[str] = []
    for tag, kws in TAG_RULES.items():
        for kw in kws:
            if kw in text:
                tags.append(tag)
                break
    # If nothing matched but it's from crypto news, still tag btc as soft default if BTC mention appears
    if not tags and ("btc" in text or "bitcoin" in text):
        tags.append("btc")

    score = 0.0
    for t in tags:
        score += TAG_WEIGHTS.get(t, 0.1)
    # boost for BTC-specific mentions
    if "bitcoin" in text or re.search(r"\bbtc\b", text):
        score += 0.5
    # clamp
    score = min(3.0, score)

    item.tags = sorted(set(tags))
    item.score = float(score)
    return item

def story_id_for(item: NewsItem) -> str:
    # cluster by normalized title core tokens (cheap & stable)
    t = normalize_title(item.title)
    tokens = [w for w in tokenize_for_trends(t) if w not in STOPWORDS_EN and w not in STOPWORDS_ZH]
    core = " ".join(tokens[:12]) if tokens else t[:120]
    return sha1(core)

# -----------------------------
# In-memory cache (per process)
# -----------------------------

class TTLCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            v = self._data.get(key)
            if not v:
                return None
            exp, val = v
            if time.time() > exp:
                self._data.pop(key, None)
                return None
            return val

    def set(self, key: str, val: Any, ttl_sec: int) -> None:
        with self._lock:
            self._data[key] = (time.time() + ttl_sec, val)

CACHE = TTLCache()

# -----------------------------
# Service
# -----------------------------

class MarketIntelService:
    def __init__(self):
        self.rss_urls = self._default_rss_urls()
        self.finnhub_token = os.environ.get("FINNHUB_TOKEN", "").strip()
        self.gdelt_enabled = os.environ.get("GDELT_ENABLED", "1").strip() not in ("0", "false", "False")
        self.gdelt_query = os.environ.get("GDELT_QUERY", "bitcoin OR btc OR cryptocurrency")
        self.gdelt_max = int(os.environ.get("GDELT_MAXRECORDS", "50"))
        self.cache_ttl = int(os.environ.get("MARKET_INTEL_CACHE_TTL_SEC", "60"))

    def _default_rss_urls(self) -> List[str]:
        # CoinDesk official article about RSS is sometimes blocked; this arc feed is widely used.
        # Add more sources by setting MARKET_INTEL_RSS_URLS (comma-separated).
        env = os.environ.get("MARKET_INTEL_RSS_URLS")
        if env:
            urls = [u.strip() for u in env.split(",") if u.strip()]
            return urls
        return [
            "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
            "https://cointelegraph.com/rss",
            "https://news.bitcoin.com/feed/",
        ]

    def get_news(self, window_hours: int = 24, q: str = "", tags: Optional[List[str]] = None, limit: int = 200) -> Dict[str, Any]:
        q_norm = (q or "").strip().lower()
        tags_norm = sorted(set([t.strip().lower() for t in (tags or []) if t.strip()]))
        cache_key = f"news:{window_hours}:{q_norm}:{','.join(tags_norm)}:{limit}"
        cached = CACHE.get(cache_key)
        if cached is not None:
            return cached

        items: List[NewsItem] = []
        # Providers
        if self.rss_urls:
            items.extend(RSSProvider(self.rss_urls).fetch(window_hours=window_hours))

        if self.finnhub_token:
            try:
                items.extend(FinnhubProvider(self.finnhub_token).fetch(window_hours=window_hours))
            except Exception as e:
                logger.warning("Finnhub fetch failed: %s", e)

        if self.gdelt_enabled:
            try:
                items.extend(GDELTProvider(query=self.gdelt_query, max_records=self.gdelt_max).fetch(window_hours=window_hours))
            except Exception as e:
                logger.warning("GDELT fetch failed: %s", e)

        # Normalize, tag, score, story cluster
        out: List[NewsItem] = []
        seen: set = set()
        for it in items:
            if not it.url or not it.title:
                continue
            it = tag_and_score(it)
            it.story_id = story_id_for(it)
            # dedupe by url canonical + title
            key = sha1((it.url.split("?")[0]) + "|" + normalize_title(it.title))
            if key in seen:
                continue
            seen.add(key)
            out.append(it)

        # Filter by q/tags
        if q_norm:
            out = [x for x in out if q_norm in (x.title.lower() + " " + (x.summary or "").lower())]
        if tags_norm:
            out = [x for x in out if x.tags and any(t in x.tags for t in tags_norm)]

        # Sort by published desc, score desc
        out.sort(key=lambda x: (x.published_at, x.score), reverse=True)
        out = out[:max(1, limit)]

        # Build story clusters
        stories: Dict[str, Dict[str, Any]] = {}
        for x in out:
            sid = x.story_id or "unknown"
            s = stories.get(sid)
            if not s:
                stories[sid] = {
                    "story_id": sid,
                    "headline": x.title,
                    "top_tags": x.tags or [],
                    "max_score": x.score,
                    "latest_ts": x.published_at,
                    "items": [asdict(x)],
                    "sources": [x.source],
                }
            else:
                s["items"].append(asdict(x))
                s["sources"] = sorted(set(s["sources"] + [x.source]))
                s["latest_ts"] = max(int(s["latest_ts"]), int(x.published_at))
                s["max_score"] = max(float(s["max_score"]), float(x.score))
                # pick best headline
                if float(x.score) > float(s["max_score"]) or len(x.title) > len(s["headline"]):
                    s["headline"] = x.title

        story_list = list(stories.values())
        story_list.sort(key=lambda s: (s["latest_ts"], s["max_score"]), reverse=True)

        result = {
            "window_hours": window_hours,
            "q": q,
            "tags": tags_norm,
            "items": [asdict(x) for x in out],
            "stories": story_list[:50],
            "generated_at": now_ts(),
        }
        CACHE.set(cache_key, result, self.cache_ttl)
        return result

    def get_trends(self, window_hours: int = 24, q: str = "", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        news = self.get_news(window_hours=window_hours, q=q, tags=tags, limit=500)
        items = news["items"]
        # keyword trends
        freq: Dict[str, int] = {}
        tag_freq: Dict[str, int] = {}
        src_freq: Dict[str, int] = {}
        for it in items:
            for t in (it.get("tags") or []):
                tag_freq[t] = tag_freq.get(t, 0) + 1
            src = it.get("source") or "unknown"
            src_freq[src] = src_freq.get(src, 0) + 1
            tokens = tokenize_for_trends((it.get("title") or "") + " " + (it.get("summary") or ""))
            for tok in tokens:
                freq[tok] = freq.get(tok, 0) + 1

        top_keywords = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:30]
        top_tags = sorted(tag_freq.items(), key=lambda kv: kv[1], reverse=True)
        top_sources = sorted(src_freq.items(), key=lambda kv: kv[1], reverse=True)[:20]

        return {
            "window_hours": window_hours,
            "q": q,
            "tags": sorted(set([t.strip().lower() for t in (tags or []) if t.strip()])),
            "top_keywords": [{"term": k, "count": v} for k, v in top_keywords],
            "top_tags": [{"tag": k, "count": v} for k, v in top_tags],
            "top_sources": [{"source": k, "count": v} for k, v in top_sources],
            "generated_at": now_ts(),
        }
