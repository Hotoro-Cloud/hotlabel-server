#!/bin/bash
set -e

if [ "$1" = "api" ]; then
    echo "Starting FastAPI application..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
elif [ "$1" = "worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A app.worker.celery_app worker --loglevel=info
elif [ "$1" = "beat" ]; then
    echo "Starting Celery beat..."
    exec celery -A app.worker.celery_app beat --loglevel=info
elif [ "$1" = "flower" ]; then
    echo "Starting Flower monitoring..."
    exec celery -A app.worker.celery_app flower --port=5555 --address=0.0.0.0
else
    echo "Unknown command: $1"
    echo "Available commands: api, worker, beat, flower"
    exit 1
fi