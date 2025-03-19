# Vector Store Implementation

## Overview

The Vector Store is a key component of the YouTube Transcript Analyzer that enables efficient semantic search across transcript segments. It uses ChromaDB as the underlying vector database and the BGE-M3 embedding model for generating embeddings.

## Files

- `scripts/vector_store.py`: Main implementation of the VectorStore class
- `scripts/migrate_to_vector_store.py`: Utility for migrating existing transcript data to the vector store
- `scripts/test_vector_store.py`: Test suite for verifying vector store functionality

## Usage

### Initialization

```python
from scripts.vector_store import VectorStore

# Initialize with default settings
vector_store = VectorStore()

# Or specify a custom persistence directory
vector_store = VectorStore(persist_directory="path/to/chroma_db")
```

### Adding Transcripts

```python
# Add transcript segments to the vector store
video_id = "video_identifier"
transcript_segments = [
    {"text": "Segment text", "start": 0.0, "duration": 5.0},
    # More segments...
]

vector_store.add_transcript(video_id, transcript_segments)
```

### Searching

```python
# Search for relevant segments
results = vector_store.search(
    query="What are the benefits of using Pydantic?",
    n_results=5
)

# Search with metadata filters
results = vector_store.search(
    query="Python AI libraries",
    n_results=3,
    filter_metadata={"video_id": "specific_video_id"}
)
```

### Retrieving Video Segments

```python
# Get all segments for a specific video
segments = vector_store.get_video_segments("video_id")
```

### Deleting Videos

```python
# Delete a video and all its segments
vector_store.delete_video("video_id")
```

## Implementation Details

### Segment Processing

The VectorStore processes transcript segments in batches, enriching them with metadata and generating unique IDs. Each segment is assigned a globally unique index to ensure proper ordering and retrieval.

### Content Types

The VectorStore can detect different content types in transcript segments:
- `code`: Code snippets and commands
- `technical`: Technical explanations
- `general`: General discussion

### Context Handling

For better search results, the VectorStore combines segments with surrounding context based on content type, ensuring that search results include relevant context.

### Embedding Model

The VectorStore uses the BGE-M3 embedding model from BAAI, which provides high-quality embeddings for semantic search.

## Migration

To migrate existing transcript data to the vector store, use the `migrate_to_vector_store.py` script:

```bash
python scripts/migrate_to_vector_store.py
```

The migration process:
1. Scans the data directory for transcript files
2. Processes each transcript file
3. Adds the segments to the vector store
4. Verifies the migration was successful

## Testing

To test the vector store functionality, use the `test_vector_store.py` script:

```bash
python scripts/test_vector_store.py
```

The test script runs various search queries and retrieval operations to verify that the vector store is working correctly. 