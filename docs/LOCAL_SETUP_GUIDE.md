# Local Setup Guide - Connect to Replit Database

This guide explains how to run the Bitcoin Mining Calculator locally while keeping your data in the Replit PostgreSQL database.

## Prerequisites

1. **Python 3.9+** installed
2. **Conda** installed (for `snakeenv` environment)
3. **Access to your Replit project** to retrieve database credentials

## Step 1: Get Database Connection Details from Replit

### Option A: From Replit Environment Variables (Recommended)

1. Open your Replit project: https://replit.com/@hxl1992hao/BitcoinMiningCalculator
2. Click on the **Secrets** tab (🔒 icon) in the left sidebar
3. Look for the `DATABASE_URL` environment variable
4. Copy the entire connection string - it should look like:
   ```
   postgresql://username:password@host:port/database_name
   ```
   or
   ```
   postgres://username:password@host:port/database_name
   ```

### Option B: From Replit Shell

1. In your Replit project, open the Shell
2. Run:
   ```bash
   echo $DATABASE_URL
   ```
3. Copy the output

### Option C: From Replit Database Tab

1. In Replit, go to the **Database** tab
2. You'll see connection details including:
   - Host
   - Port
   - Database name
   - Username
   - Password
3. Construct the connection string manually:
   ```
   postgresql://username:password@host:port/database_name
   ```

### Important Note About External Connections

⚠️ **Replit databases may not allow external connections by default**. If you cannot connect from your local machine, you have two options:

1. **Use Replit's Database Proxy** (if available):
   - Replit may provide a proxy URL for external access
   - Check Replit documentation for database proxy setup

2. **Use a VPN/Tunnel**:
   - Set up a tunnel using tools like `ngrok` or similar
   - This is more complex and may violate Replit's terms of service

3. **Alternative: Export and Import Data**:
   - Export data from Replit database
   - Set up a local PostgreSQL database
   - Import the data locally

## Step 2: Get Session Secret from Replit

1. In Replit, check the **Secrets** tab for `SESSION_SECRET`
2. If it doesn't exist, you can generate a new one:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Copy the generated secret

## Step 3: Set Up Local Environment

### ⚠️ IMPORTANT: Always Use snakeenv Environment

**Every command must be run with `conda activate snakeenv` first!**

### Activate Conda Environment

```bash
conda activate snakeenv
```

If the environment doesn't exist, create it:
```bash
conda create -n snakeenv python=3.9
conda activate snakeenv
```

**Remember:** Always activate snakeenv before running any Python commands!

### Install Dependencies

**⚠️ Make sure snakeenv is activated first!**

```bash
conda activate snakeenv
cd /Users/macab/Documents/BTC/BitcoinMiningCalculator
pip install -r requirements_fixed.txt
```

## Step 4: Configure Environment Variables

### Option A: Create a `.env` file (Recommended)

Create a `.env` file in the project root:

```bash
cd /Users/macab/Documents/BTC/BitcoinMiningCalculator
touch .env
```

Add the following to `.env`:

```env
# Required - Database Connection (from Replit)
DATABASE_URL=postgresql://username:password@host:port/database_name

# Required - Session Security
SESSION_SECRET=your_session_secret_from_replit

# Optional - API Keys
COINWARZ_API_KEY=your_coinwarz_api_key_if_you_have_one

# Optional - Background Services
ENABLE_BACKGROUND_SERVICES=0

# Optional - Logging
LOG_LEVEL=INFO
FLASK_ENV=development
```

**Replace the values** with your actual Replit credentials.

### Option B: Export Environment Variables in Terminal

```bash
export DATABASE_URL="postgresql://username:password@host:port/database_name"
export SESSION_SECRET="your_session_secret_from_replit"
export COINWARZ_API_KEY="your_api_key"  # Optional
export ENABLE_BACKGROUND_SERVICES="0"   # Optional
export FLASK_ENV="development"          # Optional
```

### Option C: Use a Shell Script

Create a file `setup_env.sh`:

```bash
#!/bin/bash
export DATABASE_URL="postgresql://username:password@host:port/database_name"
export SESSION_SECRET="your_session_secret_from_replit"
export COINWARZ_API_KEY="your_api_key"
export ENABLE_BACKGROUND_SERVICES="0"
export FLASK_ENV="development"
```

