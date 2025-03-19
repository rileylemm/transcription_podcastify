import requests
from typing import Dict, Any
import json
from datetime import datetime

def extract_reddit_post(url: str) -> Dict[str, Any]:
    # Add .json to the URL to get JSON response
    if not url.endswith('/'):
        url += '/'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # First try to get the JSON version of the post
        json_url = url + '.json'
        response = requests.get(json_url, headers=headers)
        response.raise_for_status()
        
        json_data = response.json()
        post_data = json_data[0]['data']['children'][0]['data']
        
        # Extract relevant information
        extracted_data = {
            'title': post_data.get('title'),
            'author': post_data.get('author'),
            'subreddit': post_data.get('subreddit'),
            'score': post_data.get('score'),
            'upvote_ratio': post_data.get('upvote_ratio'),
            'created_utc': datetime.fromtimestamp(post_data.get('created_utc')).isoformat(),
            'content': post_data.get('selftext'),
            'url': url,
            'is_self': post_data.get('is_self'),
            'permalink': f"https://reddit.com{post_data.get('permalink')}",
            'num_comments': post_data.get('num_comments')
        }
        
        return extracted_data
        
    except requests.RequestException as e:
        return {'error': f"Failed to fetch Reddit post: {str(e)}"}
    except (KeyError, IndexError) as e:
        return {'error': f"Failed to parse Reddit data: {str(e)}"}
    except Exception as e:
        return {'error': f"Unexpected error: {str(e)}"}

if __name__ == "__main__":
    test_url = "https://www.reddit.com/r/PromptEngineering/comments/1j8m0rs/the_ultimate_fucking_guide_to_prompt_engineering/"
    
    result = extract_reddit_post(test_url)
    print(json.dumps(result, indent=2)) 