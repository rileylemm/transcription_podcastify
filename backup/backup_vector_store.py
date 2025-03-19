#!/usr/bin/env python3
"""
ChromaDB Vector Store Backup Utility

This script provides backup functionality for the ChromaDB vector store used in the
YouTube Transcript Analyzer. It implements two backup strategies:
1. Filesystem backup - Copies the entire ChromaDB directory
2. API export - Exports collections via ChromaDB's API (requires chromadb-data-pipes)
"""

import os
import shutil
import logging
import argparse
from datetime import datetime
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_backup_directory(base_backup_dir):
    """Create a timestamped backup directory."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(base_backup_dir, f"chroma_backup_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def filesystem_backup(source_dir, backup_dir):
    """Perform a filesystem backup of the ChromaDB directory."""
    try:
        logger.info(f"Starting filesystem backup from {source_dir} to {backup_dir}")
        
        # Ensure source directory exists
        if not os.path.exists(source_dir):
            logger.error(f"Source directory {source_dir} does not exist")
            return False
            
        # Copy the entire directory
        shutil.copytree(source_dir, os.path.join(backup_dir, "chroma_db"))
        
        logger.info(f"Filesystem backup completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during filesystem backup: {str(e)}")
        return False

def api_export_backup(source_dir, backup_dir):
    """Perform an API export backup using chromadb-data-pipes."""
    try:
        logger.info(f"Starting API export backup from {source_dir} to {backup_dir}")
        
        # Check if chromadb-data-pipes is installed
        try:
            subprocess.run(["pip", "show", "chromadb-data-pipes"], 
                          check=True, capture_output=True)
        except subprocess.CalledProcessError:
            logger.error("chromadb-data-pipes is not installed. Install with: pip install chromadb-data-pipes")
            return False
            
        # Export each collection
        export_dir = os.path.join(backup_dir, "chroma_export")
        os.makedirs(export_dir, exist_ok=True)
        
        # Run the export command
        cmd = [
            "python", "-m", "chromadb_data_pipes", 
            "export", "--source", f"chroma://{source_dir}", 
            "--destination", f"file://{export_dir}", 
            "--format", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"API export failed: {result.stderr}")
            return False
            
        logger.info(f"API export completed successfully to {export_dir}")
        return True
    except Exception as e:
        logger.error(f"Error during API export: {str(e)}")
        return False

def rotate_backups(backup_dir, max_backups=5):
    """Remove old backups, keeping only the specified number."""
    try:
        logger.info(f"Rotating backups, keeping {max_backups} most recent")
        
        # List all backup directories
        backup_pattern = "chroma_backup_"
        backups = [d for d in os.listdir(backup_dir) 
                  if os.path.isdir(os.path.join(backup_dir, d)) and d.startswith(backup_pattern)]
        
        # Sort by creation time (newest first)
        backups.sort(reverse=True)
        
        # Remove older backups
        if len(backups) > max_backups:
            for old_backup in backups[max_backups:]:
                old_backup_path = os.path.join(backup_dir, old_backup)
                logger.info(f"Removing old backup: {old_backup_path}")
                shutil.rmtree(old_backup_path)
                
        logger.info(f"Backup rotation completed, kept {min(len(backups), max_backups)} backups")
        return True
    except Exception as e:
        logger.error(f"Error during backup rotation: {str(e)}")
        return False

def main():
    """Main function to run the backup process."""
    parser = argparse.ArgumentParser(description="ChromaDB Vector Store Backup Utility")
    parser.add_argument("--source", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db"), 
                        help="Source ChromaDB directory (default: chroma_db in project root)")
    parser.add_argument("--backup-dir", default="/Volumes/RileyNumber1/youtube_transcription/chroma_db_backup", 
                        help="Base directory for backups (default: /Volumes/RileyNumber1/youtube_transcription/chroma_db_backup)")
    parser.add_argument("--max-backups", type=int, default=5, 
                        help="Maximum number of backups to keep (default: 5)")
    parser.add_argument("--api-export", action="store_true", 
                        help="Perform API export in addition to filesystem backup")
    
    args = parser.parse_args()
    
    # Create base backup directory if it doesn't exist
    os.makedirs(args.backup_dir, exist_ok=True)
    
    # Create timestamped backup directory
    backup_dir = create_backup_directory(args.backup_dir)
    logger.info(f"Created backup directory: {backup_dir}")
    
    # Perform filesystem backup
    fs_success = filesystem_backup(args.source, backup_dir)
    
    # Perform API export if requested
    api_success = True
    if args.api_export:
        api_success = api_export_backup(args.source, backup_dir)
    
    # Rotate old backups
    rotate_backups(args.backup_dir, args.max_backups)
    
    if fs_success and api_success:
        logger.info("Backup completed successfully")
        return 0
    else:
        logger.error("Backup completed with errors")
        return 1

if __name__ == "__main__":
    exit(main()) 