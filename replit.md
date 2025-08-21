# BTC Mining Calculator System

## Overview
The BTC Mining Calculator is a web application for Bitcoin mining profitability analysis, designed for mining site owners and their clients. It provides tools for mining operations, customer relationship management (CRM), and power management. Key capabilities include real-time data integration, highly accurate dual-algorithm validation for calculations, multilingual support (Chinese/English), and robust role-based access control. The project aims to be a reliable, enterprise-grade system for optimizing Bitcoin mining investments, offering a technical analysis platform and professional reporting.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes
**2025-08-21: Completed ROI Chart Tooltips with Full Multilingual Support**
- Successfully implemented comprehensive multilingual tooltip system for ROI charts
- Added algorithm income comparison showing both Static and Dynamic method revenues in dollars
- Enhanced chart.js with robust translation functionality supporting Chinese/English switching
- Added chart-specific translations to translations.py for consistent language experience
- Optimized tooltip content structure to avoid duplicate data display
- Fixed JavaScript language detection to work with global currentLang variable and multiple fallback methods
- Resolved tooltip callback function errors and information hierarchy issues
- User confirmed final implementation working correctly with proper language switching and clean data display

**2025-08-21: Fixed Network Difficulty Display Issue**
- Resolved critical bug where network difficulty displayed as 0.00T instead of correct value (129.43T)
- Root cause: calculator_clean.js incorrectly divided API-returned difficulty by 1e12
- API was returning correct pre-formatted values, but frontend was applying unnecessary conversion
- Fixed conversion logic in both main.js and calculator_clean.js
- Removed duplicate network statistics card that was causing UI confusion
- User confirmed fix is working correctly

## System Architecture
The application is a modular Flask web application with a mobile-first design.

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 (dark theme, golden accents).
- **UI Framework**: Bootstrap CSS and Bootstrap Icons.
- **JavaScript**: Vanilla JavaScript with Chart.js for data visualization.
- **Responsive Design**: Mobile-first, supporting screen sizes from 320px to 1200px+.
- **Multilingual Support**: Dynamic Chinese/English language switching across all UI elements.
- **UI/UX Decisions**: Professional introduction page, clear navigation flow (Landing Page → Price Page → Login → Main Dashboard → Role-based Functions). Color-coded visual system for technical analysis (red, yellow, blue, green).

### Backend Architecture
- **Web Framework**: Flask, using Blueprint-based modular routing.
- **Authentication**: Custom email-based system with role management and secure password hashing.
- **API Integration**: Aggregates data from multiple sources with intelligent fallback mechanisms.
- **Background Services**: Scheduler for automated data collection.
- **Calculation Engine**: Dual-algorithm system for mining profitability analysis, supporting 17+ ASIC miner models, real-time data, ROI analysis, power curtailment analysis, and hashrate decay. Optimized for batch processing of large datasets (5000+ miners).
- **Technical Analysis Platform**: Server-side calculation of indicators (RSI, MACD, SMA20/50, EMA12/26, Bollinger Bands, 30-day volatility) using historical BTC price, with signal interpretation and real-time market integration.
- **Permission Control System**: Advanced decorators and a comprehensive permission matrix for fine-grained, role-based access control.
- **User Management**: Admin interface for user creation, role assignment, and management.
- **Professional Report Generation**: Capabilities for generating reports, including ARIMA predictions and Monte Carlo simulations.
- **Data Consolidation**: Network snapshot data consolidated into a unified market_analytics table.
- **Caching System**: Intelligent caching implemented for major API endpoints.
- **Deployment Optimization**: Fast startup mode with deferred background services, lightweight health check endpoints, and deployment-ready configuration.

### Database Architecture
- **Primary Database**: PostgreSQL.
- **ORM**: SQLAlchemy with declarative base.
- **Connection Management**: Connection pooling with automatic reconnection, health monitoring, and retry logic.
- **Data Models**: Comprehensive models for users, customers, mining data, network snapshots, and miner specifications.

### Key Features
- **Mining Calculator Engine**: Core business logic for profitability calculations.
- **Authentication System**: Manages user access, Gmail SMTP bilingual email verification, role-based permissions, and session security.
- **CRM System**: Handles customer lifecycle management, lead and deal tracking, and commission management.
- **Network Data Collection**: Automated historical data accumulation for BTC price, difficulty, and network hashrate from multiple sources.
- **Multilingual System**: Provides dynamic Chinese/English interface support with comprehensive chart tooltip localization.
- **Subscription Management**: Comprehensive plan management with tiered access and role-based exemptions.

## External Dependencies

### APIs
- **CoinWarz API**: Professional mining data and multi-coin profitability.
- **CoinGecko API**: Real-time cryptocurrency pricing.
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