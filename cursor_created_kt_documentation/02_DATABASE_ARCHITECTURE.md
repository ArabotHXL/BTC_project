# HashInsight Enterprise Platform - Database Architecture

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Target Audience:** Database Administrators, Backend Developers, Data Engineers

---

## Table of Contents

1. [Database Overview](#database-overview)
2. [Complete Table Reference](#complete-table-reference)
3. [Table Update Patterns](#table-update-patterns)
4. [Business Logic to Database Mapping](#business-logic-to-database-mapping)
5. [Data Relationships](#data-relationships)
6. [Indexes and Performance](#indexes-and-performance)
7. [Data Retention Policies](#data-retention-policies)

---

## Database Overview

### Database Technology
- **Type:** PostgreSQL 15+
- **Hosting:** Neon (cloud-managed)
- **ORM:** SQLAlchemy 2.0+ with DeclarativeBase
- **Connection:** Via `DATABASE_URL` environment variable
- **Connection Pool:** 10 base connections, 20 max overflow

### Database Statistics
- **Total Tables:** 80+ tables
- **Core Business Tables:** 50+ tables
- **CDC Platform Tables:** 3 tables
- **Control Plane Tables:** 10+ tables
- **Device Encryption Tables:** 4+ tables
- **Remote Control Tables:** 2+ tables

---

## Complete Table Reference

### 1. Authentication & User Management

#### `user_access`
**Purpose:** User accounts, authentication, and access control

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | User ID | Auto-increment |
| `name` | VARCHAR(100) | NOT NULL | User full name | Manual update |
| `email` | VARCHAR(256) | UNIQUE, NOT NULL | Email address | Manual update |
| `username` | VARCHAR(50) | UNIQUE | Username | Manual update |
| `password_hash` | VARCHAR(512) | | Hashed password | On password change |
| `is_email_verified` | BOOLEAN | DEFAULT FALSE | Email verification status | On email verification |
| `email_verification_token` | VARCHAR(100) | | Verification token | On registration |
| `company` | VARCHAR(200) | | Company name | Manual update |
| `position` | VARCHAR(100) | | Job position | Manual update |
| `role` | VARCHAR(20) | DEFAULT 'guest' | User role | Admin update |
| `subscription_plan` | VARCHAR(20) | DEFAULT 'free' | Subscription tier | On subscription change |
| `access_days` | INTEGER | DEFAULT 30 | Access duration | Admin update |
| `expires_at` | TIMESTAMP | | Access expiration | Calculated from access_days |
| `last_login` | TIMESTAMP | | Last login time | On login |
| `wallet_address` | VARCHAR(42) | UNIQUE | Web3 wallet address | On wallet linking |
| `wallet_verified` | BOOLEAN | DEFAULT FALSE | Wallet verification | On wallet verification |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `created_by_id` | INTEGER | FK to user_access | Creator user ID | On creation |

**Update Logic:**
- **On Registration:** INSERT new user with `is_email_verified=False`, generate token
- **On Email Verification:** UPDATE `is_email_verified=True`, clear token
- **On Login:** UPDATE `last_login=now()`
- **On Password Change:** UPDATE `password_hash` with new hash
- **On Subscription Change:** UPDATE `subscription_plan`, recalculate `expires_at`

**Stored Data:**
- User authentication credentials
- Access control information
- Subscription status
- Web3 wallet integration

---

#### `login_records`
**Purpose:** Track user login attempts and history

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Record ID | Auto-increment |
| `email` | VARCHAR(256) | NOT NULL | User email | On login attempt |
| `login_time` | TIMESTAMP | DEFAULT NOW() | Login timestamp | Auto |
| `successful` | BOOLEAN | DEFAULT TRUE | Login success | On login attempt |
| `ip_address` | VARCHAR(50) | | Client IP address | On login attempt |
| `login_location` | VARCHAR(512) | | Geolocation | On login attempt |

**Update Logic:**
- **On Login Attempt:** INSERT new record with success/failure status
- **On Successful Login:** INSERT with `successful=True`
- **On Failed Login:** INSERT with `successful=False`

**Stored Data:**
- Login history for security auditing
- Failed login attempts for security monitoring
- IP addresses for fraud detection

---

### 2. Mining Calculator & Models

#### `miner_models`
**Purpose:** ASIC miner model specifications and reference data

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Model ID | Auto-increment |
| `model_name` | VARCHAR(100) | UNIQUE, NOT NULL | Miner model name | Manual/admin |
| `manufacturer` | VARCHAR(50) | NOT NULL | Manufacturer name | Manual/admin |
| `reference_hashrate` | FLOAT | NOT NULL | Hashrate in TH/s | Manual/admin |
| `reference_power` | INTEGER | NOT NULL | Power in watts | Manual/admin |
| `reference_efficiency` | FLOAT | | Efficiency W/TH | Auto-calculated |
| `reference_price` | FLOAT | | Reference price USD | Manual/admin |
| `release_date` | DATE | | Release date | Manual/admin |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status | Admin update |
| `is_liquid_cooled` | BOOLEAN | DEFAULT FALSE | Liquid cooling | Manual/admin |
| `chip_type` | VARCHAR(50) | | Chip type | Manual/admin |
| `operating_temp_min` | INTEGER | | Min operating temp | Manual/admin |
| `operating_temp_max` | INTEGER | | Max operating temp | Manual/admin |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Update Logic:**
- **On Model Addition:** INSERT new model, auto-calculate `reference_efficiency`
- **On Model Update:** UPDATE fields, auto-update `updated_at`
- **On Model Deactivation:** UPDATE `is_active=False` (soft delete)

**Stored Data:**
- Reference specifications for 42+ ASIC miner models
- Technical specifications for calculations
- Pricing and availability information

---

#### `user_miners`
**Purpose:** User's actual miner configurations and inventory

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | User miner ID | Auto-increment |
| `user_id` | INTEGER | FK to user_access | User owner | On creation |
| `miner_model_id` | INTEGER | FK to miner_models | Miner model | On creation |
| `custom_name` | VARCHAR(100) | | User custom name | User update |
| `quantity` | INTEGER | DEFAULT 1 | Number of units | User update |
| `actual_hashrate` | FLOAT | NOT NULL | Actual hashrate TH/s | User update |
| `actual_power` | INTEGER | NOT NULL | Actual power W | User update |
| `actual_price` | FLOAT | NOT NULL | Purchase price USD | User update |
| `electricity_cost` | FLOAT | NOT NULL | Cost per kWh | User update |
| `decay_rate_monthly` | FLOAT | DEFAULT 0.5 | Monthly decay % | User update |
| `status` | VARCHAR(20) | DEFAULT 'active' | Status | User/system update |
| `location` | VARCHAR(200) | | Physical location | User update |
| `purchase_date` | DATE | | Purchase date | User update |
| `original_hashrate` | FLOAT | | Original hashrate | On creation |
| `last_maintenance_date` | DATE | | Last maintenance | On maintenance |
| `maintenance_count` | INTEGER | DEFAULT 0 | Maintenance count | On maintenance |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Update Logic:**
- **On Miner Addition:** INSERT new record, set `original_hashrate=actual_hashrate`
- **On Miner Update:** UPDATE fields, auto-update `updated_at`
- **On Maintenance:** UPDATE `last_maintenance_date`, increment `maintenance_count`
- **On Calculation:** READ only, no updates
- **On Portfolio Recalculation:** READ for calculations, may trigger CDC events

**Stored Data:**
- User's miner inventory
- Actual specifications (may differ from reference)
- Maintenance history
- Cost basis for ROI calculations

**Business Logic Updates:**
```python
# When user adds a miner
user_miner = UserMiner(
    user_id=user_id,
    miner_model_id=model_id,
    actual_hashrate=hashrate,
    actual_power=power,
    actual_price=price,
    electricity_cost=cost,
    quantity=quantity
)
db.session.add(user_miner)
db.session.commit()
# Triggers: CDC event 'user_miner.created'
```

---

#### `network_snapshots`
**Purpose:** Historical Bitcoin network data snapshots

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Snapshot ID | Auto-increment |
| `recorded_at` | TIMESTAMP | DEFAULT NOW(), INDEX | Snapshot time | Auto |
| `btc_price` | FLOAT | NOT NULL | BTC price USD | Scheduler |
| `network_difficulty` | FLOAT | NOT NULL | Network difficulty T | Scheduler |
| `network_hashrate` | FLOAT | NOT NULL | Network hashrate EH/s | Scheduler |
| `block_reward` | FLOAT | DEFAULT 3.125 | Block reward BTC | Scheduler |
| `price_source` | VARCHAR(50) | DEFAULT 'coingecko' | Price API source | Scheduler |
| `data_source` | VARCHAR(50) | DEFAULT 'blockchain.info' | Data API source | Scheduler |
| `is_valid` | BOOLEAN | DEFAULT TRUE | Data validity | Scheduler |
| `api_response_time` | FLOAT | | API response time sec | Scheduler |

**Update Logic:**
- **On Scheduled Collection (every 10 minutes):** INSERT new snapshot
- **On Data Validation:** UPDATE `is_valid` if data quality check fails
- **On Data Cleanup:** DELETE old snapshots (retention policy: max 10 per day)

**Stored Data:**
- Historical Bitcoin network metrics
- Price history for calculations
- Network difficulty and hashrate trends
- Data quality metadata

**Business Logic Updates:**
```python
# Scheduled data collection (scheduler.py)
snapshot = NetworkSnapshot(
    btc_price=fetch_btc_price(),
    network_difficulty=fetch_difficulty(),
    network_hashrate=fetch_hashrate(),
    block_reward=3.125,
    price_source='coingecko',
    data_source='blockchain.info'
)
db.session.add(snapshot)
db.session.commit()
# Triggers: CDC event 'network.snapshot_created'
```

---

### 3. CRM System Tables

#### `crm_customers`
**Purpose:** Customer company information

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Customer ID | Auto-increment |
| `company_name` | VARCHAR(200) | NOT NULL | Company name | Manual update |
| `email` | VARCHAR(256) | UNIQUE | Primary email | Manual update |
| `phone` | VARCHAR(50) | | Phone number | Manual update |
| `address` | TEXT | | Physical address | Manual update |
| `mining_capacity_mw` | FLOAT | | Mining capacity MW | Manual update |
| `status` | VARCHAR(20) | DEFAULT 'active' | Customer status | Manual update |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Update Logic:**
- **On Customer Creation:** INSERT new customer
- **On Customer Update:** UPDATE fields, auto-update `updated_at`
- **On Customer Deactivation:** UPDATE `status='inactive'`

**Stored Data:**
- Company information
- Contact details
- Mining capacity
- Customer status

---

#### `crm_leads`
**Purpose:** Sales leads and opportunities

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Lead ID | Auto-increment |
| `customer_id` | INTEGER | FK to crm_customers | Associated customer | On creation |
| `title` | VARCHAR(200) | NOT NULL | Lead title | Manual update |
| `status` | ENUM | DEFAULT 'NEW' | Lead status | Manual/automated |
| `value` | FLOAT | | Estimated value USD | Manual update |
| `source` | VARCHAR(100) | | Lead source | Manual update |
| `assigned_to` | INTEGER | FK to user_access | Assigned user | Manual update |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Status Values:** NEW → CONTACTED → QUALIFIED → NEGOTIATION → WON/LOST

**Update Logic:**
- **On Lead Creation:** INSERT with `status='NEW'`
- **On Status Change:** UPDATE `status`, auto-update `updated_at`
- **On Lead Conversion:** UPDATE `status='WON'`, create Deal record
- **On Lead Loss:** UPDATE `status='LOST'`

**Stored Data:**
- Sales pipeline data
- Opportunity tracking
- Conversion history

---

#### `crm_deals`
**Purpose:** Sales deals and transactions

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Deal ID | Auto-increment |
| `customer_id` | INTEGER | FK to crm_customers | Customer | On creation |
| `lead_id` | INTEGER | FK to crm_leads | Source lead | On conversion |
| `title` | VARCHAR(200) | NOT NULL | Deal title | Manual update |
| `status` | ENUM | DEFAULT 'DRAFT' | Deal status | Manual/automated |
| `value` | FLOAT | NOT NULL | Deal value USD | Manual update |
| `expected_close_date` | DATE | | Expected close date | Manual update |
| `actual_close_date` | DATE | | Actual close date | On completion |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Status Values:** DRAFT → PENDING → APPROVED → SIGNED → COMPLETED/CANCELED

**Update Logic:**
- **On Deal Creation:** INSERT with `status='DRAFT'`
- **On Deal Approval:** UPDATE `status='APPROVED'`
- **On Deal Signing:** UPDATE `status='SIGNED'`, set `actual_close_date`
- **On Deal Completion:** UPDATE `status='COMPLETED'`

**Stored Data:**
- Sales transaction data
- Deal pipeline tracking
- Revenue forecasting data

---

#### `crm_invoices`
**Purpose:** Customer invoices and billing

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Invoice ID | Auto-increment |
| `customer_id` | INTEGER | FK to crm_customers | Customer | On creation |
| `deal_id` | INTEGER | FK to crm_deals | Associated deal | On creation |
| `invoice_number` | VARCHAR(50) | UNIQUE | Invoice number | Auto-generated |
| `amount` | FLOAT | NOT NULL | Invoice amount | Manual update |
| `status` | ENUM | DEFAULT 'DRAFT' | Invoice status | Manual/automated |
| `due_date` | DATE | | Due date | Manual update |
| `paid_date` | DATE | | Payment date | On payment |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Status Values:** DRAFT → SENT → PAID → OVERDUE → CANCELLED

**Update Logic:**
- **On Invoice Creation:** INSERT with `status='DRAFT'`, auto-generate `invoice_number`
- **On Invoice Sending:** UPDATE `status='SENT'`
- **On Payment:** UPDATE `status='PAID'`, set `paid_date`
- **On Overdue:** UPDATE `status='OVERDUE'` (automated check)

**Stored Data:**
- Invoice records
- Payment tracking
- Revenue recognition data

---

### 4. Hosting Services Tables

#### `hosting_sites`
**Purpose:** Mining facility/site information

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Site ID | Auto-increment |
| `name` | VARCHAR(200) | NOT NULL | Site name | Manual update |
| `location` | VARCHAR(500) | | Physical location | Manual update |
| `capacity_mw` | FLOAT | NOT NULL | Total capacity MW | Manual update |
| `electricity_rate` | FLOAT | NOT NULL | Electricity rate $/kWh | Manual update |
| `status` | VARCHAR(20) | DEFAULT 'active' | Site status | Manual/system update |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Update Logic:**
- **On Site Creation:** INSERT new site
- **On Site Update:** UPDATE fields, auto-update `updated_at`
- **On Site Deactivation:** UPDATE `status='inactive'`

**Stored Data:**
- Mining facility information
- Capacity and power rates
- Site status

---

#### `hosting_miners`
**Purpose:** Deployed miners at hosting sites

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Miner ID | Auto-increment |
| `site_id` | INTEGER | FK to hosting_sites | Hosting site | On deployment |
| `client_id` | INTEGER | FK to crm_customers | Customer owner | On deployment |
| `serial_number` | VARCHAR(100) | UNIQUE | Miner serial number | On deployment |
| `model` | VARCHAR(100) | NOT NULL | Miner model | On deployment |
| `status` | VARCHAR(20) | DEFAULT 'active' | Miner status | System/automated |
| `deployed_at` | TIMESTAMP | DEFAULT NOW() | Deployment time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Update Logic:**
- **On Miner Deployment:** INSERT new miner record
- **On Status Change:** UPDATE `status` (active/offline/maintenance/curtailed)
- **On Telemetry Update:** No direct update, but triggers status changes

**Stored Data:**
- Deployed miner inventory
- Customer ownership
- Miner status tracking

**Business Logic Updates:**
```python
# When miner is deployed
miner = HostingMiner(
    site_id=site_id,
    client_id=client_id,
    serial_number=serial,
    model=model_name,
    status='active'
)
db.session.add(miner)
db.session.commit()
# Triggers: CDC event 'miner.deployed'
```

---

#### `miner_telemetry`
**Purpose:** Real-time miner performance data

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Telemetry ID | Auto-increment |
| `miner_id` | INTEGER | FK to hosting_miners | Miner | On telemetry collection |
| `hashrate_actual` | FLOAT | | Actual hashrate TH/s | Every 5 minutes |
| `temperature` | FLOAT | | Temperature °C | Every 5 minutes |
| `power_consumption` | FLOAT | | Power W | Every 5 minutes |
| `uptime` | INTEGER | | Uptime seconds | Every 5 minutes |
| `fan_speed` | INTEGER | | Fan speed RPM | Every 5 minutes |
| `recorded_at` | TIMESTAMP | DEFAULT NOW(), INDEX | Collection time | Auto |

**Update Logic:**
- **On Telemetry Collection (every 5 minutes):** INSERT new telemetry record
- **On Data Aggregation:** Data moved to `telemetry_history_5min` and `telemetry_daily`
- **On Data Retention:** Old raw data deleted (24-hour retention)

**Stored Data:**
- Real-time miner performance metrics
- Health monitoring data
- Performance trends

**Business Logic Updates:**
```python
# Telemetry collection (services/telemetry_storage.py)
telemetry = MinerTelemetry(
    miner_id=miner_id,
    hashrate_actual=hashrate,
    temperature=temp,
    power_consumption=power,
    uptime=uptime
)
db.session.add(telemetry)
db.session.commit()
# Triggers: Status update if hashrate drops, CDC event 'miner.telemetry_updated'
```

---

#### `hosting_tickets`
**Purpose:** Customer support tickets

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Ticket ID | Auto-increment |
| `client_id` | INTEGER | FK to crm_customers | Customer | On creation |
| `site_id` | INTEGER | FK to hosting_sites | Site | On creation |
| `type` | VARCHAR(50) | | Ticket type | On creation |
| `priority` | VARCHAR(20) | DEFAULT 'medium' | Priority | Manual update |
| `status` | VARCHAR(20) | DEFAULT 'open' | Ticket status | Manual/automated |
| `subject` | VARCHAR(200) | NOT NULL | Subject | On creation |
| `description` | TEXT | | Description | On creation |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `resolved_at` | TIMESTAMP | | Resolution time | On resolution |

**Update Logic:**
- **On Ticket Creation:** INSERT with `status='open'`
- **On Ticket Resolution:** UPDATE `status='resolved'`, set `resolved_at`
- **On Ticket Update:** UPDATE fields, auto-update timestamps

**Stored Data:**
- Customer support requests
- Issue tracking
- Resolution history

---

### 5. Intelligence Layer Tables

#### `forecast_daily`
**Purpose:** AI-generated price and difficulty forecasts

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Forecast ID | Auto-increment |
| `user_id` | INTEGER | FK to user_access | User | On forecast generation |
| `forecast_date` | DATE | NOT NULL, INDEX | Forecast date | On generation |
| `btc_price_predicted` | FLOAT | NOT NULL | Predicted price | ARIMA model |
| `btc_price_lower_bound` | FLOAT | | Lower confidence bound | ARIMA model |
| `btc_price_upper_bound` | FLOAT | | Upper confidence bound | ARIMA model |
| `difficulty_predicted` | FLOAT | | Predicted difficulty | ARIMA model |
| `model_params` | JSONB | | Model parameters | ARIMA model |
| `rmse` | FLOAT | | Root mean square error | ARIMA model |
| `mae` | FLOAT | | Mean absolute error | ARIMA model |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Generation time | Auto |
| `expires_at` | TIMESTAMP | | Expiration time | Auto (30 days) |

**Update Logic:**
- **On Forecast Generation:** INSERT new forecast (7 days ahead)
- **On Forecast Refresh:** DELETE old forecasts, INSERT new ones
- **On Forecast Expiration:** DELETE expired forecasts (cleanup job)

**Stored Data:**
- 7-day price predictions
- Confidence intervals
- Model accuracy metrics

**Business Logic Updates:**
```python
# Forecast generation (intelligence/api/forecast_api.py)
forecast = ForecastDaily(
    user_id=user_id,
    forecast_date=date,
    btc_price_predicted=predicted_price,
    btc_price_lower_bound=lower_bound,
    btc_price_upper_bound=upper_bound,
    model_params=model_params,
    rmse=rmse,
    mae=mae
)
db.session.add(forecast)
db.session.commit()
# Triggers: CDC event 'intelligence.forecast_generated'
```

---

#### `ops_schedule`
**Purpose:** Power curtailment optimization schedules

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Schedule ID | Auto-increment |
| `user_id` | INTEGER | FK to user_access | User | On schedule creation |
| `target_date` | DATE | NOT NULL, INDEX | Target date | On creation |
| `hour` | INTEGER | NOT NULL | Hour (0-23) | On creation |
| `miner_id` | INTEGER | FK to user_miners | Miner | On creation |
| `action` | ENUM | NOT NULL | Action (shutdown/startup) | On creation |
| `expected_profit` | FLOAT | | Expected profit | Optimization |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |

**Update Logic:**
- **On Optimization Request:** INSERT schedule entries for each hour/miner
- **On Schedule Execution:** UPDATE status, record actual results
- **On Schedule Completion:** Mark as completed

**Stored Data:**
- Hourly optimization schedules
- Miner shutdown/startup plans
- Profit optimization data

**Business Logic Updates:**
```python
# Optimization schedule creation (intelligence/api/optimize_api.py)
schedule = OpsSchedule(
    user_id=user_id,
    target_date=date,
    hour=hour,
    miner_id=miner_id,
    action='shutdown',
    expected_profit=profit
)
db.session.add(schedule)
db.session.commit()
# Triggers: CDC event 'ops.schedule_created'
```

---

### 6. CDC Platform Tables

#### `event_outbox`
**Purpose:** Transactional outbox for event-driven architecture

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Event ID | Auto-increment |
| `kind` | VARCHAR(100) | NOT NULL, INDEX | Event type | On event creation |
| `user_id` | INTEGER | FK to user_access | User | On event creation |
| `tenant_id` | INTEGER | | Tenant ID | On event creation |
| `entity_id` | INTEGER | | Entity ID | On event creation |
| `payload` | JSONB | NOT NULL | Event data | On event creation |
| `idempotency_key` | VARCHAR(255) | UNIQUE | Idempotency key | On event creation |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `processed` | BOOLEAN | DEFAULT FALSE | Processed flag | Debezium |

**Update Logic:**
- **On Business Event:** INSERT into outbox in same transaction
- **On CDC Processing:** UPDATE `processed=True` (Debezium)
- **On Event Publishing:** Event consumed by Kafka

**Stored Data:**
- Business events for CDC
- Event payloads
- Idempotency tracking

**Business Logic Updates:**
```python
# Event creation (cdc-platform/core/infra/outbox.py)
event = EventOutbox(
    kind='miner.portfolio_updated',
    user_id=user_id,
    payload=json.dumps(payload),
    idempotency_key=generate_key()
)
db.session.add(event)
# Same transaction as business data update
db.session.commit()
# Debezium captures and publishes to Kafka
```

---

#### `event_inbox`
**Purpose:** Consumer idempotency tracking

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `event_id` | INTEGER | PRIMARY KEY | Event ID | On processing |
| `consumer_group` | VARCHAR(100) | NOT NULL | Consumer group | On processing |
| `processed_at` | TIMESTAMP | DEFAULT NOW() | Processing time | Auto |

**Update Logic:**
- **On Event Processing:** INSERT to mark as processed
- **On Duplicate Check:** SELECT to check if already processed

**Stored Data:**
- Processed event tracking
- Idempotency guarantees

---

#### `event_dlq`
**Purpose:** Dead letter queue for failed events

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | DLQ ID | Auto-increment |
| `event_id` | INTEGER | | Original event ID | On failure |
| `kind` | VARCHAR(100) | | Event type | On failure |
| `user_id` | INTEGER | | User ID | On failure |
| `payload` | JSONB | | Event payload | On failure |
| `error_message` | TEXT | | Error message | On failure |
| `retry_count` | INTEGER | DEFAULT 0 | Retry attempts | On retry |
| `failed_at` | TIMESTAMP | DEFAULT NOW() | Failure time | Auto |
| `replayed_at` | TIMESTAMP | | Replay time | On replay |

**Update Logic:**
- **On Processing Failure:** INSERT into DLQ
- **On Retry:** UPDATE `retry_count`
- **On Replay:** UPDATE `replayed_at`

**Stored Data:**
- Failed event records
- Error information
- Retry tracking

---

### 7. Control Plane Tables

#### `zones`
**Purpose:** Site-level operational boundaries

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Zone ID | Auto-increment |
| `site_id` | INTEGER | FK to hosting_sites | Site | On creation |
| `name` | VARCHAR(200) | NOT NULL | Zone name | Manual update |
| `capacity_mw` | FLOAT | NOT NULL | Zone capacity | Manual update |
| `status` | VARCHAR(20) | DEFAULT 'active' | Zone status | Manual update |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |

**Update Logic:**
- **On Zone Creation:** INSERT new zone
- **On Zone Update:** UPDATE fields

**Stored Data:**
- Zone partitioning for multi-tenant isolation
- Capacity management

---

#### `price_plans`
**Purpose:** Hosting price plans

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Plan ID | Auto-increment |
| `zone_id` | INTEGER | FK to zones | Zone | On creation |
| `name` | VARCHAR(200) | NOT NULL | Plan name | Manual update |
| `price_per_kw_monthly` | FLOAT | NOT NULL | Price per kW/month | Manual update |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status | Manual update |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |

**Update Logic:**
- **On Plan Creation:** INSERT new plan
- **On Plan Update:** Create new version (immutable history)

**Stored Data:**
- Pricing plans
- Version history (via `price_plan_versions`)

---

#### `demand_15min`
**Purpose:** 15-minute interval power demand metering

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Record ID | Auto-increment |
| `zone_id` | INTEGER | FK to zones | Zone | On collection |
| `interval_start` | TIMESTAMP | NOT NULL, INDEX | Interval start | Every 15 minutes |
| `demand_kw` | FLOAT | NOT NULL | Demand kW | Every 15 minutes |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |

**Update Logic:**
- **On Demand Collection (every 15 minutes):** INSERT new record
- **On Monthly Aggregation:** Aggregate to `demand_ledger_monthly`

**Stored Data:**
- 15-minute power demand intervals
- Billing accuracy data

---

### 8. Device Encryption Tables

#### `edge_devices`
**Purpose:** Edge collector devices

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Device ID | Auto-increment |
| `zone_id` | INTEGER | FK to zones | Zone | On registration |
| `device_serial` | VARCHAR(100) | UNIQUE | Device serial | On registration |
| `token_hash` | VARCHAR(255) | NOT NULL | Token hash | On registration |
| `status` | VARCHAR(20) | DEFAULT 'active' | Device status | System update |
| `registered_at` | TIMESTAMP | DEFAULT NOW() | Registration time | Auto |

**Update Logic:**
- **On Device Registration:** INSERT new device
- **On Status Change:** UPDATE `status`

**Stored Data:**
- Edge device registry
- Security tokens

---

#### `miner_secrets`
**Purpose:** Encrypted miner credentials

| Column | Type | Constraints | Description | Update Triggers |
|--------|------|-------------|-------------|-----------------|
| `id` | INTEGER | PRIMARY KEY | Secret ID | Auto-increment |
| `miner_id` | INTEGER | FK to hosting_miners | Miner | On creation |
| `encryption_mode` | INTEGER | DEFAULT 1 | Encryption mode | On creation |
| `credential_ciphertext` | TEXT | NOT NULL | Encrypted credential | On creation |
| `credential_fingerprint` | VARCHAR(64) | | SHA-256 hash | On creation |
| `anti_rollback_counter` | INTEGER | DEFAULT 0 | Rollback counter | On update |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time | Auto |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Update time | Auto on update |

**Update Logic:**
- **On Credential Creation:** INSERT encrypted credential
- **On Credential Update:** UPDATE with new ciphertext, increment counter
- **On Rollback Attempt:** Reject if counter decreases

**Stored Data:**
- Encrypted miner credentials
- Security metadata
- Anti-rollback protection

---

## Table Update Patterns

### Pattern 1: User Actions

**Calculator Calculation:**
```
User submits calculation
    ↓
READ: user_miners (user's miners)
READ: miner_models (miner specs)
READ: network_snapshots (latest network data)
    ↓
Calculate profitability (in-memory)
    ↓
NO DATABASE UPDATE (calculation only)
    ↓
Return results to user
```

**User Adds Miner:**
```
User adds miner configuration
    ↓
INSERT: user_miners
    - user_id, miner_model_id, actual_hashrate, etc.
    ↓
COMMIT transaction
    ↓
INSERT: event_outbox
    - kind: 'user_miner.created'
    - payload: {user_id, miner_id}
    ↓
COMMIT transaction
    ↓
Debezium captures → Kafka → Portfolio Consumer
    ↓
Portfolio Consumer: Recalculate portfolio
    - READ: user_miners (all user's miners)
    - Calculate new ROI
    - UPDATE: user dashboard cache (Redis)
```

---

### Pattern 2: Scheduled Jobs

**Network Data Collection (every 10 minutes):**
```
Scheduler triggers collection
    ↓
Fetch from APIs:
    - CoinGecko (BTC price)
    - Blockchain.info (difficulty, hashrate)
    ↓
INSERT: network_snapshots
    - btc_price, network_difficulty, network_hashrate
    ↓
COMMIT
    ↓
Cleanup old snapshots (retention: max 10/day)
    - DELETE: network_snapshots WHERE recorded_at < cutoff
```

**Telemetry Collection (every 5 minutes):**
```
Edge collector sends telemetry
    ↓
INSERT: miner_telemetry
    - miner_id, hashrate_actual, temperature, power
    ↓
COMMIT
    ↓
Aggregate to history tables:
    - INSERT: telemetry_history_5min (aggregated)
    - UPDATE: telemetry_daily (daily aggregates)
    ↓
Check for alerts:
    - If hashrate drops → UPDATE: hosting_miners.status='offline'
    - INSERT: miner_alerts (if rule triggered)
```

---

### Pattern 3: CRM Operations

**Lead Creation:**
```
Sales creates lead
    ↓
INSERT: crm_leads
    - customer_id, title, status='NEW', value
    ↓
COMMIT
    ↓
INSERT: crm_activities
    - type='lead_created', description
    ↓
COMMIT
```

**Lead Conversion:**
```
Sales converts lead to deal
    ↓
UPDATE: crm_leads
    - status='WON'
    ↓
INSERT: crm_deals
    - customer_id, lead_id, status='DRAFT', value
    ↓
COMMIT
    ↓
INSERT: crm_activities
    - type='lead_converted', deal_id
    ↓
COMMIT
```

**Invoice Generation:**
```
Deal completed, generate invoice
    ↓
INSERT: crm_invoices
    - customer_id, deal_id, amount, status='DRAFT'
    - Auto-generate invoice_number
    ↓
COMMIT
    ↓
On sending:
    UPDATE: crm_invoices
    - status='SENT', due_date
    ↓
COMMIT
```

---

### Pattern 4: Intelligence Layer

**Forecast Generation:**
```
User requests forecast
    ↓
Check cache (Redis)
    - If exists and fresh → return cached
    ↓
If cache miss:
    READ: network_snapshots (last 90 days)
    ↓
Run ARIMA model
    - Generate 7-day predictions
    ↓
DELETE: forecast_daily (old forecasts for user)
    ↓
INSERT: forecast_daily (7 new records)
    - One per day, with confidence intervals
    ↓
COMMIT
    ↓
Cache results (Redis, 30 min TTL)
    ↓
INSERT: event_outbox
    - kind: 'intelligence.forecast_generated'
    ↓
COMMIT
```

**Optimization Schedule:**
```
User requests curtailment optimization
    ↓
READ: user_miners (user's miners)
READ: network_snapshots (current network data)
    ↓
Run linear programming (PuLP)
    - Optimize shutdown schedule
    ↓
DELETE: ops_schedule (old schedules for date)
    ↓
INSERT: ops_schedule (24 records, one per hour)
    - For each hour: which miners to shutdown
    ↓
COMMIT
    ↓
INSERT: event_outbox
    - kind: 'ops.schedule_created'
    ↓
COMMIT
```

---

## Data Relationships

### Entity Relationship Diagram

```
user_access (1) ──< (many) user_miners
user_access (1) ──< (many) login_records
user_access (1) ──< (many) forecast_daily
user_access (1) ──< (many) ops_schedule

miner_models (1) ──< (many) user_miners
miner_models (1) ──< (many) hosting_miners

crm_customers (1) ──< (many) crm_leads
crm_customers (1) ──< (many) crm_deals
crm_customers (1) ──< (many) crm_invoices
crm_customers (1) ──< (many) hosting_miners

crm_leads (1) ──< (1) crm_deals
crm_deals (1) ──< (many) crm_invoices

hosting_sites (1) ──< (many) hosting_miners
hosting_sites (1) ──< (many) zones
hosting_miners (1) ──< (many) miner_telemetry
hosting_miners (1) ──< (many) miner_secrets

zones (1) ──< (many) price_plans
zones (1) ──< (many) demand_15min
zones (1) ──< (many) edge_devices

event_outbox (1) ──< (1) event_inbox
event_outbox (1) ──< (1) event_dlq (on failure)
```

---

## Indexes and Performance

### Key Indexes

```sql
-- User access indexes
CREATE INDEX idx_user_access_email ON user_access(email);
CREATE INDEX idx_user_access_role ON user_access(role);
CREATE INDEX idx_user_access_expires ON user_access(expires_at);

-- User miners indexes
CREATE INDEX idx_user_miners_user_id ON user_miners(user_id);
CREATE INDEX idx_user_miners_model_id ON user_miners(miner_model_id);
CREATE INDEX idx_user_miners_status ON user_miners(status);

-- Network snapshots indexes
CREATE INDEX idx_network_snapshots_recorded_at ON network_snapshots(recorded_at);
CREATE INDEX idx_network_snapshots_btc_price ON network_snapshots(btc_price);

-- CRM indexes
CREATE INDEX idx_crm_leads_status ON crm_leads(status);
CREATE INDEX idx_crm_leads_customer_id ON crm_leads(customer_id);
CREATE INDEX idx_crm_deals_status ON crm_deals(status);
CREATE INDEX idx_crm_invoices_status ON crm_invoices(status);

-- Hosting indexes
CREATE INDEX idx_hosting_miners_site_id ON hosting_miners(site_id);
CREATE INDEX idx_hosting_miners_client_id ON hosting_miners(client_id);
CREATE INDEX idx_hosting_miners_status ON hosting_miners(status);
CREATE INDEX idx_miner_telemetry_miner_id ON miner_telemetry(miner_id);
CREATE INDEX idx_miner_telemetry_recorded_at ON miner_telemetry(recorded_at);

-- Intelligence indexes
CREATE INDEX idx_forecast_daily_user_date ON forecast_daily(user_id, forecast_date);
CREATE INDEX idx_ops_schedule_user_date ON ops_schedule(user_id, target_date);

-- CDC indexes
CREATE INDEX idx_event_outbox_kind ON event_outbox(kind);
CREATE INDEX idx_event_outbox_processed ON event_outbox(processed);
CREATE INDEX idx_event_outbox_created_at ON event_outbox(created_at);
```

---

## Data Retention Policies

### Retention Rules

| Table | Retention Policy | Cleanup Method |
|-------|-----------------|----------------|
| `network_snapshots` | Max 10 per day | Daily cleanup job |
| `miner_telemetry` | 24 hours raw, then aggregated | Auto-aggregate to history tables |
| `telemetry_history_5min` | 30 days | Monthly cleanup |
| `telemetry_daily` | 365 days | Yearly cleanup |
| `login_records` | 90 days | Monthly cleanup |
| `forecast_daily` | 30 days | Auto-expire |
| `event_outbox` | 7 days after processed | Daily cleanup |
| `event_dlq` | 30 days | Monthly cleanup |

### Cleanup Implementation

```python
# Scheduled cleanup job
def cleanup_old_data():
    # Network snapshots: keep max 10 per day
    cutoff = datetime.utcnow() - timedelta(days=1)
    old_snapshots = NetworkSnapshot.query.filter(
        NetworkSnapshot.recorded_at < cutoff
    ).all()
    # Keep only latest 10 per day
    # ... cleanup logic
    
    # Login records: 90 days
    cutoff = datetime.utcnow() - timedelta(days=90)
    LoginRecord.query.filter(
        LoginRecord.login_time < cutoff
    ).delete()
    db.session.commit()
```

---

## Next Steps

For **Architecture Details**, see:
- [High-Level Architecture](01_HIGH_LEVEL_ARCHITECTURE.md) - System overview
- [Technical Architecture](03_TECHNICAL_ARCHITECTURE.md) - Implementation details

For **Route Information**, see:
- [Route-to-Page Mapping](05_ROUTE_TO_PAGE_MAPPING.md) - URL structure
