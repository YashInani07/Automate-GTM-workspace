#!/bin/sh
# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start Celery Worker in the background
echo "Starting Celery worker..."
celery -A app.worker.celery_app worker --loglevel=info &

# Start Celery Beat in the background
echo "Starting Celery beat..."
celery -A app.worker.celery_app beat --loglevel=info &

# Start uvicorn as the foreground process
echo "Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
