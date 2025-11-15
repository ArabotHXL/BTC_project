# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application providing real-time Bitcoin mining profitability analysis for mining farm owners and clients. It integrates real-time data, dual-algorithm verification, and multi-language support to optimize Bitcoin mining investments. The system offers comprehensive operational management, CRM, Web3 integration, technical analysis, and professional reporting, supporting over 19 ASIC miner models, ROI analysis, and an AI-powered intelligence layer. Its primary goal is to provide transparency and optimize investments through advanced analytics and management tools.

## User Preferences
- **Communication style**: Simple, everyday language
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## System Architecture

### UI/UX Decisions
The front-end utilizes Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design. Chart.js (v3 and v4.4.0) and CountUp.js v2.8.0 are used for data visualization and animations. The system supports dynamic English and Chinese language switching.

### Technical Implementations
The system is built on a Flask backend using Blueprints for modularity, custom email authentication, session management, and an RBAC decorator system. SQLAlchemy with PostgreSQL handles data persistence, and Redis is employed for caching and task queuing.

### Feature Specifications
- **Calculator Module**: Dual-algorithm profitability analysis for 19+ ASIC models, real-time BTC price/difficulty integration, ROI analysis, and batch calculation.
- **CRM System**: Flask-native CRM with features like lead management, deal pipeline, invoice generation, and asset management, including numerous KPI cards and Chart.js visualizations.
- **System Monitoring**: Unified dashboard for real-time health checks, performance metrics, cache analysis, and alerts across all modules.
- **Technical Analysis Platform**: Server-side calculation of 10+ technical indicators, historical BTC price analysis, and intelligent signal aggregation.
- **Intelligence Layer**: Event-driven system with ARIMA forecasting for BTC price and difficulty, anomaly detection, power optimization strategies (including curtailment), and intelligent ROI explanations.
- **User Management**: Admin backend for user creation, role assignment, RBAC, and access period management.
- **Web3 Configuration Wizard**: Secure interface for blockchain credential setup via MetaMask, Replit Secrets, or manual configuration, with bilingual support.
- **Hosting Services Module**: Real-time miner monitoring, single/batch miner creation APIs, operational ticketing, and comprehensive hosting management. This includes a production-ready CGMiner Real-Time Monitoring System for 6,000+ Antminer devices, featuring telemetry collection, API endpoints for data access, UI features with real-time status and alerts, and a dedicated Miner Detail Page with historical data charting.
- **Smart Power Curtailment Module** (Enhanced: 2025-11-15): Comprehensive bilingual (English/Chinese) mining farm hosting management platform featuring smart energy management with automated scheduler. The system supports manual curtailment triggering (when power companies demand reduction) with automatic miner recovery, prioritizing shutdown of low-efficiency miners using Performance Priority strategy. Designed for large-scale deployments (6000+ miners).
  - **Architecture**: Service layer pattern (CurtailmentPlanService) separates business logic from controllers and scheduler. State machine: PENDING → EXECUTING → RECOVERY_PENDING → COMPLETED with automatic/manual recovery flows.
  - **Curtailment Scheduler** (services/curtailment_scheduler.py): Production-ready APScheduler-based system with background tasks (check_pending_plans every 1 min, check_recovery_plans every 1 min, send_upcoming_notifications every 5 min, heartbeat every 60s). SchedulerLock mechanism prevents multi-worker duplication. Automatic execution at scheduled_start_time, automatic recovery at scheduled_end_time (or manual recovery if end_time is null). Email notifications sent 15 minutes before execution using Gmail SMTP with retry logic and failure tracking. Graceful shutdown with atexit cleanup.
  - **Plan Management UI** (templates/hosting/curtailment_management.html): Bootstrap 5 tabs-based interface with Calculator tab (AI prediction, curtailment planner, strategy selection) and Schedule Management tab (create schedule form with start/end time + target kW + strategy, active plans cards with real-time countdown and execute/cancel/recover buttons, history table with status filter). Full bilingual support (EN/CH), real-time countdown timers updated every second, site-aware data loading integrated with site selector.
  - **API Endpoints** (modules/hosting/routes.py, namespace /hosting/api/curtailment/): POST /schedules (create plan: site_id, scheduled_start_time, target_power_reduction_kw, strategy_id), GET /schedules (list with filters: site_id, status, created_by_id), POST /schedules/{id}/execute (manually trigger, validates PENDING/APPROVED status), POST /schedules/{id}/recover (recover miners, validates EXECUTING/RECOVERY_PENDING status), DELETE /schedules/{id} (cancel plan, validates PENDING/APPROVED, changes to CANCELLED).
  - **State Management**: CurtailmentPlan.status flows PENDING (created) → EXECUTING (miners shutting down) → RECOVERY_PENDING (scheduled end reached) → COMPLETED (miners recovered). CANCELLED for manual cancellation before execution. Zero miners selected → immediately COMPLETED. All failures → rollback to PENDING.
  - **Execution Logic** (services/curtailment_plan_service.py): execute_plan() queries miners by strategy, updates HostingMiner.status to 'maintenance', tracks HostingMiner.actual_power for power reduction. recover_plan() queries miners in maintenance status, restores to 'active', recalculates power usage. Partial failure handling: Success if >0 miners affected, rollback to PENDING if all fail. CurtailmentExecution records log every execute/recover action with execution_action ('execute'/'recover'), miners_affected, power_affected_kw, executed_at.
  - **AI Features**: Performance Priority strategy (low hashrate/high power = shut down first), AI Smart Prediction (24-hour ARIMA forecasting with Chart.js visualization), scenario planning with cost/revenue analysis.
  - **Notification System**: Bilingual HTML email templates (Chinese/English) sent 15 minutes before plan execution. Retry logic with failure tracking (≥3 failures = warning). Prevents duplicate notifications using in-memory set.
  - **Database Models**: CurtailmentPlan (plan_name, site_id, scheduled_start_time, scheduled_end_time nullable, target_power_reduction_kw, strategy_id, status PlanStatus enum, created_by_id, created_at). CurtailmentExecution (plan_id, execution_action 'execute'/'recover', miners_affected, power_affected_kw, executed_at). Uses HostingMiner.status ('active', 'maintenance') and HostingMiner.actual_power fields.
  - **Performance**: Supports 5000+ miner operations, batch database commits, efficient query patterns, 3-second CGMiner API timeout.
  - **Security**: Role-based access control (mining_site/admin), defensive validation, audit trails for all operations.
  - **Usage Example**: 1) Navigate to Curtailment Management page, select mining site. 2) Use AI Prediction to analyze optimal curtailment schedule. 3) Create plan: Set start time (e.g., 2025-11-15 14:00), end time (optional, 2025-11-15 18:00), target reduction (500 kW), strategy (Performance Priority). 4) System sends email reminder 15 minutes before execution. 5) At start time: Scheduler automatically executes plan (shuts down low-efficiency miners). 6) At end time: Scheduler automatically recovers all miners (or manual recovery via button). 7) View execution history in History table with status badges and action buttons.
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage monitoring, sell strategy templates, and a backtesting engine.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint, with role-specific dashboards.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics and branding.

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