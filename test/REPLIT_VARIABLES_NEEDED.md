# 📋 Environment Variables Needed from Replit

This document lists all environment variables you need to get from Replit to run the application locally.

## 🔴 CRITICAL - Required for Application to Start

These variables **MUST** be set, otherwise the application will not start.

### 1. DATABASE_URL
- **Friendly Name**: Database Connection
- **Description**: PostgreSQL database connection string
- **Where to Find in Replit**: 
  - Go to **Secrets** tab (🔒 icon)
  - Look for `DATABASE_URL`
  - Or check your Neon database dashboard
- **Format**: `postgresql://username:password@host:port/database_name`
- **Example**: `postgresql://neondb_owner:npg_b6invzHZaV7y@ep-rapid-glitter-a4u95yg1.us-east-1.aws.neon.tech/neondb?sslmode=require`
- **Status**: ✅ You already have this!

### 2. SESSION_SECRET
- **Friendly Name**: Session Security Key
- **Description**: Flask session encryption key (minimum 32 characters)
- **Where to Find in Replit**: 
  - Go to **Secrets** tab (🔒 icon)
  - Look for `SESSION_SECRET`
  - If it doesn't exist, generate one:
    ```python
    import secrets
    print(secrets.token_urlsafe(32))
    ```
- **Format**: Any secure random string (32+ characters)
- **Example**: `your-secure-random-secret-key-here-minimum-32-chars`
- **Status**: ⚠️ Check if you have this!

---

## 🟡 IMPORTANT - Recommended for Full Functionality

These variables are recommended but not strictly required.

### 3. COINWARZ_API_KEY
- **Friendly Name**: CoinWarz API Key
- **Description**: API key for CoinWarz mining data service
- **Where to Find in Replit**: Secrets tab → `COINWARZ_API_KEY`
- **Required**: No (application will work without it, but with limited data)
- **Status**: Optional

### 4. REDIS_URL
- **Friendly Name**: Redis Cache URL
- **Description**: Redis connection URL for caching (optional)
- **Where to Find in Replit**: Secrets tab → `REDIS_URL` (if using Redis)
- **Required**: No (application uses in-memory cache if not set)
- **Status**: Optional

---

## 🟢 BLOCKCHAIN - Optional Blockchain Features

These are only needed if you want blockchain functionality.

### 5. BLOCKCHAIN_PRIVATE_KEY
- **Friendly Name**: Blockchain Wallet Private Key
- **Description**: Private key for blockchain transactions
- **Where to Find in Replit**: Secrets tab → `BLOCKCHAIN_PRIVATE_KEY`
- **Required**: No (application runs in testnet mode without it)
- **Status**: Optional

### 6. PINATA_JWT
- **Friendly Name**: Pinata IPFS Token
- **Description**: Pinata JWT token for IPFS storage
- **Where to Find in Replit**: Secrets tab → `PINATA_JWT`
- **Required**: No (set `BLOCKCHAIN_DISABLE_IPFS=true` to disable)
- **Alternative**: Set `BLOCKCHAIN_DISABLE_IPFS=true` in your `.env` file
- **Status**: Optional (IPFS is disabled by default)

### 7. BLOCKCHAIN_DISABLE_IPFS
- **Friendly Name**: Disable IPFS
- **Description**: Disable IPFS functionality (set to "true" if no PINATA_JWT)
- **Where to Find in Replit**: Secrets tab → `BLOCKCHAIN_DISABLE_IPFS`
- **Required**: No (but recommended if you don't have PINATA_JWT)
- **Status**: Optional (already set to `true` in your setup)

---

## 🔵 OPTIONAL - Performance and Features

These have sensible defaults and are optional.

### 8. ENABLE_BACKGROUND_SERVICES
- **Friendly Name**: Background Services
- **Description**: Enable background scheduled tasks (0 or 1)
- **Default**: `0` (disabled)
- **Status**: Optional

### 9. LOG_LEVEL
- **Friendly Name**: Log Level
- **Description**: Logging level (DEBUG, INFO, WARNING, ERROR)
- **Default**: `INFO`
- **Status**: Optional

### 10. FLASK_ENV
- **Friendly Name**: Flask Environment
- **Description**: Flask environment (development or production)
- **Default**: `development`
- **Status**: Optional

### 11. FLASK_RUN_PORT
- **Friendly Name**: Application Port
- **Description**: Port to run Flask application
- **Default**: `5001` (5000 is used by macOS AirPlay)
- **Status**: Optional

### 12. SKIP_DATABASE_HEALTH_CHECK
- **Friendly Name**: Skip DB Health Check
- **Description**: Skip database health check on startup (1 or 0)
- **Default**: `1` (enabled for fast startup)
- **Status**: Optional

### 13. FAST_STARTUP
- **Friendly Name**: Fast Startup
- **Description**: Enable fast startup mode (1 or 0)
- **Default**: `1` (enabled)
- **Status**: Optional

---

## 📝 Quick Checklist

### From Replit Secrets Tab (🔒 icon):

- [ ] `DATABASE_URL` - ✅ You have this!
- [ ] `SESSION_SECRET` - ⚠️ Check if you have this!
- [ ] `COINWARZ_API_KEY` - Optional
- [ ] `REDIS_URL` - Optional
- [ ] `BLOCKCHAIN_PRIVATE_KEY` - Optional
- [ ] `PINATA_JWT` - Optional (or set `BLOCKCHAIN_DISABLE_IPFS=true`)

### How to Get Values from Replit:

1. **Open Replit project**
2. **Click on the 🔒 Secrets tab** (usually in the left sidebar)
3. **Find the variable name** in the list
4. **Copy the value** (click to reveal if hidden)
5. **Add to your `.env` file** locally

### If Variable Doesn't Exist in Replit:

- **SESSION_SECRET**: Generate a new one (see instructions above)
- **COINWARZ_API_KEY**: Get from https://coinwarz.com (if needed)
- **Others**: Use defaults or set to optional values

---

## 🚀 Next Steps

1. Run the test suite to see what's missing:
   ```bash
   conda activate snakeenv
   python test/test_environment.py
   ```

2. Add missing variables to your `.env` file

3. Run the application test:
   ```bash
   python test/test_application.py
   ```

4. Start the application:
   ```bash
   python main.py
   ```
