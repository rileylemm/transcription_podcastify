"""
Transcript Analysis Module

Provides AI-powered analysis tools for extracting valuable information from YouTube transcripts.
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

class TranscriptAnalyzer:
    def __init__(self, openai_api_key: Optional[str] = None, data_dir: Optional[str] = None):
        """
        Initialize the analyzer with optional OpenAI API key.
        
        Args:
            openai_api_key: Optional OpenAI API key for GPT models
            data_dir: Directory to store transcript data and analysis results
        """
        self.mistral_api_url = os.getenv('MISTRAL_API_URL', 'http://mistral:11434')
        self.openai_api_key = openai_api_key
        
        # Use provided data_dir or default to youtube_transcripts/data
        if data_dir is None:
            self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        else:
            self.data_dir = data_dir
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        if openai_api_key:
            self.openai_client = AsyncOpenAI(
                api_key=openai_api_key,
                timeout=60.0  # Increase timeout for longer transcripts
            )
        else:
            self.openai_client = None
        
    def _get_video_dir(self, video_title: str) -> str:
        """Get or create directory for video data."""
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join(self.data_dir, safe_title)
        os.makedirs(video_dir, exist_ok=True)
        return video_dir

    async def save_original_transcript(self, transcript: List[Dict], video_title: str) -> str:
        """Save original transcript to JSON file."""
        try:
            video_dir = self._get_video_dir(video_title)
            filename = generate_transcript_filename(video_title)
            filepath = os.path.join(video_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving transcript: {str(e)}", exc_info=True)
            raise

    async def save_analysis(self, analysis_content: str, video_title: str, analysis_type: str, model: str = "mistral") -> str:
        """Save analysis results to JSON file."""
        try:
            video_dir = self._get_video_dir(video_title)
            filename = generate_analysis_filename(video_title, analysis_type, model)
            filepath = os.path.join(video_dir, filename)
            
            analysis_data = {
                'type': analysis_type,
                'model': model,
                'content': analysis_content,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving analysis: {str(e)}", exc_info=True)
            raise

    async def analyze_with_mistral(self, transcript: List[Dict], analysis_type: str) -> str:
        """Analyze the transcript using Mistral model."""
        # Convert transcript segments to text with timestamps
        full_text = ""
        for segment in transcript:
            minutes = int(segment['start'] // 60)
            seconds = int(segment['start'] % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}] "
            full_text += timestamp + segment['text'] + "\n\n"

        system_messages = {
            "technical_summary": """You are a technical documentation expert tasked with analyzing video transcripts and creating comprehensive, well-structured summaries. Follow these requirements exactly:

1. FORMAT:
- Start with a high-level overview (2-3 sentences)
- Break content into clear sections with descriptive headings
- Use bullet points for key concepts and features
- Include code blocks and technical examples exactly as presented
- Maintain consistent formatting throughout

2. CONTENT REQUIREMENTS:
- Preserve all technical accuracy and depth from the original
- Include all specific examples, numbers, and code snippets
- Use consistent technical terminology throughout
- Explicitly connect related concepts and ideas
- Remove only advertising and filler content

3. EXAMPLE OUTPUT:
# Overview
[2-3 sentence technical overview]

## Core Concepts
- [Technical concept 1]
  - [Specific details]
  - [Example or code if provided]
- [Technical concept 2]
  ...

## Implementation Details
[Technical details section with code examples]

## Key Examples
[Specific examples from the content]

4. VALIDATION:
- Verify all technical information is preserved
- Check terminology consistency
- Confirm all key examples are included
- Ensure logical flow between sections

Now analyze the following transcript, maintaining all technical depth while following the format above:

{transcript}""",
            "code_snippets": (
                "Extract and analyze code related to LLM implementation and usage. For each code snippet:\n"
                "1. Identify the specific LLM-related functionality (e.g., prompt engineering, API calls, etc.)\n"
                "2. Explain the technical implementation details\n"
                "3. Highlight best practices for LLM integration\n"
                "4. Note any performance considerations or limitations\n"
                "5. Suggest potential improvements or alternatives\n\n"
                "Focus on code that directly interfaces with or supports LLM functionality."
            ),
            "tools_and_resources": (
                "Identify all LLM-related tools, libraries, and resources mentioned. For each:\n"
                "1. Specific role in LLM implementation or usage\n"
                "2. Technical capabilities and limitations\n"
                "3. Integration requirements and compatibility\n"
                "4. Performance characteristics and scaling considerations\n"
                "5. Alternatives and trade-offs discussed\n\n"
                "Focus on tools that are directly relevant to LLM development and deployment."
            ),
            "key_workflows": (
                "Document workflows and processes specific to LLM implementation and usage:\n"
                "1. Step-by-step procedures for LLM integration\n"
                "2. Best practices for prompt engineering\n"
                "3. Testing and validation approaches\n"
                "4. Performance optimization techniques\n"
                "5. Error handling and edge cases\n\n"
                "Emphasize practical, actionable workflows for LLM development."
            ),
            "full_context": """You're having a conversation with someone who missed this video and wants to know everything important from it. Tell them about it as if you watched it yourself, keeping all the valuable content while making it engaging and easy to follow.

Keep everything that matters:
• Technical details and explanations
• Examples and demonstrations
• Personal insights and experiences
• Practical tips and advice
• The natural flow of ideas

Skip the non-essential parts:
• Promotional messages
• Like/subscribe reminders
• Repeated information
• Technical issues
• Off-topic tangents

Start by telling them what the video is about, then share the content in a natural way, as if you're having a conversation. Include timestamps for important points so they can find specific parts if needed.

Remember: Don't summarize - help them experience the full value of the video in written form.

Here's the transcript - tell me about this video:

