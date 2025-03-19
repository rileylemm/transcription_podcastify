import os
import json
import logging
import hashlib
import shutil
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
# from scripts.vector_store import VectorStore  # Old import
# from vector_db.vector_store import VectorStore  # New import from same directory
from .vector_store import VectorStore  # Relative import

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migrate_to_vector_store.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = "shared/data"
CHECKPOINT_DIR = "checkpoints"
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

class MigrationError(Exception):
    """Base exception for migration errors."""
    pass

class DataValidationError(MigrationError):
    """Exception raised for data validation errors."""
    pass

class CheckpointError(MigrationError):
    """Exception raised for checkpoint errors."""
    pass

def calculate_checksum(data: Dict) -> str:
    """Calculate a checksum for the data to detect changes."""
    data_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(data_str.encode()).hexdigest()

def save_checkpoint(checkpoint_data: Dict, video_id: str) -> None:
    """Save checkpoint data for a video."""
    try:
        checkpoint_file = os.path.join(CHECKPOINT_DIR, f"{video_id}.json")
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)
        logger.debug(f"Saved checkpoint for {video_id}")
    except Exception as e:
        logger.error(f"Error saving checkpoint for {video_id}: {str(e)}")
        raise CheckpointError(f"Failed to save checkpoint: {str(e)}")

def load_checkpoint(video_id: str) -> Optional[Dict]:
    """Load checkpoint data for a video if it exists."""
    try:
        checkpoint_file = os.path.join(CHECKPOINT_DIR, f"{video_id}.json")
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error loading checkpoint for {video_id}: {str(e)}")
        return None

def clean_text_data(text: str) -> str:
    """Clean and normalize text data."""
    if not text:
        return ""
    
    # Replace multiple spaces with a single space
    text = " ".join(text.split())
    
    # Remove any non-printable characters
    text = "".join(c for c in text if c.isprintable() or c in ["\n", "\t"])
    
    return text.strip()

def validate_transcript_segment(segment: Dict) -> bool:
    """Validate transcript segment has required fields and valid data."""
    try:
        # Check required fields
        required_fields = {'text', 'start', 'duration'}
        if not all(field in segment for field in required_fields):
            return False
        
        # Validate data types and ranges
        if not isinstance(segment['text'], str) or not segment['text'].strip():
            return False
        if not isinstance(segment['start'], (int, float)) or segment['start'] < 0:
            return False
        if not isinstance(segment['duration'], (int, float)) or segment['duration'] <= 0:
            return False
        
        # Clean text data
        segment['text'] = clean_text_data(segment['text'])
        return bool(segment['text'])
    
    except Exception:
        return False

def validate_analysis_content(analysis: Dict) -> bool:
    """Validate analysis content has required fields and valid data."""
    try:
        # Check required fields
        required_fields = {'content', 'model', 'timestamp'}
        if not all(field in analysis for field in required_fields):
            return False
        
        # Validate data types
        if not isinstance(analysis['content'], str) or not analysis['content'].strip():
            return False
        if not isinstance(analysis['model'], str) or not analysis['model'].strip():
            return False
        if not isinstance(analysis['timestamp'], (int, float)):
            return False
        
        # Clean content
        analysis['content'] = clean_text_data(analysis['content'])
        return bool(analysis['content'])
    
    except Exception:
        return False

