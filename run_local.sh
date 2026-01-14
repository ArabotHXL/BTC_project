#!/bin/bash
# Run HashInsight locally - Always uses snakeenv conda environment
# Usage: ./run_local.sh

# Initialize conda
source "$(conda info --base)/etc/profile.d/conda.sh"

# Activate snakeenv environment
echo "🔧 Activating conda environment: snakeenv"
conda activate snakeenv

# Verify activation
if [ "$CONDA_DEFAULT_ENV" != "snakeenv" ]; then
    echo "❌ Failed to activate snakeenv environment"
    echo "Current environment: $CONDA_DEFAULT_ENV"
    exit 1
fi

echo "✅ Running in: $CONDA_DEFAULT_ENV"
echo ""

# Load .env file if it exists
if [ -f .env ]; then
    echo "📄 Loading .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the application
echo "🚀 Starting HashInsight..."
echo ""
python main.py
