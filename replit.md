# BTC Mining Calculator System

## Overview
The BTC Mining Calculator is an enterprise-grade web application for Bitcoin mining profitability analysis, targeting mining site owners and their clients. It provides real-time data integration, dual-algorithm validation, multilingual support (Chinese/English), and robust role-based access control. The system aims to optimize Bitcoin mining investments through comprehensive operations management, CRM, power management, technical analysis, and professional reporting.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The application is a modular Flask web application with a mobile-first design, supporting both English and Chinese, and employs a complete page isolation architecture.

### Frontend Architecture
-   **Template Engine**: Jinja2 with Bootstrap 5 (dark theme, golden accents).
-   **UI Framework**: Bootstrap CSS, Bootstrap Icons, Chart.js for data visualization.
-   **Responsive Design**: Mobile-first.
-   **Multilingual Support**: Dynamic Chinese/English language switching across all UI elements.
-   **UI/UX Decisions**: Professional introduction page, clear navigation, and color-coded visual systems for technical analysis.

### Backend Architecture
-   **Web Framework**: Flask, using Blueprint-based modular routing with complete page isolation.
-   **Modular Architecture**: Independent modules (Calculator, CRM, Batch, Analytics, Broker) communicate primarily through the database.
-   **Authentication**: Custom email-based system with role management and secure password hashing.
-   **API Integration**: Aggregates data from multiple sources with intelligent fallback.
-   **Background Services**: Scheduler for automated data collection.
-   **Calculation Engine**: Dual-algorithm system for mining profitability analysis, supporting 17+ ASIC miner models, real-time data, ROI analysis, power curtailment, and hashrate decay. Optimized for batch processing.
-   **Technical Analysis Platform**: Server-side calculation of indicators (RSI, MACD, SMA, EMA, Bollinger Bands, volatility) using historical BTC price.
-   **Permission Control System**: Advanced decorators and a comprehensive permission matrix for role-based access control (RBAC).
-   **User Management**: Admin interface for user creation, role assignment, and management.
-   **Professional Report Generation**: Capabilities for generating reports, including ARIMA predictions and Monte Carlo simulations.
-   **Caching System**: Intelligent caching for major API endpoints, including Stale-While-Revalidate (SWR) for performance.
-   **Deployment Optimization**: Fast startup, lightweight health checks, and production-ready configuration, separating scheduler and worker services.
-   **Personal Layer Selection System (L1-L4)**: Integrated layer selector for risk-reward levels with real-time target price calculation.
-   **Data Integrity**: Uses real API data sources for user portfolio management, historical data, and technical indicators.
-   **HashInsight Treasury Management**: Professional Bitcoin treasury platform.
-   **CRM System**: Handles customer lifecycle management, lead/deal tracking, and commission management.
-   **Network Data Collection**: Automated historical data accumulation for BTC price, difficulty, and network hashrate.
-   **Subscription Management**: Comprehensive plan management with tiered access.
-   **Treasury Strategy Templates**: Pre-configured selling strategies.
-   **Signal Aggregation System**: 10 sophisticated modules for advanced signal generation.
-   **Backtesting Engine**: Evaluates historical strategy performance.
-   **订单执行优化系统**: Institutional-grade execution capabilities.
-   **Intelligence Layer**: Event-driven smart layer for mining operations automation and predictive analytics, featuring an event-driven system (Outbox Pattern), task queue system (Redis Queue), intelligence modules (Forecast, Anomaly Detection, Power Optimizer, ROI Explainer), and enhanced cache management.
-   **SLO Monitoring System**: Tracks critical performance metrics like P95 TTR, success rate, and latency distribution with configurable alerts.

### Database Architecture
-   **Primary Database**: PostgreSQL.
-   **ORM**: SQLAlchemy with declarative base.
-   **Connection Management**: Connection pooling with automatic reconnection, health monitoring, and retry logic.
-   **Data Models**: Comprehensive models for users, customers, mining data, network snapshots, and miner specifications.
-   **Optimization**: Data storage optimized to a maximum of 10 data points per day, with cleanup policies.

### CRM Platform (Node.js/TypeScript)
A new enterprise-grade CRM platform built with Node.js/TypeScript, PostgreSQL, and React is being developed to replace and extend the existing Flask CRM system.

**Architecture**:
-   **Backend**: Node.js/TypeScript API service (Express + Prisma ORM).
-   **Frontend**: React SPA with Vite + Tailwind CSS.
-   **Shared**: Shared TypeScript types and Zod schemas for type safety.
-   **Event System**: Redis Pub/Sub + EventQueue dual-write pattern for reliable event distribution.

**Security & Authentication**:
-   **JWT-based Authentication**: Dual tokens (access + refresh) with automatic rotation.
-   **RBAC Permission Engine**: 4 roles (SUPER_ADMIN, ADMIN, SALES, OPS) with 20+ granular permissions.
-   **Secure Logout**: Refresh token revocation with logout-all functionality.
-   **Token Security**: Proper userId validation to prevent cross-account token revocation.

**Core CRM Modules (Completed)**:
-   **Lead/Deal Management**: Intelligent lead scoring (40pts referral, 35pts partner), stage-based pipeline (10%-75% probability), contract auto-generation (CON-YYYY-XXXXX).
-   **Billing System**: Invoice/Payment tracking with aging reports (0-30, 31-60, 61-90, 90+ days), net revenue calculation (output - power - service fees), payment accrual logic (PENDING→CONFIRMED→CLEARED).
-   **Asset Management**: 10-state lifecycle (ORDERED→IN_TRANSIT→RECEIVED→IN_STORAGE→DEPLOYED→MINING→MAINTENANCE→DELAYED→CANCELLED→DECOMMISSIONED), serial number tracking, batch/shipment integration, bulk import (max 1000), inventory summaries, maintenance history.

