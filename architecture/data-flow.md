# Data Flow & Process Flows

> **Audience**: Developers, system integrators, DevOps engineers

## 🔄 Overview

This document explains how data flows through the HashInsight Enterprise system, covering:
- End-to-end request processing
- Background data collection pipelines
- Real-time telemetry flows
- Event-driven architecture
- Cache invalidation patterns

## 📊 User-Initiated Request Flows

### Flow 1: Mining Calculator Request

**User Story**: User calculates profitability for Antminer S19 Pro

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Flask Route
    participant Calculator Service
    participant Cache Manager
    participant Database
    participant CoinGecko API
    participant Blockchain.info API
    
    User->>Browser: Enter miner model + electricity cost
    Browser->>Flask Route: POST /calculator/calculate
    
    Flask Route->>Calculator Service: calculate_profitability()
    
    par Fetch BTC Price
        Calculator Service->>Cache Manager: get('btc_price')
        alt Price in cache (< 5 min old)
            Cache Manager->>Calculator Service: Return cached price
        else Price stale/missing
            Calculator Service->>CoinGecko API: GET /simple/price
            CoinGecko API->>Calculator Service: $92,477
            Calculator Service->>Cache Manager: set('btc_price', $92,477, 300s)
        end
    and Fetch Network Difficulty
        Calculator Service->>Cache Manager: get('network_difficulty')
        alt Difficulty in cache
            Cache Manager->>Calculator Service: Return cached difficulty
        else Difficulty stale
            Calculator Service->>Blockchain.info API: GET /stats
            Blockchain.info API->>Calculator Service: 152.27T
            Calculator Service->>Cache Manager: set('network_difficulty', 152.27T, 900s)
        end
    and Fetch Miner Specs
        Calculator Service->>Database: SELECT * FROM miner_models WHERE id = 2
        Database->>Calculator Service: S19 Pro specs (110 TH/s, 3250W)
    end
    
    Calculator Service->>Calculator Service: Calculate profitability
    Note over Calculator Service: Daily Revenue = (110 TH/s / 991.6 EH/s) × 450 BTC<br/>Daily Cost = 3.25kW × 24h × $0.10<br/>Net Profit = Revenue - Cost<br/>ROI = Investment / Annual Profit
    
    Calculator Service->>Database: INSERT INTO calculation_history
    Calculator Service->>Flask Route: Return results
    Flask Route->>Browser: Render calculator.html with results
    Browser->>User: Display profitability metrics
```

**Key Metrics**:
- **Cache Hit Rate**: 85% for BTC price, 90% for difficulty
- **Response Time**: < 200ms with cache, < 1s without
- **API Calls**: 0-2 per request (cached vs. fresh)

### Flow 2: Hosting - Miner Detail Page

**User Story**: User views real-time performance of a specific miner

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Flask Route
    participant Hosting Service
    participant Database
    participant Cache
    
    User->>Browser: Click on miner S19PRO-00001
    Browser->>Flask Route: GET /hosting/miner/20/detail
    
    Flask Route->>Hosting Service: get_miner_details(miner_id=20)
    
    par Fetch Miner Info
        Hosting Service->>Database: SELECT * FROM hosting_miners WHERE id = 20
        Database->>Hosting Service: Miner details (model, site, status)
    and Fetch Telemetry (Last 24h)
        Hosting Service->>Cache: get('miner_20_telemetry_24h')
        alt Cache miss
            Hosting Service->>Database: SELECT * FROM miner_telemetry<br/>WHERE miner_id = 20<br/>AND recorded_at > NOW() - INTERVAL '24 hours'<br/>ORDER BY recorded_at
            Database->>Hosting Service: 24 rows of telemetry
            Hosting Service->>Cache: set('miner_20_telemetry_24h', data, 60s)
        else Cache hit
            Cache->>Hosting Service: Return cached telemetry
        end
    and Fetch Site Info
        Hosting Service->>Database: SELECT * FROM hosting_sites WHERE id = 5
        Database->>Hosting Service: HashPower MegaFarm 20MW details
    end
    
    Hosting Service->>Hosting Service: Calculate KPIs
    Note over Hosting Service: Avg Hashrate = SUM(hashrate) / COUNT(*)<br/>Avg Temp = SUM(temperature) / COUNT(*)<br/>Avg Power = SUM(power_consumption) / COUNT(*)<br/>Efficiency = Avg Hashrate / Avg Power
    
    Hosting Service->>Flask Route: Return miner + telemetry + KPIs
    Flask Route->>Browser: Render miner_detail.html
    Browser->>User: Display charts (Chart.js)
```

