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
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage monitoring, sell strategy templates, and backtesting engine.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint, with role-specific dashboards and automated reports.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics, unified HashInsight Enterprise branding, and highlights of Web3, AI, hosting, treasury, and security features.
- **Smart Power Curtailment Module**: AI-powered intelligent load management for mining farms. Includes performance scoring of miners, strategy selection (performance, customer priority, fair distribution, custom rules), AI Smart Prediction (24-hour ARIMA forecasting with Chart.js visualization for optimal curtailment based on BTC price, difficulty, and electricity pricing), scenario planning, and execution modes (auto/semi-auto/manual) with audit trails and emergency recovery. Supports 5000+ miner operations and integrates with CGMiner API.

### System Design Choices
- **Modularity**: Page-isolated architecture with database-centric module communication.
- **Authentication**: Custom email-based authentication with session management and RBAC.
- **API Integration Strategy**: Intelligent fallback, Stale-While-Revalidate (SWR) caching, batch API calls, and robust error handling.
- **Deployment**: Optimized for Replit platform using Gunicorn.

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