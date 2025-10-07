# BTC Mining Calculator System

## Overview
The BTC Mining Calculator is an enterprise-grade web application designed for Bitcoin mining profitability analysis. It serves mining site owners and their clients by offering real-time data integration, dual-algorithm validation, multilingual support (Chinese/English), and robust role-based access control. The system focuses on optimizing Bitcoin mining investments through mining operations management, customer relationship management (CRM), power management, technical analysis, and professional reporting.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The application is a modular Flask web application with a mobile-first design, supporting both English and Chinese. It employs a complete page isolation architecture where each module operates independently.

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 (dark theme, golden accents).
- **UI Framework**: Bootstrap CSS and Bootstrap Icons, Chart.js for data visualization.
- **Responsive Design**: Mobile-first, supporting various screen sizes.
- **Multilingual Support**: Dynamic Chinese/English language switching across all UI elements, including chart tooltips.
- **UI/UX Decisions**: Professional introduction page, clear navigation flow, and color-coded visual systems for technical analysis.

### Backend Architecture
- **Web Framework**: Flask, using Blueprint-based modular routing with complete page isolation.
- **Modular Architecture**: Independent modules (Calculator, CRM, Batch, Analytics, Broker) with their own routes, templates, and static resources, communicating only through the database.
- **Authentication**: Custom email-based system with role management and secure password hashing.
- **API Integration**: Aggregates data from multiple sources with intelligent fallback mechanisms.
- **Background Services**: Scheduler for automated data collection.
- **Calculation Engine**: Dual-algorithm system for mining profitability analysis, supporting 17+ ASIC miner models, real-time data, ROI analysis, power curtailment, and hashrate decay. Optimized for batch processing.
- **Technical Analysis Platform**: Server-side calculation of indicators (RSI, MACD, SMA, EMA, Bollinger Bands, volatility) using historical BTC price, with signal interpretation and real-time market integration.
- **Permission Control System**: Advanced decorators and a comprehensive permission matrix for role-based access control.
- **User Management**: Admin interface for user creation, role assignment, and management.
- **Professional Report Generation**: Capabilities for generating reports, including ARIMA predictions and Monte Carlo simulations.
- **Caching System**: Intelligent caching for major API endpoints.
- **Deployment Optimization**: Fast startup mode, lightweight health checks, and deployment-ready configuration.
- **Personal Layer Selection System (L1-L4)**: Integrated layer selector for risk-reward levels with real-time target price calculation.
- **Data Integrity**: Uses real API data sources for user portfolio management, historical data, and technical indicators.
- **HashInsight Treasury Management**: Professional Bitcoin treasury platform with BTC inventory, cost basis, cash coverage, sell strategies, signal aggregation, and execution planning.
- **CRM System**: Handles customer lifecycle management, lead/deal tracking, and commission management.
- **Network Data Collection**: Automated historical data accumulation for BTC price, difficulty, and network hashrate.
- **Subscription Management**: Comprehensive plan management with tiered access.
- **Treasury Strategy Templates**: Pre-configured selling strategies (OPEX coverage, layered profit-taking, mining cycle, basis/funding, volatility-triggered).
- **Signal Aggregation System**: 10 sophisticated modules for advanced signal generation, including regime-aware adaptation, breakout exhaustion detection, and ensemble aggregation scoring.
- **Backtesting Engine**: Evaluates historical strategy performance with professional metrics.
- **订单执行优化系统**: Institutional-grade execution capabilities, including real-time slippage prediction, TWAP calculation, liquidity depth assessment, and market impact minimization.
- **Intelligence Layer**: Event-driven smart layer for mining operations automation and predictive analytics, featuring an event-driven system (Outbox Pattern), task queue system (Redis Queue), intelligence modules (Forecast, Anomaly Detection, Power Optimizer, ROI Explainer), and enhanced cache management.

### Database Architecture
- **Primary Database**: PostgreSQL.
- **ORM**: SQLAlchemy with declarative base.
- **Connection Management**: Connection pooling with automatic reconnection, health monitoring, and retry logic.
- **Data Models**: Comprehensive models for users, customers, mining data, network snapshots, and miner specifications.
- **Optimization**: Data storage optimized to a maximum of 10 data points per day, with cleanup policies.

## External Dependencies

### APIs
- **CoinWarz API**: Mining data and multi-coin profitability.
- **CoinGecko API**: Real-time cryptocurrency pricing and historical data.
- **Blockchain.info API**: Bitcoin network statistics.
- **IP-API**: Geographic location services.
- **Ankr RPC**: Free Bitcoin RPC service.
- **Gmail SMTP**: Email service.
- **Deribit API**: Trading data integration.
- **OKX API**: Trading data integration.
- **Binance API**: Trading data integration.

### Third-party Libraries
- **Flask**: Web application framework.
- **SQLAlchemy**: ORM for database interaction.
- **Requests**: HTTP client.
- **NumPy/Pandas**: Mathematical calculations and data analysis.
- **Chart.js**: Frontend data visualization.
- **Bootstrap**: UI framework.
- **Werkzeug**: Secure password hashing.
- **RQ (Redis Queue)**: Task distribution.
- **Statsmodels ARIMA**: Time series forecasting.
- **PuLP**: Linear programming optimization.
- **XGBoost**: Advanced ML predictions.
- **Flask-Caching**: Performance optimization.

### Infrastructure
- **PostgreSQL**: Relational database.
- **Python 3.9+**: Runtime environment.
- **Gunicorn**: Production WSGI server.