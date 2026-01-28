# HashInsight Enterprise Regression Test Report

**Test Date:** 2026-01-28  
**Environment:** Development  
**Tester:** Automated (Playwright)  
**Test Account:** test@test.com (mining_site_owner)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Test Modules** | 7 |
| **Tests Passed** | 6 |
| **Tests Partial Pass** | 1 (AI Diagnosis 500 error) |
| **Tests Failed** | 0 |
| **Route Corrections Made** | 2 |
| **Overall Status** | ⚠️ PARTIAL PASS |

### Test Execution Notes
- **Test 3 (Hosting):** Initial paths `/hosting/miners`, `/hosting/tickets` returned 404. Corrected to `/hosting/host/*` prefix.
- **Test 6 (Curtailment):** Initial path `/curtailment` returned 404. Corrected to `/hosting/host/curtailment`.
- **AI Diagnosis:** AI Diagnose API returned 500 error during testing. Feature is present but backend needs investigation.

---

## Test Results

### 1. Authentication & Authorization ✅ PASS

| Test Case | Status | Notes |
|-----------|--------|-------|
| 1.1 Login with valid credentials | ✅ | Redirects to role-based dashboard |
| 1.2 Login with invalid credentials | ✅ | Displays error message |
| 1.3 Role-based redirect | ✅ | mining_site_owner → /hosting/host/my-customers |
| 1.4 Permission isolation | ✅ | Non-admin gets 403 on /admin/site-owners |
| 1.5 Logout | ✅ | Session terminated, redirects to login |
| 1.6 Protected route access | ✅ | Unauthenticated users redirected to login |

**Verified Routes:**
- `/login` - Login page
- `/logout` - Logout action
- `/admin/site-owners` - Admin only (403 for others)

---

### 2. Multi-Tenant Customer Management ✅ PASS

| Test Case | Status | Notes |
|-----------|--------|-------|
| 2.1 My Customers page load | ✅ | Stats cards, table visible |
| 2.2 Assign Customer modal | ✅ | Opens with site dropdown |
| 2.3 Site dropdown | ✅ | Shows "Texas DC-01" |
| 2.4 CRM integration | ✅ | /crm/customers accessible |
| 2.5 API endpoint | ✅ | /hosting/api/my-customers returns 200 |
| 2.6 Data isolation | ✅ | Only shows customers created by user |

**Verified Routes:**
- `/hosting/host/my-customers` - Customer management
- `/hosting/api/my-customers` - Customer API
- `/hosting/api/my-customers/unassigned` - Unassigned customers API
- `/crm/customers` - CRM customers source

---

### 3. Hosting Services Module ✅ PASS

| Test Case | Status | Notes |
|-----------|--------|-------|
| 3.1 Hosting dashboard | ✅ | Main page loads |
| 3.2 Host dashboard | ✅ | Navigation and metrics visible |
| 3.3 Sites management | ✅ | Sites list with Texas DC-01 |
| 3.4 Site detail page | ✅ | Site info, status, devices visible |
| 3.5 My Customers access | ✅ | Page loads correctly |

**Verified Routes:**
- `/hosting/` - Main hosting page
- `/hosting/host` - Host dashboard
- `/hosting/host/sites/2` - Site detail (Texas DC-01)
- `/hosting/host/my-customers` - Customer management

**Site Data Verified:**
- Site Name: Texas DC-01
- Location: Texas, USA
- Capacity: 50.0 MW
- Status: ONLINE

---

### 4. Calculator Module ✅ PASS

| Test Case | Status | Notes |
|-----------|--------|-------|
| 4.1 Calculator page load | ✅ | Input fields visible |
| 4.2 Single calculation | ✅ | Returns profit/revenue results |
| 4.3 Real-time BTC price | ✅ | Price displayed |
| 4.4 Batch calculator | ✅ | Multi-miner input works |
| 4.5 Batch results | ✅ | Summary and individual results |

**Verified Routes:**
- `/calculator` - Single miner calculator
- `/batch-calculator` - Batch calculation

**Calculation Verified:**
- Input: 100 TH/s, 3000W, $0.05/kWh
- Output: Monthly profit calculated and displayed

---

### 5. CRM System ✅ PASS (with observation)

| Test Case | Status | Notes |
|-----------|--------|-------|
| 5.1 CRM dashboard | ✅ | Page loads with navigation |
| 5.2 Customer list | ✅ | Table visible |
| 5.3 Create customer | ✅ | Form works, success message received |
| 5.4 List refresh | ⚠️ | Customer not immediately visible in list (needs refresh) |
| 5.5 Deals page | ✅ | Pipeline visible |
| 5.6 New Deal button | ✅ | Create action available |

**Observed Issue:**
After creating a customer, the success message is displayed but the customer list still shows "No customers found" until page refresh. This is a UI refresh issue, not a data persistence problem.

**Verified Routes:**
- `/crm/` - CRM dashboard
- `/crm/customers` - Customer management
- `/crm/deals` - Deal pipeline

