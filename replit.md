# BTC Mining Calculator System

## Overview

The BTC Mining Calculator is a comprehensive web application built with Flask that provides Bitcoin mining profitability analysis tools. The system serves mining site owners and their clients with specialized calculations for mining operations, customer relationship management, and power management features. It includes real-time data integration, dual-algorithm validation, multilingual support (Chinese/English), and role-based access control.

## System Architecture

The application follows a modular Flask web application architecture with clean separation of concerns:

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 dark theme
- **UI Framework**: Bootstrap CSS with Bootstrap Icons
- **JavaScript**: Vanilla JavaScript with Chart.js for visualization
- **Responsive Design**: Mobile-first responsive layout
- **Multilingual Support**: Dynamic Chinese/English switching

### Backend Architecture
- **Web Framework**: Flask with Blueprint-based modular routing
- **Authentication**: Custom email-based authentication with role management
- **API Integration**: Multi-source data aggregation with intelligent fallback
- **Background Services**: Automated data collection scheduler
- **Calculation Engine**: Dual-algorithm mining profitability system

### Database Architecture
- **Primary Database**: PostgreSQL with 10 core tables
- **ORM**: SQLAlchemy with declarative base
- **Connection Management**: Connection pooling with automatic reconnection
- **Data Models**: Comprehensive business models for users, customers, mining data, and network snapshots

## Key Components

### 1. Mining Calculator Engine (`mining_calculator.py`)
**Purpose**: Core business logic for mining profitability calculations
- Supports 10 different ASIC miner models with accurate specifications
- Dual-algorithm approach: API-based network hashrate vs difficulty-based calculations
- Real-time data integration from multiple sources
- ROI analysis for both host and client perspectives
- Power curtailment analysis with efficiency-based shutdown strategies
- Monthly and yearly profit projections

### 2. Authentication System (`auth.py`)
**Purpose**: User access control and session management
- Email-based verification system
- Role-based permissions (owner, admin, mining_site, guest)
- Session security with encrypted cookies
- Database-driven user access management
- Geographic login tracking with IP geolocation

### 3. CRM System (`crm_routes.py`, `mining_broker_routes.py`)
**Purpose**: Customer relationship and business management
- Complete customer lifecycle management
- Lead tracking with status progression
- Deal management with commission tracking
- Activity logging and customer communication history
- Mining broker business operations with specialized workflows

### 4. Network Data Collection (`services/network_data_service.py`)
**Purpose**: Automated historical data accumulation
- Real-time BTC price, difficulty, and network hashrate collection
- Automated snapshot recording during calculations
- Historical trend analysis and forecasting
- Multi-source data validation and health monitoring
- EST timezone-aware data recording

### 5. API Integration Layer (`coinwarz_api.py`)
**Purpose**: External data source management
- Primary: CoinWarz professional mining API
- Secondary: CoinGecko for BTC pricing
- Tertiary: Blockchain.info for network data
- Intelligent fallback mechanism with health monitoring
- Rate limit management and API status tracking

### 6. Multilingual System (`translations.py`)
**Purpose**: Complete Chinese/English interface support
- Dynamic language switching without page reload
- Comprehensive translation coverage for all UI elements
- Language preference persistence in user sessions
- Business-context aware translations

## Data Flow

### 1. User Authentication Flow
```
User Email Input → Email Verification → Role Assignment → Session Creation → Feature Access Control
```

### 2. Mining Calculation Flow
```
User Input Parameters → Real-time Data Fetch → Dual Algorithm Calculation → ROI Analysis → Result Visualization → Network Snapshot Recording
```

### 3. CRM Data Flow
```
Customer Creation → Lead Generation → Opportunity Tracking → Deal Closure → Commission Recording → Activity Logging
```

### 4. Network Data Collection Flow
```
Scheduled Collection → Multi-API Data Fetch → Data Validation → Database Storage → Trend Analysis → Forecasting
```

## External Dependencies

### APIs
- **CoinWarz API**: Professional mining data and multi-coin profitability
- **CoinGecko API**: Real-time cryptocurrency pricing
- **Blockchain.info API**: Bitcoin network statistics
- **IP-API**: Geographic location services for login tracking

### Third-party Libraries
- **Flask**: Web application framework
- **SQLAlchemy**: Database ORM and management
- **Requests**: HTTP client for API integration
- **NumPy/Pandas**: Mathematical calculations and data analysis
- **Chart.js**: Frontend data visualization
- **Bootstrap**: UI framework and responsive design

### Infrastructure
- **PostgreSQL**: Primary database storage
- **Python 3.9+**: Runtime environment
- **Gunicorn**: Production WSGI server

## Deployment Strategy

### Environment Configuration
- Database connection via `DATABASE_URL` environment variable
- Session security via `SESSION_SECRET` environment variable
- API keys managed through environment variables
- Configurable default values for network parameters

### Database Setup
- Automatic table creation on first run
- Migration-safe schema updates
- Connection pooling for performance
- Backup and recovery procedures

### Production Considerations
- Multi-source API redundancy for 99.9% uptime
- Automated data collection for historical analysis
- Role-based security for sensitive business operations
- Performance optimization with caching strategies
- Error handling and graceful degradation

### Monitoring and Maintenance
- API health monitoring with automatic failover
- Database performance tracking
- User activity logging and analysis
- Automated data quality validation

## Changelog
- June 28, 2025: **COMPLETED** - Analytics API system fully operational with 4/4 endpoints working (market-data, latest-report, technical-indicators, price-history), all external service dependencies removed, direct database integration implemented, average response time 0.27s
- June 28, 2025: **COMPLETED** - Full analytics system integration into main interface with owner-only widget, navigation menu access, modal windows for reports/indicators, auto-refresh every 5 minutes, and seamless multilingual support
- June 28, 2025: Added independent Bitcoin analytics engine with real-time data collection, technical analysis, and automated reporting system
- June 28, 2025: Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.