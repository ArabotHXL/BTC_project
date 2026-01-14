#!/bin/bash
# Run all tests and show results

echo "🧪 Running All Tests..."
echo ""

# Activate snakeenv
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate snakeenv

# Run environment test
echo "📋 Testing Environment Variables..."
python test/test_environment.py

echo ""
echo ""

# Run application test
echo "🔧 Testing Application Functionality..."
python test/test_application.py

echo ""
echo "✅ All tests complete!"
echo ""
echo "Check the output above for any failures or missing variables."
