# How to Start the Application on Your Laptop

**Simple step-by-step instructions**

---

## ✅ Quick Start (Copy & Paste)

Open **Terminal** on your Mac and run:

```bash
cd /Users/macab/Documents/BTC/BitcoinMiningCalculator
conda activate snakeenv
python main.py
```

---

## 📋 Detailed Steps

### Step 1: Open Terminal
- Press `Cmd + Space`
- Type "Terminal"
- Press Enter

### Step 2: Navigate to Project
```bash
cd /Users/macab/Documents/BTC/BitcoinMiningCalculator
```

### Step 3: Activate Environment
```bash
conda activate snakeenv
```

You should see `(snakeenv)` in your terminal prompt.

### Step 4: Run Application
```bash
python main.py
```

---

## 🌐 What You'll See

When it starts successfully, you'll see output like:

```
✅ Loaded environment variables from .env file
✅ Database connected successfully
 * Running on http://127.0.0.1:5000
 * Running on http://0.0.0.0:5000
Press CTRL+C to quit
```

---

## 🌐 Access the Application

Once you see "Running on...", open your browser:

**http://localhost:5000**

---

## 🛑 To Stop

Press `Ctrl + C` in the terminal

---

## ❌ If It Doesn't Start

### Check 1: Environment Variables
```bash
conda activate snakeenv
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DATABASE_URL:', 'Set' if os.getenv('DATABASE_URL') else 'Missing')"
```

### Check 2: Dependencies
```bash
conda activate snakeenv
pip install -r requirements_fixed.txt
```

### Check 3: Port Available
```bash
lsof -ti:5000
```
If something is using port 5000, stop it first.

---

## 📝 Current Configuration

Your `.env` file is set up with:
- ✅ DATABASE_URL (Neon PostgreSQL)
- ✅ SESSION_SECRET
- ✅ All required settings

**Everything is ready - just run the commands above!**
