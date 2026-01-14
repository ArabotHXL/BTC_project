# HashInsight Enterprise Platform - High-Level Architecture

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Target Audience:** Business Analysts, Product Managers, Technical Managers

---

## System Overview

HashInsight is a modular, enterprise-grade web application built on Flask (Python) that provides comprehensive Bitcoin mining management capabilities. The system follows a **page-isolated architecture** where modules communicate primarily through the database, enabling independent development and deployment.

### Architecture Principles

1. **Modularity** - Independent modules with clear boundaries
2. **Database-Centric Communication** - Modules interact via shared database
3. **Event-Driven Updates** - CDC (Change Data Capture) platform for real-time synchronization
4. **Role-Based Access Control** - Granular permissions per module
5. **Scalability** - Designed to handle 1000+ concurrent users

---

## System Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  (Web UI - Jinja2 Templates, Bootstrap 5, Chart.js)     │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                      │
│  (Flask Routes, Blueprints, Business Logic)             │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                          │
│  (Calculators, Analytics, Intelligence, CRM Services)    │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                             │
│  (PostgreSQL Database, Redis Cache, CDC Platform)       │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                    Integration Layer                      │
│  (External APIs, Blockchain, Email, Payment Systems)     │
└─────────────────────────────────────────────────────────┘
```

---

## Core Business Modules

### 1. Authentication & Authorization Module

**Purpose:** User management, login, session handling, role-based access control

**Key Components:**
- Email-based authentication with verification
- Session management (Flask sessions)
- RBAC (Role-Based Access Control) system
- Password security (Werkzeug hashing)

**User Roles:**
- Owner (full access)
- Admin (administrative access)
- Mining Site Manager (site-specific access)
- Customer (own data only)
- Guest (read-only basic features)

**Key Routes:**
- `/login` - User login
- `/register` - User registration
- `/logout` - User logout
- `/admin/user_access` - User management (admin only)

---

### 2. Mining Calculator Module

**Purpose:** Calculate Bitcoin mining profitability for different ASIC miner models

**Key Features:**
- Dual-algorithm calculation system
- Support for 42+ ASIC miner models
- Real-time BTC price integration
- Network difficulty and hashrate tracking
- ROI analysis
- Power curtailment impact calculation

**Key Components:**
- `mining_calculator.py` - Core calculation engine
- `complete_miner_specs.py` - Miner model database
- Real-time data integration (CoinGecko, Blockchain.info)

**Key Routes:**
- `/calculator` - Main calculator interface
- `/api/calculate` - Calculation API endpoint
- `/curtailment-calculator` - Power outage impact calculator

**Data Flow:**
```
User Input (Miner Model, Quantity, Electricity Cost)
    ↓
Query Miner Specs Database
    ↓
Fetch Real-Time Market Data (BTC Price, Difficulty, Hashrate)
    ↓
Dual-Algorithm Calculation
    ↓
