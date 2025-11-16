# BTC Mining Calculator System

## Overview
HashInsight Enterprise is an enterprise-grade web application designed for mining farm owners and clients. Its core purpose is to provide real-time Bitcoin mining profitability analysis, integrating real-time data, dual-algorithm verification, and multi-language support. The system offers comprehensive operational management, CRM, Web3 integration, technical analysis, professional reporting, and an AI-powered intelligence layer to optimize Bitcoin mining investments and provide transparency through advanced analytics.

## User Preferences
- **Communication style**: Simple, everyday language
- **Technical preferences**: Native Flask implementation, avoid over-complication
- **Design preferences**: BTC themed dark UI (#1a1d2e background, #f7931a gold accent)

## System Architecture

### UI/UX Decisions
The front-end uses Jinja2 with Bootstrap 5 for a mobile-first, responsive, BTC-themed dark design. Chart.js and CountUp.js are used for data visualization and animations. The system supports dynamic English and Chinese language switching.

### Technical Implementations
The system is built on a Flask backend using Blueprints for modularity, custom email authentication, session management, and an RBAC decorator system. SQLAlchemy with PostgreSQL handles data persistence, and Redis is used for caching and task queuing.

### Feature Specifications
- **Calculator Module**: Dual-algorithm profitability analysis for 19+ ASIC models, real-time BTC price/difficulty integration, ROI analysis, and batch calculation.
- **CRM System**: Flask-native CRM with lead management, deal pipeline, invoice generation, and asset management, including KPI cards and Chart.js visualizations.
- **System Monitoring**: Unified dashboard for real-time health checks, performance metrics, cache analysis, and alerts.
- **Technical Analysis Platform**: Server-side calculation of 10+ technical indicators, historical BTC price analysis, and intelligent signal aggregation.
- **Intelligence Layer**: Event-driven system with ARIMA forecasting for BTC price and difficulty, anomaly detection, power optimization, and intelligent ROI explanations.
- **User Management**: Admin backend for user creation, role assignment, RBAC, and access period management.
- **Web3 Configuration Wizard**: Secure interface for blockchain credential setup.
- **Hosting Services Module**: Real-time miner monitoring, single/batch miner creation APIs, operational ticketing, and comprehensive hosting management. This includes advanced device management for large-scale operations (6000+ miners) with a KPI dashboard, quick search, batch operations (Approve, Reject, Start, Shutdown, Change Status, Delete), single miner controls, and an operation audit trail. The device management UI features a smart pagination navigation system for 301 pages (20 miners per page) with boundary-aware page number display, First/Last/Previous/Next navigation buttons, page jump input with validation, and bilingual support (EN/中文). The pagination uses a delta=2 strategy to show the current page ±2 neighbors with ellipses for gaps, ensuring optimal UX for large-scale deployments.
- **Smart Power Curtailment Module**: Bilingual mining farm hosting management platform with automated scheduler for smart energy management. It supports manual curtailment and automatic miner recovery, prioritizing low-efficiency miners using a Performance Priority strategy. Features include a scheduler with background tasks, plan management UI, API endpoints, state management, and AI features like ARIMA forecasting and scenario planning.
- **Treasury Management**: BTC inventory tracking, cost basis analysis, cash coverage monitoring, sell strategy templates, and a backtesting engine.
- **Multi-Format Reporting**: Professional report generation in PDF, Excel, and PowerPoint, with role-specific dashboards.
- **Landing Page**: Enterprise-focused homepage with dynamic real-time statistics.

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
- **Chart.js**: Data visualization.
- **CountUp.js**: Number animation.

### Infrastructure
- **PostgreSQL**: Relational database (Replit hosted).
- **Redis**: In-memory data store (cache + task queue).
- **Python 3.9+**: Runtime.
- **Replit Platform**: Deployment and hosting.