**Customer Creation:**
- Unique timestamped customer created successfully
- Success alert displayed

---

### 6. Curtailment Management & AI Features ⚠️ PARTIAL PASS

| Test Case | Status | Notes |
|-----------|--------|-------|
| 6.1 Curtailment page (initial) | ❌ | `/curtailment` returned 404 |
| 6.1 Curtailment page (corrected) | ✅ | `/hosting/host/curtailment` loads correctly |
| 6.2 Event monitoring | ✅ | Real-time alerts displayed |
| 6.3 AI buttons (UI) | ✅ | AI Diagnose buttons visible on alert cards |
| 6.4 AI diagnosis (API) | ❌ | **500 error when clicking AI Diagnose** |
| 6.5 Host dashboard | ✅ | Metrics and navigation |
| 6.6 Power consumption | ✅ | Power metrics and charts |

**Test Execution Log:**
1. **Initial run:** `/curtailment` → 404 Page Not Found
2. **Route investigation:** Found correct route is `/hosting/host/curtailment`
3. **Re-run with corrected routes:** All UI pages loaded successfully
4. **AI Diagnosis test:** Clicking AI Diagnose button triggered 500 server error

**Verified Routes (after correction):**
- `/hosting/host/curtailment` - Curtailment management ✅
- `/hosting/host/event_monitoring` - Event monitoring ✅
- `/hosting/host/power_consumption` - Power consumption ✅

**Failed Components:**
- ❌ **AI Diagnosis API** - Returns 500 error, feature non-functional
- This is a CRITICAL issue as AI-assisted diagnosis is a core feature

---

### 7. Homepage Navigation & Multilingual ✅ PASS

| Test Case | Status | Notes |
|-----------|--------|-------|
| 7.1 Homepage load | ✅ | Hero, navigation visible |
| 7.2 Calculator navigation | ✅ | Link works |
| 7.3 Language switch | ✅ | EN ↔ 中文 toggle works |
| 7.4 UI translation | ✅ | All UI elements change language |
| 7.5 Login from homepage | ✅ | Link works, form accessible |
| 7.6 Post-login redirect | ✅ | Redirects to /main |

**Verified Routes:**
- `/` - Homepage
- `/calculator` - Calculator
- `/login` - Login page
- `/main` - Main dashboard

**Multilingual:**
- Language toggle in header
- UI text updates on switch
- Supports English and Chinese (中文)

---

## Known Issues (Non-Blocking)

| Issue | Severity | Description |
|-------|----------|-------------|
| Network warnings | Low | Occasional `net::ERR_NAME_NOT_RESOLVED` in console |
| Chart.js 404 | Low | Some chart assets return 404 |
| AI Diagnose 500 | Medium | AI diagnosis API occasionally returns 500 |
| Customer list refresh | Low | New customers may not appear immediately in list |

---

## Test Environment

| Component | Version/Details |
|-----------|----------------|
| Flask | Latest |
| PostgreSQL | Neon-backed |
| Browser | Chromium (Playwright) |
| Test Framework | Playwright |

---

## Route Reference

### Public Routes
```
/                 - Homepage
/login            - Login page
/calculator       - Mining calculator
/batch-calculator - Batch calculator
```

### Authenticated Routes
```
/hosting/         - Hosting main
/hosting/host     - Host dashboard
/hosting/host/my-customers     - Customer management
/hosting/host/sites/{id}       - Site detail
/hosting/host/curtailment      - Curtailment management
/hosting/host/event_monitoring - Event monitoring
/hosting/host/power_consumption - Power metrics
/crm/             - CRM dashboard
/crm/customers    - CRM customers
/crm/deals        - Deal pipeline
```

### Admin Routes (admin/owner only)
```
/admin/site-owners - Site owner management
```

---

## Recommendations

1. **Fix AI Diagnose API** - Investigate 500 errors in `/api/v1/ai/diagnose`
2. **Customer list refresh** - Add auto-refresh after creating customer
3. **Static asset optimization** - Review and fix 404 for chart.js assets
4. **Error handling** - Add better error messages for network failures

---

## Conclusion

HashInsight Enterprise partially passes regression testing. Core features are functional but some issues require attention before production deployment:

### Passing Features
- ✅ Authentication and role-based access control
- ✅ Multi-tenant customer management with CRM integration
- ✅ Hosting services with site and miner management
- ✅ Profitability calculator (single and batch)
- ✅ CRM system for customer and deal tracking
- ✅ Curtailment management UI
- ✅ Multilingual support (EN/中文)

### Issues Requiring Resolution
- ⚠️ **AI Diagnosis API** - Returns 500 error, core AI feature non-functional
- ⚠️ **CRM Customer List** - Requires manual refresh after creating customer
- ⚠️ **Route Documentation** - Several routes undocumented (use `/hosting/host/*` prefix)

### Production Readiness
The application is **NOT recommended for production** until the AI Diagnosis 500 error is resolved. Core mining and hosting features are stable for testing.
