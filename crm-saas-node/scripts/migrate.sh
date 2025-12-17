#!/bin/bash

set -e

echo "======================================"
echo "🔄 Database Migration Script"
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

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/crm_db_backup_${TIMESTAMP}.sql"

# Check if Docker is running
if ! $DOCKER_COMPOSE ps | grep -q "Up"; then
    echo -e "${RED}❌ Docker containers are not running. Please start them first.${NC}"
    echo -e "   Run: ./scripts/start.sh"
    exit 1
fi

# 1. Create backup directory
echo -e "\n${YELLOW}[1/4]${NC} Preparing backup directory..."
mkdir -p $BACKUP_DIR
echo -e "${GREEN}✅ Backup directory ready${NC}"

# 2. Backup current database
echo -e "\n${YELLOW}[2/4]${NC} Backing up current database..."
if $DOCKER_COMPOSE exec -T db pg_dump -U crm_user crm_db > "$BACKUP_FILE" 2>/dev/null; then
    echo -e "${GREEN}✅ Database backed up to: $BACKUP_FILE${NC}"
    
    # Compress backup
    gzip "$BACKUP_FILE" 2>/dev/null || true
    if [ -f "${BACKUP_FILE}.gz" ]; then
        echo -e "${GREEN}✅ Backup compressed: ${BACKUP_FILE}.gz${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Backup failed or database is empty${NC}"
fi

# 3. Run Prisma migrations
echo -e "\n${YELLOW}[3/4]${NC} Running Prisma migrations..."

# Check if it's a fresh migration or update
if $DOCKER_COMPOSE exec -T api sh -c "cd /app && npx prisma migrate deploy"; then
    echo -e "${GREEN}✅ Migrations applied successfully${NC}"
else
    echo -e "${RED}❌ Migration failed${NC}"
    echo -e "${YELLOW}💡 To restore from backup, run:${NC}"
    echo -e "   $DOCKER_COMPOSE exec -T db psql -U crm_user crm_db < ${BACKUP_FILE}"
    exit 1
fi

# 4. Verify migration and generate Prisma Client
echo -e "\n${YELLOW}[4/4]${NC} Verifying migration and generating Prisma Client..."

# Generate Prisma Client
if $DOCKER_COMPOSE exec -T api sh -c "cd /app && npx prisma generate"; then
    echo -e "${GREEN}✅ Prisma Client generated${NC}"
else
    echo -e "${RED}❌ Prisma Client generation failed${NC}"
    exit 1
fi

# Check database connection
if $DOCKER_COMPOSE exec -T db psql -U crm_user -d crm_db -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database connection verified${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    exit 1
fi

# Display migration status
echo -e "\n======================================"
echo -e "${GREEN}✅ Migration Completed Successfully${NC}"
echo -e "======================================\n"

echo -e "📊 ${GREEN}Migration Info:${NC}"
echo -e "   Backup saved:    ${BACKUP_FILE}.gz"
echo -e "   Migration time:  $(date)"

echo -e "\n📝 ${GREEN}Next Steps:${NC}"
echo -e "   1. Verify data integrity"
echo -e "   2. Run seed data if needed: npm run prisma:seed"
echo -e "   3. Test application functionality"

echo -e "\n💡 ${YELLOW}Rollback Instructions:${NC}"
echo -e "   To restore from backup:"
echo -e "   gunzip ${BACKUP_FILE}.gz"
echo -e "   $DOCKER_COMPOSE exec -T db psql -U crm_user crm_db < ${BACKUP_FILE}"

echo -e "\n${GREEN}Migration complete! 🎉${NC}\n"

# List recent backups
echo -e "📦 ${GREEN}Recent Backups:${NC}"
ls -lht $BACKUP_DIR | head -6
