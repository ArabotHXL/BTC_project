# BTC Mining Calculator System

## Overview
The BTC Mining Calculator is an enterprise-grade web application for Bitcoin mining profitability analysis, targeting mining site owners and their clients. It provides real-time data integration, dual-algorithm validation, multilingual support (Chinese/English), and robust role-based access control. The system aims to optimize Bitcoin mining investments through comprehensive operations management, CRM, power management, technical analysis, and professional reporting.

## 📚 Architecture Documentation
**完整系统架构文档**: 查看 [`SYSTEM_ARCHITECTURE_COMPLETE.md`](./SYSTEM_ARCHITECTURE_COMPLETE.md) 获取：
- 20个业务模块完整映射
- 50+数据库表结构
- 100+ API端点详细列表
- 外部集成（CoinGecko, Blockchain.info, Deribit, OKX, Binance等）
- Redis缓存策略和分布式锁
- CDC事件平台完整架构
- 数据流向图和技术栈

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The application is a modular Flask web application with a mobile-first design, supporting both English and Chinese, and employs a complete page isolation architecture.

### Frontend Architecture
-   **Template Engine**: Jinja2 with Bootstrap 5 (dark theme, golden accents).
-   **UI Framework**: Bootstrap CSS, Bootstrap Icons, Chart.js for data visualization.
-   **Responsive Design**: Mobile-first.
-   **Multilingual Support**: Dynamic Chinese/English language switching across all UI elements.
-   **UI/UX Decisions**: Professional introduction page, clear navigation, and color-coded visual systems for technical analysis.

### Backend Architecture
-   **Web Framework**: Flask, using Blueprint-based modular routing with complete page isolation.
-   **Modular Architecture**: Independent modules (Calculator, CRM, Batch, Analytics, Broker) communicate primarily through the database.
-   **Authentication**: Custom email-based system with role management and secure password hashing.
-   **API Integration**: Aggregates data from multiple sources with intelligent fallback.
-   **Background Services**: Scheduler for automated data collection.
-   **Calculation Engine**: Dual-algorithm system for mining profitability analysis, supporting 17+ ASIC miner models, real-time data, ROI analysis, power curtailment, and hashrate decay. Optimized for batch processing.
-   **Technical Analysis Platform**: Server-side calculation of indicators (RSI, MACD, SMA, EMA, Bollinger Bands, volatility) using historical BTC price.
-   **Permission Control System**: Advanced decorators and a comprehensive permission matrix for role-based access control (RBAC).
-   **User Management**: Admin interface for user creation, role assignment, and management.
-   **Professional Report Generation**: Capabilities for generating reports, including ARIMA predictions and Monte Carlo simulations.
-   **Caching System**: Intelligent caching for major API endpoints, including Stale-While-Revalidate (SWR) for performance.
-   **Deployment Optimization**: Fast startup, lightweight health checks, and production-ready configuration, separating scheduler and worker services.
-   **Personal Layer Selection System (L1-L4)**: Integrated layer selector for risk-reward levels with real-time target price calculation.
-   **Data Integrity**: Uses real API data sources for user portfolio management, historical data, and technical indicators.
-   **HashInsight Treasury Management**: Professional Bitcoin treasury platform.
-   **CRM System**: Handles customer lifecycle management, lead/deal tracking, and commission management.
-   **Network Data Collection**: Automated historical data accumulation for BTC price, difficulty, and network hashrate.
-   **Subscription Management**: Comprehensive plan management with tiered access.
-   **Treasury Strategy Templates**: Pre-configured selling strategies.
-   **Signal Aggregation System**: 10 sophisticated modules for advanced signal generation.
-   **Backtesting Engine**: Evaluates historical strategy performance.
-   **订单执行优化系统**: Institutional-grade execution capabilities.
-   **Intelligence Layer**: Event-driven smart layer for mining operations automation and predictive analytics, featuring an event-driven system (Outbox Pattern), task queue system (Redis Queue), intelligence modules (Forecast, Anomaly Detection, Power Optimizer, ROI Explainer), and enhanced cache management.
-   **SLO Monitoring System**: Tracks critical performance metrics like P95 TTR, success rate, and latency distribution with configurable alerts.

### Database Architecture
-   **Primary Database**: PostgreSQL.
-   **ORM**: SQLAlchemy with declarative base.
-   **Connection Management**: Connection pooling with automatic reconnection, health monitoring, and retry logic.
-   **Data Models**: Comprehensive models for users, customers, mining data, network snapshots, and miner specifications.
-   **Optimization**: Data storage optimized to a maximum of 10 data points per day, with cleanup policies.

### CRM System (Flask Native Implementation)
The CRM system is natively integrated into the Flask application, accessible at `/crm/` routes, using the main application's session-based authentication and PostgreSQL database.