Return Results (Daily Revenue, Profit, ROI, Chart Data)
```

---

### 3. CRM Module

**Purpose:** Customer relationship management, sales pipeline, billing

**Key Features:**
- Customer lifecycle management
- Lead tracking and qualification
- Deal pipeline management
- Invoice generation
- Commission tracking
- Activity logging

**Data Models:**
- `Customer` - Company information, contacts
- `Lead` - Sales opportunities (NEW → CONTACTED → QUALIFIED → WON/LOST)
- `Deal` - Sales transactions (DRAFT → PENDING → APPROVED → SIGNED → COMPLETED)
- `Invoice` - Billing documents (DRAFT → SENT → PAID → OVERDUE)
- `Asset` - Equipment tracking
- `Activity` - Interaction history

**Key Routes:**
- `/crm/dashboard` - CRM overview
- `/crm/customers` - Customer list
- `/crm/leads` - Lead management
- `/crm/deals` - Deal pipeline
- `/crm/invoices` - Invoice management

**Integration Points:**
- Links to Hosting module for customer equipment
- Links to Billing module for payment processing

---

### 4. Hosting Services Module

**Purpose:** Manage mining facilities, track deployed equipment, monitor performance

**Key Features:**
- Multi-site management
- Real-time miner monitoring
- Telemetry data collection
- SLA template management
- Incident tracking
- Ticket system

**Data Models:**
- `HostingSite` - Mining facility (capacity, location, electricity rate)
- `HostingMiner` - Deployed miner (site, client, model, status)
- `MinerTelemetry` - Real-time performance data
- `HostingIncident` - Operational issues
- `HostingTicket` - Customer support tickets

**Key Routes:**
- `/hosting/` - Hosting dashboard
- `/hosting/sites` - Site management
- `/hosting/miners` - Miner management
- `/hosting/tickets` - Ticket system

**Integration Points:**
- CRM module (customer data)
- Client module (customer-facing views)
- Edge Collector (real-time telemetry)

---

### 5. Analytics Module

**Purpose:** Technical analysis, market data, historical trends, ROI visualization

**Key Features:**
- Technical indicators (RSI, MACD, SMA, EMA, Bollinger Bands)
- Historical data replay
- ROI heatmaps
- Power curtailment simulation
- Market trend analysis

**Key Components:**
- `analytics_engine.py` - Core analytics engine
- `historical_data_engine.py` - Historical data processing
- `advanced_algorithm_engine.py` - Advanced signal processing

**Key Routes:**
- `/analytics` - Analytics dashboard
- `/api/analytics/roi-heatmap` - ROI visualization
- `/api/analytics/historical-replay` - Historical analysis
- `/technical-analysis` - Technical indicators page

**Data Sources:**
- Internal database (network_snapshots, market_analytics)
- External APIs (CoinGecko, Blockchain.info)

---

### 6. Intelligence Layer

**Purpose:** AI-powered predictions, optimizations, and recommendations

**Sub-Modules:**

#### 6.1 Forecast Module
- **Purpose:** Predict Bitcoin prices and network difficulty
- **Technology:** ARIMA time-series forecasting
- **Output:** 7-day predictions with confidence intervals
- **Routes:** `/api/intelligence/forecast/{user_id}`

#### 6.2 Optimize Module
- **Purpose:** Optimize power curtailment strategies
- **Technology:** Linear programming (PuLP)
- **Output:** Optimal miner shutdown schedule during outages
- **Routes:** `/api/intelligence/optimize/curtailment`

#### 6.3 Explain Module
- **Purpose:** Explain ROI changes and provide recommendations
- **Technology:** Rule-based expert system
- **Output:** Human-readable explanations and suggestions
- **Routes:** `/api/intelligence/explain/roi/{user_id}`

**Data Flow:**
```
User Request
    ↓
Check Cache (Redis)
    ↓
If Cache Miss:
    - Query Historical Data
    - Run ML Model
    - Store Results in Database
    - Cache Results
    ↓