Make it executable and source it:
```bash
chmod +x setup_env.sh
source setup_env.sh
```

## Step 5: Test Database Connection

Before running the full application, test the connection:

**⚠️ Always activate snakeenv first!**

```bash
conda activate snakeenv
python -c "
import os
import psycopg2
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('❌ DATABASE_URL not set')
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()
    print(f'✅ Database connected successfully!')
    print(f'PostgreSQL version: {version[0]}')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    print('⚠️  Make sure:')
    print('   1. DATABASE_URL is correct')
    print('   2. Replit database allows external connections')
    print('   3. Your IP is whitelisted (if required)')
"
```

## Step 6: Run the Application

### ⚠️ IMPORTANT: Always Activate snakeenv First!

**Every run command requires `conda activate snakeenv` before execution.**

### Option 1: Using Helper Script (Easiest)

```bash
./run_local.sh
```
This script automatically activates snakeenv and runs the application.

### Option 2: Using main.py (Manual)

```bash
conda activate snakeenv
python main.py
```

### Option 3: Using app.py directly

```bash
conda activate snakeenv
export FLASK_APP=app.py
flask run
```

### Option 4: Using Gunicorn (Production-like)

```bash
conda activate snakeenv
gunicorn -c gunicorn.conf.py app:app
```

**Remember:** Always run `conda activate snakeenv` before any Python command!

## Step 7: Access the Application

Once running, the application should be available at:
- **Local**: http://127.0.0.1:5000 or http://localhost:5000
- Check the terminal output for the exact port

## Troubleshooting

### Database Connection Issues

**Error: "connection refused" or "timeout"**
- Replit databases may not allow external connections
- Check if Replit provides a database proxy URL
- Consider using a VPN or tunnel (check Replit terms of service)

**Error: "authentication failed"**
- Verify your `DATABASE_URL` is correct
- Check username and password in the connection string
- Ensure credentials haven't changed in Replit

**Error: "database does not exist"**
- Verify the database name in `DATABASE_URL`
- Check if the database exists in Replit

### Session Secret Issues

**Error: "SESSION_SECRET environment variable must be set"**
- Make sure you've exported `SESSION_SECRET` or added it to `.env`
- If using `.env`, ensure you're loading it (Flask doesn't auto-load `.env` - you may need `python-dotenv`)

### Missing Dependencies

**Error: "ModuleNotFoundError"**
- Make sure you're in the `snakeenv` conda environment
- Reinstall dependencies: `pip install -r requirements_fixed.txt`

### Port Already in Use

**Error: "Address already in use"**
- Change the port: `export FLASK_RUN_PORT=5001`
- Or kill the process using port 5000

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string from Replit | `postgresql://user:pass@host:5432/dbname` |
| `SESSION_SECRET` | Flask session encryption key | `your_secret_key_here` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `COINWARZ_API_KEY` | API key for CoinWarz service | None |
| `ENABLE_BACKGROUND_SERVICES` | Enable background tasks | `0` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING) | `INFO` |
| `FLASK_ENV` | Flask environment (development/production) | `development` |
| `SKIP_DATABASE_HEALTH_CHECK` | Skip DB health check on startup | `1` |
| `FAST_STARTUP` | Enable fast startup mode | `0` |

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit `.env` file** - Add it to `.gitignore`
2. **Keep `SESSION_SECRET` secure** - Use a strong random string
3. **Database credentials** - Treat `DATABASE_URL` as sensitive
4. **Local development** - The app uses `DevelopmentConfig` which has relaxed security settings

## Next Steps

Once the application is running locally:

1. **Test the connection** - Log in and verify data loads from Replit database
2. **Check functionality** - Test key features to ensure everything works
3. **Monitor performance** - Note any latency due to remote database connection
4. **Consider caching** - For better performance, you might want to enable Redis caching locally

## Alternative: Using python-dotenv for .env Support

If you want automatic `.env` file loading, install `python-dotenv`:

```bash
pip install python-dotenv
```

Then add this to the top of `main.py` or `app.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

This will automatically load variables from `.env` file when the app starts.
