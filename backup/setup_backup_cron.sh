#!/bin/bash

# Script to set up weekly backup cron job for ChromaDB vector store

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_SCRIPT="$PROJECT_DIR/backup/backup_vector_store.py"

# Check if backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "Error: Backup script not found at $BACKUP_SCRIPT"
    exit 1
fi

# Create a temporary file for the crontab
TEMP_CRON=$(mktemp)

# Export current crontab
crontab -l > "$TEMP_CRON" 2>/dev/null || echo "" > "$TEMP_CRON"

# Check if the backup job already exists
if grep -q "backup_vector_store.py" "$TEMP_CRON"; then
    echo "Backup cron job already exists. Updating..."
    # Remove existing backup job
    grep -v "backup_vector_store.py" "$TEMP_CRON" > "${TEMP_CRON}.new"
    mv "${TEMP_CRON}.new" "$TEMP_CRON"
fi

# Add the backup job to run every Sunday at midnight
echo "0 0 * * 0 cd $PROJECT_DIR && python backup/backup_vector_store.py --api-export" >> "$TEMP_CRON"

# Install the new crontab
crontab "$TEMP_CRON"

# Clean up
rm "$TEMP_CRON"

echo "Weekly backup cron job has been set up successfully."
echo "Backups will run every Sunday at midnight."
echo "Backup location: /Volumes/RileyNumber1/youtube_transcription/chroma_db_backup" 