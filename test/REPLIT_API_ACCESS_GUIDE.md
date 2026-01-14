# 🔑 Complete API Access Guide - What You Need from Replit

This document lists **ALL** environment variables and credentials needed from Replit to get **full access** to all APIs and features in the application.

---

## 🔴 CRITICAL - Required for Application to Start

These **MUST** be set, otherwise the application will not start.

### 1. DATABASE_URL
- **Friendly Name**: Database Connection
- **Description**: PostgreSQL database connection string
- **Where to Find in Replit**: Secrets tab (🔒) → `DATABASE_URL`
- **Format**: `postgresql://username:password@host:port/database_name`
- **Status**: ✅ You already have this!

### 2. SESSION_SECRET
- **Friendly Name**: Session Security Key
- **Description**: Flask session encryption key (minimum 32 characters)
- **Where to Find in Replit**: Secrets tab (🔒) → `SESSION_SECRET`
- **How to Generate** (if missing):
  ```python
  import secrets
  print(secrets.token_urlsafe(32))
  ```
- **Status**: ⚠️ Check if you have this!

---

## 🟡 API KEYS - For External API Integrations

These enable full functionality with external services.

### 3. COINWARZ_API_KEY
- **Friendly Name**: CoinWarz Mining Data API Key
- **Description**: API key for CoinWarz mining profitability data
- **Where to Find in Replit**: Secrets tab (🔒) → `COINWARZ_API_KEY`
- **How to Get**: https://www.coinwarz.com/api
- **Required**: No (app works without it, but with limited mining data)
- **Used For**: 
  - Mining profitability calculations
  - Multi-coin mining data
  - Algorithm-specific profitability
- **Status**: Optional but recommended

### 4. COINGECKO_API_KEY
- **Friendly Name**: CoinGecko Price API Key
- **Description**: API key for CoinGecko cryptocurrency price data
- **Where to Find in Replit**: Secrets tab (🔒) → `COINGECKO_API_KEY`
- **How to Get**: https://www.coingecko.com/api
- **Required**: No (free tier available, but rate-limited)
- **Used For**:
  - Real-time BTC price
  - Historical price data
  - Market charts
- **Status**: Optional (free tier: 50 calls/minute)

### 5. SENDGRID_API_KEY
- **Friendly Name**: SendGrid Email API Key
- **Description**: API key for SendGrid email service
- **Where to Find in Replit**: Secrets tab (🔒) → `SENDGRID_API_KEY`
- **How to Get**: https://sendgrid.com
- **Required**: No (email features disabled without it)
- **Used For**:
  - Email notifications
  - Report delivery
  - User communications
- **Status**: Optional

### 6. GMAIL_USER & GMAIL_PASSWORD
- **Friendly Name**: Gmail SMTP Credentials
- **Description**: Gmail account for sending emails (alternative to SendGrid)
- **Where to Find in Replit**: Secrets tab (🔒) → `GMAIL_USER`, `GMAIL_PASSWORD`
- **How to Get**: 
  - Use Gmail account
  - Generate app-specific password: https://myaccount.google.com/apppasswords
- **Required**: No (only if using Gmail instead of SendGrid)
- **Used For**: Email notifications
- **Status**: Optional

### 7. SLACK_WEBHOOK_URL
- **Friendly Name**: Slack Webhook URL
- **Description**: Slack webhook for notifications
- **Where to Find in Replit**: Secrets tab (🔒) → `SLACK_WEBHOOK_URL`
- **How to Get**: Create Slack webhook in your workspace
- **Required**: No
- **Used For**: Slack notifications and alerts
- **Status**: Optional

---

## 🟢 BLOCKCHAIN & WEB3 APIs

These enable blockchain features and Web3 integrations.