Return Predictions/Optimizations
```

---

### 7. Treasury Management Module

**Purpose:** Bitcoin inventory tracking, sell strategy optimization, backtesting

**Key Features:**
- BTC position tracking with cost basis
- 5 pre-configured sell strategies
- 10 signal aggregation modules
- Backtesting engine (366 historical data points)
- Order execution optimization

**Signal Modules:**
1. Technical Indicators
2. Sentiment Analysis
3. On-Chain Data
4. Derivatives Data
5. Market Microstructure
6. Pattern Recognition
7. Regime Detection
8. Breakout Exhaustion
9. Support/Resistance
10. Ensemble Scoring

**Key Routes:**
- `/api/treasury/overview` - Treasury dashboard
- `/api/treasury/signals` - Trading signals
- `/api/treasury-exec/execute` - Execute trades

---

### 8. Batch Processing Module

**Purpose:** Bulk calculations, CSV import/export, Excel generation

**Key Features:**
- CSV template download
- Bulk miner import
- Batch profitability calculations
- Excel export with charts
- Error reporting

**Key Routes:**
- `/batch-calculator` - Batch calculator interface
- `/batch/upload` - CSV upload
- `/api/batch-calculate` - Batch calculation API

---

### 9. Client Portal Module

**Purpose:** Customer-facing interface for hosted miners

**Key Features:**
- Customer dashboard
- Asset overview
- Bill viewing
- Ticket submission
- Performance reports

**Key Routes:**
- `/client/dashboard` - Customer dashboard
- `/client/assets` - Equipment view
- `/client/bills` - Billing information

---

### 10. Web3 & Blockchain Module

**Purpose:** Blockchain integration, SLA NFT certificates, transparency verification

**Key Features:**
- SLA certificate NFT minting
- IPFS metadata storage
- Blockchain data verification
- Base L2 integration
- Transparency audit trails

**Key Routes:**
- `/api/sla/mint-certificate` - Mint SLA NFT
- `/api/blockchain/verify-data` - Verify blockchain data
- `/trust/verify` - Transparency verification

---

## Data Architecture

### Primary Database (PostgreSQL)

**Core Tables:**
- `user_access` - User accounts and authentication
- `miner_models` - ASIC miner specifications
- `user_miners` - User's miner configurations
- `network_snapshots` - Historical Bitcoin network data
- `market_analytics` - Market analysis data

**CRM Tables:**
- `crm_customers`, `crm_leads`, `crm_deals`, `crm_invoices`, `crm_assets`

**Hosting Tables:**
- `hosting_sites`, `hosting_miners`, `miner_telemetry`, `hosting_incidents`

**Intelligence Tables:**
- `forecast_daily` - Price/difficulty predictions
- `ops_schedule` - Optimization schedules
- `treasury_positions` - BTC holdings
- `treasury_strategies` - Sell strategies

**CDC Platform Tables:**
- `event_outbox` - Transactional outbox for events
- `event_inbox` - Consumer idempotency tracking
- `event_dlq` - Dead letter queue for failed events

### Caching Layer (Redis)

**Cache Categories:**
- Real-time data (BTC price, network stats) - 5-60 second TTL
- Miner data - 1 hour TTL
- Calculation results - 5 minutes TTL
- Analytics data - 5 minutes to 1 hour TTL
- Intelligence predictions - 30 minutes TTL

**Cache Strategy:** Stale-While-Revalidate (SWR) - return cached data immediately, refresh in background

---

## External Integrations

### Data Sources
- **CoinGecko API** - Real-time cryptocurrency prices
- **Blockchain.info API** - Bitcoin network statistics
- **CoinWarz API** - Mining profitability data
- **Alternative.me API** - Fear & Greed Index
- **Ankr RPC** - Bitcoin blockchain RPC calls

### Trading Data
- **Deribit API** - Options and futures data
- **OKX API** - Exchange data
- **Binance API** - Market data

### Infrastructure
- **PostgreSQL** - Primary database (Neon hosted)
- **Redis** - Caching and distributed locks
- **Kafka** - Event streaming (CDC platform)
- **Debezium** - Change Data Capture

### Services
- **SendGrid** - Email delivery
- **Pinata/IPFS** - NFT metadata storage
- **Base L2** - Blockchain network
- **Stripe** - Payment processing (optional)

---

## Event-Driven Architecture (CDC Platform)

### How It Works

1. **Business Operation** - User updates miner configuration
2. **Database Transaction** - Update `user_miners` table + insert into `event_outbox` (same transaction)
3. **CDC Capture** - Debezium reads from PostgreSQL WAL (Write-Ahead Log)
4. **Event Publishing** - Event published to Kafka topic
5. **Consumer Processing** - Background workers consume events
6. **Idempotency Check** - Check `event_inbox` to prevent duplicate processing
7. **Business Logic** - Recalculate ROI, update forecasts, etc.
8. **Error Handling** - Failed events go to DLQ for retry

### Event Types
- `miner.portfolio_updated` - Miner configuration changed
- `treasury.position_updated` - BTC position changed
- `ops.schedule_created` - Power optimization schedule created
- `crm.deal_closed` - Sales deal completed

### Benefits
- **Real-time Updates** - Changes propagate within 3 seconds
- **Reliability** - Failed events can be retried
- **Scalability** - Multiple consumers can process events in parallel
- **Decoupling** - Modules don't need direct dependencies

---

## Security Architecture

### Authentication
- Email-based login with verification
- Secure password hashing (Werkzeug PBKDF2)
- Session management with secure cookies
- JWT tokens for API access

### Authorization
- Role-Based Access Control (RBAC)
- Module-level permissions
- Data-level isolation (users only see their data)
- API key management

### Data Protection
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection (Jinja2 auto-escaping)
- CSRF protection (custom tokens)
- Input validation and sanitization
- Encrypted data storage

### Compliance
- SOC 2 audit-ready
- GDPR compliant
- PCI DSS scope clarified
- Audit logging for all operations

---

## Performance Architecture

### Optimization Strategies

1. **Caching**
   - Multi-tier caching (memory + Redis)
   - SWR (Stale-While-Revalidate) strategy
   - Smart cache warming on startup

2. **Database**
   - Connection pooling (10 connections, 20 overflow)
   - Query optimization with indexes
   - Batch processing for large datasets
   - Data retention policies (max 10 data points/day)

3. **API**
   - Rate limiting
   - Response compression
   - Async task processing (RQ)
   - Request coalescing (9.8x performance improvement)

### Performance Targets
- **Page Load Time:** < 2 seconds
- **API Response Time:** < 200ms (P95)
- **Database Query Time:** < 50ms
- **Write-to-Visible Latency:** < 3 seconds (P95)
- **Uptime:** 99.95%

---

## Deployment Architecture

### Production Stack
```
Load Balancer (Replit/Cloud Provider)
    ↓
