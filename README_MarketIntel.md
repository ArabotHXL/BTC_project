# HashInsight Market Intel (BTC Market News Monitor)

This patch adds a **Market Intel** feature to your Flask app:
- Aggregates BTC/Crypto news from **RSS + (optional) Finnhub + (optional) GDELT**
- Normalizes + deduplicates + tags + relevance scoring + story clustering
- Provides a **dark UI page** + API endpoints
- Adds **Bookmarks** + **Alert rules** (stored in SQLite by default)

---

## 1) Routes added

UI:
- `GET /analytics/market-intel`

API:
- `GET /api/market-intel/news?window_hours=24&q=etf&tags=mining,regulation&limit=200`
- `GET /api/market-intel/trends?window_hours=24&q=&tags=`
- `GET/POST/DELETE /api/market-intel/bookmarks`
- `GET/POST/DELETE /api/market-intel/alerts`
- `GET /api/market-intel/alerts/matches?window_hours=24`

---

## 2) Files added

- `routes/market_intel_routes.py`
- `services/market_intel_service.py`
- `services/market_intel_store.py` (SQLite persistence)
- `templates/market_intel.html`
- `static/js/market-intel.js`
- `static/css/market-intel.css`

`analytics_main.html` (and template copy) adds a sidebar link to **Market Intel**.

---

## 3) Config (environment variables)

### Data sources
- `MARKET_INTEL_RSS_URLS` (comma-separated). Default includes:
  - CoinDesk RSS: `https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml`
  - Cointelegraph RSS: `https://cointelegraph.com/rss`
  - Bitcoin.com RSS: `https://news.bitcoin.com/feed/`

Optional:
- `FINNHUB_TOKEN` → enables Finnhub `/news?category=crypto`
- `GDELT_ENABLED` (`1` or `0`) → enable/disable GDELT
- `GDELT_QUERY` → default: `bitcoin OR btc OR cryptocurrency`
- `GDELT_MAXRECORDS` → default: `50`

### Caching
- `MARKET_INTEL_CACHE_TTL_SEC` → default `60`

### Storage
- `MARKET_INTEL_SQLITE_PATH` → default `market_intel.db` (relative to app working dir)

---

## 4) Notes / Next upgrades

- Providers are intentionally modular:
  - Add more RSS feeds by appending to `MARKET_INTEL_RSS_URLS`
  - Add more API providers by implementing the same `fetch()` pattern as existing providers
- Alert “matches” are computed on-demand (no background job).
  - If you want push notifications: add a scheduler (Celery/APS) later.

