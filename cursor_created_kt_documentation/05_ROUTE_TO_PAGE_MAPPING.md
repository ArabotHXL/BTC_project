# Route-to-Page Mapping - Complete URL Structure

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Purpose:** Complete mapping of all routes to their corresponding pages and functionality

---

## Public Routes (No Authentication)

| Route | Template | Description | Blueprint |
|-------|----------|-------------|-----------|
| `/` | `index.html` | Homepage (redirects based on login status) | `app.py` |
| `/main` | `index.html` | Main page redirect | `app.py` |
| `/login` | `login.html` | Login page | `auth_bp` |
| `/register` | `register.html` | Registration page | `auth_bp` |
| `/verify-email/<token>` | `login.html` | Email verification | `auth_bp` |
| `/legal` | `legal.html` | Legal terms page | `app.py` |
| `/pricing` | `pricing.html` | Pricing page | `app.py` |

---

## Authenticated Routes (Login Required)

### Dashboard & Main Pages

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/dashboard` | `dashboard_home.html` | Main dashboard | All users |
| `/welcome` | `index.html` | Welcome page | All users |
| `/unauthorized` | `unauthorized.html` | Unauthorized access page | All users |

### Calculator Routes

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/calculator` | `calculator.html` | Main mining calculator | All users |
| `/mining-calculator` | `calculator.html` | Calculator alias | All users |
| `/curtailment-calculator` | `curtailment_calculator.html` | Power outage calculator | All users |
| `/algorithm-test` | `algorithm_test.html` | Algorithm testing page | Admin/Owner |

### Analytics Routes

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/analytics` | `analytics_main.html` | Analytics dashboard | All users |
| `/analytics/dashboard` | `analytics_dashboard.html` | Analytics dashboard (new) | All users |
| `/technical-analysis` | `technical_analysis.html` | Technical analysis page | All users |
| `/network-history` | `network_history.html` | Network history data | All users |

### CRM Routes (Prefix: `/crm`)

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/crm/` | `crm/dashboard.html` | CRM dashboard | CRM access |
| `/crm/customers` | `crm/customers.html` | Customer list | CRM access |
| `/crm/customers/add` | `crm/customer_form.html` | Add customer | CRM access |
| `/crm/customers/view/<id>` | `crm/customer_detail.html` | Customer details | CRM access |
| `/crm/leads` | `crm/leads.html` | Lead management | CRM access |
| `/crm/deals` | `crm/deals.html` | Deal pipeline | CRM access |
| `/crm/invoices` | `crm/invoices.html` | Invoice management | CRM access |

### Hosting Routes (Prefix: `/hosting`)

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/hosting/` | `hosting/dashboard.html` | Hosting dashboard | Hosting access |
| `/hosting/sites` | `hosting/sites.html` | Site management | Hosting access |
| `/hosting/miners` | `hosting/miners.html` | Miner management | Hosting access |
| `/hosting/tickets` | `hosting/tickets.html` | Ticket system | Hosting access |
| `/hosting/status/<site_slug>` | `hosting/public_status.html` | Public site status | Public |

### Client Portal Routes (Prefix: `/client`)

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/client/dashboard` | `client/dashboard.html` | Client dashboard | Customer |
| `/client/assets` | `client/assets.html` | Client assets | Customer |
| `/client/bills` | `client/bills.html` | Client bills | Customer |

### Admin Routes (Prefix: `/admin`)

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/admin/user_access` | `user_access.html` | User management | Admin/Owner |
| `/admin/user_access/add` | `admin/user_form.html` | Add user | Admin/Owner |
| `/admin/user_access/edit/<id>` | `admin/user_form.html` | Edit user | Admin/Owner |
| `/admin/user_access/view/<id>` | `admin/user_detail.html` | User details | Admin/Owner |
| `/admin/login_records` | `login_records.html` | Login history | Admin/Owner |
| `/admin/miners` | `admin/miners.html` | Miner model management | Admin/Owner |
| `/admin/miners/add` | `admin/miner_form.html` | Add miner model | Admin/Owner |

### Batch Processing Routes

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/batch-calculator` | `batch_calculator.html` | Batch calculator | Batch access |
| `/batch/upload` | `batch/upload.html` | CSV upload | Batch access |
| `/batch/template` | - | Download CSV template | Batch access |

