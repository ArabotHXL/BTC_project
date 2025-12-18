# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application for mining farm owners and clients. It provides real-time Bitcoin mining profitability analysis, integrates real-time data, offers dual-algorithm verification, and supports multiple languages. The system delivers comprehensive operational management, CRM, Web3 integration, technical analysis, professional reporting, and an AI-powered intelligence layer to optimize Bitcoin mining investments and enhance transparency.

## User Preferences
- **Communication style**: Simple, everyday language (中文/English)
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## Recent Updates (December 2025)

### Performance Optimizations
- **Hosting API N+1 Query Fix**: Optimized `/api/sites`, `/api/client/dashboard`, and `/api/client/miner-distribution` routes using SQL aggregation queries instead of N+1 queries, significantly improving load times for 6000+ miners.
- **Database Query Optimization**: Replaced Python-side loops with `db.func.count()`, `db.func.sum()`, and `db.case()` for efficient server-side aggregation.

### Security Fixes
- **Open Redirect Vulnerability Fix**: Language switcher (`/set_language`) now validates referrer URLs to prevent external redirect attacks. Only same-origin URLs are allowed.
- **CSRF Protection**: Re-enabled on authentication routes for protection against cross-site request forgery.
- **SQL Injection Fixes**: Parameterized queries in database.py and intelligence_api.py to prevent SQL injection attacks.
- **Redis Rate Limiting**: Enterprise-grade sliding window algorithm with Redis backend, thread-safe in-memory fallback, accurate reset time calculation from oldest request timestamp, and proper X-RateLimit headers on all responses.

### Architecture Improvements
- **Blueprint Extraction**: Modularized routes into separate blueprints (health_routes.py, i18n_routes.py, calculator_routes.py, admin_routes.py) for better code organization.
- **Test Coverage**: Unit tests for rate_limiting.py (14 tests) covering memory/Redis backends, decorators, and header injection.

### Language System Enhancements
- **859+ Translation Keys**: Comprehensive bilingual support across all modules (homepage, CRM, hosting, calculator, etc.)
- **Instant No-Refresh Language Switching**: Client-side i18n.js engine updates all data-i18n elements without page reload
- **Session-Based Persistence**: Language preference stored in Flask session with browser auto-detection fallback
- **Security-Validated Switching**: Language endpoint validates redirect URLs against allowed domains
- **Dynamic Content Translation**: All JavaScript-rendered content (tables, status badges, buttons) properly translated via onLangChange callbacks and I18n.updatePageTranslations() calls
- **Race Condition Handling**: Dynamic content uses fallback text from meta tag language when I18n hasn't initialized yet

### CRM-Hosting Integration
- **Deep Integration Architecture**: Customer.email ↔ UserAccess.email → UserMiner relationship enables mine owners to view customer mining operations directly in CRM
- **5 API Endpoints**: `/crm/api/customer/<id>/hosting-stats`, `/crm/api/customer/<id>/hosting-miners`, `/crm/api/customer/<id>/sync-hosting`, `/crm/api/sync-all-hosting`, `/crm/api/sync-status`
- **Real-Time Data Display**: CRM customer detail pages show live miner status, hashrate, and revenue data
- **Sync Status Monitoring**: Health check endpoint reports link rate, sync health, and integration issues
- **Architecture Documentation**: Complete API specs in `architecture/integration/CRM-Flask-sync.md`
- **Schema Definitions**: Python dataclasses for type validation in `common/schemas/crm_sync.py`

### Power Efficiency Metrics (Engineering-Focused)
- **24h Hashrate & Efficiency Chart**: Replaced net revenue chart with dual-axis performance visualization
- **TH/kW Efficiency Metric**: Power efficiency calculated as `hashrate_TH/s × 1000 / power_W` (higher is better)
- **Dual Y-Axis**: Left axis (cyan): Hashrate in TH/s, Right axis (orange): Efficiency in TH/kW
- **Bilingual Support**: Full English/Chinese translations for chart title, axis labels, legend, and tooltip notes