{transcript}""",
        }
        
        system_msg = system_messages.get(analysis_type, system_messages["technical_summary"])
        prompt = f"{system_msg}\n\nTranscript:\n{full_text}\n\nAnalysis:"
        
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

    async def analyze_with_gpt(self, transcript: List[Dict], analysis_type: str) -> str:
        """Analyze the transcript using OpenAI's GPT model."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not provided")

        # Convert transcript segments to text with timestamps
        full_text = ""
        for segment in transcript:
            minutes = int(segment['start'] // 60)
            seconds = int(segment['start'] % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}] "
            full_text += timestamp + segment['text'] + "\n\n"
            
        client = AsyncOpenAI(
            api_key=self.openai_api_key,
            timeout=60.0
        )
        
        system_messages = {
            "technical_summary": (
                "You are an expert in AI and LLM technology analysis. Your task is to create a focused summary of the video's technical content about LLMs and AI, specifically addressing:\n"
                "1. Core LLM/AI concepts and techniques discussed\n"
                "2. Specific implementation details and best practices\n"
                "3. Unique insights about LLM usage and capabilities\n"
                "4. Practical applications and limitations mentioned\n"
                "5. Technical challenges and solutions presented\n\n"
                "Format the output with clear headings and concise bullet points.\n"
                "Focus only on the most valuable technical insights about LLM technology."
            ),
            "code_snippets": (
                "Extract and analyze code related to LLM implementation and usage. For each code snippet:\n"
                "1. Identify the specific LLM-related functionality (e.g., prompt engineering, API calls, etc.)\n"
                "2. Explain the technical implementation details\n"
                "3. Highlight best practices for LLM integration\n"
                "4. Note any performance considerations or limitations\n"
                "5. Suggest potential improvements or alternatives\n\n"
                "Focus on code that directly interfaces with or supports LLM functionality."
            ),
            "tools_and_resources": (
                "Identify all LLM-related tools, libraries, and resources mentioned. For each:\n"
                "1. Specific role in LLM implementation or usage\n"
                "2. Technical capabilities and limitations\n"
                "3. Integration requirements and compatibility\n"
                "4. Performance characteristics and scaling considerations\n"
                "5. Alternatives and trade-offs discussed\n\n"
                "Focus on tools that are directly relevant to LLM development and deployment."
            ),
            "key_workflows": (
                "Document workflows and processes specific to LLM implementation and usage:\n"
                "1. Step-by-step procedures for LLM integration\n"
                "2. Best practices for prompt engineering\n"
                "3. Testing and validation approaches\n"
                "4. Performance optimization techniques\n"
                "5. Error handling and edge cases\n\n"
                "Emphasize practical, actionable workflows for LLM development."
            ),
            "full_context": """You're having a conversation with someone who missed this video and wants to know everything important from it. Tell them about it as if you watched it yourself, keeping all the valuable content while making it engaging and easy to follow.

Keep everything that matters:
• Technical details and explanations
• Examples and demonstrations
• Personal insights and experiences
• Practical tips and advice
• The natural flow of ideas

Skip the non-essential parts:
• Promotional messages
• Like/subscribe reminders
• Repeated information
• Technical issues
• Off-topic tangents

Start by telling them what the video is about, then share the content in a natural way, as if you're having a conversation. Include timestamps for important points so they can find specific parts if needed.

Remember: Don't summarize - help them experience the full value of the video in written form.

Here's the transcript - tell me about this video:

{transcript}""",
        }
        
        system_msg = system_messages.get(analysis_type, system_messages["technical_summary"])
        
        try:
            response = await client.chat.completions.create(
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

    async def analyze_transcript(self, 
                               transcript: List[Dict], 
                               analysis_type: str,
                               video_title: str,
                               model: str = "mistral") -> AnalysisResult:
        """
        Main analysis method that routes to appropriate model.
        
        Args:
            transcript: List of transcript segments
            analysis_type: Type of analysis to perform
            video_title: Title of the video
            model: Model to use ('mistral' or 'gpt')
        """
        try:
            # Prevent Mistral from being used for full context analysis
            if model == "mistral" and analysis_type == "full_context":
                return AnalysisResult(
                    success=False,
                    content="",
                    model_used=model,
                    error="Full Context analysis is only available with GPT"
                )
            
            # Save the original transcript first
            await self.save_original_transcript(transcript, video_title)
            
            # Get analysis based on selected model
            if model == "mistral":
                content = await self.analyze_with_mistral(transcript, analysis_type)
            elif model == "gpt":
                content = await self.analyze_with_gpt(transcript, analysis_type)
            else:
                return AnalysisResult(
                    success=False,
                    content="",
                    model_used=model,
                    error=f"Unknown model: {model}"
                )

            # Save the analysis result
            await self.save_analysis(content, video_title, analysis_type, model)
            
            return AnalysisResult(
                success=True,
                content=content,
                model_used=model
            )
            
        except Exception as e:
            logger.error(f"Error analyzing transcript: {str(e)}", exc_info=True)
            return AnalysisResult(
                success=False,
                content="",
                model_used=model,
                error=str(e)
            )

    async def chat_with_mistral(self, messages: List[Dict]) -> str:
        """Chat with Mistral model using provided messages."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.mistral_api_url}/api/chat",
                    json={
                        "model": "mistral-base",
                        "messages": messages,
                        "stream": False
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'message' in result:
                            return result['message']['content']
                        else:
                            logger.error(f"Unexpected API response format: {result}")
                            raise Exception("Unexpected API response format")
                    else:
                        error_text = await response.text()
                        raise Exception(f"Mistral API error: {error_text}")
                        
        except Exception as e:
            logger.error(f"Error in chat_with_mistral: {str(e)}")
            raise Exception(f"Error chatting with Mistral: {str(e)}") 