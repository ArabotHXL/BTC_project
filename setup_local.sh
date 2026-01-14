#!/bin/bash
# Local Setup Script for HashInsight Platform
# This script helps set up the local environment
# IMPORTANT: Always uses conda environment 'snakeenv'

set -e

echo "🚀 HashInsight Local Setup"
echo "=========================="
echo "⚠️  This script requires conda environment 'snakeenv'"
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found. Please install Anaconda or Miniconda first."
    exit 1
fi

# Initialize conda
source "$(conda info --base)/etc/profile.d/conda.sh"

# Check if snakeenv exists
if conda env list | grep -q "snakeenv"; then
    echo "✅ Conda environment 'snakeenv' exists"
else
    echo "📦 Creating conda environment 'snakeenv'..."
    conda create -n snakeenv python=3.9 -y
    echo "✅ Environment created"
fi

# Activate environment (REQUIRED)
echo "🔧 Activating conda environment 'snakeenv'..."
conda activate snakeenv

# Verify activation
if [ "$CONDA_DEFAULT_ENV" != "snakeenv" ]; then
    echo "❌ Failed to activate snakeenv environment"
    echo "Current environment: $CONDA_DEFAULT_ENV"
    exit 1
fi

echo "✅ Activated: $CONDA_DEFAULT_ENV"
echo ""

# Check if .env file exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file"
        exit 0
    fi
fi

# Prompt for required values
echo ""
echo "📝 Please provide the following information from Replit:"
echo "   (See REPLIT_CONNECTION_CHECKLIST.md for where to find these)"
echo ""

# Get DATABASE_URL
read -p "DATABASE_URL (postgresql://...): " DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL is required!"
    exit 1
fi

# Get SESSION_SECRET
read -p "SESSION_SECRET (or press Enter to generate new one): " SESSION_SECRET
if [ -z "$SESSION_SECRET" ]; then
    echo "🔐 Generating new SESSION_SECRET..."
    SESSION_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
    echo "Generated: $SESSION_SECRET"
fi

# Get optional values
read -p "COINWARZ_API_KEY (optional, press Enter to skip): " COINWARZ_API_KEY
read -p "REDIS_URL (optional, press Enter to skip): " REDIS_URL

# Create .env file
echo ""
echo "📄 Creating .env file..."

cat > .env << EOF
# Database Connection (from Replit)
DATABASE_URL=$DATABASE_URL

# Session Security (from Replit or generated)
SESSION_SECRET=$SESSION_SECRET

# Optional - API Keys
EOF

if [ ! -z "$COINWARZ_API_KEY" ]; then
    echo "COINWARZ_API_KEY=$COINWARZ_API_KEY" >> .env
fi

if [ ! -z "$REDIS_URL" ]; then
    echo "REDIS_URL=$REDIS_URL" >> .env
fi

cat >> .env << EOF

# Optional - Configuration
ENABLE_BACKGROUND_SERVICES=0
LOG_LEVEL=INFO
FLASK_ENV=development
SKIP_DATABASE_HEALTH_CHECK=1
FAST_STARTUP=1
EOF

echo "✅ .env file created"

# Install dependencies (in snakeenv)
echo ""
echo "📦 Installing dependencies in snakeenv environment..."
echo "⚠️  Make sure 'conda activate snakeenv' is active!"
pip install -r requirements_fixed.txt

# Install python-dotenv if not present
pip install python-dotenv 2>/dev/null || true

echo ""
echo "✅ Setup complete!"
echo ""
echo "⚠️  IMPORTANT: Always activate snakeenv before running commands!"
echo ""
echo "Next steps:"
echo "1. Test database connection:"
echo "   conda activate snakeenv"
echo "   python -c \"import os; from dotenv import load_dotenv; load_dotenv(); import psycopg2; conn = psycopg2.connect(os.getenv('DATABASE_URL')); print('✅ Database connected!')\""
echo ""
echo "2. Run the application:"
echo "   conda activate snakeenv"
echo "   python main.py"
echo ""
echo "3. Access at: http://localhost:5000"
echo ""
echo "💡 Tip: Create an alias in your ~/.zshrc:"
echo "   alias hashinsight='conda activate snakeenv && cd /Users/macab/Documents/BTC/BitcoinMiningCalculator'"
echo ""
