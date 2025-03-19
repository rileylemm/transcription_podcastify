#!/usr/bin/env python3
"""
YouTube Transcript Fetcher

This script fetches and saves transcripts from YouTube videos.
It handles various YouTube URL formats and saves the transcripts
with metadata in JSON format.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import re
import aiohttp
import asyncio
import argparse
import logging
import ssl
import certifi
import os

# Configure logging
logger = logging.getLogger(__name__)

async def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    # Handle different URL formats
    if 'youtu.be' in url:
        return url.split('/')[-1]
    
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        if 'watch' in parsed_url.path:
            return parse_qs(parsed_url.query)['v'][0]
        elif 'embed' in parsed_url.path:
            return parsed_url.path.split('/')[-1]
    
    raise ValueError("Invalid YouTube URL format")

async def get_video_metadata(video_id: str) -> Dict:
    """
    Fetch video metadata using YouTube's oEmbed API and additional data from the video page.
    """
    try:
        # First get basic metadata using oEmbed API
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(oembed_url) as response:
                if response.status == 200:
                    oembed_data = await response.json()
                else:
                    raise Exception(f"Failed to fetch oEmbed data: {await response.text()}")

        # Now get additional metadata from the video page
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Extract additional metadata using regex patterns
                    view_count_match = re.search(r'"viewCount":"(\d+)"', html)
                    publish_date_match = re.search(r'"publishDate":"([^"]+)"', html)
                    channel_id_match = re.search(r'"channelId":"([^"]+)"', html)
                    description_match = re.search(r'"description":{"simpleText":"([^"]+)"', html)
                    
                    # Combine all metadata
                    metadata = {
                        'video_id': video_id,
                        'title': oembed_data.get('title'),
                        'channel_name': oembed_data.get('author_name'),
                        'channel_url': oembed_data.get('author_url'),
                        'thumbnail_url': f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",  # High quality thumbnail
                        'thumbnail_url_hq': f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                        'thumbnail_url_mq': f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                        'thumbnail_url_default': f"https://i.ytimg.com/vi/{video_id}/default.jpg",
                        'view_count': int(view_count_match.group(1)) if view_count_match else None,
                        'publish_date': publish_date_match.group(1) if publish_date_match else None,
                        'channel_id': channel_id_match.group(1) if channel_id_match else None,
                        'description': description_match.group(1) if description_match else None,
                        'html': oembed_data.get('html'),  # Embed HTML
                        'provider_name': oembed_data.get('provider_name'),
                        'provider_url': oembed_data.get('provider_url'),
                        'fetched_at': datetime.now().isoformat(),
                    }
                    
                    # Download thumbnails
                    async with aiohttp.ClientSession() as session:
                        for quality in ['default', 'mq', 'hq']:
                            thumb_url = metadata[f'thumbnail_url_{quality}']
                            try:
                                async with session.get(thumb_url) as thumb_response:
                                    if thumb_response.status == 200:
                                        metadata[f'thumbnail_{quality}_available'] = True
                                    else:
                                        metadata[f'thumbnail_{quality}_available'] = False
                            except Exception as e:
                                logger.error(f"Error checking thumbnail {quality}: {str(e)}")
                                metadata[f'thumbnail_{quality}_available'] = False
                    
                    return metadata
                else:
                    raise Exception(f"Failed to fetch video page: {response.status}")
                    
    except Exception as e:
        logger.error(f"Error fetching video metadata: {str(e)}")
        raise

async def get_video_title(url: str) -> str:
    """Get the title of a YouTube video."""
    try:
        video_id = await extract_video_id(url)
        metadata = await get_video_metadata(video_id)
        return metadata['title']
    except Exception as e:
        logger.error(f"Error getting video title: {str(e)}")
        raise

async def get_transcript(url: str) -> Tuple[List[Dict], Dict]:
    """
    Get transcript and metadata for a YouTube video.
    Returns a tuple of (transcript, metadata).
    """
    try:
        video_id = await extract_video_id(url)
        
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Get metadata
        metadata = await get_video_metadata(video_id)
        
        return transcript, metadata
        
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        raise

async def save_video_metadata(metadata: Dict, video_dir: str) -> str:
    """Save video metadata to a file."""
    try:
        os.makedirs(video_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}__metadata__{metadata['video_id']}.json"
        filepath = os.path.join(video_dir, filename)
        
        # Simplify thumbnail URLs to just store the best available version
        thumbnail_url = metadata['thumbnail_url_hq']  # Try high quality first
        if not await check_thumbnail_availability(thumbnail_url):
            thumbnail_url = metadata['thumbnail_url_mq']  # Fall back to medium quality
            if not await check_thumbnail_availability(thumbnail_url):
                thumbnail_url = metadata['thumbnail_url_default']  # Fall back to default
        
        # Update metadata with single thumbnail URL and video URL
        metadata['thumbnail_url'] = thumbnail_url
        metadata['video_url'] = f"https://www.youtube.com/watch?v={metadata['video_id']}"
        
        # Remove redundant thumbnail URLs
        for key in ['thumbnail_url_hq', 'thumbnail_url_mq', 'thumbnail_url_default']:
            metadata.pop(key, None)
        
        # Save metadata
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        # Save single thumbnail
        thumb_filename = f"{timestamp}__thumbnail__{metadata['video_id']}.jpg"
        thumb_path = os.path.join(video_dir, thumb_filename)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as response:
                if response.status == 200:
                    with open(thumb_path, 'wb') as f:
                        f.write(await response.read())
        
        return filepath
        
    except Exception as e:
        logger.error(f"Error saving video metadata: {str(e)}")
        raise

async def check_thumbnail_availability(url: str) -> bool:
    """Check if a thumbnail URL is available."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return response.status == 200
    except Exception:
        return False

