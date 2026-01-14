# 📡 Complete API Endpoints Reference

This document lists **ALL** API endpoints available in the application and what credentials are needed to access them.

---

## 🔓 Public APIs (No Authentication Required)

These endpoints are publicly accessible:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/btc-price` | GET | Bitcoin current price |
| `/api/get_btc_price` | GET | Bitcoin price (alias) |
| `/api/network-stats` | GET | Network statistics |
| `/api/network-data` | GET | Network data |
| `/api/market-data` | GET | Market data |
| `/api/get_network_stats` | GET | Network stats (alias) |
| `/api/get_miners` | GET | Miner models data |
| `/api/miner-data` | GET | Miner data |
| `/api/miner-models` | GET | Miner models list |
| `/health` | GET | Basic health check |
| `/api/health` | GET | Detailed health check |
| `/api/intelligence/health` | GET | Intelligence layer health |
| `/api/intelligence/health/slo` | GET | SLO metrics |

---

## 🔐 Authenticated APIs (Require Login or API Key)

### Authentication Methods

1. **Session Cookie** (after web login)
2. **API Key** (via `X-API-Key` header)
3. **JWT Token** (via `Authorization: Bearer <token>` header)

### Default Development API Key
- **Key**: `hsi_dev_key_2025`
- **Role**: `developer`
- **Usage**: Development/testing only

### Custom API Keys from Replit
- **Environment Variables**: `API_KEY_1`, `API_KEY_2`, ..., `API_KEY_10`
- **Role Variables**: `API_KEY_1_ROLE`, `API_KEY_2_ROLE`, etc.
- **Where to Find**: Replit Secrets tab (🔒)

---

## 📊 Calculator APIs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/calculate` | POST | Yes | Main profitability calculation |
| `/api/test/calculate` | POST | Yes | Test calculation endpoint |
| `/api/user-miners` | GET | Yes | Get user miner configurations |
| `/api/user-miners` | POST | Yes | Save miner configurations |
| `/api/profit-chart-data` | POST | Yes | Profit chart data |

---

## 📈 Analytics APIs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/analytics/data` | GET | Yes | Analytics data |
| `/api/analytics/market-data` | GET | Yes | Market data |
| `/api/analytics/roi-heatmap` | POST | Yes | ROI heatmap generation |
| `/api/analytics/historical-replay` | POST | Yes | Historical data replay |
| `/api/analytics/curtailment-simulation` | POST | Yes | Curtailment simulation |
| `/api/analytics/technical-indicators` | GET | Yes | Technical indicators |
| `/api/analytics/latest-report` | GET | Yes | Latest analytics report |
| `/api/analytics/price-history` | GET | Yes | Price history data |

---

## 🧠 Intelligence Layer APIs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/intelligence/forecast/<user_id>` | GET | Yes | Get forecast for user |
| `/api/intelligence/forecast/<user_id>/refresh` | POST | Yes | Refresh forecast |
| `/api/intelligence/optimize/curtailment` | POST | Yes | Optimize curtailment plan |
| `/api/intelligence/optimize/<user_id>/<date>` | GET | Yes | Get optimization schedule |
| `/api/intelligence/explain/roi/<user_id>` | GET | Yes | ROI explanation |
| `/api/intelligence/explain/roi/<user_id>/change` | GET | Yes | ROI change analysis |
| `/api/intelligence/explain/roi/<user_id>/recommendations` | GET | Yes | Get recommendations |

---

## 🏢 Hosting APIs (Prefix: `/hosting/api`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hosting/api/overview` | GET | Yes | Hosting overview |
| `/hosting/api/sites` | GET/POST | Yes | Site management |
| `/hosting/api/sites/<id>` | GET/PUT/DELETE | Yes | Site operations |
| `/hosting/api/miners` | GET/POST | Yes | Miner management |
| `/hosting/api/miners/<id>` | GET/PUT/DELETE | Yes | Miner operations |
| `/hosting/api/miners/stats` | GET | Yes | Miner statistics |
| `/hosting/api/incidents` | GET | Yes | Incident list |
| `/hosting/api/tickets` | GET/POST | Yes | Support tickets |
| `/hosting/api/usage/preview` | GET | Yes | Usage preview |
| `/hosting/api/client/reports/chart` | GET | Yes | Client reports chart |
| `/hosting/api/kpi/<site_id>` | GET | Yes | KPI data for site |

---

## 💼 CRM APIs (Prefix: `/crm/api`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/crm/api/customers` | GET/POST | Yes | Customer management |
| `/crm/api/customers/<id>` | GET/PUT/DELETE | Yes | Customer operations |
| `/crm/api/leads` | GET/POST | Yes | Lead management |
| `/crm/api/deals` | GET/POST | Yes | Deal management |
| `/crm/api/invoices` | GET/POST | Yes | Invoice management |
| `/crm/api/kpi/customers` | GET | Yes | Customer KPI |
| `/crm/api/analytics/revenue-trend` | GET | Yes | Revenue trend |

---

