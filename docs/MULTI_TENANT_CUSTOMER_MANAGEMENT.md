# Multi-Tenant Customer Management System

## Overview

HashInsight Enterprise implements a multi-tenant customer management system that allows mining site owners to manage their own customers while maintaining data isolation between different operators.

## Architecture

### Data Model

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   UserAccess    │       │    Customer     │       │  HostingSite    │
│  (Login Acct)   │       │   (CRM Data)    │       │  (Mining Site)  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id              │◄──────│ user_account_id │       │ id              │
│ email           │       │ site_id         │──────►│ owner_id        │──┐
│ role            │       │ created_by_id   │──┐    │ name            │  │
│ managed_by_site │       │ name, email     │  │    │ location        │  │
└─────────────────┘       │ company         │  │    └─────────────────┘  │
                          └─────────────────┘  │                         │
                                               │    ┌─────────────────┐  │
                                               └───►│   UserAccess    │◄─┘
                                                    │ (Site Owner)    │
                                                    └─────────────────┘
```

### Key Fields

| Table | Field | Description |
|-------|-------|-------------|
| `crm_customers` | `site_id` | Links customer to their assigned hosting site |
| `crm_customers` | `user_account_id` | Links customer to their login account (optional) |
| `crm_customers` | `created_by_id` | The user who created this customer (for ownership) |
| `hosting_sites` | `owner_id` | The site owner who manages this mining site |

## User Roles

### Platform Admin (`admin`, `owner`)
- Full access to all features
- Can view and manage all site owners
- Can assign any site to any site owner
- Can view all customers across all sites
- Access: `/admin/site-owners`

### Mining Site Owner (`mining_site_owner`)
- Manages one or more mining sites
- Can only see customers they created
- Can assign their customers to their sites
- Can create login accounts for customers
- Access: `/hosting/host/my-customers`

### Client (`client`)
- End customer with mining equipment
- Can view their own dashboard and miners
- Limited to data from their assigned site
- Access: `/hosting/` (dashboard)

## Workflow

### 1. Platform Admin: Create Site Owner

```
Admin Dashboard → Site Owner Management → Create New Site Owner
```

1. Navigate to `/admin/site-owners`
2. Click "Create Site Owner"
3. Enter name, email, password
4. Assign one or more sites to the owner

### 2. Site Owner: Create Customer in CRM

```
CRM Module → Customers → New Customer
```

1. Navigate to `/crm/customers`
2. Click "New Customer"
3. Enter customer details (name, email, company, etc.)
4. Customer is now in CRM with `created_by_id` set to current user

### 3. Site Owner: Assign Customer to Site

```
My Customers → Assign Customer → Select Customer & Site
```

1. Navigate to `/hosting/host/my-customers`
2. Click "Assign Customer"
3. Select an unassigned customer from dropdown
4. Select the target site
5. Click "Assign"

### 4. Site Owner: Create Login Account for Customer

```
My Customers → Customer Row → Create Account
```

1. In the customers table, find a customer without login
2. Click "Create Account" button
3. System generates temporary password
4. Share credentials with customer
5. Customer can now login to view their dashboard

## API Reference

### Platform Admin APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/site-owners` | List all site owners |
| POST | `/admin/site-owners/create` | Create new site owner |
| POST | `/admin/site-owners/<id>/toggle-status` | Enable/disable site owner |
| POST | `/admin/site-owners/<id>/assign-site` | Assign site to owner |
| GET | `/admin/site-owners/<id>` | View site owner details |

### Site Owner APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/hosting/host/my-customers` | Customer management page |
| GET | `/hosting/api/my-customers` | List customers for owned sites |
| GET | `/hosting/api/my-customers/unassigned` | List unassigned CRM customers |
| POST | `/hosting/host/my-customers/assign` | Assign customer to site |
| POST | `/hosting/host/my-customers/<id>/create-account` | Create login for customer |
| POST | `/hosting/host/my-customers/<id>/edit` | Edit customer info |
| POST | `/hosting/host/my-customers/<id>/toggle-status` | Enable/disable customer |

## Security & Data Isolation

### RBAC Helpers (`common/rbac.py`)

```python
# Get site IDs the current user can access
site_ids = get_accessible_site_ids()

# Filter a query by site access
query = filter_by_site_access(query, Model.site_id)

# Check if user can access a specific site
if not check_site_access(site_id):
    return 403
```

### Ownership Filtering

Site owners can only:
- See customers they created (`Customer.created_by_id == user_id`)
- Assign customers they created
- Manage customers assigned to their sites

### Applied Filters

All hosting endpoints apply site-level filtering:
- `get_sites()` - Filter by `owner_id`
- `get_miners()` - Filter by `site_id`
- `get_tickets()` - Filter by `site_id`
- `get_incidents()` - Filter by `site_id`
- `get_my_customers()` - Filter by `created_by_id` and `site_id`

## Login Redirect

Based on user role, login redirects to appropriate dashboard:

| Role | Redirect Path |
|------|---------------|
| `admin`, `owner` | `/admin/site-owners` |
| `mining_site_owner` | `/hosting/host/my-customers` |
| `client` | `/hosting/` |

## Database Migrations

```sql
-- Migration 024: Add multi-tenant fields
ALTER TABLE hosting_sites ADD COLUMN owner_id INTEGER REFERENCES user_access(id);
ALTER TABLE user_access ADD COLUMN managed_by_site_id INTEGER REFERENCES hosting_sites(id);
ALTER TABLE user_access ADD COLUMN is_active BOOLEAN DEFAULT true;

-- Migration 025: Link CRM customers to sites
ALTER TABLE crm_customers ADD COLUMN site_id INTEGER REFERENCES hosting_sites(id);
ALTER TABLE crm_customers ADD COLUMN user_account_id INTEGER REFERENCES user_access(id);
```

## UI Components

### Admin: Site Owner Management
- **Template**: `templates/owner/site_owner_management.html`
- **Features**: List, create, toggle status, assign sites

### Site Owner: My Customers
- **Template**: `templates/hosting/my_customers.html`
- **Features**: 
  - Stats cards (Total, Active, With Account, Sites)
  - Customer table with search and filters
  - Assign Customer modal
  - Create Account functionality
  - Edit and toggle status actions

## Best Practices

1. **Always use CRM as source of truth** - Create customers in CRM first, then assign to sites
2. **Create accounts only when needed** - Not all CRM customers need system login
3. **Maintain ownership chain** - `created_by_id` ensures proper data isolation
4. **Use RBAC helpers** - Always apply `filter_by_site_access()` for queries

## Troubleshooting

### "No unassigned customers" in dropdown
- The user has no CRM customers without a site assignment
- Go to CRM module first to create customers

### "Access denied" on site owner page
- Current user doesn't have `admin` or `owner` role
- Only platform admins can access site owner management

### Customer not showing in My Customers
- Customer's `site_id` may not match user's owned sites
- Check that customer was created by current user
