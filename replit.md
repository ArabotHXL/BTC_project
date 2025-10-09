# BTC Mining Calculator System

## Overview
The BTC Mining Calculator is an enterprise-grade web application designed for mining farm owners and clients. It provides real-time profitability analysis for Bitcoin mining, integrating real-time data, dual-algorithm verification, and multi-language support (English and Chinese). The system aims to optimize Bitcoin mining investments through comprehensive operational management, CRM, power management, technical analysis, and professional reporting. Key capabilities include support for 17+ miner models, ROI analysis, CRM with 60+ API endpoints, unified system monitoring, and advanced technical analysis.

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
- **Calculator Module**: Dual-algorithm mining profitability analysis supporting 17+ ASIC miner models, real-time BTC price and difficulty integration, ROI analysis, and batch calculation.
- **CRM System**: A fully re-architected Flask-native CRM with 15 pages, 60+ API endpoints, 56+ animated KPI cards, and 42+ Chart.js visualizations. Includes real-time KPIs, sales funnels, capacity distribution, and specific features for lead management and mining brokers.
- **System Monitoring**: A unified dashboard providing real-time health checks, performance metrics (P95 latency, success rate), and alerts for all system modules, with automatic refreshes every 5 seconds.
- **Technical Analysis Platform**: Server-side calculation of indicators like RSI, MACD, SMA, EMA, and Bollinger Bands, historical BTC price analysis, and volatility calculations.
- **Intelligence Layer**: An event-driven system with a task queue for predictive analytics, anomaly detection, power optimization, and ROI interpretation.
- **User Management**: An Admin backend for user creation, role assignment, access period management, and system monitoring access.

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