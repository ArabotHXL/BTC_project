# Step-by-Step Local Setup Guide

**Follow these steps to run HashInsight locally with Replit database**

---

## Step 1: Get Information from Replit

### Go to Replit Project
1. Open: https://replit.com/@hxl1992hao/BitcoinMiningCalculator
2. Click **🔒 Secrets** tab in the left sidebar

### Copy These Values:

#### Required:
- **`DATABASE_URL`** - Copy the entire PostgreSQL connection string
  - Format: `postgresql://username:password@host:port/database_name`
  
- **`SESSION_SECRET`** - Copy the session secret key
  - If not found, we'll generate one

#### Optional (for full functionality):
- **`COINWARZ_API_KEY`** - For mining data (optional)

---

## Step 2: Update Local .env File

I'll help you create/update the `.env` file with the values from Replit.

**Just provide me:**
1. The `DATABASE_URL` from Replit Secrets
2. The `SESSION_SECRET` from Replit Secrets (or I can generate one)
3. Any optional API keys you want to include

---

## Step 3: Test Database Connection

Once `.env` is set up, I'll test the connection to make sure it works.

---

## Step 4: Run the Application

I'll start the application for you.

---

## Quick Commands Reference

After setup, you can run:

```bash
# Always activate snakeenv first!
conda activate snakeenv

# Run the app
python main.py

# Or use helper script
./run_local.sh
```

---

**Ready?** Just provide me the `DATABASE_URL` and `SESSION_SECRET` from Replit, and I'll set everything up!
