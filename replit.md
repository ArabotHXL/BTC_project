# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application designed for Bitcoin mining farm owners and clients. It provides real-time Bitcoin mining profitability analysis, integrates real-time data, offers dual-algorithm verification, and supports multiple languages. The system delivers comprehensive operational management, CRM, Web3 integration, technical analysis, professional reporting, and an AI-powered intelligence layer to optimize Bitcoin mining investments and enhance transparency.

## User Preferences
- **Communication style**: Simple, everyday language (中文/English)
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## System Architecture

### UI/UX Decisions
The front-end utilizes Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design. Chart.js and CountUp.js are used for data visualization and animations. Dynamic English and Chinese language switching is supported with 859+ translation keys and instant no-refresh updates via client-side i18n.js.

### Technical Implementations
The system is built on a Flask backend using Blueprints for modularity. It features custom email authentication, session management, and an enterprise RBAC v2.0 system with 6 roles and 40+ modules. SQLAlchemy with PostgreSQL handles data persistence, and Redis is used for caching and task queuing. Performance-critical routes use SQL aggregation to avoid N+1 query patterns. Device Envelope Encryption provides zero-knowledge E2EE for miner credentials using X25519 Sealed Box and AES-256-GCM. A 4-layer telemetry storage system (raw_24h, live, history_5min, daily) with APScheduler jobs manages high-volume mining data within storage limits.

### Feature Specifications
- **Calculator Module**: Dual-algorithm profitability analysis for 19+ ASIC models, real-time BTC price/difficulty integration, ROI analysis, and batch calculation.
- **CRM System**: Flask-native CRM with deep integration to hosting services, providing lead management, deal pipeline, invoice generation, and asset management.
- **System Monitoring**: Unified dashboard for real-time health checks, performance metrics, cache analysis, and alerts.
- **Technical Analysis Platform**: Server-side calculation of 10+ technical indicators and historical BTC price analysis.
- **Intelligence Layer**: Event-driven system with ARIMA forecasting for BTC price/difficulty, anomaly detection, power optimization, and intelligent ROI explanations.
- **User Management**: Admin backend for user creation, role assignment, RBAC, and access period management.
- **Web3 Configuration Wizard**: Secure interface for blockchain credential setup.
- **Hosting Services Module**: Real-time miner monitoring, single/batch miner creation APIs, operational ticketing, comprehensive hosting management, KPI dashboard, and quick search. Includes a detailed Single Miner Dashboard. Supports White Label Branding.
- **Smart Power Curtailment Module**: Bilingual platform with automated scheduler for smart energy management, supporting manual curtailment and automatic miner recovery based on a Performance Priority strategy, integrated with AI forecasting. Features Temperature-Based Intelligent Frequency Control for thermal protection.
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage monitoring, sell strategy templates, and a backtesting engine.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint, with role-specific dashboards.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics.
- **Edge Collector Architecture**: Enables real-time miner telemetry collection from on-premises mining farms to cloud infrastructure, including a Python-based edge collector, a cloud receiver API, and a management UI. Features an alert rules engine and a bidirectional command control system. Includes auto-creation of `hosting_miners` records.
- **IP Scanner & Miner Discovery**: Automatic network scanning to discover Bitcoin miners via CGMiner API, supporting IP ranges and CIDR notation.

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

## Recent Changes (2026-01-02)

### RBAC Role Mapping Fix
- Added `site_manager` role mapping to `MINING_SITE_OWNER` in `common/rbac.py`
- This fixes access control for users with `site_manager` role in database
- Without this mapping, `site_manager` users were defaulting to `Guest` permissions

### Power Consumption Center (电力监控中心)
- New page: `/hosting/host/power_consumption` replaces the old monitoring page
- **Core Statistics**: Real-time power (kW), daily consumption (kWh), monthly cost estimate ($), curtailment savings ($)
- **Electricity Rate Management**: Site-by-site rate configuration with edit modal, supports time-of-use pricing (peak/off-peak/normal)
- **Power Trend Charts**: 24H/7D/30D consumption visualization with Chart.js
- **Power Bills**: Generate monthly electricity bills per customer
- **Power Alerts**: Peak hour warnings, abnormal consumption detection, price change notifications
- **Historical Comparison**: Month-over-Month (MoM) and Year-over-Year (YoY) analysis
- **Contract Tracking**: Contracted capacity vs actual usage with over-limit warnings
- **Carbon Emissions**: Calculate carbon footprint based on electricity source (hydro/solar/wind/nuclear/grid/coal)
- **Curtailment Savings**: Smart curtailment effect statistics

### Power APIs (11 endpoints)
- GET `/hosting/api/power/overview` - Power overview data
- GET `/hosting/api/power/consumption` - Consumption with time range
- GET/PUT `/hosting/api/power/rates` - Electricity rate management
- GET `/hosting/api/power/curtailment-savings` - Curtailment savings
- GET/POST `/hosting/api/power/bills` - Power bill management
- GET `/hosting/api/power/alerts` - Power alerts
- GET `/hosting/api/power/contracts` - Contract tracking
- GET `/hosting/api/power/carbon` - Carbon emissions
- GET `/hosting/api/power/comparison` - Historical comparison

### Power Aggregation Scheduler (电力聚合调度器)
- New scheduler: `services/power_aggregation_scheduler.py` using APScheduler
- Uses `SchedulerLock` mechanism to prevent duplicate workers in multi-instance environments
- **Hourly aggregation**: Runs every hour to calculate site-level energy consumption from miner telemetry
- **Daily aggregation**: Runs at 00:30 to aggregate hourly data into daily summaries
- **Monthly aggregation**: Runs on 1st of each month at 01:00 to create monthly records
- **Carbon emission factors**: hydro (0.024), solar (0.048), wind (0.011), nuclear (0.012), natural_gas (0.41), coal (0.82), grid (0.42) kg CO2/kWh
- **Data models**: `SiteEnergyHourly`, `SiteEnergyDaily`, `SiteEnergyMonthly` with proper unique constraints and indexes

### Previous Changes (2026-01-01)

### API Optimization
- Optimized miner list API (`/hosting/api/miners`) with joinedload() to eliminate N+1 queries
- Aggregated 3 count queries into 1 for better performance
- Added fast estimation mode (default) vs full metrics mode (`?include_metrics=true`)

### Miner Model Filter
- Added "Miner Model" dropdown filter to `/hosting/host/devices` page
- Created `/hosting/api/miner-models` API endpoint for populating the dropdown
- Removed restrictive `@requires_module_access` decorator from the endpoint - now only requires login since model list is public lookup data
- Added `loadModelsForDropdown()` JavaScript function with DOMContentLoaded initialization

### Memory Optimization Notes
- Server uses minimal gunicorn settings (1 worker) to conserve memory
- Background schedulers use SchedulerLock to prevent duplicate workers
- For production stability, consider Reserved VM deployment with more RAM