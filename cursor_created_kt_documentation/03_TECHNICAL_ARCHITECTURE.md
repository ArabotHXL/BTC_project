# HashInsight Enterprise Platform - Technical Architecture

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Target Audience:** Software Developers, Technical Leads, System Architects

---

## Table of Contents

1. [Application Structure](#application-structure)
2. [Flask Blueprint Architecture](#flask-blueprint-architecture)
3. [Route Organization](#route-organization)
4. [Database Models](#database-models)
5. [Service Layer](#service-layer)
6. [API Design](#api-design)
7. [Authentication & Authorization](#authentication--authorization)
8. [Caching Strategy](#caching-strategy)
9. [Event-Driven Architecture](#event-driven-architecture)
10. [External Integrations](#external-integrations)
11. [Error Handling](#error-handling)
12. [Testing Strategy](#testing-strategy)

---

## Application Structure

### Project Layout

```
BitcoinMiningCalculator/
├── app.py                          # Main Flask application entry point
├── main.py                         # Application factory and startup
├── config.py                       # Configuration management
├── db.py                           # Database initialization
├── models.py                       # SQLAlchemy database models
├── auth.py                         # Authentication utilities
├── mining_calculator.py            # Core mining calculation engine
├── routes/                         # Route blueprints
│   ├── auth_routes.py             # Authentication routes
│   ├── calculator_routes.py        # Calculator routes
│   ├── admin_routes.py             # Admin routes
│   ├── analytics_routes.py         # Analytics routes
│   ├── health_routes.py            # Health check routes
│   └── ...
├── modules/                        # Business logic modules
│   ├── calculator/                # Calculator module
│   ├── crm/                       # CRM module
│   ├── hosting/                   # Hosting module
│   ├── client/                    # Client portal module
│   └── analytics/                 # Analytics module
├── intelligence/                   # Intelligence layer
│   ├── api/                       # Intelligence APIs
│   │   ├── forecast_api.py       # Forecasting API
│   │   ├── optimize_api.py        # Optimization API
│   │   ├── explain_api.py         # Explanation API
│   │   └── health_api.py          # Health check API
│   └── ...
├── api/                            # API modules
│   ├── portal_lite_api.py         # Portal Lite API
│   ├── control_plane_api.py       # Control plane API
│   ├── remote_control_api.py     # Remote control API
│   └── ...
├── cdc-platform/                  # CDC event platform
│   ├── core/                      # Core CDC infrastructure
│   ├── workers/                   # Event consumers
│   └── ...
├── templates/                      # Jinja2 templates
├── static/                         # Static assets (CSS, JS, images)
└── tests/                          # Test suite
```

---

## Flask Blueprint Architecture

### Blueprint Registration Order

Blueprints are registered in `app.py` in the following order:

#### 1. Core System Blueprints (Lines 1914-1967)

| Blueprint | URL Prefix | File | Purpose |
|-----------|------------|------|---------|
| `system_health_bp` | None | `routes/health_routes.py` | System health checks |
| `i18n_bp` | None | `routes/i18n_routes.py` | Internationalization |
| `auth_bp` | None | `routes/auth_routes.py` | Authentication |
| `calculator_bp` | None | `routes/calculator_routes.py` | Mining calculator |
| `admin_bp` | None | `routes/admin_routes.py` | Admin functions |
| `hosting_bp` | `/hosting` | `modules/hosting/__init__.py` | Hosting services |
| `client_bp` | `/client` | `modules/client/__init__.py` | Client portal |

#### 2. Business Feature Blueprints (Lines 4569-4660)

| Blueprint | URL Prefix | File | Purpose |
|-----------|------------|------|---------|
| `billing_bp` | `/billing` | `billing_routes.py` | Subscription & payments |
| `batch_calculator_bp` | None | `batch_calculator_routes.py` | Batch calculations |
| `miner_bp` | `/admin/miners` | `miner_management_routes.py` | Miner management |
| `deribit_bp` | None | `deribit_web_routes.py` | Deribit analysis |
| `deribit_advanced_bp` | None | `deribit_analysis_package/...` | Advanced Deribit |
| `sla_nft_bp` | None | `sla_nft_routes.py` | SLA NFT management |
| `batch_import_bp` | `/batch` | `routes/batch_import_routes.py` | Batch imports |
| `miner_import_bp` | `/api/miners` | `routes/miner_import_routes.py` | Miner imports |
| `analytics_bp` | `/api/analytics` | `routes/analytics_routes.py` | Analytics |
| `trust_bp` | `/trust` | `routes/trust_routes.py` | Trust center |

#### 3. Intelligence Layer Blueprints (Lines 4657-4660)

| Blueprint | URL Prefix | File | Purpose |
|-----------|------------|------|---------|
| `forecast_bp` | `/api/intelligence/forecast` | `intelligence/api/forecast_api.py` | Forecasting |
| `optimize_bp` | `/api/intelligence/optimize` | `intelligence/api/optimize_api.py` | Optimization |
| `explain_bp` | `/api/intelligence/explain` | `intelligence/api/explain_api.py` | Explanations |
| `health_bp` | `/api/intelligence` | `intelligence/api/health_api.py` | Intelligence health |

#### 4. Monitoring & System Blueprints (Lines 4673-4799)

| Blueprint | URL Prefix | File | Purpose |
|-----------|------------|------|---------|
| `monitoring_bp` | None | `monitoring_routes.py` | System monitoring |
| `web3_sla_bp` | `/api/web3/sla` | `api/web3_sla_api.py` | Web3 SLA |
| `treasury_execute_bp` | `/api/treasury-exec` | `api/treasury_execute_api.py` | Treasury execution |
| `crm_integration_bp` | `/api/crm-integration` | `api/crm_integration_api.py` | CRM integration |
| `rbac_bp` | None | `routes/rbac_routes.py` | RBAC management |
| `collector_bp` | None | `routes/collector_routes.py` | Data collector |
| `device_bp` | None | `api/device_api.py` | Device management |
| `miner_secrets_bp` | None | `api/...` | Miner secrets |
| `edge_secrets_bp` | None | `api/...` | Edge secrets |
| `audit_bp` | None | `api/...` | Audit logs |
| `ip_encryption_bp` | None | `api/...` | IP encryption |
| `sites_api_bp` | None | `api/...` | Sites API |
| `monitor_bp` | None | `routes/monitor_routes.py` | Monitoring |

#### 5. Control Plane Blueprints (Lines 4769-4829)

| Blueprint | URL Prefix | File | Purpose |
|-----------|------------|------|---------|
| `scan_bp` | None | `api/scan_api.py` | Network scanning |
| `edge_scan_bp` | None | `api/...` | Edge scanning |
| `remote_control_bp` | None | `api/remote_control_api.py` | Remote control |
| `collector_routes_bp` | None | `routes/collector_routes.py` | Collector routes |
| `credential_protection_bp` | None | `api/credential_protection_api.py` | Credential protection |
| `control_plane_bp` | None | `api/control_plane_api.py` | Control plane |
| `portal_bp` | `/api/v1/portal` | `api/portal_lite_api.py` | Portal Lite API |
| `legacy_bp` | `/api/remote` | `api/legacy_adapter.py` | Legacy API adapter |

### Total Blueprint Count

**Active Blueprints:** ~40+ blueprints registered

**Registration Pattern:**
```python
try:
    from module import blueprint_name
    app.register_blueprint(blueprint_name, url_prefix='...')
    logging.info("Blueprint registered successfully")
except ImportError as e:
    logging.warning(f"Blueprint not available: {e}")
```

This pattern allows the application to continue running even if optional modules are missing.

---

## Route Organization

### Route Categories

#### 1. Public Routes (No Authentication Required)
- `/` - Homepage
- `/login` - Login page
- `/register` - Registration
- `/verify-email/<token>` - Email verification
- `/legal` - Legal terms

#### 2. Authenticated Routes (Login Required)
- `/dashboard` - User dashboard
- `/calculator` - Mining calculator
- `/analytics` - Analytics dashboard
- `/crm/*` - CRM module (role-based access)

#### 3. Admin Routes (Admin/Owner Only)
- `/admin/user_access` - User management
- `/admin/miners` - Miner model management
- `/admin/login_records` - Login history

#### 4. API Routes (JSON Responses)
- `/api/*` - RESTful API endpoints
- `/api/intelligence/*` - Intelligence layer APIs
- `/api/analytics/*` - Analytics APIs

### Route Decorators

```python
from auth import login_required
from decorators import requires_role, requires_admin_or_owner

# Basic authentication
@app.route('/dashboard')
@login_required
def dashboard():
    ...

# Role-based access
@app.route('/admin/users')
@requires_role(['admin', 'owner'])
def admin_users():
    ...

# Module-specific access
@app.route('/crm/customers')
@requires_crm_access
def crm_customers():
    ...
```

---

## Database Models

### Core Models (models.py)

#### User Management
```python
class UserAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True)
    password_hash = db.Column(db.String(512))
    role = db.Column(db.String(20))
    has_access = db.Column(db.Boolean)
    subscription_plan = db.Column(db.String(20))
    expires_at = db.Column(db.DateTime)
```

#### Mining Data
```python
class MinerModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), unique=True)
    hashrate_th = db.Column(db.Float)
    power_w = db.Column(db.Integer)
    efficiency = db.Column(db.Float)

class UserMiner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'))
    miner_model_id = db.Column(db.Integer, db.ForeignKey('miner_models.id'))
    quantity = db.Column(db.Integer)
```

#### Network Data
```python
class NetworkSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    btc_price = db.Column(db.Float)
    difficulty = db.Column(db.Float)
    hashrate = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime)
```

### CRM Models
```python
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200))
    email = db.Column(db.String(256))
    status = db.Column(db.String(20))

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'))
    status = db.Column(db.Enum(LeadStatus))
    value = db.Column(db.Float)
```

### Hosting Models
```python
class HostingSite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    capacity_mw = db.Column(db.Float)
    electricity_rate = db.Column(db.Float)
    status = db.Column(db.String(20))

class HostingMiner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('crm_customers.id'))
    model = db.Column(db.String(100))
    status = db.Column(db.String(20))
```

### Intelligence Models
```python
class ForecastDaily(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'))
    forecast_date = db.Column(db.Date)
    btc_price_predicted = db.Column(db.Float)
    confidence_lower = db.Column(db.Float)
    confidence_upper = db.Column(db.Float)
```

---

## Service Layer

### Mining Calculator Service

**File:** `mining_calculator.py`

**Key Functions:**
```python
def calculate_mining_profitability(
    miner_model: str,
    quantity: int,
    electricity_cost: float,
    btc_price: float = None,
    difficulty: float = None
) -> dict:
    """
    Calculate mining profitability
    
    Returns:
        {
            'daily_revenue': float,
            'daily_cost': float,
            'daily_profit': float,
            'roi_days': float,
            'monthly_profit': float
        }
    """
```

**Algorithm:**
1. Fetch miner specs from database
2. Get real-time BTC price (if not provided)
3. Get network difficulty (if not provided)
4. Calculate BTC mined per day
5. Calculate revenue (BTC * price)
6. Calculate costs (power * electricity_rate)
7. Calculate profit and ROI

### Analytics Service

**File:** `modules/analytics/engines/analytics_engine.py`

**Key Functions:**
```python
def calculate_technical_indicators(price_data: list) -> dict:
    """Calculate RSI, MACD, SMA, EMA, Bollinger Bands"""
    
def generate_roi_heatmap(miners: list, price_range: tuple) -> dict:
    """Generate ROI heatmap data"""
    
def historical_replay(start_date: date, end_date: date) -> dict:
    """Replay historical calculations"""
```

### Intelligence Services

**Forecast Service** (`intelligence/api/forecast_api.py`):
- ARIMA time-series forecasting
- 7-day price predictions
- Confidence intervals

**Optimize Service** (`intelligence/api/optimize_api.py`):
- Linear programming optimization
- Power curtailment scheduling
- Profit maximization

**Explain Service** (`intelligence/api/explain_api.py`):
- ROI change explanations
- Recommendations
- Rule-based expert system

---

## API Design

### RESTful API Conventions

**URL Structure:**
- `/api/{resource}` - Resource collection
- `/api/{resource}/{id}` - Specific resource
- `/api/{resource}/{id}/{action}` - Resource action

**HTTP Methods:**
- `GET` - Retrieve data
- `POST` - Create new resource
- `PUT` - Update entire resource
- `PATCH` - Partial update
- `DELETE` - Delete resource

**Response Format:**
```json
{
    "success": true,
    "data": { ... },
    "message": "Operation successful",
    "timestamp": "2025-01-06T12:00:00Z"
}
```

**Error Format:**
```json
{
    "success": false,
    "error": "Error message",
    "code": "ERROR_CODE",
    "timestamp": "2025-01-06T12:00:00Z"
}
```

### Key API Endpoints

#### Mining Calculator
```
POST /api/calculate
Body: {
    "miner_model": "Antminer S21",
    "quantity": 10,
    "electricity_cost": 0.06
}
Response: {
    "daily_revenue": 120.50,
    "daily_profit": 45.30,
    "roi_days": 180
}
```

#### Analytics
```
GET /api/analytics/market-data
Response: {
    "btc_price": 45000,
    "network_hashrate": 900,
    "fear_greed_index": 65
}

POST /api/analytics/roi-heatmap
Body: {
    "miners": [...],
    "price_range": [40000, 50000]
}
```

#### Intelligence
```
GET /api/intelligence/forecast/{user_id}
Response: {
    "predictions": [
        {
            "date": "2025-01-07",
            "price": 46000,
            "lower_bound": 44000,
            "upper_bound": 48000
        }
    ]
}
```

---

## Authentication & Authorization

### Authentication Flow

1. **Login:**
   ```
   POST /login
   Body: { "email": "...", "password": "..." }
   → Sets Flask session cookie
   → Redirects to dashboard
   ```

2. **Session Management:**
   - Flask sessions with secure cookies
   - HttpOnly, Secure, SameSite=None flags
   - 8-hour session lifetime
   - Automatic timeout on inactivity

3. **Logout:**
   ```
   GET /logout
   → Clears session
   → Redirects to login
   ```

### Authorization Decorators

```python
# Basic login required
@login_required
def my_route():
    ...

# Role-based
@requires_role(['admin', 'owner'])
def admin_route():
    ...

# Module-specific
@requires_crm_access
def crm_route():
    ...

# Owner only
@requires_owner_only
def owner_route():
    ...
```

### RBAC System

**Roles:**
- `owner` - Full access
- `admin` - Administrative access
- `mining_site` - Site management
- `customer` - Own data only
- `guest` - Read-only

**Permission Matrix:**
| Feature | Owner | Admin | Mining Site | Customer | Guest |
|---------|-------|-------|-------------|----------|-------|
| Calculator | ✅ | ✅ | ✅ | ✅ | ✅ |
| CRM | ✅ | ✅ | ✅ | ❌ | ❌ |
| Hosting | ✅ | ✅ | ✅ | Limited | ❌ |
| Admin | ✅ | ✅ | ❌ | ❌ | ❌ |
| Intelligence | ✅ | ✅ | ✅ | ✅ | ❌ |

---

## Caching Strategy

### Cache Layers

1. **Memory Cache** (Flask-Caching)
   - In-process cache
   - Fast access
   - Lost on restart

2. **Redis Cache**
   - Distributed cache
   - Persists across restarts
   - Shared across workers

### Cache Keys

```python
# Real-time data (short TTL)
"btc_price"                    # 60 seconds
"network_hashrate"             # 60 seconds
"network_difficulty"           # 60 seconds

# Miner data (medium TTL)
"miner_specs:{model_id}"       # 1 hour
"miner_models"                 # 1 hour

# Calculations (medium TTL)
"calculation:{user_id}:{hash}" # 5 minutes

# Analytics (variable TTL)
"technical_indicators"         # 5 minutes
"roi_heatmap:{hash}"           # 1 hour

# Intelligence (long TTL)
"intelligence:forecast:{user_id}" # 30 minutes
```

### Cache Strategy: Stale-While-Revalidate

```python
def get_with_swr(key, fetch_fn, ttl=300):
    cached = redis.get(key)
    if cached:
        # Return cached data immediately
        if redis.ttl(key) < ttl / 2:
            # Refresh in background
            background_refresh(key, fetch_fn, ttl)
        return cached
    # Cache miss - fetch and cache
    return fetch_and_cache(key, fetch_fn, ttl)
```

---

## Event-Driven Architecture

### CDC Platform Components

1. **Transactional Outbox** (`cdc-platform/core/infra/outbox.py`)
   - Writes events in same transaction as business data
   - Table: `event_outbox`

2. **Debezium Connector**
   - Reads from PostgreSQL WAL
   - Publishes to Kafka topics

3. **Kafka Topics**
   - `events.miner` - Miner-related events
   - `events.treasury` - Treasury events
   - `events.ops` - Operations events
   - `events.crm` - CRM events

4. **Event Consumers** (`cdc-platform/workers/`)
   - `portfolio_consumer.py` - Portfolio recalculation
   - `intel_consumer.py` - Intelligence updates

### Event Flow Example

```
User updates miner configuration
    ↓
BEGIN TRANSACTION
    UPDATE user_miners SET quantity = 5
    INSERT INTO event_outbox (event_type, payload)
        VALUES ('miner.portfolio_updated', {...})
COMMIT
    ↓
Debezium captures WAL change (< 200ms)
    ↓
Event published to Kafka: events.miner
    ↓
Portfolio Consumer receives event
    ↓
Check event_inbox (idempotency)
    ↓
Recalculate portfolio ROI
    ↓
Update database
    ↓
Insert into event_inbox (mark as processed)
```

---

## External Integrations

### Data Source APIs

**CoinGecko API:**
```python
def get_real_time_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "usd"}
    response = requests.get(url, params=params)
    return response.json()["bitcoin"]["usd"]
```

**Blockchain.info API:**
```python
def get_network_stats():
    url = "https://blockchain.info/stats"
    response = requests.get(url)
    return {
        "difficulty": response.json()["difficulty"],
        "hashrate": response.json()["hash_rate"]
    }
```

### Error Handling

```python
def get_with_fallback(primary_fn, fallback_fn, cache_key=None):
    try:
        result = primary_fn()
        if cache_key:
            cache.set(cache_key, result, ttl=60)
        return result
    except Exception as e:
        logging.warning(f"Primary API failed: {e}, using fallback")
        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                return cached
        return fallback_fn()
```

---

## Error Handling

### Global Error Handlers

```python
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logging.error(f"Internal error: {error}")
    return render_template('errors/500.html'), 500
```

### API Error Responses

```python
def api_error(message, code=400, error_code=None):
    return jsonify({
        "success": False,
        "error": message,
        "code": error_code,
        "timestamp": datetime.utcnow().isoformat()
    }), code
```

### Validation

```python
from flask import request

def validate_calculation_request():
    data = request.get_json()
    required = ['miner_model', 'quantity', 'electricity_cost']
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    return data
```

---

## Testing Strategy

### Test Structure

```
tests/
├── unit/              # Unit tests
│   ├── test_calculator.py
│   ├── test_analytics.py
│   └── ...
├── integration/       # Integration tests
│   ├── test_api.py
│   └── ...
└── fixtures/          # Test data
```

### Example Test

```python
def test_calculate_profitability():
    result = calculate_mining_profitability(
        miner_model="Antminer S21",
        quantity=10,
        electricity_cost=0.06,
        btc_price=45000,
        difficulty=100
    )
    assert result['daily_revenue'] > 0
    assert result['roi_days'] > 0
```

---

## Next Steps

For **Implementation Details**, see:
- [Low-Level Implementation](04_LOW_LEVEL_IMPLEMENTATION.md) - Code-level details
- [Route-to-Page Mapping](05_ROUTE_TO_PAGE_MAPPING.md) - Complete URL structure

For **Architecture Overview**, see:
- [High-Level Architecture](01_HIGH_LEVEL_ARCHITECTURE.md) - Business-focused
- [Executive Summary](00_EXECUTIVE_SUMMARY.md) - Non-technical