### Billing Routes (Prefix: `/billing`)

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/billing/plans` | `billing_plans.html` | Subscription plans | All users |
| `/billing/subscribe` | `billing/subscribe.html` | Subscribe to plan | All users |
| `/billing/manage` | `billing/manage.html` | Manage subscription | All users |
| `/subscription` | `subscription.html` | Subscription page | All users |

### Trust & Transparency Routes (Prefix: `/trust`)

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/trust/` | `trust/dashboard.html` | Trust center | All users |
| `/trust/verify` | `transparency_verification_center.html` | Verification | Public |

### Other Feature Routes

| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/deribit` | `deribit_analysis.html` | Deribit analysis | All users |
| `/sla-nft` | `sla_nft_manager.html` | SLA NFT manager | Admin/Owner |
| `/web3-dashboard` | `web3_dashboard.html` | Web3 dashboard | Admin/Owner |
| `/debug-info` | `debug_info.html` | Debug information | Admin/Owner |
| `/modules-dashboard` | `modules_dashboard.html` | Modules overview | Admin/Owner |

---

## API Routes (JSON Responses)

### Authentication API

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/auth/login` | POST | User login | No |
| `/api/auth/logout` | POST | User logout | Yes |
| `/api/auth/me` | GET | Current user info | Yes |

### Calculator API

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/calculate` | POST | Calculate profitability | Yes |
| `/api/user-miners` | GET/POST | User miner config | Yes |
| `/api/test/calculate` | POST | Test calculation | Yes |

### Network Data API

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/btc-price` | GET | BTC price | No |
| `/api/network-stats` | GET | Network statistics | No |
| `/api/network-data` | GET | Network data | No |
| `/api/market-data` | GET | Market data | No |

### Analytics API (Prefix: `/api/analytics`)

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/analytics/data` | GET | Analytics data | Yes |
| `/api/analytics/market-data` | GET | Market data | Yes |
| `/api/analytics/roi-heatmap` | POST | ROI heatmap | Yes |
| `/api/analytics/historical-replay` | POST | Historical replay | Yes |
| `/api/analytics/curtailment-simulation` | POST | Curtailment sim | Yes |
| `/api/analytics/technical-indicators` | GET | Technical indicators | Yes |

### Intelligence API (Prefix: `/api/intelligence`)

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/intelligence/forecast/<user_id>` | GET | Get forecast | Yes |
| `/api/intelligence/forecast/<user_id>/refresh` | POST | Refresh forecast | Yes |
| `/api/intelligence/optimize/curtailment` | POST | Optimize curtailment | Yes |
| `/api/intelligence/optimize/<user_id>/<date>` | GET | Get schedule | Yes |
| `/api/intelligence/explain/roi/<user_id>` | GET | ROI explanation | Yes |
| `/api/intelligence/health` | GET | Health check | No |
| `/api/intelligence/health/slo` | GET | SLO metrics | No |

### CRM API

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/leads` | GET/POST | Lead management | CRM access |
| `/api/deals` | GET/POST | Deal management | CRM access |
| `/api/invoices` | GET/POST | Invoice management | CRM access |
| `/api/customers` | GET/POST | Customer management | CRM access |

### Hosting API (Prefix: `/hosting/api`)

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/hosting/api/overview` | GET | Hosting overview | Yes |
| `/hosting/api/sites` | GET/POST | Site management | Yes |
| `/hosting/api/miners` | GET/POST | Miner management | Yes |
| `/hosting/api/usage/preview` | GET | Usage preview | Yes |

### Treasury API (Prefix: `/api/treasury`)

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/treasury/overview` | GET | Treasury overview | Yes |
| `/api/treasury/signals` | GET | Trading signals | Yes |
| `/api/treasury-exec/execute` | POST | Execute trade | Yes |

### Web3 & Blockchain API

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/sla/mint-certificate` | POST | Mint SLA NFT | Yes |
| `/api/blockchain/verify-data` | POST | Verify data | Yes |
| `/api/web3/sla/mint-request` | POST | Mint request | Yes |

