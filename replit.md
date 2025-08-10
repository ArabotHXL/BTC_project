# BTC Mining Calculator System

## Overview

The BTC Mining Calculator is a comprehensive web application designed to provide Bitcoin mining profitability analysis. It offers specialized tools for mining operations, customer relationship management (CRM), and power management, catering to mining site owners and their clients. Key capabilities include real-time data integration, dual-algorithm validation for calculations, multilingual support (Chinese/English), and robust role-based access control. The project aims to deliver a reliable, enterprise-grade system for optimizing Bitcoin mining investments.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application is built upon a modular Flask web application architecture, emphasizing separation of concerns and a mobile-first design philosophy.

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 (dark theme)
- **UI Framework**: Bootstrap CSS and Bootstrap Icons
- **JavaScript**: Vanilla JavaScript with Chart.js for data visualization
- **Responsive Design**: Mobile-first approach, supporting 320px-1200px+ screen sizes.
- **Multilingual Support**: Dynamic Chinese/English language switching.

### Backend Architecture
- **Web Framework**: Flask, utilizing Blueprint-based modular routing.
- **Authentication**: Custom email-based system with role management.
- **API Integration**: Aggregates data from multiple sources with intelligent fallback mechanisms.
- **Background Services**: Scheduler for automated data collection.
- **Calculation Engine**: Dual-algorithm system for mining profitability analysis, incorporating specifications for 10 ASIC miner models, real-time data, ROI analysis (host and client), and power curtailment analysis.

### Database Architecture
- **Primary Database**: PostgreSQL
- **ORM**: SQLAlchemy with declarative base
- **Connection Management**: Connection pooling with automatic reconnection
- **Data Models**: Comprehensive models for users, customers, mining data, and network snapshots.

### Key Features and Technical Implementations
- **Mining Calculator Engine**: Core business logic for profitability calculations, supporting real-time data, ROI analysis, and power curtailment. The main interface has been simplified by removing complex power curtailment parameters, while advanced features remain accessible on a dedicated page.
- **Authentication System**: Manages user access, email-based verification, role-based permissions, and session security.
- **CRM System**: Handles customer lifecycle management, lead and deal tracking, commission management, and activity logging.
- **Network Data Collection**: Automated accumulation of historical data for BTC price, difficulty, and network hashrate, including multi-source validation.
- **Multilingual System**: Provides dynamic Chinese/English interface support across all UI elements, ensuring pure language display without mixed texts.

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

### Infrastructure
- **PostgreSQL**: Relational database.
- **Python 3.9+**: Runtime environment.
- **Gunicorn**: Production WSGI server.