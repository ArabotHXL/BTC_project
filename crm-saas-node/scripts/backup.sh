#!/bin/bash

set -e

echo "======================================"
echo "💾 Database Backup Script"
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
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/crm_backup_$TIMESTAMP.sql"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

echo -e "\n${YELLOW}[1/3]${NC} Creating database backup..."

# Check if containers are running
if ! $DOCKER_COMPOSE ps db | grep -q "Up"; then
    echo -e "${RED}❌ Database container is not running${NC}"
    exit 1
fi

# Create backup
if $DOCKER_COMPOSE exec -T db pg_dump -U crm_user crm_db > "$BACKUP_FILE" 2>/dev/null; then
    echo -e "${GREEN}✅ Database backed up to: $BACKUP_FILE${NC}"
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

# Compress backup
echo -e "\n${YELLOW}[2/3]${NC} Compressing backup..."
gzip "$BACKUP_FILE"

if [ -f "${BACKUP_FILE}.gz" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    echo -e "${GREEN}✅ Backup compressed: ${BACKUP_FILE}.gz (${BACKUP_SIZE})${NC}"
fi

# Keep only last 7 backups
echo -e "\n${YELLOW}[3/3]${NC} Cleaning up old backups..."
find "$BACKUP_DIR" -name "crm_backup_*.sql.gz" -mtime +7 -delete
echo -e "${GREEN}✅ Old backups cleaned up (kept last 7 days)${NC}"

# Summary
echo -e "\n======================================"
echo -e "${GREEN}✅ Backup Completed Successfully${NC}"
echo -e "======================================\n"

echo -e "📦 ${GREEN}Backup Details:${NC}"
echo -e "   File:      ${BACKUP_FILE}.gz"
echo -e "   Size:      ${BACKUP_SIZE}"
echo -e "   Timestamp: $(date)"

echo -e "\n📝 ${GREEN}Available Backups:${NC}"
ls -lht $BACKUP_DIR | head -6

echo -e "\n💡 ${YELLOW}To restore this backup:${NC}"
echo -e "   ./scripts/restore.sh ${BACKUP_FILE}.gz"

echo -e "\n${GREEN}Backup complete! 🎉${NC}\n"