### Temperature-Based Intelligent Frequency Control (温度智能控频)
- **Data Models**: `ThermalProtectionConfig` for temperature thresholds and frequency settings, `ThermalEvent` for event logging
- **ThermalProtectionService**: Monitors miner temperatures and auto-throttles frequency when overheating
- **Temperature Thresholds**: Configurable warning (70°C), throttle (80°C), critical (90°C), and recovery (65°C) temperatures
- **Auto-Recovery**: Automatically restores frequency when temperature drops below recovery threshold
- **Event Logging**: All thermal protection events (warning/throttle/critical/recovery) logged with timestamps
- **Notification System**: Configurable email alerts for each event type
- **API Endpoints**: `/api/thermal/config`, `/api/thermal/check`, `/api/thermal/events`, `/api/thermal/stats`
- **UI Configuration**: Site settings page with temperature threshold configuration and real-time stats

### White Label Branding System (白标系统)
- **Data Model**: `SiteBranding` stores company name, logo URLs, color schemes, and contact info per site
- **Logo Upload**: Supports PNG, JPG, SVG, WebP with automatic file naming
- **Color Configuration**: Primary, secondary, and accent colors with live preview
- **Social Media Links**: Twitter, Telegram, Discord integration
- **API Endpoints**: `/api/branding/<site_id>` for GET/PUT, `/api/branding/<site_id>/logo` for upload
- **UI Configuration**: Site settings page with brand preview and color picker

### Enterprise RBAC v2.0 Permission Matrix (企业级权限矩阵)
- **6 User Roles**: Owner, Admin, Mining_Site_Owner, Client, Customer, Guest
- **40+ Modules**: Granular permission control across all system features
- **3 Access Levels**: FULL (完全访问), READ (只读), NONE (无权限)
- **Module-Based Decorators**: `@requires_module_access(Module.XXX)` for consistent enforcement
- **Auth Layering**: `@login_required` + `@requires_module_access` for proper authentication → authorization flow
- **Key Permissions**:
  - User Delete: Only Owner (Admin cannot)
  - Remote Control Execute: Owner/Admin/Mining_Site_Owner only
  - Client/Customer: READ access to hosting status, curtailment history, financial data
  - Guest: Calculator and technical analysis only
- **Routes Protected**: 100+ API and HTML routes with module-level RBAC enforcement
- **Core File**: `common/rbac.py` defines the complete permission matrix

### Device Envelope Encryption (设备信封加密)
- **Zero-Knowledge Architecture**: End-to-end encryption for miner credentials between browser and Edge Collector, server never sees plaintext
- **Cryptography**: X25519 Sealed Box for DEK wrapping + AES-256-GCM for credential encryption
- **Device Management**: Edge device registration with X25519 keypairs, key rotation, device revocation
- **Capability Levels**: 3-tier permission system (DISCOVERY/TELEMETRY/CONTROL) controlling Edge Collector access
- **Anti-Rollback Protection**: Monotonic counter prevents replay attacks
- **Security Audit**: Full audit logging with IP masking and sensitive data redaction
- **API Endpoints**: `/api/devices/*`, `/api/miners/:id/secrets`, `/api/miners/:id/capability`, `/api/edge/secrets`, `/api/audit/*`
- **CSP Protection**: Content Security Policy enabled in production with wasm-unsafe-eval for libsodium WebAssembly
- **UI Integration**: Device management, capability config, and audit log viewer in site settings page
- **Documentation**: Complete architecture documentation at `architecture/device_envelope_encryption.md`

## System Architecture

### UI/UX Decisions
The front-end utilizes Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design. Chart.js and CountUp.js are used for data visualization and animations. Dynamic English and Chinese language switching is supported with 859+ translation keys and instant no-refresh updates via client-side i18n.js.

### Technical Implementations
The system is built on a Flask backend using Blueprints for modularity. It features custom email authentication, session management, and an enterprise RBAC v2.0 system. SQLAlchemy with PostgreSQL handles data persistence, and Redis is used for caching and task queuing. Performance-critical routes use SQL aggregation to avoid N+1 query patterns.

