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

### Language System Enhancements
- **434+ Translation Keys**: Comprehensive bilingual support across all modules (homepage, CRM, hosting, calculator, etc.)
- **Session-Based Persistence**: Language preference stored in Flask session with browser auto-detection fallback
- **Security-Validated Switching**: Language endpoint validates redirect URLs against allowed domains

### CRM-Hosting Integration
- **Deep Integration Architecture**: Customer.email ↔ UserAccess.email → UserMiner relationship enables mine owners to view customer mining operations directly in CRM
- **4 API Endpoints**: `/crm/api/hosting/customer-miners`, `/crm/api/hosting/customer-stats`, `/crm/api/hosting/customer-performance`, `/crm/api/hosting/customer-revenue`
- **Real-Time Data Display**: CRM customer detail pages show live miner status, hashrate, and revenue data

## System Architecture

### UI/UX Decisions
The front-end utilizes Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design. Chart.js and CountUp.js are used for data visualization and animations. Dynamic English and Chinese language switching is supported with 434+ translation keys.

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