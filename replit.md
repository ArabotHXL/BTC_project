# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application designed for mining farm owners and clients. It provides real-time profitability analysis for Bitcoin mining, integrating real-time data, dual-algorithm verification, and multi-language support (English and Chinese). The system aims to optimize Bitcoin mining investments through comprehensive operational management, CRM, Web3 integration, technical analysis, and professional reporting. Key capabilities include support for 19+ ASIC miner models, ROI analysis, full CRM with 60+ API endpoints, unified system monitoring, AI-powered intelligence layer, Web3 blockchain transparency, hosting services management, and treasury management.

## Recent Changes

### Smart Power Curtailment System (November 11, 2025)
- ✅ **Intelligent power curtailment management integrated** - Performance-based load reduction for mining operations
- **Database Schema**: 6 new models (MinerPerformanceScore, CurtailmentStrategy, CurtailmentPlan, CurtailmentExecution, CurtailmentNotification, PowerPriceConfig) + 8 enums (StrategyType, ExecutionMode, PlanStatus, ExecutionAction, ExecutionStatus, NotificationType, DeliveryStatus, PriceMode), optimized for 5000+ miner scalability with proper indexes and constraints
- **Performance Scoring Engine** (intelligence/performance_scorer.py): Real-time miner evaluation using weighted formula (hashrate efficiency 70% + power efficiency 20% + uptime 10%), batch SQL aggregation for large-scale operations, floor-bucket timestamp logic to prevent unique constraint violations, offline miner handling with zero-score records
- **Strategy Algorithms** (intelligence/curtailment_engine.py): 4 intelligent selection methods - (1) Pure performance priority (lowest scores first), (2) Customer priority with VIP protection toggle, (3) Fair distribution (proportional by customer), (4) Custom rules (uptime/maintenance/temperature filters). Economic impact analysis included
- **Curtailment APIs** (modules/hosting/routes.py): 8 production-ready endpoints - /calculate (compute optimal plan), /execute (create and run plan), /cancel (abort plan), /emergency-restore (recover all miners), /strategies (list site strategies), /kpis (real-time statistics), /history (execution audit trail), /sites/list (dropdown data). All with comprehensive parameter validation returning 400 for malformed inputs
- **Execution Engine** (intelligence/executor.py): Auto/semi-auto/manual modes, Plan-B strategy (updates miner status to 'curtailed' instead of physical shutdown), CGMiner API integration prepared for production PDU control, comprehensive audit trails via CurtailmentExecution records, transaction-safe rollback protection
- **UI Integration**: Dedicated curtailment management page at /hosting/host/curtailment with KPI dashboard (total miners, curtailed count, power saved), scenario planner wizard, execution history table, emergency restore button. Bilingual support (EN/中文), responsive design with hosting theme
- **Status**: All core functionality operational and architect-reviewed (database schema, performance scorer, strategy engine, APIs, executor, UI)

### Database Migration (November 1, 2025)
- ✅ **Successfully migrated to Replit PostgreSQL** - All data preserved with zero data loss
- **Migration Summary**: 78 tables, 9,750+ rows, 16 user accounts all intact
- **Verified Data**: CRM records (5 customers, 9 deals, 3 invoices), hosting miners (8), market analytics (4,836+ rows), technical indicators (2,264+ rows), miner models (42)
- **Security Enhancement**: Updated `export_database.py` utility to enforce environment variables for database credentials
- **Documentation**: Created `DATABASE_MIGRATION_SUCCESS.md` with complete migration details
- **Status**: All systems operational - login verified, database connection stable, data collectors running

## User Preferences
- **Communication style**: Simple, everyday language
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## System Architecture

