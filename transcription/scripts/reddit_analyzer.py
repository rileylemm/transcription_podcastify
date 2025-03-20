"""
Reddit Post Analysis Module

Provides AI-powered analysis tools for extracting insights from Reddit posts.
Supports both local Ollama models and OpenAI's GPT models.
"""

import json
import requests
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import os
import asyncio
from pathlib import Path
from datetime import datetime
from openai import AsyncOpenAI
import aiohttp
import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Container for analysis results"""
    success: bool
    content: Union[Dict, List, str]
    model_used: str
    error: Optional[str] = None

def sanitize_filename(name):
    """Convert a string to a safe filename."""
    safe_name = "".join(c if c.isalnum() else '_' for c in name)
    safe_name = '_'.join(filter(None, safe_name.split('_')))
    return safe_name.lower()

def get_timestamp_prefix():
    """Get current timestamp in YYYYMMDD_HHMMSS format."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def generate_reddit_filename(post_id, analysis_type, model):
    """Generate consistent filename for Reddit analyses."""
    safe_id = sanitize_filename(post_id)
    safe_type = sanitize_filename(analysis_type)
    safe_model = sanitize_filename(model)
    return f"{get_timestamp_prefix()}__reddit__{safe_type}__{safe_model}__{safe_id}.json"

def generate_post_filename(post_id):
    """Generate consistent filename for original post content."""
    safe_id = sanitize_filename(post_id)
    return f"{get_timestamp_prefix()}__post__{safe_id}.json"

def generate_metadata_filename(post_id):
    """Generate consistent filename for post metadata."""
    safe_id = sanitize_filename(post_id)
    return f"{get_timestamp_prefix()}__metadata__{safe_id}.json"

