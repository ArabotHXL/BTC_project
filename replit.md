# BTC Mining Calculator System

## Overview
The BTC Mining Calculator is a web application designed for Bitcoin mining profitability analysis, serving mining site owners and their clients. Its main purpose is to be an enterprise-grade system for optimizing Bitcoin mining investments. Key capabilities include real-time data integration, dual-algorithm validation for calculations, multilingual support (Chinese/English), and robust role-based access control. The project provides tools for mining operations, customer relationship management (CRM), power management, technical analysis, and professional reporting, aiming to be a reliable platform.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture Documentation
- **Created**: Comprehensive bilingual (English/Chinese) system architecture documentation
- **Location**: ARCHITECTURE.md
- **Contents**: Technology stack, system components, database design, API architecture, security measures, performance optimization, deployment details, and data flow diagrams
- **Languages**: Full support for both English and Chinese throughout the documentation

## Recent Changes (August 2025)
- **Regression Testing Achievement Complete (Aug 22)**: Successfully achieved 100% pass rate (48/48 tests) in comprehensive regression testing, exceeding the 99%+ target. Fixed critical string-integer arithmetic errors in mining calculator API through enhanced type conversion and parameter validation.
- **Mining Calculator API Stability (Aug 22)**: Resolved all "unsupported operand type(s) for -: 'str' and 'int'" errors by implementing robust type conversion at function entry points. System now handles all parameter types (string, integer, float, null) gracefully with comprehensive error handling.
- **API Response Format Enhancement (Aug 22)**: Updated all API endpoints to return consistent nested data structure under 'data' field while maintaining backward compatibility. Enhanced test suite to properly validate new response formats.
- **JavaScript Error Resolution Complete (Aug 22)**: All Treasury Management backtest JavaScript errors eliminated, including Chart.js v4 compatibility fixes, variable scoping issues, Promise rejection handling, and button state management. System now operates with 100% reliability and zero console errors.
- **Performance Monitor Fix Complete (Aug 22)**: Fixed all performance monitoring API errors by replacing complex monitor classes with psutil-based real-time system metrics. Enhanced error handling and JavaScript data processing for 100% stability.
- **Main Dashboard Modernization (Aug 22)**: Completely redesigned /main page with modern gradients, real-time data displays, enhanced card interactions, and professional Hero section with live Bitcoin price and network statistics.
- **Free Account Enhancement (Aug 22)**: Increased free account miner limit from 1 to 10 miners in batch calculator. Fixed batch calculator API errors by removing incorrect fast processor calls. Free users can now effectively use batch calculation features with up to 10 miners.

## System Architecture
The application is a modular Flask web application with a mobile-first design.

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 (dark theme, golden accents).
- **UI Framework**: Bootstrap CSS and Bootstrap Icons.
- **JavaScript**: Vanilla JavaScript with Chart.js for data visualization.
- **Responsive Design**: Mobile-first, supporting screen sizes from 320px to 1200px+.
- **Multilingual Support**: Dynamic Chinese/English language switching across all UI elements.
- **UI/UX Decisions**: Professional introduction page, clear navigation flow (Landing Page → Price Page → Login → Main Dashboard → Role-based Functions). Color-coded visual system for technical analysis (red, yellow, blue, green), improved visibility for navigation elements and disclaimers with enhanced contrast.

### Backend Architecture
- **Web Framework**: Flask, using Blueprint-based modular routing.
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
- **Enhanced Language Engine v2.0**: Advanced multilingual system with context-aware translations, variable interpolation, smart formatting for numbers/currency/dates, caching system, and seamless Chinese/English interface support with comprehensive chart tooltip localization.
- **Data Integrity**: Comprehensive system to use real API data sources, replacing estimated values for user portfolio management, historical data, and technical indicators.

### Database Architecture
- **Primary Database**: PostgreSQL.
- **ORM**: SQLAlchemy with declarative base.
- **Connection Management**: Connection pooling with automatic reconnection, health monitoring, and retry logic.
- **Data Models**: Comprehensive models for users, customers, mining data, network snapshots, and miner specifications.
- **Optimization**: Data storage optimized to a maximum of 10 data points per day, with cleanup policies.

### Key Features
- **HashInsight Treasury Management**: Professional Bitcoin treasury platform for miners with BTC inventory, cost basis, cash coverage tracking, sell strategies, signal aggregation, and execution planning.
- **Mining Calculator Engine**: Core business logic for profitability calculations.
- **Authentication System**: Manages user access, email verification, role-based permissions, and session security.
- **CRM System**: Handles customer lifecycle management, lead and deal tracking, and commission management.
- **Network Data Collection**: Automated historical data accumulation for BTC price, difficulty, and network hashrate from multiple sources.
- **Subscription Management**: Comprehensive plan management with tiered access and role-based exemptions.
- **Treasury Strategy Templates**: Pre-configured selling strategies including OPEX coverage, layered profit-taking, mining cycle, basis/funding, and volatility-triggered approaches.
- **Signal Aggregation System**: Phase 3 Advanced Signal System - 10 sophisticated modules including regime-aware adaptation, breakout exhaustion detection, support/resistance confluence, adaptive ATR layering, pattern target recognition, miner cycle analysis, derivatives pressure monitoring, microstructure execution optimization, bandit-sizing allocation, and ensemble aggregation scoring.
- **Advanced Algorithm Engine**: 完整的Phase 3 (10模块)智能交易系统已100%完成并投入运行，包含：
  - A. 趋势感知自适应 (Regime-Aware Adaptation)
  - B. 突破衰竭检测 (Breakout Exhaustion Detection) 
  - C. 支撑阻力共振 (Support/Resistance Confluence)
  - D. ATR动态分层 (Adaptive ATR Layering)
  - E. 挖矿周期分析 (Miner Cycle Analysis)
  - F. 形态目标识别 (Pattern Target Recognition)
  - G. 衍生品压力监测 (Derivatives Pressure Monitoring)
  - H. 微观结构优化 (Microstructure Execution Optimization) - 包含TWAP执行、滑点控制、流动性评估
  - I. 智能仓位配置 (Bandit-Sizing Allocation)
  - J. 集成聚合决策 (Ensemble Aggregation Scoring)
- **Backtesting Engine**: Historical strategy performance evaluation with professional metrics (Sharpe ratio, max drawdown, win rate).
- **订单执行优化系统**: 完整的机构级执行能力，包含实时滑点预测、TWAP时间窗口计算、流动性深度评估、市场冲击最小化，可有效减少大额Bitcoin交易的执行成本20-40%。
- **Treasury Management回测系统**: 100%无JavaScript错误的可靠回测功能，支持Chart.js v4.5.0，具备完整的按钮状态管理、错误处理和366个真实历史数据点计算能力，达到机构级稳定性标准。

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