**Architecture** (October 2025):
-   **Integration**: Native Flask blueprint registered at `/crm/` prefix
-   **Templates**: Jinja2 templates with Bootstrap 5 dark theme
-   **Authentication**: Session-based (shares main app's authentication)
-   **Database**: SQLAlchemy ORM with PostgreSQL

**🆕 CRM Complete Redesign (October 2025)**:
-   **Scope**: 15 pages fully redesigned with mining industry-specific features
-   **Scale**: 60+ API endpoints, 56+ animated KPI cards, 42+ Chart.js visualizations
-   **Quality**: 100% test coverage, 6 critical bugs fixed, enterprise-grade stability
-   **Dashboard**: dashboard_new.html with Chart.js & CountUp.js v2.8.0
-   **Design**: BTC-themed dark UI (#1a1d2e background, #f7931a gold accent)
-   **Features**: 
    - Real-time KPI animations (Customers, Deals, Hosting Capacity, Revenue)
    - Advanced visualizations (Revenue Trends, Sales Funnel, Capacity Distribution, Customer Geo-map)
    - Mining Analytics (Miner Models Ranking, Customer Capacity TOP 5, Equipment Status)
    - Smart Operations (Follow-ups, Urgent Alerts, Quick Actions, Commission Tracking)
-   **API Layer**: Comprehensive endpoints for dashboard KPIs, analytics, rankings, follow-ups, alerts, and broker management
-   **Bug Fixes**: CountUp.js NaN issues, Jinja2 template errors, API serialization bugs, form route customer object handling

**Core Models**:
-   **Customer**: Company information, contacts, mining capacity, electricity costs
-   **Lead**: Potential opportunities with status tracking (NEW, CONTACTED, QUALIFIED, NEGOTIATION, WON, LOST)
-   **Deal**: Transaction projects with value tracking, mining-specific fields, commission management
-   **Invoice**: Billing with status flow (draft, sent, paid, overdue, cancelled)
-   **Asset**: Equipment tracking (miners, hosting slots) with lifecycle management
-   **Activity**: Customer interaction history and notes

**CRM Features**:
-   **Dashboard**: Real-time statistics for customers, leads, deals, and revenue
-   **Customer Management**: Full CRUD operations with relationship tracking
-   **Lead Pipeline**: Visual workflow with status filtering and follow-up reminders
-   **Lead Detail Page** (October 2025): 
    - Vertical timeline view with activity tracking
    - Conversion prediction with gauge chart and smart algorithms
    - KPI cards (lead score 0-100, lead days, activity count)
    - CountUp.js v2.8.0 with multi-layer fallback protection
    - Fixed NaN display bugs via enhanced error handling and data preloading
-   **Deal Tracking**: Transaction management with mining farm broker support
-   **Invoice Management**: Billing with tax calculations and payment tracking
-   **Asset Management**: Equipment inventory with serial number tracking
-   **Activity Logging**: Complete interaction history across all entities

**Mining Broker Features**:
-   Commission tracking (percentage or fixed amount)
-   Mining farm deal management
-   Client investment and profit estimation
-   Monthly commission records with payment status

**Data Integrity**:
-   All routes enforce session-based authentication
-   Real database queries (no mock data)
-   Foreign key relationships between entities
-   Audit trail through Activity records

**Deprecated**: React/Node.js CRM proxy removed (October 2025) - replaced with native Flask implementation for better integration with main app authentication and simplified architecture.

## External Dependencies

### APIs
-   **CoinWarz API**: Mining data and multi-coin profitability.
-   **CoinGecko API**: Real-time cryptocurrency pricing and historical data.
-   **Blockchain.info API**: Bitcoin network statistics.
-   **IP-API**: Geographic location services.
-   **Ankr RPC**: Free Bitcoin RPC service.
-   **Gmail SMTP**: Email service.
-   **Deribit API**: Trading data integration.
-   **OKX API**: Trading data integration.
-   **Binance API**: Trading data integration.

### Third-party Libraries
-   **Flask**: Web application framework.
-   **SQLAlchemy**: ORM for database interaction.
-   **Requests**: HTTP client.
-   **NumPy/Pandas**: Mathematical calculations and data analysis.
-   **Chart.js**: Frontend data visualization.
-   **Bootstrap**: UI framework.
-   **Werkzeug**: Secure password hashing.
-   **RQ (Redis Queue)**: Task distribution.
-   **Statsmodels ARIMA**: Time series forecasting.
-   **PuLP**: Linear programming optimization.
-   **XGBoost**: Advanced ML predictions.
-   **Flask-Caching**: Performance optimization.
-   **Express**: Node.js web application framework.
-   **Prisma**: ORM for Node.js/TypeScript.
-   **React**: Frontend library.
-   **Vite**: Frontend build tool.
-   **Tailwind CSS**: Utility-first CSS framework.
-   **Zod**: Schema declaration and validation.

### Infrastructure
-   **PostgreSQL**: Relational database.
-   **Python 3.9+**: Runtime environment for Flask application.
-   **Node.js 18+**: Runtime environment for CRM platform.
-   **Redis**: In-memory data store for caching and task queues.
-   **Gunicorn**: Production WSGI server for Flask.
-   **Docker Compose**: Containerization for services.