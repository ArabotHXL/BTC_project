# HI Integration - Multi-Tenant Hosting System

## 1. Overview

HI Integration (Hosting Integration) is a multi-tenant hosting management subsystem within HashInsight Enterprise. It enables mining farm operators to manage multiple hosting clients (tenants) with strict data isolation, automated billing, power curtailment control, and comprehensive audit logging.

### Key Capabilities

| Capability | Description |
|---|---|
| Multi-Tenant Isolation | Membership-based binding ensures each tenant can only access their own data |
| Curtailment Engine | Simulate / Execute / Verify workflow for power curtailment plans |
| 3-Tier Power Usage | Nominal watts estimation, metered data, and evidence-based tracking |
| Automated Billing | Contract-based invoicing with usage records and CSV export |
| RBAC | 4-role hierarchy with security-hardened cross-tenant access prevention |
| Audit Trail | All mutations logged with actor, entity, org/tenant scope, and request ID |

---

## 2. Architecture

### 2.1 Data Hierarchy

```
HiOrg (org_type: 'self')
  ├── HiTenant (tenant_type: 'self' | 'customer', status: 'active')
  │     ├── HiTenantMembership (user ↔ tenant binding, member_role)
  │     ├── HiGroup (site-scoped miner groups)
  │     ├── HiContract (tariff, billing cycle, fee structure)
  │     ├── HiUsageRecord (kWh, avg kW, period)
  │     ├── HiInvoice (line items, totals, CSV export)
  │     └── HiCurtailmentPlan (actions, results, reports)
  ├── HiTariff (flat / tiered / time-of-use)
  ├── HiCommandQueue (miner control commands)
  └── HiAuditLog (all mutations)
```

### 2.2 File Structure

| File | Purpose |
|---|---|
| `common/hi_tenant.py` | Tenant isolation middleware, RBAC decorators, query filters |
| `api/hi_api.py` | All HI REST API endpoints (`/api/hi/*`) |
| `models_hi.py` | SQLAlchemy models for all HI tables |
| `services/curtailment_engine.py` | Curtailment simulate/execute/verify logic |
| `services/usage_service.py` | Power usage calculation and record generation |
| `services/billing_service.py` | Invoice generation from contracts + usage |
| `scripts/seed_demo.py` | Demo data seeding (org, tenants, memberships) |
| `scripts/verify_hi_tenant_isolation.py` | P0 Gate verification (37 tests) |
| `alembic/versions/20260221_0001_hi_tables.py` | Main HI tables migration |
| `alembic/versions/20260221_0002_hi_tenant_memberships.py` | Membership table migration |

---

## 3. Role-Based Access Control (RBAC)

### 3.1 Role Mapping

The system maps platform roles to HI-specific roles:

| Platform Role | HI Role | Scope |
|---|---|---|
| `owner` | `operator_admin` | Full org-wide access, all tenants |
| `admin` | `operator_admin` | Full org-wide access, all tenants |
| `mining_site_owner` | `operator_ops` | Org-wide operational access |
| `operator` | `operator_ops` | Org-wide operational access |
| `client` | `tenant_viewer` (initial) → **`tenant_admin`** (via membership) | Own tenant only |

### 3.2 Membership-Based Role Override

**Critical design decision**: The initial role from `ROLE_TO_HI_ROLE` mapping is always overridden by `HiTenantMembership.member_role`. This prevents the `tenant_admin` → `tenant_viewer` downgrade bug.

```
Request flow:
1. session['role'] = 'client' → ROLE_TO_HI_ROLE['client'] = 'tenant_viewer'
2. Query HiTenantMembership for user_id
3. membership.member_role = 'tenant_admin' → g.hi_role = 'tenant_admin' (override)
```

### 3.3 Role Categories

```python
OPERATOR_ROLES = ('operator_admin', 'operator_ops')  # Org-wide access
TENANT_ROLES   = ('tenant_admin', 'tenant_viewer')    # Tenant-scoped access
```

### 3.4 Access Decorators