def get_best_transcript(video_id: str, lang: str = 'en') -> List[Dict]:
    """
    Get the best available transcript for a video.
    Tries to get manual transcripts first, then falls back to auto-generated.
    Also attempts to get transcripts with formatting if available.
    
    Args:
        video_id: YouTube video ID
        lang: Language code (default: 'en')
        
    Returns:
        List of transcript segments
    """
    try:
        # Get list of available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            # First try to get manual transcript in target language
            transcript = transcript_list.find_manually_created_transcript([lang])
        except:
            try:
                # Then try to get manual transcript in any language and translate
                transcript = transcript_list.find_manually_created_transcript()
                transcript = transcript.translate(lang)
            except:
                try:
                    # Fall back to auto-generated in target language
                    transcript = transcript_list.find_generated_transcript([lang])
                except:
                    # Last resort: auto-generated in any language and translate
                    transcript = transcript_list.find_generated_transcript()
                    transcript = transcript.translate(lang)
        
        return transcript.fetch()
    
    except Exception as e:
        print(f"Error getting best transcript: {str(e)}")
        # Fall back to basic transcript fetch
        return YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])


def clean_and_format_text(text: str) -> str:
    """
    Clean and format transcript text.
    - Fixes common OCR/auto-transcription errors
    - Adds proper capitalization
    - Ensures proper spacing and punctuation
    
    Args:
        text: Raw transcript text
        
    Returns:
        Cleaned and formatted text
    """
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Fix common transcription errors
    text = text.replace(" i ", " I ")
    text = text.replace(" im ", " I'm ")
    text = text.replace(" ive ", " I've ")
    text = text.replace(" id ", " I'd ")
    text = text.replace(" ill ", " I'll ")
    
    # Capitalize first letter of sentences
    text = '. '.join(s.capitalize() for s in text.split('. '))
    
    # Ensure proper spacing after punctuation
    text = re.sub(r'([.!?]),', r'\1', text)
    text = re.sub(r'([.!?])([^\s])', r'\1 \2', text)
    
    # Remove spaces before punctuation
    text = re.sub(r'\s+([.!?,])', r'\1', text)
    
    return text.strip()


def group_transcript_segments(transcript_list: List[Dict]) -> List[Dict]:
    """
    Group transcript segments into larger, meaningful chunks.
    Uses natural breaks and ensures proper formatting.
    """
    grouped_segments = []
    current_group = {
        'text': '',
        'start': 0,
        'duration': 0
    }
    
    for i, segment in enumerate(transcript_list):
        if i == 0:
            current_group['text'] = clean_and_format_text(segment['text'])
            current_group['start'] = segment['start']
            current_group['duration'] = segment['duration']
            continue
            
        prev_segment = transcript_list[i - 1]
        pause_duration = segment['start'] - (prev_segment['start'] + prev_segment['duration'])
        
        # Improved grouping logic
        should_start_new_group = (
            pause_duration > 2.0 or
            (pause_duration > 1.0 and 
             any(prev_segment['text'].strip().endswith(p) for p in '.!?')) or
            len(current_group['text']) > 300 or
            segment.get('new_paragraph', False)  # Some transcripts include paragraph markers
        )
        
        if should_start_new_group and current_group['text']:
            current_group['text'] = clean_and_format_text(current_group['text'])
            grouped_segments.append(current_group.copy())
            current_group = {
                'text': clean_and_format_text(segment['text']),
                'start': segment['start'],
                'duration': segment['duration']
            }
        else:
            # Add appropriate spacing between segments
            if not current_group['text'].endswith(('.', '!', '?', ',')):
                current_group['text'] += ' '
            current_group['text'] += segment['text']
            current_group['duration'] = (segment['start'] + segment['duration']) - current_group['start']
    
    # Add the last group
    if current_group['text']:
        current_group['text'] = clean_and_format_text(current_group['text'])
        grouped_segments.append(current_group)
    
    return grouped_segments


async def save_transcript(transcript_data: Dict, output_dir: str = None) -> str:
    """
    Save transcript data to a JSON file.
    
    Args:
        transcript_data: Dictionary containing transcript and metadata
        output_dir: Directory to save the transcript file (defaults to shared/data/transcripts in project root)
    
    Returns:
        str: Path to the saved file
    """
    # Set default output directory relative to project root
    if output_dir is None:
        # Get the project root directory (parent of youtube_transcripts)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_dir = os.path.join(project_root, 'shared', 'data', 'transcripts')

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename using timestamp and video ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = transcript_data.get('video_id', 'unknown')
    safe_title = transcript_data.get('title', video_id).replace(' ', '_').lower()
    
    # Create video-specific directory
    video_dir = os.path.join(output_dir, safe_title)
    os.makedirs(video_dir, exist_ok=True)
    
    # Create filename with timestamp and video ID
    filename = f"{timestamp}__transcript__{video_id}.json"
    filepath = os.path.join(video_dir, filename)
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)
    
    return filepath


async def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Fetch and save YouTube video transcripts')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--lang', default='en', help='Language code (default: en)')
    args = parser.parse_args()
    
    try:
        # Get transcript
        transcript_data = await get_transcript(args.url)
        
        # Save transcript
        filepath = await save_transcript(transcript_data)
        print(f"\nTranscript saved to: {filepath}")
        
        # Print first few segments
        print("\nFirst few segments of transcript:")
        for segment in transcript_data[:3]:
            print(f"\n[{formatTime(segment['start'])}]")
            print(segment['text'])
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        return 1
    
    return 0


def formatTime(seconds: float) -> str:
    """Format time in seconds to MM:SS format"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


if __name__ == '__main__':
    import sys
    sys.exit(asyncio.run(main())) 