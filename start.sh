#!/bin/sh
# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start uvicorn
echo "Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