### 8. BLOCKCHAIN_PRIVATE_KEY
- **Friendly Name**: Blockchain Wallet Private Key
- **Description**: Private key for blockchain transactions (Base L2 network)
- **Where to Find in Replit**: Secrets tab (🔒) → `BLOCKCHAIN_PRIVATE_KEY`
- **Format**: `0x...` (hex string)
- **Required**: No (app runs in testnet mode without it)
- **Used For**:
  - Blockchain transactions
  - NFT minting
  - Data on-chain recording
- **Security**: ⚠️ Keep this secret! Never commit to git.
- **Status**: Optional (testnet mode available)

### 9. PINATA_JWT
- **Friendly Name**: Pinata IPFS JWT Token
- **Description**: JWT token for Pinata IPFS storage service
- **Where to Find in Replit**: Secrets tab (🔒) → `PINATA_JWT`
- **How to Get**: https://pinata.cloud → Create API key → Generate JWT
- **Required**: No (set `BLOCKCHAIN_DISABLE_IPFS=true` to disable)
- **Used For**:
  - IPFS data storage
  - Blockchain transparency records
  - SLA certificate metadata
- **Alternative**: Set `BLOCKCHAIN_DISABLE_IPFS=true` to disable IPFS
- **Status**: Optional

### 10. BLOCKCHAIN_DISABLE_IPFS
- **Friendly Name**: Disable IPFS
- **Description**: Disable IPFS functionality (set to "true" if no PINATA_JWT)
- **Where to Find in Replit**: Secrets tab (🔒) → `BLOCKCHAIN_DISABLE_IPFS`
- **Value**: `true` or `false`
- **Status**: Optional (recommended if you don't have PINATA_JWT)

### 11. MINING_REGISTRY_CONTRACT_ADDRESS
- **Friendly Name**: Mining Registry Contract Address
- **Description**: Smart contract address on Base L2 network
- **Where to Find in Replit**: Secrets tab (🔒) → `MINING_REGISTRY_CONTRACT_ADDRESS`
- **Required**: Only if using blockchain features
- **Status**: Optional

---

## 🔵 INFRASTRUCTURE APIs

### 12. REDIS_URL
- **Friendly Name**: Redis Cache URL
- **Description**: Redis connection URL for caching and job queues
- **Where to Find in Replit**: Secrets tab (🔒) → `REDIS_URL`
- **Format**: `redis://host:port/0` or `redis://:password@host:port/0`
- **Required**: No (app uses in-memory cache if not set)
- **Used For**:
  - API response caching
  - Session storage
  - Background job queues
- **Status**: Optional (recommended for production)

---

## 🟣 EXCHANGE APIs (Optional - For Trading Features)

### 13. DERIBIT_API_KEY & DERIBIT_API_SECRET
- **Friendly Name**: Deribit Exchange API Credentials
- **Description**: API credentials for Deribit options trading
- **Where to Find in Replit**: Secrets tab (🔒) → `DERIBIT_API_KEY`, `DERIBIT_API_SECRET`
- **How to Get**: https://www.deribit.com → API section
- **Required**: No (only for Deribit analysis features)
- **Used For**: Options trading analysis
- **Status**: Optional

### 14. OKX_API_KEY & OKX_API_SECRET
- **Friendly Name**: OKX Exchange API Credentials
- **Description**: API credentials for OKX exchange
- **Where to Find in Replit**: Secrets tab (🔒) → `OKX_API_KEY`, `OKX_API_SECRET`
- **How to Get**: https://www.okx.com → API management
- **Required**: No
- **Used For**: Exchange data integration
- **Status**: Optional

### 15. BINANCE_API_KEY & BINANCE_API_SECRET
- **Friendly Name**: Binance Exchange API Credentials
- **Description**: API credentials for Binance exchange
- **Where to Find in Replit**: Secrets tab (🔒) → `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- **How to Get**: https://www.binance.com → API management
- **Required**: No
- **Used For**: Exchange data integration
- **Status**: Optional

---

## 🟠 ENCRYPTION & SECURITY

### 16. ENCRYPTION_PASSWORD
- **Friendly Name**: Data Encryption Master Key
- **Description**: Master password for data encryption (minimum 32 characters)
- **Where to Find in Replit**: Secrets tab (🔒) → `ENCRYPTION_PASSWORD`
- **How to Generate**:
  ```python
  import secrets
  print(secrets.token_urlsafe(32))
  ```
- **Required**: Recommended for production
- **Used For**: Encrypting sensitive data
- **Status**: Optional but recommended

### 17. ENCRYPTION_SALT
- **Friendly Name**: Encryption Salt
- **Description**: Salt for encryption key derivation
- **Where to Find in Replit**: Secrets tab (🔒) → `ENCRYPTION_SALT`
- **How to Generate**:
  ```python
  import secrets
  print(secrets.token_urlsafe(16))
  ```
- **Required**: Only if using encryption features
- **Status**: Optional

---

## 🔴 APPLICATION API AUTHENTICATION

### 18. FLASK_API_KEY (or custom API keys)
- **Friendly Name**: Flask Application API Key
- **Description**: API key for authenticating external API calls to this application
- **Where to Find in Replit**: Secrets tab (🔒) → `FLASK_API_KEY` or check `api_auth_middleware.py`
- **Default Development Key**: `hsi_dev_key_2025` (for development only)
- **Required**: No (development key available)
- **Used For**: External systems calling this application's APIs
- **Status**: Optional (development key works for testing)

### 19. REQUEST_SIGNING_ENABLED & FLASK_SIGNING_SECRET
- **Friendly Name**: Request Signing Configuration
- **Description**: Enable request signing for API security
- **Where to Find in Replit**: Secrets tab (🔒) → `REQUEST_SIGNING_ENABLED`, `FLASK_SIGNING_SECRET`
- **Required**: No (only for enhanced API security)
- **Status**: Optional

---

## 📊 API ENDPOINTS AVAILABLE IN THIS APPLICATION

### Public APIs (No Authentication Required)
- `GET /api/btc-price` - Bitcoin price
- `GET /api/network-stats` - Network statistics
- `GET /api/network-data` - Network data
- `GET /api/market-data` - Market data
- `GET /health` - Health check
- `GET /api/intelligence/health` - Intelligence layer health

### Authenticated APIs (Require Login or API Key)

#### Calculator APIs
- `POST /api/calculate` - Mining profitability calculation
- `GET /api/user-miners` - Get user miner configurations
- `POST /api/user-miners` - Save miner configurations

#### Analytics APIs
- `GET /api/analytics/data` - Analytics data
- `POST /api/analytics/roi-heatmap` - ROI heatmap
- `POST /api/analytics/historical-replay` - Historical replay
- `GET /api/analytics/technical-indicators` - Technical indicators

#### Intelligence APIs
- `GET /api/intelligence/forecast/<user_id>` - Get forecast
- `POST /api/intelligence/forecast/<user_id>/refresh` - Refresh forecast
- `POST /api/intelligence/optimize/curtailment` - Optimize curtailment
- `GET /api/intelligence/explain/roi/<user_id>` - ROI explanation

#### Hosting APIs
- `GET /hosting/api/overview` - Hosting overview
- `GET /hosting/api/sites` - Site management
- `GET /hosting/api/miners` - Miner management
- `GET /hosting/api/miners/stats` - Miner statistics

#### CRM APIs
- `GET /crm/api/customers` - Customer list
- `POST /crm/api/customers` - Create customer
- `GET /crm/api/deals` - Deal management
- `GET /crm/api/invoices` - Invoice management

#### Blockchain/Web3 APIs
- `POST /api/sla/mint-certificate` - Mint SLA NFT
- `POST /api/blockchain/verify-data` - Verify blockchain data
- `POST /api/web3/sla/mint-request` - Web3 mint request

---

## 📋 Quick Checklist from Replit

### From Replit Secrets Tab (🔒 icon):

#### Critical (Required):
- [ ] `DATABASE_URL` - ✅ You have this!
- [ ] `SESSION_SECRET` - ⚠️ Check if you have this!

#### API Keys (For Full Functionality):
- [ ] `COINWARZ_API_KEY` - For mining data
- [ ] `COINGECKO_API_KEY` - For price data (optional, free tier available)
- [ ] `SENDGRID_API_KEY` - For email (optional)
- [ ] `GMAIL_USER` & `GMAIL_PASSWORD` - Alternative to SendGrid (optional)

#### Blockchain (Optional):
- [ ] `BLOCKCHAIN_PRIVATE_KEY` - For blockchain transactions
- [ ] `PINATA_JWT` - For IPFS storage (or set `BLOCKCHAIN_DISABLE_IPFS=true`)
- [ ] `MINING_REGISTRY_CONTRACT_ADDRESS` - Smart contract address

#### Infrastructure (Optional):
- [ ] `REDIS_URL` - For caching (optional)

#### Exchange APIs (Optional):
- [ ] `DERIBIT_API_KEY` & `DERIBIT_API_SECRET` - For Deribit analysis
- [ ] `OKX_API_KEY` & `OKX_API_SECRET` - For OKX integration
- [ ] `BINANCE_API_KEY` & `BINANCE_API_SECRET` - For Binance integration

#### Security (Optional but Recommended):
- [ ] `ENCRYPTION_PASSWORD` - For data encryption
- [ ] `ENCRYPTION_SALT` - For encryption salt

---

## 🚀 How to Get These from Replit

### Method 1: Secrets Tab (Easiest)
1. Open your Replit project
2. Click the **🔒 Secrets** tab in the left sidebar
3. You'll see all environment variables listed
4. Copy each value you need

### Method 2: Shell Commands
In Replit Shell, run:
```bash
# Critical
echo $DATABASE_URL
echo $SESSION_SECRET

# API Keys
echo $COINWARZ_API_KEY
echo $COINGECKO_API_KEY
echo $SENDGRID_API_KEY

# Blockchain
echo $BLOCKCHAIN_PRIVATE_KEY
echo $PINATA_JWT

# Infrastructure
echo $REDIS_URL

# List all environment variables
env | grep -E "(API|KEY|SECRET|TOKEN|JWT|PASSWORD)"
```

---

## 💡 What Each API Key Enables

| API Key | Enables | Impact if Missing |
|---------|---------|-------------------|
| `COINWARZ_API_KEY` | Enhanced mining data | Limited mining profitability data |
| `COINGECKO_API_KEY` | Enhanced price data | Rate-limited free tier (50 calls/min) |
| `SENDGRID_API_KEY` | Email notifications | Email features disabled |
| `BLOCKCHAIN_PRIVATE_KEY` | Blockchain transactions | Testnet mode only, no transactions |
| `PINATA_JWT` | IPFS storage | IPFS features disabled |
| `REDIS_URL` | Advanced caching | In-memory cache only |
| `DERIBIT_API_KEY` | Deribit analysis | Deribit features unavailable |

---

## 🔐 Security Notes

1. **Never commit secrets to git** - Add `.env` to `.gitignore`
2. **Keep credentials secure** - Don't share API keys
3. **Use different keys for development** - Consider generating new keys for local use
4. **Rotate keys regularly** - Especially for production

---

## 📝 Next Steps

1. **Run the test suite** to see what's missing:
   ```bash
   conda activate snakeenv
   python test/test_environment.py
   ```

2. **Add missing variables** to your `.env` file

3. **Test API access**:
   ```bash
   # Test public API
   curl http://localhost:5001/api/btc-price
   
   # Test authenticated API (after login)
   curl -H "X-API-Key: your_api_key" http://localhost:5001/api/calculate
   ```

---

## 📚 Related Documentation

- [Replit Variables Needed](REPLIT_VARIABLES_NEEDED.md) - Basic variable guide
- [Hosting Access Guide](HOSTING_ACCESS_GUIDE.md) - How to access hosting features
- [Local Setup Guide](../docs/LOCAL_SETUP_GUIDE.md) - Complete setup instructions
