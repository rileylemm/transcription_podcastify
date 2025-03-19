# RAG Database Schema Documentation

## Overview

This document outlines the schema and structure for the RAG (Retrieval-Augmented Generation) database system used in the YouTube Transcript Analyzer. The system is designed to be modular and extensible, with future integration into a larger system-wide knowledge base in mind.

## Database Structure

### Vector Database

- **Technology**: ChromaDB
- **Location**: `chroma_db/`
- **Persistence**: Local persistence with backup support
- **Implementation**: `scripts/vector_store.py`
- **Migration Utility**: `scripts/migrate_to_vector_store.py`
- **Testing**: `scripts/test_vector_store.py`
- **Collections Structure**:
  ```
  vector_db/
  ├── transcripts/     # Chunked transcript embeddings
  ├── analyses/        # Analysis results embeddings
  └── chat_history/    # Relevant chat interactions
  ```

## Document Schema

### Base Metadata (Common across all documents)
```json
{
    "source_type": "youtube_transcript",
    "content_type": "transcript|analysis|chat",
    "system_metadata": {
        "added_date": "ISO-8601 datetime",
        "last_updated": "ISO-8601 datetime",
        "source_system": "youtube_analyzer",
        "version": "string",
        "embedding_model": "string"
    }
}
```

### Video Metadata
```json
{
    "video_metadata": {
        "video_id": "string",
        "video_url": "string",
        "title": "string",
        "channel_name": "string",
        "channel_url": "string",
        "published_date": "ISO-8601 datetime",
        "duration_seconds": "number",
        "view_count": "number",
        "like_count": "number",
        "description": "string",
        "tags": ["string"],
        "categories": ["string"],
        "thumbnail_url": "string",
        "language": "string",
        "capture_date": "ISO-8601 datetime"
    }
}
```

### Transcript Chunks
```json
{
    "chunk_metadata": {
        "chunk_index": "number",
        "total_chunks": "number",
        "timestamp_start": "number",
        "timestamp_end": "number",
        "word_count": "number",
        "speakers": ["string"],  // If available
        "language": "string",
        "is_translation": "boolean",
        "original_language": "string"  // If translated
    },
    "content": "string",
    "embedding": "vector"
}
```

### Analysis Documents
```json
{
    "analysis_metadata": {
        "analysis_type": "technical_summary|code_snippets|tools_and_resources|key_workflows",
        "model": "mistral|gpt-4",
        "analysis_date": "ISO-8601 datetime",
        "chunk_index": "number",  // If analyzing specific chunks
        "total_chunks": "number",
        "confidence_score": "number",
        "processing_time": "number"
    },
    "content": "string",
    "embedding": "vector"
}
```

### Chat History Documents
```json
{
    "chat_metadata": {
        "message_id": "string",
        "timestamp": "ISO-8601 datetime",
        "role": "user|assistant",
        "parent_message_id": "string",
        "referenced_chunks": ["string"],  // IDs of referenced transcript/analysis chunks
        "context_window_start": "number",
        "context_window_end": "number"
    },
    "content": "string",
    "embedding": "vector"
}
```

## Indexing Strategy

### Chunking Rules
- **Transcript Chunks**:
  - Maximum chunk size: 1000 tokens
  - Break at natural sentence boundaries
  - Maintain context overlap between chunks (100 tokens)
  - Preserve timestamp alignment

- **Analysis Chunks**:
  - Maximum chunk size: 1500 tokens
  - Break at section boundaries
  - Maintain hierarchical structure

### Embedding Generation
- Model: Multi-QA MiniLM L6 (default)
- Dimension: 384
- Normalized vectors
- Batch processing for efficiency

## Query Interface

### Search Parameters
```python
SearchParams = {
    "query": "string",
    "filters": {
        "source_type": ["string"],
        "content_type": ["string"],
        "date_range": {
            "start": "ISO-8601 datetime",
            "end": "ISO-8601 datetime"
        },
        "video_metadata": {
            "channel_name": "string",
            "language": "string",
            # ... other video metadata filters
        }
    },
    "limit": "number",
    "offset": "number",
    "min_relevance_score": "number"
}
```

## Future Extensibility

### Integration Points
- Modular collection structure
- Consistent metadata schema
- Standardized embedding format
- Flexible query interface

### Planned Features
- Multi-source integration
- Cross-reference support
- Enhanced metadata extraction
- Advanced filtering capabilities
- Real-time updates
- Distributed storage support

## Migration Strategy

### Export Format
```json
{
    "metadata": {
        "version": "string",
        "export_date": "ISO-8601 datetime",
        "source_system": "string"
    },
    "collections": [
        {
            "name": "string",
            "documents": [
                {
                    "content": "string",
                    "metadata": {},
                    "embedding": []
                }
            ]
        }
    ]
}
```

### Integration Process
1. Export collections to standardized format
2. Validate metadata completeness
3. Transform to target system schema
4. Batch import with verification
5. Maintain source tracking

## Backup and Maintenance

### Backup Strategy
- Regular snapshots of vector store
- Metadata exports
- Version control integration
- Incremental updates

### Maintenance Tasks
- Regular reindexing
- Embedding updates
- Metadata enrichment
- Performance optimization
- Data validation 