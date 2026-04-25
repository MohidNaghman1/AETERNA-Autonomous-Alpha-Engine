#!/bin/bash
set -e

SERVICE_TYPE=${SERVICE_TYPE:-api}

echo "=== Starting service: $SERVICE_TYPE ==="

# Only the API process should run migrations.
# Worker / consumer / resolver connect to the DB but must never race alembic.
if [ "$SERVICE_TYPE" = "api" ]; then
  echo "=== Running database migrations ==="
  python -m alembic upgrade head
  echo "=== Migrations complete ==="
fi

case $SERVICE_TYPE in
  api)
    echo "Starting FastAPI web server..."
    exec uvicorn app.main:sio_app --host 0.0.0.0 --port ${PORT:-8080}
    ;;
  worker)
    echo "Starting on-chain collector worker..."
    exec python onchain_worker.py
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
  resolver)
    echo "Starting trade outcome resolver..."
    exec python -m app.modules.intelligence.application.trade_records \
      --interval-seconds ${TRADE_RESOLVER_INTERVAL_SECONDS:-120}
    ;;
  *)
    echo "ERROR: Unknown SERVICE_TYPE='$SERVICE_TYPE'"
    echo "Valid values: api | worker | consumer | resolver | celery-worker | celery-beat"
    exit 1
    ;;
esac
