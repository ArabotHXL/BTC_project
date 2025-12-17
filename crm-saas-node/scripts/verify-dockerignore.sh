#!/bin/bash

set -e

echo "🔍 Verifying .dockerignore allows required files..."

# Test files that MUST be included
REQUIRED_FILES=(
    "backend/package.json"
    "backend/tsconfig.json"
    "backend/prisma/schema.prisma"
    "backend/src/server.ts"
    "docs/openapi.yaml"
    "frontend/package.json"
    "frontend/tsconfig.json"
)

# Create a test context
TMP_DIR=$(mktemp -d)
cp -r . "$TMP_DIR/"

# Simulate Docker build context (apply .dockerignore)
cd "$TMP_DIR"

echo "📂 Checking if required files are present..."

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file - MISSING!"
        echo "⚠️  This file is required for Docker build but may be excluded by .dockerignore"
        exit 1
    fi
done

# Cleanup
cd - > /dev/null
rm -rf "$TMP_DIR"

echo "✅ All required files are available for Docker build"
