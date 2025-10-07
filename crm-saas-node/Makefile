.PHONY: help start stop restart logs health migrate seed clean rebuild test

# Detect Docker Compose command
DOCKER_COMPOSE := $(shell if docker compose version > /dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)

# Default target
help:
        @echo "======================================"
        @echo "🚀 CRM Platform - Available Commands"
        @echo "======================================"
        @echo ""
        @echo "  make start      - Start all services"
        @echo "  make stop       - Stop all services"
        @echo "  make restart    - Restart all services"
        @echo "  make logs       - View logs (all services)"
        @echo "  make health     - Check service health"
        @echo "  make migrate    - Run database migrations"
        @echo "  make seed       - Seed database with sample data"
        @echo "  make clean      - Stop and remove volumes"
        @echo "  make rebuild    - Rebuild and restart services"
        @echo "  make test       - Run tests"
        @echo "  make shell-api  - Open shell in API container"
        @echo "  make shell-db   - Open PostgreSQL shell"
        @echo "  make backup     - Backup database"
        @echo ""

# Start all services
start:
        @chmod +x scripts/*.sh
        @./scripts/start.sh

# Stop all services
stop:
        @chmod +x scripts/stop.sh
        @./scripts/stop.sh

# Restart services
restart: stop start

# View logs
logs:
        @$(DOCKER_COMPOSE) logs -f

# Logs for specific service
logs-api:
        @$(DOCKER_COMPOSE) logs -f api

logs-db:
        @$(DOCKER_COMPOSE) logs -f db

logs-redis:
        @$(DOCKER_COMPOSE) logs -f redis

# Health check
health:
        @chmod +x scripts/health-check.sh
        @./scripts/health-check.sh

# Database migrations
migrate:
        @chmod +x scripts/migrate.sh
        @./scripts/migrate.sh

# Seed database
seed:
        @$(DOCKER_COMPOSE) exec api npm run prisma:seed

# Clean everything (stop + remove volumes)
clean:
        @chmod +x scripts/stop.sh
        @./scripts/stop.sh --clean

# Rebuild services
rebuild:
        @$(DOCKER_COMPOSE) down
        @$(DOCKER_COMPOSE) build --no-cache
        @make start

# Run tests
test:
        @$(DOCKER_COMPOSE) exec api npm test

# Open shell in API container
shell-api:
        @$(DOCKER_COMPOSE) exec api sh

# Open PostgreSQL shell
shell-db:
        @$(DOCKER_COMPOSE) exec db psql -U crm_user -d crm_db

# Open Redis CLI
shell-redis:
        @$(DOCKER_COMPOSE) exec redis redis-cli

# Backup database
backup:
        @mkdir -p backups
        @$(DOCKER_COMPOSE) exec -T db pg_dump -U crm_user crm_db > backups/crm_db_backup_$$(date +%Y%m%d_%H%M%S).sql
        @echo "✅ Database backed up successfully"

# Generate Prisma Client
prisma-generate:
        @$(DOCKER_COMPOSE) exec api npx prisma generate

# Prisma Studio
prisma-studio:
        @$(DOCKER_COMPOSE) exec api npx prisma studio

# Install dependencies
install:
        @$(DOCKER_COMPOSE) exec api npm install

# Development mode (with hot reload)
dev:
        @$(DOCKER_COMPOSE) up

# Production mode
prod:
        @NODE_ENV=production $(DOCKER_COMPOSE) up -d

# Check container status
status:
        @$(DOCKER_COMPOSE) ps

# Remove stopped containers
prune:
        @docker system prune -f

# Show disk usage
disk:
        @docker system df
