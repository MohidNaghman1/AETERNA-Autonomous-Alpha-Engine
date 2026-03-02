#!/bin/bash
# =====================================================================
# Development Startup Script for AETERNA
# Usage: bash scripts/dev_start.sh
# =====================================================================

set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}AETERNA Development Environment Setup${NC}"
echo -e "${CYAN}========================================${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker found${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker Compose found${NC}"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please review and configure .env file${NC}"
fi

echo -e "${YELLOW}🔨 Building Docker images...${NC}"
docker-compose build

echo -e "${YELLOW}📦 Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Check if app is running
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ FastAPI app is running${NC}"
else
    echo -e "${YELLOW}⚠️  FastAPI app not ready yet, check logs with: docker-compose logs app${NC}"
fi

# Run migrations
echo -e "${YELLOW}🗄️  Running database migrations...${NC}"
docker-compose exec -T app alembic upgrade head

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Development environment is ready!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "API Documentation: ${CYAN}http://localhost:8000/docs${NC}"
echo -e "API Docs (ReDoc): ${CYAN}http://localhost:8000/redoc${NC}"
echo -e "RabbitMQ Dashboard: ${CYAN}http://localhost:15672${NC}"
echo -e "  Username: guest | Password: guest"
echo ""
echo -e "Useful commands:"
echo -e "  ${CYAN}make logs${NC}          - View logs"
echo -e "  ${CYAN}make test${NC}          - Run tests"
echo -e "  ${CYAN}make lint${NC}          - Run linters"
echo -e "  ${CYAN}make quality${NC}       - Run all quality checks"
echo -e "  ${CYAN}make down${NC}          - Stop all services"
echo ""