| Decorator | Required Role | Description |
|---|---|---|
| `@hi_require_auth` | Any authenticated HI role | Basic auth + tenant binding check |
| `@hi_require_operator` | `operator_admin` or `operator_ops` | Operator-only endpoints |
| `@hi_require_tenant_or_operator` | Any HI role | Tenant or operator access |

---

## 4. Tenant Isolation Middleware

### 4.1 Request Context (`common/hi_tenant.py`)

On every request, `init_hi_tenant()` populates Flask's `g` object:

| Variable | Operator | Tenant |
|---|---|---|
| `g.hi_org_id` | org.id (org_type='self') | tenant.org_id |
| `g.hi_tenant_id` | `None` (sees all tenants) | tenant.id (own tenant only) |
| `g.hi_role` | `operator_admin` / `operator_ops` | `tenant_admin` / `tenant_viewer` |

### 4.2 Tenant Resolution Flow

```
1. User authenticates → session['user_id'], session['role']
2. ROLE_TO_HI_ROLE maps platform role → initial HI role
3. If OPERATOR: find default org → g.hi_org_id, g.hi_tenant_id = None
4. If TENANT:
   a. Check session['hi_tenant_id'] → query HiTenantMembership(user_id, tenant_id)
   b. If no match → fallback to default membership (is_default=True)
   c. If membership found AND tenant is active:
      → g.hi_tenant_id = tenant.id
      → g.hi_org_id = tenant.org_id  
      → g.hi_role = membership.member_role (OVERRIDE)
      → session['hi_tenant_id'] = tenant.id (persist)
   d. If no membership → g.hi_tenant_id = None → 403 HI_TENANT_BINDING_REQUIRED
```

### 4.3 Query Filters

**`hi_filter_by_tenant(query, model)`** - Automatically scopes queries:
- Operators: filter by `org_id`
- Tenants: filter by `tenant_id` (returns empty set if no tenant bound)

**`hi_check_tenant_id_override(requested_tenant_id)`** - Validates `?tenant_id=X` params:
- Tenants: can only query their own tenant_id
- Operators: can query any tenant within their org
- Returns `False` → 403 ACCESS_DENIED

---

## 5. API Endpoints

Base URL: `/api/hi`

### 5.1 Authentication & Context

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/me` | `@hi_require_auth` | Current user's HI context (org, tenant, role) |
| GET | `/portal` | `@hi_require_auth` | Portal page (HTML) |

### 5.2 Organization & Tenants

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/tenants` | `@hi_require_auth` | List visible tenants (scoped by role) |
| POST | `/tenants` | `@hi_require_operator` | Create new tenant |
| GET | `/sites` | `@hi_require_auth` | List hosting sites (with miner counts) |

### 5.3 Miners & Groups

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/miners` | `@hi_require_auth` | List miners (tenant-scoped, filterable) |
| GET | `/groups` | `@hi_require_auth` | List miner groups |
| POST | `/groups` | `@hi_require_operator` | Create miner group |

### 5.4 Curtailment Engine

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/curtailment/plans` | `@hi_require_auth` | List plans (tenant-scoped) |
| POST | `/curtailment/plans` | `@hi_require_operator` | Create curtailment plan |
| POST | `/curtailment/plans/:id/simulate` | `@hi_require_operator` | Simulate plan (dry run) |
| POST | `/curtailment/plans/:id/execute` | `@hi_require_operator` | Execute plan (send commands) |
| POST | `/curtailment/plans/:id/verify` | `@hi_require_operator` | Verify execution results |
| GET | `/curtailment/plans/:id/report` | `@hi_require_auth` | Plan report (tenant-scoped) |

