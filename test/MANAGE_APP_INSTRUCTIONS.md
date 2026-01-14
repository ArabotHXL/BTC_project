# 🚀 Application Management Script Instructions

Simple instructions for managing the Flask application using the `manage_app.sh` script.

---

## 📋 Quick Start

### 1. Make the script executable (if not already)
```bash
chmod +x manage_app.sh
```

### 2. Run commands directly

#### Start the application:
```bash
./manage_app.sh start
```

#### Check status:
```bash
./manage_app.sh status
```

#### View logs:
```bash
./manage_app.sh logs
```

#### Follow logs in real-time:
```bash
./manage_app.sh follow
```

#### Stop the application:
```bash
./manage_app.sh stop
```

#### Restart the application:
```bash
./manage_app.sh restart
```

#### Show help:
```bash
./manage_app.sh help
```

---

## 📝 Available Commands

| Command | Description |
|---------|-------------|
| `start` | Start the application on port 5001 |
| `stop` | Stop the running application |
| `restart` | Stop and start the application |
| `status` | Check if application is running and responding |
| `logs` | Show last 50 lines of application logs |
| `follow` | Follow logs in real-time (Ctrl+C to exit) |
| `help` | Show help message |

---

## 🔧 How It Works

The script:
1. ✅ Automatically activates the `snakeenv` conda environment
2. ✅ Checks if the application is already running
3. ✅ Starts the app in the background
4. ✅ Saves the PID to `/tmp/bitcoin_mining_calc.pid`
5. ✅ Logs output to `/tmp/bitcoin_mining_calc.log`
6. ✅ Provides colored status messages

---

## 📍 File Locations

- **Script**: `manage_app.sh` (in project root)
- **PID File**: `/tmp/bitcoin_mining_calc.pid`
- **Log File**: `/tmp/bitcoin_mining_calc.log`
- **Application**: Runs on `http://localhost:5001`

---

## 💡 Usage Examples

### Start the app and check status:
```bash
./manage_app.sh start
./manage_app.sh status
```

### View logs while app is running:
```bash
./manage_app.sh follow
```

### Restart after making changes:
```bash
./manage_app.sh restart
```

### Check if app is running:
```bash
./manage_app.sh status
```

---

## ⚠️ Troubleshooting

### Script says "Application is already running"
```bash
# Stop it first
./manage_app.sh stop

# Then start again
./manage_app.sh start
```

### Application fails to start
```bash
# Check the logs
./manage_app.sh logs

# Or view full log file
tail -f /tmp/bitcoin_mining_calc.log
```

### Port 5001 is already in use
```bash
# Find what's using the port
lsof -ti:5001

# Kill it manually if needed
kill -9 $(lsof -ti:5001)

# Then start the app
./manage_app.sh start
```

### Conda/snakeenv not found
```bash
# Make sure conda is in your PATH
which conda

# If not, add conda to PATH:
# source ~/anaconda3/etc/profile.d/conda.sh
# (or wherever your conda is installed)
```

---

## 🎯 Quick Reference Card

```bash
# Start
./manage_app.sh start

# Status
./manage_app.sh status

# Logs
./manage_app.sh logs

# Follow logs
./manage_app.sh follow

# Stop
./manage_app.sh stop

# Restart
./manage_app.sh restart
```

---

## 📚 Related Files

- `run_local.sh` - Simple run script (runs in foreground)
- `setup_local.sh` - Initial setup script
- `test/test_environment.py` - Environment variable checker
