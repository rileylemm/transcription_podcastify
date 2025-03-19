# Application Architecture

## Core Classes and Their Locations

### Analyzer Classes

1. **TranscriptAnalyzer** (`scripts/transcript_analyzer.py`)
   - Handles YouTube transcript analysis
   - Methods for both Mistral and GPT analysis
   - Responsible for saving analysis results
   - Used by: `app.py` for transcript analysis endpoints

2. **RedditAnalyzer** (`scripts/reddit_analyzer.py`)
   - Handles Reddit post analysis
   - Methods for both Mistral and GPT analysis
   - Responsible for saving analysis results
   - Used by: `app.py` for Reddit analysis endpoints

### Vector Store Implementation

The VectorStore class exists in two locations:

1. **Legacy Location** (`scripts/vector_store.py`)
   - Original implementation
   - Should be considered deprecated
   - ⚠️ Do not use for new features

2. **Current Location** (`vector_db/vector_store.py`)
   - Current implementation
   - Used by all new features
   - Handles both transcript and Reddit post embeddings

## Important Notes

### Analysis Result Storage

When modifying analysis-related code, ensure to update all relevant places:

1. **Analysis Generation**
   - Analyzer classes (`TranscriptAnalyzer`, `RedditAnalyzer`)
   - Analysis route handlers in `app.py`

2. **Analysis Storage**
   - File system storage (in `data/` directory)
   - Vector store storage (using `VectorStore` class)

3. **Analysis Retrieval**
   - Frontend templates (`templates/`)
   - API routes in `app.py`

### Common Gotchas

1. **Endpoint Mismatches**
   - Frontend JavaScript calls in templates must match backend routes in `app.py`
   - Example: `/analyze_reddit_post` vs `/reddit/analyze`

2. **Data Structure Consistency**
   - Analysis results should maintain consistent structure between:
     - File storage
     - Vector store storage
     - Frontend display

3. **Class Method Consistency**
   - When updating analyzer methods, ensure both Mistral and GPT variants are updated
   - Keep save/load methods synchronized between classes

## Best Practices

1. **Adding New Features**
   - Use the current VectorStore implementation in `vector_db/vector_store.py`
   - Follow existing patterns for analysis storage and retrieval
   - Update this documentation when adding new classes or significant features

2. **Modifying Existing Features**
   - Check all related files listed in this document
   - Test both analysis generation and retrieval
   - Verify frontend displays updated data correctly

3. **Error Prevention**
   - Use consistent naming across frontend and backend
   - Maintain parallel structure in analyzer classes
   - Document any new endpoints or data structures

## Directory Structure Quick Reference

```
.
├── app.py                           # Main application file
├── scripts/
│   ├── transcript_analyzer.py       # YouTube transcript analysis
│   ├── reddit_analyzer.py          # Reddit post analysis
│   └── vector_store.py            # Legacy vector store (deprecated)
├── vector_db/
│   └── vector_store.py            # Current vector store implementation
└── templates/
    ├── reddit_post.html           # Reddit post display template
    └── reddit_library.html        # Reddit posts listing template
``` 