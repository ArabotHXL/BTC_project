# Architecture Diagrams - Visual Guide

Welcome to the comprehensive visual architecture documentation for HashInsight Enterprise!

## 📊 Diagram Collection

This folder contains **6 detailed diagram documents** with **40+ Mermaid diagrams** explaining every aspect of the system architecture.

### Quick Navigation

| # | Document | Description | Best For |
|---|----------|-------------|----------|
| 1️⃣ | [System Overview](./01-system-overview.md) | Complete system architecture with all components | Everyone - Start here! |
| 2️⃣ | [Data Flow](./02-data-flow-complete.md) | How data moves through the system | Developers, Integrators |
| 3️⃣ | [Database Schema](./03-database-schema-visual.md) | Entity relationships and database design | DBAs, Backend Developers |
| 4️⃣ | [Module Interaction](./04-module-interaction.md) | How modules communicate and depend on each other | Developers, Architects |
| 5️⃣ | [Authentication Flow](./05-authentication-flow.md) | Complete authentication and authorization | Security Engineers |
| 6️⃣ | [Deployment Architecture](./06-deployment-architecture.md) | Infrastructure and deployment setup | DevOps, System Admins |

## 🎯 Use Cases

### "I'm new to the project"
**Start with**: [01-system-overview.md](./01-system-overview.md)
- Get the big picture
- Understand what each component does
- See how everything connects

### "I need to integrate with this system"
**Read**: [02-data-flow-complete.md](./02-data-flow-complete.md) + [04-module-interaction.md](./04-module-interaction.md)
- Understand API endpoints
- See data flow patterns
- Learn module dependencies

### "I'm working on the database"
**Study**: [03-database-schema-visual.md](./03-database-schema-visual.md)
- Complete ERD with all relationships
- Index strategies
- Performance optimization tips

### "I need to deploy/scale this"
**Review**: [06-deployment-architecture.md](./06-deployment-architecture.md)
- Infrastructure requirements
- Scaling strategies
- Monitoring setup

### "I'm implementing authentication"
**Check**: [05-authentication-flow.md](./05-authentication-flow.md)
- Email/password flow
- Web3 wallet flow
- RBAC implementation
- Session management

## 📋 Diagram Types Included

### Architectural Diagrams
- **System Overview** - Complete architecture
- **Layer Architecture** - 5-layer breakdown
- **Module Ecosystem** - Module relationships
- **Deployment Architecture** - Infrastructure setup

### Flow Diagrams
- **User Request Flows** - Synchronous processing
- **Background Processing** - Asynchronous jobs
- **Data Collection Pipelines** - Telemetry and market data
- **Curtailment Execution** - Smart power management

### Entity Relationship Diagrams
- **Complete Database ERD** - All 15+ tables
- **Table Relationships** - Foreign keys and joins
- **Index Coverage** - Performance optimization

### Security Diagrams
- **Authentication Flows** - 3 auth methods
- **Authorization (RBAC)** - Role-based access
- **Session Management** - Security features
- **Network Security** - Layer-by-layer protection

### Sequence Diagrams
- **Calculator Request** - Step-by-step flow
- **Telemetry Collection** - Background job execution
- **Multi-Exchange Aggregation** - Parallel API calls
- **CRM Deal Creation** - Transaction flow

### State Diagrams
- **Authentication States** - Login flow states
- **Session Lifecycle** - From creation to expiration

## 🎨 How to View These Diagrams

### Option 1: GitHub/GitLab (Recommended)
- GitHub and GitLab render Mermaid diagrams automatically
- Just open any `.md` file in the browser

### Option 2: VS Code
1. Install "Markdown Preview Mermaid Support" extension
2. Open any `.md` file
3. Click "Open Preview" (Ctrl+Shift+V)

### Option 3: Online Mermaid Editor
1. Copy the Mermaid code block
2. Paste into https://mermaid.live
3. View and export as SVG/PNG

### Option 4: Documentation Platforms
- **GitBook**: Native Mermaid support
- **ReadTheDocs**: With mermaid extension
- **Confluence**: Via Mermaid plugin
- **Notion**: Via Mermaid embed

## 📊 Diagram Statistics

| Metric | Count |
|--------|-------|
| **Total Documents** | 6 |
| **Total Diagrams** | 40+ |
| **Architecture Diagrams** | 8 |
| **Flow Diagrams** | 12 |
| **Sequence Diagrams** | 10 |
| **State Diagrams** | 3 |
| **ERD Diagrams** | 4 |
| **Infrastructure Diagrams** | 5 |

## 🔍 Key Diagrams by Topic

### Complete System Architecture
📄 **Document**: [01-system-overview.md](./01-system-overview.md)
- Shows all modules, services, databases, and external integrations
- Color-coded components for easy understanding
- Perfect for stakeholder presentations

