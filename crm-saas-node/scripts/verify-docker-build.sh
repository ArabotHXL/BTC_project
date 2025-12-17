#!/bin/bash

set -e

echo "🔍 Verifying Docker build includes required files..."

# Navigate to crm-saas-node directory
cd "$(dirname "$0")/.."

# Build backend image with root context
echo "📦 Building backend image..."
docker build -t crm-backend-test -f ./backend/Dockerfile .

# Create temporary container
echo "🐳 Creating temporary container..."
CONTAINER_ID=$(docker create crm-backend-test)

# Check if docs/openapi.yaml exists
echo "🔎 Checking for docs/openapi.yaml in container..."
if docker cp $CONTAINER_ID:/app/docs/openapi.yaml /tmp/openapi-test.yaml 2>/dev/null; then
    echo "✅ docs/openapi.yaml found in Docker image"
    echo "📄 File size: $(wc -c < /tmp/openapi-test.yaml) bytes"
    rm /tmp/openapi-test.yaml
else
    echo "❌ docs/openapi.yaml NOT found in Docker image"
    echo "📂 Contents of /app in container:"
    docker run --rm crm-backend-test ls -la /app
    echo ""
    echo "📂 Contents of /app/docs (if exists):"
    docker run --rm crm-backend-test ls -la /app/docs 2>/dev/null || echo "docs directory not found"
    docker rm $CONTAINER_ID
    exit 1
fi

# Cleanup
docker rm $CONTAINER_ID
echo "✅ Docker build verification passed"
echo ""
echo "🎉 All checks completed successfully!"