### UI/UX Decisions
The front-end utilizes Jinja2 with Bootstrap 5, featuring a BTC-themed dark design (#1a1d2e background, #f7931a gold accent). It's built with a mobile-first, responsive approach ensuring a consistent visual language across cards, buttons, and tables. Data visualization is handled by Chart.js v3 and CountUp.js v2.8.0 for professional graphs and smooth animations. The system supports dynamic English and Chinese language switching.

### Technical Implementations
The system is built on a Flask backend with SQLAlchemy and PostgreSQL. Redis is used for caching and task queuing.
- **Backend**: Flask with Blueprint for modular routing, custom email authentication, session management, and an RBAC decorator system for fine-grained permissions.
- **Frontend**: Jinja2 templating, Bootstrap 5 for UI, Chart.js for data visualization, and CountUp.js for numerical animations.
- **Database**: PostgreSQL with SQLAlchemy ORM, focusing on `user_access` for authentication and roles, and `users` for business-related user information. Data optimization includes daily data point limits and automatic cleanup.

### Feature Specifications
- **Calculator Module**: Dual-algorithm mining profitability analysis supporting 19+ ASIC miner models (Antminer S19/S21 series, WhatsMiner M50/M53/M56 series, Avalon), real-time BTC price and difficulty integration, ROI analysis, and batch calculation supporting 5000+ miners.
- **CRM System**: A fully re-architected Flask-native CRM with 15 pages, 60+ API endpoints, 56+ animated KPI cards, and 42+ Chart.js visualizations. Includes real-time KPIs, sales funnels, capacity distribution, lead management, deal pipeline, invoice generation, payment tracking, asset management, and mining broker features.
- **System Monitoring**: A unified dashboard providing real-time health checks, performance metrics (P95 latency, success rate), cache performance analysis, and alerts for all system modules, with automatic refreshes every 5 seconds.
- **Technical Analysis Platform**: Server-side calculation of 10+ technical indicators (RSI, MACD, SMA, EMA, Bollinger Bands), historical BTC price analysis, volatility calculations, Fear & Greed Index, and intelligent signal aggregation from multiple modules.
- **Intelligence Layer**: An event-driven system with ARIMA forecasting for BTC price and difficulty, anomaly detection for hashrate/power/ROI, power optimization strategies with curtailment scheduling, and intelligent ROI explanation with actionable insights.
- **User Management**: An Admin backend for user creation, role assignment, RBAC permission control, access period management, and system monitoring access.
- **Web3 Configuration Wizard**: A secure configuration interface providing three methods for setting up blockchain credentials: (1) MetaMask wallet connection (browser-based, no key sharing), (2) Replit Secrets environment variables (secure server-side storage), and (3) Manual configuration guide (educational reference). Features complete bilingual support and comprehensive security warnings.
- **Hosting Services Module**: Real-time miner monitoring with telemetry tracking (hashrate, temperature, power, pool data), single/batch miner creation APIs, operational ticketing system, and comprehensive hosting management dashboard.
- **Treasury Management**: BTC inventory tracking with cost basis analysis, cash coverage monitoring, pre-configured sell strategy templates, signal aggregation from multiple modules, and backtesting engine for strategy evaluation.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint formats. Role-specific dashboards for Investors, Operations, and Finance teams. Automated weekly operations reports and monthly SLA reports.
- **Landing Page**: Updated enterprise-focused homepage (templates/landing.html) showcasing all live features with **dynamic real-time statistics**. The ASIC model count automatically queries the `miner_models` database table to display the current number of active miner models. Other statistics: 9+ data sources, 60+ API endpoints, 5000+ batch processing capacity. Features unified **HashInsight Enterprise** branding throughout (navbar, hero section, footer). Navigation includes Features anchor link, Login redirect, and bilingual language toggle (EN/中文) with smooth transitions and hover effects. Highlights Web3 integration, AI intelligence layer, hosting services, treasury management, and enterprise security features.
- **Smart Power Curtailment Module**: AI-powered intelligent load management system for mining farm operators. Core workflow: (1) Performance Scoring - continuous evaluation of all miners using weighted metrics (hashrate efficiency 70%, power efficiency 20%, uptime 10%), (2) Strategy Selection - choose from 4 algorithms (pure performance, customer priority with VIP protection, fair distribution, custom rules), (3) Scenario Planning - input target power reduction to receive optimized shutdown recommendations with economic impact analysis (revenue lost vs. cost saved), (4) Execution - deploy plans in auto/semi-auto/manual modes with comprehensive audit trails, (5) Emergency Recovery - one-click restore all curtailed miners. Key features: support for 5000+ miner operations, batch SQL optimization, CGMiner API integration (Plan-B fallback to status updates), transaction-safe rollback protection, real-time KPI dashboard, execution history with full audit trails, bilingual UI (/hosting/host/curtailment). Role-based access control: mining_site_owner/admin can create and execute plans, operators can execute pre-approved plans. Database-driven with 6 models and 8 enums ensuring referential integrity and comprehensive state management.

### System Design Choices
- **Modularity**: Completely page-isolated architecture with modules communicating via the database.
- **Authentication**: Custom email-based authentication with session management and RBAC for authorization, using the `user_access` table as the primary source for credentials and permissions.
- **API Integration Strategy**: Features intelligent fallback with multiple data sources, Stale-While-Revalidate (SWR) caching, batch API calls, and robust error handling.
- **Deployment**: Optimized for the Replit platform, using Gunicorn for production WSGI serving.

## External Dependencies

### API Integration
- **CoinWarz API**: Mining data and multi-currency profitability.
- **CoinGecko API**: Real-time cryptocurrency prices and historical data.
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
- **Chart.js v3**: Data visualization.
- **CountUp.js v2.8.0**: Number animation.

### Infrastructure
- **PostgreSQL**: Relational database (Replit hosted).
- **Redis**: In-memory data store (cache + task queue).
- **Python 3.9+**: Runtime.
- **Replit Platform**: Deployment and hosting.