### End-to-End Request Processing
📄 **Document**: [02-data-flow-complete.md](./02-data-flow-complete.md)
- **Calculator Request**: User → Flask → APIs → Database → Response
- **Telemetry Collection**: Scheduler → CGMiner → Database → Cache
- **Curtailment Execution**: Plan → Optimization → Shutdown → Notification

### Database Design
📄 **Document**: [03-database-schema-visual.md](./03-database-schema-visual.md)
- 15+ tables with complete relationships
- Indexes for performance
- Data retention policies
- Growth estimates

### Module Communication
📄 **Document**: [04-module-interaction.md](./04-module-interaction.md)
- Dependency matrix
- Synchronous vs. asynchronous patterns
- Event-driven architecture
- API endpoint organization

### Security Architecture
📄 **Document**: [05-authentication-flow.md](./05-authentication-flow.md)
- Email/Password authentication (step-by-step)
- Web3 wallet integration (with MetaMask)
- RBAC flow (6 role types)
- Session security

### Infrastructure & Deployment
📄 **Document**: [06-deployment-architecture.md](./06-deployment-architecture.md)
- Replit platform architecture
- Network flow & security layers
- Caching strategy
- Monitoring & observability

## 🎓 Learning Path

### For Business Stakeholders
1. [System Overview](./01-system-overview.md) - Understand what the system does
2. [Deployment Architecture](./06-deployment-architecture.md) - See infrastructure requirements
3. Done! You have a solid high-level understanding

### For New Developers
1. [System Overview](./01-system-overview.md) - Get the big picture
2. [Module Interaction](./04-module-interaction.md) - Understand module organization
3. [Data Flow](./02-data-flow-complete.md) - Learn how data moves
4. [Authentication Flow](./05-authentication-flow.md) - Master security implementation
5. [Database Schema](./03-database-schema-visual.md) - Study data models
6. [Deployment Architecture](./06-deployment-architecture.md) - Infrastructure knowledge

### For Integration Engineers
1. [Module Interaction](./04-module-interaction.md) - API endpoints and dependencies
2. [Data Flow](./02-data-flow-complete.md) - Integration patterns
3. [Deployment Architecture](./06-deployment-architecture.md) - External service connections

### For DevOps/SRE
1. [Deployment Architecture](./06-deployment-architecture.md) - Infrastructure setup
2. [Data Flow](./02-data-flow-complete.md) - Performance bottlenecks
3. [Database Schema](./03-database-schema-visual.md) - Database optimization

## 💡 Tips for Using These Diagrams

### In Presentations
- Use [System Overview](./01-system-overview.md) for executive presentations
- Export diagrams as SVG/PNG from https://mermaid.live
- Color schemes are consistent across all diagrams

### In Documentation
- Link to specific diagrams from your technical docs
- Embed rendered images in wikis/confluence
- Reference diagram sections in code comments

### In Code Reviews
- Reference architecture diagrams when explaining design decisions
- Use flow diagrams to explain complex logic
- Point to database ERD for schema discussions

### In Onboarding
- Assign new developers the learning path above
- Use diagrams in onboarding presentations
- Create exercises based on the flows

## 🔗 Related Documentation

These diagrams complement the main architecture documentation:

- **[../README.md](../README.md)** - Documentation index
- **[../architecture-overview.md](../architecture-overview.md)** - High-level text overview
- **[../system-architecture.md](../system-architecture.md)** - Technical deep dive
- **[../data-flow.md](../data-flow.md)** - Process flow descriptions
- **[../module-guide.md](../module-guide.md)** - Module reference
- **[../database-schema.md](../database-schema.md)** - Database documentation
- **[../external-integrations.md](../external-integrations.md)** - API integrations

## 📝 Diagram Conventions

### Colors
- 🟢 **Green**: User-facing components, successful operations
- 🔵 **Blue**: Application logic, services
- 🟠 **Orange**: Intelligence/AI components
- 🟣 **Purple**: Advanced features
- 🔴 **Red**: Alerts, errors, critical paths
- ⚫ **Black**: Core application (Flask)
- 🟤 **Brown**: Databases

### Icons
- 🧮 Calculator
- 👥 CRM
- 🏭 Hosting
- 📊 Analytics
- ⚡ Curtailment/Optimization
- 🗄️ Database
- ⏰ Scheduler
- 🌐 Web/Network
- 🔐 Security
- 📧 Email

### Symbols
- `→` Direct dependency/flow
- `↔` Bidirectional communication
- `⚡` Fast/cached operation
- `🚀` Optimized path
- `⚠️` Warning/attention needed
- `✅` Success/completion
- `❌` Failure/error

---

**Happy diagramming!** 🎉

For questions about these diagrams or to request additional visualizations, please refer to the main architecture documentation or contact the development team.
