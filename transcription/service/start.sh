#!/bin/bash

# Script to start Supervisord for the YouTube Transcript Analyzer

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$PROJECT_DIR/service"
SUPERVISOR_CONF="$SERVICE_DIR/supervisord.conf"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Check if Supervisord is already running
if [ -f "$SERVICE_DIR/supervisord.pid" ]; then
    PID=$(cat "$SERVICE_DIR/supervisord.pid")
    if ps -p $PID > /dev/null; then
        echo "Supervisord is already running with PID $PID"
        echo "To restart, run: ./service/stop.sh && ./service/start.sh"
        exit 0
    else
        echo "Removing stale PID file"
        rm "$SERVICE_DIR/supervisord.pid"
    fi
fi

# Start Supervisord with PROJECT_DIR environment variable
echo "Starting Supervisord..."
export PROJECT_DIR
cd "$SERVICE_DIR"
supervisord -c "$SUPERVISOR_CONF"

# Check if Supervisord started successfully
if [ $? -eq 0 ]; then
    echo "Supervisord started successfully"
    echo "The YouTube Transcript Analyzer is now running in the background"
    echo "You can access it at http://localhost:5002"
    echo ""
    echo "To check the status: ./service/status.sh"
    echo "To stop the service: ./service/stop.sh"
    echo "To view logs: tail -f $PROJECT_DIR/logs/app.log"
else
    echo "Failed to start Supervisord"
    exit 1
fi 