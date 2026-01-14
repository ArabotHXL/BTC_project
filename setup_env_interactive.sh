#!/bin/bash
# Interactive .env Setup Script
# This helps you set up your .env file with values from Replit

set -e

echo "🔧 HashInsight Local Environment Setup"
echo "======================================="
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo "📄 Found existing .env file"
    echo ""
    echo "Current contents:"
    cat .env | grep -v "^#" | grep -v "^$" | head -5
    echo ""
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file"
        exit 0
    fi
fi

echo "📝 Please provide the following from Replit Secrets tab:"
echo ""

# Get DATABASE_URL
read -p "DATABASE_URL (from Replit Secrets): " DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL is required!"
    exit 1
fi

# Get SESSION_SECRET
read -p "SESSION_SECRET (from Replit Secrets, or press Enter to generate): " SESSION_SECRET
if [ -z "$SESSION_SECRET" ]; then
    echo "🔐 Generating new SESSION_SECRET..."
    source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
    conda activate snakeenv 2>/dev/null || true
    SESSION_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "✅ Generated: $SESSION_SECRET"
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
EOF

if [ ! -z "$COINWARZ_API_KEY" ]; then
    echo "COINWARZ_API_KEY=$COINWARZ_API_KEY" >> .env
fi

if [ ! -z "$REDIS_URL" ]; then
    echo "REDIS_URL=$REDIS_URL" >> .env
fi

cat >> .env << EOF

# Configuration
FLASK_ENV=development
LOG_LEVEL=INFO
ENABLE_BACKGROUND_SERVICES=0
SKIP_DATABASE_HEALTH_CHECK=1
FAST_STARTUP=1
BLOCKCHAIN_DISABLE_IPFS=true
EOF

echo "✅ .env file created successfully!"
echo ""
echo "📋 Contents:"
echo "   DATABASE_URL: ${DATABASE_URL:0:30}..."
echo "   SESSION_SECRET: ${SESSION_SECRET:0:20}..."
if [ ! -z "$COINWARZ_API_KEY" ]; then
    echo "   COINWARZ_API_KEY: Set"
fi
echo ""
echo "✅ Setup complete! You can now run the application."
