"""
Vector Store Module

Handles storage and retrieval of vectorized content from YouTube transcripts and Reddit posts.
Uses ChromaDB for efficient similarity search.
"""

import chromadb
import nltk
from typing import List, Dict
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str = None):
        """Initialize the vector store with optional persistence."""
        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()
            
        # Create collections for different content types
        self.transcript_collection = self.client.get_or_create_collection(
            name="transcripts",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.reddit_collection = self.client.get_or_create_collection(
            name="reddit_posts",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize NLTK for text segmentation
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

    def segment_text(self, text: str, min_length: int = 100, max_length: int = 512) -> List[str]:
        """
        Segment text into semantic chunks using NLTK.
        
        Args:
            text: Text to segment
            min_length: Minimum segment length
            max_length: Maximum segment length
        """
        try:
            # Split into sentences
            sentences = nltk.sent_tokenize(text)
            
            segments = []
            current_segment = []
            current_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence)
                
                if current_length + sentence_length > max_length and current_segment:
                    # Add current segment if it meets minimum length
                    segment_text = ' '.join(current_segment)
                    if len(segment_text) >= min_length:
                        segments.append(segment_text)
                    current_segment = []
                    current_length = 0
                
                current_segment.append(sentence)
                current_length += sentence_length
            
            # Add final segment if it meets minimum length
            if current_segment:
                segment_text = ' '.join(current_segment)
                if len(segment_text) >= min_length:
                    segments.append(segment_text)
            
            return segments
            
        except Exception as e:
            logger.error(f"Error segmenting text: {str(e)}", exc_info=True)
            raise

    def enrich_metadata(self, metadata: Dict) -> Dict:
        """
        Enrich metadata with additional fields.
        
        Args:
            metadata: Original metadata dictionary
        """
        enriched = metadata.copy() if metadata else {}
        
        # Add timestamp if not present
        if 'timestamp' not in enriched:
            from datetime import datetime
            enriched['timestamp'] = datetime.now().isoformat()
            
        return enriched

    def add_transcript(self, video_id: str, segments: List[Dict], metadata: Dict = None) -> None:
        """
        Add a video transcript to the vector store.
        
        Args:
            video_id: YouTube video ID
            segments: List of transcript segments
            metadata: Additional metadata about the video
        """
        try:
            # Prepare metadata
            base_metadata = {
                'video_id': video_id,
                'type': 'transcript'
            }
            
            if metadata:
                base_metadata.update(metadata)
            
            base_metadata = self.enrich_metadata(base_metadata)
            
            # Process segments
            documents = []
            metadatas = []
            ids = []
            
            for i, segment in enumerate(segments):
                # Get text content
                text = segment.get('text', '').strip()
                if not text:
                    continue
                    
                # Add segment-specific metadata
                segment_metadata = base_metadata.copy()
                segment_metadata.update({
                    'start': segment.get('start', 0),
                    'duration': segment.get('duration', 0)
                })
                
                documents.append(text)
                metadatas.append(segment_metadata)
                ids.append(f"{video_id}_{i}")
            
            if documents:
                self.transcript_collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logger.info(f"Added transcript {video_id} to vector store with {len(documents)} segments")
            
        except Exception as e:
            logger.error(f"Error adding transcript to vector store: {str(e)}", exc_info=True)
            raise

    def add_reddit_post(self, post_id: str, content: Dict, metadata: Dict = None) -> None:
        """
        Add a Reddit post to the vector store.
        
        Args:
            post_id: Unique identifier for the Reddit post
            content: Dictionary containing post content and comments
            metadata: Additional metadata about the post
        """
        try:
            # Combine title and content
            full_text = f"{content['title']}\n\n{content.get('selftext', '')}"
            
            # Get segments from the main post
            post_segments = self.segment_text(full_text)
            
            # Process comments if available
            comment_segments = []
            if 'comments' in content:
                for comment in content['comments']:
                    comment_segments.extend(self.segment_text(comment['body']))
            
            # Combine all segments
            all_segments = post_segments + comment_segments
            
            # Prepare metadata
            base_metadata = {
                'post_id': post_id,
                'subreddit': content.get('subreddit', ''),
                'author': content.get('author', ''),
                'created_utc': content.get('created_utc', ''),
                'score': content.get('score', 0),
                'type': 'reddit_post'
            }
            
            if metadata:
                base_metadata.update(metadata)
                
            base_metadata = self.enrich_metadata(base_metadata)
            
            # Add to collection
            self.reddit_collection.add(
                documents=all_segments,
                metadatas=[base_metadata for _ in all_segments],
                ids=[f"{post_id}_{i}" for i in range(len(all_segments))]
            )
            
            logger.info(f"Added Reddit post {post_id} to vector store with {len(all_segments)} segments")
            
        except Exception as e:
            logger.error(f"Error adding Reddit post to vector store: {str(e)}", exc_info=True)
            raise

    def search(self, query: str, n_results: int = 5, content_type: str = "all") -> List[Dict]:
        """
        Search for similar content across all collections or specific content type.
        
        Args:
            query: Search query
            n_results: Number of results to return
            content_type: Type of content to search ("all", "transcript", or "reddit")
        """
        try:
            results = []
            
            if content_type in ["all", "transcript"]:
                transcript_results = self.transcript_collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
                results.extend([
                    {
                        'content': doc,
                        'metadata': meta,
                        'distance': dist,
                        'type': 'transcript'
                    }
                    for doc, meta, dist in zip(
                        transcript_results['documents'][0],
                        transcript_results['metadatas'][0],
                        transcript_results['distances'][0]
                    )
                ])
            
            if content_type in ["all", "reddit"]:
                reddit_results = self.reddit_collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
                results.extend([
                    {
                        'content': doc,
                        'metadata': meta,
                        'distance': dist,
                        'type': 'reddit'
                    }
                    for doc, meta, dist in zip(
                        reddit_results['documents'][0],
                        reddit_results['metadatas'][0],
                        reddit_results['distances'][0]
                    )
                ])
            
            # Sort by distance
            results.sort(key=lambda x: x['distance'])
            return results[:n_results]
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}", exc_info=True)
            raise

    def get_video_segments(self, video_id: str) -> List[Dict]:
        """
        Retrieve all segments for a specific video.
        
        Args:
            video_id: YouTube video ID
        """
        try:
            results = self.transcript_collection.get(
                where={"video_id": video_id}
            )
            
            return [
                {
                    'content': doc,
                    'metadata': meta
                }
                for doc, meta in zip(results['documents'], results['metadatas'])
            ]
            
        except Exception as e:
            logger.error(f"Error retrieving video segments: {str(e)}", exc_info=True)
            raise

    def get_reddit_post(self, post_id: str) -> List[Dict]:
        """
        Retrieve all segments for a specific Reddit post.
        
        Args:
            post_id: ID of the Reddit post
        """
        try:
            results = self.reddit_collection.get(
                where={"post_id": post_id}
            )
            
            return [
                {
                    'content': doc,
                    'metadata': meta
                }
                for doc, meta in zip(results['documents'], results['metadatas'])
            ]
            
        except Exception as e:
            logger.error(f"Error retrieving Reddit post: {str(e)}", exc_info=True)
            raise

    def search_reddit(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search only Reddit posts.
        
        Args:
            query: Search query
            n_results: Number of results to return
        """
        return self.search(query, n_results, content_type="reddit") 