### Feature Specifications
- **Calculator Module**: Dual-algorithm profitability analysis for 19+ ASIC models, real-time BTC price/difficulty integration, ROI analysis, and batch calculation.
- **CRM System**: Flask-native CRM with lead management, deal pipeline, invoice generation, and asset management.
- **System Monitoring**: Unified dashboard for real-time health checks, performance metrics, cache analysis, and alerts.
- **Technical Analysis Platform**: Server-side calculation of 10+ technical indicators and historical BTC price analysis.
- **Intelligence Layer**: Event-driven system with ARIMA forecasting for BTC price/difficulty, anomaly detection, power optimization, and intelligent ROI explanations.
- **User Management**: Admin backend for user creation, role assignment, RBAC, and access period management.
- **Web3 Configuration Wizard**: Secure interface for blockchain credential setup.
- **Hosting Services Module**: Real-time miner monitoring, single/batch miner creation APIs, operational ticketing, and comprehensive hosting management, including advanced device management (6000+ miners) with KPI dashboard, quick search, batch operations, single miner controls, and an operation audit trail. Features smart pagination and a collapsible sidebar. Includes a detailed Single Miner Dashboard for individual miner health and performance tracking.
- **Smart Power Curtailment Module**: Bilingual platform with automated scheduler for smart energy management, supporting manual curtailment and automatic miner recovery based on a Performance Priority strategy, integrated with AI forecasting.
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage monitoring, sell strategy templates, and a backtesting engine.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint, with role-specific dashboards.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics.
- **Edge Collector Architecture**: Enables real-time miner telemetry collection from on-premises mining farms to cloud infrastructure, including a Python-based edge collector, a cloud receiver API, and a management UI. Features an alert rules engine and a bidirectional command control system for cloud-to-edge miner control.
- **IP Scanner & Miner Discovery**: Automatic network scanning to discover Bitcoin miners via CGMiner API (TCP port 4028). Supports IP range (192.168.1.1-254), CIDR notation (192.168.1.0/24), and edge-delegated scanning. Discovery returns: hashrate (TH/s), temperature, pool URL, worker name, firmware version, MAC address, uptime, latency. Full telemetry (fan speeds, frequency) available via Edge Collector pipeline after registration. API routes: `/api/scan/start`, `/api/scan/<scan_id>/status`, `/api/scan/<scan_id>/results`, `/api/scan/<scan_id>/register`. Service: `services/ip_scanner.py`. Documentation: `docs/ip_scan_miner_discovery_manual.md`.
- **End-to-End Encryption (E2EE)**: Implements zero-knowledge E2EE for sensitive miner connection credentials (e.g., passwords), with encryption/decryption occurring client-side in the browser or on the Edge Collector, utilizing AES-256-GCM. Supports two-tier encryption plans (credentials only or full connection object).

### System Design Choices
The architecture emphasizes modularity with page-isolated components and database-centric communication. Authentication is custom email-based with session management and RBAC. API integrations follow a strategy of intelligent fallback, Stale-While-Revalidate (SWR) caching, batch API calls, and robust error handling. The system is optimized for deployment on the Replit platform using Gunicorn.

## External Dependencies

### API Integration
- **CoinWarz API**: Mining data and profitability.
- **CoinGecko API**: Real-time and historical cryptocurrency prices.
- **Blockchain.info API**: Bitcoin network statistics.
- **IP-API**: Geolocation services.
- **Ankr RPC**: Free Bitcoin RPC service.
- **Gmail SMTP**: Email services.
- **Deribit, OKX, Binance APIs**: Trading data.

### Python Libraries
- **Flask**: Web framework.
- **SQLAlchemy**: ORM.
- **Requests**: HTTP client.
- **NumPy/Pandas**: Data analysis.
- **Werkzeug**: Password hashing.
- **RQ (Redis Queue)**: Task distribution.
- **Statsmodels**: Time-series prediction.
- **PuLP**: Linear programming optimization.
- **XGBoost**: Machine learning prediction.
- **Flask-Caching**: Performance optimization.
- **Gunicorn**: WSGI server.
- **psycopg2-binary**: PostgreSQL adapter.
- **cryptography**: For E2EE decryption in Edge Collector.

### JavaScript Libraries
- **Bootstrap 5**: UI framework.
- **Bootstrap Icons**: Icons.
- **Chart.js**: Data visualization.
- **CountUp.js**: Number animation.

### Infrastructure
- **PostgreSQL**: Relational database (Replit hosted).
- **Redis**: In-memory data store (cache + task queue).
- **Python 3.9+**: Runtime.
- **Replit Platform**: Deployment and hosting.