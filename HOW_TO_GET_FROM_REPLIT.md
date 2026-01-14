# How to Get Values from Replit - Step by Step

**Complete guide to getting DATABASE_URL and SESSION_SECRET from your Replit project**

---

## Method 1: Secrets Tab (Easiest - Recommended)

### Step-by-Step Instructions:

1. **Open your Replit project:**
   - Go to: https://replit.com/@hxl1992hao/BitcoinMiningCalculator
   - Or search for "BitcoinMiningCalculator" in Replit

2. **Find the Secrets tab:**
   - Look at the **left sidebar** of your Replit project
   - Find the **🔒 Secrets** icon/button (usually near the bottom of the sidebar)
   - Click on it

3. **View the secrets:**
   - You'll see a list of environment variables
   - Each secret has a name and a value
   - Values are hidden by default (shown as dots or asterisks)

4. **Get DATABASE_URL:**
   - Look for a secret named `DATABASE_URL`
   - Click on it or the "reveal" button (👁️ icon) to show the value
   - **Copy the entire value** - it should look like:
     ```
     postgresql://username:password@host:port/database_name
     ```
   - Make sure to copy the COMPLETE string

5. **Get SESSION_SECRET:**
   - Look for a secret named `SESSION_SECRET`
   - Click to reveal the value
   - **Copy the entire value** - it's a long hex string (64 characters)
   - If it doesn't exist, we can generate one

6. **Optional - Get COINWARZ_API_KEY:**
   - Look for `COINWARZ_API_KEY` (if it exists)
   - Copy the value if you want to use it

---

## Method 2: Replit Shell (Alternative)

If you can't find the Secrets tab, use the Shell:

1. **Open the Shell tab:**
   - Click on **Shell** in the Replit interface (usually at the bottom)

2. **Run these commands:**

   ```bash
   # Get DATABASE_URL
   echo $DATABASE_URL
   ```

   ```bash
   # Get SESSION_SECRET
   echo $SESSION_SECRET
   ```

   ```bash
   # Get COINWARZ_API_KEY (if exists)
   echo $COINWARZ_API_KEY
   ```

3. **Copy the output:**
   - The values will be printed in the terminal
   - Copy them carefully

---

## Method 3: Database Tab (For DATABASE_URL only)

If you need to construct the DATABASE_URL manually:

1. **Go to Database tab:**
   - Click on **Database** in the left sidebar
   - Or look for database-related tabs

2. **Find connection details:**
   - You should see:
     - **Host/Endpoint** (e.g., `db.example.com` or IP address)
     - **Port** (usually 5432 for PostgreSQL)
     - **Database name** (e.g., `mydb`)
     - **Username** (e.g., `user`)
     - **Password** (may be hidden)

3. **Construct the connection string:**
   ```
   postgresql://username:password@host:port/database_name
   ```
   
   **Example:**
   - Host: `db.example.com`
   - Port: `5432`
   - Database: `mydb`
   - Username: `user`
   - Password: `pass123`
   
   **Result:**
   ```
   postgresql://user:pass123@db.example.com:5432/mydb
   ```

---

## Visual Guide (What to Look For)

### In Replit Interface:

```
┌─────────────────────────────────┐
│  Replit Project                 │
├─────────────────────────────────┤
│  [Files] [Search] [Packages]    │
│  [Database] [🔒 Secrets] ← Click│
│  [Shell] [Console]              │
└─────────────────────────────────┘
```

### Secrets Tab View:

```
┌─────────────────────────────────┐
│  Secrets                        │
├─────────────────────────────────┤
│  DATABASE_URL                   │
│  └─ postgresql://...            │
│                                 │
│  SESSION_SECRET                 │
│  └─ a1b2c3d4e5f6...            │
│                                 │
│  COINWARZ_API_KEY (optional)    │
│  └─ your_key_here               │
└─────────────────────────────────┘
```

---

## What the Values Look Like

### DATABASE_URL Examples:

**Format 1 (postgresql://):**
```
postgresql://user:password@host.example.com:5432/database_name
```

**Format 2 (postgres://):**
```
postgres://user:password@host.example.com:5432/database_name
```

**Format 3 (with special characters in password):**
```
postgresql://user:p%40ssw%3Drd@host:5432/dbname
```
(URL-encoded password)

### SESSION_SECRET Example:

```
a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890ab
```
(64 character hexadecimal string)

---

## Troubleshooting

### "I can't find the Secrets tab"

**Solution:**
- Look for "Environment Variables" or "Env" tab
- Check if you're logged into the correct Replit account
- Try using Method 2 (Shell commands) instead

### "DATABASE_URL is not in Secrets"

**Solution:**
- Check if it's set as a regular environment variable
- Use Shell method: `echo $DATABASE_URL`
- Check if database is configured in a different way

### "The value is hidden/encrypted"

**Solution:**
- Click the "reveal" or "show" button (👁️ icon)
- Some Replit versions require clicking on the secret name
- Try double-clicking the secret

### "I see the value but it's cut off"

**Solution:**
- Click on the secret to expand it
- Use "Copy" button if available
- Or select all text and copy manually

---

## Security Notes

⚠️ **Important:**
- These values are **sensitive** - don't share them publicly
- Only use them in your local `.env` file
- Never commit `.env` to git
- Keep them secure

---

## After Getting the Values

Once you have `DATABASE_URL` and `SESSION_SECRET`:

1. **Run the setup script:**
   ```bash
   ./setup_env_interactive.sh
   ```
   Then paste the values when prompted.

2. **Or create `.env` manually:**
   ```bash
   # Create .env file
   cat > .env << 'EOF'
   DATABASE_URL=your_database_url_here
   SESSION_SECRET=your_session_secret_here
   FLASK_ENV=development
   EOF
   ```

3. **Test the connection:**
   ```bash
   source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate snakeenv && python -c "import os; from dotenv import load_dotenv; load_dotenv(); import psycopg2; conn = psycopg2.connect(os.getenv('DATABASE_URL')); print('✅ Database connected!')"
   ```

4. **Run the application:**
   ```bash
   source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate snakeenv && python main.py
   ```

---

## Quick Checklist

- [ ] Opened Replit project
- [ ] Found Secrets tab (🔒 icon)
- [ ] Copied `DATABASE_URL` (complete string)
- [ ] Copied `SESSION_SECRET` (or ready to generate)
- [ ] (Optional) Copied `COINWARZ_API_KEY`
- [ ] Ready to set up `.env` file

---

**Need more help?** If you're having trouble finding the Secrets tab, try the Shell method (Method 2) - it's often easier!
