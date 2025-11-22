# Module Interaction & Dependencies

## Complete Module Ecosystem

```mermaid
graph TB
    subgraph "User-Facing Modules"
        CALC[🧮 Calculator Module<br/>━━━━━━━━━━━━<br/>Profitability Calculation<br/>Batch Processing<br/>ROI Analysis]
        
        CRM[👥 CRM Module<br/>━━━━━━━━━━━━<br/>Lead Management<br/>Deal Pipeline<br/>Invoice Generation]
        
        HOST[🏭 Hosting Module<br/>━━━━━━━━━━━━<br/>Device Management<br/>Real-time Telemetry<br/>Operations Dashboard]
        
        ANALYTICS[📊 Analytics Module<br/>━━━━━━━━━━━━<br/>Technical Analysis<br/>Market Indicators<br/>Signal Generation]
    end
    
    subgraph "Intelligence Layer"
        CURTAIL[⚡ Curtailment Engine<br/>━━━━━━━━━━━━<br/>Performance Priority<br/>Optimization (PuLP)<br/>Auto Recovery]
        
        FORECAST[🔮 Forecasting Engine<br/>━━━━━━━━━━━━<br/>ARIMA Models<br/>Price Prediction<br/>Difficulty Forecast]
        
        ANOMALY[⚠️ Anomaly Detection<br/>━━━━━━━━━━━━<br/>Outlier Detection<br/>Threshold Alerts<br/>Pattern Recognition]
        
        EVENTS[📡 Event Publisher<br/>━━━━━━━━━━━━<br/>Database Hooks<br/>Outbox Pattern<br/>CDC Integration]
    end
    
    subgraph "Supporting Services"
        TREASURY[💰 Treasury Module<br/>━━━━━━━━━━━━<br/>BTC Inventory<br/>Sell Strategies<br/>Backtesting Engine]
        
        REPORT[📄 Report Generator<br/>━━━━━━━━━━━━<br/>PDF Reports<br/>Excel Exports<br/>PowerPoint Decks]
        
        BILLING[💳 Billing System<br/>━━━━━━━━━━━━<br/>Hosting Fees<br/>Crypto Payments<br/>Invoice Automation]
        
        BLOCKCHAIN_MOD[⛓️ Blockchain Module<br/>━━━━━━━━━━━━<br/>Base L2 Integration<br/>IPFS Storage<br/>Data Verification]
    end
    
    subgraph "Background Services"
        CGMINER_SCHED[⏰ CGMiner Scheduler<br/>━━━━━━━━━━━━<br/>Telemetry Collection<br/>Every 60 seconds<br/>Distributed Lock]
        
        CURTAIL_SCHED[⏰ Curtailment Scheduler<br/>━━━━━━━━━━━━<br/>Plan Execution<br/>Recovery Monitor<br/>Every 60 seconds]
        
        ANALYTICS_SCHED[⏰ Analytics Scheduler<br/>━━━━━━━━━━━━<br/>Market Data Collection<br/>Indicator Calculation<br/>Every 15 minutes]
        
        DATA_COL[📡 Data Collectors<br/>━━━━━━━━━━━━<br/>Multi-threaded<br/>API Aggregation<br/>Parallel Execution]
    end
    
    subgraph "Data Layer"
        DB[(🗄️ PostgreSQL<br/>━━━━━━━━━<br/>15+ Tables<br/>Indexed Queries<br/>Transactions)]
        
        CACHE[(⚡ Redis<br/>━━━━━━━━━<br/>API Cache<br/>Sessions<br/>Job Queue)]
    end
    
    subgraph "Shared Components"
        CACHE_MGR[📦 Cache Manager<br/>━━━━━━━━━━━━<br/>Stale-While-Revalidate<br/>TTL Management<br/>Fallback Strategy]
        
        SECURITY[🔐 Security Manager<br/>━━━━━━━━━━━━<br/>CSRF Protection<br/>Session Handling<br/>RBAC Enforcement]
        
        AUTH[🔑 Auth System<br/>━━━━━━━━━━━━<br/>Email/Password<br/>Web3 Wallet<br/>Email Verification]
    end
    
    %% User Module Dependencies
    CALC --> CACHE_MGR
    CALC --> DB
    CALC --> TREASURY
    CALC --> REPORT
    
    CRM --> DB
    CRM --> BILLING
    CRM --> REPORT
    CRM --> BLOCKCHAIN_MOD
    
    HOST --> DB
    HOST --> CACHE_MGR
    HOST --> CURTAIL
    HOST --> BILLING
    HOST --> REPORT
    HOST --> BLOCKCHAIN_MOD
    
    ANALYTICS --> DB
    ANALYTICS --> CACHE_MGR
    ANALYTICS --> FORECAST
    ANALYTICS --> REPORT
    
    %% Intelligence Dependencies
    CURTAIL --> DB
    CURTAIL --> HOST
    CURTAIL --> EVENTS
    
    FORECAST --> ANALYTICS
    FORECAST --> DB
    
    ANOMALY --> DB
    ANOMALY --> EVENTS
    
    EVENTS --> DB
    EVENTS --> BLOCKCHAIN_MOD
    
    %% Supporting Service Dependencies
    TREASURY --> CALC
    TREASURY --> ANALYTICS
    TREASURY --> DB
    
    REPORT --> CALC
    REPORT --> CRM
    REPORT --> HOST
    REPORT --> ANALYTICS
    REPORT --> DB
    
    BILLING --> HOST
    BILLING --> CRM
    BILLING --> DB
    
    BLOCKCHAIN_MOD --> DB
    
    %% Background Service Dependencies
    CGMINER_SCHED --> DATA_COL
    CGMINER_SCHED --> DB
    CGMINER_SCHED --> CACHE
    CGMINER_SCHED --> ANOMALY
    
    CURTAIL_SCHED --> CURTAIL
    CURTAIL_SCHED --> DB
    
    ANALYTICS_SCHED --> DATA_COL
    ANALYTICS_SCHED --> ANALYTICS
    ANALYTICS_SCHED --> DB
    ANALYTICS_SCHED --> CACHE
    
    DATA_COL --> CACHE_MGR
    DATA_COL --> DB
    
    %% Shared Component Dependencies
    CACHE_MGR --> CACHE
    SECURITY --> DB
    AUTH --> DB
    AUTH --> SECURITY
    
    %% All modules use Auth & Security
    CALC --> AUTH
    CRM --> AUTH
    HOST --> AUTH
    ANALYTICS --> AUTH
    
    CALC --> SECURITY
    CRM --> SECURITY
    HOST --> SECURITY
    ANALYTICS --> SECURITY
    
    style CALC fill:#4CAF50,stroke:#2E7D32,color:#fff
    style CRM fill:#2196F3,stroke:#0D47A1,color:#fff
    style HOST fill:#FF9800,stroke:#E65100,color:#fff
    style ANALYTICS fill:#9C27B0,stroke:#4A148C,color:#fff
    style CURTAIL fill:#F44336,stroke:#b71c1c,color:#fff
    style DB fill:#336791,stroke:#1a3a52,color:#fff
    style CACHE fill:#DC382D,stroke:#8b2119,color:#fff
```

