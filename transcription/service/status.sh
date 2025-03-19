#!/bin/bash

# Script to check the status of Supervisord for the YouTube Transcript Analyzer

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$PROJECT_DIR/service"
SUPERVISOR_CONF="$SERVICE_DIR/supervisord.conf"

# Check if Supervisord is running
if [ ! -f "$SERVICE_DIR/supervisord.pid" ]; then
    echo "Supervisord is not running"
    exit 1
fi

PID=$(cat "$SERVICE_DIR/supervisord.pid")
if ! ps -p $PID > /dev/null; then
    echo "Supervisord is not running (stale PID file)"
    rm "$SERVICE_DIR/supervisord.pid"
    exit 1
fi

# Check the status of the processes
echo "Supervisord is running with PID $PID"
echo ""
echo "Process status:"
supervisorctl -c "$SUPERVISOR_CONF" status

# Check if the application is accessible
echo ""
echo "Checking if the application is accessible..."
if curl -s -I http://localhost:5002 > /dev/null; then
    echo "The application is accessible at http://localhost:5002"
else
    echo "The application is NOT accessible at http://localhost:5002"
fi 