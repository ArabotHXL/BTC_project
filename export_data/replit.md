# HashInsight Bitcoin Mining Calculator

## Overview

HashInsight is a comprehensive Bitcoin mining intelligence platform hosted at calc.hashinsight.net. The system provides mining profitability calculations, batch analysis for large mining operations, treasury management with sell strategies, real-time monitoring, and hosting transparency features for mining site operators and their clients.

The platform serves multiple user types: platform owners/admins, mining site operators, hosting clients, app customers, and guests. Core capabilities include single and batch miner ROI calculations, intelligent curtailment (power reduction) planning, CRM for mining customers, analytics dashboards, and optional Web3 integration for transparent SLA verification.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Next.js with TypeScript
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: React hooks and context
- **Internationalization**: Chinese and English bilingual support throughout

### Backend Architecture
- **Primary Stack**: Python 3.10+ with Flask
- **API Design**: REST endpoints with Pydantic validation
- **Authentication**: JWT tokens with role-based access control (RBAC)
- **Roles**: Owner, Admin, Mining_Site_Owner, Client, Customer, Guest
- **Multi-tenancy**: Row-level security (RLS) with tenant_id isolation

### Event-Driven Architecture
- **Pattern**: Transactional Outbox with CDC (Change Data Capture)
- **Message Broker**: Kafka with Debezium for PostgreSQL CDC
- **Worker Queues**: Redis with RQ (Redis Queue) for background jobs
- **Event Types**: Miner updates, treasury signals, ops alerts, CRM events
- **Guarantees**: At-least-once delivery with inbox pattern for idempotency

### Caching Strategy
- **Cache Layer**: Redis with Flask-Caching
- **TTLs**: Real-time market data (1-5s), network stats (5-10m)
- **Invalidation**: Event-driven cache busting on data changes

### Security Architecture
- **Credential Storage**: End-to-end encryption for miner credentials
- **Encryption**: AES-256-GCM with X25519 sealed box key wrapping
- **Key Management**: Device keypairs for edge collectors, server stores only ciphertext
- **Anti-replay**: Counter-based protection with AAD binding
- **CSP**: Content Security Policy headers enforced

### Edge Collector Architecture
- **Purpose**: On-site agent for mining facility data collection
- **Protocol**: CGMiner/BMminer API over TCP port 4028
- **Capabilities**: Three levels - discovery only, read-only telemetry, full management
- **Security**: Device generates X25519 keypair, only edge can decrypt credentials

### Monitoring & Telemetry
- **Time-series Data**: PostgreSQL with TimescaleDB extension
- **Metrics**: Hashrate, temperature, power consumption per miner
- **Alerting**: Rule-based with configurable thresholds
- **Audit Logging**: All sensitive operations logged to JSONL files

## External Dependencies

### Database
- **PostgreSQL 15**: Primary data store with TimescaleDB for time-series
- **Redis**: Caching, session storage, distributed locks, job queues

### Message Infrastructure
- **Kafka**: Event streaming with KRaft or Zookeeper
- **Kafka Connect**: Debezium source connector for CDC
- **Topics**: events.miner, events.treasury, events.ops, events.crm, events.dlq

### External APIs
- **Price Data**: CoinWarz API, multi-exchange collectors
- **Network Stats**: Bitcoin RPC, mining pool APIs (ViaBTC, BTC.com)
- **Market Data**: Deribit for derivatives analysis

### Third-Party Integrations (Placeholder/Optional)
- **Email**: Gmail API with OAuth 2.0
- **E-Signature**: DocuSign/PandaDoc endpoints
- **Accounting**: QuickBooks/Xero for invoice sync
- **Web3**: IPFS for audit data, L2 chains for SLA attestations

### Infrastructure
- **Deployment**: Replit (primary), Docker Compose for local dev
- **Container Services**: web, worker-portfolio, worker-intel, postgres, redis, kafka, connect
- **Health Checks**: /healthz endpoint for orchestration