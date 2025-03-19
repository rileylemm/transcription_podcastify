#!/bin/bash

# Script to stop Supervisord for the YouTube Transcript Analyzer

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$PROJECT_DIR/service"
SUPERVISOR_CONF="$SERVICE_DIR/supervisord.conf"

# Check if Supervisord is running
if [ ! -f "$SERVICE_DIR/supervisord.pid" ]; then
    echo "Supervisord is not running"
    exit 0
fi

PID=$(cat "$SERVICE_DIR/supervisord.pid")
if ! ps -p $PID > /dev/null; then
    echo "Supervisord is not running (stale PID file)"
    rm "$SERVICE_DIR/supervisord.pid"
    exit 0
fi

# Stop Supervisord
echo "Stopping Supervisord..."
supervisorctl -c "$SUPERVISOR_CONF" shutdown

# Wait for Supervisord to stop
echo "Waiting for Supervisord to stop..."
for i in {1..10}; do
    if ! ps -p $PID > /dev/null; then
        echo "Supervisord stopped successfully"
        exit 0
    fi
    sleep 1
done

# If Supervisord didn't stop, kill it
echo "Supervisord didn't stop gracefully, killing it..."
kill -9 $PID
rm "$SERVICE_DIR/supervisord.pid"
echo "Supervisord killed" 