**Smart Telemetry API Fallback**:
```python
# If last 24h is empty, fallback to last 30 days
def get_miner_telemetry(miner_id):
    # Try last 24 hours
    telemetry = MinerTelemetry.query.filter(
        MinerTelemetry.miner_id == miner_id,
        MinerTelemetry.recorded_at > datetime.utcnow() - timedelta(hours=24)
    ).order_by(MinerTelemetry.recorded_at.desc()).limit(50).all()
    
    if not telemetry:
        # Fallback: last 30 days
        telemetry = MinerTelemetry.query.filter(
            MinerTelemetry.miner_id == miner_id,
            MinerTelemetry.recorded_at > datetime.utcnow() - timedelta(days=30)
        ).order_by(MinerTelemetry.recorded_at.desc()).limit(50).all()
    
    return telemetry
```

### Flow 3: CRM - Create Deal from Lead

**User Story**: Sales team converts a qualified lead into a deal

```mermaid
sequenceDiagram
    actor Sales Rep
    participant Browser
    participant Flask Route
    participant CRM Service
    participant Database
    participant Email Service
    participant Audit Log
    
    Sales Rep->>Browser: Click "Convert to Deal" on lead
    Browser->>Flask Route: POST /crm/leads/123/convert
    
    Flask Route->>CRM Service: convert_lead_to_deal(lead_id=123)
    
    CRM Service->>Database: BEGIN TRANSACTION
    
    CRM Service->>Database: SELECT * FROM crm_leads WHERE id = 123
    Database->>CRM Service: Lead data (name, email, company)
    
    CRM Service->>Database: INSERT INTO crm_deals<br/>(lead_id, title, value, stage, owner_id)
    Database->>CRM Service: Deal created (deal_id=456)
    
    CRM Service->>Database: UPDATE crm_leads SET status = 'converted'<br/>WHERE id = 123
    
    CRM Service->>Database: INSERT INTO crm_activities<br/>(deal_id, type='lead_converted', user_id)
    
    CRM Service->>Database: COMMIT
    
    par Post-Creation Actions
        CRM Service->>Email Service: Send notification to sales rep
        Email Service->>Sales Rep: Email: "New deal #456 created"
    and
        CRM Service->>Audit Log: Log action: "Lead 123 converted to Deal 456"
    end
    
    CRM Service->>Flask Route: Return deal details
    Flask Route->>Browser: Redirect to /crm/deals/456
    Browser->>Sales Rep: Display deal page
```

## 🔁 Background Data Collection Pipelines

### Pipeline 1: Real-Time Miner Telemetry Collection

**Frequency**: Every 60 seconds (APScheduler)

