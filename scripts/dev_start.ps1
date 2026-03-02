# =====================================================================
# Development Startup Script for AETERNA (Windows)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/dev_start.ps1
# =====================================================================

param(
    [Switch]$Force
)

# Colors
function Write-Success {
    Write-Host $args -ForegroundColor Green
}

function Write-Error-Custom {
    Write-Host "❌ $args" -ForegroundColor Red
}

function Write-Warning-Custom {
    Write-Host "⚠️  $args" -ForegroundColor Yellow
}

function Write-Info {
    Write-Host "ℹ️  $args" -ForegroundColor Cyan
}

# Header
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AETERNA Development Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Success "✓ Docker found"
} catch {
    Write-Error-Custom "Docker is not installed. Please install Docker Desktop first."
    exit 1
}

# Check if Docker Compose is installed
try {
    docker-compose --version | Out-Null
    Write-Success "✓ Docker Compose found"
} catch {
    Write-Error-Custom "Docker Compose is not installed."
    exit 1
}

# Create .env if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Warning-Custom "Creating .env from template..."
    Copy-Item ".env.example" ".env"
    Write-Warning-Custom "Please review and configure .env file"
}

# Build images
Write-Warning-Custom "🔨 Building Docker images..."
docker-compose build

# Start services
Write-Warning-Custom "📦 Starting services..."
docker-compose up -d

# Wait for services
Write-Warning-Custom "⏳ Waiting for services to be ready..."
Start-Sleep -Seconds 10

# Check app health
Write-Host "Checking service health..."
$HealthCheck = $null
try {
    $HealthCheck = Invoke-WebRequest -Uri "http://localhost:8000/health" -ErrorAction SilentlyContinue
    if ($HealthCheck.StatusCode -eq 200) {
        Write-Success "✓ FastAPI app is running"
    }
} catch {
    Write-Warning-Custom "FastAPI app not ready yet, check logs: docker-compose logs app"
}

# Run migrations
Write-Warning-Custom "🗄️  Running database migrations..."
docker-compose exec -T app alembic upgrade head

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Development environment is ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "API Docs (ReDoc): http://localhost:8000/redoc" -ForegroundColor Cyan
Write-Host "RabbitMQ Dashboard: http://localhost:15672" -ForegroundColor Cyan
Write-Host "  Username: guest | Password: guest"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  make logs          - View logs" -ForegroundColor Cyan
Write-Host "  make test          - Run tests" -ForegroundColor Cyan
Write-Host "  make lint          - Run linters" -ForegroundColor Cyan
Write-Host "  make quality       - Run all quality checks" -ForegroundColor Cyan
Write-Host "  make down          - Stop all services" -ForegroundColor Cyan
Write-Host ""