def verify_migration(vector_store, video_id: str, expected_segments: int) -> bool:
    """Verify that a video's transcript was migrated correctly."""
    try:
        logger.info(f"Verifying migration for {video_id} (expected {expected_segments} segments)")
        
        # Track segment indices
        segment_indices = {}
        all_segments = []
        
        # First try to get all segments at once
        try:
            results = vector_store.collection.query(
                query_texts=[""],
                where={"video_id": video_id},
                n_results=expected_segments
            )
            
            if not results['ids'][0]:
                logger.error(f"No segments found for {video_id}")
                return False
            
            # Process all segments
            for i, metadata in enumerate(results['metadatas'][0]):
                # Check required fields
                required_fields = {'video_id', 'start', 'duration', 'content_type', 'segment_index', 'total_segments'}
                if not all(field in metadata for field in required_fields):
                    missing_fields = required_fields - set(metadata.keys())
                    logger.error(f"Missing required fields in segment metadata for {video_id}: {missing_fields}")
                    return False
                
                # Get the segment index from metadata
                idx = metadata['segment_index']
                
                # Track segment indices
                if idx in segment_indices:
                    # This is a true duplicate - same segment index appears multiple times
                    logger.error(f"Duplicate segment index {idx} for {video_id}")
                    return False
                
                segment_indices[idx] = i
                all_segments.append(metadata)
            
        except Exception as e:
            logger.error(f"Error retrieving segments for {video_id}: {str(e)}")
            return False
        
        # Check total segment count
        if len(all_segments) != expected_segments:
            logger.error(f"Segment count mismatch for {video_id}. Expected: {expected_segments}, Got: {len(all_segments)}")
            return False
        
        # Verify all indices are present and in valid range
        for idx in range(expected_segments):
            if idx not in segment_indices:
                logger.error(f"Missing segment index {idx} for {video_id}")
                return False
            
            if idx < 0 or idx >= expected_segments:
                logger.error(f"Invalid segment index {idx} for {video_id} (should be between 0 and {expected_segments-1})")
                return False
        
        logger.info(f"Migration verification successful for {video_id}: all {expected_segments} segments present")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying migration for {video_id}: {str(e)}")
        return False

def find_latest_file(directory: str, pattern: str) -> Optional[str]:
    """Find the latest file matching the pattern in the directory."""
    try:
        matching_files = [
            os.path.join(directory, f) for f in os.listdir(directory)
            if f.startswith(pattern) and os.path.isfile(os.path.join(directory, f))
        ]
        
        if not matching_files:
            return None
        
        # Return the most recently modified file
        return max(matching_files, key=os.path.getmtime)
    
    except Exception as e:
        logger.error(f"Error finding latest file in {directory} with pattern {pattern}: {str(e)}")
        return None

def load_json_file(filepath: str) -> Optional[Dict]:
    """Load and parse a JSON file."""
    try:
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    except Exception as e:
        logger.error(f"Error loading JSON file {filepath}: {str(e)}")
        return None

def get_video_data(video_dir: str) -> Tuple[Optional[List], Optional[Dict], Dict[str, List]]:
    """Get transcript, metadata, and analysis data for a video."""
    try:
        # Check if directory exists
        if not os.path.exists(video_dir) or not os.path.isdir(video_dir):
            logger.warning(f"Video directory not found: {video_dir}")
            return None, None, {}
        
        # Load transcript
        transcript_files = [f for f in os.listdir(video_dir) if "__transcript__" in f]
        if not transcript_files:
            logger.warning(f"No transcript file found in {video_dir}")
            return None, None, {}
        
        # Get the latest transcript file
        transcript_file = os.path.join(video_dir, max(transcript_files))  # max will get the latest by timestamp
        transcript = load_json_file(transcript_file)
        
        # Load metadata
        metadata_files = [f for f in os.listdir(video_dir) if "__metadata__" in f]
        metadata = None
        if metadata_files:
            metadata_file = os.path.join(video_dir, max(metadata_files))
            metadata = load_json_file(metadata_file)
        
        # Load analysis files
        analysis_data = {}
        
        # Look for analysis files with the pattern: __analysis__type__model__
        analysis_files = [f for f in os.listdir(video_dir) if "__analysis__" in f]
        
        for analysis_file in analysis_files:
            # Extract analysis type and model from filename
            parts = analysis_file.split("__")
            if len(parts) >= 4:
                analysis_type = parts[2]  # e.g., "full_context"
                model = parts[3]  # e.g., "gpt"
                
                analysis = load_json_file(os.path.join(video_dir, analysis_file))
                
                if analysis and validate_analysis_content(analysis):
                    key = f"{analysis_type}_{model}"
                    
                    if key not in analysis_data:
                        analysis_data[key] = []
                    
                    # Create a segment-like structure for the analysis
                    analysis_segment = {
                        "text": analysis["content"],
                        "start": 0,  # Analysis doesn't have a specific timestamp
                        "duration": 0,  # Analysis doesn't have a duration
                        "model": model,
                        "timestamp": analysis.get("timestamp", 0),
                        "analysis_type": analysis_type
                    }
                    
                    analysis_data[key].append(analysis_segment)
        
        return transcript, metadata, analysis_data
    
    except Exception as e:
        logger.error(f"Error getting video data from {video_dir}: {str(e)}")
        return None, None, {}

