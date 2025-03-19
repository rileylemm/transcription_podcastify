"""
Migration script to update file naming convention for better RAG database integration.
"""

import os
import json
from datetime import datetime
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def sanitize_filename(name):
    """Convert a string to a safe filename."""
    safe_name = "".join(c if c.isalnum() else '_' for c in name)
    safe_name = '_'.join(filter(None, safe_name.split('_')))
    return safe_name.lower()

def get_timestamp_prefix():
    """Get current timestamp in YYYYMMDD_HHMMSS format."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def generate_transcript_filename(video_title):
    """Generate consistent filename for transcripts."""
    safe_title = sanitize_filename(video_title)
    return f"{get_timestamp_prefix()}__transcript__{safe_title}.json"

def generate_analysis_filename(video_title, analysis_type, model):
    """Generate consistent filename for analyses."""
    safe_title = sanitize_filename(video_title)
    safe_type = sanitize_filename(analysis_type)
    safe_model = sanitize_filename(model)
    return f"{get_timestamp_prefix()}__analysis__{safe_type}__{safe_model}__{safe_title}.json"

def generate_chat_filename(video_title):
    """Generate consistent filename for chat history."""
    safe_title = sanitize_filename(video_title)
    return f"{get_timestamp_prefix()}__chat__{safe_title}.json"

def migrate_files(data_dir):
    """Migrate existing files to new naming convention."""
    logger.info("Starting file migration...")
    
    # Create backup directory
    backup_dir = os.path.join(os.path.dirname(data_dir), 'data_backup')
    backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'backup_{backup_timestamp}')
    
    logger.info(f"Creating backup at: {backup_path}")
    shutil.copytree(data_dir, backup_path)
    
    # Process each video directory
    for video_dir_name in os.listdir(data_dir):
        video_dir = os.path.join(data_dir, video_dir_name)
        if not os.path.isdir(video_dir):
            continue
            
        logger.info(f"Processing directory: {video_dir_name}")
        
        # Process files in the video directory
        for filename in os.listdir(video_dir):
            old_path = os.path.join(video_dir, filename)
            if not os.path.isfile(old_path):
                continue
                
            try:
                # Handle transcript files
                if filename.endswith('_transcript_original.json'):
                    with open(old_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    new_filename = generate_transcript_filename(video_dir_name)
                    new_path = os.path.join(video_dir, new_filename)
                    with open(new_path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    os.remove(old_path)
                    logger.info(f"Migrated transcript: {filename} -> {new_filename}")
                
                # Handle analysis files
                elif '_analysis_' in filename and filename.endswith('.json'):
                    with open(old_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    analysis_type = content.get('type', 'technical_summary')
                    model = content.get('model', 'mistral')
                    new_filename = generate_analysis_filename(video_dir_name, analysis_type, model)
                    new_path = os.path.join(video_dir, new_filename)
                    with open(new_path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    os.remove(old_path)
                    logger.info(f"Migrated analysis: {filename} -> {new_filename}")
                
                # Handle chat history files
                elif filename.endswith('_chat_history.json'):
                    with open(old_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    new_filename = generate_chat_filename(video_dir_name)
                    new_path = os.path.join(video_dir, new_filename)
                    with open(new_path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    os.remove(old_path)
                    logger.info(f"Migrated chat history: {filename} -> {new_filename}")
                    
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                continue
    
    logger.info("Migration completed successfully!")
    logger.info(f"Backup created at: {backup_path}")

if __name__ == '__main__':
    # Get the absolute path to the data directory
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(current_dir, 'data')
    
    # Run migration
    migrate_files(data_dir) 