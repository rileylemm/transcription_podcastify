from flask import Flask, request, jsonify
from podcastfy.client import generate_podcast
import os
import json
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure paths
TRANSCRIPTS_DIR = Path("/app/data/transcripts")
ANALYSIS_DIR = Path("/app/data/analysis")
OUTPUT_DIR = Path("/app/output")

def read_transcript_data(transcript_id):
    """Read transcript and analysis data for a given ID."""
    # Read transcript
    transcript_file = TRANSCRIPTS_DIR / f"{transcript_id}.json"
    if not transcript_file.exists():
        raise FileNotFoundError(f"Transcript {transcript_id} not found")
    
    with open(transcript_file, 'r') as f:
        transcript_data = json.load(f)
    
    # Read analysis if available
    analysis_file = ANALYSIS_DIR / f"{transcript_id}.json"
    analysis_data = None
    if analysis_file.exists():
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
    
    return transcript_data, analysis_data

def format_content_for_podcast(transcript_data, analysis_data=None):
    """Format transcript and analysis data for podcast generation."""
    content = []
    
    # Add video title and description if available
    if 'video_info' in transcript_data:
        content.append(f"Title: {transcript_data['video_info'].get('title', 'Untitled')}")
        if 'description' in transcript_data['video_info']:
            content.append(f"Description: {transcript_data['video_info']['description']}")
    
    # Add transcript content
    if 'transcript' in transcript_data:
        content.append("\nTranscript:")
        for segment in transcript_data['transcript']:
            content.append(segment.get('text', ''))
    
    # Add analysis insights if available
    if analysis_data:
        content.append("\nKey Insights:")
        if 'summary' in analysis_data:
            content.append(f"Summary: {analysis_data['summary']}")
        if 'key_points' in analysis_data:
            content.append("Key Points:")
            for point in analysis_data['key_points']:
                content.append(f"- {point}")
    
    return "\n".join(content)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/generate/from-transcript/<transcript_id>', methods=['POST'])
def generate_from_transcript(transcript_id):
    try:
        # Read transcript and analysis data
        transcript_data, analysis_data = read_transcript_data(transcript_id)
        
        # Format content for podcast generation
        content = format_content_for_podcast(transcript_data, analysis_data)
        
        # Get optional parameters
        options = request.get_json() or {}
        
        # Generate podcast from content
        output_path = OUTPUT_DIR / f"podcast_{transcript_id}.mp3"
        
        # Generate podcast using formatted content
        audio_file = generate_podcast(
            content=content,
            output_path=str(output_path),
            **options
        )
        
        return jsonify({
            "status": "success",
            "audio_file": audio_file,
            "transcript_id": transcript_id
        })
        
    except FileNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'urls' not in data:
            return jsonify({"error": "Missing required field: urls"}), 400
            
        urls = data['urls']
        if not isinstance(urls, list):
            return jsonify({"error": "urls must be a list"}), 400
            
        # Optional parameters
        options = data.get('options', {})
        
        # Generate podcast
        audio_file = generate_podcast(
            urls=urls,
            **options
        )
        
        return jsonify({
            "status": "success",
            "audio_file": audio_file
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 