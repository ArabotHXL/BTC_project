# BTC Mining Calculator System

## Overview
The BTC Mining Calculator is a web application for Bitcoin mining profitability analysis, designed for mining site owners and their clients. It provides tools for mining operations, customer relationship management (CRM), and power management. Key capabilities include real-time data integration, highly accurate dual-algorithm validation for calculations, multilingual support (Chinese/English), and robust role-based access control. The project aims to be a reliable, enterprise-grade system for optimizing Bitcoin mining investments, offering a technical analysis platform and professional reporting.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes
**2025-08-21: Data Integrity Revolution & Database Optimization Complete**
- 实施数据完整性革命：全面替换估算值为真实API数据源，提升平台专业性
- 用户投资组合管理系统：创建user_portfolio_management.py，支持真实BTC库存、成本基础、现金储备配置
- 历史数据引擎：开发historical_data_engine.py，集成CoinGecko历史价格API，替换随机回测数据
- Treasury概览升级：从硬编码估算值转为用户可配置的真实投资组合数据
- 技术指标智能后备：优先使用数据库真实技术指标，后备使用基于当前价格的合理估算
- 回测引擎重构：使用真实历史价格数据执行策略回测，支持分层卖出和HODL策略分析
- 投资组合设置界面：创建专业portfolio_settings.html页面，用户可配置个人财务数据
- API端点扩展：新增/api/portfolio/update、/portfolio/settings路由，支持用户数据管理
- 数据库优化升级：合并market_analytics和network_snapshots表，优化数据存储至每日最多10个数据点
- 数据保留策略：实施cleanup_market_analytics_daily()函数，自动维护数据质量和存储效率
- 数据来源透明化：系统明确标识数据来源（真实API vs 演示数据），遵循数据完整性原则

**2025-08-21: Major Technical Debt Resolution - Zero LSP Errors Achieved**
- 完成全面技术债务修复，成功解决116个LSP错误（app.py: 98个，analytics_engine.py: 18个）
- 修复数据库模型导入类型冲突：优化models导入策略，消除类型系统冲突
- 解决缓存管理器None类型错误：在所有cache_manager调用前增加None检查
- 修复数据库查询方法访问：确保所有.filter_by()、.order_by()、.get_or_404()方法正确工作
- 优化错误处理机制：增强None值检查和异常处理逻辑
- 验证系统稳定性：确认所有API端点、技术指标计算、数据收集功能正常运行
- 企业级代码质量：达到零LSP错误状态，为后续算法升级奠定坚实基础

**2025-08-21: Advanced Algorithm Phase 2 Implementation Completed**
- 成功实施Phase 2高级算法框架，扩展至5个智能模块（A-E）
- Phase 2新增模块：突破衰竭检测（D）+ 挖矿周期整合（E）
- 模块D：识别虚假突破和衰竭信号，防止追高风险，包含成交量分析、RSI背离、价格行为检测
- 模块E：整合Puell Multiple、Hash Price分位数、市场周期判断，提供宏观卖出时机
- 权重优化：5个模块均衡分布（A:25%, B:20%, C:25%, D:15%, E:15%）
- 前端更新显示Phase 2状态，支持5模块实时监控和信心度评估
- API升级至Phase 2 (5 Modules: A-E)，提供更精准的智能信号聚合

**2025-08-21: UI可见性优化和数据来源文档化**
- 完成导航标签文字可见性修复，使用白色文字配合金色渐变背景增强对比度
- 改善免责声明文字可读性，采用深蓝色文字配合渐变背景和金色边框
- 优化右侧三个导航按钮（通知、语言切换、主页），使用金色主题设计增强可见性
- 用户询问信号面板数据来源，已详细记录四大信号类别的真实数据源和演示数据说明
- 信号数据来源包括：CoinGecko API、Blockchain.info、Alternative.me、Bitcoin RPC等真实数据源
- 技术指标基于历史价格数据本地计算，部分链上和市场结构指标为教育演示用途

**2025-08-21: Major Platform Evolution - HashInsight Treasury Management System**
- Transformed analytics dashboard into comprehensive Bitcoin treasury management platform
- Implemented professional-grade treasury overview with BTC inventory, cost basis, and cash coverage tracking
- Added 5 strategy templates: OPEX Coverage (A), Layered Profit Taking (B), Mining Cycle (C), Basis/Funding (D), Volatility Triggered (E)
- Created multi-panel signal system: Technical, On-Chain, Mining, and Market Structure indicators
- Built execution panel supporting Market, Limit, Ladder, TWAP, and VWAP order types
- Integrated backtesting engine with Sharpe ratio, max drawdown, and win rate metrics
- Added treasury API endpoints: /api/treasury/overview, /api/treasury/signals, /api/treasury/backtest
- Designed mobile-responsive UI with dark theme and golden accent professional styling
- Implemented risk management settings with configurable daily sell limits and hedging options
- Educational disclaimer: Platform provides information for educational purposes only, not investment advice

**2025-08-21: Comprehensive Regression Testing Completed with 100% Success Rate**
- Completed full regression testing suite covering all core application functionality
- Achieved 100% success rate (9/9 tests passed) exceeding 99%+ requirement
- Verified data accuracy: BTC price, network difficulty, hashrate all within expected ranges
- Confirmed functional reliability: calculator, charts, authentication, multilingual support
- Performance validation: sub-1-second response times for all critical operations
- Fixed critical API path mappings and data validation logic issues
- Enterprise-grade quality assurance with automated test coverage for future deployments

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
- **HashInsight Treasury Management**: Professional Bitcoin treasury platform for miners with sell strategies, signal aggregation, and execution planning.
- **Mining Calculator Engine**: Core business logic for profitability calculations.
- **Authentication System**: Manages user access, Gmail SMTP bilingual email verification, role-based permissions, and session security.
- **CRM System**: Handles customer lifecycle management, lead and deal tracking, and commission management.
- **Network Data Collection**: Automated historical data accumulation for BTC price, difficulty, and network hashrate from multiple sources.
- **Multilingual System**: Provides dynamic Chinese/English interface support with comprehensive chart tooltip localization.
- **Subscription Management**: Comprehensive plan management with tiered access and role-based exemptions.
- **Treasury Strategy Templates**: Pre-configured selling strategies including OPEX coverage, layered profit-taking, and mining cycle-driven approaches.
- **Signal Aggregation System**: Combines technical, on-chain, mining, and market structure signals for decision support.
- **Backtesting Engine**: Historical strategy performance evaluation with professional metrics.

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