from vector_store import VectorStore
import os
import json
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"[{minutes:02d}:{seconds:02d}]"

def print_search_results(results: List[Dict], query: str):
    """Pretty print search results."""
    print(f"\nQuery: {query}")
    print("-" * 80)
    print()
    
    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"Video ID: {result['metadata']['video_id']}")
        print(f"Timestamp: {format_timestamp(result['metadata']['start'])}")
        print(f"Text: {result['text']}")
        print(f"Relevance Score: {result['relevance_score']:.3f}")
        print("-" * 40)

def run_search_test(vector_store: VectorStore, query: str, description: str, n_results: int = 3):
    """Run a search test with the given query and print results."""
    logger.info(f"\nTest Case: {description}")
    results = vector_store.search(query, n_results=n_results)
    print_search_results(results, query)

def test_vector_store():
    """Test the vector store with various queries."""
    try:
        # Initialize vector store with persist_directory in parent directory
        persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chroma_db')
        vector_store = VectorStore(persist_directory=persist_directory)
        
        # Test for Claude and MCP content
        run_search_test(
            vector_store,
            "What is discussed about Claude and MCP setup in the tutorial?",
            "Specific content search - Claude and MCP setup",
            n_results=5
        )
        
        # Test 1: General semantic search
        run_search_test(
            vector_store,
            "What are the main benefits and use cases of Pydantic in Python applications?",
            "General semantic search - Pydantic benefits"
        )
        
        # Test 2: Technical concept search
        run_search_test(
            vector_store,
            "Explain the process of AI model quantization and its impact on performance",
            "Technical concept search - AI Quantization"
        )
        
        # Test 3: Tool recommendations
        run_search_test(
            vector_store,
            "What are the most important Python libraries for building AI applications and why?",
            "Tool recommendations - Python AI libraries"
        )
        
        # Test 4: Best practices
        run_search_test(
            vector_store,
            "What are the key best practices and tips for fine-tuning large language models effectively?",
            "Best practices - LLM fine-tuning",
            n_results=4
        )
        
        # Test 5: Implementation search
        run_search_test(
            vector_store,
            "How can you build and implement AI agents using Python? What are the key components?",
            "Implementation search - AI Agents in Python"
        )
        
        # Test 6: Get video segments
        logger.info("\nTest Case: Full video segment retrieval")
        video_id = "pydantic_tutorial_solving_python_s_biggest_problem"
        segments = vector_store.get_video_segments(video_id)
        
        print(f"\nRetrieved {len(segments)} segments from video: {video_id}\n")
        print("First three segments:\n")
        
        for i, segment in enumerate(segments[:3], 1):
            print(f"Segment {i}:")
            print(f"Timestamp: {format_timestamp(segment['start'])}")
            print(f"Text: {segment['text']}")
            print(f"Duration: {segment['duration']:.2f}s\n")
        
        # Test 7: Cross-video concept search
        run_search_test(
            vector_store,
            "What are different approaches to working with LLMs and AI models in production?",
            "Cross-video concept search - LLM/AI implementation approaches",
            n_results=5
        )
        
    except Exception as e:
        logger.error(f"Error testing vector store: {str(e)}")

if __name__ == "__main__":
    test_vector_store() 