```mermaid
sequenceDiagram
    participant Scheduler
    participant Lock Manager
    participant CGMiner Collector
    participant Mining Hardware
    participant Database
    participant Cache
    participant Alerting
    
    Scheduler->>Lock Manager: Acquire lock 'cgminer_scheduler_lock'
    
    alt Lock acquired
        Lock Manager->>Scheduler: Lock granted (PID 8682)
        
        Scheduler->>CGMiner Collector: _collect_telemetry_job()
        
        CGMiner Collector->>Database: SELECT * FROM hosting_miners<br/>WHERE status = 'active'<br/>AND cgminer_enabled = true
        Database->>CGMiner Collector: 8 active miners
        
        loop For each miner
            CGMiner Collector->>Mining Hardware: TCP connect to 192.168.1.100:4028<br/>Send: {"command":"summary"}
            
            alt Connection successful
                Mining Hardware->>CGMiner Collector: JSON response<br/>{hashrate: 110.5, temp: 72.3, power: 3200}
                CGMiner Collector->>Database: INSERT INTO miner_telemetry<br/>(miner_id, hashrate, temp, power, recorded_at)
                
                CGMiner Collector->>Cache: set('miner_20_latest', data, 120s)
                
                CGMiner Collector->>Alerting: Check thresholds
                alt Temperature > 80°C
                    Alerting->>Email Service: Send alert email
                end
            else Connection timeout
                CGMiner Collector->>Database: INSERT INTO miner_operation_log<br/>(miner_id, operation='connection_failed')
                CGMiner Collector->>Alerting: Mark miner as offline
            end
        end
        
        CGMiner Collector->>Scheduler: Report completion (8 processed)
        Scheduler->>Lock Manager: Refresh heartbeat
        
    else Lock held by another process
        Lock Manager->>Scheduler: Lock denied (PID 7860 owns it)
        Scheduler->>Scheduler: Skip execution (prevent duplicates)
    end
```

**Distributed Lock Mechanism**:
```python
class SchedulerLock:
    def acquire_lock(self, key, timeout=60):
        # Check if lock exists and not expired
        existing_lock = SchedulerLockModel.query.filter_by(lock_key=key).first()
        
        if existing_lock and not existing_lock.is_expired:
            return None  # Another process holds the lock
        
        # Create or update lock
        lock = SchedulerLockModel(
            lock_key=key,
            process_id=os.getpid(),
            hostname=socket.gethostname(),
            expires_at=datetime.utcnow() + timedelta(seconds=timeout)
        )
        db.session.merge(lock)
        db.session.commit()
        return lock
```

### Pipeline 2: Market Data Analytics Collection

**Frequency**: Every 15 minutes

```mermaid
graph TB
    START([Scheduler Trigger - Every 15 min])
    
    START --> COLLECT_PRICES[Collect BTC Prices]
    START --> COLLECT_HASHRATE[Collect Network Hashrate]
    START --> COLLECT_EXCHANGE[Collect Exchange Data]
    
    subgraph "Price Collection"
        COLLECT_PRICES --> COINGECKO[CoinGecko API]
        COINGECKO --> FALLBACK1{Success?}
        FALLBACK1 -->|No| BLOCKCHAIN_INFO[Blockchain.info API]
        FALLBACK1 -->|Yes| AGGREGATE_PRICE
        BLOCKCHAIN_INFO --> FALLBACK2{Success?}
        FALLBACK2 -->|No| MEMPOOL[Mempool.space API]
        FALLBACK2 -->|Yes| AGGREGATE_PRICE
        MEMPOOL --> AGGREGATE_PRICE[Aggregate & Average]
    end
    
    subgraph "Hashrate Collection"
        COLLECT_HASHRATE --> BLOCKCHAIN_STATS[Blockchain.info Stats]
        BLOCKCHAIN_STATS --> ANKR[Ankr RPC Fallback]
        ANKR --> HASHRATE_RESULT[Calculate EH/s]
    end
    
    subgraph "Exchange Data"
        COLLECT_EXCHANGE --> BINANCE_API[Binance API]
        COLLECT_EXCHANGE --> OKX_API[OKX API]
        COLLECT_EXCHANGE --> DERIBIT_API[Deribit API]
        COLLECT_EXCHANGE --> BYBIT_API[Bybit API]
        
        BINANCE_API --> MULTI_EXCHANGE_AGG
        OKX_API --> MULTI_EXCHANGE_AGG
        DERIBIT_API --> MULTI_EXCHANGE_AGG
        BYBIT_API --> MULTI_EXCHANGE_AGG[Aggregate 4 Exchanges]
    end
    
    AGGREGATE_PRICE --> SAVE_DB[(Save to Database)]
    HASHRATE_RESULT --> SAVE_DB
    MULTI_EXCHANGE_AGG --> SAVE_DB
    
    SAVE_DB --> CALC_INDICATORS[Calculate Technical Indicators]
    
    CALC_INDICATORS --> RSI[RSI]
    CALC_INDICATORS --> MACD[MACD]
    CALC_INDICATORS --> BB[Bollinger Bands]
    CALC_INDICATORS --> EMA[EMA/SMA]
    
    RSI --> SAVE_INDICATORS[(Save Indicators)]
    MACD --> SAVE_INDICATORS
    BB --> SAVE_INDICATORS
    EMA --> SAVE_INDICATORS
    
    SAVE_INDICATORS --> UPDATE_CACHE[Update Cache]
    UPDATE_CACHE --> END([End])
```

