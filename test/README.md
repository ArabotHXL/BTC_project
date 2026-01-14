# 🧪 Test Suite

This folder contains comprehensive tests to identify what's failing and what you need from Replit.

## 📋 What's Included

### 1. `test_environment.py` - Environment Variables Test
Tests all environment variables and identifies what's missing from Replit.

**Run it:**
```bash
conda activate snakeenv
python test/test_environment.py
```

**What it checks:**
- ✅ Critical variables (DATABASE_URL, SESSION_SECRET)
- ✅ Important variables (COINWARZ_API_KEY, REDIS_URL)
- ✅ Blockchain variables (optional)
- ✅ Optional variables (with defaults)
- ✅ Database connection
- ✅ Module imports

### 2. `test_application.py` - Application Functionality Test
Tests all major components and identifies failures.

**Run it:**
```bash
conda activate snakeenv
python test/test_application.py
```

**What it checks:**
- ✅ Environment variables
- ✅ Database connection
- ✅ Flask app creation
- ✅ Database models
- ✅ Billing routes
- ✅ Calculator routes
- ✅ Cache manager
- ✅ Mining calculator
- ✅ Blueprint registration
- ✅ Python compatibility

### 3. `REPLIT_VARIABLES_NEEDED.md` - Complete Guide
User-friendly guide listing all variables needed from Replit with:
- Friendly names
- Descriptions
- Where to find them in Replit
- Examples
- Status indicators

### 4. `run_all_tests.sh` - Run All Tests
Convenience script to run all tests at once.

**Run it:**
```bash
conda activate snakeenv
./test/run_all_tests.sh
```

## 🚀 Quick Start

1. **Check what you need from Replit:**
   ```bash
   conda activate snakeenv
   python test/test_environment.py
   ```

2. **Test application functionality:**
   ```bash
   python test/test_application.py
   ```

3. **Read the guide:**
   - Open `test/REPLIT_VARIABLES_NEEDED.md` for complete instructions

## 📊 Test Results

### ✅ What's Working
- Environment variables are set correctly
- Database connection is working
- Application starts successfully

### ⚠️ Expected Warnings (Not Errors)
- Blockchain/Web3 errors: Expected in testnet mode
- Missing optional API modules: Expected if not installed
- IPFS disabled: Expected if PINATA_JWT not set

### ❌ What Needs Attention
Check the test output for any failures. Most common issues:
- Missing environment variables (see `REPLIT_VARIABLES_NEEDED.md`)
- Import errors (check dependencies)
- Database connection issues (verify DATABASE_URL)

## 💡 Tips

1. **Always activate snakeenv first:**
   ```bash
   conda activate snakeenv
   ```

2. **Check the friendly names:**
   - Variables are shown with user-friendly names
   - Example: "Database Connection" instead of "DATABASE_URL"

3. **Read the guide:**
   - `REPLIT_VARIABLES_NEEDED.md` has complete instructions
   - Shows exactly where to find each variable in Replit

4. **Run tests before starting:**
   - Helps identify issues early
   - Shows what's missing from Replit

## 🔗 Related Documentation

- [Replit Variables Needed](REPLIT_VARIABLES_NEEDED.md) - Complete variable guide
- [Local Setup Guide](../docs/LOCAL_SETUP_GUIDE.md) - Setup instructions
- [Replit Connection Checklist](../REPLIT_CONNECTION_CHECKLIST.md) - Quick checklist
