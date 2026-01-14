# How to Run HashInsight on Your Laptop

**Simple steps to run the application locally**

---

## ✅ Quick Start (3 Steps)

### Step 1: Open Terminal
Open Terminal on your Mac (Applications > Utilities > Terminal)

### Step 2: Navigate to Project
```bash
cd /Users/macab/Documents/BTC/BitcoinMiningCalculator
```

### Step 3: Run the Application
```bash
conda activate snakeenv
python main.py
```

That's it! The application will start and you'll see output in your terminal.

---

## 🌐 Access the Application

Once you see "Running on..." in the terminal, open your browser:

**http://localhost:5000**

---

## 📋 What You'll See

When you run `python main.py`, you'll see output like:

```
🚀 Starting BTC Mining Calculator...
✅ Database connected successfully
✅ Application initialized
 * Running on http://127.0.0.1:5000
```

---

## 🛑 To Stop the Application

Press `Ctrl + C` in the terminal where it's running.

---

## ✅ Current Setup Status

Your `.env` file is already configured with:
- ✅ DATABASE_URL (Neon PostgreSQL)
- ✅ SESSION_SECRET
- ✅ All required settings

**You're ready to run!**

---

## 🔧 Troubleshooting

### "conda: command not found"
- Make sure Anaconda/Miniconda is installed
- Or use: `source ~/anaconda3/etc/profile.d/conda.sh` first

### "Environment snakeenv not found"
- Create it: `conda create -n snakeenv python=3.9`
- Then activate: `conda activate snakeenv`

### "ModuleNotFoundError"
- Install dependencies: `pip install -r requirements_fixed.txt`

### "Port 5000 already in use"
- Stop the existing process: `pkill -f "python main.py"`
- Or use a different port: `export FLASK_RUN_PORT=5001`

---

## 💡 Pro Tips

1. **Keep terminal open** - The app runs in the terminal, so keep it open
2. **Check logs** - All application logs appear in the terminal
3. **Use helper script** - Or run `./run_local.sh` which activates snakeenv automatically

---

**Ready?** Just run:
```bash
conda activate snakeenv
python main.py
```

Then open http://localhost:5000 in your browser!
