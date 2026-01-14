# HashInsight Enterprise Platform - Low-Level Implementation

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Target Audience:** System Architects, Senior Developers, Technical Leads

---

## Table of Contents

1. [Application Initialization](#application-initialization)
2. [Database Connection Management](#database-connection-management)
3. [Blueprint Registration Flow](#blueprint-registration-flow)
4. [Request Processing Pipeline](#request-processing-pipeline)
5. [Authentication Flow](#authentication-flow)
6. [Caching Implementation](#caching-implementation)
7. [Event Processing](#event-processing)
8. [Error Handling Mechanisms](#error-handling-mechanisms)
9. [Performance Optimizations](#performance-optimizations)
10. [Security Implementation](#security-implementation)

---

## Application Initialization

### Entry Point: main.py

```python
def create_app():
    """Factory function to create and configure the Flask app"""
    # 1. Validate environment variables
    required_env_vars = ["DATABASE_URL", "SESSION_SECRET"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        if "SESSION_SECRET" in missing_vars:
            raise SystemExit("CRITICAL SECURITY ERROR: SESSION_SECRET required")
        if "DATABASE_URL" in missing_vars:
            raise SystemExit("CRITICAL ERROR: DATABASE_URL required")
    
    # 2. Database health check (optional)
    skip_db_check = os.environ.get("SKIP_DATABASE_HEALTH_CHECK", "1")
    if not skip_db_check:
        db_status = db_health_manager.check_database_connection(database_url)
        if not db_status['connected']:
            logging.error(f"Database connection failed: {db_status.get('error')}")
    
    # 3. Create Flask app
    app = Flask(__name__)
    
    # 4. Load configuration
    from config import get_config
    config_class = get_config()
    app.config.from_object(config_class)
    
    # 5. Initialize extensions
    db.init_app(app)
    security_manager = SecurityManager(app)
    
    # 6. Register blueprints (see Blueprint Registration Flow)
    register_all_blueprints(app)
    
    # 7. Initialize database tables
    with app.app_context():
        db.create_all()
    
    return app
```

### Startup Sequence

1. **Environment Validation** (main.py:24-35)
2. **Database Health Check** (main.py:38-50)
3. **Flask App Creation** (app.py:30)
4. **Configuration Loading** (app.py:34-36)
5. **Database Initialization** (app.py:52-53)
6. **Security Manager Setup** (app.py:56)
7. **Blueprint Registration** (app.py:1907-4829)
8. **Database Table Creation** (app.py:317-340)
9. **Background Services Start** (app.py:461-488)

---

## Database Connection Management

### Connection Pool Configuration

**File:** `config.py`

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,              # Base connection pool size
    'pool_recycle': 300,           # Recycle connections after 5 minutes
    'pool_pre_ping': True,         # Test connections before use
    'pool_timeout': 30,            # Wait up to 30 seconds for connection
    'max_overflow': 20,            # Allow 20 additional connections
    'connect_args': {
        'connect_timeout': 15,     # Connection timeout
        'application_name': 'btc_mining_calculator'
    }
}
```

### Connection Lifecycle

1. **Connection Acquisition:**
   ```python
   # SQLAlchemy automatically manages pool
   result = db.session.execute(query)
   ```

2. **Connection Validation:**
   - `pool_pre_ping=True` tests connection before use
   - Invalid connections are recycled

3. **Connection Recycling:**
   - Connections older than 300 seconds are recycled
   - Prevents stale connection errors

4. **Connection Cleanup:**
   ```python
   @app.teardown_appcontext
   def shutdown_session(exception=None):
       db.session.remove()  # Return connection to pool
   ```

### Health Check Implementation

**File:** `database_health.py`

```python
def check_database_connection(database_url):
    try:
        conn = psycopg2.connect(database_url, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return {
            'connected': True,
            'database_version': version,
            'response_time_ms': (time.time() - start) * 1000
        }
    except Exception as e:
        return {
            'connected': False,
            'error': str(e),
            'suggestion': 'Check DATABASE_URL and network connectivity'
        }
```

---

## Blueprint Registration Flow

### Registration Order in app.py

1. **Core System** (Lines 1914-1967)
   - Health routes
   - i18n routes
   - Auth routes
   - Calculator routes
   - Admin routes
   - Hosting module
   - Client module

2. **Business Features** (Lines 4569-4660)
   - Billing
   - Batch calculator
   - Miner management
   - Analytics
   - Trust center

3. **Intelligence Layer** (Lines 4657-4660)
   - Forecast API
   - Optimize API
   - Explain API
   - Health API

4. **System & Monitoring** (Lines 4673-4799)
   - Monitoring
   - Web3 SLA
   - Treasury execution
   - CRM integration

5. **Control Plane** (Lines 4769-4829)
   - Control plane API
   - Portal Lite API
   - Legacy adapter
   - Remote control

### Registration Pattern

```python
try:
    from module import blueprint_name
    app.register_blueprint(blueprint_name, url_prefix='...')
    logging.info("Blueprint registered successfully")
except ImportError as e:
    logging.warning(f"Blueprint not available: {e}")
    # Application continues without this blueprint
```

**Benefits:**
- Graceful degradation if optional modules missing
- Easy to enable/disable features
- Clear error logging

---

## Request Processing Pipeline

### Middleware Stack

```
1. WSGI Server (Gunicorn)
   ↓
2. CookiePartitionMiddleware (app.py:78-98)
   - Adds Partitioned attribute for Chrome 3PCD
   ↓
3. Security Headers Middleware (app.py:118-139)
   - Adds security headers to all responses
   ↓
4. Flask Application
   ↓
5. Blueprint Router
   - Routes request to appropriate blueprint
   ↓
6. Route Handler
   - Executes route function
   ↓
7. Response Generation
   - Renders template or returns JSON
   ↓
8. After Request Hook (app.py:118-139)
   - Applies security headers
```

### Cookie Partition Middleware

**File:** `app.py:78-98`

```python
class CookiePartitionMiddleware:
    def __init__(self, app, session_cookie_name):
        self.app = app
        self.session_cookie_name = session_cookie_name

    def __call__(self, environ, start_response):
        def _start_response(status, headers, exc_info=None):
            new_headers = []
            for k, v in headers:
                if k.lower() == 'set-cookie' and v.startswith(f"{self.session_cookie_name}="):
                    if 'SameSite=None' in v and 'Secure' in v:
                        if 'Partitioned' not in v:
                            v = v + '; Partitioned'
                new_headers.append((k, v))
            return start_response(status, new_headers, exc_info)
        return self.app(environ, _start_response)
```

**Purpose:** Enables cookies in iframe contexts (Replit preview)

---

## Authentication Flow

### Login Process

**File:** `routes/auth_routes.py`

```python
@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    # 1. Validate input
    if not email or not password:
        flash('Email and password required')
        return redirect(url_for('auth.login'))
    
    # 2. Query user from database
    user = UserAccess.query.filter_by(email=email).first()
    
    # 3. Verify password
    if user and check_password_hash(user.password_hash, password):
        # 4. Check access
        if not user.has_access:
            flash('Account access revoked')
            return redirect(url_for('auth.login'))
        
        # 5. Create session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_role'] = user.role
        session.permanent = True
        
        # 6. Log login
        log_login(user.id, request.remote_addr)
        
        # 7. Redirect
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid credentials')
        return redirect(url_for('auth.login'))
```

### Session Management

**Configuration:** `config.py`

```python
SESSION_COOKIE_SECURE = True        # HTTPS only
SESSION_COOKIE_HTTPONLY = True      # No JavaScript access
SESSION_COOKIE_SAMESITE = 'None'    # Cross-site cookies
SESSION_COOKIE_DOMAIN = None        # Default domain
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8 hour sessions
```

### Authorization Decorators

**File:** `decorators.py`

```python
def requires_role(roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if session.get('user_role') not in roles:
                flash('Insufficient permissions')
                return redirect(url_for('unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

## Caching Implementation

### Cache Manager

**File:** `cache_manager.py`

```python
from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'simple',  # In-memory cache
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Redis cache (if available)
try:
    import redis
    redis_client = redis.Redis.from_url(os.getenv('REDIS_URL'))
    cache = Cache(config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': os.getenv('REDIS_URL'),
        'CACHE_DEFAULT_TIMEOUT': 300
    })
except:
    pass  # Fallback to simple cache
```

### Cache Usage Pattern

```python
@cache.memoize(timeout=60)
def get_btc_price():
    """Cache BTC price for 60 seconds"""
    return fetch_from_api()

# Manual caching
def get_with_cache(key, fetch_fn, ttl=300):
    cached = cache.get(key)
    if cached:
        return cached
    result = fetch_fn()
    cache.set(key, result, timeout=ttl)
    return result
```

### Stale-While-Revalidate

```python
def get_with_swr(key, fetch_fn, ttl=300):
    cached = cache.get(key)
    if cached:
        # Check if cache is about to expire
        ttl_remaining = cache.get(key + '_ttl', ttl)
        if ttl_remaining < ttl / 2:
            # Refresh in background
            threading.Thread(target=lambda: cache.set(key, fetch_fn(), timeout=ttl)).start()
        return cached
    # Cache miss - fetch and cache
    result = fetch_fn()
    cache.set(key, result, timeout=ttl)
    return result
```

---

## Event Processing

### CDC Platform Architecture

**Outbox Pattern Implementation**

**File:** `cdc-platform/core/infra/outbox.py`

```python
class OutboxPublisher:
    def publish(self, event_type, user_id, payload):
        """Publish event to outbox table"""
        event = EventOutbox(
            kind=event_type,
            user_id=user_id,
            payload=json.dumps(payload),
            idempotency_key=generate_idempotency_key(),
            created_at=datetime.utcnow()
        )
        db.session.add(event)
        # Event committed in same transaction as business data
        db.session.commit()
```

**Event Consumer**

**File:** `cdc-platform/workers/portfolio_consumer.py`

```python
def consume_event(event):
    # 1. Check idempotency
    if event_already_processed(event.id, 'portfolio-recalc-group'):
        return  # Skip duplicate
    
    # 2. Acquire distributed lock
    lock_key = f"lock:user:{event.user_id}:portfolio"
    if not acquire_lock(lock_key, ttl=60):
        return  # Another consumer is processing
    
    try:
        # 3. Process event
        recalculate_portfolio(event.user_id)
        
        # 4. Mark as processed
        mark_event_processed(event.id, 'portfolio-recalc-group')
    finally:
        # 5. Release lock
        release_lock(lock_key)
```

---

## Error Handling Mechanisms

### Global Error Handlers

**File:** `app.py`

```python
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()  # Prevent session issues
    logging.error(f"Internal error: {error}", exc_info=True)
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

# Usage
@api_bp.route('/calculate')
def calculate():
    try:
        result = perform_calculation()
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return api_error(str(e), code=400, error_code="INVALID_INPUT")
    except Exception as e:
        logging.error(f"Calculation error: {e}", exc_info=True)
        return api_error("Internal server error", code=500, error_code="INTERNAL_ERROR")
```

### Database Error Handling

```python
def safe_db_query(query_func):
    """Wrapper for database queries with error handling"""
    try:
        return query_func()
    except sqlalchemy.exc.OperationalError as e:
        logging.error(f"Database connection error: {e}")
        # Attempt reconnection
        db.session.rollback()
        return query_func()  # Retry once
    except Exception as e:
        logging.error(f"Database query error: {e}")
        db.session.rollback()
        raise
```

---

## Performance Optimizations

### Connection Pooling

- **Pool Size:** 10 base connections
- **Max Overflow:** 20 additional connections
- **Pre-ping:** Validates connections before use
- **Recycle:** 300 seconds to prevent stale connections

### Query Optimization

```python
# Bad: N+1 query problem
users = User.query.all()
for user in users:
    miners = UserMiner.query.filter_by(user_id=user.id).all()  # N queries

# Good: Eager loading
users = User.query.options(
    db.joinedload(User.miners)
).all()  # 1 query with JOIN
```

### Batch Processing

```python
def batch_calculate(miners_data):
    """Process multiple calculations efficiently"""
    results = []
    for batch in chunk(miners_data, size=100):
        batch_results = process_batch(batch)
        results.extend(batch_results)
    return results
```

### Lazy Loading

```python
# Delay heavy imports until needed
_cache_manager = None

def get_cache_manager():
    global _cache_manager
    if _cache_manager is None:
        from cache_manager import cache
        _cache_manager = cache
    return _cache_manager
```

---

## Security Implementation

### Password Hashing

**File:** `auth.py`

```python
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    """Hash password using PBKDF2"""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(password_hash, password):
    """Verify password against hash"""
    return check_password_hash(password_hash, password)
```

### CSRF Protection

**File:** `security_enhancements.py`

```python
class SecurityManager:
    @staticmethod
    def generate_csrf_token():
        """Generate CSRF token"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return session['csrf_token']
    
    @staticmethod
    def validate_csrf_token(token):
        """Validate CSRF token"""
        return token and token == session.get('csrf_token')
```

### SQL Injection Prevention

**Always use parameterized queries:**

```python
# Bad: SQL injection vulnerable
query = f"SELECT * FROM users WHERE email = '{email}'"

# Good: Parameterized query
query = text("SELECT * FROM users WHERE email = :email")
result = db.session.execute(query, {"email": email})
```

### XSS Prevention

**Jinja2 auto-escaping:**

```python
# In templates, variables are auto-escaped
{{ user_input }}  # Automatically escaped

# If you need raw HTML (use carefully)
{{ user_input|safe }}  # Only if you trust the input
```

---

## Next Steps

For **Architecture Overview**, see:
- [High-Level Architecture](01_HIGH_LEVEL_ARCHITECTURE.md) - Business view
- [Technical Architecture](03_TECHNICAL_ARCHITECTURE.md) - Developer view

For **Route Details**, see:
- [Route-to-Page Mapping](05_ROUTE_TO_PAGE_MAPPING.md) - Complete URL structure

For **Documentation Maintenance**, see:
- [Dynamic Update Guide](06_DYNAMIC_UPDATE_GUIDE.md) - Keeping docs updated