## Module Communication Patterns

### 1. Synchronous Communication (Request/Response)

```mermaid
sequenceDiagram
    participant User
    participant Calculator
    participant CacheManager
    participant Analytics
    participant Database
    
    User->>Calculator: Calculate profitability
    Calculator->>CacheManager: Get BTC price
    CacheManager->>Analytics: Fetch if cache miss
    Analytics->>Database: Query market_analytics
    Database-->>Analytics: Latest price
    Analytics-->>CacheManager: Return price
    CacheManager-->>Calculator: Cached price
    Calculator->>Database: Get miner specs
    Database-->>Calculator: Miner data
    Calculator-->>User: Profitability results
```

### 2. Asynchronous Communication (Event-Driven)

```mermaid
sequenceDiagram
    participant Scheduler
    participant CurtailmentEngine
    participant EventPublisher
    participant OutboxTable
    participant ExternalConsumer
    
    Scheduler->>CurtailmentEngine: Execute plan
    CurtailmentEngine->>CurtailmentEngine: Shutdown miners
    CurtailmentEngine->>EventPublisher: Publish event
    EventPublisher->>OutboxTable: INSERT event
    Note over OutboxTable: Event: curtailment.executed<br/>Payload: {site_id, miners_affected}
    ExternalConsumer->>OutboxTable: Poll for events
    OutboxTable-->>ExternalConsumer: Unprocessed events
    ExternalConsumer->>ExternalConsumer: Process event
    ExternalConsumer->>OutboxTable: Mark as processed
```

## Module Dependency Matrix

| Module | Dependencies | Provides Services To | Database Tables Used |
|--------|--------------|---------------------|---------------------|
| **Calculator** | Cache Manager, Database | Treasury, Report Generator | miner_models, calculation_history |
| **CRM** | Database, Billing | Report Generator, Blockchain | crm_leads, crm_deals, crm_invoices |
| **Hosting** | Cache Manager, Database, Curtailment | Billing, Report, Blockchain | hosting_sites, hosting_miners, miner_telemetry |
| **Analytics** | Cache Manager, Database, Forecasting | Calculator, Report, Treasury | market_analytics, technical_indicators |
| **Curtailment** | Database, Optimization Engine | Hosting | curtailment_plans, curtailment_plan_miners |
| **Forecasting** | Analytics, Database | Curtailment, Treasury | market_analytics |
| **Report Generator** | Calculator, CRM, Hosting, Analytics | End Users | All tables (read-only) |
| **Blockchain** | Database | CRM, Hosting | outbox_events |

## API Endpoint Organization

