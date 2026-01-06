# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application for Bitcoin mining farm owners and clients. It provides real-time Bitcoin mining profitability analysis, integrates real-time data, offers dual-algorithm verification, and supports multiple languages. The system delivers comprehensive operational management, CRM, Web3 integration, technical analysis, professional reporting, and an AI-powered intelligence layer to optimize Bitcoin mining investments and enhance transparency.

## User Preferences
- **Communication style**: Simple, everyday language (中文/English)
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## System Architecture

### UI/UX Decisions
The front-end uses Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design. Chart.js and CountUp.js are used for data visualization and animations. Dynamic English and Chinese language switching is supported with client-side i18n.js.

### Technical Implementations
The system is built on a Flask backend using Blueprints. It features custom email authentication, session management, an enterprise RBAC v2.0 system, and SQLAlchemy with PostgreSQL for data persistence. Redis is used for caching and task queuing. Performance-critical routes use SQL aggregation. Device Envelope Encryption provides zero-knowledge E2EE for miner credentials. A 4-layer telemetry storage system (raw_24h, live, history_5min, daily) with APScheduler jobs manages high-volume mining data.

### Feature Specifications
- **Calculator Module**: Dual-algorithm profitability analysis for 19+ ASIC models, real-time BTC price/difficulty integration, ROI analysis, and batch calculation.
- **CRM System**: Flask-native CRM with deep integration to hosting services, providing lead management, deal pipeline, invoice generation, and asset management.
- **System Monitoring**: Unified dashboard for real-time health checks, performance metrics, cache analysis, and alerts.
- **Technical Analysis Platform**: Server-side calculation of 10+ technical indicators and historical BTC price analysis.
- **Intelligence Layer**: Event-driven system with ARIMA forecasting for BTC price/difficulty, anomaly detection, power optimization, and intelligent ROI explanations.
- **User Management**: Admin backend for user creation, role assignment, RBAC, and access period management.
- **Web3 Configuration Wizard**: Secure interface for blockchain credential setup.
- **Hosting Services Module**: Real-time miner monitoring, single/batch miner creation APIs, operational ticketing, hosting management, KPI dashboard, and quick search. Supports White Label Branding.
- **Smart Power Curtailment Module**: Bilingual platform with automated scheduler for smart energy management, supporting manual curtailment and automatic miner recovery based on a Performance Priority strategy, integrated with AI forecasting.
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage monitoring, sell strategy templates, and a backtesting engine.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint, with role-specific dashboards.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics.
- **Edge Collector Architecture**: Enables real-time miner telemetry collection from on-premises farms to cloud infrastructure via a Python-based edge collector, cloud receiver API, and management UI. Features an alert rules engine and bidirectional command control.
- **IP Scanner & Miner Discovery**: Automatic network scanning to discover Bitcoin miners via CGMiner API.
- **Control Plane System**: Enterprise-grade system for 100MW+ mining operations with:
  - **Zone Partitioning**: Site-level operational boundaries for multi-tenant isolation (models_control_plane.py: Zone, ZoneMembership)
  - **ABAC (Attribute-Based Access Control)**: Customer isolation ensuring users only access their own data (api/portal_lite_api.py)
  - **Dual-Approval Workflow**: High-risk operations require both customer and owner approval with configurable risk levels and approver roles
  - **Price Plan Versioning**: Audit-safe pricing with immutable version history (models_control_plane.py: PricePlan, PricePlanVersion)
  - **15-Minute Demand Calculation**: Interval-based power metering with DemandLedger for billing accuracy
  - **Audit Event Hash Chain**: SHA-256 blockchain-style immutable audit trail (AuditEvent, AuditChainService)
  - **Portal Lite API**: Customer-facing REST API at /api/v1/portal/* for miners, approvals, and zone status
  - **Legacy API Compatibility**: /api/remote/* adapter with deprecation warnings for gradual migration
  - **Zone-Bound Device Security**: Edge devices have zone_id and token_hash for strict access control
  - **Remote Command Flow**: Full state machine (PENDING → PENDING_APPROVAL → APPROVED → DISPATCHED → COMPLETED)
  - **Credential Protection (NEW)**: Three-tier IP/credential protection with anti-rollback validation:
    - **Mode 1 (UI Masking)**: Plaintext storage with RBAC-based display masking for IP and sensitive fields
    - **Mode 2 (Server Envelope)**: Two-layer key management (MASTER_KEY → Site DEK) using PBKDF2 + Fernet encryption
    - **Mode 3 (Device E2EE)**: End-to-end encryption where server only stores ciphertext, Edge device decrypts locally
    - **Anti-Rollback Counter**: Monotonic counter validation prevents replay attacks (ANTI_ROLLBACK_REJECT audit events)
    - **Credential Fingerprint**: SHA-256 truncated hash for integrity verification
    - **REST API**: /api/v1/sites/{id}/security-settings, /api/v1/miners/{id}/credential, /api/v1/miners/{id}/reveal, /api/v1/sites/{id}/batch-migrate, /api/v1/edge/decrypt, /api/v1/audit/verify
  - **Test Coverage**: 63+ tests covering security, ABAC, approval workflow, command states, credential protection, and audit chain verification

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
- **PostgreSQL**: Relational database (Replit hosted).
- **Redis**: In-memory data store (cache + task queue).
- **Python 3.9+**: Runtime.
- **Replit Platform**: Deployment and hosting.

## Documentation

### Documentation Practices
- **Update docs when making changes**: Always update relevant documentation when modifying modules, APIs, or system logic
- **Keep docs/ folder current**: Technical architecture documents should reflect the current system state
- **Include flowcharts for complex flows**: Use ASCII diagrams for data flow and system architecture

### Key Documentation Files
| File | Description |
|------|-------------|
| `docs/COLLECTOR_REMOTE_CONTROL_FLOWCHART.md` | Edge collector and remote control system architecture, endpoints, and database tables |
| `SYSTEM_ARCHITECTURE_COMPLETE.md` | Complete system architecture overview |
| `OPERATIONS_MANUAL_EN.md` | Operations and deployment guide |
| `replit.md` | Project summary and user preferences (this file) |