def migrate_data():
    """Migrate transcript and analysis data to the vector store."""
    try:
        # Initialize vector store
        vector_store = VectorStore()
        
        # Clear existing data
        logger.info("Clearing existing vector store data...")
        vector_store.clear()
        
        # Get all video directories
        videos = {}
        transcripts_dir = os.path.join(DATA_DIR, "transcripts")
        
        # Walk through all subdirectories
        for root, dirs, files in os.walk(transcripts_dir):
            # Look for transcript files in this directory
            transcript_files = [f for f in files if "__transcript__" in f]
            if transcript_files:
                # Use the directory name as the video_id
                video_id = os.path.basename(root)
                videos[video_id] = root
        
        # Process each video
        total_videos = len(videos)
        processed_videos = 0
        successful_videos = 0
        error_videos = 0
        skipped_videos = 0
        
        for video_id, video_dir in videos.items():
            logger.info(f"\nProcessing video: {video_id}")
            
            try:
                # Check for checkpoint
                checkpoint = load_checkpoint(video_id)
                if checkpoint:
                    logger.info(f"Resuming from checkpoint for {video_id}")
                
                # Get video data
                transcript, metadata, analysis_data = get_video_data(video_dir)
                
                # Skip if no transcript
                if not transcript:
                    logger.warning(f"No transcript found for {video_id}")
                    skipped_videos += 1
                    continue
                
                # Validate transcript segments
                valid_segments = []
                if isinstance(transcript, list):
                    for segment in transcript:
                        if validate_transcript_segment(segment):
                            valid_segments.append(segment)
                else:
                    logger.warning(f"Transcript for {video_id} is not a list: {type(transcript)}")
                
                # Skip if no valid segments
                if not valid_segments:
                    logger.warning(f"No valid segments found for {video_id}")
                    skipped_videos += 1
                    continue
                
                # Add transcript to vector store
                vector_store.add_transcript(video_id, valid_segments)
                logger.info(f"Added all {len(valid_segments)} segments for {video_id}")
                
                # Verify migration
                if verify_migration(vector_store, video_id, len(valid_segments)):
                    logger.info(f"Migration successful for {video_id}")
                    successful_videos += 1
                else:
                    logger.error(f"Migration verification failed for {video_id}")
                    error_videos += 1
                
                # Add analysis data
                for analysis_key, analysis_segments in analysis_data.items():
                    if analysis_segments:
                        analysis_type, model = analysis_key.split("_", 1)
                        analysis_video_id = f"{video_id}_{analysis_key}"
                        
                        # Add analysis to vector store
                        vector_store.add_transcript(analysis_video_id, analysis_segments)
                        logger.info(f"Added {analysis_type} analysis ({model}) for {video_id}")
                
                # Save checkpoint
                checkpoint_data = {
                    "video_id": video_id,
                    "timestamp": metadata.get("timestamp") if metadata else None,
                    "segment_count": len(valid_segments),
                    "checksum": calculate_checksum(valid_segments)
                }
                save_checkpoint(checkpoint_data, video_id)
                
            except Exception as e:
                logger.error(f"Error processing video {video_id}: {str(e)}")
                error_videos += 1
            
            processed_videos += 1
        
        # Print summary
        logger.info("\nMigration Summary:")
        logger.info(f"Total videos processed: {total_videos}")
        logger.info(f"Successfully processed: {successful_videos}")
        logger.info(f"Errors encountered: {error_videos}")
        logger.info(f"Videos skipped: {skipped_videos}")
        logger.info(f"Verification failed: {total_videos - successful_videos - error_videos - skipped_videos}")
        
        if error_videos > 0 or (total_videos - successful_videos - error_videos - skipped_videos) > 0:
            logger.warning("Some errors occurred during migration. Check the log file for details.")
    
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")

if __name__ == "__main__":
    migrate_data() 