class RedditAnalyzer:
    def __init__(self, openai_api_key: Optional[str] = None, data_dir: Optional[str] = None):
        """Initialize the analyzer with optional OpenAI API key and data directory."""
        self.mistral_api_url = os.getenv('MISTRAL_API_URL', 'http://mistral:11434')
        self.openai_api_key = openai_api_key
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        if openai_api_key:
            self.openai_client = AsyncOpenAI(
                api_key=openai_api_key,
                timeout=60.0
            )
        else:
            self.openai_client = None

    def _get_post_dir(self, post_id: str) -> str:
        """Get or create directory for post data."""
        # Get the post directory from data/reddit/[post_dir]
        reddit_base_dir = os.path.join(self.data_dir, 'reddit')
        index_path = os.path.join(reddit_base_dir, 'post_index.json')
        
        # Load the index to get the post directory name
        with open(index_path, 'r', encoding='utf-8') as f:
            post_index = json.load(f)
            
        if post_id not in post_index:
            raise ValueError(f"Post {post_id} not found in index")
            
        post_info = post_index[post_id]
        post_dir = os.path.join(reddit_base_dir, post_info['dir_name'])
        os.makedirs(post_dir, exist_ok=True)
        return post_dir

    async def save_analysis(self, analysis_content: str, post_id: str, analysis_type: str, model: str = "mistral") -> str:
        """Save analysis results to JSON file."""
        try:
            # Get the post directory from data/reddit/[post_dir]
            reddit_base_dir = os.path.join(self.data_dir, 'reddit')
            index_path = os.path.join(reddit_base_dir, 'post_index.json')
            
            # Load the index to get the post directory name
            with open(index_path, 'r', encoding='utf-8') as f:
                post_index = json.load(f)
                
            if post_id not in post_index:
                raise ValueError(f"Post {post_id} not found in index")
                
            post_info = post_index[post_id]
            post_dir = os.path.join(reddit_base_dir, post_info['dir_name'])
            
            # Generate filename for the analysis
            filename = f"{get_timestamp_prefix()}__analysis__{analysis_type}__{model}__{post_id}.json"
            filepath = os.path.join(post_dir, filename)
            
            analysis_data = {
                'type': analysis_type,
                'model': model,
                'content': analysis_content,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'analysis_type': analysis_type,
                    'model': model,
                    'post_id': post_id
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving analysis: {str(e)}", exc_info=True)
            raise

    async def save_post_data(self, post_data: Dict) -> str:
        """Save original post content to JSON file."""
        try:
            post_dir = self._get_post_dir(post_data['id'])
            filename = generate_post_filename(post_data['id'])
            filepath = os.path.join(post_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(post_data, f, ensure_ascii=False, indent=2)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving post data: {str(e)}", exc_info=True)
            raise

    async def save_post_metadata(self, post_data: Dict) -> str:
        """Save post metadata to JSON file."""
        try:
            post_dir = self._get_post_dir(post_data['id'])
            filename = generate_metadata_filename(post_data['id'])
            filepath = os.path.join(post_dir, filename)
            
            # Extract metadata fields
            metadata = {
                'id': post_data['id'],
                'title': post_data['title'],
                'subreddit': post_data.get('subreddit', ''),
                'author': post_data.get('author', ''),
                'score': post_data.get('score', 0),
                'upvote_ratio': post_data.get('upvote_ratio', 0),
                'num_comments': post_data.get('num_comments', 0),
                'created_utc': post_data.get('created_utc', ''),
                'url': post_data.get('url', ''),
                'permalink': post_data.get('permalink', '')
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving post metadata: {str(e)}", exc_info=True)
            raise

    def create_post_segments(self, post_data: Dict) -> List[Dict]:
        """Create structured segments from post content and comments."""
        segments = []
        
        # Add post title and content as first segments
        title_segment = {
            'text': post_data['title'],
            'type': 'title',
            'author': post_data.get('author', ''),
            'timestamp': post_data.get('created_utc', '')
        }
        segments.append(title_segment)
        
        if post_data.get('selftext'):
            content_segment = {
                'text': post_data['selftext'],
                'type': 'post_content',
                'author': post_data.get('author', ''),
                'timestamp': post_data.get('created_utc', '')
            }
            segments.append(content_segment)
        
        # Add comments as segments
        if 'comments' in post_data:
            for comment in post_data['comments']:
                comment_segment = {
                    'text': comment['body'],
                    'type': 'comment',
                    'author': comment.get('author', ''),
                    'timestamp': comment.get('created_utc', '')
                }
                segments.append(comment_segment)
        
        return segments

    async def analyze_with_mistral(self, post_data: Dict, analysis_type: str) -> str:
        """Analyze the Reddit post using Mistral model."""
        # Combine post title and content
        full_text = f"Title: {post_data['title']}\n\nContent:\n{post_data.get('selftext', '')}"
        
        # Add comments if available
        if 'comments' in post_data:
            full_text += "\n\nTop Comments:\n"
            for comment in post_data['comments'][:5]:  # Include top 5 comments
                full_text += f"\n---\n{comment['body']}\n"

        system_messages = {
            "sentiment": """Analyze the sentiment of this Reddit post and its comments. Format your response in markdown with the following sections:

# Overall Sentiment
- Overall tone and mood of the post
- Key emotional indicators
- Writing style and presentation

# User Engagement
- Comment patterns and themes
- Interaction quality
- Community response

# Key Observations
- Notable sentiment shifts
- Standout comments or reactions
- Contextual factors

Ensure each section uses proper markdown formatting with headers (#) and bullet points (-).""",
            
            "keywords": """Extract and analyze key topics and themes from this Reddit post. Include:
1. Main keywords and their frequency
2. Important phrases and concepts
3. Technical terms used
4. Recurring themes in comments

Present the findings in a structured format with examples.""",
            
            "engagement": """Analyze the engagement patterns in this Reddit post. Consider:
1. Upvote patterns
2. Comment quantity and quality
3. User interaction types
4. Discussion depth and breadth

Provide detailed metrics and insights about the post's engagement.""",
            
            "summary": """Create a comprehensive summary of this Reddit post and its discussion. Include:
1. Main points and arguments
2. Key insights from comments
3. Notable disagreements or debates
4. Valuable resources shared

Present a well-structured summary that captures the essence of the discussion.""",
            
            "top_comments": """Analyze the most impactful comments in this Reddit post. Focus on:
1. Most upvoted comments
2. Most controversial comments
3. Comments with valuable insights
4. Expert contributions

Provide detailed analysis of the most significant comments.""",

            "tools_workflow": """Extract and analyze tools, workflows, and methodologies mentioned in this AI/LLM/coding discussion. Focus on:
1. Software tools and libraries mentioned
2. Development workflows and processes
3. Best practices and methodologies
4. Implementation details and setup instructions
5. Integration patterns and architecture decisions

Present a structured analysis of the technical implementation details.""",

            "prompting_patterns": """Analyze prompting patterns and techniques discussed in this LLM-related content. Extract:
1. Prompt engineering techniques
2. System message patterns
3. Chain of thought and reasoning strategies
4. Context window optimization methods
5. Model-specific prompting tips

Provide a detailed analysis of prompting strategies and their applications.""",

            "code_review": """Perform a technical analysis of any code or pseudocode shared. Focus on:
1. Implementation patterns and design choices
2. Error handling and edge cases
3. Performance considerations
4. Best practices followed or suggested
5. Potential improvements or alternatives suggested

Present a structured review of the technical implementation."""
        }
        
        system_msg = system_messages.get(analysis_type, system_messages["summary"])
        prompt = f"{system_msg}\n\nPost Content:\n{full_text}\n\nAnalysis:"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.mistral_api_url}/api/generate",
                    json={
                        "model": "mistral",
                        "prompt": prompt,
                        "stream": False
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['response'].strip()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Mistral API error: {error_text}")
                        
        except Exception as e:
            raise Exception(f"Error analyzing with Mistral: {str(e)}")

    async def analyze_with_gpt(self, post_data: Dict, analysis_type: str) -> str:
        """Analyze the Reddit post using OpenAI's GPT model."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not provided")

        # Combine post title and content
        full_text = f"Title: {post_data['title']}\n\nContent:\n{post_data.get('selftext', '')}"
        
        # Add comments if available
        if 'comments' in post_data:
            full_text += "\n\nTop Comments:\n"
            for comment in post_data['comments'][:5]:  # Include top 5 comments
                full_text += f"\n---\n{comment['body']}\n"
            
        system_messages = {
            "sentiment": """You are an expert in sentiment analysis. Analyze this Reddit post and its comments for:
1. Overall emotional tone
2. Sentiment patterns
3. User reactions
4. Emotional triggers
Provide a detailed analysis with examples.""",
            
            "keywords": """You are an expert in content analysis. Extract and analyze from this Reddit post:
1. Key topics and themes
2. Important technical terms
3. Recurring concepts
4. Significant phrases
Present your findings in a structured format.""",
            
            "engagement": """You are an expert in social media engagement analysis. Examine this Reddit post for:
1. Engagement metrics
2. User interaction patterns
3. Discussion quality
4. Community response
Provide detailed insights with supporting data.""",
            
            "summary": """You are an expert in content summarization. Create a comprehensive summary of:
1. Main discussion points
2. Key insights
3. Notable debates
4. Valuable resources
Present a well-structured summary of the entire discussion.""",
            
            "top_comments": """You are an expert in community discussion analysis. Analyze the comments for:
1. Most valuable contributions
2. Expert insights
3. Controversial points
4. Community consensus
Provide detailed analysis of significant comments.""",

            "tools_workflow": """You are an expert in AI/ML development workflows and tooling. Analyze this discussion for:
1. Technical tools and frameworks mentioned
2. Development workflows and methodologies
3. Infrastructure and deployment patterns
4. Best practices and optimization techniques
5. Integration strategies and architectural decisions

Extract and structure all technical implementation details, providing context for each tool and workflow mentioned.""",

            "prompting_patterns": """You are an expert in LLM prompt engineering and optimization. Analyze this content for:
1. Advanced prompting techniques and patterns
2. System message design strategies
3. Chain of thought and reasoning frameworks
4. Context window management methods
5. Model-specific optimization approaches

Provide detailed analysis of prompting strategies with practical examples and implementation notes.""",

            "code_review": """You are an expert in technical code review and software architecture. Analyze the shared code and implementation details for:
1. Design patterns and architectural choices
2. Error handling and edge case management
3. Performance optimization opportunities
4. Best practices adherence
5. Alternative approaches and improvements

Present a comprehensive technical review with specific recommendations."""
        }
        
        system_msg = system_messages.get(analysis_type, system_messages["summary"])
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": full_text}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"Error analyzing with GPT: {str(e)}")

    async def analyze_reddit_post(self, 
                                post_data: Dict,
                                analysis_type: str,
                                model: str = "mistral",
                                vector_store = None) -> AnalysisResult:
        """
        Main analysis method that routes to appropriate model.
        
        Args:
            post_data: Dictionary containing Reddit post data
            analysis_type: Type of analysis to perform
            model: Model to use ('mistral' or 'gpt')
            vector_store: Optional VectorStore instance for content vectorization
        """
        try:
            # Save the original post data and metadata
            await self.save_post_data(post_data)
            await self.save_post_metadata(post_data)
            
            # Add to vector store if provided
            if vector_store:
                try:
                    vector_store.add_reddit_post(post_data)
                    logger.info(f"Added post {post_data['id']} to vector store")
                except Exception as e:
                    logger.error(f"Error adding post to vector store: {str(e)}")
                    # Continue execution even if vectorization fails
            
            # Get analysis based on selected model
            if model == "mistral":
                content = await self.analyze_with_mistral(post_data, analysis_type)
            elif model == "gpt":
                content = await self.analyze_with_gpt(post_data, analysis_type)
            else:
                return AnalysisResult(
                    success=False,
                    content="",
                    model_used=model,
                    error=f"Unknown model: {model}"
                )

            # Save the analysis result
            await self.save_analysis(content, post_data['id'], analysis_type, model)
            
            # Add analysis to vector store if provided
            if vector_store:
                try:
                    analysis_doc = {
                        'id': post_data['id'],
                        'title': post_data['title'],
                        'content': content,
                        'type': f'analysis_{analysis_type}',
                        'model': model
                    }
                    vector_store.add_reddit_post(analysis_doc)
                    logger.info(f"Added analysis to vector store for post {post_data['id']}")
                except Exception as e:
                    logger.error(f"Error adding analysis to vector store: {str(e)}")
                    # Continue execution even if vectorization fails
            
            return AnalysisResult(
                success=True,
                content=content,
                model_used=model
            )
            
        except Exception as e:
            logger.error(f"Error analyzing Reddit post: {str(e)}", exc_info=True)
            return AnalysisResult(
                success=False,
                content="",
                model_used=model,
                error=str(e)
            ) 