# Quick Start - Run Locally with snakeenv

**⚠️ IMPORTANT: Always activate `snakeenv` conda environment before running any commands!**

---

## 📋 What You Need from Replit

Get these values from Replit **Secrets** tab (🔒 icon):

1. **`DATABASE_URL`** - PostgreSQL connection string (REQUIRED)
2. **`SESSION_SECRET`** - Flask session key (REQUIRED)
3. **`COINWARZ_API_KEY`** - Optional, for mining data

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Get Replit Information

In Replit, open **Secrets** tab and copy:
- `DATABASE_URL`
- `SESSION_SECRET`

### Step 2: Create .env File

```bash
cd /Users/macab/Documents/BTC/BitcoinMiningCalculator
touch .env
```

Add to `.env`:
```env
DATABASE_URL=postgresql://username:password@host:port/database_name
SESSION_SECRET=your_session_secret_here
FLASK_ENV=development
```

### Step 3: Run Application

**Option A: Use Helper Script (Easiest)**
```bash
./run_local.sh
```

**Option B: Manual (Always activate snakeenv first!)**
```bash
conda activate snakeenv
python main.py
```

---

## ✅ All Commands (Always activate snakeenv first!)

### Install Dependencies
```bash
conda activate snakeenv
pip install -r requirements_fixed.txt
```

### Test Database Connection
```bash
conda activate snakeenv
python -c "import os; from dotenv import load_dotenv; load_dotenv(); import psycopg2; conn = psycopg2.connect(os.getenv('DATABASE_URL')); print('✅ Connected!')"
```

### Run Application
```bash
conda activate snakeenv
python main.py
```

### Run with Flask
```bash
conda activate snakeenv
export FLASK_APP=app.py
flask run
```

---

## 📝 Helper Scripts

### `./run_local.sh`
Automatically activates snakeenv and runs the application.

### `./setup_local.sh`
Interactive setup script that creates .env file and installs dependencies.

### `./get_replit_info.sh`
Run this in Replit Shell to get all environment variable values.

---

## 🔍 Where to Find Replit Values

1. **Replit Secrets Tab** (🔒 icon) - Easiest method
2. **Replit Shell** - Run `echo $VARIABLE_NAME`
3. **Replit Database Tab** - For database connection details

---

## ⚠️ Important Notes

- **Always activate snakeenv** before running Python commands
- **Never commit .env file** - It contains sensitive credentials
- **Database may not allow external connections** - See troubleshooting in LOCAL_SETUP_GUIDE.md

---

## 📚 Full Documentation

- [Replit Connection Checklist](REPLIT_CONNECTION_CHECKLIST.md) - What to get from Replit
- [Local Setup Guide](docs/LOCAL_SETUP_GUIDE.md) - Complete setup instructions
- [Database Architecture](cursor_created_kt_documentation/02_DATABASE_ARCHITECTURE.md) - Database details

---

## 🆘 Troubleshooting

**"conda: command not found"**
- Install Anaconda or Miniconda first

**"Environment snakeenv not found"**
- Create it: `conda create -n snakeenv python=3.9`

**"Database connection failed"**
- Replit databases may not allow external connections
- Check DATABASE_URL is correct
- See LOCAL_SETUP_GUIDE.md for alternatives

**"ModuleNotFoundError"**
- Make sure snakeenv is activated: `conda activate snakeenv`
- Install dependencies: `pip install -r requirements_fixed.txt`
