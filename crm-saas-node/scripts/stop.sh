#!/bin/bash

echo "======================================"
echo "🛑 Stopping CRM Platform"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Parse arguments
CLEAN_VOLUMES=false
if [ "$1" == "--clean" ] || [ "$1" == "-c" ]; then
    CLEAN_VOLUMES=true
fi

# Stop containers
echo -e "\n${YELLOW}Stopping Docker containers...${NC}"
$DOCKER_COMPOSE down

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Containers stopped successfully${NC}"
else
    echo -e "${RED}❌ Failed to stop containers${NC}"
    exit 1
fi

# Clean volumes if requested
if [ "$CLEAN_VOLUMES" = true ]; then
    echo -e "\n${YELLOW}Cleaning data volumes...${NC}"
    read -p "⚠️  This will delete all database and Redis data. Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $DOCKER_COMPOSE down -v
        echo -e "${GREEN}✅ Volumes cleaned${NC}"
    else
        echo -e "${YELLOW}Volume cleanup cancelled${NC}"
    fi
fi

echo -e "\n======================================"
echo -e "${GREEN}✅ CRM Platform Stopped${NC}"
echo -e "======================================\n"

echo -e "📝 ${GREEN}Available Commands:${NC}"
echo -e "   Start services:      ./scripts/start.sh"
echo -e "   View stopped status: $DOCKER_COMPOSE ps -a"
echo -e "   Clean volumes:       ./scripts/stop.sh --clean"

echo -e "\n${GREEN}Goodbye! 👋${NC}\n"
