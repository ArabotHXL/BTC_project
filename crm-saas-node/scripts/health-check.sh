#!/bin/bash

echo "======================================"
echo "🏥 CRM Platform Health Check"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detect Docker Compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

# Health check results
ALL_HEALTHY=true

# Function to check service health
check_service() {
    local service_name=$1
    local check_command=$2
    
    echo -e "\n${BLUE}Checking $service_name...${NC}"
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service_name is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name is unhealthy${NC}"
        ALL_HEALTHY=false
        return 1
    fi
}

# 1. Check Docker containers are running
echo -e "\n${YELLOW}[1/4]${NC} Container Status:"
echo "========================================"
$DOCKER_COMPOSE ps

# 2. Check API Service
echo -e "\n${YELLOW}[2/4]${NC} API Service Health Check:"
echo "========================================"

# Check if API container is running
if $DOCKER_COMPOSE ps api | grep -q "Up"; then
    # Try to hit health endpoint
    if check_service "API Server" "curl -f -s http://localhost:3000/health"; then
        # Get API details
        API_RESPONSE=$(curl -s http://localhost:3000/health 2>/dev/null || echo "{}")
        echo -e "   Response: $API_RESPONSE"
    else
        echo -e "${YELLOW}   Note: API health endpoint may not be implemented yet${NC}"
        # Check if port is listening
        if nc -z localhost 3000 2>/dev/null || lsof -i:3000 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API port 3000 is listening${NC}"
        else
            echo -e "${RED}❌ API port 3000 is not accessible${NC}"
            ALL_HEALTHY=false
        fi
    fi
else
    echo -e "${RED}❌ API container is not running${NC}"
    ALL_HEALTHY=false
fi

# 3. Check Database Connection
echo -e "\n${YELLOW}[3/4]${NC} Database Health Check:"
echo "========================================"

check_service "PostgreSQL" "$DOCKER_COMPOSE exec -T db pg_isready -U crm_user -d crm_db"

if [ $? -eq 0 ]; then
    # Get database info
    DB_VERSION=$($DOCKER_COMPOSE exec -T db psql -U crm_user -d crm_db -t -c "SELECT version();" 2>/dev/null | head -1 | xargs)
    DB_SIZE=$($DOCKER_COMPOSE exec -T db psql -U crm_user -d crm_db -t -c "SELECT pg_size_pretty(pg_database_size('crm_db'));" 2>/dev/null | xargs)
    DB_TABLES=$($DOCKER_COMPOSE exec -T db psql -U crm_user -d crm_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
    
    echo -e "   Version: $DB_VERSION"
    echo -e "   Size: $DB_SIZE"
    echo -e "   Tables: $DB_TABLES"
fi

# 4. Check Redis Connection
echo -e "\n${YELLOW}[4/4]${NC} Redis Health Check:"
echo "========================================"

check_service "Redis" "$DOCKER_COMPOSE exec -T redis redis-cli ping"

if [ $? -eq 0 ]; then
    # Get Redis info
    REDIS_VERSION=$($DOCKER_COMPOSE exec -T redis redis-cli INFO server 2>/dev/null | grep redis_version | cut -d: -f2 | tr -d '\r')
    REDIS_MEMORY=$($DOCKER_COMPOSE exec -T redis redis-cli INFO memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    REDIS_KEYS=$($DOCKER_COMPOSE exec -T redis redis-cli DBSIZE 2>/dev/null | cut -d: -f2 | tr -d '\r')
    
    echo -e "   Version: $REDIS_VERSION"
    echo -e "   Memory: $REDIS_MEMORY"
    echo -e "   Keys: $REDIS_KEYS"
fi

# Summary Report
echo -e "\n======================================"
if [ "$ALL_HEALTHY" = true ]; then
    echo -e "${GREEN}✅ All Services Are Healthy${NC}"
    echo -e "======================================"
    echo -e "\n${GREEN}System Status: OPERATIONAL ✨${NC}\n"
    
    echo -e "🔗 ${GREEN}Service URLs:${NC}"
    echo -e "   API:      http://localhost:3000"
    echo -e "   Adminer:  http://localhost:8080"
    echo -e "   Database: localhost:5432"
    echo -e "   Redis:    localhost:6379"
    
    exit 0
else
    echo -e "${RED}❌ Some Services Are Unhealthy${NC}"
    echo -e "======================================"
    echo -e "\n${RED}System Status: DEGRADED ⚠️${NC}\n"
    
    echo -e "📝 ${YELLOW}Troubleshooting Steps:${NC}"
    echo -e "   1. Check logs: $DOCKER_COMPOSE logs -f"
    echo -e "   2. Restart services: ./scripts/stop.sh && ./scripts/start.sh"
    echo -e "   3. Check .env configuration"
    echo -e "   4. Verify Docker resources (memory, disk)"
    
    exit 1
fi
