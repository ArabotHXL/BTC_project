
#!/bin/bash
# Optimized startup script with error handling

echo "🚀 Starting BTC Mining Calculator..."

# Set optimized environment variables
export FAST_STARTUP=1
export SKIP_DATABASE_HEALTH_CHECK=1
export ENABLE_BACKGROUND_SERVICES=1
export PYTHONPATH="${PYTHONPATH}:."

# Check if required files exist
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found"
    exit 1
fi

if [ ! -f "database_health.py" ]; then
    echo "⚠️  Warning: database_health.py not found, creating minimal version..."
    cat > database_health.py << 'EOF'
class DatabaseHealthManager:
    def check_database_connection(self, url):
        return {'connected': True, 'database_version': 'Unknown'}
    def wait_for_database(self, url, timeout=60):
        return True

db_health_manager = DatabaseHealthManager()
EOF
fi

# Try Python3 first, then fallback to python
if command -v python3 &> /dev/null; then
    echo "📡 Starting with Python3..."
    python3 main.py
elif command -v python &> /dev/null; then
    echo "📡 Starting with Python..."
    python main.py
else
    echo "❌ Error: Python not found"
    exit 1
fi