**Business Logic**:
-   **Lead Scoring Algorithm**: Automated scoring based on source quality and company signals.
-   **Deal Probability**: Stage-based conversion rates (PROSPECTING 10% → CLOSED_WON 75%).
-   **Invoice Auto-numbering**: INV-YYYY-MM-XXXXX format with sequential generation.
-   **Payment Status Flow**: PENDING→CONFIRMED→CLEARED with proper accrual tracking.
-   **Asset Status Validation**: Enforced state transition rules via STATUS_TRANSITIONS mapping, all changes through validateStatusTransition().
-   **Shipment-Asset Synchronization**: Shipment status automatically updates related asset states (markAsShipped → IN_TRANSIT, markAsDelivered → RECEIVED).

**Event-Driven Architecture (Production-Ready)**:
-   **Event System Components**: EventPublisher (dual-write), EventSubscriber (Redis real-time), EventConsumer (queue polling), EventProcessor (lifecycle coordinator), dedicated worker process.
-   **16 Event Handlers**: Covering all 12 core events - lead.captured, lead.converted, deal.stage_changed, deal.won, contract.signed, invoice.created, invoice.issued, invoice.paid, payment.received, payment.confirmed, asset.status_changed, asset.deployed, asset.mining_started, shipment.shipped, shipment.delivered, plus contract.generated.
-   **Dual-Write Pattern**: Events persist to EventQueue table (reliable) and publish to Redis Pub/Sub (real-time) for fault tolerance.
-   **Auto-Reconnection**: Publisher and Subscriber automatically reconnect to Redis every 5 seconds when disconnected.
-   **Worker Process**: Independent event worker with health check endpoint (port 3001), startup retry (5 attempts), graceful shutdown, and component status monitoring.
-   **Production Features**: Partial startup support, error swallowing for resilience, reconnection loops, health checks reflecting Redis status.

**Flask Integration Services (Completed)**:
-   **FlaskClient**: API Key authentication (X-API-Key), HMAC-SHA256 request signing, retry mechanism (5xx errors, 2 retries, exponential backoff), 30s timeout.
-   **CalcService**: Mining profitability calculations (`/calculate` endpoint), miner data, SHA256 comparison.
-   **IntelligenceService**: Forecast, optimization, explanations, health checks (`/api/intelligence/*`).
-   **AnalyticsService**: BTC price, network stats, technical indicators, treasury overview, trading signals, backtesting (`/api/analytics/*`, `/api/treasury/*`).
-   **Authentication**: API Key-based (no self-signed JWT), request signing with query params and empty body handling, production-ready.

**Data Integrity & Security**:
-   **Status Bypass Prevention**: UpdateAssetDTO/Schema excludes status field; all status changes require validation.
-   **Lifecycle Enforcement**: validateStatusTransition() guards prevent invalid state transitions.
-   **Event Consistency**: All state mutations emit events for downstream consumers.
-   **Error Handling**: Graceful degradation with try-catch for multi-asset operations.

**Data Model**: 30 core tables and 23 enum types managed via Prisma ORM.

**API Endpoints (28 total)**:
-   Lead/Deal: 12 endpoints (CRUD, scoring, stage management, contract generation)
-   Billing: 9 endpoints (invoice/payment CRUD, aging reports, revenue calculation)
-   Assets: 15 endpoints (CRUD, status flow, bulk import, inventory, maintenance)
-   Batches: 6 endpoints (batch management, asset association, summaries)
-   Shipments: 7 endpoints (tracking, status updates, delivery management)

## External Dependencies

### APIs
-   **CoinWarz API**: Mining data and multi-coin profitability.
-   **CoinGecko API**: Real-time cryptocurrency pricing and historical data.
-   **Blockchain.info API**: Bitcoin network statistics.
-   **IP-API**: Geographic location services.
-   **Ankr RPC**: Free Bitcoin RPC service.
-   **Gmail SMTP**: Email service.
-   **Deribit API**: Trading data integration.
-   **OKX API**: Trading data integration.
-   **Binance API**: Trading data integration.

### Third-party Libraries
-   **Flask**: Web application framework.
-   **SQLAlchemy**: ORM for database interaction.
-   **Requests**: HTTP client.
-   **NumPy/Pandas**: Mathematical calculations and data analysis.
-   **Chart.js**: Frontend data visualization.
-   **Bootstrap**: UI framework.
-   **Werkzeug**: Secure password hashing.
-   **RQ (Redis Queue)**: Task distribution.
-   **Statsmodels ARIMA**: Time series forecasting.
-   **PuLP**: Linear programming optimization.
-   **XGBoost**: Advanced ML predictions.
-   **Flask-Caching**: Performance optimization.
-   **Express**: Node.js web application framework.
-   **Prisma**: ORM for Node.js/TypeScript.
-   **React**: Frontend library.
-   **Vite**: Frontend build tool.
-   **Tailwind CSS**: Utility-first CSS framework.
-   **Zod**: Schema declaration and validation.

### Infrastructure
-   **PostgreSQL**: Relational database.
-   **Python 3.9+**: Runtime environment for Flask application.
-   **Node.js 18+**: Runtime environment for CRM platform.
-   **Redis**: In-memory data store for caching and task queues.
-   **Gunicorn**: Production WSGI server for Flask.
-   **Docker Compose**: Containerization for services.