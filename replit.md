# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application for Bitcoin mining farm owners and clients. It provides real-time Bitcoin mining profitability analysis, integrates real-time data, offers dual-algorithm verification, and supports multiple languages. The system delivers comprehensive operational management, CRM, Web3 integration, technical analysis, professional reporting, and an AI-powered intelligence layer to optimize Bitcoin mining investments and enhance transparency.

## Recent Changes

### 2026-01-26: Architecture Convergence & AI Closed-Loop

**1. Command System Convergence**
- `api/remote_control_api.py` converted to compatibility layer with deprecation headers (Sunset: 2026-06-01)
- All command operations route through `api/control_plane_api.py` v1 as single source of truth
- Unified audit logging to `AuditEvent` table with blockchain-style hash chain
- See: `docs/COMMAND_API_CONVERGENCE.md`

**2. Telemetry Single Source of Truth**
- Created `services/telemetry_service.py` for unified telemetry operations
- New unified API: `api/telemetry_api.py` at `/api/v1/telemetry/*`
- Data contract documented in `docs/TELEMETRY_DATA_CONTRACT.md`
- Four-layer architecture: raw_24h → live → history_5min → daily

**3. Coming Soon Feature Gates**
- Created `common/feature_gates.py` for unified feature flag handling
- `@require_feature('feature_key')` decorator prevents mock data leakage
- Standardized `feature_disabled` response with requirements and waitlist

**4. AI Closed-Loop System**
- Created `models_ai_closedloop.py`: AIRecommendation, AIRecommendationFeedback, AutoApproveRule
- Created `services/ai_closedloop_service.py` for complete closed-loop workflow
- Created `api/ai_closedloop_api.py` at `/api/v1/ai/recommendations/*`
- Full flow: Detect → Diagnose → Recommend → Approve → Act → Audit → Learn
- Integration with Control Plane v1 via RemoteCommand model

## User Preferences
- **Communication style**: Simple, everyday language (中文/English)
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## System Architecture

### UI/UX Decisions
The front-end uses Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design. Chart.js and CountUp.js are used for data visualization and animations. Dynamic English and Chinese language switching is supported with client-side i18n.js.

### Technical Implementations
The system is built on a Flask backend using Blueprints, featuring custom email authentication, session management, an enterprise RBAC v2.0 system, and SQLAlchemy with PostgreSQL for data persistence. Redis is used for caching and task queuing. Performance-critical routes use SQL aggregation. Device Envelope Encryption provides zero-knowledge E2EE for miner credentials. A 4-layer telemetry storage system (raw_24h, live, history_5min, daily) with APScheduler jobs manages high-volume mining data. Command operations are routed through a single control plane API. A unified telemetry service and API are implemented, along with a feature gating system. An AI closed-loop system is integrated for recommendations and feedback.

### Feature Specifications
- **Calculator Module**: Dual-algorithm profitability analysis, real-time BTC price/difficulty integration, ROI analysis, batch calculation.
- **CRM System**: Flask-native CRM with lead management, deal pipeline, invoice generation, and asset management.
- **System Monitoring**: Unified dashboard for real-time health checks, performance metrics, cache analysis, and alerts.
- **Technical Analysis Platform**: Server-side calculation of 10+ technical indicators and historical BTC price analysis.
- **Intelligence Layer**: Event-driven system with ARIMA forecasting, anomaly detection, power optimization, and intelligent ROI explanations.
- **User Management**: Admin backend for user creation, role assignment, RBAC, and access period management.
- **Web3 Configuration Wizard**: Secure interface for blockchain credential setup.
- **Hosting Services Module**: Real-time miner monitoring, miner creation APIs, operational ticketing, hosting management, KPI dashboard, and White Label Branding.
- **Smart Power Curtailment Module**: Bilingual platform with automated scheduler for energy management, supporting manual curtailment and automatic miner recovery based on Performance Priority.
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage monitoring, sell strategy templates, and a backtesting engine.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint, with role-specific dashboards.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics.
- **Edge Collector Architecture**: Real-time miner telemetry collection via Python-based edge collector, cloud receiver API, and management UI, including an alert rules engine and bidirectional command control.
- **IP Scanner & Miner Discovery**: Automatic network scanning to discover Bitcoin miners via CGMiner API.
- **Control Plane System**: Enterprise-grade system for 100MW+ mining operations with:
  - **Zone Partitioning**: Site-level operational boundaries for multi-tenant isolation.
  - **ABAC (Attribute-Based Access Control)**: Customer isolation.
  - **Dual-Approval Workflow**: Configurable risk levels and approver roles for high-risk operations.
  - **Price Plan Versioning**: Audit-safe pricing with immutable version history.
  - **15-Minute Demand Calculation**: Interval-based power metering with DemandLedger.
  - **Audit Event Hash Chain**: SHA-256 blockchain-style immutable audit trail.
  - **Portal Lite API**: Customer-facing REST API for miners, approvals, and zone status.
  - **Zone-Bound Device Security**: Edge devices with zone_id and token_hash for strict access control.
  - **Remote Command Flow**: Full state machine for command dispatch.
  - **Production-Grade Command Reliability**: Atomic lease dispatch, idempotent ACK, retry with exponential backoff, rate limiting, dedupe key, HMAC signatures, and Prometheus metrics.
  - **Credential Protection**: Three-tier IP/credential protection with anti-rollback validation and credential fingerprinting.
  - **Test Coverage**: Extensive test suite covering security, ABAC, approval workflow, command states, credential protection, and audit chain verification.
- **SOC2 Security Compliance Module**: Enterprise security features for SOC2 Type II compliance including log retention, login security enhancements, password policy, session security, security alerts, data access logging, and PII data masking.

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
- **cryptography**: For E2EE decryption.

### JavaScript Libraries
- **Bootstrap 5**: UI framework.
- **Bootstrap Icons**: Icons.
- **Chart.js**: Data visualization.
- **CountUp.js**: Number animation.

### Infrastructure
- **PostgreSQL**: Relational database.
- **Redis**: In-memory data store (cache + task queue).
- **Python 3.9+**: Runtime.
- **Replit Platform**: Deployment and hosting.