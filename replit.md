# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application designed for mining farm owners and clients. It provides real-time profitability analysis for Bitcoin mining, integrating real-time data, dual-algorithm verification, and multi-language support (English and Chinese). The system aims to optimize Bitcoin mining investments through comprehensive operational management, CRM, Web3 integration, technical analysis, and professional reporting. Key capabilities include support for 19+ ASIC miner models, ROI analysis, full CRM with 60+ API endpoints, unified system monitoring, AI-powered intelligence layer, Web3 blockchain transparency, hosting services management, and treasury management.

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
- **Landing Page**: Updated enterprise-focused homepage (templates/landing.html) showcasing all live features with accurate statistics: 19+ ASIC models, 9+ data sources, 60+ API endpoints, 5000+ batch processing capacity. Highlights Web3 integration, AI intelligence layer, hosting services, treasury management, and enterprise security features.

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