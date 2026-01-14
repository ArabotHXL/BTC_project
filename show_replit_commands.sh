#!/bin/bash
# Commands to run in Replit Shell to get all values
# Copy and paste these into Replit Shell

echo "=== Copy these commands into Replit Shell ==="
echo ""
echo "# 1. Get DATABASE_URL"
echo "echo \$DATABASE_URL"
echo ""
echo "# 2. Get SESSION_SECRET"
echo "echo \$SESSION_SECRET"
echo ""
echo "# 3. Get COINWARZ_API_KEY (if exists)"
echo "echo \$COINWARZ_API_KEY"
echo ""
echo "# 4. List all relevant environment variables"
echo "env | grep -E '(DATABASE|SESSION|COINWARZ|REDIS)'"
echo ""
echo "=== After running in Replit, copy the output values ==="
