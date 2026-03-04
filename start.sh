#!/bin/bash
set -e

echo "=== Running database migrations ==="
python -m alembic upgrade head

# Determine service type
SERVICE_TYPE=${SERVICE_TYPE:-api}

echo "=== Starting service: $SERVICE_TYPE ==="

case $SERVICE_TYPE in
  api)
    echo "Starting FastAPI web server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
    ;;
  celery-worker)
    echo "Starting Celery worker..."
    exec celery -A app.modules.ingestion.application.celery_app worker -l info
    ;;
  celery-beat)
    echo "Starting Celery beat scheduler..."
    exec celery -A app.modules.ingestion.application.celery_app beat -l info
    ;;
  consumer)
    echo "Starting RabbitMQ event consumer..."
    exec python -m app.modules.ingestion.application.consumer
    ;;
  *)
    echo "Unknown service type: $SERVICE_TYPE"
    exit 1
    ;;
esac
