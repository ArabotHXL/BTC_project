# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application for mining farm owners and clients, providing real-time Bitcoin mining profitability analysis. It integrates real-time data, dual-algorithm verification, and multi-language support to optimize Bitcoin mining investments. Key features include comprehensive operational management, CRM, Web3 integration, technical analysis, and professional reporting, supporting over 19 ASIC miner models, ROI analysis, and an AI-powered intelligence layer. The system aims to provide transparency and optimize investments through advanced analytics and management tools.

## User Preferences
- **Communication style**: Simple, everyday language
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## System Architecture

### UI/UX Decisions
The front-end uses Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design (#1a1d2e background, #f7931a gold accent). Chart.js (v3 and v4.4.0) and CountUp.js v2.8.0 handle data visualization and animations. The system supports dynamic English and Chinese language switching.

### Technical Implementations
The system is built on a Flask backend with SQLAlchemy and PostgreSQL. Redis is used for caching and task queuing.
- **Backend**: Flask with Blueprints for modularity, custom email authentication, session management, and an RBAC decorator system.
- **Frontend**: Jinja2 templating, Bootstrap 5, Chart.js, and CountUp.js.
- **Database**: PostgreSQL with SQLAlchemy ORM, focusing on `user_access` for authentication and `users` for business information.

### Feature Specifications
- **Calculator Module**: Dual-algorithm profitability analysis for 19+ ASIC models, real-time BTC price/difficulty integration, ROI analysis, and batch calculation for 5000+ miners.
- **CRM System**: Flask-native CRM with 15 pages, 60+ API endpoints, 56+ animated KPI cards, and 42+ Chart.js visualizations, including lead management, deal pipeline, invoice generation, and asset management.
- **System Monitoring**: Unified dashboard for real-time health checks, performance metrics, cache analysis, and alerts across all modules.
- **Technical Analysis Platform**: Server-side calculation of 10+ technical indicators, historical BTC price analysis, and intelligent signal aggregation.
- **Intelligence Layer**: Event-driven system with ARIMA forecasting for BTC price and difficulty, anomaly detection, power optimization strategies (including curtailment), and intelligent ROI explanations.
- **User Management**: Admin backend for user creation, role assignment, RBAC, and access period management.
- **Web3 Configuration Wizard**: Secure interface for blockchain credential setup via MetaMask, Replit Secrets, or manual configuration, with bilingual support and security warnings.
- **Hosting Services Module**: Real-time miner monitoring, single/batch miner creation APIs, operational ticketing, and comprehensive hosting management.
- **CGMiner Real-Time Monitoring System** (Implemented: 2025-11-14): Production-ready system for real-time monitoring of 6,000+ Antminer devices via CGMiner API (TCP port 4028). Features include:
  - **14 CGMiner Telemetry Fields**: temperature_avg/max (°C), fan_speeds (JSON array), fan_avg (RPM), reject_rate (%), hardware_errors (count), cgminer_online (boolean), pool_url, pool_worker, uptime_seconds, hashrate_5s (TH/s), accepted/rejected_shares, last_seen (UTC timestamp)
  - **Background Scheduler**: Automated telemetry collection every 60 seconds using APScheduler with ThreadPoolExecutor (max_workers=2), SchedulerLock mechanism prevents multi-worker duplication, atexit cleanup for graceful shutdown, db.session.refresh for data consistency
  - **API Endpoints**: POST `/hosting/api/miners/<id>/telemetry` (merge-only updates, UTC timezone, 5-min debounce), GET `/hosting/api/miners/<id>/test-connection` (CGMiner validation), GET `/hosting/api/miners/<id>/telemetry-history` (24-hour historical data for Chart.js)
  - **UI Features**: Real-time status icons with color-coding (green=online, gray=offline, red=error), temperature display with color warnings (>85°C red, >75°C yellow), test/refresh buttons, bilingual tooltips (EN/CH), Bootstrap toast notifications
  - **Miner Detail Page**: Dedicated page with Chart.js v4.4.0 dual-axis charts (hashrate TH/s + temperature °C over 24 hours), responsive design, bilingual support, role-based access control (owner/admin/mining_site vs customer)
  - **Smart Alert System**: Automatic detection and badge display for critical issues - temperature >85°C (warning) or >90°C (critical), hashrate drop >20% vs miner_model.hashrate, offline >5 minutes. Color-coded badges (red=critical, yellow=warning) with count display and hover tooltips showing all alerts
  - **Technical Implementation**: CGMinerTester utility (tools/test_cgminer.py) with socket timeout (3s), JSON protocol parsing, services/cgminer_collector.py for batch telemetry collection, services/cgminer_scheduler.py for scheduling with production-safe lifecycle management
  - **MinerTelemetry Model**: Dedicated table for historical telemetry data with fields: hashrate, power_consumption, temperature, fan_speed, pool_url, pool_worker, accepted/rejected_shares, recorded_at (indexed)
  - **Performance**: Supports 5000+ concurrent miner operations, 3-second timeout per miner prevents blocking, batch database commits, skip maintenance status miners, efficient query patterns avoid N+1 issues
  - **Security**: Role-based permission checks with defensive validation (user_id null checks), CGMiner API uses read-only commands, no credentials stored in database, audit logging for all operations
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage monitoring, sell strategy templates, and backtesting engine.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint, with role-specific dashboards and automated reports.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics, unified HashInsight Enterprise branding, and highlights of Web3, AI, hosting, treasury, and security features.
- **Smart Power Curtailment Module**: AI-powered intelligent load management for mining farms. Includes performance scoring of miners, strategy selection (performance, customer priority, fair distribution, custom rules), AI Smart Prediction (24-hour ARIMA forecasting with Chart.js visualization for optimal curtailment based on BTC price, difficulty, and electricity pricing), scenario planning, and execution modes (auto/semi-auto/manual) with audit trails and emergency recovery. Supports 5000+ miner operations and integrates with CGMiner API.

### System Design Choices
- **Modularity**: Page-isolated architecture with database-centric module communication.
- **Authentication**: Custom email-based authentication with session management and RBAC.
- **API Integration Strategy**: Intelligent fallback, Stale-While-Revalidate (SWR) caching, batch API calls, and robust error handling.
- **Deployment**: Optimized for Replit platform using Gunicorn.

### Test Environments
- **20MW Mining Farm Test Environment** (Created: 2025-11-13):
  - **Site**: "HashPower MegaFarm 20MW" (ID: 5)
  - **Location**: Texas, USA - Enterprise Facility
  - **Capacity**: 25.0 MW total, 20.34 MW used
  - **Miners**: 6,000 total
    - 3,000x Antminer S19 Pro (Avg 109.95 TH/s, 3249.57W) = 9.749 MW
    - 3,000x Antminer S21 Pro (Avg 233.93 TH/s, 3530.28W) = 10.591 MW
  - **Total Hashrate**: ~1,039 TH/s
  - **Power Pricing**: Peak-Valley model
    - Peak: $0.12/kWh (10:00-22:00)
    - Valley: $0.04/kWh (22:00-10:00)
  - **Test Account**: test@test.com (role: mining_site)
  - **Curtailment AI Results** (validated 2025-11-13):
    - Hours to Curtail: 12 hours
    - Cost Saved: $27,858.12
    - Revenue Lost: $21,700.70
    - Net Benefit: +$6,157.44/day
  - **Purpose**: E2E validation of Smart Power Curtailment Module at enterprise scale

## External Dependencies

### API Integration
- **CoinWarz API**: Mining data and profitability.
- **CoinGecko API**: Real-time and historical cryptocurrency prices.
- **Blockchain.info API**: Bitcoin network statistics.
- **IP-API**: Geolocation services.
- **Ankr RPC**: Free Bitcoin RPC service.
- **Gmail SMTP**: Email services.
- **Deribit API**: Trading data.
- **OKX API**: Trading data.
- **Binance API**: Trading data.

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

### JavaScript Libraries
- **Bootstrap 5**: UI framework.
- **Bootstrap Icons**: Icons.
- **Chart.js v3 & v4.4.0**: Data visualization.
- **CountUp.js v2.8.0**: Number animation.

### Infrastructure
- **PostgreSQL**: Relational database (Replit hosted).
- **Redis**: In-memory data store (cache + task queue).
- **Python 3.9+**: Runtime.
- **Replit Platform**: Deployment and hosting.