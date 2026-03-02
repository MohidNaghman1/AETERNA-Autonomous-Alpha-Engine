.PHONY: help install build up down logs test lint format typecheck clean migrate shell

# Color output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(CYAN)AETERNA - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Development Setup
install: ## Install dependencies in virtual environment
	pip install -r requirements.txt

setup: ## Complete setup (install + docker build)
	@echo "$(CYAN)Setting up environment...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env && echo "$(YELLOW)Created .env file. Please configure it.$(NC)"; fi
	pip install -r requirements.txt
	docker-compose build

# Docker Management
build: ## Build Docker images
	docker-compose build

up: ## Start all services
	@echo "$(GREEN)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started. App: http://localhost:8000$(NC)"

down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker-compose down

restart: ## Restart all services
	@echo "$(YELLOW)Restarting services...$(NC)"
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-app: ## View app logs only
	docker-compose logs -f app

clean-volumes: ## Remove all volumes (WARNING: deletes data)
	@echo "$(RED)WARNING: This will delete all data in volumes!$(NC)"
	docker-compose down -v

rebuild: clean-volumes build up migrate ## Clean rebuild from scratch

# Testing
test: ## Run tests
	docker-compose exec app pytest tests/ -v --tb=short

test-coverage: ## Run tests with coverage
	docker-compose exec app pytest tests/ -v --cov=app --cov-report=html
	@echo "$(GREEN)Coverage report generated. Open: htmlcov/index.html$(NC)"

test-fast: ## Run tests without coverage
	docker-compose exec app pytest tests/ -x -q

# Code Quality
lint: ## Lint code with flake8
	@echo "$(CYAN)Running flake8...$(NC)"
	docker-compose exec app flake8 app --max-line-length=127

format: ## Format code with black
	@echo "$(CYAN)Running black...$(NC)"
	docker-compose exec app black app

format-check: ## Check formatting without changes
	@echo "$(CYAN)Checking black...$(NC)"
	docker-compose exec app black --check app

typecheck: ## Run type checking with mypy
	@echo "$(CYAN)Running mypy...$(NC)"
	docker-compose exec app mypy app --ignore-missing-imports || true

quality: format lint typecheck test ## Run all quality checks

# Database
migrate: ## Run migrations
	@echo "$(CYAN)Running migrations...$(NC)"
	docker-compose exec app alembic upgrade head

migrate-down: ## Rollback one migration
	docker-compose exec app alembic downgrade -1

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	@if [ -z "$(MSG)" ]; then echo "$(RED)Usage: make migrate-create MSG='description'$(NC)"; exit 1; fi
	docker-compose exec app alembic revision --autogenerate -m "$(MSG)"

migrate-current: ## Show current migration version
	docker-compose exec app alembic current

db-shell: ## Access PostgreSQL shell
	docker-compose exec postgres psql -U postgres -d aeterna_db

db-dump: ## Backup database
	@echo "$(CYAN)Creating database backup...$(NC)"
	mkdir -p backups
	docker-compose exec postgres pg_dump -U postgres aeterna_db > backups/aeterna_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup created in backups/$(NC)"

# Services
shell: ## Access app shell/bash
	docker-compose exec app bash

celery-logs: ## View celery worker logs
	docker-compose logs -f celery_worker

celery-purge: ## Purge all tasks from queue
	docker-compose exec celery_worker celery -A app.modules.ingestion.infrastructure.celery_app purge -f

# Production
build-prod: ## Build production Docker image
	docker build -t aeterna:prod .

push-prod: ## Push production image to registry (requires login)
	docker tag aeterna:prod ghcr.io/your-org/aeterna:prod
	docker push ghcr.io/your-org/aeterna:prod

# Monitoring
health: ## Check service health status
	@echo "$(CYAN)Checking service health...$(NC)"
	@echo "App:" && curl -s http://localhost:8000/health || echo "❌ Not available"
	@echo "Postgres:" && docker-compose exec postgres pg_isready -U postgres || echo "❌ Not available"
	@echo "Redis:" && docker-compose exec redis redis-cli ping || echo "❌ Not available"
	@echo "RabbitMQ:" && curl -s http://localhost:15672/api/overview || echo "❌ Not available"

stats: ## Show container resource usage
	docker stats --no-stream

# Development utilities
dev: up migrate ## Start development environment with migrations
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "RabbitMQ: http://localhost:15672 (guest/guest)"

reset: ## Reset everything to fresh start
	@echo "$(RED)Resetting development environment...$(NC)"
	make down clean-volumes
	rm -f .env
	cp .env.example .env
	make up migrate
	@echo "$(GREEN)Reset complete. Configure .env if needed.$(NC)"

docs: ## Generate and open API documentation
	@echo "$(CYAN)Opening API documentation...$(NC)"
	@echo "Visit: http://localhost:8000/docs"

# Utils
requirements-freeze: ## Freeze current dependencies
	pip freeze > requirements-frozen.txt
	@echo "$(GREEN)Dependencies frozen in requirements-frozen.txt$(NC)"

.DEFAULT_GOAL := help