### Control Plane API (Prefix: `/api/v1`)

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/v1/portal/miners` | GET | Portal miners | Yes |
| `/api/v1/portal/zones` | GET | Portal zones | Yes |
| `/api/v1/sites/<id>/security-settings` | GET/PUT | Security settings | Yes |
| `/api/v1/miners/<id>/credential` | GET/PUT | Miner credentials | Yes |

### Health Check API

| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/health` | GET | Basic health check | No |
| `/ready` | GET | Readiness probe | No |
| `/alive` | GET | Liveness probe | No |
| `/api/health` | GET | Detailed health | No |

---

## Route Organization by Blueprint

### Core Blueprints
- **system_health_bp** - Health checks
- **i18n_bp** - Internationalization
- **auth_bp** - Authentication
- **calculator_bp** - Calculator
- **admin_bp** - Admin

### Business Blueprints
- **crm_bp** (via `init_crm_routes`) - CRM system
- **hosting_bp** - Hosting services
- **client_bp** - Client portal
- **billing_bp** - Billing & subscriptions
- **batch_calculator_bp** - Batch processing
- **analytics_bp** - Analytics
- **trust_bp** - Trust center

### Intelligence Blueprints
- **forecast_bp** - Forecasting
- **optimize_bp** - Optimization
- **explain_bp** - Explanations
- **health_bp** - Intelligence health

### System Blueprints
- **monitoring_bp** - System monitoring
- **rbac_bp** - RBAC management
- **collector_bp** - Data collection
- **monitor_bp** - Monitoring

### Control Plane Blueprints
- **control_plane_bp** - Control plane
- **portal_bp** - Portal Lite API
- **legacy_bp** - Legacy API adapter
- **remote_control_bp** - Remote control
- **scan_bp** - Network scanning

---

## Template Organization

### Base Templates
- `base.html` - Base template with navigation
- `index.html` - Homepage template
- `error.html` - Error page template

### Feature Templates
- `calculator.html` - Calculator interface
- `analytics_main.html` - Analytics dashboard
- `batch_calculator.html` - Batch calculator
- `curtailment_calculator.html` - Curtailment calculator

### Admin Templates
- `user_access.html` - User management
- `admin/*` - Admin-specific templates

### Module Templates
- `crm/*` - CRM templates
- `hosting/*` - Hosting templates
- `client/*` - Client portal templates
- `billing/*` - Billing templates

---

## Route Access Control Matrix

| Route Category | Guest | Customer | Mining Site | Admin | Owner |
|----------------|-------|---------|-------------|-------|-------|
| Public Routes | ✅ | ✅ | ✅ | ✅ | ✅ |
| Calculator | ✅ | ✅ | ✅ | ✅ | ✅ |
| Analytics | ❌ | ✅ | ✅ | ✅ | ✅ |
| CRM | ❌ | ❌ | ✅ | ✅ | ✅ |
| Hosting | ❌ | Limited | ✅ | ✅ | ✅ |
| Admin | ❌ | ❌ | ❌ | ✅ | ✅ |
| Intelligence | ❌ | ✅ | ✅ | ✅ | ✅ |

---

## Dynamic Route Generation

Some routes are generated dynamically:

```python
# Example: Dynamic CRM routes
@crm_bp.route('/customers/view/<int:customer_id>')
def view_customer(customer_id):
    # Route generated based on customer ID
    ...

# Example: Dynamic intelligence routes
@forecast_bp.route('/<int:user_id>')
def get_forecast(user_id):
    # Route includes user ID
    ...
```

---

## Route Naming Conventions

1. **Page Routes:** Use kebab-case (`/mining-calculator`)
2. **API Routes:** Use `/api/` prefix (`/api/calculate`)
3. **Module Routes:** Use module prefix (`/crm/customers`)
4. **Admin Routes:** Use `/admin/` prefix (`/admin/users`)
5. **Resource Routes:** RESTful style (`/api/resource/<id>`)

---

## Next Steps

For **Implementation Details**, see:
- [Technical Architecture](03_TECHNICAL_ARCHITECTURE.md) - Technical deep dive
- [Low-Level Implementation](04_LOW_LEVEL_IMPLEMENTATION.md) - Code details

For **Architecture Overview**, see:
- [High-Level Architecture](01_HIGH_LEVEL_ARCHITECTURE.md) - Business view
- [Executive Summary](00_EXECUTIVE_SUMMARY.md) - Executive view
