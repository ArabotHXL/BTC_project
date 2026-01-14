# Replit Connection Checklist - What You Need

**Purpose:** Complete list of information needed from Replit to run the application locally

---

## ✅ Required Information from Replit

### 1. Database Connection String (REQUIRED)

**What to get:**
- Full PostgreSQL connection string (`DATABASE_URL`)

**Where to find it in Replit:**
1. **Secrets Tab (Recommended):**
   - Open your Replit project
   - Click the **🔒 Secrets** tab in the left sidebar
   - Look for `DATABASE_URL`
   - Copy the entire value

2. **Shell Command:**
   ```bash
   echo $DATABASE_URL
   ```

3. **Database Tab:**
   - Go to **Database** tab in Replit
   - Note down:
     - Host/Endpoint
     - Port (usually 5432)
     - Database name
     - Username
     - Password
   - Construct: `postgresql://username:password@host:port/database_name`

**Format:**
```
postgresql://username:password@host:port/database_name
```
or
```
postgres://username:password@host:port/database_name
```

**⚠️ Important:** Replit databases may not allow external connections. If connection fails, see troubleshooting section below.

---

### 2. Session Secret (REQUIRED)

**What to get:**
- Flask session encryption key (`SESSION_SECRET`)

**Where to find it in Replit:**
1. **Secrets Tab:**
   - Open **🔒 Secrets** tab
   - Look for `SESSION_SECRET`
   - Copy the value

2. **If it doesn't exist:**
   - Generate a new one in Replit shell:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - Or generate locally:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```

**Format:**
```
a1b2c3d4e5f6... (64 character hex string)
```

---

## 🔧 Optional Information (For Full Functionality)

### 3. CoinWarz API Key (Optional)

**What to get:**
- CoinWarz API key for mining data

**Where to find it:**
- **Secrets Tab:** Look for `COINWARZ_API_KEY`

**Note:** Application will work without this, but some mining data features may be limited.

---

### 4. Redis URL (Optional - For Caching)

**What to get:**
- Redis connection string (if using Redis cache)

**Where to find it:**
- **Secrets Tab:** Look for `REDIS_URL`

**Format:**
```
redis://host:port/0
```

**Note:** Application works without Redis (uses in-memory cache), but performance may be reduced.

---

### 5. Other Optional Environment Variables

Check Replit Secrets for these (not required, but may be useful):

- `FLASK_ENV` - Environment (development/production)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING)
- `ENABLE_BACKGROUND_SERVICES` - Enable background tasks (0 or 1)
- `SKIP_DATABASE_HEALTH_CHECK` - Skip DB check on startup (1 or 0)
- `FAST_STARTUP` - Fast startup mode (0 or 1)

---

## 📋 Quick Checklist

Before running locally, make sure you have:

- [ ] `DATABASE_URL` - PostgreSQL connection string
- [ ] `SESSION_SECRET` - Flask session key
- [ ] (Optional) `COINWARZ_API_KEY` - For mining data
- [ ] (Optional) `REDIS_URL` - For caching

---

## 🔍 How to Get These Values from Replit

### Method 1: Secrets Tab (Easiest)

1. Open your Replit project: https://replit.com/@hxl1992hao/BitcoinMiningCalculator
2. Click **🔒 Secrets** in the left sidebar
3. You'll see all environment variables listed
4. Copy each value you need

### Method 2: Shell Commands

In Replit Shell, run:

```bash
# Database URL
echo $DATABASE_URL

# Session Secret
echo $SESSION_SECRET

# CoinWarz API Key (if exists)
echo $COINWARZ_API_KEY

# Redis URL (if exists)
echo $REDIS_URL

# List all environment variables
env | grep -E "(DATABASE|SESSION|COINWARZ|REDIS)"
```

### Method 3: Database Tab

1. Go to **Database** tab in Replit
2. You'll see connection details:
   - Host/Endpoint
   - Port
   - Database name
   - Username
   - Password
3. Construct the connection string manually

---

## ⚠️ Important Notes

### Database Connection Limitations

**Replit databases may not allow external connections by default.**

If you get connection errors:

1. **Check if Replit provides a proxy URL:**
   - Some Replit databases have a proxy endpoint for external access
   - Check Replit documentation or database settings

2. **Alternative: Use Replit's Database Proxy (if available):**
   - Replit may provide a proxy URL specifically for external connections
   - This is different from the internal `DATABASE_URL`
   - Look for "External Connection" or "Proxy URL" in database settings

3. **If external connection is not possible:**
   - Export data from Replit database
   - Set up a local PostgreSQL database
   - Import the data locally
   - Update `DATABASE_URL` to point to local database

### Security Warnings

- **Never commit secrets to git** - Add `.env` to `.gitignore`
- **Keep credentials secure** - Don't share `DATABASE_URL` or `SESSION_SECRET`
- **Use different secrets for development** - Consider generating new `SESSION_SECRET` for local use

---

## 🚀 Next Steps

Once you have the information:

1. **Create `.env` file** in project root:
   ```bash
   cd /Users/macab/Documents/BTC/BitcoinMiningCalculator
   touch .env
   ```

2. **Add your values to `.env`:**
   ```env
   DATABASE_URL=postgresql://username:password@host:port/database_name
   SESSION_SECRET=your_session_secret_here
   COINWARZ_API_KEY=your_key_here  # Optional
   FLASK_ENV=development
   ```

3. **Test connection (ALWAYS activate snakeenv first):**
   ```bash
   conda activate snakeenv
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DATABASE_URL:', os.getenv('DATABASE_URL')[:50] + '...' if os.getenv('DATABASE_URL') else 'NOT SET')"
   ```

4. **Run the application (ALWAYS activate snakeenv first):**
   ```bash
   conda activate snakeenv
   python main.py
   ```
   
   **OR use the helper script:**
   ```bash
   ./run_local.sh
   ```
   (This automatically activates snakeenv for you)

---

## 📞 Need Help?

If you're having trouble getting the information:

1. **Check Replit Secrets tab** - Most reliable source
2. **Check Replit Shell** - Use `echo $VARIABLE_NAME` commands
3. **Check Replit Database tab** - For database connection details
4. **Review Replit documentation** - For database proxy/external access options

---

## 🔗 Related Documentation

- [Local Setup Guide](docs/LOCAL_SETUP_GUIDE.md) - Complete setup instructions
- [Database Architecture](cursor_created_kt_documentation/02_DATABASE_ARCHITECTURE.md) - Database structure details