```mermaid
graph LR
    subgraph "Public Routes (No Auth)"
        PUB1[GET /<br/>Homepage]
        PUB2[GET /calculator<br/>Calculator UI]
        PUB3[POST /calculator/calculate<br/>Calculate Profitability]
        PUB4[GET /login<br/>Login Page]
    end
    
    subgraph "User Routes (Login Required)"
        USER1[GET /main<br/>Dashboard]
        USER2[GET /hosting/client/dashboard<br/>Client Dashboard]
        USER3[GET /calculator/batch<br/>Batch Calculator]
    end
    
    subgraph "Admin Routes (Admin/Owner Only)"
        ADMIN1[GET /crm/leads<br/>Lead Management]
        ADMIN2[GET /crm/deals<br/>Deal Pipeline]
        ADMIN3[GET /admin/users<br/>User Management]
    end
    
    subgraph "Host Routes (Host Role Only)"
        HOST1[GET /hosting/host/devices<br/>Device Management]
        HOST2[POST /hosting/host/devices/batch<br/>Batch Operations]
        HOST3[GET /hosting/curtailment<br/>Curtailment Dashboard]
        HOST4[POST /hosting/curtailment/trigger<br/>Trigger Curtailment]
    end
    
    subgraph "API Routes (API Key Auth)"
        API1[GET /hosting/api/telemetry/:id<br/>Get Telemetry]
        API2[POST /hosting/api/miner/:id/start<br/>Start Miner]
        API3[POST /hosting/api/miner/:id/shutdown<br/>Shutdown Miner]
    end
    
    style PUB1 fill:#4CAF50,stroke:#2E7D32,color:#fff
    style USER1 fill:#2196F3,stroke:#0D47A1,color:#fff
    style ADMIN1 fill:#FF9800,stroke:#E65100,color:#fff
    style HOST1 fill:#9C27B0,stroke:#4A148C,color:#fff
    style API1 fill:#F44336,stroke:#b71c1c,color:#fff
```

## Module Layering Architecture

```mermaid
graph TB
    subgraph "Layer 1: Presentation"
        L1[Templates + Static Assets]
    end
    
    subgraph "Layer 2: Application (Routes)"
        L2A[Calculator Routes]
        L2B[CRM Routes]
        L2C[Hosting Routes]
        L2D[Analytics Routes]
    end
    
    subgraph "Layer 3: Business Logic"
        L3A[Calculator Service]
        L3B[CRM Service]
        L3C[Hosting Service]
        L3D[Analytics Engine]
        L3E[Curtailment Engine]
        L3F[Forecasting Engine]
    end
    
    subgraph "Layer 4: Data Access"
        L4A[SQLAlchemy Models]
        L4B[Cache Manager]
        L4C[Query Builders]
    end
    
    subgraph "Layer 5: External Integration"
        L5A[Market Data APIs]
        L5B[CGMiner APIs]
        L5C[Blockchain APIs]
        L5D[Email Service]
    end
    
    L1 --> L2A
    L1 --> L2B
    L1 --> L2C
    L1 --> L2D
    
    L2A --> L3A
    L2B --> L3B
    L2C --> L3C
    L2D --> L3D
    
    L3A --> L4A
    L3B --> L4A
    L3C --> L4A
    L3C --> L3E
    L3D --> L3F
    
    L3E --> L4A
    L3F --> L4A
    
    L4A --> L4B
    L4B --> L4C
    
    L3A --> L5A
    L3C --> L5B
    L3E --> L5C
    L3B --> L5D
    
    style L1 fill:#4CAF50,stroke:#2E7D32,color:#fff
    style L4A fill:#336791,stroke:#1a3a52,color:#fff
    style L4B fill:#DC382D,stroke:#8b2119,color:#fff
```

## Cross-Module Data Sharing

### Shared Data Objects

```mermaid
graph LR
    subgraph "BTC Price Data"
        PRICE[BTC Price<br/>$92,477]
    end
    
    subgraph "Modules Using Price"
        CALC_M[Calculator]
        ANALYTICS_M[Analytics]
        TREASURY_M[Treasury]
        REPORT_M[Reports]
    end
    
    PRICE --> CALC_M
    PRICE --> ANALYTICS_M
    PRICE --> TREASURY_M
    PRICE --> REPORT_M
    
    subgraph "Telemetry Data"
        TELEM[Miner Telemetry<br/>Hashrate, Temp, Power]
    end
    
    subgraph "Modules Using Telemetry"
        HOST_M[Hosting]
        CURTAIL_M[Curtailment]
        ANOMALY_M[Anomaly Detection]
        REPORT_M2[Reports]
    end
    
    TELEM --> HOST_M
    TELEM --> CURTAIL_M
    TELEM --> ANOMALY_M
    TELEM --> REPORT_M2
    
    style PRICE fill:#FFD700,stroke:#FFA500,color:#000
    style TELEM fill:#87CEEB,stroke:#4682B4,color:#000
```

## Module Isolation & Boundaries

- **No Direct Module-to-Module Calls**: Modules communicate via shared services (Cache Manager, Database)
- **Event-Driven for Async**: Use Event Publisher for asynchronous cross-module communication
- **Shared Data Models**: SQLAlchemy models in `models.py` accessible to all modules
- **Service Layer Abstraction**: Business logic encapsulated in service classes
- **API Contracts**: Well-defined API endpoints for external integration
