#!/bin/bash

set -e

echo "======================================"
echo "🚀 Starting CRM Platform"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. Check Docker environment
echo -e "\n${YELLOW}[1/8]${NC} Checking Docker environment..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

# Detect Docker Compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
    echo -e "${GREEN}✅ Using docker compose (plugin version)${NC}"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo -e "${GREEN}✅ Using docker-compose (standalone version)${NC}"
else
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker environment ready${NC}"

# 2. Create .env file if not exists
echo -e "\n${YELLOW}[2/8]${NC} Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created. Please update with your configuration.${NC}"
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi

# 3. Start Docker containers
echo -e "\n${YELLOW}[3/8]${NC} Starting Docker containers..."
$DOCKER_COMPOSE up -d

# 4. Wait for database to be ready
echo -e "\n${YELLOW}[4/8]${NC} Waiting for database to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if $DOCKER_COMPOSE exec -T db pg_isready -U crm_user -d crm_db > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Database is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo -e "   Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Database failed to start${NC}"
    exit 1
fi

# 5. Wait for Redis to be ready
echo -e "\n${YELLOW}[5/8]${NC} Waiting for Redis to be ready..."
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if $DOCKER_COMPOSE exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo -e "   Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Redis failed to start${NC}"
    exit 1
fi

# 6. Run database migrations
echo -e "\n${YELLOW}[6/8]${NC} Running database migrations..."
if $DOCKER_COMPOSE exec -T api sh -c "cd /app && npx prisma migrate deploy" 2>/dev/null; then
    echo -e "${GREEN}✅ Migrations completed${NC}"
else
    echo -e "${YELLOW}⚠️  No migrations to run or migration failed${NC}"
fi

# 7. Generate Prisma Client
echo -e "\n${YELLOW}[7/8]${NC} Generating Prisma Client..."
$DOCKER_COMPOSE exec -T api sh -c "cd /app && npx prisma generate" > /dev/null 2>&1
echo -e "${GREEN}✅ Prisma Client generated${NC}"

# 8. Execute seed data (optional)
echo -e "\n${YELLOW}[8/8]${NC} Seeding database (optional)..."
if $DOCKER_COMPOSE exec -T api sh -c "cd /app && npm run prisma:seed" 2>/dev/null; then
    echo -e "${GREEN}✅ Database seeded${NC}"
else
    echo -e "${YELLOW}⚠️  Seed skipped or failed${NC}"
fi

# Display service status and URLs
echo -e "\n======================================"
echo -e "${GREEN}✅ CRM Platform Started Successfully${NC}"
echo -e "======================================\n"

echo -e "📊 ${GREEN}Service Status:${NC}"
$DOCKER_COMPOSE ps

echo -e "\n🔗 ${GREEN}Access URLs:${NC}"
echo -e "   API Server:     http://localhost:3000"
echo -e "   Database Admin: http://localhost:8080"
echo -e "   Database:       localhost:5432"
echo -e "   Redis:          localhost:6379"

echo -e "\n📝 ${GREEN}Useful Commands:${NC}"
echo -e "   View logs:      $DOCKER_COMPOSE logs -f"
echo -e "   Stop services:  ./scripts/stop.sh"
echo -e "   Health check:   ./scripts/health-check.sh"
echo -e "   Run migration:  ./scripts/migrate.sh"

echo -e "\n${GREEN}Happy coding! 🎉${NC}\n"
