#!/bin/bash
# Optimized startup script for deployment compatibility

echo "🚀 Starting BTC Mining Calculator with deployment optimizations..."

# Set deployment-optimized environment variables
export FAST_STARTUP=1
export SKIP_DATABASE_HEALTH_CHECK=1
export ENABLE_BACKGROUND_SERVICES=1

# Start the application
echo "📡 Launching Gunicorn server..."
exec gunicorn --config gunicorn.conf.py main:app