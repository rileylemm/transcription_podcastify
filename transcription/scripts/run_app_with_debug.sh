#!/bin/bash

# Debug script to run the Flask app with additional logging
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
APP_SCRIPT="$PROJECT_DIR/app.py"

echo "Starting YouTube Transcript Analyzer at $(date)" > "$PROJECT_DIR/logs/startup.log"
echo "Python interpreter: $PYTHON_PATH" >> "$PROJECT_DIR/logs/startup.log"
echo "Working directory: $(pwd)" >> "$PROJECT_DIR/logs/startup.log"
echo "Environment variables:" >> "$PROJECT_DIR/logs/startup.log"
env >> "$PROJECT_DIR/logs/startup.log"

# Check if Flask is available
if ! "$PYTHON_PATH" -c "import flask" 2>/dev/null; then
    echo "Error: Flask is not available in the Python environment" >> "$PROJECT_DIR/logs/startup.log"
    exit 1
fi

# Run the Flask app directly
cd "$PROJECT_DIR"

echo "Starting Flask with: $PYTHON_PATH $APP_SCRIPT" >> "$PROJECT_DIR/logs/startup.log"
exec "$PYTHON_PATH" "$APP_SCRIPT"
