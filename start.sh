#!/bin/sh
set -e

SERVICE_TYPE=${SERVICE_TYPE:-worker}

echo "=== Starting service: $SERVICE_TYPE ==="

case $SERVICE_TYPE in
  worker)
    echo "Starting on-chain collector worker..."
    exec python onchain_worker.py
    ;;
  consumer)
    echo "Starting RabbitMQ event consumer..."
    exec python -m app.modules.ingestion.application.consumer
    ;;
  resolver)
    echo "Starting trade outcome resolver..."
    exec python -m app.modules.intelligence.application.trade_records 
    ;;
  *)
    echo "ERROR: Unknown SERVICE_TYPE='$SERVICE_TYPE'"
    exit 1
    ;;
esac