### 5.5 Billing & Contracts

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/tariffs` | `@hi_require_auth` | List tariff plans |
| POST | `/tariffs` | `@hi_require_operator` | Create tariff |
| GET | `/contracts` | `@hi_require_auth` | List contracts (tenant-scoped) |
| POST | `/contracts` | `@hi_require_operator` | Create contract |
| POST | `/usage/generate` | `@hi_require_operator` | Generate usage records |
| GET | `/usage` | `@hi_require_auth` | List usage records (tenant-scoped) |
| POST | `/invoices/generate` | `@hi_require_operator` | Generate invoices from contracts |
| GET | `/invoices` | `@hi_require_auth` | List invoices (tenant-scoped) |
| GET | `/invoices/:id` | `@hi_require_auth` | Invoice detail (scope-checked) |
| GET | `/invoices/:id/export.csv` | `@hi_require_auth` | Export invoice as CSV |

### 5.6 Audit & Commands

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/audit` | `@hi_require_auth` | List audit logs (org-scoped) |
| GET | `/commands/:request_id` | `@hi_require_auth` | Command execution status |

---

## 6. Data Models

### 6.1 HiTenantMembership

Binds users to tenants with specific roles. Critical for tenant isolation.

```
hi_tenant_memberships
├── id          (PK)
├── user_id     (FK → user_access.id) + INDEX
├── tenant_id   (FK → hi_tenants.id) + INDEX
├── member_role (String: 'tenant_admin' | 'tenant_viewer')
├── is_default  (Boolean: default binding)
├── created_at  (DateTime)
└── UNIQUE(user_id, tenant_id)
```

### 6.2 HiCurtailmentPlan

Represents a power curtailment plan with lifecycle: `draft → ready → executing → completed`.

```
hi_curtailment_plans
├── id, org_id, site_id, tenant_scope, tenant_id
├── name, objective ('save_cost' | 'capacity' | ...)
├── inputs_json  (electricity_rate, min_online_pct, protected_groups, ...)
├── expected_json (simulation results)
├── status (draft → ready → executing → completed)
├── created_by (FK → user_access.id)
└── created_at, updated_at
```

### 6.3 HiInvoice

```
hi_invoices
├── id, org_id, tenant_id, contract_id
├── period_start, period_end
├── subtotal, total, status ('draft' | 'issued' | 'paid')
├── line_items_json, evidence_json
└── created_at, updated_at
```

### 6.4 HiUsageRecord

```
hi_usage_records
├── id, org_id, site_id, tenant_id
├── period_start, period_end
├── kwh_estimated, avg_kw_estimated
├── method ('nominal_watts' | 'metered' | 'estimated')
├── evidence_json
└── created_at
```

---

## 7. Curtailment Engine Workflow

### 7.1 Three-Phase Process

```
         ┌─────────┐     ┌─────────┐     ┌────────┐
Draft →  │SIMULATE │ →   │EXECUTE  │ →   │VERIFY  │ → Completed
         └─────────┘     └─────────┘     └────────┘
```

**Phase 1: Simulate** (`POST /curtailment/plans/:id/simulate`)
- Reads plan inputs (electricity rate, min online %, protected groups)
- Queries groups at the target site (respects tenant_scope)
- Calculates expected savings: watts saved, hashrate lost, revenue impact
- Returns simulation without writing to DB
- Status: `draft → ready`

**Phase 2: Execute** (`POST /curtailment/plans/:id/execute`)
- Creates `HiCurtailmentAction` records for each group
- Enqueues commands to `HiCommandQueue` (stop/sleep commands)
- Takes "before snapshot" of current miner states
- Status: `ready → executing`

**Phase 3: Verify** (`POST /curtailment/plans/:id/verify`)
- Takes "after snapshot" of miner states
- Compares actual vs expected results
- Creates `HiCurtailmentResult` record
- Status: `executing → completed`

### 7.2 Simulation Parameters

```json
{
  "electricity_rate": 0.06,       // USD/kWh
  "min_online_pct": 0.2,          // Keep at least 20% online
  "protected_groups": [1, 3],     // Group IDs to skip
  "max_offline_groups": 5,        // Limit groups affected
  "duration_hours": 4,            // Plan duration
  "btc_price": 65000,             // BTC price for revenue calc
  "hashprice": 0.05               // USD/TH/day
}
```

---

## 8. Security Model

### 8.1 Tenant Isolation Guarantees

