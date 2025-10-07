.PHONY: help up down logs migrate seed test clean restart

help:
        @echo "HashInsight Deployment Commands"
        @echo "================================"
        @echo "make up         - Start all services"
        @echo "make down       - Stop all services"
        @echo "make logs       - View logs"
        @echo "make migrate    - Run database migrations"
        @echo "make seed       - Seed database"
        @echo "make test       - Run tests"
        @echo "make clean      - Clean up volumes"
        @echo "make restart    - Restart services"

up:
        docker-compose up -d
        @echo "Services started. Web: http://localhost:5000"

down:
        docker-compose down

logs:
        docker-compose logs -f

migrate:
        docker-compose exec web python -c "from db import db; from app import app; app.app_context().push(); db.create_all()"

seed:
        docker-compose exec web python scripts/seed_data.py

test:
        docker-compose exec web pytest -v

clean:
        docker-compose down -v
        @echo "All volumes removed"

restart:
        docker-compose restart