**Code Implementation**:
```python
# modules/analytics/engines/analytics_engine.py
class AnalyticsEngine:
    def collect_and_analyze(self):
        # Collect market data
        btc_price = self._collect_btc_price()
        hashrate = self._collect_network_hashrate()
        difficulty = self._collect_difficulty()
        exchange_data = self._collect_exchange_data()
        
        # Save to database
        market_data = MarketAnalytics(
            btc_price=btc_price,
            network_hashrate=hashrate,
            network_difficulty=difficulty,
            volume_24h=exchange_data['total_volume']
        )
        db.session.add(market_data)
        
        # Calculate technical indicators
        indicators = self._calculate_indicators()
        db.session.add(indicators)
        
        db.session.commit()
        
        # Update cache
        cache_manager.set('latest_btc_price', btc_price, timeout=300)
        cache_manager.set('latest_market_data', market_data.to_dict(), timeout=600)
```

### Pipeline 3: Smart Curtailment Automation

**Frequency**: Every 1 minute (check for pending plans)

```mermaid
sequenceDiagram
    participant Scheduler
    participant Curtailment Engine
    participant Database
    participant Optimization Engine
    participant Miner API
    participant Notification Service
    
    Scheduler->>Curtailment Engine: _check_pending_plans()
    
    Curtailment Engine->>Database: SELECT * FROM curtailment_plans<br/>WHERE status = 'pending'<br/>AND scheduled_time <= NOW()
    Database->>Curtailment Engine: 1 plan (reduce 5 MW at site 5)
    
    Curtailment Engine->>Optimization Engine: recommend_shutdown(site_id=5, target_mw=5)
    
    Optimization Engine->>Database: SELECT * FROM hosting_miners<br/>WHERE site_id = 5 AND status = 'active'
    Database->>Optimization Engine: 6000 active miners
    
    Optimization Engine->>Optimization Engine: Calculate efficiency scores
    Note over Optimization Engine: For each miner:<br/>efficiency = hashrate / power_consumption<br/>Sort by efficiency ASC (worst first)
    
    Optimization Engine->>Optimization Engine: PuLP Linear Programming
    Note over Optimization Engine: Minimize: Hashrate Loss<br/>Subject to: Power Reduction >= 5000 kW<br/>Variables: shutdown[miner_id] binary
    
    Optimization Engine->>Curtailment Engine: Recommend 1538 miners to shutdown<br/>Total power: 5.00 MW, Hashrate loss: 169.18 TH/s
    
    Curtailment Engine->>Database: BEGIN TRANSACTION
    
    loop For each recommended miner
        Curtailment Engine->>Miner API: POST /api/miner/{id}/shutdown
        Miner API->>Curtailment Engine: Success
        
        Curtailment Engine->>Database: UPDATE hosting_miners<br/>SET status = 'curtailed'<br/>WHERE id = miner_id
        
        Curtailment Engine->>Database: INSERT INTO miner_operation_log<br/>(miner_id, operation='curtailment_shutdown')
    end
    
    Curtailment Engine->>Database: UPDATE curtailment_plans<br/>SET status = 'executed', executed_at = NOW()
    
    Curtailment Engine->>Database: COMMIT
    
    Curtailment Engine->>Notification Service: Send execution report
    Notification Service->>Farm Manager: Email: "Curtailment executed: 5 MW reduced"
```

## 🔔 Event-Driven Architecture

### Intelligence Layer Event Publishing

