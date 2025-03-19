import requests
from typing import Dict, Any
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditExtractor:
    """Class for extracting content from Reddit posts."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def extract_post_id(self, url: str) -> str:
        """Extract post ID from Reddit URL."""
        try:
            # Remove trailing slash if present
            if url.endswith('/'):
                url = url[:-1]
            # Extract ID from URL
            return url.split('/comments/')[1].split('/')[0]
        except Exception as e:
            logger.error(f"Failed to extract post ID from URL {url}: {str(e)}")
            raise ValueError(f"Invalid Reddit URL format: {url}")
    
    def extract_post(self, url: str) -> Dict[str, Any]:
        """Extract data from a Reddit post."""
        try:
            # Validate and clean URL
            if not url:
                raise ValueError("URL cannot be empty")
                
            # Ensure URL ends with slash for .json append
            if not url.endswith('/'):
                url += '/'
            
            # Get JSON version of the post
            json_url = url + '.json'
            logger.info(f"Fetching Reddit post from: {json_url}")
            
            try:
                response = requests.get(json_url, headers=self.headers, timeout=10)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {json_url}: {str(e)}")
                if response.status_code == 403:
                    raise ValueError("Access forbidden. The post may be private or deleted.")
                elif response.status_code == 404:
                    raise ValueError("Post not found. The URL may be invalid.")
                else:
                    raise ValueError(f"Failed to fetch post: HTTP {response.status_code}")
            
            try:
                json_data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                raise ValueError("Invalid response from Reddit")
            
            if not json_data or not isinstance(json_data, list) or len(json_data) < 1:
                raise ValueError("Invalid response format from Reddit")
            
            try:
                post_data = json_data[0]['data']['children'][0]['data']
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to extract post data from response: {str(e)}")
                raise ValueError("Could not find post data in response")
            
            # Extract relevant information
            extracted_data = {
                'title': post_data.get('title'),
                'author': post_data.get('author'),
                'subreddit': post_data.get('subreddit'),
                'score': post_data.get('score'),
                'upvote_ratio': post_data.get('upvote_ratio'),
                'created_utc': post_data.get('created_utc'),
                'selftext': post_data.get('selftext'),
                'url': url,
                'is_self': post_data.get('is_self'),
                'permalink': f"https://reddit.com{post_data.get('permalink')}",
                'num_comments': post_data.get('num_comments'),
                'id': self.extract_post_id(url)
            }
            
            # Validate required fields
            if not extracted_data['title']:
                raise ValueError("Post title is missing")
            
            logger.info(f"Successfully extracted Reddit post: {extracted_data['title']}")
            return extracted_data
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error extracting post: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to extract post data: {str(e)}") 