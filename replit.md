# BTC Mining Calculator System

## Overview
The BTC Mining Calculator is a web application for Bitcoin mining profitability analysis, designed for mining site owners and their clients. It aims to be an enterprise-grade system for optimizing Bitcoin mining investments, offering real-time data integration, dual-algorithm validation, multilingual support (Chinese/English), and robust role-based access control. Key capabilities include mining operations management, customer relationship management (CRM), power management, technical analysis, and professional reporting.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The application is a modular Flask web application with a mobile-first design, supporting both English and Chinese.

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 (dark theme, golden accents).
- **UI Framework**: Bootstrap CSS and Bootstrap Icons.
- **JavaScript**: Vanilla JavaScript with Chart.js for data visualization.
- **Responsive Design**: Mobile-first, supporting screen sizes from 320px to 1200px+.
- **Multilingual Support**: Dynamic Chinese/English language switching across all UI elements, including comprehensive chart tooltip localization.
- **UI/UX Decisions**: Professional introduction page, clear navigation flow (Landing Page → Price Page → Login → Main Dashboard → Role-based Functions). Color-coded visual system for technical analysis (red, yellow, blue, green), improved visibility for navigation elements and disclaimers with enhanced contrast.

### Backend Architecture
- **Web Framework**: Flask, using Blueprint-based modular routing with **完全页面隔离架构**.
- **Modular Architecture**: **NEW** - Complete page isolation system where each module operates independently with its own routes, templates, and static resources. Modules communicate only through the database layer.
- **Module System**: 
  - **Calculator Module**: Independent mining calculator with own CSS/JS
  - **CRM Module**: Isolated customer management system
  - **Batch Module**: Standalone batch processing calculator
  - **Analytics Module**: Separate data analysis dashboard
  - **Broker Module**: Independent broker management system
- **Module Benefits**: 
  - Complete isolation - changes to module A don't affect module B
  - Independent static resources (CSS/JS) per module
  - Shared database for data consistency
  - Module-specific error handling
  - Easy to enable/disable modules
- **Authentication**: Custom email-based system with role management and secure password hashing.
- **API Integration**: Aggregates data from multiple sources with intelligent fallback mechanisms.
- **Background Services**: Scheduler for automated data collection.
- **Calculation Engine**: Dual-algorithm system for mining profitability analysis, supporting 17+ ASIC miner models, real-time data, ROI analysis, power curtailment analysis, and hashrate decay. Optimized for batch processing of large datasets.
- **Technical Analysis Platform**: Server-side calculation of indicators (RSI, MACD, SMA20/50, EMA12/26, Bollinger Bands, 30-day volatility) using historical BTC price, with signal interpretation and real-time market integration.
- **Permission Control System**: Advanced decorators and a comprehensive permission matrix for fine-grained, role-based access control.
- **User Management**: Admin interface for user creation, role assignment, and management.
- **Professional Report Generation**: Capabilities for generating reports, including ARIMA predictions and Monte Carlo simulations.
- **Data Consolidation**: Network snapshot data consolidated into a unified market_analytics table.
- **Caching System**: Intelligent caching implemented for major API endpoints.
- **Deployment Optimization**: Fast startup mode with deferred background services, lightweight health check endpoints, and deployment-ready configuration.
- **Personal Layer Selection System (L1-L4)**: Compact, integrated layer selector within Next Sell Price framework allowing users to choose personal risk-reward levels with real-time target price calculation and risk level display.
- **Data Integrity**: Comprehensive system to use real API data sources, replacing estimated values for user portfolio management, historical data, and technical indicators.
- **HashInsight Treasury Management**: Professional Bitcoin treasury platform for miners with BTC inventory, cost basis, cash coverage tracking, sell strategies, signal aggregation, and execution planning.
- **CRM System**: Handles customer lifecycle management, lead and deal tracking, and commission management.
- **Network Data Collection**: Automated historical data accumulation for BTC price, difficulty, and network hashrate from multiple sources.
- **Subscription Management**: Comprehensive plan management with tiered access and role-based exemptions.
- **Treasury Strategy Templates**: Pre-configured selling strategies including OPEX coverage, layered profit-taking, mining cycle, basis/funding, and volatility-triggered approaches.
- **Signal Aggregation System**: 10 sophisticated modules for advanced signal generation, including regime-aware adaptation, breakout exhaustion detection, support/resistance confluence, adaptive ATR layering, pattern target recognition, miner cycle analysis, derivatives pressure monitoring, microstructure execution optimization, bandit-sizing allocation, and ensemble aggregation scoring.
- **Backtesting Engine**: Historical strategy performance evaluation with professional metrics (Sharpe ratio, max drawdown, win rate).
- **订单执行优化系统**: Institutional-grade execution capabilities, including real-time slippage prediction, TWAP time window calculation, liquidity depth assessment, and market impact minimization.

### Database Architecture
- **Primary Database**: PostgreSQL.
- **ORM**: SQLAlchemy with declarative base.
- **Connection Management**: Connection pooling with automatic reconnection, health monitoring, and retry logic.
- **Data Models**: Comprehensive models for users, customers, mining data, network snapshots, and miner specifications.
- **Optimization**: Data storage optimized to a maximum of 10 data points per day, with cleanup policies.

## External Dependencies

### APIs
- **CoinWarz API**: Professional mining data and multi-coin profitability.
- **CoinGecko API**: Real-time cryptocurrency pricing and historical data.
- **Blockchain.info API**: Bitcoin network statistics.
- **IP-API**: Geographic location services for login tracking.
- **Ankr RPC**: Free Bitcoin RPC service for real-time blockchain data.
- **Gmail SMTP**: Email service for user verification and notifications.
- **Deribit API**: Trading data integration.
- **OKX API**: Trading data integration.
- **Binance API**: Trading data integration.

### Third-party Libraries
- **Flask**: Web application framework.
- **SQLAlchemy**: ORM for database interaction.
- **Requests**: HTTP client for API integrations.
- **NumPy/Pandas**: Mathematical calculations and data analysis.
- **Chart.js**: Frontend library for data visualization.
- **Bootstrap**: UI framework.
- **Werkzeug**: Secure password hashing.

### Infrastructure
- **PostgreSQL**: Relational database.
- **Python 3.9+**: Runtime environment.
- **Gunicorn**: Production WSGI server.