Gunicorn Workers (3-4 workers)
    ↓
Flask Application
    ↓
PostgreSQL Database (Neon)
    ↓
Redis Cache
    ↓
Kafka Cluster (CDC Platform)
```

### Scalability
- **Horizontal Scaling:** Multiple Flask workers behind load balancer
- **Database Scaling:** Read replicas for queries
- **Cache Scaling:** Redis cluster for distributed caching
- **Event Processing:** Multiple Kafka consumers for parallel processing

---

## Module Communication Patterns

### Pattern 1: Direct Database Access
Modules read/write directly to shared database tables
- **Example:** CRM module reads customer data from `crm_customers` table
- **Pros:** Simple, fast
- **Cons:** Tight coupling

### Pattern 2: Event-Driven (CDC)
Modules communicate via events through CDC platform
- **Example:** Miner update triggers portfolio recalculation
- **Pros:** Loose coupling, real-time updates
- **Cons:** More complex, eventual consistency

### Pattern 3: API Calls
Modules call each other's APIs
- **Example:** Analytics module calls Intelligence API for predictions
- **Pros:** Clear interfaces, versioning
- **Cons:** Network latency, dependency management

---

## Technology Stack Summary

### Backend
- **Language:** Python 3.9+
- **Framework:** Flask 2.3+
- **Server:** Gunicorn
- **Database:** PostgreSQL 15+
- **ORM:** SQLAlchemy 2.0+
- **Cache:** Redis 7+

### Frontend
- **Templates:** Jinja2
- **UI Framework:** Bootstrap 5
- **Charts:** Chart.js
- **Icons:** Bootstrap Icons

### Data Processing
- **Analytics:** NumPy, Pandas
- **ML:** statsmodels, XGBoost
- **Optimization:** PuLP

### Infrastructure
- **CDC:** Debezium, Kafka
- **Blockchain:** Web3.py, Base L2
- **Email:** SendGrid

---

## Next Steps

For **Technical Implementation Details**, see:
- [Technical Architecture Document](03_TECHNICAL_ARCHITECTURE.md) - Developer-focused deep dive
- [Low-Level Implementation](04_LOW_LEVEL_IMPLEMENTATION.md) - Architect-level details
- [Route-to-Page Mapping](05_ROUTE_TO_PAGE_MAPPING.md) - Complete URL structure

For **Business Understanding**, see:
- [Executive Summary](00_EXECUTIVE_SUMMARY.md) - Non-technical overview
