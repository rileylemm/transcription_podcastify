#!/bin/bash

# Script to set up the YouTube Transcript Analyzer as a background service

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_SCRIPT="$PROJECT_DIR/app.py"

# Check if app.py exists
if [ ! -f "$APP_SCRIPT" ]; then
    echo "Error: app.py not found at $APP_SCRIPT"
    exit 1
fi

# Find the Python interpreter in the virtual environment
if [ -f "$PROJECT_DIR/venv/bin/python" ]; then
    PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
elif [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
else
    echo "Warning: Virtual environment not found. Using system Python."
    PYTHON_PATH=$(which python)
fi

echo "Using Python interpreter: $PYTHON_PATH"

# Verify that the Python interpreter exists and is executable
if [ ! -x "$PYTHON_PATH" ]; then
    echo "Error: Python interpreter not found or not executable: $PYTHON_PATH"
    exit 1
fi

# Verify that Flask is installed in the Python environment
if ! "$PYTHON_PATH" -c "import flask; print('Flask is installed')" > /dev/null 2>&1; then
    echo "Error: Flask is not installed in the Python environment: $PYTHON_PATH"
    echo "Please install Flask: $PYTHON_PATH -m pip install flask"
    exit 1
fi

echo "Flask is installed in the Python environment"

# Check if port 5002 is already in use
if lsof -i:5002 > /dev/null 2>&1; then
    echo "Warning: Port 5002 is already in use. The service may not start correctly."
    echo "You can check what's using the port with: lsof -i:5002"
    echo "You may need to stop the existing process before proceeding."
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup aborted."
        exit 1
    fi
fi

# Create the LaunchAgents directory if it doesn't exist
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS_DIR"

# Create the plist file
PLIST_FILE="$LAUNCH_AGENTS_DIR/com.user.youtubetranscriptanalyzer.plist"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Create a debug script that will be called by launchd
DEBUG_SCRIPT="$PROJECT_DIR/scripts/run_app_with_debug.sh"
cat > "$DEBUG_SCRIPT" << EOL
#!/bin/bash

# Debug script to run the Flask app with additional logging
echo "Starting YouTube Transcript Analyzer at \$(date)" > "$PROJECT_DIR/logs/startup.log"
echo "Python interpreter: $PYTHON_PATH" >> "$PROJECT_DIR/logs/startup.log"
echo "Working directory: \$(pwd)" >> "$PROJECT_DIR/logs/startup.log"
echo "Environment variables:" >> "$PROJECT_DIR/logs/startup.log"
env >> "$PROJECT_DIR/logs/startup.log"

# Check if Flask is available
if ! "$PYTHON_PATH" -c "import flask" 2>/dev/null; then
    echo "Error: Flask is not available in the Python environment" >> "$PROJECT_DIR/logs/startup.log"
    exit 1
fi

# Run the Flask app
cd "$PROJECT_DIR"
exec "$PYTHON_PATH" "$APP_SCRIPT"
EOL

# Make the debug script executable
chmod +x "$DEBUG_SCRIPT"

# Check if .env file exists and load it
ENV_VARS=""
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "Loading environment variables from .env file"
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Skip comments and empty lines
        [[ $key == \#* ]] && continue
        [[ -z "$key" ]] && continue
        
        # Remove quotes from value if present
        value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
        
        # Add to environment variables
        ENV_VARS="$ENV_VARS
        <key>$key</key>
        <string>$value</string>"
    done < "$PROJECT_DIR/.env"
fi

cat > "$PLIST_FILE" << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.youtubetranscriptanalyzer</string>
    <key>ProgramArguments</key>
    <array>
        <string>${DEBUG_SCRIPT}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/logs/app.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/logs/app_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH}</string>
        <key>PYTHONPATH</key>
        <string>${PROJECT_DIR}</string>$ENV_VARS
    </dict>
</dict>
</plist>
EOL

# Unload the service if it's already loaded
launchctl unload "$PLIST_FILE" 2>/dev/null

# Load the service
launchctl load "$PLIST_FILE"

echo "YouTube Transcript Analyzer service has been set up successfully."
echo "The application will now run automatically in the background."
echo "Log files are located at:"
echo "  - Standard output: $PROJECT_DIR/logs/app.log"
echo "  - Standard error: $PROJECT_DIR/logs/app_error.log"
echo "  - Startup log: $PROJECT_DIR/logs/startup.log"
echo ""
echo "To stop the service: launchctl unload $PLIST_FILE"
echo "To start the service: launchctl load $PLIST_FILE"
echo "To check if the service is running: launchctl list | grep youtubetranscriptanalyzer" 