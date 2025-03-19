# YouTube Transcript Analyzer

A web application for fetching, analyzing, and extracting insights from YouTube video transcripts. Supports multiple language models (Mistral and GPT-4) for advanced analysis and interactive chat.

## Features

- Fetch transcripts from YouTube videos
- Clean and format transcript text
- Multiple analysis tools:
  - Technical Summary
  - Code & Commands Extraction
  - Tools & Resources List
  - Workflow Extraction
- Support for multiple LLM backends:
  - Mistral 7B (local via Ollama)
  - GPT-4 (via OpenAI API)
- Comprehensive Library Page:
  - View all analyzed videos in one place
  - Access saved transcripts and analyses
  - Run additional analyses directly from the library
  - Track analysis history with timestamps
  - Filter by model type (Mistral/GPT-4)
- Detailed Individual Video Pages:
  - Clean, organized transcript view with minute-based timestamps
  - Video metadata and statistics
  - Direct link to YouTube video
  - Channel information and view count
  - Tabbed interface for transcript, analyses, and chat
  - Real-time analysis generation
- Enhanced LLM Analysis:
  - Focused LLM prompts for better technical insights
  - Specialized analysis for LLM-related content
  - Improved context handling for more relevant responses
  - Structured output with clear sections and bullet points
- Interactive Chat Interface:
  - Context-aware chat about video content
  - Smart context filtering for LLM-related content
  - Persistent chat history
  - Message management (delete, more actions)
  - Timestamps for all messages
  - Clean, modern UI with dropdown menus
  - Real-time updates and feedback

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
- Copy `.env.example` to `.env`
- Set your OpenAI API key (optional)
- Configure Ollama settings if needed

4. Install and start Ollama:
- Follow instructions at [Ollama.ai](https://ollama.ai)
- Pull the Mistral model: `ollama pull mistral`

5. Initialize the vector database:
```bash
python vector_db/migrate_to_vector_store.py
```
This will create the ChromaDB database in the `chroma_db` directory. Note: This directory is gitignored as it can grow large.

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to `http://127.0.0.1:5002`

### Running as a Background Service

You can set up the application to run continuously in the background using Supervisord:

1. Start the service:
```bash
./service/start.sh
```

2. Check the service status:
```bash
./service/status.sh
```

3. Stop the service:
```bash
./service/stop.sh
```

The service will continue running in the background even if you close your terminal, and will automatically restart if it crashes.

3. Paste a YouTube video URL and click "Get Transcript"

4. Use the analysis tools to extract insights:
- Choose between Mistral (local) or GPT-4
- Select the type of analysis you want to perform
- View the results in a structured format

5. Access the Library Page:
- Click "View Library" to see all analyzed videos
- Browse through saved transcripts and analyses
- Run additional analyses on any video
- Track analysis history with timestamps
- View results from different models side by side

6. Individual Video Pages:
- Click on any video title to access its dedicated page
- View organized transcript with minute-based timestamps
- Access video metadata and statistics
- Generate new analyses in real-time
- Chat with AI about specific video content
- Watch the original video on YouTube

## Project Structure

```
youtube_transcripts/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── backup/               # Backup-related scripts and utilities
│   ├── backup_vector_store.py     # Vector store backup script
│   └── setup_backup_cron.sh       # Cron job setup for scheduled backups
├── service/              # Service management scripts
│   ├── start.sh                   # Start the application service
│   ├── stop.sh                    # Stop the application service
│   ├── status.sh                  # Check service status
│   └── supervisord.conf           # Supervisord configuration
├── vector_db/            # Vector database related code
│   ├── vector_store.py            # Vector database implementation
│   ├── migrate_to_vector_store.py # Migration utility
│   └── test_vector_store.py       # Testing utility
├── scripts/
│   ├── youtube_transcript.py      # Transcript fetching and processing
│   └── transcript_analyzer.py     # Analysis logic and chat functionality
├── static/
│   └── css/              # Stylesheets
└── templates/
    ├── index.html        # Main web interface
    ├── library.html      # Library page
    ├── video_page.html   # Individual video page
    └── error.html        # Error page template
```

## Data Storage

- Transcripts: Stored as JSON files in video-specific directories
- Analyses: Saved with timestamps and model information
- Chat History: Persistent storage with message metadata
- Video Metadata: Includes thumbnails, channel info, and statistics
- Vector Database: ChromaDB for efficient semantic search of transcript segments
  - Located in `chroma_db/` directory (not version controlled)
  - Initialize using the migration script (see Setup section)
  - Automatic backups can be configured (see Backup section)
- All data is organized by video title for easy access

## Backup and Restore

The application includes functionality to backup and restore the ChromaDB vector store.

### Manual Backup

To manually trigger a backup:

```bash
python backup/backup_vector_store.py
```

To include API export in the backup:

```bash
python backup/backup_vector_store.py --api-export
```

### Scheduled Backups

To set up a weekly backup (runs every Sunday at midnight):

```bash
./backup/setup_backup_cron.sh
```

This will create a cron job that backs up the vector store to the external drive at `/Volumes/RileyNumber1/youtube_transcription/chroma_db_backup`.

For more details, see [Vector Store Backup Documentation](docs/vector_store_backup.md).

## Contributing

Feel free to open issues or submit pull requests for improvements.

## License

MIT License 