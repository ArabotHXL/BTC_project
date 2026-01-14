#!/bin/bash
# Script to help extract Replit information
# Run this in Replit Shell to get all needed values

echo "=== Replit Connection Information ==="
echo ""
echo "1. DATABASE_URL:"
echo $DATABASE_URL
echo ""
echo "2. SESSION_SECRET:"
if [ -z "$SESSION_SECRET" ]; then
    echo "NOT SET - Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
else
    echo $SESSION_SECRET
fi
echo ""
echo "3. COINWARZ_API_KEY:"
if [ -z "$COINWARZ_API_KEY" ]; then
    echo "NOT SET (Optional)"
else
    echo $COINWARZ_API_KEY
fi
echo ""
echo "4. REDIS_URL:"
if [ -z "$REDIS_URL" ]; then
    echo "NOT SET (Optional)"
else
    echo $REDIS_URL
fi
echo ""
echo "5. FLASK_ENV:"
echo ${FLASK_ENV:-development}
echo ""
echo "=== Copy the values above to your local .env file ==="
