# HashInsight Enterprise - System Architecture Documentation

Welcome to the complete architecture documentation for the HashInsight Enterprise BTC Mining Calculator platform.

## 📚 Documentation Index

This folder contains comprehensive architecture documentation designed for both technical and non-technical audiences:

### Core Documentation

1. **[Architecture Overview](./architecture-overview.md)** 🎯
   - High-level system overview
   - Key components and their purposes
   - Technology stack
   - System capabilities
   - **Audience**: Everyone (business stakeholders to developers)

2. **[System Architecture](./system-architecture.md)** 🏗️
   - Detailed technical architecture
   - Layer-by-layer breakdown
   - Component interactions
   - Security architecture
   - **Audience**: Technical teams, architects, senior developers

3. **[Data Flow & Process Flows](./data-flow.md)** 🔄
   - End-to-end request flows
   - Background processing pipelines
   - Real-time data collection
   - Event-driven architecture
   - **Audience**: Developers, DevOps, system integrators

4. **[Module Guide](./module-guide.md)** 📦
   - All system modules explained
   - Module dependencies
   - Inter-module communication
   - API interfaces
   - **Audience**: Developers, technical leads

5. **[Database Architecture](./database-schema.md)** 🗄️
   - Complete database schema
   - Table relationships
   - Data models
   - Migration strategy
   - **Audience**: Database administrators, backend developers

6. **[External Integrations](./external-integrations.md)** 🔌
   - API integrations map
   - Third-party services
   - Blockchain connectivity
   - Web3 features
   - **Audience**: Integration engineers, technical leads

## 🎨 Architecture Diagrams

All documentation includes visual diagrams using Mermaid syntax, which can be rendered in:
- GitHub/GitLab markdown viewers
- VS Code with Mermaid extension
- Online Mermaid editors
- Documentation platforms (GitBook, ReadTheDocs, etc.)

## 🚀 Quick Start

### For Business Stakeholders
Start with [Architecture Overview](./architecture-overview.md) to understand what the system does and its capabilities.

### For New Developers
1. Read [Architecture Overview](./architecture-overview.md)
2. Review [Module Guide](./module-guide.md)
3. Study [Data Flow](./data-flow.md)
4. Dive into [System Architecture](./system-architecture.md)

### For Integration Engineers
1. Check [External Integrations](./external-integrations.md)
2. Review [Data Flow](./data-flow.md)
3. Consult [Module Guide](./module-guide.md) for API endpoints

### For Database Administrators
1. Start with [Database Architecture](./database-schema.md)
2. Review data models in [System Architecture](./system-architecture.md)

## 📊 System Overview at a Glance

**HashInsight Enterprise** is a comprehensive, enterprise-grade Bitcoin mining management platform featuring:

- **Mining Profitability Calculator** - Real-time ROI analysis for 19+ ASIC models
- **CRM System** - Complete customer relationship management with deal pipeline
- **Hosting Services** - Large-scale mining farm management (6000+ miners)
- **Smart Power Curtailment** - AI-powered energy optimization
- **Technical Analysis** - 10+ indicators with BTC price forecasting
- **Intelligence Layer** - ARIMA forecasting, anomaly detection, optimization
- **Web3 Integration** - Blockchain transparency and wallet authentication
- **Multi-Format Reporting** - Professional PDF, Excel, PowerPoint generation

## 🏗️ Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Flask (Python), SQLAlchemy ORM, Gunicorn WSGI |
| **Database** | PostgreSQL (Replit hosted) |
| **Caching** | Redis (in-memory data store) |
| **Frontend** | Jinja2 templates, Bootstrap 5, Chart.js, CountUp.js |
| **Background Jobs** | APScheduler, RQ (Redis Queue) |
| **APIs** | CoinGecko, Blockchain.info, Ankr RPC, Deribit, OKX, Binance |
| **Blockchain** | Web3.py, Base L2 (Sepolia testnet), IPFS (Pinata) |
| **Machine Learning** | ARIMA (statsmodels), XGBoost, PuLP optimization |
| **Infrastructure** | Replit platform, Nix environment |

## 🔐 Security Features

- Custom CSRF protection with iframe compatibility
- Role-Based Access Control (RBAC)
- Web3 wallet authentication (MetaMask)
- Email/password authentication with strong hashing
- Session management with secure cookies
- API authentication middleware
- Audit logging and compliance tracking

## 📈 System Scale

- **Miners Supported**: 6000+ devices per farm
- **ASIC Models**: 19+ models with detailed specifications
- **Users**: Multi-tenant with role-based access
- **Languages**: Bilingual (English/Chinese)
- **Real-time Data**: Telemetry collection every 60 seconds
- **API Calls**: Intelligent caching and fallback strategies

## 🔄 Last Updated

This documentation was generated on: **November 20, 2025**

## 📞 Support

For questions about this documentation or the system architecture:
- Review the specific documentation files listed above
- Check inline code comments in the repository
- Consult `replit.md` for development preferences

---

**Navigate to any section above to dive deeper into the system architecture!** 🚀
