# Get These Values from Replit

## Quick Steps

1. **Go to Replit:** https://replit.com/@hxl1992hao/BitcoinMiningCalculator
2. **Click 🔒 Secrets tab** (left sidebar)
3. **Copy these values:**

---

## Required Values

### 1. DATABASE_URL
- **What it looks like:**
  ```
  postgresql://username:password@host:port/database_name
  ```
- **Example:**
  ```
  postgresql://user:pass123@db.example.com:5432/mydb
  ```
- **Copy the ENTIRE string**

### 2. SESSION_SECRET
- **What it looks like:**
  ```
  a1b2c3d4e5f6... (64 character hex string)
  ```
- **If not found:** We can generate a new one

---

## Optional Values

### 3. COINWARZ_API_KEY (Optional)
- Only if you have a CoinWarz API key
- Application works without it

### 4. REDIS_URL (Optional)
- Only if using Redis for caching
- Application works without it (uses in-memory cache)

---

## After Getting Values

**Option 1: Use Interactive Script**
```bash
./setup_env_interactive.sh
```
Then paste the values when prompted.

**Option 2: Manual Setup**
1. Create/edit `.env` file
2. Add:
   ```env
   DATABASE_URL=your_database_url_here
   SESSION_SECRET=your_session_secret_here
   FLASK_ENV=development
   ```

---

## Need Help Finding Values?

### In Replit Shell:
```bash
echo $DATABASE_URL
echo $SESSION_SECRET
```

### In Replit Secrets Tab:
- All environment variables are listed there
- Just click to reveal and copy

---

**Once you have the values, I can help you set up the .env file!**
