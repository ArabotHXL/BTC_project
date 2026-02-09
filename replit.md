# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application for Bitcoin mining farm owners and clients. It provides real-time Bitcoin mining profitability analysis, comprehensive operational management, and an AI-powered intelligence layer. The system aims to optimize Bitcoin mining investments, enhance transparency through dual-algorithm verification, real-time data integration, and multi-language support. Key capabilities include CRM, Web3 integration, technical analysis, professional reporting, and an advanced AI closed-loop system for recommendations and automated actions, with a vision to become the leading platform for Bitcoin mining optimization and management.

## User Preferences
- **Communication style**: Simple, everyday language (中文/English)
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## System Architecture

### UI/UX Decisions
The front-end uses Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design. It supports dynamic English and Chinese language switching via i18n.js and utilizes Chart.js and CountUp.js for data visualization and animations.

### Technical Implementations
The system is built on a Flask backend using Blueprints, custom email authentication, and robust session management. It incorporates an enterprise RBAC v2.0 system with 6 roles (Owner → Admin → Mining Site Owner → Operator → Client → Guest) and uses SQLAlchemy with PostgreSQL for data persistence. Redis is used for caching and task queuing. Performance-critical routes leverage SQL aggregation. Device Envelope Encryption provides zero-knowledge E2EE for miner credentials. A 4-layer telemetry storage system (raw_24h, live, history_5min, daily) is managed by APScheduler jobs. All command operations are routed through a single control plane API. The architecture includes a unified telemetry service, a feature gating system, and an integrated AI closed-loop system for recommendations, feedback, and auto-execution. It employs an Application Factory Pattern for robust environment configuration and supports Alembic for database migrations.

### Feature Specifications
- **Calculator Module**: Dual-algorithm profitability analysis, real-time BTC price/difficulty integration, ROI analysis, batch calculation.
- **CRM System**: Flask-native CRM with lead/deal management, invoicing, and asset management.
- **System Monitoring**: Unified dashboard for real-time health, performance, cache, and alerts.
- **Technical Analysis Platform**: Server-side calculation of 10+ indicators and historical BTC price analysis.
- **Intelligence Layer**: Event-driven system with ARIMA forecasting, anomaly detection, power optimization, and intelligent ROI explanations.
- **User Management**: Admin backend for user creation, role assignment, RBAC, and access period management.
- **Web3 Configuration Wizard**: Secure interface for blockchain credential setup.
- **Hosting Services Module**: Real-time miner monitoring, operational ticketing, hosting management, KPI dashboard, and White Label Branding.
- **Smart Power Curtailment Module**: Automated scheduler for energy management.
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage, sell strategy templates, and backtesting.
- **Multi-Format Reporting**: Professional reports (PDF, Excel, PowerPoint) and role-specific dashboards.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics.
- **Edge Collector Architecture**: Real-time miner telemetry via Python-based edge collector, cloud receiver API, management UI, alert rules engine, and bidirectional command control.
- **IP Scanner & Miner Discovery**: Automatic network scanning for Bitcoin miners.
- **Control Plane System**: Enterprise-grade system for large mining operations featuring zone partitioning, ABAC for customer isolation, dual-approval workflow, price plan versioning, 15-minute demand calculation, blockchain-style immutable audit event hash chain, robust remote command flow, and three-tier credential protection.
- **SOC2 Security Compliance Module**: Enterprise security features for SOC2 Type II compliance including log retention, login security, password policy, session security, security alerts, data access logging, and PII data masking.
- **AI Closed-Loop System**: Detects, diagnoses, recommends, approves, acts, audits, and learns from mining operations, integrating with a Control Plane v1 via RemoteCommand. Features include AI-powered alert diagnosis, ticket drafting, and curtailment advisory, with auto-execution based on multi-dimensional risk assessment and rule-based auto-approval.
- **Problem Registry & Anomaly Detection**: Centralized system for detecting, tracking, and resolving miner issues, including per-miner baselining, mode inference, fleet baseline analysis, and a health rules engine for anomaly detection.

### System Design Choices
The architecture emphasizes modularity with page-isolated components and database-centric communication. Authentication is custom email-based with session management and RBAC. API integrations follow intelligent fallback, Stale-While-Revalidate (SWR) caching, batch API calls, and robust error handling. The system is optimized for deployment on the Replit platform using Gunicorn.

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
- **eth_keys**: For secp256k1 operations in custom BIP32/BIP44 implementation.

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