| Attack Vector | Defense |
|---|---|
| `?tenant_id=3` parameter injection | `hi_check_tenant_id_override()` validates against `g.hi_tenant_id` |
| Direct ID access (`/plans/42/report`) | `_get_scoped_plan_or_404()` checks tenant ownership |
| Invoice CSV export by ID | `_get_scoped_invoice_or_404()` checks tenant ownership |
| Role downgrade (session manipulation) | Membership always queried; `member_role` overrides session |
| Unbound user access | 403 with `HI_TENANT_BINDING_REQUIRED` error code |

### 8.2 Error Codes

| Code | HTTP Status | Meaning |
|---|---|---|
| `HI_AUTH_REQUIRED` | 401 | Not authenticated |
| `HI_TENANT_BINDING_REQUIRED` | 403 | Tenant user without membership |
| `HI_OPERATOR_REQUIRED` | 403 | Operator endpoint accessed by tenant |
| `HI_ACCESS_DENIED` | 403 | General access denied |
| `ACCESS_DENIED` | 403 | Cross-tenant data access attempt |
| `NOT_FOUND` | 404 | Resource not found (or not in scope) |

---

## 9. Verification & Testing

### 9.1 P0 Gate Test Suite

Run: `python scripts/verify_hi_tenant_isolation.py`

| Test Group | Tests | What It Validates |
|---|---|---|
| [1] Model check | 1 | `hi_tenant_memberships` table exists |
| [2] Membership records | 6 | Alpha/Beta have correct tenant_id, role, is_default |
| [3] Role mapping | 4 | Platform roles map to correct HI roles |
| [4] API isolation | 8 | Cross-tenant parameter injection blocked (6 endpoints) |
| [5] Auto-bind | 6 | Membership resolves tenant + role without session |
| [6] Role persistence | 2 | tenant_admin does not downgrade with session set |
| [7] Cross-ID access | 3 | Plan report, invoice detail, invoice CSV blocked |
| [8] Unbound 403 | 2 | Error code = HI_TENANT_BINDING_REQUIRED |
| [9] Operator scope | 4 | Admin sees all tenants, has operator_admin role |
| **Total** | **37** | |

### 9.2 Running Tests

```bash
# Initialize database
python scripts/init_db.py

# Seed demo data (org, tenants, memberships, users)
python scripts/seed_demo.py

# Run P0 verification (must show 37/37 passed)
python scripts/verify_hi_tenant_isolation.py
```

### 9.3 Demo Accounts

| Email | Password | Platform Role | HI Role | Tenant |
|---|---|---|---|---|
| `client_alpha@demo.com` | `demo123` | client | tenant_admin | Alpha Mining Corp (id=2) |
| `client_beta@demo.com` | `demo123` | client | tenant_admin | Beta Hosting LLC (id=3) |
| `admin@test.com` | `admin123` | admin | operator_admin | None (all tenants) |

---

## 10. Database Migrations

### Migration 0001: HI Tables

Creates core tables: `hi_orgs`, `hi_tenants`, `hi_groups`, `hi_audit_log`, `hi_curtailment_plans`, `hi_curtailment_actions`, `hi_curtailment_results`, `hi_command_queue`, `hi_tariffs`, `hi_contracts`, `hi_usage_records`, `hi_invoices`.

### Migration 0002: Tenant Memberships

Creates `hi_tenant_memberships` table with unique constraint on `(user_id, tenant_id)` and index on `(user_id, is_default)`.

**Note**: All `server_default` timestamps use `CURRENT_TIMESTAMP` (not `now()`) for cross-database compatibility.

---

## 11. Changelog

| Date | Change | Impact |
|---|---|---|
| 2026-02-21 | Initial HI tables + API | Core system |
| 2026-02-21 | Tenant memberships added | Membership-based binding |
| 2026-02-22 | P0 Gate: Role stability fix | `member_role` always overrides initial mapping |
| 2026-02-22 | P0 Gate: Migration compatibility | `CURRENT_TIMESTAMP` for SQLite support |
| 2026-02-22 | P0 Gate: 37-test verification suite | Regression prevention |
