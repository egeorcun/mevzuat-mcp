#!/bin/bash
# start.sh
# Production startup script for Mevzuat MCP Server

set -e

# Default values
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}
WORKERS=${WORKERS:-"1"}
LOG_LEVEL=${LOG_LEVEL:-"info"}

echo "🚀 Starting Mevzuat MCP Server..."
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Workers: $WORKERS"
echo "   Log Level: $LOG_LEVEL"

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if we should run with multiple workers (production)
if [ "$WORKERS" -gt 1 ]; then
    echo "🔧 Running with Gunicorn (Production Mode)"
    exec gunicorn web_server:app \
        --bind $HOST:$PORT \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --log-level $LOG_LEVEL \
        --access-logfile - \
        --error-logfile - \
        --preload \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --timeout 30 \
        --keep-alive 2
else
    echo "🔧 Running with Uvicorn (Development Mode)"
    exec uvicorn web_server:app \
        --host $HOST \
        --port $PORT \
        --log-level $LOG_LEVEL
fi
