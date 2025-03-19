from flask import Flask, request, jsonify, render_template
from scripts.youtube_transcript import (
    get_transcript, get_video_title, save_video_metadata
)
from scripts.transcript_analyzer import TranscriptAnalyzer
from scripts.reddit_analyzer import RedditAnalyzer
from reddit_scraper.reddit_extractor import RedditExtractor
# from scripts.vector_store import VectorStore  # Old import
from vector_db.vector_store import VectorStore  # New import from dedicated directory
from dotenv import load_dotenv
import os
import asyncio
import logging
import json
from datetime import datetime
import aiofiles
import urllib.parse
from typing import Optional, Dict
from werkzeug.utils import secure_filename
import shutil
from functools import lru_cache
from diskcache import Cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/app/data'
app.config['CHROMA_DATA_DIR'] = '/app/data/chroma'
app.config['CACHE_DIR'] = '/app/data/cache'

# Create required directories
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts'), exist_ok=True)
os.makedirs(app.config['CHROMA_DATA_DIR'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'reddit'), exist_ok=True)

# Initialize analyzers
openai_api_key = os.getenv('OPENAI_API_KEY')
analyzer = TranscriptAnalyzer(openai_api_key=openai_api_key, data_dir=os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts'))
reddit_analyzer = RedditAnalyzer(openai_api_key=openai_api_key, data_dir=app.config['UPLOAD_FOLDER'])
reddit_extractor = RedditExtractor()

# Initialize vector store
vector_store = VectorStore(persist_directory=app.config['CHROMA_DATA_DIR'])

# Initialize cache
cache = Cache('./cache')
POSTS_PER_PAGE = 20  # Number of posts to show per page

# Create a function to maintain the post index
def update_post_index():
    """Update the post index file with metadata from all posts."""
    reddit_base_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'reddit')
    os.makedirs(reddit_base_dir, exist_ok=True)
    
    post_index = {}
    for dirname in os.listdir(reddit_base_dir):
        if dirname == 'post_index.json':  # Skip the index file itself
            continue
            
        post_dir = os.path.join(reddit_base_dir, dirname)
        if not os.path.isdir(post_dir):
            continue
            
        post_id = dirname.split('__')[-1]
        post_files = [f for f in os.listdir(post_dir) if f.endswith('.json') and '__post__' in f]
        
        if post_files:
            latest_post_file = max(post_files, key=lambda f: os.path.getmtime(os.path.join(post_dir, f)))
            post_filepath = os.path.join(post_dir, latest_post_file)
            
            try:
                with open(post_filepath, 'r', encoding='utf-8') as f:
                    post_data = json.load(f)
                    post_index[post_id] = {
                        'dir_name': dirname,
                        'metadata': {
                            'title': post_data['title'],
                            'author': post_data['author'],
                            'subreddit': post_data['subreddit'],
                            'created_utc': post_data['created_utc'],
                            'score': post_data['score'],
                            'num_comments': post_data['num_comments'],
                            'post_id': post_id
                        },
                        'latest_post_file': latest_post_file
                    }
            except Exception as e:
                logger.error(f"Error processing post file {latest_post_file}: {str(e)}")
                continue
    
    # Save the index
    index_path = os.path.join(reddit_base_dir, 'post_index.json')
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(post_index, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully updated post index with {len(post_index)} posts")
    except Exception as e:
        logger.error(f"Error saving post index: {str(e)}")
    
    return post_index

@lru_cache(maxsize=100)
def get_post_data(post_id):
    """Get post data with caching."""
    reddit_base_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'reddit')
    index_path = os.path.join(reddit_base_dir, 'post_index.json')
    
    try:
        # Update index if it doesn't exist
        if not os.path.exists(index_path):
            post_index = update_post_index()
        else:
            # Load the index
            with open(index_path, 'r', encoding='utf-8') as f:
                post_index = json.load(f)
            
        if post_id not in post_index:
            # Try updating the index in case the post was just added
            post_index = update_post_index()
            if post_id not in post_index:
                logger.error(f"Post {post_id} not found in index")
                return None
            
        post_info = post_index[post_id]
        post_dir = os.path.join(reddit_base_dir, post_info['dir_name'])
        post_filepath = os.path.join(post_dir, post_info['latest_post_file'])
        
        with open(post_filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Error getting post data: {str(e)}")
        return None

@lru_cache(maxsize=100)
def get_post_analyses(post_id):
    """Get post analyses with caching."""
    reddit_base_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'reddit')
    index_path = os.path.join(reddit_base_dir, 'post_index.json')
    
    try:
        # Load the index
        with open(index_path, 'r', encoding='utf-8') as f:
            post_index = json.load(f)
            
        if post_id not in post_index:
            return None
            
        post_info = post_index[post_id]
        post_dir = os.path.join(reddit_base_dir, post_info['dir_name'])
        
        analyses = {}
        
        for filename in os.listdir(post_dir):
            if '__analysis__' in filename and filename.endswith('.json'):
                try:
                    filepath = os.path.join(post_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                        
                    metadata = analysis_data.get('metadata', {})
                    # Check both root level and metadata for analysis type
                    analysis_type = analysis_data.get('type') or metadata.get('analysis_type')
                    model = analysis_data.get('model') or metadata.get('model', 'mistral')
                    
                    if analysis_type:
                        if analysis_type not in analyses:
                            analyses[analysis_type] = {'mistral': [], 'gpt': []}
                        
                        if model in analyses[analysis_type]:
                            analyses[analysis_type][model].append({
                                'content': str(analysis_data.get('content', '')),
                                'metadata': metadata,
                                'timestamp': os.path.getmtime(filepath)
                            })
                        
                except Exception as e:
                    logger.error(f"Error reading analysis file {filename}: {str(e)}")
                    continue
                    
        # Sort analyses by timestamp
        for analysis_type in analyses:
            for model in analyses[analysis_type]:
                analyses[analysis_type][model].sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                
        return analyses
        
    except Exception as e:
        logger.error(f"Error getting post analyses: {str(e)}")
        return None

def sanitize_filename(name):
    """Convert a string to a safe filename."""
    # Replace spaces and special chars with underscores
    safe_name = "".join(c if c.isalnum() else '_' for c in name)
    # Remove consecutive underscores
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

def find_latest_file(directory: str, pattern: str) -> Optional[str]:
    """Find the most recent file matching a pattern in a directory."""
    try:
        matching_files = [f for f in os.listdir(directory) if pattern in f]
        if not matching_files:
            return None
        latest_file = max(matching_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
        return os.path.join(directory, latest_file)
    except Exception as e:
        logger.error(f"Error finding latest file: {str(e)}")
        return None

def load_json_file(filepath: str) -> Optional[Dict]:
    """Load and parse a JSON file."""
    try:
        if not filepath or not os.path.exists(filepath):
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file: {str(e)}")
        return None

async def load_chat_history(video_title):
    """Load chat history for a specific video."""
    try:
        # Get sanitized video directory
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        
        if not os.path.exists(video_dir):
            return {"video_id": video_title, "messages": []}
        
        # Find the most recent chat history file
        chat_filename = find_latest_file(video_dir, '__chat__')
        
        if chat_filename:
            try:
                async with aiofiles.open(chat_filename, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    history = json.loads(content)
                    return history
            except Exception as e:
                logger.error(f"Error reading chat history file: {str(e)}", exc_info=True)
                return {"video_id": video_title, "messages": []}
        
        return {"video_id": video_title, "messages": []}
        
    except Exception as e:
        logger.error(f"Error loading chat history: {str(e)}", exc_info=True)
        return {"video_id": video_title, "messages": []}

async def save_chat_history(video_title, user_message, assistant_response):
    """Save chat history for a specific video."""
    try:
        # Get sanitized video directory
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        os.makedirs(video_dir, exist_ok=True)
        
        chat_filename = generate_chat_filename(video_title)
        chat_file = os.path.join(video_dir, chat_filename)
        
        # Load existing history
        history = await load_chat_history(video_title)
        
        # Add new messages
        timestamp = datetime.now().isoformat()
        history["messages"].extend([
            {
                "role": "user",
                "content": user_message,
                "timestamp": timestamp
            },
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": timestamp
            }
        ])
        
        # Save updated history
        async with aiofiles.open(chat_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(history, indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"Error saving chat history: {str(e)}", exc_info=True)

async def get_video_context(video_title):
    """Get combined context from transcript and analyses."""
    try:
        # Get sanitized video directory
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        context = []
        
        # Add a focused system message
        context.append(
            "You are an expert AI assistant specializing in LLM technology and implementation. "
            "Your role is to help users understand and work with LLMs effectively. "
            "Focus on providing accurate, technical, and practical information about LLM concepts, "
            "implementation details, and best practices. "
            "If a question is not related to LLMs or AI, politely redirect the conversation to these topics."
        )
        
        # Get most recent technical summary first
        analysis_files = [f for f in os.listdir(video_dir) if '__analysis__technical_summary__' in f]
        if analysis_files:
            latest_summary = max(analysis_files, key=lambda f: os.path.getmtime(os.path.join(video_dir, f)))
            with open(os.path.join(video_dir, latest_summary), 'r', encoding='utf-8') as f:
                summary = json.load(f)
            context.append("\n### Latest Technical Summary:")
            context.append(summary['content'])
        
        # Get transcript segments
        transcript_file = find_latest_file(video_dir, '__transcript__')
        if transcript_file:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
            context.append("\n### Relevant Transcript Segments:")
            for seg in transcript:
                minutes = int(seg['start'] // 60)
                seconds = int(seg['start'] % 60)
                timestamp = f"[{minutes:02d}:{seconds:02d}]"
                # Only include segments that mention LLM-related keywords
                text = seg['text'].lower()
                if any(keyword in text for keyword in ['llm', 'ai', 'model', 'gpt', 'language model', 'prompt', 'token']):
                    context.append(f"{timestamp} {seg['text']}")
        
        # Get most recent analyses of other types
        for analysis_type in ['code_snippets', 'tools_and_resources', 'key_workflows']:
            files = [f for f in os.listdir(video_dir) if f'__analysis__{analysis_type}__' in f]
            if files:
                latest = max(files, key=lambda f: os.path.getmtime(os.path.join(video_dir, f)))
                with open(os.path.join(video_dir, latest), 'r', encoding='utf-8') as f:
                    analysis = json.load(f)
                context.append(f"\n### Latest {analysis_type.replace('_', ' ').title()}:")
                context.append(analysis['content'])
        
        # Join all context with proper spacing
        full_context = "\n".join(context)
        
        return full_context
    except Exception as e:
        logger.error(f"Error getting video context: {str(e)}", exc_info=True)
        return ""

@app.route('/')
def index():
    logger.debug("Serving index page")
    return render_template('index.html')

@app.route('/library')
def library():
    logger.debug("Serving library page")
    
    # Dictionary to store organized video data
    videos = {}
    
    try:
        # Scan the transcripts directory specifically
        transcripts_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts')
        for item in os.listdir(transcripts_dir):
            item_path = os.path.join(transcripts_dir, item)
            
            # Skip if not a directory
            if not os.path.isdir(item_path):
                continue
                
            # Check for transcript file to confirm it's a video entry
            transcript_file = find_latest_file(item_path, '__transcript__')
            if not transcript_file:
                continue
                
            # Initialize video entry
            videos[item] = {
                'video_dir': item_path,
                'original_transcript': None,
                'analyses': {
                    'technical_summary': {'mistral': [], 'gpt': []},
                    'full_context': {'mistral': [], 'gpt': []},
                    'code_snippets': {'mistral': [], 'gpt': []},
                    'tools_and_resources': {'mistral': [], 'gpt': []},
                    'key_workflows': {'mistral': [], 'gpt': []}
                }
            }
            
            # Add transcript info
            videos[item]['original_transcript'] = {
                'filename': os.path.basename(transcript_file),
                'timestamp': os.path.getmtime(transcript_file)
            }
            
            # Scan files in the video directory for analyses
            for filename in os.listdir(item_path):
                if '__analysis__' in filename and filename.endswith('.json'):
                    filepath = os.path.join(item_path, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            analysis_data = json.load(f)
                            
                        # Parse filename to get type and model
                        parts = filename.split('__')
                        if len(parts) >= 5:  # timestamp__analysis__type__model__title.json
                            analysis_type = parts[2]
                            model = parts[3]
                            timestamp = os.path.getmtime(filepath)
                            
                            if analysis_type in videos[item]['analyses']:
                                videos[item]['analyses'][analysis_type][model].append({
                                    'filename': filename,
                                    'timestamp': timestamp,
                                    'filepath': filepath
                                })
                                
                                # Sort analyses by timestamp (newest first)
                                videos[item]['analyses'][analysis_type][model].sort(
                                    key=lambda x: x['timestamp'],
                                    reverse=True
                                )
                    except Exception as e:
                        logger.error(f"Error processing analysis file {filename}: {str(e)}")
                        continue
        
        # Sort videos by most recently modified analysis
        def get_latest_timestamp(video_data):
            timestamps = []
            
            # Check original transcript
            if video_data.get('original_transcript'):
                timestamps.append(video_data['original_transcript'].get('timestamp', 0))
            
            # Check all analyses
            for analysis_type in video_data.get('analyses', {}):
                for model in video_data['analyses'][analysis_type]:
                    for analysis in video_data['analyses'][analysis_type][model]:
                        timestamps.append(analysis.get('timestamp', 0))
            
            return max(timestamps) if timestamps else 0
        
        sorted_videos = dict(sorted(
            videos.items(),
            key=lambda x: get_latest_timestamp(x[1]),
            reverse=True
        ))
        
        return render_template('library.html', videos=sorted_videos)
        
    except Exception as e:
        logger.error(f"Error serving library page: {str(e)}", exc_info=True)
        return render_template('library.html', videos={}, error=str(e))

@app.route('/get_transcript', methods=['POST'])
async def get_video_transcript():
    try:
        logger.debug("Received /get_transcript request")
        data = request.get_json()
        video_url = data.get('video_url')
        
        if not video_url:
            logger.warning("No video URL provided in request")
            return jsonify({'error': 'No video URL provided'}), 400

        logger.info(f"Fetching transcript and metadata for video URL: {video_url}")
        try:
            transcript, metadata = await get_transcript(video_url)
            logger.info(f"Retrieved transcript with {len(transcript)} segments")
            logger.info(f"Retrieved metadata for video: {metadata['title']}")
        except Exception as e:
            logger.error(f"Error fetching transcript or metadata: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to fetch video data: {str(e)}'}), 500

        # Create video directory using sanitized title
        video_title = metadata['title']
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        os.makedirs(video_dir, exist_ok=True)

        logger.info("Saving transcript and metadata")
        try:
            # Save transcript
            await analyzer.save_original_transcript(transcript, video_title)
            
            # Save metadata and thumbnails
            await save_video_metadata(metadata, video_dir)
            
            # Add transcript to vector store
            try:
                video_id = metadata.get('video_id', safe_title)
                vector_store.add_transcript(video_id, transcript)
                logger.info("Added transcript to vector store")
            except Exception as e:
                logger.error(f"Error adding transcript to vector store: {str(e)}", exc_info=True)
                # Continue execution even if vector store update fails
            
            logger.info("Transcript and metadata saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

        # Format transcript with timestamps
        formatted_transcript = {
            'segments': [{
                'timestamp': f"[{int(seg['start'])//60:02d}:{int(seg['start'])%60:02d}]" if int(seg['start']) % 60 == 0 else None,
                'start': seg['start'],
                'text': seg['text'].strip()  # Remove any extra whitespace
            } for seg in transcript]
        }

        # Combine segments that are part of the same sentence
        combined_segments = []
        current_text = []
        current_timestamp = None
        last_minute = -1

        for segment in formatted_transcript['segments']:
            current_minute = int(segment['start']) // 60
            
            # If we've moved to a new minute and haven't stored the timestamp yet
            if current_minute > last_minute:
                # If we have accumulated text, add it to segments
                if current_text:
                    combined_segments.append({
                        'timestamp': current_timestamp,
                        'text': ' '.join(current_text)
                    })
                    current_text = []
                
                current_timestamp = f"[{current_minute:02d}:00]"
                last_minute = current_minute
            
            current_text.append(segment['text'])
        
        # Add any remaining text
        if current_text:
            combined_segments.append({
                'timestamp': current_timestamp or f"[{int(formatted_transcript['segments'][-1]['start'])//60:02d}:00]",
                'text': ' '.join(current_text)
            })

        # Update the response data with combined segments
        response_data = {
            'title': video_title,
            'transcript': {'segments': combined_segments},
            'metadata': {
                'channel_name': metadata['channel_name'],
                'channel_url': metadata['channel_url'],
                'publish_date': metadata['publish_date'],
                'view_count': metadata['view_count'],
                'description': metadata['description'],
                'thumbnail_url': metadata['thumbnail_url']
            }
        }

        logger.info("Successfully processed video data")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in get_video_transcript: {str(e)}", exc_info=True)
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/analyze_transcript', methods=['POST'])
async def analyze_transcript():
    try:
        logger.debug("Received /analyze_transcript request")
        data = request.get_json()
        video_title = data.get('video_title')
        analysis_type = data.get('analysis_type', 'technical_summary')
        model = data.get('model', 'mistral')
        
        logger.info(f"Analyzing transcript for video: {video_title}")
        logger.info(f"Analysis type: {analysis_type}, Model: {model}")
        
        if not video_title:
            logger.warning("No video title provided in request")
            return jsonify({'error': 'No video title provided'}), 400
            
        # Get sanitized video directory
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        
        if not os.path.exists(video_dir):
            logger.error(f"Video directory not found: {video_dir}")
            return jsonify({'error': 'Video not found'}), 404

        # Find the most recent transcript file
        transcript_file = find_latest_file(video_dir, '__transcript__')
        if not transcript_file:
            logger.error("No transcript file found")
            return jsonify({'error': 'Transcript not found'}), 404
            
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
            logger.info("Retrieved original transcript")
        except Exception as e:
            logger.error(f"Error reading transcript file: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to read transcript: {str(e)}'}), 500
            
        try:
            if model == 'mistral':
                logger.info("Analyzing with Mistral model")
                result = await analyzer.analyze_with_mistral(transcript, analysis_type)
            else:
                logger.info("Analyzing with GPT model")
                result = await analyzer.analyze_with_gpt(transcript, analysis_type)
            logger.info("Analysis completed successfully")
            
            # Add analysis to vector store
            try:
                # Create a document with metadata for the analysis
                analysis_doc = {
                    'text': result,
                    'type': f'analysis_{analysis_type}',
                    'model': model,
                    'post_id': post_id
                }
                vector_store.add_reddit_analysis(post_id, analysis_type, model, {'text': result, 'metadata': analysis_doc})
                logger.info("Added analysis to vector store")
            except Exception as e:
                logger.error(f"Error adding analysis to vector store: {str(e)}", exc_info=True)
                # Continue execution even if vector store update fails
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}", exc_info=True)
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500
            
        try:
            await analyzer.save_analysis(result, video_title, analysis_type, model)
            logger.info("Analysis results saved successfully")
        except Exception as e:
            logger.error(f"Error saving analysis results: {str(e)}", exc_info=True)
            # Continue even if saving fails
            
        return jsonify({'analysis': result})
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_transcript: {str(e)}", exc_info=True)
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/get_saved_transcript', methods=['POST'])
async def get_saved_transcript():
    try:
        data = request.get_json()
        video_title = data.get('video_title')
        
        if not video_title:
            return jsonify({'error': 'No video title provided'}), 400
            
        # Get sanitized video directory
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        
        if not os.path.exists(video_dir):
            return jsonify({'error': 'Video not found'}), 404
            
        # Find the most recent transcript file
        transcript_file = find_latest_file(video_dir, '__transcript__')
        if not transcript_file:
            return jsonify({'error': 'Transcript not found'}), 404
            
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
        except Exception as e:
            logger.error(f"Error reading transcript file: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to read transcript: {str(e)}'}), 500
            
        # Format transcript with timestamps
        formatted_transcript = {
            'segments': []
        }
        
        last_minute = -1
        current_text = []
        current_timestamp = None
        
        for seg in transcript:
            current_minute = int(seg['start']) // 60
            
            # If we've moved to a new minute
            if current_minute > last_minute:
                # If we have accumulated text, add it to segments
                if current_text:
                    formatted_transcript['segments'].append({
                        'timestamp': current_timestamp,
                        'text': ' '.join(current_text)
                    })
                    current_text = []
                
                current_timestamp = f"[{current_minute:02d}:00]"
                last_minute = current_minute
            
            current_text.append(seg['text'])
        
        # Add any remaining text
        if current_text:
            formatted_transcript['segments'].append({
                'timestamp': current_timestamp or f"[{last_minute:02d}:00]",
                'text': ' '.join(current_text)
            })
        
        return jsonify(formatted_transcript)
        
    except Exception as e:
        logger.error(f"Error in get_saved_transcript: {str(e)}", exc_info=True)
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/get_analysis', methods=['POST'])
async def get_analysis():
    try:
        data = request.get_json()
        filepath = data.get('filepath')
        
        if not filepath:
            return jsonify({'error': 'No filepath provided'}), 400
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading analysis file: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to read analysis: {str(e)}'}), 500
            
        return jsonify({'content': analysis_data['content']})
        
    except Exception as e:
        logger.error(f"Error in get_analysis: {str(e)}", exc_info=True)
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

# Add timestamp filter for Jinja templates
@app.template_filter('timestamp')
def timestamp_filter(value):
    """Convert a timestamp to a readable date format."""
    try:
        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return str(value)

@app.template_filter('urlencode')
def urlencode_filter(s):
    """URL encode a string."""
    if isinstance(s, str):
        s = s.encode('utf-8')
    return urllib.parse.quote_plus(s)

@app.route('/chat_with_video', methods=['POST'])
async def chat_with_video():
    try:
        data = request.get_json()
        video_title = data.get('video_title')
        message = data.get('message')
        
        if not video_title or not message:
            return jsonify({'error': 'Missing video title or message'}), 400
            
        # Get context and chat history
        context = await get_video_context(video_title)
        history = await load_chat_history(video_title)
        
        # Prepare system message with context
        system_message = (
            "You are a helpful AI assistant discussing a YouTube video. "
            "Below is the video's transcript and analyses. This information includes:\n"
            "1. The video title\n"
            "2. The full transcript with timestamps\n"
            "3. Various analyses of the content\n\n"
            "Use this information to answer questions about the video. "
            "Reference specific timestamps when relevant. "
            "If you can't find the answer in the provided context, say so clearly. "
            "Keep responses clear and concise.\n\n"
            f"{context}"
        )
        
        # Format chat history for Mistral
        chat_messages = [{"role": "system", "content": system_message}]
        # Add last few messages for context (limit to keep context window manageable)
        for msg in history["messages"][-6:]:  # Last 3 exchanges
            chat_messages.append({"role": msg["role"], "content": msg["content"]})
        # Add current message
        chat_messages.append({"role": "user", "content": message})
        
        try:
            # Get response from Mistral
            response = await analyzer.chat_with_mistral(chat_messages)
            
            # Save to history
            await save_chat_history(video_title, message, response)
            
            return jsonify({'response': response})
            
        except Exception as e:
            logger.error(f"Error getting Mistral response: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to get response: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in chat_with_video: {str(e)}", exc_info=True)
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
            
@app.route('/get_chat_history', methods=['POST'])
async def get_chat_history():
    try:
        data = request.get_json()  # Remove await since Flask's request.get_json() is not async
        video_title = data.get('video_title')
        if not video_title:
            return jsonify({'error': 'Video title is required'}), 400
            
        # Get sanitized video directory
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        
        if not os.path.exists(video_dir):
            return jsonify({'video_id': video_title, 'messages': []}), 200
            
        # Find the most recent chat history file
        chat_filename = find_latest_file(video_dir, '__chat__')
        
        if chat_filename:
            try:
                with open(chat_filename, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                return jsonify({'messages': history.get('messages', [])})
            except Exception as e:
                logger.error(f"Error reading chat history file: {str(e)}", exc_info=True)
                return jsonify({'error': f'Failed to read chat history: {str(e)}'}), 500
        else:
            return jsonify({'video_id': video_title, 'messages': []}), 200
            
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to load chat history: {str(e)}'}), 500
            
@app.route('/delete_chat_message', methods=['POST'])
async def delete_chat_message():
    try:
        data = request.get_json()  # Remove await since Flask's request.get_json() is not async
        video_title = data.get('video_title')
        timestamp = data.get('timestamp')
        
        if not video_title or not timestamp:
            return jsonify({'error': 'Video title and timestamp are required'}), 400
            
        # Load current history
        history = await load_chat_history(video_title)
        
        # Filter out the message with matching timestamp
        history['messages'] = [msg for msg in history.get('messages', []) if msg.get('timestamp') != timestamp]
        
        # Save updated history
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        chat_filename = generate_chat_filename(video_title)
        history_file = os.path.join(video_dir, chat_filename)
        
        async with aiofiles.open(history_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(history, indent=2, ensure_ascii=False))
            
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting chat message: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to delete message'}), 500

@app.route('/video/<video_title>')
async def video_page(video_title):
    try:
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', sanitize_filename(video_title))
        
        if not os.path.exists(video_dir):
            return render_template('error.html', error="Video not found"), 404

        # Get metadata for video URL
        metadata = None
        metadata_file = find_latest_file(video_dir, '__metadata__')
        if metadata_file:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.error(f"Error reading metadata file: {str(e)}")

        # Get transcript - find most recent transcript file
        transcript = []
        transcript_filename = find_latest_file(video_dir, '__transcript__')
        if transcript_filename:
            try:
                transcript_path = os.path.join(video_dir, transcript_filename)
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    raw_transcript = json.load(f)
                    
                    # Process transcript with minute-based timestamps
                    last_minute = -1
                    current_text = []
                    current_timestamp = None
                    
                    for seg in raw_transcript:
                        current_minute = int(seg['start']) // 60
                        
                        # If we've moved to a new minute
                        if current_minute > last_minute:
                            # If we have accumulated text, add it to transcript
                            if current_text:
                                transcript.append({
                                    'timestamp': current_timestamp,
                                    'text': ' '.join(current_text)
                                })
                                current_text = []
                            
                            current_timestamp = f"[{current_minute:02d}:00]"
                            last_minute = current_minute
                        
                        current_text.append(seg['text'])
                    
                    # Add any remaining text
                    if current_text:
                        transcript.append({
                            'timestamp': current_timestamp or f"[{last_minute:02d}:00]",
                            'text': ' '.join(current_text)
                        })
            except Exception as e:
                logger.error(f"Error reading transcript file: {str(e)}")

        # Get analyses
        analyses = {
            'technical_summary': {'mistral': [], 'gpt': []},
            'full_context': {'mistral': [], 'gpt': []},
            'code_snippets': {'mistral': [], 'gpt': []},
            'tools_and_resources': {'mistral': [], 'gpt': []},
            'key_workflows': {'mistral': [], 'gpt': []}
        }
        
        # Group analysis files by type and model
        for filename in os.listdir(video_dir):
            if '__analysis__' in filename and filename.endswith('.json'):
                filepath = os.path.join(video_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    
                    # Parse filename to get type and model
                    parts = filename.split('__')
                    if len(parts) >= 5:  # timestamp__analysis__type__model__title.json
                        analysis_type = parts[2]
                        model = parts[3]
                        timestamp = os.path.getmtime(filepath)
                        
                        if analysis_type in analyses:
                            analyses[analysis_type][model].append({
                                'content': analysis_data['content'],
                                'timestamp': timestamp
                            })
                except Exception as e:
                    logger.error(f"Error reading analysis file {filename}: {str(e)}")
                    continue

        # Sort analyses by timestamp
        for analysis_type in analyses:
            for model in analyses[analysis_type]:
                analyses[analysis_type][model].sort(key=lambda x: x['timestamp'], reverse=True)

        # Get chat history for stats
        chat_history = await load_chat_history(video_title)
        
        # Calculate stats
        stats = {
            'transcript_length': sum(len(seg['text'].split()) for seg in transcript),
            'analyses_count': sum(
                len(model_analyses) 
                for analysis_type in analyses.values() 
                for model_analyses in analysis_type.values()
            ),
            'chat_messages': len(chat_history.get('messages', [])),
        }
        
        # Calculate duration from transcript
        if transcript and raw_transcript:
            try:
                last_start = raw_transcript[-1]['start']
                minutes = int(last_start // 60)
                seconds = int(last_start % 60)
                stats['duration'] = f"{minutes}:{seconds:02d}"
            except (IndexError, ValueError, NameError):
                stats['duration'] = "0:00"
        else:
            stats['duration'] = "0:00"

        return render_template(
            'video_page.html',
            video_title=video_title,
            transcript=transcript,
            analyses=analyses,
            stats=stats,
            metadata=metadata  # Add metadata to template context
        )
        
    except Exception as e:
        logger.error(f"Error serving video page: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e)), 500

@app.context_processor
def utility_processor():
    """Add utility functions to template context."""
    return {
        'find_latest_file': find_latest_file,
        'load_json_file': load_json_file
    }

@app.route('/delete_video', methods=['POST'])
def delete_video():
    try:
        data = request.get_json()
        video_title = data.get('video_title')
        
        if not video_title:
            return jsonify({'error': 'Video title is required'}), 400
            
        # Get sanitized video directory
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        
        if not os.path.exists(video_dir):
            return jsonify({'error': 'Video not found'}), 404
            
        try:
            # Delete from vector store
            try:
                # Delete transcript segments
                vector_store.delete_video(safe_title)
                
                # Delete analyses
                for analysis_type in ['technical_summary', 'full_context', 'code_snippets', 'tools_and_resources', 'key_workflows']:
                    for model in ['mistral', 'gpt']:
                        vector_store.delete_video(f"{safe_title}_{analysis_type}_{model}")
                logger.info("Deleted video data from vector store")
            except Exception as e:
                logger.error(f"Error deleting from vector store: {str(e)}", exc_info=True)
                # Continue with file deletion even if vector store deletion fails
            
            # Remove all files in the directory
            for filename in os.listdir(video_dir):
                file_path = os.path.join(video_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {str(e)}")
            
            # Remove the directory
            os.rmdir(video_dir)
            
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"Error deleting video directory: {str(e)}")
            return jsonify({'error': f'Failed to delete video: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in delete_video: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/delete_analysis', methods=['POST'])
def delete_analysis():
    try:
        logger.debug("Received /delete_analysis request")
        data = request.get_json()
        
        video_title = data.get('video_title')
        analysis_type = data.get('analysis_type')
        model = data.get('model')
        timestamp = data.get('timestamp')
        
        if not all([video_title, analysis_type, model, timestamp]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        # Get sanitized video directory
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'transcripts', safe_title)
        
        if not os.path.exists(video_dir):
            return jsonify({'error': 'Video not found'}), 404
            
        # Find the analysis file with matching timestamp
        target_file = None
        for filename in os.listdir(video_dir):
            if (f'__analysis__{analysis_type}__{model}__' in filename and 
                filename.endswith('.json')):
                filepath = os.path.join(video_dir, filename)
                if abs(os.path.getmtime(filepath) - float(timestamp)) < 1:  # Within 1 second
                    target_file = filepath
                    break
        
        if not target_file:
            logger.error(f"Analysis file not found: {target_file}")
            return jsonify({'error': 'Analysis file not found'}), 404
            
        try:
            os.remove(target_file)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error deleting analysis file: {str(e)}")
            return jsonify({'error': f'Failed to delete analysis: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in delete_analysis: {str(e)}", exc_info=True)
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/admin/backup', methods=['POST'])
def trigger_backup():
    try:
        import subprocess
        import os
        
        data = request.get_json() or {}
        api_export = data.get('api_export', False)
        max_backups = data.get('max_backups', 5)
        
        # Use external drive as default backup location
        backup_dir = data.get('backup_dir', '/Volumes/RileyNumber1/youtube_transcription/chroma_db_backup')
        
        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)
        
        # Construct command with updated script path
        cmd = [
            'python', os.path.join(os.path.dirname(__file__), 'backup', 'backup_vector_store.py'),
            '--source', os.path.join(os.path.dirname(__file__), 'chroma_db'),
            '--backup-dir', backup_dir,
            '--max-backups', str(max_backups)
        ]
        
        if api_export:
            cmd.append('--api-export')
        
        logger.info(f"Running backup command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Backup completed successfully")
            return jsonify({'success': True, 'message': 'Backup completed successfully'})
        else:
            logger.error(f"Backup failed: {result.stderr}")
            return jsonify({'success': False, 'error': result.stderr}), 500
            
    except Exception as e:
        logger.error(f"Error triggering backup: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/backup/schedule', methods=['GET'])
def get_backup_schedule():
    try:
        import subprocess
        
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({'success': False, 'error': 'Failed to get crontab'}), 500
            
        crontab = result.stdout
        
        # Look for backup job
        backup_jobs = []
        for line in crontab.splitlines():
            if 'backup_vector_store.py' in line and not line.startswith('#'):
                # Parse cron schedule
                parts = line.strip().split()
                if len(parts) >= 5:
                    schedule = {
                        'minute': parts[0],
                        'hour': parts[1],
                        'day_of_month': parts[2],
                        'month': parts[3],
                        'day_of_week': parts[4],
                        'command': ' '.join(parts[5:])
                    }
                    
                    # Convert day of week to human-readable format
                    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                    if schedule['day_of_week'] in ['0', 'SUN', 'Sun', 'sunday']:
                        schedule['readable'] = f"Every Sunday at {schedule['hour']}:{schedule['minute']}"
                    elif schedule['day_of_week'] == '*' and schedule['day_of_month'] == '*':
                        schedule['readable'] = f"Every day at {schedule['hour']}:{schedule['minute']}"
                    else:
                        try:
                            day_num = int(schedule['day_of_week'])
                            if 0 <= day_num <= 6:
                                schedule['readable'] = f"Every {days[day_num]} at {schedule['hour']}:{schedule['minute']}"
                            else:
                                schedule['readable'] = f"At {schedule['hour']}:{schedule['minute']} on day-of-week {schedule['day_of_week']}"
                        except ValueError:
                            schedule['readable'] = f"At {schedule['hour']}:{schedule['minute']} on {schedule['day_of_week']}"
                    
                    backup_jobs.append(schedule)
        
        if backup_jobs:
            return jsonify({
                'success': True, 
                'backup_jobs': backup_jobs,
                'next_backup': backup_jobs[0]['readable']
            })
        else:
            return jsonify({
                'success': True,
                'backup_jobs': [],
                'message': 'No scheduled backups found'
            })
            
    except Exception as e:
        logger.error(f"Error getting backup schedule: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/reddit/fetch', methods=['POST'])
def fetch_reddit_post():
    """First step: Fetch and store Reddit post content."""
    try:
        data = request.get_json()
        post_url = data.get('post_url')
        
        if not post_url:
            logger.warning("No post URL provided")
            return jsonify({'error': 'Post URL is required'}), 400
            
        logger.info(f"Attempting to fetch Reddit post: {post_url}")
            
        # Extract post data
        try:
            post_data = reddit_extractor.extract_post(post_url)
        except ValueError as e:
            logger.error(f"Validation error extracting post: {str(e)}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Unexpected error extracting post: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to extract post data. Please check the URL and try again.'}), 500
            
        if not post_data:
            logger.error("No post data returned from extractor")
            return jsonify({'error': 'Failed to extract post data'}), 400

        # Create reddit directory if it doesn't exist
        reddit_base_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'reddit')
        os.makedirs(reddit_base_dir, exist_ok=True)

        # Sanitize post title for directory name
        safe_title = sanitize_filename(post_data['title'])
        # Append post ID to ensure uniqueness
        dir_name = f"{safe_title}__{post_data['id']}"
        post_dir = os.path.join(reddit_base_dir, dir_name)
        os.makedirs(post_dir, exist_ok=True)

        # Save post data to file with descriptive name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        post_filename = f"{timestamp}__post__{safe_title}__{post_data['id']}.json"
        post_filepath = os.path.join(post_dir, post_filename)

        try:
            with open(post_filepath, 'w', encoding='utf-8') as f:
                json.dump(post_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved post data to {post_filepath}")
        except Exception as e:
            logger.error(f"Error saving post data to file: {str(e)}", exc_info=True)
            # Continue since we can still store in vector DB
            
        # Store in vector database
        try:
            vector_store.add_reddit_post(post_data['id'], post_data)
            logger.info(f"Successfully stored post {post_data['id']} in vector database")
        except Exception as e:
            logger.error(f"Error storing post in vector database: {str(e)}", exc_info=True)
            # Continue since we can still return the post data even if storage fails
        
        # Format timestamp for display
        try:
            created_utc = datetime.fromtimestamp(post_data['created_utc']).isoformat()
        except (TypeError, ValueError):
            created_utc = post_data['created_utc']
        
        # Return post data for display
        response_data = {
            'title': post_data['title'],
            'selftext': post_data['selftext'],
            'author': post_data['author'],
            'subreddit': post_data['subreddit'],
            'created_utc': created_utc,
            'score': post_data['score'],
            'num_comments': post_data['num_comments'],
            'post_id': post_data['id']  # Add post_id to response
        }
        
        logger.info(f"Successfully fetched and processed Reddit post: {post_data['title']}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in fetch_reddit_post: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/analyze_reddit_post', methods=['POST'])
async def analyze_reddit_post():
    try:
        logger.debug("Received /analyze_reddit_post request")
        data = request.get_json()
        post_id = data.get('post_id')
        analysis_type = data.get('analysis_type', 'summary')
        model = data.get('model', 'mistral')
        
        logger.info(f"Analyzing Reddit post ID: {post_id}")
        logger.info(f"Analysis type: {analysis_type}, Model: {model}")
        
        if not post_id:
            logger.warning("No post ID provided in request")
            return jsonify({'error': 'No post ID provided'}), 400
            
        # Get post data from saved files
        post_data = get_post_data(post_id)
        if not post_data:
            logger.error("Failed to get post data")
            return jsonify({'error': 'Failed to get post data'}), 400
            
        logger.info(f"Successfully retrieved post data for ID: {post_id}")
        
        try:
            if model == 'mistral':
                logger.info("Analyzing with Mistral model")
                result = await reddit_analyzer.analyze_with_mistral(post_data, analysis_type)
            else:
                logger.info("Analyzing with GPT model")
                result = await reddit_analyzer.analyze_with_gpt(post_data, analysis_type)
            logger.info("Analysis completed successfully")
            
            # Add analysis to vector store
            try:
                # Create a document with metadata for the analysis
                analysis_doc = {
                    'text': result,
                    'type': f'analysis_{analysis_type}',
                    'model': model,
                    'post_id': post_id
                }
                vector_store.add_reddit_analysis(post_id, analysis_type, model, {'text': result, 'metadata': analysis_doc})
                logger.info("Added analysis to vector store")
            except Exception as e:
                logger.error(f"Error adding analysis to vector store: {str(e)}", exc_info=True)
                # Continue execution even if vector store update fails
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}", exc_info=True)
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500
            
        try:
            await reddit_analyzer.save_analysis(result, post_id, analysis_type, model)
            logger.info("Analysis results saved successfully")
        except Exception as e:
            logger.error(f"Error saving analysis results: {str(e)}", exc_info=True)
            # Continue even if saving fails
            
        return jsonify({'analysis': result})
            
    except Exception as e:
        logger.error(f"Error in analyze_reddit_post: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/delete_reddit_analysis', methods=['POST'])
def delete_reddit_analysis():
    try:
        logger.debug("Received /delete_reddit_analysis request")
        data = request.get_json()
        
        post_id = data.get('post_id')
        analysis_type = data.get('analysis_type')
        model = data.get('model')
        timestamp = data.get('timestamp')
        
        if not all([post_id, analysis_type, model, timestamp]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        # Get post directory
        post_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'reddit', post_id)
        
        if not os.path.exists(post_dir):
            return jsonify({'error': 'Post not found'}), 404
            
        # Find the analysis file with matching timestamp
        target_file = None
        for filename in os.listdir(post_dir):
            if (f'__analysis__{analysis_type}__{model}__' in filename and 
                filename.endswith('.json')):
                filepath = os.path.join(post_dir, filename)
                if abs(os.path.getmtime(filepath) - float(timestamp)) < 1:  # Within 1 second
                    target_file = filepath
                    break
        
        if not target_file:
            logger.error(f"Analysis file not found: {target_file}")
            return jsonify({'error': 'Analysis file not found'}), 404
            
        try:
            os.remove(target_file)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error deleting analysis file: {str(e)}")
            return jsonify({'error': f'Failed to delete analysis: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in delete_reddit_analysis: {str(e)}", exc_info=True)
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/reddit/library')
def reddit_library():
    """Serve the Reddit library page."""
    logger.debug("Serving Reddit library page")
    
    try:
        # Update the post index
        post_index = update_post_index()
        
        # Get the current page from query parameters
        page = request.args.get('page', 1, type=int)
        
        # Calculate pagination
        total_posts = len(post_index)
        total_pages = (total_posts + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
        start_idx = (page - 1) * POSTS_PER_PAGE
        end_idx = start_idx + POSTS_PER_PAGE
        
        # Get the slice of posts for the current page
        current_page_posts = dict(list(post_index.items())[start_idx:end_idx])
        
        # Add analyses to each post
        formatted_posts = {}
        for post_id, post_info in current_page_posts.items():
            analyses = get_post_analyses(post_id)
            if analyses:
                # Flatten analyses for display
                flattened_analyses = []
                for analysis_type, models in analyses.items():
                    for model, items in models.items():
                        for analysis in items:
                            flattened_analyses.append({
                                'analysis': analysis['content'],
                                'metadata': {
                                    'analysis_type': analysis_type,
                                    'model': model,
                                    'timestamp': analysis.get('timestamp', '')
                                }
                            })
                post_info['analyses'] = flattened_analyses
            else:
                post_info['analyses'] = []
            
            formatted_posts[post_id] = post_info
        
        return render_template(
            'reddit_library.html',
            posts=formatted_posts,
            current_page=page,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error serving Reddit library page: {str(e)}", exc_info=True)
        return render_template('reddit_library.html', posts={}, error=str(e))

@app.route('/reddit/post/<post_id>')
def reddit_post(post_id):
    """Serve the Reddit post page."""
    try:
        logger.debug(f"Serving Reddit post page for post_id: {post_id}")
        
        # Get post data
        post_data = get_post_data(post_id)
        if not post_data:
            logger.error(f"Post data not found for post_id: {post_id}")
            return render_template('error.html', error="Post not found"), 404
            
        # Get analyses
        analyses = get_post_analyses(post_id)
        if analyses:
            # Flatten analyses for display
            flattened_analyses = []
            for analysis_type, models in analyses.items():
                for model, items in models.items():
                    for analysis in items:
                        flattened_analyses.append({
                            'analysis': analysis['content'],
                            'metadata': {
                                'analysis_type': analysis_type,
                                'model': model,
                                'timestamp': analysis.get('timestamp', '')
                            }
                        })
        else:
            flattened_analyses = []
        
        # Format post data for template
        formatted_post = {
            'id': post_id,
            'title': post_data['title'],
            'author': post_data['author'],
            'subreddit': post_data['subreddit'],
            'score': post_data['score'],
            'upvote_ratio': post_data.get('upvote_ratio', 0.0),
            'num_comments': post_data['num_comments'],
            'created_utc': post_data['created_utc'],
            'selftext': post_data['selftext'],
            'url': post_data.get('url', ''),
            'permalink': post_data.get('permalink', '')
        }
        
        return render_template(
            'reddit_post.html',
            post=formatted_post,
            analyses=flattened_analyses
        )
        
    except Exception as e:
        logger.error(f"Error serving Reddit post page: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e)), 500

@app.route('/delete_reddit_post', methods=['POST'])
def delete_reddit_post():
    """Delete a Reddit post and its associated files."""
    try:
        logger.debug("Received /delete_reddit_post request")
        data = request.get_json()
        post_id = data.get('post_id')
        
        if not post_id:
            logger.warning("No post ID provided")
            return jsonify({'error': 'No post ID provided'}), 400
            
        # Get post directory from index
        post_index = update_post_index()
        if post_id not in post_index:
            logger.error(f"Post {post_id} not found in index")
            return jsonify({'error': 'Post not found'}), 404
            
        post_info = post_index[post_id]
        post_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'reddit', post_info['dir_name'])
        
        if not os.path.exists(post_dir):
            logger.error(f"Post directory not found: {post_dir}")
            return jsonify({'error': 'Post directory not found'}), 404
            
        try:
            # Delete from vector store first
            vector_store.delete_reddit_post(post_id)
            logger.info(f"Deleted post {post_id} from vector store")
            
            # Then delete the directory
            shutil.rmtree(post_dir)
            logger.info(f"Deleted post directory: {post_dir}")
            
            # Update the index
            update_post_index()
            
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"Error deleting post: {str(e)}")
            return jsonify({'error': f'Failed to delete post: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in delete_reddit_post: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Add markdown filter
@app.template_filter('markdown')
def markdown_filter(text):
    """Convert markdown text to HTML with advanced features."""
    if not text:
        return ""
    try:
        import markdown2
        extras = [
            "fenced-code-blocks",   # Support ```code blocks```
            "tables",               # Support markdown tables
            "break-on-newline",     # Support line breaks
            "cuddled-lists",        # Better list handling
            "code-friendly",        # Better code block handling
            "numbering",            # Support numbered lists
            "strike",               # Support ~~strikethrough~~
            "task_list",            # Support [ ] task lists
            "wiki-tables",          # Support more complex tables
            "header-ids"            # Add IDs to headers for linking
        ]
        return markdown2.markdown(text, extras=extras, safe_mode=False)
    except ImportError:
        return text.replace('\n', '<br>')

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=5002, debug=True) 