```mermaid
graph LR
    subgraph "Database Operations"
        INSERT[INSERT INTO users]
        UPDATE[UPDATE hosting_miners]
        DELETE[DELETE FROM deals]
    end
    
    subgraph "SQLAlchemy Event Hooks"
        AFTER_INSERT[after_insert hook]
        AFTER_UPDATE[after_update hook]
        AFTER_DELETE[after_delete hook]
    end
    
    subgraph "Intelligence Layer"
        EVENT_PUBLISHER[Event Publisher]
        OUTBOX[Outbox Table]
    end
    
    subgraph "External Consumers"
        CDC[Change Data Capture]
        WEBHOOK[Webhook Subscribers]
        ANALYTICS[External Analytics]
    end
    
    INSERT --> AFTER_INSERT
    UPDATE --> AFTER_UPDATE
    DELETE --> AFTER_DELETE
    
    AFTER_INSERT --> EVENT_PUBLISHER
    AFTER_UPDATE --> EVENT_PUBLISHER
    AFTER_DELETE --> EVENT_PUBLISHER
    
    EVENT_PUBLISHER --> OUTBOX
    
    OUTBOX --> CDC
    OUTBOX --> WEBHOOK
    OUTBOX --> ANALYTICS
```

**Implementation**:
```python
# intelligence/db_hooks.py
from sqlalchemy import event

def register_hooks(db):
    # User events
    @event.listens_for(UserMiner, 'after_insert')
    def publish_user_miner_created(mapper, connection, target):
        publish_event('user_miner.created', {
            'user_id': target.user_id,
            'miner_id': target.miner_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Miner events
    @event.listens_for(HostingMiner, 'after_update')
    def publish_miner_updated(mapper, connection, target):
        if target.status == 'offline':
            publish_event('miner.offline', {
                'miner_id': target.id,
                'site_id': target.site_id,
                'last_seen': target.updated_at.isoformat()
            })

def publish_event(event_type, payload):
    outbox_event = OutboxEvent(
        event_type=event_type,
        payload=json.dumps(payload),
        status='pending'
    )
    db.session.add(outbox_event)
```

## 💾 Cache Invalidation Patterns

### Pattern 1: Time-Based Expiration (TTL)

```python
# Automatically expires after timeout
cache_manager.set('btc_price', 92477, timeout=300)  # 5 minutes

# Next request after 5 minutes will miss cache
price = cache_manager.get('btc_price')  # None (expired)
```

### Pattern 2: Write-Through Invalidation

```python
# When data changes, update both database and cache
def update_miner_status(miner_id, new_status):
    # Update database
    miner = HostingMiner.query.get(miner_id)
    miner.status = new_status
    db.session.commit()
    
    # Invalidate cache
    cache_manager.delete(f'miner_{miner_id}_details')
    cache_manager.delete(f'site_{miner.site_id}_active_miners')
```

### Pattern 3: Event-Driven Invalidation

```python
@event.listens_for(MinerTelemetry, 'after_insert')
def invalidate_telemetry_cache(mapper, connection, target):
    # Clear cached telemetry when new data arrives
    cache_manager.delete(f'miner_{target.miner_id}_telemetry_24h')
    cache_manager.delete(f'site_{target.miner.site_id}_telemetry_summary')
```

## 🔄 Data Consistency Patterns

### Database Transactions

```python
# Atomic operations with rollback on error
try:
    db.session.begin()
    
    # Multiple related operations
    deal = CRMDeal(...)
    db.session.add(deal)
    
    lead.status = 'converted'
    
    activity = CRMActivity(deal_id=deal.id, ...)
    db.session.add(activity)
    
    db.session.commit()  # All or nothing
    
except Exception as e:
    db.session.rollback()
    logger.error(f"Transaction failed: {e}")
    raise
```

### Distributed Lock for Background Jobs

```python
# Prevent duplicate execution across multiple workers
with scheduler_lock.acquire('telemetry_collection'):
    if scheduler_lock.is_locked():
        # Execute telemetry collection
        collect_all_telemetry()
    else:
        # Another worker is running it, skip
        pass
```

---

*This document provides comprehensive data flow patterns. For module-specific flows, refer to [Module Guide](./module-guide.md).*
