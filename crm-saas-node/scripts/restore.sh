#!/bin/bash

set -e

echo "======================================"
echo "📥 Database Restore Script"
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

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ No backup file specified${NC}"
    echo -e "\nUsage: ./scripts/restore.sh <backup-file.sql.gz>"
    echo -e "\n📦 ${GREEN}Available backups:${NC}"
    ls -lh ./backups/ 2>/dev/null || echo "No backups found in ./backups/"
    exit 1
fi

BACKUP_FILE=$1

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Warning
echo -e "\n${RED}⚠️  WARNING: This will overwrite the current database!${NC}"
echo -e "${YELLOW}   All existing data will be lost and replaced with the backup.${NC}"
read -p "Are you sure you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Restore cancelled.${NC}"
    exit 0
fi

# Check if containers are running
if ! $DOCKER_COMPOSE ps db | grep -q "Up"; then
    echo -e "${RED}❌ Database container is not running${NC}"
    echo -e "   Run: ./scripts/start.sh"
    exit 1
fi

# Create a pre-restore backup
echo -e "\n${YELLOW}[1/4]${NC} Creating pre-restore backup..."
PRE_RESTORE_BACKUP="./backups/pre_restore_$(date +%Y%m%d_%H%M%S).sql"
$DOCKER_COMPOSE exec -T db pg_dump -U crm_user crm_db > "$PRE_RESTORE_BACKUP" 2>/dev/null
gzip "$PRE_RESTORE_BACKUP"
echo -e "${GREEN}✅ Pre-restore backup created: ${PRE_RESTORE_BACKUP}.gz${NC}"

# Drop existing connections
echo -e "\n${YELLOW}[2/4]${NC} Terminating active database connections..."
$DOCKER_COMPOSE exec -T db psql -U crm_user -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'crm_db' AND pid <> pg_backend_pid();" > /dev/null 2>&1
echo -e "${GREEN}✅ Connections terminated${NC}"

# Restore from backup
echo -e "\n${YELLOW}[3/4]${NC} Restoring database from $BACKUP_FILE..."

if [[ "$BACKUP_FILE" == *.gz ]]; then
    # Decompress and restore
    if gunzip -c "$BACKUP_FILE" | $DOCKER_COMPOSE exec -T db psql -U crm_user crm_db > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Database restored successfully${NC}"
    else
        echo -e "${RED}❌ Restore failed${NC}"
        echo -e "${YELLOW}💡 Restoring from pre-restore backup...${NC}"
        gunzip -c "${PRE_RESTORE_BACKUP}.gz" | $DOCKER_COMPOSE exec -T db psql -U crm_user crm_db > /dev/null 2>&1
        echo -e "${GREEN}✅ Rolled back to pre-restore state${NC}"
        exit 1
    fi
else
    # Direct restore
    if cat "$BACKUP_FILE" | $DOCKER_COMPOSE exec -T db psql -U crm_user crm_db > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Database restored successfully${NC}"
    else
        echo -e "${RED}❌ Restore failed${NC}"
        exit 1
    fi
fi

# Verify restore
echo -e "\n${YELLOW}[4/4]${NC} Verifying database integrity..."
if $DOCKER_COMPOSE exec -T db psql -U crm_user -d crm_db -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database connection verified${NC}"
else
    echo -e "${RED}❌ Database verification failed${NC}"
    exit 1
fi

# Summary
echo -e "\n======================================"
echo -e "${GREEN}✅ Restore Completed Successfully${NC}"
echo -e "======================================\n"

echo -e "📊 ${GREEN}Restore Details:${NC}"
echo -e "   Source:        $BACKUP_FILE"
echo -e "   Pre-backup:    ${PRE_RESTORE_BACKUP}.gz"
echo -e "   Restore time:  $(date)"

echo -e "\n📝 ${GREEN}Next Steps:${NC}"
echo -e "   1. Restart backend: $DOCKER_COMPOSE restart api"
echo -e "   2. Verify data integrity"
echo -e "   3. Test application functionality"

echo -e "\n💡 ${YELLOW}Rollback Instructions:${NC}"
echo -e "   To rollback to pre-restore state:"
echo -e "   ./scripts/restore.sh ${PRE_RESTORE_BACKUP}.gz"

echo -e "\n${GREEN}Restore complete! 🎉${NC}\n"
