# BTC Mining Calculator System

## Overview

The BTC Mining Calculator is a comprehensive web application designed for Bitcoin mining profitability analysis. It provides specialized tools for mining operations, customer relationship management (CRM), and power management, targeting mining site owners and their clients. Key capabilities include real-time data integration, dual-algorithm validation for calculations ensuring high accuracy (99%+), multilingual support (Chinese/English), and robust role-based access control. The project aims to deliver a reliable, enterprise-grade system for optimizing Bitcoin mining investments, complete with a fully functional technical analysis platform and professional reporting capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### UI Improvements (August 12, 2025)
- Enhanced batch calculator quota indicator with compact #/# format display
- Optimized size and layout for better visual balance (120-160px width)
- Added real-time quota tracking with progress bar visualization
- Improved user experience with clear remaining capacity indicators

## System Architecture

The application is built upon a modular Flask web application architecture, emphasizing separation of concerns and a mobile-first design philosophy.

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 (dark theme, golden accents).
- **UI Framework**: Bootstrap CSS and Bootstrap Icons.
- **JavaScript**: Vanilla JavaScript with Chart.js for data visualization.
- **Responsive Design**: Mobile-first approach, supporting 320px-1200px+ screen sizes.
- **Multilingual Support**: Dynamic Chinese/English language switching for all UI elements and dynamic content.
- **UI/UX Decisions**: Professional introduction page at root path with clear navigation flow (Landing Page → Price Page → Login → Main Dashboard → Role-based Functions). Color-coded visual system for technical analysis (red=危险/看跌, yellow=警告/趋势, blue=正常, green=安全/看涨).

### Backend Architecture
- **Web Framework**: Flask, utilizing Blueprint-based modular routing.
- **Authentication**: Custom email-based system with robust role management (Owner, Manager, Mining_site, Guest) and secure password hashing.
- **API Integration**: Aggregates data from multiple sources with intelligent fallback mechanisms.
- **Background Services**: Scheduler for automated data collection.
- **Calculation Engine**: Verified dual-algorithm system (99%+ accuracy) for mining profitability analysis, incorporating specifications for 17+ ASIC miner models, real-time data, ROI analysis (host and client), and power curtailment analysis.
- **Technical Analysis Platform**: Server-side calculation of indicators (RSI, MACD, SMA20/50, EMA12/26, Bollinger Bands, 30-day volatility) using historical BTC price records, with intelligent signal interpretation and real-time market integration.
- **Permission Control System**: Advanced decorators and a comprehensive permission matrix for fine-grained, role-based access control to critical routes and data.
- **User Management**: Admin interface for user creation, role assignment, and management with security improvements.
- **Professional Report Generation**: Capabilities for generating professional reports, including ARIMA predictions and Monte Carlo simulations.

### Database Architecture
- **Primary Database**: PostgreSQL.
- **ORM**: SQLAlchemy with declarative base.
- **Connection Management**: Connection pooling with automatic reconnection.
- **Data Models**: Comprehensive models for users, customers, mining data, and network snapshots.

### Key Features and Technical Implementations
- **Mining Calculator Engine**: Core business logic for profitability calculations.
- **Authentication System**: Manages user access, email-based verification, role-based permissions, and session security.
- **CRM System**: Handles customer lifecycle management, lead and deal tracking, and commission management.
- **Network Data Collection**: Automated accumulation of historical data for BTC price, difficulty, and network hashrate from multiple sources.
- **Multilingual System**: Provides dynamic Chinese/English interface support across all UI elements.

## External Dependencies

### APIs
- **CoinWarz API**: Primary source for professional mining data and multi-coin profitability.
- **CoinGecko API**: Real-time cryptocurrency pricing.
- **Blockchain.info API**: Bitcoin network statistics.
- **IP-API**: Geographic location services for login tracking.

### Third-party Libraries
- **Flask**: Web application framework.
- **SQLAlchemy**: ORM for database interaction.
- **Requests**: HTTP client for API integrations.
- **NumPy/Pandas**: Used for mathematical calculations and data analysis.
- **Chart.js**: Frontend library for data visualization.
- **Bootstrap**: UI framework.
- **Werkzeug**: For secure password hashing.

### Infrastructure
- **PostgreSQL**: Relational database.
- **Python 3.9+**: Runtime environment.
- **Gunicorn**: Production WSGI server.