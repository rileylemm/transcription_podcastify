#!/bin/bash

# Script to manage the YouTube Transcript Analyzer service

# Service identifier
SERVICE_NAME="com.user.youtubetranscriptanalyzer"
PLIST_FILE="$HOME/Library/LaunchAgents/$SERVICE_NAME.plist"

# Check if the plist file exists
if [ ! -f "$PLIST_FILE" ]; then
    echo "Error: Service is not installed. Run setup_service.sh first."
    exit 1
fi

# Function to check if the service is running
check_status() {
    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo "Service is running."
        return 0
    else
        echo "Service is not running."
        return 1
    fi
}

# Function to start the service
start_service() {
    echo "Starting YouTube Transcript Analyzer service..."
    launchctl load "$PLIST_FILE"
    sleep 2
    check_status
}

# Function to stop the service
stop_service() {
    echo "Stopping YouTube Transcript Analyzer service..."
    launchctl unload "$PLIST_FILE"
    sleep 2
    check_status
}

# Function to restart the service
restart_service() {
    echo "Restarting YouTube Transcript Analyzer service..."
    stop_service
    sleep 2
    start_service
}

# Function to show logs
show_logs() {
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    LOG_FILE="$PROJECT_DIR/logs/app.log"
    ERROR_LOG="$PROJECT_DIR/logs/app_error.log"
    
    if [ ! -f "$LOG_FILE" ]; then
        echo "Log file not found: $LOG_FILE"
    else
        echo "=== Last 20 lines of application log ==="
        tail -n 20 "$LOG_FILE"
        echo ""
    fi
    
    if [ ! -f "$ERROR_LOG" ]; then
        echo "Error log file not found: $ERROR_LOG"
    else
        echo "=== Last 20 lines of error log ==="
        tail -n 20 "$ERROR_LOG"
    fi
}

# Main script logic
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac

exit 0 