## 💰 Treasury & Financial APIs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/treasury/overview` | GET | Yes | Treasury overview |
| `/api/treasury/signals` | GET | Yes | Trading signals |
| `/api/treasury/advanced-signals` | GET | Yes | Advanced signals |
| `/api/treasury/backtest` | POST | Yes | Backtest trading strategy |
| `/api/portfolio/update` | POST | Yes | Update portfolio |

---

## ⛓️ Blockchain & Web3 APIs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/sla/mint-certificate` | POST | Yes | Mint SLA NFT certificate |
| `/api/blockchain/verify-data` | POST | Yes | Verify blockchain data |
| `/api/blockchain/status` | GET | Yes | Blockchain status |
| `/api/web3/sla/mint-request` | POST | Yes | Web3 mint request |
| `/api/ipfs/browser` | GET | Yes | IPFS browser |
| `/api/transparency/audit` | POST | Yes | Transparency audit |

---

## 🎛️ Control Plane APIs (Prefix: `/api/v1`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/portal/miners` | GET | Yes | Portal miners |
| `/api/v1/portal/zones` | GET | Yes | Portal zones |
| `/api/v1/sites/<id>/security-settings` | GET/PUT | Yes | Security settings |
| `/api/v1/miners/<id>/credential` | GET/PUT | Yes | Miner credentials |
| `/api/v1/miners/<id>/reveal` | POST | Yes | Reveal credentials |
| `/api/v1/edge/decrypt` | POST | Yes | Edge device decryption |

---

## 🔧 System & Admin APIs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/debug-session` | GET | Yes | Debug session info |
| `/api/crm/current-user` | GET | Yes | Current user info |
| `/api/network/snapshots` | GET | Yes | Network snapshots |

---

## 📋 What You Need from Replit for Full API Access

### For External APIs (Outgoing)
These are for the application to call external services:

1. **COINWARZ_API_KEY** - Mining data
2. **COINGECKO_API_KEY** - Price data
3. **SENDGRID_API_KEY** - Email service
4. **BLOCKCHAIN_PRIVATE_KEY** - Blockchain transactions
5. **PINATA_JWT** - IPFS storage
6. **DERIBIT_API_KEY** & **DERIBIT_API_SECRET** - Deribit exchange
7. **OKX_API_KEY** & **OKX_API_SECRET** - OKX exchange
8. **BINANCE_API_KEY** & **BINANCE_API_SECRET** - Binance exchange

### For Application APIs (Incoming)
These are for external systems to call this application:

1. **API_KEY_1** through **API_KEY_10** - Custom API keys
2. **API_KEY_1_ROLE** through **API_KEY_10_ROLE** - Roles for each key
3. **JWT_SECRET_KEY** - For JWT token generation (defaults to SESSION_SECRET)
4. **REQUEST_SIGNING_ENABLED** & **FLASK_SIGNING_SECRET** - For request signing

---

## 🔑 How to Use API Keys

### Method 1: API Key Header
```bash
curl -H "X-API-Key: hsi_dev_key_2025" \
  http://localhost:5001/api/calculate
```

### Method 2: JWT Token
```bash
curl -H "Authorization: Bearer <jwt_token>" \
  http://localhost:5001/api/calculate
```

### Method 3: Session Cookie
```bash
# After logging in via web interface
curl -b cookies.txt \
  http://localhost:5001/api/calculate
```

---

## 📝 Complete Checklist

### From Replit Secrets Tab (🔒):

#### Critical (Required):
- [x] `DATABASE_URL` - ✅ You have this!
- [ ] `SESSION_SECRET` - ⚠️ Check if you have this!

#### External API Keys (For Full Functionality):
- [ ] `COINWARZ_API_KEY` - Mining data
- [ ] `COINGECKO_API_KEY` - Price data
- [ ] `SENDGRID_API_KEY` - Email
- [ ] `GMAIL_USER` & `GMAIL_PASSWORD` - Alternative email
- [ ] `SLACK_WEBHOOK_URL` - Notifications

#### Blockchain:
- [ ] `BLOCKCHAIN_PRIVATE_KEY` - Blockchain transactions
- [ ] `PINATA_JWT` - IPFS storage
- [ ] `MINING_REGISTRY_CONTRACT_ADDRESS` - Smart contract

#### Exchange APIs:
- [ ] `DERIBIT_API_KEY` & `DERIBIT_API_SECRET`
- [ ] `OKX_API_KEY` & `OKX_API_SECRET`
- [ ] `BINANCE_API_KEY` & `BINANCE_API_SECRET`

#### Application API Keys (For External Access):
- [ ] `API_KEY_1` through `API_KEY_10` - Custom API keys
- [ ] `API_KEY_1_ROLE` through `API_KEY_10_ROLE` - Roles
- [ ] `JWT_SECRET_KEY` - JWT secret (defaults to SESSION_SECRET)
- [ ] `REQUEST_SIGNING_ENABLED` - Enable request signing
- [ ] `FLASK_SIGNING_SECRET` - Signing secret

#### Infrastructure:
- [ ] `REDIS_URL` - Caching

---

## 🚀 Quick Reference

**See the complete guide**: `test/REPLIT_API_ACCESS_GUIDE.md`

**Test your setup**:
```bash
conda activate snakeenv
python test/test_environment.py
```
